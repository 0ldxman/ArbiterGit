import asyncio
import pprint

from ArbDatabase import DataManager
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from discord import SelectOption
from dataclasses import dataclass
import inspect
from typing import Callable, get_type_hints


discord.Color.brand_green()

@dataclass()
class EmbedRow:
    title: str | None
    value: str | None
    inline: bool | None


class ArbEmbed:
    def __init__(self, title:str=None, desc:str=None, **kwargs):
        self.title = title if title else ''
        self.desc = desc if desc else ''

        self.rgb = kwargs.get('rgb_code') if 'rgb_code' in kwargs else (43, 45, 49)
        self.logo = kwargs.get('logo_url') if 'logo_url' in kwargs else None
        self.picture = kwargs.get('picture') if 'picture' in kwargs else None
        self.footer = kwargs.get('footer') if 'footer' in kwargs else None
        self.footer_logo = kwargs.get('footer_logo') if 'footer_logo' in kwargs else None

        self.embed = discord.Embed(title=self.title,
                                   colour=discord.Color.from_rgb(*self.rgb),
                                   description=self.desc)

        if self.picture:
            self.embed.set_image(url=self.picture)

        if self.logo:
            self.embed.set_thumbnail(url=self.logo)

        if self.footer or self.footer_logo:
            self.embed.set_footer(text=self.footer, icon_url=self.footer_logo)


        self.rows: list[EmbedRow] = kwargs.get('rows') if 'rows' in kwargs else []

        for row in self.rows:
            self.embed.add_field(name=row.title if row.title is not None else '‎',
                                 value=row.value if row.value is not None else '',
                                 inline= row.inline if row.inline is not None else False)

    def add_row(self, name:str, value:str, inline:bool=False):
        self.embed.add_field(name=name, value=value, inline=inline)

    def set_logo(self, avatar_url:str):
        self.embed.set_thumbnail(url=avatar_url)

    def set_footer(self, text:str=None, url_str:str=None):
        self.embed.set_footer(text=text or '', icon_url=url_str)

    def set_title(self, title:str):
        self.title = title
        self.embed.title = title

    def set_description(self, desc:str):
        self.desc = desc
        self.embed.description = desc

    def set_color(self, rgb_code: tuple):
        self.rgb = rgb_code
        self.embed = discord.Embed(title=self.title,
                                   color=discord.Color.from_rgb(*self.rgb),
                                   description=self.desc)

        for row in self.rows:
            self.embed.add_field(name=row.title if row.title is not None else '',
                                 value=row.value if row.value is not None else '',
                                 inline=row.inline if row.inline is not None else False)

        if self.picture:
            self.embed.set_image(url=self.picture)

        if self.logo:
            self.embed.set_thumbnail(url=self.logo)

        if self.footer:
            self.embed.set_footer(text=self.footer, icon_url=self.footer_logo)

    def set_author(self, author_name:str = None, url:str = None, icon_url:str = None):
        self.embed.set_author(name=author_name, url=url, icon_url=icon_url)

    def get_embed(self):
        return self.embed

    def to_dict(self):
        return self.embed.to_dict()


class SuccessEmbed(ArbEmbed):
    def __init__(self, title: str=None, desc:str=None, **kwargs):
        super().__init__(title, desc, **kwargs)
        success_color = (87, 242, 135)
        self.set_color(success_color)


class ErrorEmbed(ArbEmbed):
    def __init__(self, title: str=None, desc:str=None, **kwargs):
        super().__init__(title, desc, **kwargs)
        error_color = (237, 66, 69)
        self.set_color(error_color)


class HealthEmbed(ArbEmbed):
    def __init__(self, title: str=None, desc:str=None, damage:int=None, **kwargs):
        super().__init__(title, desc, **kwargs)
        start_point = (87, 242, 135)
        end_point = (237, 66, 69)

        damage = damage/100 if damage else 0

        avg_point = (end_point[0]-start_point[0], end_point[1]-start_point[1], end_point[2]-start_point[2])

        total_code = (end_point[0]-round(avg_point[0]*damage), end_point[1]-round(avg_point[1]*damage), end_point[2]-round(avg_point[2]*damage))

        self.set_color(total_code)


