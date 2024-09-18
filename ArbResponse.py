import dataclasses

import discord.ext.commands

from ArbDatabase import DataManager, DataModel, DataDict
from ArbUIUX import ArbEmbed, SuccessEmbed, ErrorEmbed, Paginator
from dataclasses import dataclass


class Response:
    def __init__(self, success: bool = False, message: str = None, title: str = None, **kwargs):
        self.success = success
        self.message = message if message is not None else 'Нет описания'
        self.title = title if title is not None else 'Ответ'
        self.footer = kwargs.get('footer') if kwargs.get('footer') else None
        self.footer_logo = kwargs.get('footer_logo') if kwargs.get('footer_logo') else None

    def get_embed(self) -> SuccessEmbed | ErrorEmbed:
        if self.success:
            return SuccessEmbed(title=self.title, desc=self.message, footer=self.footer, footer_logo=self.footer_logo)
        else:
            return ErrorEmbed(title=self.title, desc=self.message, footer=self.footer, footer_logo=self.footer_logo)

    def to_dict(self):
        return self.get_embed().to_dict()

    def __str__(self):
        return f'# {self.title}\n{self.message}'

    def __repr__(self):
        return f'Response(success={self.success}, message="{self.message}")'


class ResponsePool:
    def __init__(self, responses: list[Response] | Response):
        if isinstance(responses, list):
            self.responses = responses
        elif isinstance(responses, Response):
            self.responses = [responses]

    def get_embeds(self) -> list[ErrorEmbed | SuccessEmbed]:
        return [response.get_embed() for response in self.responses if response is not None]

    def __str__(self):
        return '\n'.join([str(response) for response in self.responses if response is not None])


@dataclass()
class RespondForm:
    title: str
    content: str


class RespondIcon:
    def __init__(self):
        self.success_icon = ':white_check_mark:'
        self.danger_icon = ':warning:'
        self.failure_icon = ':x:'
        self.info_icon = ':bell:'

    @classmethod
    def default(cls):
        return RespondIcon().info_icon

    @classmethod
    def info(cls):
        return RespondIcon().info_icon

    @classmethod
    def success(cls):
        return RespondIcon().success_icon

    @classmethod
    def failure(cls):
        return RespondIcon().failure_icon

    @classmethod
    def danger(cls):
        return RespondIcon().danger_icon


class RespondLog:
    def __init__(self, data_manager: DataManager = None, **kwargs):
        self.data_manager = data_manager if data_manager is not None else DataManager()
        self.footer = kwargs.get('footer', None)
        self.footer_logo = kwargs.get('footer_logo', None)
        self.responds: list[RespondForm] = []

    def add_respond(self, title:str, content:str, *, respond_icon: str = None):
        form = RespondForm(f'{title}{f" {respond_icon}" if respond_icon else ""}', content)
        self.responds.append(form)

    def response_to_respond(self, response: Response, custom_title:str=None, custom_icon:str=None):
        self.add_respond(response.title if not custom_title else custom_title, response.message, respond_icon=RespondIcon.success() if response.success else RespondIcon.failure() if not custom_icon else custom_icon)

    def response_pool_to_respond(self, response_pool: ResponsePool):
        for response in response_pool.responses:
            self.response_to_respond(response)

    def embed_responds(self):
        from ArbUtils.ArbDataParser import ListChunker
        chunker = ListChunker(5, self.responds)
        embeds = []
        for chunk in chunker:
            chunk_text = ''
            for respond in chunk:
                chunk_text += f'### {respond.title}\n> {respond.content}\n\n'

            embed = ArbEmbed(f'Последствия действий', chunk_text, footer=self.footer, footer_logo=self.footer_logo)
            embeds.append(embed)

        return embeds

    async def view_responds(self, ctx):
        embeds = self.embed_responds()
        view = Paginator(embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)


class Notification(DataModel):
    def __init__(self, note_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager()) if kwargs.get('data_manager') else DataManager()
        self.note_id = note_id
        DataModel.__init__(self, 'NOTIFICATIONS', f'note_id = {self.note_id}', data_manager=self.data_manager)

        self.title = self.get('title', 'Уведомление') if self.get('title') else 'Уведомление'
        self.content = self.get('content', 'Нет описания') if self.get('content') else 'Нет описания'
        self.type = self.get('type', 'info') if self.get('type') else 'info'
        self.character_id = self.get('character_id', None)

    def get_users_id(self):
        users = self.data_manager.select_dict('PLAYERS', filter=f'character_id = {self.character_id}')
        if not users:
            return []
        else:
            return [user.get('id') for user in users]

    def get_character(self):
        from ArbCharacters import Character

        if self.character_id:
            return Character(self.character_id, data_manager=self.data_manager)
        else:
            return None

    def character_name(self):
        return self.get_character().name if self.get_character() else 'Неизвестный персонаж'

    def character_picture(self):
        return self.get_character().picture if self.get_character() else None

    async def get_users(self, ctx):
        users_id = self.get_users_id()
        users = [ctx.bot.get_user(user_id) for user_id in users_id]
        return users

    def create_embed(self):
        if self.type == 'success':
            return SuccessEmbed(title=f'{self.title} {RespondIcon.success()}', desc=self.content, footer=self.character_name(), footer_logo=self.character_picture())
        elif self.type == 'failure':
            return ErrorEmbed(title=f'{self.title} {RespondIcon.failure()}', desc=self.content, footer=self.character_name(), footer_logo=self.character_picture())
        elif self.type == 'danger':
            return ErrorEmbed(title=f'{self.title} {RespondIcon.danger()}', desc=self.content, footer=self.character_name(), footer_logo=self.character_picture())
        else:
            return ArbEmbed(title=f'{self.title} {RespondIcon.info()}', desc=self.content, footer=self.character_name(), footer_logo=self.character_picture())

    async def send_notification(self, ctx):
        users = await self.get_users(ctx)
        if not users:
            return

        embed = self.create_embed()
        for user in users:
            await user.send(embed=embed)

        self.delete_record()

    def __str__(self):
        return f'Notification(note_id={self.note_id}, title="{self.title}", content="{self.content}", type="{self.type}", character_id={self.character_id})'

    @staticmethod
    def create_notification(title:str, content:str, character_id:int=None, type:str='info'):
        db = DataManager()
        owner_data = db.select_dict('CHARS_INIT', filter=f'id = {character_id}')
        if not owner_data:
            owner_data = db.select_dict('PLAYERS', filter=f'character_id = {character_id}')
            if not owner_data:
                return

        note_id = db.maxValue('NOTIFICATIONS', 'note_id') + 1 if db.select_dict('NOTIFICATIONS') else 0
        query = {'note_id':note_id, 'content':content, 'character_id': character_id, 'title': title, 'type': type}

        db.insert('NOTIFICATIONS', query)

    @staticmethod
    def delete_notification(note_id:int):
        db = DataManager()
        db.delete('NOTIFICATIONS', f'note_id = {note_id}')

    @staticmethod
    def get_all_notifications():
        db = DataManager()
        return [Notification(note_id.get('note_id'), data_manager=db) for note_id in db.select_dict('NOTIFICATIONS')]

    @staticmethod
    async def send_all_notifications(ctx):
        notifications = Notification.get_all_notifications()
        for notification in notifications:
            await notification.send_notification(ctx)

    @staticmethod
    def from_respond_log(respond_log: RespondLog):
        for response in respond_log.responds:
            Notification.create_notification(response.title, response.content, None, type='info')


