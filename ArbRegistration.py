from ArbDatabase import DataManager, DataModel, DataDict
from ArbFormer import Pattern, Extractor, Validator, Former
from ArbUIUX import ArbEmbed, ErrorEmbed, SuccessEmbed
from typing import Any, Optional
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from discord import SelectOption


class Registrator:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())

        name = Pattern('Имя Фамилия', 'name')

        callsign = Pattern(['Позывной', 'Кличка'], 'callsign')

        race = Pattern(['Раса', 'Вид'], 'race')
        race.set_validator(Validator.create_db_validator('RACES_INIT', 'name'))
        race.set_extractor(Extractor.find_in_database('RACES_INIT', 'name', 'id'))

        sex = Pattern('Пол', 'sex')

        age = Pattern('Возраст', 'age')
        age.set_validator(Validator.is_numeric)
        age.set_extractor(Extractor.extract_number)

        worldview = Pattern('Мировоззрение', 'worldview')
        worldview.set_validator(Validator.create_db_validator('WORLDVIEW', 'label'))
        worldview.set_extractor(Extractor.find_in_database('WORLDVIEW', 'label', 'id'))

        org = Pattern('Организация', 'org')
        org.set_validator(Validator.create_db_validator('ORG_INIT', 'label'))
        org.set_extractor(Extractor.find_in_database('ORG_INIT', 'label', 'id'))

        org_lvl = Pattern(['Звание', 'Должность'], 'org_lvl')
        org_lvl.set_validator(Validator.create_db_validator('ORG_RANKS', 'label'))
        org_lvl.set_extractor(Extractor.find_in_database('ORG_RANKS', 'label', 'id'))

        faction = Pattern(['Фракция', 'Подорганизация', 'Подразделение', 'Объединение', 'Гражданство'], 'frac')

        avatar = Pattern(['Картинка', 'Внешность', 'Аватарка', 'Аватар'], 'avatar')

        self.form = Former()
        self.form.add_pattern(name)
        self.form.add_pattern(callsign)
        self.form.add_pattern(race)
        self.form.add_pattern(sex)
        self.form.add_pattern(age)
        self.form.add_pattern(worldview)
        self.form.add_pattern(org)
        self.form.add_pattern(org_lvl)
        self.form.add_pattern(faction)
        self.form.add_pattern(avatar)

    def extend_data(self, key:str, value: Any):
        self.form.data[key] = value

    def parse_text(self, text):
        self.form.parse_text(text)

    def to_dict(self):
        return self.form.to_dict()

    def save_to_db(self, table, data_dict):
        self.data_manager.insert_dict(table, data_dict)


class CharacterRegistration(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.is_ended = False
        self.form = Registrator()

        self.embed = self.create_main_embed()
        self.message = None
        self.tip_message = None

    def create_main_embed(self):
        embed = ArbEmbed('Форма регистрации персонажа')
        for pattern in self.form.form.patterns:
            value = self.form.form.data.get(pattern.field_name, [])
            value = '||*Не заполнено*||' if not value else value[1]
            value = '||*Не заполнено*||' if value[1] is None else value

            embed.add_row(name=pattern.tags[0], value=value)
        return embed

    async def send_tip_message(self):
        tip_embed = SuccessEmbed('Подсказка', f'Для заполнения пунктов укажите их название в формате:\n> *[Название пункта]: **Значение***'
                                              f'\n\n### **Пример:**\n-# > Имя Фамилия: Джон Сноу\n-# > Раса: Человек\n-# > Пол: Мужской'
                                              f'\n\n-# Для завершения заполнения анкеты введите сообщение: **"Закончить"**')

        message = await self.ctx.send('', embed = tip_embed)
        self.tip_message = message

    async def send_success_message(self):
        success_embed = SuccessEmbed('Регистрация завершена', '*Ваша анкета была сохранена и отправлена на рассмотрение администрации сервера!*\n\n-# *Анкета будет рассмотрена в скором времени, если у вас остались какие-то вопросы или пожелания свяжитесь с администрацией!*')
        await self.ctx.send('', embed=success_embed)

    async def start(self):
        self.message = await self.ctx.respond('', embed=self.embed)
        return await self.wait_for_message()

    async def wait_for_message(self):
        while not self.is_ended:
            await self.send_tip_message()
            final_message = await self.handle_message()
            await self.tip_message.delete()
            if not final_message:
                await self.message.delete_original_response()
                await self.send_success_message()
                return self.form.to_dict()

    async def handle_message(self):
        def check(msg):
            return msg.author == self.ctx.author and msg.channel == self.ctx.channel

        message = await self.ctx.bot.wait_for('message', timeout=None, check=check)

        content = message.content

        if content.lower() == 'закончить':
            self.is_ended = True
            return False

        self.form.parse_text(content)

        self.embed = self.create_main_embed()

        await self.message.edit(embed=self.embed)
        await message.delete()
        return True

    def insert_registration_data(self):
        # TODO: Сделать после завершения регистрации добавление в базу данных и отправку эмбеда с информацией админам

        # TODO: Сделать класс сервера и класс игрока (один для настройки параметров бота администрацией, второй для управления игроком и его персонажами

        # TODO: Сделать таблицу для параметров регистрации

        pass