class Paginator(discord.ui.View):
    def __init__(self, embeds, interaction, page_names=None, ignore_footer:bool=False):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.interaction = interaction
        self.offset = 0
        self.page_names = page_names if page_names else {}
        self.default_button_names = ['<', '>']


        if ignore_footer:
            for emb in self.embeds:
                emb.set_footer(text=self.get_footer_text(self.embeds.index(emb) + 1))

    def get_footer_text(self, page_number):
        if page_number in self.page_names:
            return f'{self.page_names[page_number]} {page_number}/{len(self.embeds)}'
        return f'Страница {page_number}/{len(self.embeds)}'

    async def update_button(self):
        offset = self.offset
        is_first_page = offset == 0
        is_last_page = offset == len(self.embeds)-1

        self.back.disabled = is_first_page
        self.forward.disabled = is_last_page

        self.back.label = self.page_names.get(offset, self.default_button_names[0]) if not is_first_page else self.default_button_names[0]
        self.forward.label = self.page_names.get(offset+2, self.default_button_names[1]) if not is_last_page else self.default_button_names[1]

    async def interaction_check(self, interaction: discord.MessageInteraction):
        if self.interaction.author.id != interaction.user.id:
            return await interaction.response.send_message(f'{interaction.user.mention} Вы не можете это использовать', ephemeral=True)
        return True

    async def go_to_page(self, offset: int):
        self.offset = offset
        await self.update_button()
        await self.interaction.response.edit_message(embed=self.embeds[self.offset], view=self)

    @discord.ui.button(label='<', style=discord.ButtonStyle.secondary)
    async def back(self, _, interaction: discord.MessageInteraction):
        self.offset -= 1
        await self.update_button()
        await interaction.response.edit_message(embed=self.embeds[self.offset], view=self)

    @discord.ui.button(label='Закрыть', style=discord.ButtonStyle.danger)
    async def close(self, _, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()

    @discord.ui.button(label='>', style=discord.ButtonStyle.secondary)
    async def forward(self, _, interaction: discord.MessageInteraction):
        self.offset += 1
        await self.update_button()
        await interaction.response.edit_message(embed=self.embeds[self.offset], view=self)


@dataclass()
class FormStep:
    name: str
    description: str
    type: str
    label: str
    required: bool = False


class InteractiveForm(View):
    def __init__(self, ctx, steps: list[FormStep], title: str = None, description: str = None, end_description: str = None):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.steps = steps
        self.current_step = 0
        self.user_inputs = {}

        self.title = title if title else "Интерактивная Форма"
        self.description = description if description else "Заполните форму ниже."
        self.end_description = end_description if end_description else 'Спасибо за заполнение формы!'
        self.main_embed = self.create_main_embed()
        self.main_message = None
        self.question_embed = self.create_question_embed()
        self.question_message = None

        self.is_ended = False

    def create_main_embed(self) -> discord.Embed:
        """Создает эмбед с основными данными."""
        embed = discord.Embed(title=self.title, description=self.description)
        for question in self.steps:
            key = question.name
            value = self.user_inputs.get(key, "???")
            embed.add_field(name=question.label, value=value, inline=False)
        return embed

    async def send_temporary_embed(self, title: str, description: str):
        """Отправляет временный эмбед, который удаляется через 10 секунд."""
        embed = discord.Embed(title=title, description=description)
        await self.ctx.send(embed=embed, delete_after=10)

    async def send_end_embed(self):
        """Отправляет завершающий эмбед и удаляет вопрос."""
        embed = discord.Embed(title=f'{self.title} завершена!', description=self.end_description)
        await self.ctx.send(embed=embed, delete_after=10)
        await self.question_message.delete()

    def create_question_embed(self) -> discord.Embed:
        """Создает эмбед с текущим вопросом."""
        step = self.steps[self.current_step]
        embed = discord.Embed(title=f"{step.label}{'<:required:1265820311069134939>' if step.required else ''}", description=step.description)
        return embed

    async def handle_message(self):
        def check(msg):
            return msg.author == self.ctx.author and msg.channel == self.ctx.channel

        while not self.is_ended:
            message = await self.ctx.bot.wait_for('message', timeout=None, check=check)
            if self.is_ended:
                return False

            step = self.steps[self.current_step]
            key = step.name
            value_type = step.type

            if value_type == 'text':
                self.user_inputs[key] = message.content
                break
            elif value_type == 'int':
                try:
                    self.user_inputs[key] = int(message.content)
                    break
                except ValueError:
                    await self.send_temporary_embed('Неверное значение', f'{self.ctx.author.mention}, введите целое число!')
            elif value_type == 'float':
                try:
                    self.user_inputs[key] = float(message.content)
                    break
                except ValueError:
                    await self.send_temporary_embed('Неверное значение', f'{self.ctx.author.mention}, введите целое или десятичное число с использованием точки!')

        if self.is_ended:
            return False

        self.main_embed = self.create_main_embed()
        await self.main_message.edit(embed=self.main_embed)
        await message.delete()
        return True

    async def start(self):
        """Начинает процесс заполнения формы."""
        self.main_message = await self.ctx.respond(embed=self.main_embed)
        self.question_message = await self.ctx.send(embed=self.question_embed, view=self)
        return await self.wait_for_message()

    async def wait_for_message(self):
        """Ждет и обрабатывает сообщения пользователя."""
        while not self.is_ended:
            await self.update_button()
            message_complete = await self.handle_message()
            if message_complete:
                self.current_step += 1

            if self.current_step < len(self.steps):
                self.question_embed = self.create_question_embed()
                await self.question_message.edit(embed=self.question_embed, view=self)
            else:
                self.is_ended = True
                await self.main_message.delete_original_response()
                await self.send_end_embed()
                return self.user_inputs

        return self.user_inputs

    @discord.ui.button(label='Назад', style=discord.ButtonStyle.secondary, custom_id='back')
    async def back(self, button: Button, interaction: discord.Interaction):
        if self.current_step > 0:
            self.current_step -= 1
            await self.update_button()
            self.question_embed = self.create_question_embed()
            await self.question_message.edit(embed=self.question_embed, view=self)
        await interaction.response.defer()

    @discord.ui.button(label='Отменить', style=discord.ButtonStyle.danger, custom_id='cancel')
    async def close(self, button: Button, interaction: discord.Interaction):
        self.is_ended = True
        await self.send_temporary_embed('Отмена', f'{self.ctx.author.mention} вы прервали заполнение формы.\n-# Чтобы продолжить заполнение введите команду заново')
        await self.main_message.delete_original_response()
        await self.question_message.delete()
        await interaction.response.defer()

    @discord.ui.button(label='Пропустить', style=discord.ButtonStyle.secondary, custom_id='forward')
    async def forward(self, button: Button, interaction: discord.Interaction):
        self.current_step += 1
        await self.update_button()
        if self.current_step < len(self.steps):
            self.question_embed = self.create_question_embed()
            await self.question_message.edit(embed=self.question_embed, view=self)
        else:
            self.is_ended = True
            await self.send_end_embed()
        await interaction.response.defer()

    async def update_button(self):
        """Обновляет состояние кнопок."""
        is_first_page = self.current_step == 0

        self.back.disabled = is_first_page

        step = self.steps[self.current_step]
        is_required = step.required and not self.user_inputs.get(step.name, False)
        print(is_required, step.label)

        self.forward.disabled = is_required

        if self.question_message:
            await self.question_message.edit(view=self)


class CustomSelectMenu(View):
    def __init__(self, ctx, options, callback, placeholder="Выберите опцию", min_values=1, max_values=1):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.callback = callback
        self.add_item(Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=[SelectOption(label=opt['label'], value=opt['value']) for opt in options]
        ))

    @discord.ui.select()
    async def select_callback(self, select, interaction: discord.Interaction):
        await self.callback(select.values, interaction)


