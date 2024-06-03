from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.stem import WordNetLemmatizer
from googletrans import Translator
import spacy
from pymystem3 import Mystem
from nltk.util import ngrams
from nltk import pos_tag

from collections import Counter, defaultdict
import itertools
from transformers import pipeline





class TextChunker:
    def __init__(self, text:str, chunk_size:int):
        self.text = text
        self.chunk_size = chunk_size
        self.chunks = list(self.chunk_text())

    def chunk_text(self):
        for i in range(0, len(self.text), self.chunk_size):
            yield self.text[i:i + self.chunk_size]

    def get_chunks_as_list(self):
        return self.chunks

    def num_chunks(self):
        return len(self.chunks)

    def get_chunk(self, index):
        if 0 <= index < len(self.chunks):
            return self.chunks[index]
        return None

    def set_chunk_size(self, new_size):
        self.chunk_size = new_size
        self.chunks = list(self.chunk_text())

    def find_chunk(self, keyword):
        for chunk in self.chunks:
            if keyword in chunk:
                return chunk
        return None

    def remove_punctuation(self):
        import string
        self.text = ''.join(char for char in self.text if char not in string.punctuation)
        self.chunks = list(self.chunk_text())

    def reverse_chunks(self):
        return self.chunks[::-1]

    def merge_chunks(self):
        return ''.join(self.chunks)

    def clear_text(self):
        self.text = ''
        self.chunks = []

    def __add__(self, other):
        if isinstance(other, TextChunker):
            new_text = self.text + other.text
            new_chunk_size = max(self.chunk_size, other.chunk_size)
            return TextChunker(new_text, new_chunk_size)
        elif isinstance(other, str):
            new_text = self.text + other
            return TextChunker(new_text, self.chunk_size)
        else:
            raise TypeError("Only TextChunker objects or strings can be concatenated")

    def __radd__(self, other):
        if isinstance(other, str):
            new_text = other + self.text
            return TextChunker(new_text, self.chunk_size)
        else:
            raise TypeError("Can only concatenate with a string")

    def __iter__(self):
        return iter(self.chunks)

    def __len__(self):
        return len(self.chunks)

    def __repr__(self):
        return f'TextChunker(text={self.text}, chunk_size={self.chunk_size})'


class WordCounter:
    def __init__(self, text:str):
        self.text = text

    def count_words(self):
        words = self.text.split()
        return len(words)

    def count_unique_words(self):
        words = self.text.split()
        unique_words = set(words)
        return len(unique_words)


class TextTranslator:
    def __init__(self, text:str):
        self.text = text
        self.translator = Translator()

    def translate_to_english(self):
        translated_text = self.translator.translate(self.text, src='ru', dest='en').text
        return translated_text


