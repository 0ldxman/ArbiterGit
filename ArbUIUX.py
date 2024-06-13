from ArbDatabase import DataManager
import discord
from discord.ext import commands
from dataclasses import dataclass

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
        start_point = (153, 184, 152)
        end_point = (232, 74, 95)

        damage = damage/100 if damage else 0

        avg_point = (end_point[0]-start_point[0], end_point[1]-start_point[1], end_point[2]-start_point[2])

        total_code = (end_point[0]-round(avg_point[0]*damage), end_point[1]-round(avg_point[1]*damage), end_point[2]-round(avg_point[2]*damage))

        self.set_color(total_code)




# class Paginator(discord.ui.View):
#     def __init__(self, embeds, interaction):
#         super().__init__(timeout=None)
#         self.embeds = embeds
#         self.interaction = interaction
#         self.offset = 0
#
#         for emb in self.embeds:
#             emb.set_footer(text=f'Страница {self.embeds.index(emb) + 1}/{len(self.embeds)}')
#
#     async def update_button(self):
#         offset = self.offset
#         is_first_page = offset == 0
#         is_last_page = offset == len(self.embeds)-1
#
#         self.back.disabled = is_first_page
#         self.forward.disabled = is_last_page
#
#     async def interaction_check(self, interaction: discord.MessageInteraction):
#         if self.interaction.author.id != interaction.user.id:
#             return await interaction.response.send_message(f'{interaction.user.mention} Вы не можете это использовать', ephemeral=True)
#         return True
#
#     @discord.ui.button(label='<', style=discord.ButtonStyle.secondary)
#     async def back(self, _, interaction: discord.MessageInteraction):
#         self.offset -= 1
#         await self.update_button()
#         await interaction.response.edit_message(embed=self.embeds[self.offset], view=self)
#
#     @discord.ui.button(label='Закрыть', style=discord.ButtonStyle.danger)
#     async def close(self, _, interaction: discord.Interaction):
#         await interaction.response.defer()
#         await interaction.delete_original_response()
#
#     @discord.ui.button(label='>', style=discord.ButtonStyle.secondary)
#     async def forward(self, _, interaction: discord.MessageInteraction):
#         self.offset += 1
#         await self.update_button()
#         await interaction.response.edit_message(embed=self.embeds[self.offset], view=self)
#

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