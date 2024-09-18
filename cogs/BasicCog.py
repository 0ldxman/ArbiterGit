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

    @staticmethod
    def prepare_id(user_input:str):
        processed = user_input.split(' ')[0]
        if processed.isdigit():
            return int(processed)
        else:
            return None

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

    def is_group_leader(self, character_id:int):
        from ArbGroups import Group, GroupRole
        group = Group.find_group_by_character_id(character_id)
        if not group:
            return False
        role = GroupRole(group.get_member_role(character_id))
        if role.is_leader:
            return True
        else:
            return False

    def is_single(self, character_id:int):
        from ArbGroups import Group
        group = Group.find_group_by_character_id(character_id)
        if not group:
            return True

        members = group.fetch_group_members()
        if len(members) == 1:
            return True
        else:
            return False

    async def respond_if_not_admin(self, ctx):
        respond = ErrorEmbed('Недостаточно прав', f'-# *{ctx.author.mention} у Вас недостаточно прав для использования данного функционала!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_no_characters(self, ctx):
        respond = ErrorEmbed('Персонаж не обнаружен', f'-# *{ctx.author.mention} в базе данных не было найдено информации о том, что вы управляете персонажем!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_not_in_battle(self, ctx):
        respond = ErrorEmbed('Персонаж не находится в бою', f'-# *{ctx.author.mention} ваш персонаж не находится в бою!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_in_battle(self, ctx):
        respond = ErrorEmbed('Персонаж находится в бою', f'-# *{ctx.author.mention} вы не можете это использовать пока ваш персонаж находится в бою!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_not_coordinator(self, ctx):
        respond = ErrorEmbed('Вы не являетесь координатором', f'-# *{ctx.author.mention} ваш персонаж не является координатором команды!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_if_cant_move_group(self, ctx):
        respond = ErrorEmbed('Вы не являетесь лидером группы', f'-# *{ctx.author.mention} только лидеры отряда и одиночные бойцы без группы могут это использовать!*')
        await ctx.respond(embed=respond, ephemeral=True)

    async def respond_error(self, ctx, e: Exception):
        respond = ErrorEmbed('Ошибка', f'-# *Возникла ошибка при выполнении операции:*\n``{e}``')
        await ctx.respond(embed=respond, ephemeral=True)

    @staticmethod
    def admin_required(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if not self.is_admin_or_moderator(ctx):
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

    @staticmethod
    def is_group_leader_or_single(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            character_id = kwargs.get('character_id', None)

            is_group_leader = self.is_group_leader(character_id)
            is_single = self.is_single(character_id)

            if not (is_group_leader or is_single):
                await self.respond_if_cant_move_group(ctx)
                return
            kwargs['character_id'] = character_id
            await func(self, ctx, *args, **kwargs)

        return wrapper

    @staticmethod
    def not_in_battle(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            character_id = kwargs.get('character_id', None)

            if self.in_battle_check(character_id) is not None:
                await self.respond_if_in_battle(ctx)
                return
            kwargs['character_id'] = character_id
            await func(self, ctx, *args, **kwargs)

        return wrapper

    @staticmethod
    def exception_handle(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            try:
                return await func(self, ctx, *args, **kwargs)
            except Exception as e:
                print('ОШИБКА:', e)
                await self.respond_error(ctx, e)
                return None

        return wrapper


def setup(bot):
    bot.add_cog(BasicCog(bot))