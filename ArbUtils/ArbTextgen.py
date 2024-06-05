import csv
import random
from collections import defaultdict, Counter


class CallsGenerator:
    def __init__(self, csv_file):
        self.bigram_transitions = defaultdict(Counter)
        self.trigram_transitions = defaultdict(Counter)
        self.start_bigrams = Counter()
        self.start_trigrams = Counter()
        self._analyze_texts(csv_file)

    def _analyze_texts(self, csv_file):
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                text = row[0]
                if not text:
                    continue
                # Анализируем биграммы
                for i in range(len(text) - 1):
                    bigram = text[i:i+2]
                    next_char = text[i+2:i+3]  # Следующий символ
                    if i == 0:
                        self.start_bigrams[bigram] += 1
                    if next_char:
                        self.bigram_transitions[bigram][next_char] += 1
                    else:
                        self.bigram_transitions[bigram][''] += 1  # End of text marker
                # Анализируем триграммы
                for i in range(len(text) - 2):
                    trigram = text[i:i+3]
                    next_char = text[i+3:i+4]  # Следующий символ
                    if i == 0:
                        self.start_trigrams[trigram] += 1
                    if next_char:
                        self.trigram_transitions[trigram][next_char] += 1
                    else:
                        self.trigram_transitions[trigram][''] += 1  # End of text marker

    def _get_next_char(self, transitions, current_gram):
        total = sum(transitions[current_gram].values())
        rand_val = random.uniform(0, total)
        cumulative = 0
        for char, count in transitions[current_gram].items():
            cumulative += count
            if cumulative > rand_val:
                return char
        return ''

    def generate_text(self, max_length=10, use_trigrams=True):
        if use_trigrams and self.start_trigrams:
            start_gram = random.choices(
                list(self.start_trigrams.keys()),
                weights=list(self.start_trigrams.values())
            )[0]
            transitions = self.trigram_transitions
        else:
            start_gram = random.choices(
                list(self.start_bigrams.keys()),
                weights=list(self.start_bigrams.values())
            )[0]
            transitions = self.bigram_transitions

        text = start_gram
        current_gram = start_gram

        while len(text) < max_length:
            next_char = self._get_next_char(transitions, current_gram)
            if next_char == '':
                break
            text += next_char
            current_gram = text[-len(start_gram):]  # Обновляем текущую грамму

        return self._postprocess(text)

    def _postprocess(self, text):
        # Пример постобработки: делаем первую букву заглавной
        return text.capitalize()