class TextAnalyzer:
    def __init__(self, text: str):
        self.text = text
        self.nlp = spacy.load("ru_core_news_sm")
        self.mystem = Mystem()
        self.stop_words = set(stopwords.words('russian'))
        self.lemmatizer = WordNetLemmatizer()

        self.cache = {}

    def clean_text(self):
        """
        Удаляет все символы, кроме букв и пробелов.
        """
        cleaned_text = re.sub(r'[^\w\s]', '', self.text)
        return cleaned_text

    def sentence_tokenize(self):
        """
        Разбивает текст на предложения, используя SpaCy.
        """
        doc = self.nlp(self.text)
        sentences = [sent.text for sent in doc.sents]
        return sentences

    def word_tokenize(self):
        """
        Разбивает текст на слова.
        """
        clean_text = self.clean_text()
        words = word_tokenize(clean_text)
        return words

    def entities(self):
        clean_text = self.clean_text()

        # Используем PyMystem3 для лемматизации
        lemmatized_text = ''.join(self.mystem.lemmatize(clean_text))
        lemmatized_doc = self.nlp(lemmatized_text)
        lemmatized_entities = [(ent.text.strip().lower(), ent.label_) for ent in lemmatized_doc.ents]

        # Создаем словарь для группировки сущностей по их нормализованным именам
        normalized_entities = {}
        single_word_entities = set()  # Для хранения одиночных слов, которые уже присутствуют в словаре

        for text, label in lemmatized_entities:
            # Разделяем текст на отдельные части
            name_parts = text.split()

            # Используем все части имени для нормализации
            key = ' '.join(name_parts)
            # Если только одно слово
            if len(name_parts) == 1:
                # Проверяем, есть ли уже такое слово в словаре
                if key not in single_word_entities:
                    # Если нет, добавляем в словарь и помечаем как известное одиночное слово
                    normalized_entities[key] = (text, label)
                    single_word_entities.add(key)
            else:
                # Если ключ уже существует и новый вариант имени длиннее, заменяем его
                if key in normalized_entities:
                    if len(name_parts) > len(normalized_entities[key][0].split()):
                        normalized_entities[key] = (text, label)
                        single_word_entities.add(name_parts[0])
                else:
                    normalized_entities[key] = (text, label)
                    single_word_entities.add(name_parts[0])

        return list(normalized_entities.values())

    def get_lemma_tokens(self):
        tokens_lemmas = self.tokenize_and_lemmatize()
        entities = {}

        for token, lemma in tokens_lemmas:
            if lemma.isalpha() and lemma.lower() != token.lower():
                if lemma not in entities:
                    entities[lemma] = [token]
                else:
                    entities[lemma].append(token)

        return entities

    def tokenize_and_lemmatize(self):
        """
        Токенизирует и лемматизирует текст.
        """
        doc = self.nlp(self.text)
        tokens_lemmas = [(token.text, token.lemma_) for token in doc]
        return tokens_lemmas

    def sentiment_analysis(self):
        """
        Выполняет анализ настроений.
        """
        c_text = TextTranslator(self.text).translate_to_english()
        sia = SentimentIntensityAnalyzer()
        sentiment_vader = sia.polarity_scores(c_text)['compound']
        if sentiment_vader > 0.1:
            return "pos", sentiment_vader
        elif sentiment_vader < -0.1:
            return "neg", sentiment_vader
        else:
            return "neu", sentiment_vader

    def extract_keywords(self, num_keywords=5):
        """
        Извлекает ключевые слова из текста.
        """
        clean_text = self.clean_text()
        words = word_tokenize(clean_text)
        stopwords_ru = set(stopwords.words('russian'))
        words = [word.lower() for word in words if word.isalpha() and word.lower() not in stopwords_ru]
        fdist = FreqDist(words)
        keywords = fdist.most_common(num_keywords)
        return keywords

    def extract_top_words(self, num_words=10):
        """
        Извлекает наиболее значимые слова из текста.
        """
        clean_text = self.clean_text()
        words = word_tokenize(clean_text)
        stopwords_ru = set(stopwords.words('russian'))
        words = [word.lower() for word in words if word.isalpha() and word.lower() not in stopwords_ru]
        fdist = FreqDist(words)
        top_words = fdist.most_common(num_words)
        return top_words

    def extract_key_sentences(self, num_sentences=3):
        """
        Определяет ключевые предложения в тексте.
        """
        doc = self.nlp(self.text)
        sentences = [sent.text for sent in doc.sents]
        word_counts = Counter(self.word_tokenize())
        key_sentences = []

        for sentence in sentences:
            sentence_score = sum(word_counts[word.lower()] for word in word_tokenize(sentence))
            key_sentences.append((sentence, sentence_score))

        key_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence[0] for sentence in key_sentences[:num_sentences]]

    def pos_tagging(self):
        """
        Определяет части речи каждого слова в тексте.
        """
        doc = self.nlp(self.text)
        pos_tags = [(token.text, token.pos_) for token in doc]
        return pos_tags

    def extract_ngrams(self, n=2, num_ngrams=None):
        """
        Анализирует наиболее часто встречающиеся биграммы и триграммы в тексте.
        """
        clean_text = self.clean_text()
        words = word_tokenize(clean_text)
        n_grams = list(ngrams(words, n))
        fdist = FreqDist(n_grams)
        if num_ngrams:
            top_ngrams = fdist.most_common(num_ngrams)
            return top_ngrams
        else:
            return list(fdist.items())

    def extract_entities_from_ngrams(self, n=2, num_ngrams=None, min_freq=2):
        ngrams = self.extract_ngrams(n, num_ngrams)
        entities = []
        for ngram in ngrams:
            # Определяем, является ли данная n-грамма значимой
            if ngram[1] >= min_freq:
                filtered_ngram = [word.lower() for word in ngram[0] if word.isalpha()]
                ngram_text = ' '.join(filtered_ngram)
                entity_type = self.detect_entity_type(ngram_text)
                if entity_type:
                    entities.append((ngram_text, entity_type))
                print(filtered_ngram, entities)

        return entities

    def detect_entity_type(self, text):
        # Проверяем, есть ли результат для данного текста в кэше
        if text in self.cache:
            return self.cache[text]

        lemmatized_text = ''.join(self.mystem.lemmatize(text))
        lemmatized_doc = self.nlp(lemmatized_text)
        lemmatized_entities = [(ent.text.strip().lower(), ent.label_) for ent in lemmatized_doc.ents]

        # Проверяем, найдены ли какие-либо сущности
        entity_type = lemmatized_entities
        # Сохраняем результат в кэшей   21
        self.cache[text] = entity_type

        return entity_type

    def extract_entities_from_key_tokens(self):
        key_sentences = self.tokenize_special_chunks()
        lemmatized_chunks = []
        for chunk in key_sentences:
            doc_chunk = self.nlp(chunk)
            lemmatized_chunk = " ".join([token.lemma_ for token in doc_chunk])
            lemmatized_chunks.append(lemmatized_chunk)
        print(lemmatized_chunks)
        entities = []

        for sentence in lemmatized_chunks:
            # Определяем, является ли данная фраза сущностью
            entity_type = self.detect_entity_type(sentence)
            print(entity_type)
            if entity_type:
                for ent in entity_type:
                    entities.append(ent)

        return entities

    def tokenize_special_chunks(self):
        doc = self.nlp(self.text)

        # Определяем правила для обнаружения особых фраз
        special_chunks = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN", "ADJ"] and token.dep_ not in ["prep"]:
                # Если текущий токен относится к существительному, исключая предлоги,
                # добавляем всю фразу в список особых чанков
                special_chunk = [t.text for t in token.subtree if t.pos_ not in ["DET", "PUNCT", "CCONJ"]]
                if len(special_chunk) > 1:  # Игнорируем одиночные токены
                    special_chunks.append(" ".join(special_chunk))

        # Удаляем дублирующиеся элементы
        special_chunks = list(set(special_chunks))

        return special_chunks

    def clean_new_text(self, text:str):
        cleaned_text = re.sub(r'[^\w\s]', '', text)
        return cleaned_text
    def lemmatize(self, text:str, clean:bool=None):
        if clean:
            text = self.clean_new_text(text)

        doc = self.nlp(text)
        lemmatized_text = " ".join([token.lemma_ for token in doc])
        return lemmatized_text

    def lemmatized_special_tokens(self):
        chunks = self.tokenize_special_chunks()
        total_chunks = [self.lemmatize(chunk) for chunk in chunks]

        return total_chunks