@dataclass()
class Selection:
    label: str
    value: str
    callback: Callable
    description: str


class SelectingForm(discord.ui.Select):
    def __init__(self, ctx, options: list[Selection], label: str = None, min_values: int = None,
                 max_values: int = None):
        self.ctx = ctx
        self.label = label if label is not None else "Выберите опцию"
        self.inputed_options: list[Selection] = options
        self.callbacks = self.potential_callbacks()
        self.current_selection = None

        super().__init__(
            placeholder=self.label,
            min_values=min_values if min_values else 1,
            max_values=max_values if max_values else 1,
            options=self.processed_options(),
        )


    async def send_arguments_embed(self, arguments:dict, label:str=None):
        text = f''
        for arg in arguments:
            value_type = arguments[arg].get('value_tupe')
            default_value = arguments[arg].get('default')
            text += f'\n{arg}: {value_type}={default_value}'

        text += f'\n-# Для ввода параметров отправьте сообщение в формате: [аргумент 1], [аргумент 2]...'

        embed = ArbEmbed(title=label if label else 'Необходмые параметры',
                         desc=text)

        await self.ctx.respond(embed=embed, ephemeral=True)

    async def callback(self, interaction):
        def check(msg):
            return msg.author == self.ctx.author and msg.channel == self.ctx.channel

        value = self.values[0]
        callback = self.callbacks.get(value)
        arguments = self.get_callable_args(callback)

        pprint.pprint(self.get_callable_args(callback))

        await self.send_arguments_embed(arguments, value)
        is_ended = False
        while not is_ended:
            message = await self.ctx.bot.wait_for('message', timeout=None, check=check)
            content = message.content
            args = content.split(',')
            args_dict = {}
            for idx, arg in enumerate(arguments):
                args_dict[arg] = args[idx]


    def potential_callbacks(self):
        options = self.inputed_options
        total_callbacks = {}
        for option in options:
            total_callbacks[option.value] = option.callback
        return total_callbacks

    def processed_options(self):
        options = self.inputed_options
        processed_options = []
        for option in options:
            proc_option = SelectOption(label=option.label, value=option.value, description=option.description)
            processed_options.append(proc_option)
        return processed_options

    def get_callable_args(self, func):
        # Проверка типа callback для корректной обработки
        if not callable(func):
            return {}

        # Получение сигнатуры функции
        signature = inspect.signature(func)
        parameters = signature.parameters
        arg_info = {}

        for param_name, param in parameters.items():
            if param_name == 'self':
                continue  # Игнорируем 'self'
            arg_info[param_name] = {
                "value_type": param.annotation if param.annotation is not param.empty else None,
                "default": param.default if param.default is not param.empty else None
            }

        return arg_info

    async def start(self):
        """Начинает процесс заполнения формы."""
        view = discord.ui.View()
        view.add_item(self)
        await self.ctx.respond(view=view)


