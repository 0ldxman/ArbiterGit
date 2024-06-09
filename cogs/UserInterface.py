from discord.ext import commands
from ArbCharacters import InterCharacter
from ArbDatabase import DataManager
from ArbHealth import LocalDisease, LocalInjury, Body
from ArbUIUX import ArbEmbed, HealthEmbed
from ArbUtils.ArbDataParser import get_owners_character


class CharacterMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def character_health_embeds(self, character:int, data_manager:DataManager = None):
        db = DataManager() if not data_manager else data_manager

        body = Body(character, data_manager=db)

        vital_damage = body.vital_damage()

        embed_stats = HealthEmbed(f'Жизненные показатели', f'{body.phisical_stats_print()}', damage=vital_damage)

        embed_injuries = HealthEmbed(f'Ранения', f'{body.__str__() if body.__str__() else "*(Здесь будут отображаться ранения вашего персонажа)*"}', damage=vital_damage)

        return embed_stats, embed_injuries

    @commands.slash_command(name='character_body', description='Ранения персонажа')
    async def __character_body(self, ctx, character_id:int=None):
        if not character_id:
            user_id = ctx.author.id
            character = get_owners_character(user_id)
        else:
            character = character_id

        if character is None:
            await ctx.send(f'{ctx.autor.mention}, у вас нет персонажа')
            return

        embed_stats, embed_injuries = self.character_health_embeds(character)

        await ctx.send(f'', embed=embed_stats)

        await ctx.send(f'', embed=embed_injuries)


def setup(bot):
    bot.add_cog(CharacterMenu(bot))