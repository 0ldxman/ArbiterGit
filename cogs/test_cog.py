from discord.ext import commands

class test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def test(self, ctx):
        await ctx.send('Cogs test success')

def setup(bot):
    bot.add_cog(test(bot))