import pprint
import random
import re
from dataclasses import dataclass
from typing import List, Union

from ArbDatabase import DataManager, DataModel
from ArbCharacters import Character
from ArbUIUX import ArbEmbed
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googletrans import Translator



class TextTranslator:
    def __init__(self, text:str):
        self.text = text
        self.translator = Translator()

    def translate_to_english(self):
        translated_text = self.translator.translate(self.text, src='ru', dest='en').text
        return translated_text

@dataclass
class PhraseType:
    name: str
    pattern: str
    verb: str

    def matches(self, phrase: str) -> bool:
        return bool(re.search(self.pattern, phrase))


@dataclass
class Content:
    content: str
    type: str

    def get_verb(self):
        if self.type == 'крик':
            return random.choice(['крикнул', 'прокричал', 'воскликнул'])
        if self.type == 'вопрос':
            return random.choice(['вопросил', 'спросил', 'задал вопрос'])
        if self.type == 'фраза':
            return random.choice(['сказал', 'произнёс', 'промолвил'])
        if self.type == 'шепот':
            return random.choice(['прошептал', 'сказал шёпотом', 'тихо произнёс'])
        if self.type == 'рация':
            return random.choice(['сказал в рацию', 'проговорил в рацию', 'промолвил в рацию'])
        if self.type == 'крик рация':
            return random.choice(['прокричал в рацию', 'проорал в рацию', 'крикнул в рацию'])

        return random.choice(['сказал', 'произнёс', 'промолвил'])

    def __str__(self):
        if self.type == 'крик':
            return f"— {self.content[:-1]}!"
        if self.type == 'вопрос':
            return f'— {self.content[:-1]}?'
        if self.type == 'фраза':
            return f'— {self.content}'
        if self.type == 'шепот':
            return f'-# {self.content[3:]}'
        if self.type == 'рация':
            return f'`[РАЦИЯ]:` — {" ".join(self.content.split(" ")[1:])}'
        if self.type == 'крик рация':
            return f'`[РАЦИЯ]:` — {" ".join(self.content[:-1].split(" ")[1:])}!'


        return f'— {self.content}'


