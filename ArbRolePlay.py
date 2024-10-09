# -*- coding: utf-8 -*-
import datetime

import discord

from ArbDatabase import DataManager, DataModel
from ArbCharacters import Character
import re
import random
from dataclasses import dataclass
import discord.ext


class Extra(DataModel):
    def __init__(self, tag:str, **kwargs):
        self.data_manager = kwargs.get('data_manager') if kwargs.get('data_manager') else DataManager()
        self.tag = tag

        DataModel.__init__(self, 'EXTRA_INIT', f'tag = "{self.tag}"', data_manager=self.data_manager)
        self.name = self.get('name', 'Неизвестный')
        self.picture = self.get('picture', None)
        self.owner_id = self.get('owner', None)

    async def say(self, ctx, phrase:str, picture:str=None):
        from ArbUIUX import ArbEmbed
        embed = ArbEmbed(self.name,
                         phrase,
                         logo_url=self.picture, picture=picture if picture else None)
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


class RPSystem:
    def __init__(self, character_id:int, **kwargs):
        self.id = character_id
        self.data_manager = kwargs.get('data_manager', DataManager())

    def get_relation_to_character(self, target_id: int):
        from ArbCharacterMemory import CharacterRelations

        return CharacterRelations(self.id, data_manager=self.data_manager).get_relationship(target_id)

    def get_relation_of_character(self, target_id: int):
        from ArbCharacterMemory import CharacterRelations

        return CharacterRelations(target_id, data_manager=self.data_manager).get_relationship(self.id)

    @staticmethod
    def update_relation_to_character(character_id:int, target_id:int, **kwargs):
        from ArbCharacterMemory import CharacterRelations

        CharacterRelations.update_relations(character_id, target_id, kwargs.get('trust', 0), kwargs.get('sympathy', 0), kwargs.get('respect', 0), kwargs.get('love', 0))

    async def get_character_user(self, character_id:int, bot_id:int=None) -> int | None:
        from ArbCore import Player
        user = Player.get_owner_by_character_id(character_id)
        if not user or user.player_id == bot_id:
            users = Player.get_players_of_character(character_id)
            if users:
                user = random.choice(users)
                user = user.player_id
            else:
                return None
        else:
            user = user.player_id

        return user

    def waiting_embed(self):
        from ArbUIUX import ArbEmbed

        embed = ArbEmbed('Ожидание ответа :clock4:', 'Ожидание ответа от персонажа...', footer=Character(self.id).name, logo_url=Character(self.id).picture)
        return embed

    async def character_interaction(self, ctx, target_id:int, title:str, desc:str, accept_label:str, deny_label:str, check_type:str=None):
        from ArbUIUX import SuccessEmbed, InviteView
        from ArbCharacters import Character

        user_id = await self.get_character_user(target_id, ctx.bot.user.id)
        print(user_id)
        if not user_id:
            relationship = self.get_relation_of_character(target_id)
            if check_type == 'trust':
                if relationship.trust >= 50:
                    return 'Accept'
                else:
                    return 'Deny'
            elif check_type == 'sympathy':
                if relationship.sympathy >= 50:
                    return 'Accept'
                else:
                    return 'Deny'
            elif check_type == 'respect':
                if relationship.respect >= 50:
                    return 'Accept'
                else:
                    return 'Deny'
            elif check_type == 'love':
                if relationship.love >= 50:
                    return 'Accept'
                else:
                    return 'Deny'
            else:
                if relationship.calculate_avg_relation() >= 50:
                    return 'Accept'
                else:
                    return 'Deny'


        embed = SuccessEmbed(f'{title}',
                             f'{desc}',
                             footer=f'{Character(target_id).name}',
                             footer_logo=Character(target_id).picture)
        embed.set_author(f'{Character(self.id).name}', icon_url=Character(self.id).picture)

        view = InviteView(ctx, accept_label=accept_label, deny_label=deny_label, acceptor=ctx.bot.get_user(user_id))
        await ctx.bot.get_user(user_id).send(embed=embed, view=view)
        result = await ctx.bot.wait_for('interaction')
        return result.custom_id

    def positive_embed(self, title:str, desc:str, target_id:int, picture:str=None):
        from ArbUIUX import SuccessEmbed
        embed = SuccessEmbed(title, desc,
                             picture=picture,
                             footer=f'{Character(target_id).name}',
                             footer_logo=Character(target_id).picture)
        embed.set_author(f'{Character(self.id).name}', icon_url=Character(self.id).picture)
        return embed

    def negative_embed(self, title:str, desc:str, target_id:int):
        from ArbUIUX import ErrorEmbed
        embed = ErrorEmbed(title, desc,
                             footer=f'{Character(target_id).name}',
                             footer_logo=Character(target_id).picture)
        embed.set_author(f'{Character(self.id).name}', icon_url=Character(self.id).picture)
        return embed

    async def kiss(self, ctx, target_id:int):
        load_embed = await ctx.respond(embed=self.waiting_embed(), ephemeral=True)

        result = await self.character_interaction(ctx, target_id, 'Поцелуй',
                                                  f'**{Character(self.id).name}** хочет поцеловать **{Character(target_id).name}**.\n\nВы ответите взаимностью или отстранитесь?',
                                                  'Поцеловать', 'Отстраниться', 'love')

        print(result)

        if result == 'Accept':
            embed = self.positive_embed('Поцелуй',
                                        f'***{Character(self.id).name}** медленно подходит и берёт **{Character(target_id).name}** за руки, после чего они заключаются в тёплые объятия и сливаются в страстном поцелуе...*',
                                        target_id,
                                        picture=f'https://media.discordapp.net/attachments/732969100204310548/1288876950643019836/Leonardo_Kino_XL_real_lighting_cinematographic_artisticCloseup_3.jpg?ex=66f6c7b3&is=66f57633&hm=329f9b231bd4fe28726905755175c7a7d17d21aa6c1cb534b64d253c6b73adc9&=&format=webp&width=720&height=404')
            await ctx.respond(embed=embed)

            self.update_relation_to_character(self.id, target_id, love=5, trust=1)
            self.update_relation_to_character(target_id, self.id, love=5, trust=1)

        else:
            embed = self.negative_embed('Поцелуй',
                                        f'***{Character(self.id).name}** медленно подходит и берёт **{Character(target_id).name}** за руки, однако **{Character(target_id).name}** отстраняется и грустно отходит в сторону...*',
                                        target_id)

            self.update_relation_to_character(self.id, target_id, love=-10, trust=-10)
            self.update_relation_to_character(target_id, self.id, love=-20, trust=-5)

            await ctx.respond(embed=embed)

        await load_embed.delete_original_response()

    async def hug(self, ctx, target_id:int):
        load_embed = await ctx.respond(embed=self.waiting_embed(), ephemeral=True)
        result = await self.character_interaction(ctx, target_id, 'Объятия',
                                                  f'**{Character(self.id).name}** хочет обнять **{Character(target_id).name}**.\n\nВы согласны или отстранитесь?',
                                                  'Обнять', 'Отстраниться', 'sympathy')

        if result == 'Accept':
            embed = self.positive_embed('Объятия',
                                        f'***{Character(self.id).name}** быстро сближается с **{Character(target_id).name}** и заключает в крепкие объятия...*',
                                        target_id,
                                        picture=f'https://media.discordapp.net/attachments/732969100204310548/1288876950215196713/Leonardo_Kino_XL_real_lighting_cinematographic_artisticCloseup_2.jpg?ex=66f6c7b3&is=66f57633&hm=f21279cdb717e56a67e5ca479cfcb40c6b757833ed0a0653a303c2e9b5945655&=&format=webp&width=666&height=666')

            self.update_relation_to_character(self.id, target_id, sympathy=2, trust=1)
            self.update_relation_to_character(target_id, self.id, sympathy=2, trust=1)

            await ctx.respond(embed=embed)
        else:
            embed = self.negative_embed('Объятия',
                                        f'***{Character(self.id).name}** быстро сближается с **{Character(target_id).name}** и заключает в крепкие объятия, но **{Character(target_id).name}** отталкивает **{Character(self.id).name}** и раздарженно отходит...*',
                                        target_id)
            await ctx.respond(embed=embed)

            self.update_relation_to_character(self.id, target_id, sympathy=-5, trust=-10)
            self.update_relation_to_character(target_id, self.id, sympathy=-10, trust=-5)

        await load_embed.delete_original_response()

    async def clap_on_shoulder(self, ctx, target_id:int):
        load_embed = await ctx.respond(embed=self.waiting_embed(), ephemeral=True)
        result = await self.character_interaction(ctx, target_id, 'Дружеский жест',
                                                  f'**{Character(self.id).name}** хлопает **{Character(target_id).name}** по плечу.\n\nКак вы отреагируете?',
                                                  'Позитивно', 'Негативно', 'sympathy')

        if result == 'Accept':
            embed = self.positive_embed('Дружеский жест',
                                        f'***{Character(self.id).name}** хлопает по плечу **{Character(target_id).name}**, после чего **{Character(target_id).name}** кажется становится лучше...*',
                                        target_id,
                                        picture=f'https://media.discordapp.net/attachments/732969100204310548/1288903102094770176/Leonardo_Kino_XL_real_lighting_cinematographic_artisticCloseup_1.jpg?ex=66f6e00e&is=66f58e8e&hm=6fb3c123405dac0a1e1b2de4d1e427e8eb9cfc3cf968abcccb4dd353f0d67b7c&=&format=webp&width=720&height=404')

            self.update_relation_to_character(self.id, target_id, sympathy=1, trust=3)
            self.update_relation_to_character(target_id, self.id, sympathy=3, trust=2)

            await ctx.respond(embed=embed)
        else:
            embed = self.negative_embed('Дружеский жест',
                                        f'***{Character(self.id).name}** хлопает по плечу **{Character(target_id).name}**, но **{Character(target_id).name}** снимает руку **{Character(self.id).name}** с плеча и раздарженно отходит...*',
                                        target_id)

            self.update_relation_to_character(self.id, target_id, sympathy=-5, trust=-3)
            self.update_relation_to_character(target_id, self.id, sympathy=-5, trust=-1)

            await ctx.respond(embed=embed)

        await load_embed.delete_original_response()

    async def slap(self, ctx, target_id:int):
        from ArbHealth import Body, Injury

        embed = self.negative_embed('Пощёчина',
                                    f'***{Character(self.id).name}** даёт пощёчину **{Character(target_id).name}** по лицу!*', target_id)

        self.update_relation_to_character(self.id, target_id, sympathy=-5, trust=-10)
        self.update_relation_to_character(target_id, self.id, sympathy=-15, trust=-10)

        head_group = Body(target_id, data_manager=self.data_manager).get_bodyparts_in_group('Голова')
        if head_group:
            for part in head_group:
                if part.label == 'Голова':
                    Injury.create_injury(target_id, 'Bruise', part.element_id, 1, f'Пощёчина от {Character(self.id).name}')
                    break

        await ctx.respond(embed=embed)

    async def punch(self, ctx, target_id:int):
        from ArbHealth import Body, Injury

        embed = self.negative_embed('Удар',
                                    f'***{Character(self.id).name}** бьёт **{Character(target_id).name}***', target_id)

        self.update_relation_to_character(self.id, target_id, sympathy=-10, trust=-20)
        self.update_relation_to_character(target_id, self.id, sympathy=-20, trust=-20)

        head_group = Body(target_id, data_manager=self.data_manager).get_bodyparts_in_group('Голова')
        if head_group:
            for part in head_group:
                if part.label == 'Голова':
                    Injury.create_injury(target_id, 'Bruise', part.element_id, 3,
                                         f'Удар от {Character(self.id).name}')
                    break

        await ctx.respond(embed=embed)


    async def handshake(self, ctx, target_id:int):
        load_embed = await ctx.respond(embed=self.waiting_embed(), ephemeral=True)

        result = await self.character_interaction(ctx, target_id, 'Рукопожатие',
                                                  f'**{Character(self.id).name}** протягивает **{Character(target_id).name}** руку.\n\nКак вы поступите?',
                                                  'Пожать', 'Игнорировать', 'respect')

        print(result)

        if result == 'Accept':
            embed = self.positive_embed('Рукопожатие',
                                        f'***{Character(self.id).name}** протягивает свою руку **{Character(target_id).name}** и **{Character(target_id).name}** жмёт её.*',
                                        target_id,
                                        picture=f'https://media.discordapp.net/attachments/732969100204310548/1288876951003599032/Leonardo_Kino_XL_real_lighting_cinematographic_artisticCloseup_3_2.jpg?ex=66f6c7b3&is=66f57633&hm=e403be1080acc9124366a99062e31706ccff261e63b954513e27aa46c4c34b33&=&format=webp&width=720&height=404')

            self.update_relation_to_character(self.id, target_id, respect=2, trust=2)
            self.update_relation_to_character(target_id, self.id, respect=5, trust=1)

            await ctx.respond(embed=embed)
        else:
            embed = self.negative_embed('Рукопожатие',
                                        f'***{Character(self.id).name}** протягивает свою руку **{Character(target_id).name}**, но **{Character(target_id).name}** игнорирует этот жест и проходит мимо...*',
                                        target_id)

            self.update_relation_to_character(self.id, target_id, respect=-5, trust=-3)
            self.update_relation_to_character(target_id, self.id, respect=-2, trust=-1)

            await ctx.respond(embed=embed)

        await load_embed.delete_original_response()

    async def salute(self, ctx, target_id:int):
        embed = self.positive_embed('Воинское приветствие',
                                    f'***{Character(self.id).name}** видит **{Character(target_id).name}** и исполняет воинское приветствие.*', target_id,
                                    picture=f'https://media.discordapp.net/attachments/732969100204310548/1288877765931696178/Leonardo_Kino_XL_real_lighting_cinematographic_artisticA_man_d_1.jpg?ex=66f6c875&is=66f576f5&hm=a38b877662e25c8b569ea84e2de5648397ea37f5a7bcee526d1f7a1fa98e96b2&=&format=webp&width=720&height=404')

        self.update_relation_to_character(target_id, self.id, respect=1)

        await ctx.respond(embed=embed)

    async def welcome(self, ctx, target_id:int):
        embed = self.positive_embed('Дружеское приветствие',
                                    f'***{Character(self.id).name}** видит **{Character(target_id).name}** и дружелюбно приветствует его.*',
                                    target_id,
                                    picture=f'https://media.discordapp.net/attachments/732969100204310548/1288879854133051402/Leonardo_Kino_XL_real_lighting_cinematographic_artisticA_man_d_3_1.jpg?ex=66f6ca67&is=66f578e7&hm=da9a1ab392eae845ec32deefbf1cf7007063275245e1a8d3ef762426151e80e9&=&format=webp&width=720&height=404')

        self.update_relation_to_character(target_id, self.id, sympathy=1)

        await ctx.respond(embed=embed)

    #TODO: Команда "Завязать диалог" для игроков, чтобы не ждать куратора постоянно, но диалог начинается в ветке и только между 2 персонажами




