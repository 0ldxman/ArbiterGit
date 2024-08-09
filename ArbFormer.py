import pprint

from ArbDatabase import DataManager, DataModel, DataDict
from dataclasses import dataclass, field
import re
from typing import Any, List, Callable, Optional
import itertools


class Validator:
    @staticmethod
    def is_numeric(value: str) -> bool:
        return any(char.isdigit() for char in value)

    @staticmethod
    def is_in_database(table: str, column: str, value: str) -> bool:
        db = DataManager()
        return db.check(table, f'{column} = "{value}"')

    @staticmethod
    def create_db_validator(table: str, column: str) -> Callable[[str], bool]:
        return lambda value: Validator.is_in_database(table, column, value)

    @staticmethod
    def is_text(value: str) -> bool:
        return bool(re.match(r'^[a-zA-Z\s]+$', value))


class Extractor:
    @staticmethod
    def extract_number(text: str) -> int:
        return int(''.join(filter(str.isdigit, text)))

    @staticmethod
    def extract_float(text: str) -> float:
        # Ищем все числа с возможной точкой для десятичной части
        match = re.search(r'\d+(\.\d+)?', text)
        if match:
            return float(match.group())
        return 0.0  # Возвращаем 0.0, если число не найдено

    @staticmethod
    def extract_text(text: str) -> str:
        return ''.join(filter(str.isalpha, text))

    @staticmethod
    def find_in_database(table: str, column_to_search: str, column_to_export: str) -> Callable[[str], any]:
        def extractor(value: str) -> any:
            db = DataManager()
            if db.check(table, f'{column_to_search} = "{value}"'):
                result = db.select_dict(table, filter=f'{column_to_search} = "{value}"')
                if result and len(result) > 0:
                    return result[0].get(column_to_export)
            return None

        return extractor


class Pattern:
    def __init__(self, tags: List[str] | str, field_name: str, *, validator: Callable[[str], bool] = None, extractor: Callable[[str], any] = None):
        # Проверка, является ли tags списком или строкой
        if isinstance(tags, list):
            self.tags = [tag for tag in tags]
        else:
            self.tags = [tags]

        self.field_name = field_name
        self.validator = validator
        self.extractor = extractor
        # Создаем паттерны для поиска
        self.patterns = self.generate_patterns(self.tags)

    def generate_patterns(self, tags: List[str]) -> List[str]:
        patterns = set()
        for tag in tags:
            # Генерация всех возможных паттернов для тегов
            base_patterns = self.generate_base_patterns(tag)
            # Создаем все возможные комбинации регистра для каждого паттерна
            for base_pattern in base_patterns:
                patterns.update(self.generate_case_variations(base_pattern))
        return list(patterns)

    def generate_base_patterns(self, tag: str) -> List[str]:
        # Генерация всех возможных комбинаций слов из тега
        words = tag.split()
        base_patterns = set()
        for r in range(1, len(words) + 1):
            for combination in itertools.combinations(words, r):
                base_patterns.add(' '.join(combination))
        return base_patterns

    def generate_case_variations(self, pattern: str) -> List[str]:
        words = pattern.split()
        case_variations = []
        # Генерируем все возможные комбинации регистра для слов
        for cases in itertools.product(*[self.case_variations(word) for word in words]):
            case_variations.append(' '.join(cases))
        return [f'{case}:\s*(.+)' for case in case_variations]

    def case_variations(self, word: str) -> List[str]:
        # Генерация вариаций регистра для одного слова
        return [
            word.lower(),
            word.upper(),
            word.capitalize(),
            word.title(),
            word.swapcase()
        ]

    def set_validator(self, validator: Callable[[str], bool]) -> None:
        self.validator = validator

    def set_extractor(self, extractor: Callable[[str], any]) -> None:
        self.extractor = extractor

    def extract_value(self, text: str) -> Optional[any]:
        # Попробуем найти значение по каждому паттерну
        for pattern in self.patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                if self.validator and not self.validator(value):
                    return None
                if self.extractor:
                    return [self.extractor(value), value]
                return [value, value]
        return None


class Former:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.data = {}
        self.patterns = []

    def add_pattern(self, pattern: Pattern) -> None:
        self.patterns.append(pattern)

    def set(self, field_name: str, value: list[str | int | float]) -> None:
        self.data[field_name] = value

    def parse_text(self, text:str):
        for pattern in self.patterns:
            if pattern.field_name in self.data:
                if self.data.get(pattern.field_name) is not None:
                    continue

            value = pattern.extract_value(text)
            self.set(pattern.field_name, value)

    def to_dict(self):
        total_dict = {}
        for key, value in self.data.items():
            if value is not None:
                total_dict[key] = value[0]
            else:
                total_dict[key] = None

        return total_dict


# name = Pattern('[Имя Фамилия]', field_name='name')
# race = Pattern('Раса', field_name='race')
# race.set_validator(Validator.create_db_validator('RACES_INIT', 'name'))
# race.set_extractor(Extractor.find_in_database('RACES_INIT', 'name', 'id'))
# org = Pattern('Организация', field_name='org')
# org.set_validator(Validator.create_db_validator('ORG_INIT', 'label'))
# org.set_extractor(Extractor.find_in_database('ORG_INIT', 'label', 'id'))
# sex = Pattern('Пол', field_name='sex')
# age = Pattern(['Возраст', 'возраст', '[Возраст]'], field_name='age', validator=Validator.is_numeric)
# age.set_extractor(Extractor.extract_number)
#
# registrator = Former()
# registrator.add_pattern(name)
# registrator.add_pattern(race)
# registrator.add_pattern(org)
# registrator.add_pattern(sex)
# registrator.add_pattern(age)
#
# registrator.parse_text(
#     '''
# иМЯ фАМИЛИЯ: Джон Сноу
# [Возраст]: 45
# Пол: Мужской
# Раса: Человек
# Организация: Новый Эдем
#     '''
# )
# print(registrator.data)
# pprint.pprint(name.__dict__)
