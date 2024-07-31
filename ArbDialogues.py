from ArbDatabase import DataManager, DataModel
from ArbCharacters import Character
from ArbUIUX import ArbEmbed


class Dialogue(DataModel):
    def __init__(self, dialogue_id:int, **kwargs):
        self.dialogue_id = dialogue_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'DIALOGUE_INIT', f'id = {self.dialogue_id}', data_manager=self.data_manager)

        self.label = self.get('label', 'Диалог')
        self.channel = self.get('channel', None)

    @staticmethod
    def get_dialogue_by_channel(channel: int, data_manager: DataManager = None):
        db = data_manager if data_manager is not None else DataManager()
        if db.check('DIALOGUE_INIT', f'channel = {channel}'):
            dialogue_id = db.select_dict('DIALOGUE_INIT', filter=f'channel = {channel}')[0].get('id')
            return Dialogue(dialogue_id, data_manager=db)
        else:
            return None


class CharacterMessage:
    def __init__(self, character_id:int, message:str, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.message = self.process_message(message)

    def get_character(self) -> Character:
        return Character(self.character_id, data_manager=self.data_manager)

    def process_message(self, message:str) -> str:
        return message

    def get_embed(self) -> ArbEmbed:
        character = self.get_character()
        message = self.message
        embed = ArbEmbed(f'{character.name}', f'— {message}', logo_url=character.picture)

        return embed

    def save_to_db(self, dialogue_id: int) -> None:
        query = {'dialogue_id': dialogue_id,
                 'character_id': self.character_id,
                 'message': self.message}

        self.data_manager.insert('DIALOGUE_MESSAGES', query)