class InviteView(View):
    def __init__(self, interaction, *, accept_embed=None, accept_label=None, deny_embed=None, deny_label=None, acceptor=None):
        super().__init__(timeout=None)

        self.interaction = interaction

        self.accept_embed = accept_embed if accept_embed else None
        self.accept_label = accept_label if accept_label else 'Принять'

        self.deny_embed = deny_embed if deny_embed else None
        self.deny_label = deny_label if deny_label else 'Отклонить'

        self.acceptor = acceptor if acceptor else self.interaction.user

    @discord.ui.button(label='Принять', style=discord.ButtonStyle.success, custom_id='Accept')
    async def accept(self, _, interaction: discord.Interaction):
        await self.respond_accept()
        await interaction.response.defer()
        await interaction.delete_original_response()

    @discord.ui.button(label='Отклонить', style=discord.ButtonStyle.danger, custom_id='Deny')
    async def deny(self, _, interaction: discord.Interaction):
        await self.respond_deny()
        await interaction.response.defer()
        await interaction.delete_original_response()

    async def update_button(self):
        self.accept.label = self.accept_label
        self.deny.label = self.deny_label

    async def respond_accept(self):
        if self.accept_embed:
            embed = self.accept_embed
        else:
            embed = SuccessEmbed('Предложение принято',
                             '-# Вы приняли предложение!')

        await self.acceptor.send(embed=embed)

    async def respond_deny(self):
        if self.deny_embed:
            embed = self.deny_embed
        else:
            embed = ErrorEmbed('Предложение отвержено',
                           '-# Вы отклонили предложение')

        await self.acceptor.send(embed=embed)


