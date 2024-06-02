from ArbDatabase import DataManager
import discord
from discord.ext import commands

class StandartEmbed():
    def __init__(self, title:str=None, desc:str=None, values:list=None, rgb_code:tuple=None, picture_url:str=None, avatar_url:str=None, footer:str=None):
        self.title = ''
        self.desc = ''
        self.values = []
        self.rgb = (43, 45, 49)

        if title:
            self.title = title
        if desc:
            self.desc = desc
        if rgb_code:
            self.rgb = rgb_code

        self.embed = discord.Embed(title=f'{self.title}',
                            color=discord.Color.from_rgb(self.rgb[0], self.rgb[1], self.rgb[2]),
                            description=f'{self.desc}')
        if values:
            for c_value in values:
                self.embed.add_field(name=c_value[0],
                                     value=c_value[1],
                                     inline=c_value[2])

        if picture_url:
            self.embed.set_image(url=picture_url)

        if avatar_url:
            self.embed.set_thumbnail(url=avatar_url)

        if footer:
            self.embed.set_footer(text=footer)

    def AddField(self, name:str, value:str, inline:bool=False):
        self.embed.add_field(name=name, value=value, inline=inline)

    def SetAvatar(self, avatar_url:str):
        self.embed.set_thumbnail(url=avatar_url)

    def set_footer(self, text:str=None, url_str:str=None):

        if not text:
            text = ''

        self.embed.set_footer(text=text,icon_url=url_str)

    async def PinEmbed(self):
        return self.embed


def chunks(c_list, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(c_list), n):
        yield c_list[i:i + n]

class Paginator(discord.ui.View):
    def __init__(self, embeds, interaction):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.interaction = interaction
        self.offset = 0

        for emb in self.embeds:
            emb.set_footer(text=f'Страница {self.embeds.index(emb) + 1}/{len(self.embeds)}')

    async def update_button(self):
        offset = self.offset
        is_first_page = offset == 0
        is_last_page = offset == len(self.embeds)-1

        self.back.disabled = is_first_page
        self.forward.disabled = is_last_page

    async def interaction_check(self, interaction: discord.MessageInteraction):
        if self.interaction.author.id != interaction.user.id:
            return await interaction.response.send_message(f'{interaction.user.mention} Вы не можете это использовать', ephemeral=True)
        return True

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