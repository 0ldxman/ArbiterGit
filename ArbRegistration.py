import datetime
import pprint

from ArbDatabase import DataManager, DataModel, DataDict
from ArbFormer import Pattern, Extractor, Validator, Former
from ArbUIUX import ArbEmbed, ErrorEmbed, SuccessEmbed
from typing import Any, Optional
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from discord import SelectOption
import json


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
                reg_form = RegForm.write_form_id_database(self.form.to_dict())
                await RegForm(reg_form).send_notification(self.ctx)
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


class RegForm(DataModel):
    def __init__(self, form_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'REGISTRATION', f'form_id = {form_id}')
        self.form_id = form_id
        self.author = self.get('user_id', None)
        self.server = self.get('server_id', None)
        self.form_data = json.loads(self.get('data')) if self.get('data') else {}

        self.translation_dict = {
            'age': 'Возраст',
            'avatar': 'Картинка',
            'callsign': 'Позывной',
            'frac': 'Фракция',
            'name': 'Имя Фамилия',
            'org': 'Организация',
            'org_lvl': 'Ранг/Должность в организации',
            'race': 'Раса',
            'worldview': 'Мировоззрение'
        }

    @staticmethod
    def write_form_id_database(form: dict, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        form_id = db.maxValue('REGISTRATION', 'form_id') + 1
        form_json = json.dumps(form)

        server_id = form.pop('server')
        author_id = form.pop('owner')
        date = form.pop('update')

        query = {
            'form_id': form_id,
            'data': form_json,
            'user_id': author_id,
            'server_id': server_id,
            'date': date
        }

        db.insert('REGISTRATION', query)

        return form_id

    @staticmethod
    def get_form_by_id(form_id: int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        return RegForm(form_id, data_manager=db)

    @staticmethod
    def get_all_forms_by_server(server_id: int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        query = f'server_id = {server_id}'
        return [RegForm(form_id.get('form_id'), data_manager=db) for form_id in db.select_dict('REGISTRATION', filter=query)]

    def to_embed(self):
        embed = ArbEmbed(f'Анкета регистрации персонажа (ID: {self.form_id})')

        form = self.form_data
        print(form)
        # form.pop('owner')
        # form.pop('server')
        # form.pop('update')

        embed.set_footer(text=f'Дата отправления: {self.get("date")}')
        for field, value in form.items():
            if field not in ['owner', 'server', 'update']:
                embed.add_row(self.translation_dict.get(field), value)

        return embed

    async def send_accept_embed(self, ctx):
        author = ctx.bot.get_user(self.author)
        embed = SuccessEmbed('Анкета принята',
                             f'Ваша анкета персонажа **{self.form_data.get("name")}** была рассмотрена и принята')
        await author.send('', embed=embed)

    async def send_accept_respond(self, ctx):
        embed = SuccessEmbed('Анкета принята',
                             f'Анкета персонажа **{self.form_data.get("name")}** была принята')
        await ctx.respond('', embed=embed)

    async def send_deny_embed(self, ctx, reason:str=None):
        author = ctx.bot.get_user(self.author)
        embed = ErrorEmbed('Анкета отклонена',
                           f'Ваша анкета персонажа **{self.form_data.get("name")}** была рассмотрена администрацией и отклонена по причине:```\n{reason if reason else "Причина не указана администратором"}```')
        await author.send('', embed=embed)

    async def send_deny_respond(self, ctx, reason:str=None):
        embed = ErrorEmbed('Анкета отклонена',
                           f'Анкета персонажа **{self.form_data.get("name")}** была отклонена по причине:```\n{reason if reason else "Причина не указана администратором"}```')
        await ctx.respond('', embed=embed)

    async def send_notification(self, ctx):
        from ArbCore import Server
        server = Server(ctx.guild.id, data_manager=self.data_manager)
        notification_channel = ctx.guild.get_channel(server.registration_chat)
        if not notification_channel:
            notification_channel = ctx.guild.get_thread(server.registration_chat)

        embed = self.to_embed()
        embed.set_author(ctx.bot.get_guild(self.server).name)
        embed.set_description(f'> **Отправитель:** {ctx.author.mention}\n')
        embed.set_logo(ctx.bot.get_guild(self.server).icon)

        await notification_channel.send('## @everyone новая анкета регистрации была отправлена на рассмотрение!', embed=embed)

    # def update_form_data(self, form_data: dict):
    #     self.form_data.update(form_data)
    #     self.update_data('data', json.dumps(self.form_data))

    def delete_form(self):
        self.data_manager.delete('REGISTRATION', f'form_id = {self.form_id}')

    def accept(self, money: float = 30_000, lvl: int = 0, skill_points: int=0, skill_mods_points: float=0, exp:float=0):
        from ArbGenerator import CharacterTemplate
        from ArbCharacters import CharacterProgress
        from ArbRaces import Race
        from ArbOrgs import Organization

        total_text = f'''setName - {self.form_data.get('name')}
setOwner_id - {self.author}
setAge - {self.form_data.get("age")}
setRace - {self.form_data.get('race')}
setSex - {self.form_data.get('sex')}
setOrg - {self.form_data.get('org')}
setOrg_rank - {self.form_data.get('org_lvl')}
setUpdated - {datetime.datetime.now().strftime('%Y-%m-%d')}
setServer - {self.server}
setMoney - {money}
SetWorldview("{self.form_data.get('worldview')}")
SetStressPoints(0)
AddSkill("PST", 15, 1, 0.5)
AddItem.SpecialPistol()
AddItem.CombatKnife()
AddItem.Cap()
AddItem.TacticalGoggles()
AddItem.FieldUniform()
AddItem.BattleVest()
AddItem.TacticalGloves()
AddItem.Berets()'''
        if self.form_data.get('callsign'):
            total_text += f'\nsetCallsign - {self.form_data.get("callsign")}'
        if self.form_data.get('avatar'):
            total_text += f'\nsetAvatar - {self.form_data.get("avatar")}'

        print(total_text)
        template = CharacterTemplate.from_text(total_text, 0, data_manager=self.data_manager)
        print(template.to_text())
        character_id = template.insert_data()

        race = Race(self.form_data.get('race'), data_manager=self.data_manager)
        avg_age = (race.race_range_min + race.race_range_max)/2

        points_skills = int(175 * (1 + (self.form_data.get('age') - avg_age)/100)) + skill_points
        points_skill_mods = round((self.form_data.get('age') - avg_age)/50 + 0.5) + skill_mods_points
        if points_skill_mods < 0:
            points_skill_mods = 0

        CharacterProgress(character_id, data_manager=self.data_manager).update_progress_data(
            lvl=lvl,
            skills=points_skills,
            skills_mods=points_skill_mods,
            exp=int(exp)
        )
        Organization(self.form_data.get('org'), data_manager=self.data_manager).change_reputation(character_id, 15)
        Organization(self.form_data.get('org'), data_manager=self.data_manager).change_loyalty(character_id, 50)