class MessageReader:
    def __init__(self, message: str, character_id:int=None):
        self.message = message
        self.character_id = character_id
        self.actions: List[str] = []  # Используем строки для действий
        self.descriptions: List[str] = []  # Используем строки для описаний
        self.non_rp: List[str] = []  # Не-РП сообщения
        self.phrases: List[Content] = []  # Фразы с типом
        self.mentions: List[str] = []  # Упоминания

        self.is_raw = False

        self.parse_message()
        self.raw_message = message
        self.mentions = [int(m) for m in self.mentions]

    def get_mentions(self, line:str) -> List[str]:
        """Извлекает упоминания из строки."""
        return re.findall(r'<@(.*?)>', line)

    def get_descriptions(self, line: str) -> List[str]:
        """Извлекает описания из строки."""
        return re.findall(r'\*\*\*(.*?)\*\*\*', line)

    def get_actions(self, line: str) -> List[str]:
        """Извлекает действия из строки."""
        return re.findall(r'\*{1,2}(.*?)\*{1,2}', line)

    def get_non_rp(self, line: str) -> Union[str, None]:
        """Извлекает не-РП сообщения из строки."""
        if line.startswith(('((', '//')):
            return line.lstrip('((').lstrip('//').strip()
        return None

    def is_shouting(self, text: str) -> bool:
        """Определяет, является ли текст криком (больше 50% символов в верхнем регистре)."""
        if text.endswith('!'):
            return True

        text = re.sub(r'\W', '', text)  # Удаляем не буквенно-цифровые символы
        if not text:
            return False
        upper_case_count = sum(1 for c in text if c.isupper())
        return (upper_case_count / len(text)) > 0.5

    def is_radio(self, text: str) -> bool:
        text = text.lower()
        if text.startswith('`[рация]:`'):
            return True
        if text.startswith('`[рация]`'):
            return True
        if text.startswith('*рация:*'):
            return True
        if text.startswith('рация:'):
            return True
        if text.startswith('р:'):
            return True
        if text.startswith('рация'):
            return True
        else:
            return False

    def determine_phrase_type(self, phrase: str) -> str:
        """Определяет тип фразы и возвращает соответствующий формат."""
        if self.is_radio(phrase) and self.is_shouting(phrase):
            return 'крик рация'
        if self.is_shouting(phrase):
            return 'крик'
        if self.is_radio(phrase):
            return 'рация'
        if phrase.startswith('-#'):
            return 'шепот'
        if phrase.endswith('?'):
            return 'вопрос'

        return 'фраза'

    def delete_patterns(self, line: str, pattern: str) -> str:
        """Удаляет паттерн из строки."""
        return re.sub(pattern, '', line).strip()

    def parse_message(self):
        """Разбирает сообщение и извлекает действия, описания, фразы и не-РП сообщения."""
        lines = self.message.split('\n')
        if lines[0].startswith('/'):
            lines[0] = lines[0][1:]
            self.is_raw = True

        for line in lines:
            line = line.strip()
            if not line:
                continue

            print(line[:1])
            if line.startswith('- ') or line.startswith('— '):
                line = line[2:]
            elif line.startswith('-') and line[:2] != '-#':
                line = line[1:]
            elif line.startswith('—'):
                line = line[1:]

            non_rp = self.get_non_rp(line)
            if non_rp:
                self.non_rp.append(non_rp)
                continue

            mentions = self.get_mentions(line)
            if mentions:
                self.mentions.extend(mentions)

            describes = self.get_descriptions(line)
            if describes:
                self.descriptions.extend(describes)
            line = self.delete_patterns(line, r'\*\*\*.*?\*\*\*')

            actions = self.get_actions(line)
            if actions:
                self.actions.extend(actions)
            line = self.delete_patterns(line, r'\*{1,2}(.*?)\*{1,2}')

            if line:
                phrase_type = self.determine_phrase_type(line)
                print(line, phrase_type, mentions)
                self.phrases.append(Content(content=line, type=phrase_type))

    def get_action_prefix(self, verb:str):
        from ArbCharacters import Character

        if self.character_id:
            return f'{verb} {Character(self.character_id).name}'
        else:
            return f'{verb} неизвестный'

    def __str__(self) -> str:
        """Форматирует сообщение в требуемом формате."""
        if self.is_raw:
            return self.raw_message[1:]

        constructed_message = []

        for i in range(max(len(self.descriptions), len(self.phrases), len(self.actions))):
            if i < len(self.descriptions):
                constructed_message.append(f'***{self.descriptions[i]}***')

            if i < len(self.phrases):
                phrase = self.phrases[i]

                if i < len(self.actions):
                    action = self.actions[i]
                    constructed_message.append(f'{phrase.__str__()} **{self.get_action_prefix(phrase.get_verb())} {action}**')
                else:
                    constructed_message.append(f'{phrase.__str__()}')
            else:
                if i < len(self.actions):
                    constructed_message.append(f'**{self.actions[i]}**')

        return '\n'.join(constructed_message)

    def create_sounds(self):
        from ArbSounds import Sound

        for phrase in self.phrases:
            if phrase.type == 'шепот':
                Sound.create_sound(self.character_id, 'Whisper', random.randint(10, 150), phrase.content)
            elif phrase.type == 'крик':
                Sound.create_sound(self.character_id, 'Scream', random.randint(50, 200), phrase.content)
            elif phrase.type in ['рация', 'крик рация']:
                Sound.create_sound(self.character_id, 'Radio', random.randint(50, 150), phrase.content)
            else:
                Sound.create_sound(self.character_id, 'Talk', random.randint(50, 150), phrase.content)

        for _ in self.non_rp:
            Sound.create_sound(self.character_id, 'Sneeze', random.randint(50, 150))

        for action in self.actions:
            Sound.create_sound(self.character_id, 'Action', random.randint(10, 110), action)


