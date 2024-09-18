# -*- coding: utf-8 -*-
from ArbDatabase import DataManager, DataModel
import re
import random


class Extra(DataModel):
    def __init__(self, tag:str, **kwargs):
        self.data_manager = kwargs.get('data_manager') if kwargs.get('data_manager') else DataManager()
        self.tag = tag

        DataModel.__init__(self, 'EXTRA_INIT', f'tag = "{self.tag}"', data_manager=self.data_manager)
        self.name = self.get('name', 'Неизвестный')
        self.picture = self.get('picture', None)
        self.owner_id = self.get('owner', None)

    async def say(self, ctx, phrase:str):
        from ArbUIUX import ArbEmbed

        embed = ArbEmbed(self.name,
                         phrase,
                         logo_url=self.picture)
        message = await ctx.respond(f'-# Сообщение от **{self.name}** отправлено', ephemeral=True)
        await ctx.send('', embed=embed)
        await message.delete_original_response()

    def __repr__(self):
        return f'Extra.{self.tag}({self.name})'

    @staticmethod
    def get_unprivate_extras():
        db = DataManager()
        extras = db.select_dict('EXTRA_INIT', filter='owner is NULL')
        return [Extra(tag.get('tag'), data_manager=db) for tag in extras]

    @staticmethod
    def get_available_extras(owner_id:int):
        db = DataManager()
        extras = db.select_dict('EXTRA_INIT', filter=f'owner = {owner_id}')
        unprivate_extras = Extra.get_unprivate_extras()
        private_extras = [Extra(tag.get('tag'), data_manager=db) for tag in extras]

        available_extras = unprivate_extras + private_extras
        return available_extras

    @staticmethod
    def create_extra(tag:str, name:str, picture:str=None, owner_id:int=None):
        db = DataManager()
        db.insert('EXTRA_INIT', {'tag': tag, 'name': name, 'picture': picture, 'owner': owner_id})

        return Extra(tag)



class RPDice:
    def __init__(self, formula: str, difficulty: int = None):
        self.formula = formula
        self.difficulty = difficulty  # Уровень сложности проверки
        self.rolls = []  # Для хранения значений выпавших кубиков
        self.result = None  # Итоговое значение после всех вычислений

    def roll_dice(self, dice, num_rolls=1):
        """Функция для броска кубика, например 3d6."""
        sides = int(dice[1:])  # Количество сторон у кубика
        total_roll = 0
        for _ in range(num_rolls):
            roll = random.randint(1, sides)  # Генерируем случайное число от 1 до количества сторон
            total_roll += roll
            self.rolls.append(f"{dice}: {roll}")  # Сохраняем каждый бросок
        return total_roll

    def parse_and_calculate(self):
        """Основная функция для парсинга формулы и расчёта итогового значения."""
        if self.result is not None:
            # Если результат уже вычислен, возвращаем его (чтобы не было дублирования)
            return

        # Разбираем формулу на части (кубики и числа)
        tokens = re.findall(r'([+-]?[\d]*d[\d]+|[+-]?\d+)', self.formula)

        self.result = 0  # Сбрасываем результат перед началом вычисления

        for token in tokens:
            sign = -1 if token.startswith('-') else 1  # Определяем знак
            token = token.lstrip('+-')  # Убираем знак для дальнейшей обработки

            if 'd' in token:  # Если это кубик, например 3d6
                if 'd' in token:
                    parts = token.split('d')
                    num_rolls = int(parts[0]) if parts[0] else 1  # Число кубиков, если не указано, то 1
                    dice = 'd' + parts[1]  # Форматируем как d6, d100 и т.д.
                    self.result += sign * self.roll_dice(dice, num_rolls)
            else:
                # Если это просто число, добавляем его к результату
                self.result += sign * int(token)

    def get_result(self):
        """Вывод итогового результата и значений каждого выпавшего кубика."""
        if self.result is None:  # Проверка, не вычисляли ли мы результат ранее
            self.parse_and_calculate()

        total_passed = self.result >= self.difficulty if self.difficulty else True  # Проверка сложности
        return {
            "rolls": self.rolls,
            "total": self.result,
            "total_check": True if total_passed else False
        }

    async def output_results(self, ctx, character_id: int = None):
        from ArbUIUX import ArbEmbed, SuccessEmbed, ErrorEmbed
        from ArbCharacters import Character

        # Получаем результат без повторного расчёта
        results = self.get_result()

        rolled_dices = ''
        for roll in results.get('rolls'):
            rolled_dices += f'-# - {roll}\n'

        if self.difficulty:
            if results.get("total_check"):
                embed = SuccessEmbed('Удачная проверка',
                                     f'### Выпало: {self.result} — Удача!\n'
                                     f'-#  - *Формула: **{self.formula}***\n'
                                     f'-#  - *Сложность: **{self.difficulty}***\n\n'
                                     f'### Выпавшие значения:\n{rolled_dices}',
                                     footer=Character(character_id).name if character_id else ctx.author.display_name,
                                     logo_url=Character(character_id).picture if character_id else ctx.author.avatar)
            else:
                embed = ErrorEmbed('Неудачная проверка',
                                   f'### Выпало: {self.result} — Неудача\n'
                                   f'-# *Формула: **{self.formula}***\n'
                                   f'-# *Сложность: **{self.difficulty}***\n\n'
                                   f'### Выпавшие значения:\n{rolled_dices}',
                                   footer=Character(character_id).name if character_id else ctx.author.display_name,
                                   logo_url=Character(character_id).picture if character_id else ctx.author.avatar)

        else:
            embed = ArbEmbed('Проверка',
                             f'### Выпало: {self.result}\n'
                             f'-# *Формула: **{self.formula}***\n\n'
                             f'### Выпавшие значения:\n{rolled_dices}',
                             footer=Character(character_id).name if character_id else ctx.author.display_name,
                             logo_url=Character(character_id).picture if character_id else ctx.author.avatar)

        await ctx.respond('', embed=embed)
