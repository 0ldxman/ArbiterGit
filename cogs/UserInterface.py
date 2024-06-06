from discord.ext import commands
from ArbCharacters import InterCharacter
from ArbDatabase import DataManager
from ArbHealth import LocalDisease, LocalInjury
from ArbUIUX import StandartEmbed
from ArbUtils.ArbDataParser import get_owners_character


class CharacterMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='character_health', description='Меню состояния персонажа')
    async def __character_health(self, ctx):
        db = DataManager()
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.autor.mention}, у вас нет персонажа')
            return

        injuries, diseases = InterCharacter(character).fetch_health_data()
        injury_text = ''
        disease_text = ''

        if injuries is not None:
            for i in injuries:
                c_inj = LocalInjury(i.get('inj_id'), i.get('id'), data_manager=db)
                injury_text += f'> {c_inj.InjuryID} {c_inj.Name} ({c_inj.Root}) \n'

        if diseases is not None:
            for i in diseases:
                c_dis = LocalDisease(i.get('dis_id'), i.get('id'), data_manager=db)
                disease_text += f'> {c_dis.DiseaseID} {c_dis.Name} ({c_dis.Root}) \n'

        embed = StandartEmbed(title=f'Состояние персонажа {character}')
        embed.add_field(name='Болезни', value=disease_text, inline=False)
        embed.add_field(name='Ранения', value=injury_text, inline=False)

        await ctx.send('',embed=embed)


def setup(bot):
    bot.add_cog(CharacterMenu(bot))