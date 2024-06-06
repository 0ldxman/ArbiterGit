import discord
from discord.ext import commands
import json
import os

from ArbDatabase import DataManager

file = open('config.json', 'r')
config = json.load(file)
bot = commands.Bot(command_prefix=commands.when_mentioned_or(config['prefix']), intents=discord.Intents.all())
API_KEY = 'MTE4MDQ1NDcwMjAxODcyMzg3MA.GI9Vf2.0f68g4twG0a6azO7Zxu-e8EG6vKwkxVtI14zPo'


@bot.event
async def on_ready():
	print("-- Arbiter ready")

@bot.slash_command(name='test_slash_command', description='Описание команды')
async def test(ctx):
     await ctx.respond('Успешный тест!')


db = DataManager()
db.update('META_INFO',{'playing_as': 0}, filter=f'id = 453133967902900225')

# @bot.slash_command(name='option_test')
# async def __test(
#         ctx,
#         number: Option(int, description='Число в диапазоне от 1 до 10', required=True, min_value=1, max_value=10),
#         member: Option(discord.Member, description='Любой участник сервера', required=True),
#         choice: Option(str, description='Выберите пункт из списка', required=True,
#                        choices=['Банан', 'Яблоко', 'Апельсин']),
#         text: Option(str, description='Текст из нескольких слов', required=False, default=''),
#         boolean: Option(bool, description='True или False', required=False, default=False)
# ):
#     await ctx.delete()
#
#     for argument in (number, boolean, member, text, choice):
#         print(f'{argument} ({type(argument).__name__})\n')

for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')



bot.run(API_KEY)