class Vote:
    def __init__(self, question:str, options:list[str], allowed_users:list[int], duration:int=5):
        self.question = question
        self.options = options
        self.allowed_users = allowed_users  # Список разрешённых пользователей для голосования
        self.votes = {option: 0 for option in options}  # Счётчики голосов для каждого варианта
        self.voted_users = set()  # Множество пользователей, которые уже проголосовали
        self.duration = duration*60  # Длительность голосования в секундах
        self.finished = False  # Статус голосования (закончено или нет)
        self.result = None

    def add_vote(self, user: discord.Interaction.user, option):
        if user.id in self.allowed_users and user.id not in self.voted_users:
            self.votes[option] += 1
            self.voted_users.add(user.id)
            return True
        return False

    def get_winner(self):
        if self.finished:
            return max(self.votes, key=self.votes.get)
        return None

    async def start(self, ctx):
        """Начинает голосование."""
        players_mentions = []
        for player in self.allowed_users:
            players_mentions.append(f'{ctx.bot.get_user(player).mention}')

        content = ', '.join(players_mentions)

        embed = ArbEmbed(title=self.question, desc=f'-# Голосование продлится: {int(self.duration / 60)} мин.\n' + '\n'.join(f'{idx+1}. {option}' for idx, option in enumerate(self.options)))
        view = VoteView(self)
        await ctx.respond(content,embed=embed, view=view)
        await asyncio.sleep(self.duration)  # Задержка до конца голосования
        self.finished = True
        self.result = self.get_winner()
        print('КОНЕЦ:', self.result, self.question, self.voted_users)
        return self.result

class VoteButton(Button):
    def __init__(self, label:str, vote:Vote, option:str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.vote = vote  # Ссылка на объект голосования
        self.option = option  # Вариант, который привязан к кнопке

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if self.vote.add_vote(user, self.option):
            print(self.vote.votes)
            await interaction.response.send_message(f"-# Ваш голос за **{self.option}** был учтён!", ephemeral=True)
        else:
            await interaction.response.send_message("-# Вы не можете голосовать или уже проголосовали.", ephemeral=True)

class VoteView(View):
    def __init__(self, vote: Vote):
        super().__init__(timeout=vote.duration)  # Тайм-аут совпадает с длительностью голосования
        self.vote = vote
        for option in vote.options:
            self.add_item(VoteButton(option, vote, option))

        self.result = None

    async def send_winner_embed(self, winner:str):
        embed = SuccessEmbed(f'Голосование завершено!',
                             f'В голосовании **"{self.vote.question}"** победил вариант: **{winner}**')
        await self.message.edit(content=None, embed=embed, view=None)  # Отправляем эмбед с результатами голосования

    async def send_canceled_embed(self):
        embed = ErrorEmbed('Голосование отменено',
                             f'-# Голосование **"{self.vote.question}"** было прервано. Победитель не определён')
        await self.message.edit(content=None, embed=embed, view=None)  # Отправляем эмбед с результатами голосования

    async def on_timeout(self):
        self.vote.finished = True  # Отмечаем, что голосование завершено
        winner = self.vote.get_winner()
        if winner:
            await self.send_winner_embed(winner)
        else:
            await self.send_canceled_embed()
