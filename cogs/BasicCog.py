from ArbDatabase import DataManager, DataModel, DataDict
import discord
from discord.ext import commands
from ArbUtils.ArbDataParser import get_owners_character
from ArbUIUX import ArbEmbed, SuccessEmbed, ErrorEmbed
from functools import wraps


class BasicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f'...Module {self.__class__.__name__} is ready')

    def has_permissions(self, ctx, *perms):
        permissions = ctx.author.guild_permissions
        return all(getattr(permissions, perm, False) for perm in perms)

    def is_admin(self, ctx):
        return self.has_permissions(ctx, 'administrator')

    def can_manage_roles(self, ctx):
        return self.has_permissions(ctx, 'manage_roles')

    def is_admin_or_moderator(self, ctx):
        return self.has_permissions(ctx, 'administrator', 'manage_guild', 'ban_members')

    def get_player_current_character(self, ctx):
        player_id = ctx.author.id
        info = DataDict('PLAYERS', f'id = {player_id}').get('character_id', None)
        return info

    def in_battle_check(self, character_id:int):
        db = DataDict('BATTLE_CHARACTERS', f'character_id = {character_id}').get('battle_id', None)
        return db

    def is_coordinator(self, character_id:int):
        db = DataDict('BATTLE_TEAMS', f'coordinator = {character_id}').get('team_id', None)
        return db

    async def respond_if_not_admin(self, ctx):
        respond = ErrorEmbed('Недостаточно прав', f'-# *{ctx.author.mention} у Вас недостаточно прав для использования данного функционала!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_no_characters(self, ctx):
        respond = ErrorEmbed('Персонаж не обнаружен', f'-# *{ctx.author.mention} в базе данных не было найдено информации о том, что вы управляете персонажем!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_not_in_battle(self, ctx):
        respond = ErrorEmbed('Персонаж не находится в бою', f'-# *{ctx.author.mention} ваш персонаж не находится в бою!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_not_coordinator(self, ctx):
        respond = ErrorEmbed('Вы не являетесь координатором', f'-# *{ctx.author.mention} ваш персонаж не является координатором команды!*')
        await ctx.respond(embed=respond, ephemeral=True)

    @staticmethod
    def admin_required(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if not self.is_admin(ctx):
                await self.respond_if_not_admin(ctx)
                return
            await func(self, ctx, *args, **kwargs)

        return wrapper

    @staticmethod
    def character_required(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            player_id = ctx.author.id
            character_id = kwargs.get('character_id', None)

            if character_id is not None:
                if not self.is_admin(ctx):
                    await self.respond_if_not_admin(ctx)
                    return
            else:
                character_id = self.get_player_current_character(ctx)
                if character_id is None:
                    await self.respond_if_no_characters(ctx)
                    return

            kwargs['character_id'] = character_id
            await func(self, ctx, *args, **kwargs)

        return wrapper

    @staticmethod
    def in_battle(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            character_id = kwargs.get('character_id', None)

            if self.in_battle_check(character_id) is None:
                await self.respond_if_not_in_battle(ctx)
                return
            kwargs['character_id'] = character_id
            await func(self, ctx, *args, **kwargs)

        return wrapper

    @staticmethod
    def character_is_coordinator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            character_id = kwargs.get('character_id', None)

            if self.is_coordinator(character_id) is None:
                await self.respond_if_not_coordinator(ctx)
                return
            kwargs['character_id'] = character_id
            await func(self, ctx, *args, **kwargs)

        return wrapper


def setup(bot):
    bot.add_cog(BasicCog(bot))