@dataclass()
class MessageContent:
    content: str
    attachments: list[discord.File]
    embeds: list[discord.Embed]

@dataclass
class DataMessage:
    __resources_channel__ = 1248998863730380834  # ID канала архива
    bot: discord.Bot
    messages: list[discord.Message]
    archive_channel_id: int

    async def _get_archive_channel(self) -> discord.TextChannel | discord.Thread:
        channel = self.bot.get_channel(self.archive_channel_id)
        if not channel:
            raise ValueError("Archive channel not found")
        return channel

    async def _get_resources_channel(self):
        channel = self.bot.get_channel(self.__resources_channel__)
        if not channel:
            raise ValueError("Archive channel not found")
        return channel

    async def _send_content_to_archive(self, attachments: list[discord.File] = None):
        """
        Отправляет сообщение в архивный канал с заданным контентом и вложениями
        """
        channel = await self._get_resources_channel()
        await channel.send(files=attachments)

    async def _send_content_to_target(self, attachments: list[discord.File] = None):
        """Отправляет сообщение в выбранный канал с заданным контентом и вложениями
                """
        channel = await self._get_archive_channel()
        await channel.send(files=attachments)

    async def _send_content_to_all(self, attachments: list[discord.File] = None):
        """Отправляет сообщение во все каналы с заданным контентом и вложениями
                """
        channels = [await self._get_archive_channel(), await self._get_resources_channel()]
        for channel in channels:
            await channel.send(files=attachments)

    async def _send_embeds_to_archive(self, embeds: list[discord.Embed]):
        """
        Отправляет embeds в архивный канал
        """
        channel = await self._get_resources_channel()
        await channel.send(embeds=embeds)

    async def _process_messages(self) -> list[MessageContent]:
        total_content: list[MessageContent] = []

        content_buffer = ''
        attachments_buffer = []
        current_user = None

        for message in self.messages:
            if message.author.id != current_user and any([content_buffer, attachments_buffer]):
                total_content.append(MessageContent(content=content_buffer,
                                                        attachments=attachments_buffer,
                                                        embeds=[]))
                content_buffer = f"\n**ОТПРАВИТЕЛЬ:** {message.author.mention}: "  # Очищаем текстовый буфер
                attachments_buffer = []  # Очищаем буфер вложений
                current_user = message.author.id

            if message.embeds:
                total_content.append(MessageContent(embeds=message.embeds,
                                                    attachments=[],
                                                    content=message.content))
                continue

            if message.attachments:
                for attachment in message.attachments:
                    await self._send_content_to_archive([await attachment.to_file()])
                    if len(attachments_buffer) < 10:
                        attachments_buffer.append(await attachment.to_file())
                    else:
                        # Если в чанке уже 10 вложений, отправляем и очищаем буфер
                        total_content.append(MessageContent(content=content_buffer,
                                                            attachments=attachments_buffer,
                                                            embeds=[]))
                        content_buffer = ""  # Очищаем текстовый буфер
                        attachments_buffer = [await attachment.to_file()]  # Добавляем текущее вложение


            if len(content_buffer) + len(message.content) >= 2000:
                total_content.append(MessageContent(content=content_buffer,
                                                    attachments=attachments_buffer,
                                                    embeds=[]))
                content_buffer = message.content  # Начинаем новый чанк с текущего сообщения
                attachments_buffer = []  # Очищаем буфер вложений
            else:
                content_buffer += f"\n{message.content}"

        return total_content

    async def archivate(self):
        messages_content = await self._process_messages()
        archive_channel = await self._get_archive_channel()

        for content in messages_content:
            if content.embeds:
                await self._send_embeds_to_archive(content.embeds)
            await archive_channel.send(content=content.content, embeds=content.embeds, files=content.attachments)
            # if content.attachments:
            #     await self._send_content_to_target([attachment for attachment in content.attachments if attachment])