class DialogueAnalyzer:
    def __init__(self, text):
        self.text = text
        self.dialogues = []
        self.actions = []
        self.non_rp_phrases = []
        self.describes = []
        self.process_dialogue()

    def process_dialogue(self):
        lines = self.text.split('\n')
        for line in lines:
            # Удаляем лишние пробелы по краям
            line = line.strip()

            # Игнорируем пустые строки
            if not line:
                continue

            # Нон РП фразы
            non_rp_matches = re.findall(r'\(\((.*?)\)\)', line)
            for match in non_rp_matches:
                self.non_rp_phrases.append(match)

            # Удаляем Нон РП фразы из основного текста
            line = re.sub(r'\(\(.*?\)\)', '', line).strip()

            #Описания
            action_matches = re.findall(r'\*{3}(.*?)\*{3}', line)
            for match in action_matches:
                self.describes.append(match)

            #удаляем описания
            line = re.sub(r'\*{3}.*?\*{3}', '', line).strip()

            # Действия персонажей
            action_matches = re.findall(r'\*{1,2}(.*?)\*{1,2}', line)
            for match in action_matches:
                self.actions.append(match)

            # Удаляем действия из основного текста
            line = re.sub(r'\*{1,2}.*?\*{1,2}', '', line).strip()

            # Оставшиеся фразы персонажей
            if line:
                self.dialogues.append(line)

    def get_dialogues(self):
        return self.dialogues

    def get_actions(self):
        return self.actions

    def get_non_rp_phrases(self):
        return self.non_rp_phrases

    def extract_keywords(self, num_keywords=5):
        text = ' '.join(self.dialogues)
        words = word_tokenize(text)
        words = [word.lower() for word in words if word.isalpha() and word.lower() not in stopwords.words('english')]
        freq_dist = Counter(words)
        return freq_dist.most_common(num_keywords)

    def pos_tagging(self):
        text = ' '.join(self.dialogues)
        words = word_tokenize(text)
        pos_tags = pos_tag(words)
        return pos_tags

    def special_tokenize(self):
        c_dialogues = '. '.join(self.dialogues)
        c_actions = '. '.join(self.actions)
        c_describe = '. '.join(self.describes)

        dia = TextAnalyzer(c_dialogues).tokenize_special_chunks()
        act = TextAnalyzer(c_actions).tokenize_special_chunks()
        desc = TextAnalyzer(c_describe).tokenize_special_chunks()

        return dia + act + desc

    def lemmatized_tokenize(self):
        c_dialogues = '. '.join(self.dialogues)
        c_actions = '. '.join(self.actions)
        c_describe = '. '.join(self.describes)

        dia = TextAnalyzer(c_dialogues).lemmatized_special_tokens()
        act = TextAnalyzer(c_actions).lemmatized_special_tokens()
        desc = TextAnalyzer(c_describe).lemmatized_special_tokens()

        return dia + act + desc

    def get_dict_of_sentiment(self):
        phrases = self.dialogues + self.actions + self.describes
        total_dict = {}
        for phrase in phrases:
            name, value = TextAnalyzer(phrase).sentiment_analysis()
            total_dict[phrase] = value
            print(value, phrase)

        total_values = total_dict.values()
        avg_value = sum(total_values) / len(total_values)

        return avg_value, total_dict

    def whole_text_sentiment(self):
        return TextAnalyzer(self.text).sentiment_analysis()

#
# text = """
# @краб помнишь февраль и то что было с моей тётей?
# Вроде да, если я правильно понял о чем ты
# Это когда её состояние стало хуже и ты сильно беспокоился?
# Всеми силами и неправдой, она все же вышла в конце марта
# Сейчас же её снова увезли на скорой
# Я кончился
# """
# anal = DialogueAnalyzer(text)
# print(anal.special_tokenize())
# print(anal.get_dict_of_sentiment())
# print(anal.whole_text_sentiment())