class Dialogue(DataModel):
    def __init__(self, dialogue_id:int, **kwargs):
        self.dialogue_id = dialogue_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'DIALOGUE_INIT', f'id = {self.dialogue_id}', data_manager=self.data_manager)

        self.label = self.get('label', 'Диалог')
        self.channel = self.get('channel', None)

    def get_total_messages(self):
        data = self.data_manager.select_dict('DIALOGUE_MESSAGES', filter=f'dialogue_id = {self.dialogue_id}')
        character_messages = {}
        total_messages = []

        for message in data:
            if message.get('character_id') not in character_messages:
                character_messages[message.get('character_id')] = []

            character_messages[message.get('character_id')].append(message.get("message"))
            total_messages.append(message.get("message"))

        return total_messages, character_messages

    def calculate_dialogue_sentiment(self):
        from ArbUtils.ArbDataParser import ListChunker

        total_messages = self.get_total_messages()[0]
        if not total_messages:
            return 0


        content = "\n".join(total_messages)
        content = Dialogue.clean_text(content)
        chunks = ListChunker(25, content.split("\n"))
        sia = SentimentIntensityAnalyzer()

        sentiment_sum = 0

        for chunk in chunks:
            inputed_text = '\n'.join(chunk)
            translated_text = TextTranslator(inputed_text).translate_to_english()
            sentiment_vader = sia.polarity_scores(translated_text)['compound']
            sentiment_sum += sentiment_vader

        sentiment_vader = sentiment_sum / len(chunks) if chunks else 0.0


        return sentiment_vader

    def type_dialogue_memory(self, sentiment:float):
        if -0.2 <= sentiment <= 0.2:
            return 'Dialogue'
        elif 0.2 < sentiment <= 0.45:
            return 'PleasantDialogue'
        elif 0.45 < sentiment:
            return 'HeartfeltConversation'
        elif -0.45 <= sentiment < -0.2:
            return 'UnpleasantDialogue'
        elif sentiment < 0.45:
            return 'Quarrel'
        else:
            return 'Dialogue'

    def type_familiarity(self, sentiment:float):
        if -0.3 <= sentiment <= 0.3:
            return 'Encounter'
        elif 0.3 < sentiment:
            return 'PleasantEncounter'
        elif sentiment < -0.3:
            return 'UnpleasantEncounter'
        else:
            return 'Encounter'

    def create_memories(self):
        sentiment = self.calculate_dialogue_sentiment()

        characters = self.get_total_messages()[1]
        if not characters:
            return

        from ArbCharacterMemory import MemoryEvent
        memory_type = self.type_dialogue_memory(sentiment)
        familiarity_type = self.type_familiarity(sentiment)

        for character in characters:
            date = Character(character, data_manager=self.data_manager).update
            self.create_familiars(character, familiarity_type)
            MemoryEvent.create_memory(character, memory_type, f'Разговор {self.label}', None, date, False)

    def create_familiars(self, character_id:int, familiarity_type:str):
        characters = self.get_total_messages()[1]
        if not characters:
            return

        if len(list(characters.keys())) == 1:
            return

        date = Character(character_id, data_manager=self.data_manager).update
        _ = characters.pop(character_id)
        from ArbCharacterMemory import MemoryEvent, CharacterRelations
        character_encounters = list(CharacterRelations(character_id, data_manager=self.data_manager).relations.keys())
        print(character_encounters)

        for character in characters:
            if character not in character_encounters:
                print('тут', character, character_id)
                CharacterRelations.create_familiar(character, character_id, 'Familiar', None)
                CharacterRelations.create_relation_values(character_id, character)
                MemoryEvent.create_memory(character_id, familiarity_type, f'Знакомство после разговора {self.label}', character, date, False)

    async def delete_dialogue(self):
        self.create_memories()
        self.delete_record()
        self.data_manager.delete('DIALOGUE_MESSAGES', f'dialogue_id = {self.dialogue_id}')

    @staticmethod
    def clean_text(text:str):
        """
        Удаляет все символы, кроме букв и пробелов.
        """
        cleaned_text = re.sub(r'[^\w\s]', '', text)
        return cleaned_text

    @staticmethod
    def get_dialogue_by_channel(channel: int, data_manager: DataManager = None):
        db = data_manager if data_manager is not None else DataManager()
        if db.check('DIALOGUE_INIT', f'channel = {channel}'):
            dialogue_id = db.select_dict('DIALOGUE_INIT', filter=f'channel = {channel}')[0].get('id')
            return Dialogue(dialogue_id, data_manager=db)
        else:
            return None

    @staticmethod
    def create_dialogue(label: str, channel: int, data_manager: DataManager = None) -> 'Dialogue':
        db = data_manager if data_manager is not None else DataManager()
        dialogue_id = db.maxValue('DIALOGUE_INIT', 'id') + 1
        db.insert('DIALOGUE_INIT', {'id': dialogue_id, 'label': label, 'channel': channel})

        return Dialogue(dialogue_id, label=label, channel=channel, data_manager=db)


class CharacterMessage:
    def __init__(self, character_id:int, message:str, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.message = self.process_message(message)
        self.proccessed_data = MessageReader(message, self.character_id)

    def get_character(self) -> Character:
        return Character(self.character_id, data_manager=self.data_manager)

    def process_message(self, message:str) -> str:
        new_message = MessageReader(message, self.character_id)
        new_message.create_sounds()
        return new_message.__str__()

    def get_embed(self) -> ArbEmbed:
        character = self.get_character()
        message = self.message
        embed = ArbEmbed(f'{character.name}', f'{message}', logo_url=character.picture)

        return embed

    def save_to_db(self, dialogue_id: int) -> None:
        phrases = self.proccessed_data.phrases
        for phrase in phrases:
            query = {'dialogue_id': dialogue_id,
                     'character_id': self.character_id,
                     'message': phrase.content}

            self.data_manager.insert('DIALOGUE_MESSAGES', query)
