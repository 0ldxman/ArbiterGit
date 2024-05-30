import discord
import json
from discord.ext import commands

file = open('../../Arbiter/config.json', 'r')
config = json.load(file)
bot = commands.Bot(command_prefix=commands.when_mentioned_or(config['prefix']), intents=discord.Intents.all())

API_KEY = "9b3291025787b55aacdadf5887baca95e28bf9bffe502c3dd0ca63cc42b7b51c"