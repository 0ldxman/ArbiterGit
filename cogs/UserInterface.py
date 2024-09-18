import datetime
import json
import pprint
import random

import discord
from discord.ext import commands
from discord import default_permissions
from ArbDatabase import DataManager
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator, SuccessEmbed, ErrorEmbed, InteractiveForm, FormStep, Selection, SelectingForm
from ArbResponse import Response, ResponsePool, RespondIcon, RespondLog, Notification

from .BasicCog import BasicCog

from ArbAutocomplete import ArbAutoComplete, AAC
from typing import Callable
from ArbUtils.ArbTimedate import TimeManager
from ArbUtils.ArbDataParser import ListChunker
from ArbCharacterMemory import CharacterMemory, Relations
from ArbGenerator import NameGenerator, TitleGenerator, GenerateBattle
from ArbCharacters import Character, CharacterProgress, Race
from ArbHealth import Body
from ArbItems import Inventory, Item, CharacterEquipment
from ArbBattle import Actor, Coordinator, Battlefield, BattleTeam, Layer, GameObject, ActionManager
from ArbDialogues import Dialogue, CharacterMessage
from ArbCore import Server, Player, Review


class CharacterMenu(BasicCog):

    generate = discord.SlashCommandGroup("генерация", "Команды генерации")
    character = discord.SlashCommandGroup("персонаж", 'Команды интерфейса персонажа')
    char_info = character.create_subgroup('сведения', 'Информация о персонаже')
    char_mgr = character.create_subgroup('управление', 'Управление персонажами')
    player = discord.SlashCommandGroup("игрок")
    player_info = player.create_subgroup('сведения', 'Информация о пользователе')
    player_reg = player.create_subgroup('анкета', 'Информация о регистрации')
    player_rev = player.create_subgroup('отзывы', 'Информация об отзывах')

    async def tables_list(self):
        db = DataManager()
        return db.get_all_tables()

    async def columns_list(ctx: discord.AutocompleteContext):
        db = DataManager()
        table_name = ctx.options['table']
        return db.get_all_columns(table_name)

    async def get_columns_types(ctx: discord.AutocompleteContext):
        db = DataManager()
        table_name = ctx.options['table']
        return db.get_columns_types(table_name)

    @character.command(name='сменить-имя')
    @BasicCog.character_required
    async def __change_name(self, ctx: discord.ApplicationContext,
                           new_name: discord.Option(str, required=True, min_length=1, max_length=100),
                            character_id: int=None):

        character = Character(character_id)
        character.update_record({'name': new_name})
        character.name = new_name

        embed = SuccessEmbed('Имя персонажа изменено',
                             f'*{ctx.author.mention} изменил имя персонажа ||({character_id})|| на **{character.name}***',
                             logo_url=character.picture,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @character.command(name='сменить-картинку')
    @BasicCog.character_required
    async def __change_avatar(self, ctx: discord.ApplicationContext,
                           new_avatar: discord.Option(discord.SlashCommandOptionType.attachment, required=True),
                           character_id: int=None):
        character = Character(character_id)
        character.update_record({'avatar': str(new_avatar.url)})
        character.picture = new_avatar.url

        embed = SuccessEmbed('Аватарка персонажа изменена',
                             f'*{ctx.author.mention} изменил внешность персонажа **{character.name} ||({character_id})||***',
                             logo_url=character.picture,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @character.command(name='сменить-позывной')
    @BasicCog.character_required
    async def __change_nickname(self, ctx: discord.ApplicationContext,
                           callsign: discord.Option(str, required=True, min_length=1, max_length=100),
                           character_id: int=None):
        from ArbOrgs import Organization, Rank

        character = Character(character_id)
        if not character.org:
            character.update_record({'callsign': callsign})

            embed = SuccessEmbed('Позывной персонажа изменен',
                                 f'*{ctx.author.mention} изменил позывной персонажа **{character.name}** ||({character_id})|| на **"{callsign}"***',
                                 logo_url=character.picture,
                                 footer=ctx.author.display_name,
                                 footer_logo=ctx.author.avatar)
            await ctx.respond(embed=embed)
            return

        character_org = Organization(character.org) if character.org else Organization('Civil')
        character_rank = Rank(character.org_lvl) if character.org_lvl else Rank(character_org.get_random_lowest_rank())

        if not character_rank.can_group:
            embed = ErrorEmbed('Невозможно изменить позывной',
                               f'У персонажа **{character.name}** недостаточно полномочий в организации **{character_org.label}** чтобы изменить позывной.',
                               logo_url=character.picture,
                               footer=ctx.author.display_name,
                               footer_logo=ctx.author.avatar)
            await ctx.respond(embed=embed)
            return

        character.update_record({'callsign': callsign})

        embed = SuccessEmbed('Позывной персонажа изменен',
                             f'*{ctx.author.mention} изменил позывной персонажа **{character.name}** ||({character_id})|| на **"{callsign}"***',
                             logo_url=character.picture,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)
        return


    @character.command(name='сказать')
    @BasicCog.character_required
    async def __say_phrase(self, ctx: discord.ApplicationContext,
                           phrase: discord.Option(str, required=True, min_length=1, max_length=2000),
                           character_id: int=None):
        from ArbDialogues import CharacterMessage, Dialogue

        message = CharacterMessage(character_id, phrase)
        embed = message.get_embed()
        dialogue = Dialogue.get_dialogue_by_channel(ctx.channel.id)
        if dialogue:
            message.save_to_db(dialogue.dialogue_id)

        command = await ctx.respond(f'-# Сообщение от **{Character(character_id).name}** отправлено', ephemeral=True)

        await ctx.send('', embed=embed)
        await command.delete_original_response()

    @character.command(name='кубик')
    @BasicCog.character_required
    async def __dice_roll(self, ctx: discord.ApplicationContext,
                          formula: discord.Option(str, required=True, min_length=2),
                          difficulty: discord.Option(int, required=False, min_value=1, default=None),
                          character_id: int=None):
        from ArbRolePlay import RPDice

        dice = RPDice(formula, difficulty)
        print(dice.get_result())
        await dice.output_results(ctx, character_id)

    @character.command(name='проверка-навыка')
    @BasicCog.character_required
    async def __skill_check(self, ctx: discord.ApplicationContext,
                           skill: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('SKILL_INIT', 'label'))),
                           difficulty: discord.Option(int, required=False, min_value=1),
                           character_id: int=None):
        from ArbSkills import Skill

        skill_id = AAC.extract('SKILL_INIT', 'label', skill, 'id')
        skill_obj = Skill(character_id, skill_id)

        success, dice = skill_obj.skill_check(difficulty)

        dice_postfix = ' (Критический успех!)' if dice.check_critical_success() else ''
        dice_postfix = ' (Полный провал)' if dice.check_critical_failure() and not dice_postfix else dice_postfix

        if not difficulty:
            embed = ArbEmbed(f'Проверка навыка "{skill_obj.label}"',
                             f'### *Выпало: **{dice.result}{dice_postfix} из {skill_obj.lvl + 50}***',
                             footer=Character(character_id).name,
                             logo_url=Character(character_id).picture)
        else:
            if success:
                embed = SuccessEmbed(f'Проверка навыка "{skill_obj.label}"',
                                     f'### *Выпало: **{dice.result}{dice_postfix} из {skill_obj.lvl + 50}***\n'
                                     f'-# - *Сложность: **{difficulty}***',
                                     footer=Character(character_id).name,
                                     logo_url=Character(character_id).picture)
            else:
                embed = ErrorEmbed(f'Проверка навыка "{skill_obj.label}"',
                                     f'### *Выпало: **{dice.result}{dice_postfix} из {skill_obj.lvl + 50}***\n'
                                     f'-# - *Сложность: **{difficulty}***',
                                     footer=Character(character_id).name,
                                     logo_url=Character(character_id).picture)

        await ctx.respond('', embed=embed)



    @character.command(name='персонаж-игрока')
    async def __player_character(self, ctx, user: discord.Option(discord.SlashCommandOptionType.user, required=True)):
        from ArbCore import Player

        player = Player(user.id)
        if not player.current_character:
            embed = ErrorEmbed('Персонаж отсутствует', f'*У игрока {user.mention} нет активного персонажа*')
            await ctx.respond('', embed=embed)
            return

        character_info = Character(player.current_character)
        embed = ArbEmbed(f'Персонаж {user.display_name}',
                         f'***{character_info.__str__()} ({character_info.id})***',
                         footer=character_info.name, footer_logo=character_info.picture)
        await ctx.respond('', embed=embed)

    @character.command(name='владелец-персонажа')
    async def __character_player(self, ctx, character_id: discord.Option(int)):
        player = DataManager().select_dict('CHARS_INIT', filter=f'id = {character_id}')
        if player is None:
            embed = ErrorEmbed('Персонаж не найден', f'*Персонаж с ``id {character_id}`` не найден!*')
            await ctx.respond('', embed=embed)
            return
        owner_id = player[0].get('owner')
        if not owner_id:
            embed = ErrorEmbed('У персонажа отсутствует владелец', f'*Персонаж **{Character(character_id).name} ({character_id})** никому не принадлежит!*')
            await ctx.respond('', embed=embed)
            return

        user = ctx.bot.get_user(owner_id)

        embed = ArbEmbed(f'Игрок - {user.display_name}', f'*Персонаж **{Character(character_id).name} ({character_id})** принадлежит игроку {user.mention}*',
                         footer=Character(character_id).name, footer_logo=Character(character_id).picture)
        await ctx.respond('', embed=embed)

    @char_info.command(name='карточка-персонажа')
    @BasicCog.character_required
    async def __character_info(self, ctx, character_id: int = None):
        character_info = Character(character_id)
        character_text = character_info.text_card()
        print(character_info.owner)
        embed = ArbEmbed(f'Информация о персонаже {character_info.name}', character_text,
                         footer=f'Последняя смена цикла {TimeManager().get_string_timestamp(character_info.update)}\nСервер: {ctx.bot.get_guild(character_info.server).name if character_info.server else "НПС"}',
                         footer_logo=ctx.bot.get_user(character_info.owner).avatar if character_info.owner else '',
                         logo_url=character_info.picture)

        await ctx.respond('', embed=embed)

    @char_info.command(name='здоровье')
    @BasicCog.character_required
    async def __character_body(self, ctx, character_id: int=None):

        body = Body(character_id)
        total_text = body.string_capacities()
        total_text += f'\n-# {body.string_pain()}\n-# {body.string_bleeding()}\n-# {body.string_vital_status()}'

        vital_damage = int(body.vital_damage())
        print(vital_damage)

        capacities_embed = HealthEmbed('Самочувствие', total_text, vital_damage)

        hediffs = body.string_hediff()
        hediffs_embed = HealthEmbed('Ранения и заболевания', hediffs if hediffs else f'-# *(Здесь будут отображаться ваши ранения и болезни)*', vital_damage)

        body_elements = body.string_bodyparts()
        body_elements_embed = HealthEmbed('Части тела', body_elements if body_elements else f'-# *(Здесь будут отображаться ваши части тела)*', vital_damage)

        total_embeds = [capacities_embed, hediffs_embed, body_elements_embed]

        view = Paginator(total_embeds, ctx, {1: 'Самочувствие', 2: 'Ранения и заболевания', 3: 'Части тела'})

        await view.update_button()
        await ctx.respond(embed=total_embeds[0], view=view)

    @character.command(name=f'инвентарь')
    @BasicCog.character_required
    async def __character_inventory(self, ctx, character_id: int=None):


        character_equipment = CharacterEquipment(character_id)
        character_inventory = Inventory.get_inventory_by_character(character_id, data_manager=character_equipment.data_manager)
        equipment_text = character_equipment.string_equipment()
        equipment_text = equipment_text if equipment_text else f'-# *(Здесь будет отображаться ваше снаряжение)*'
        inventory_text = character_inventory.string_inventory()
        inventory_text = inventory_text if inventory_text else f'-# *(Здесь будут отображаться ваши предметы)*'

        equipment_embed = ArbEmbed('Экипировка', equipment_text)
        inventory_embed = ArbEmbed('Инвентарь', inventory_text)

        embeds = [equipment_embed, inventory_embed]

        view = Paginator(embeds, ctx, {1: 'Экипировка', 2: 'Инвентарь'})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @char_info.command(name='отношения')
    @BasicCog.character_required
    async def __character_relations(self, ctx, character_id: int=None):

        character_relations = Character(character_id).text_relations()
        if not character_relations:
            relations_text = f'-# *(Здесь будут отображаться знакомые персонажи)*'
            relations_embed = ArbEmbed(f'Взаимоотношения {Character(character_id).name}', relations_text)
            await ctx.respond(embed=relations_embed)
            return

        total_embeds = []
        chunks = ListChunker(5, character_relations)
        for chunk in chunks:
            total_text = '\n\n'.join(chunk)
            relation_embed = ArbEmbed(f'Взаимоотношения {Character(character_id).name}', total_text)
            total_embeds.append(relation_embed)

        view = Paginator(total_embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=total_embeds[0], view=view)

    @char_info.command(name='воспоминания')
    @BasicCog.character_required
    async def __character_memories(self, ctx, character_id: int = None):

        character_relations = Character(character_id).text_memories()
        if not character_relations:
            relations_text = f'-# *(Здесь будут отображаться воспоминания персонажа)*'
            relations_embed = ArbEmbed(f'Воспоминания {Character(character_id).name}', relations_text)
            await ctx.respond(embed=relations_embed)
            return

        total_embeds = []
        chunks = ListChunker(5, character_relations)
        for chunk in chunks:
            total_text = '\n\n'.join(chunk)
            relation_embed = ArbEmbed(f'Воспоминания {Character(character_id).name}', total_text)
            total_embeds.append(relation_embed)

        view = Paginator(total_embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=total_embeds[0], view=view)

    @char_info.command(name='психология')
    @BasicCog.character_required
    async def __character_psychology(self, ctx, character_id: int = None):
        from ArbPsychology import CharacterPsychology, CharacterMood
        from ArbOrgs import Organization

        psychology = CharacterPsychology(character_id)
        embed = ArbEmbed(f'Психология {Character(character_id).name}',
                         f'*Мировоззрение: **{psychology.get_worldview().label}***\n'
                         f'*Лояльность к {Organization(Character(character_id).org).label if Character(character_id).org else "неизвестно"}: **||{psychology.get_loyalty()}%||***\n'
                         f'*Очки стресса: **{psychology.stress} ОС.***',
                         footer=f'Настроение: {CharacterMood(character_id).mood}',
                         footer_logo=Character(character_id).picture)

        await ctx.respond('', embed=embed)


    @generate.command(name='случайное-имя')
    async def __generate_name(self, ctx, gender: discord.Option(str, choices=['Мужской', 'Женский', 'Бесполый', 'Робот']),
                              value: discord.Option(int, required=False, default=1)):
        total_names = ''
        for _ in range(value):
            total_names += f'\n {NameGenerator(gender)}'

        embed = ArbEmbed('Сгенерированные имена', total_names)
        await ctx.respond(f'', embed=embed)

    @generate.command(name='случайное-название')
    async def __generate_title(self, ctx,
                              type: discord.Option(str, choices=['Страна', 'Планета', 'Организация', 'Город', 'Планета', 'Система']),
                              value: discord.Option(int, required=False, default=1)):
        total_names = ''
        for _ in range(value):
            total_names += f'\n {TitleGenerator(type)}'

        embed = ArbEmbed('Сгенерированные названия', total_names)
        await ctx.respond(f'', embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Обработка сообщений в боевых каналах/потоках
        if message.author.bot:
            return

        channel_id = message.channel.id
        dialogue = Dialogue.get_dialogue_by_channel(channel_id)
        if dialogue is not None:
            ctx = await self.bot.get_context(message)
            character_id = self.get_player_current_character(ctx)
            if character_id:
                char_message = CharacterMessage(character_id, message.content)
                char_message.save_to_db(dialogue.dialogue_id)
                embed = char_message.get_embed()
                await message.delete()
                await ctx.send(embed=embed)

    # @commands.slash_command(name=f'database_edit')
    # @BasicCog.admin_required
    # async def database_edit(self, ctx,
    #                         table: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(tables_list)),
    #                         column: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(columns_list)),
    #                         value,
    #                         filter: discord.Option(str)):
    #
    #     data_manager = DataManager()
    #     try:
    #         rows = data_manager.select_dict(table, filter=filter)
    #         rows_count = len(rows)
    #         row_value = rows[0].get(column)
    #         data_manager.update(table, {column: value}, filter=filter)
    #
    #         embed = SuccessEmbed(f'Изменение в базе данных',
    #                              f'Были внесены **{rows_count}** изменений в таблице `{table}` в колонке `{column}`'
    #                              f'\n-# Изменено: ``{row_value}`` на `{value}`.')
    #         await ctx.respond(embed=embed)
    #
    #     except Exception as e:
    #         embed = ErrorEmbed(f'Изменение в базе данных',
    #                            f'При изменении значения в таблице `{table}` возникла ошибка:'
    #                            f'```{e}```')
    #         await ctx.respond(embed=embed)
    #
    # @commands.slash_command(name=f'check_database')
    # @BasicCog.admin_required
    # async def check_database(self, ctx,
    #                         table: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(tables_list)),
    #                         filter: discord.Option(str, required=False),
    #                         page: discord.Option(int, required=False)):
    #
    #     data_manager = DataManager()
    #     rows = data_manager.select_dict(table, filter=filter)
    #     rows_text = []
    #     for row in rows:
    #         row_items = row.items()
    #         row_text = f''
    #         for item, value in row_items:
    #             row_text += f'- ``{item}:`` **{value}**\n'
    #         rows_text.append(row_text)
    #
    #     chuked_text = ListChunker(5, rows_text)
    #     embeds = []
    #     for chunk in chuked_text:
    #         chunk_text = '\n\n'.join(chunk)
    #         embed = ArbEmbed(f'Содержание {table}', chunk_text)
    #         embeds.append(embed)
    #
    #     view = Paginator(embeds, ctx, ignore_footer=True)
    #     await ctx.respond(view=view, embed=embeds[page-1 if page and page <= len(embeds) else 0])

    @player_info.command(name='карточка-игрока')
    async def __player_card(self, ctx, player_id: discord.Option(discord.SlashCommandOptionType.user, required=False)):
        from ArbCore import Player

        if not player_id:
            player_id = ctx.author

        await Player(player_id.id).player_card(ctx)

    @player_rev.command(name='написать-отзыв')
    async def __review(self, ctx,
                       player: discord.Option(discord.SlashCommandOptionType.user),
                       raiting: discord.Option(int, min_value=1, max_value=5, required=True),
                       is_anonymous: discord.Option(discord.SlashCommandOptionType.boolean, default=False),
                       title: discord.Option(str, required=False),
                       description: discord.Option(str, required=False)):
        from ArbCore import Review

        if player.id == ctx.author.id:
            embed = ErrorEmbed('Некорректный ввод', '-# *Вы не можете написать отзыв про самого себя!*')
            await ctx.respond('', embed=embed)
            return

        review = Review.create_review(player.id, rating=raiting, review_text=description, title=title, reviewer=ctx.author.id if not is_anonymous else None)
        embed = review.to_embed(ctx)
        await ctx.respond('', embed=embed)

    @player_rev.command(name='мои-отзывы')
    async def __my_reviews(self, ctx,
                           player_id: discord.Option(discord.SlashCommandOptionType.user, required=False)):
        from ArbCore import Review

        if not player_id:
            player_id = ctx.author

        reviews = Review.get_all_player_reviews(player_id.id)
        embeds = [embed.to_embed(ctx) for embed in reviews]
        view = Paginator(embeds, ctx)

        await ctx.respond('', view=view, embed=embeds[0])

    @player.command(name='рп-запрос')
    async def __rp_request(self, ctx,
                               type: discord.Option(str, choices=['Личный', 'Фракционный', 'Дополнительный', 'Диалоговый', 'Организационный'], required=True),
                               title: discord.Option(str, required=False),
                               description: discord.Option(str, required=False),
                               admin: discord.Option(discord.SlashCommandOptionType.user, required=False),
                               date: discord.Option(discord.SlashCommandOptionType.string, required=False)):
        from ArbCore import RPRequest

        author_id = ctx.author.id

        new_request = RPRequest.create_request(ctx.guild.id,
                                               status='Не рассмотрено',
                                               type=type,
                                               title=title,
                                               description=description,
                                               author_id=author_id,
                                               admin_id=admin.id if admin else None,
                                               requester_id=author_id,
                                               timestamp=datetime.datetime.now().strftime('%d-%m-%Y %H:%M'),
                                               planned_timestamp=date if date else None)
        await new_request.request_notification(ctx)
        dm_embed = new_request.to_embed(ctx)
        embed = SuccessEmbed('Новый РП-запрос создан!', '-# Вы успешно отправили кураторскому отделу сервера ваш запрос на ролевую отыгровку!')
        await ctx.respond('', embed=embed)
        await ctx.author.send('', embed=dm_embed)

    @player_info.command(name='мои-персонажи')
    async def __my_characters(self, ctx):
        from ArbCore import Player
        from ArbCharacters import Character

        player = Player(ctx.author.id)
        characters = [Character(char, data_manager=player.data_manager) for char in
                      player.get_all_server_characters(ctx.guild.id)]
        characters_text = ''
        for char in characters:
            characters_text += f'- *{char.__str__()}* ||(ID: {char.id})||\n'
        embed = ArbEmbed(f'Персонажи {ctx.author.display_name} | {ctx.guild.name}',
                         desc=f'{characters_text}' if characters_text else '-# *(У вас нет активных персонажей на этом сервере)*',
                         footer=f'Количество персонажей: {len(characters)} / {player.get_servers_max_characters().get(ctx.guild.id)}',
                         footer_logo=ctx.author.avatar)

        await ctx.respond('', embed=embed)

    @char_mgr.command(name='сменить-персонажа')
    async def __switch_character(self, ctx, character_id:int):
        from ArbCore import Player
        from ArbCharacters import Character
        is_admin = self.is_admin_or_moderator(ctx)

        available_characters = Player(ctx.author.id).get_characters_list()
        print(available_characters)
        if character_id not in available_characters:
            if not is_admin:
                embed = ErrorEmbed('Неверный ID персонажа', '-# Персонаж с данным ID вам не принадлежит!')
                await ctx.respond(embed=embed)
                return
            else:
                Player(ctx.author.id).switch_character(character_id)
                embed = SuccessEmbed(f'Контроль над персонажем {Character(character_id).name}', f'-# *Вы успешно взяли под личный контроль персонажа ||**{Character(character_id).__str__()}**||*')
                await ctx.respond(embed=embed)
                return
        else:
            Player(ctx.author.id).switch_character(character_id)
            embed = SuccessEmbed(f'Контроль над персонажем {Character(character_id).name}', f'-# *Вы успешно взяли под личный контроль персонажа ||**{Character(character_id).__str__()}**||*')
            await ctx.respond(embed=embed)

    @char_mgr.command(name='бросить-персонажа')
    async def __leave_my_character(self, ctx, character_id:int):
        from ArbCore import Player
        from ArbCharacters import Character
        is_admin = self.is_admin_or_moderator(ctx)

        available_characters = Player(ctx.author.id).get_characters_list()
        if character_id not in available_characters:
            if not is_admin:
                embed = ErrorEmbed('Неверный ID персонажа', '-# Персонаж с данным ID вам не принадлежит!')
                await ctx.respond(embed=embed)
                return
            else:
                player = ctx.bot.get_user(Character(character_id).owner)
                Player(ctx.author.id).leave_character(character_id)
                embed = SuccessEmbed(f'{player.display_name} потерял контроль над персонажем',
                                     f'-# *Игрок {player.mention} потерял контроль над персонажем ||**{Character(character_id).__str__()}**||*')
                await ctx.respond(embed=embed)
        else:
            Player(ctx.author.id).leave_character(character_id)
            embed = SuccessEmbed(f'{ctx.author.display_name} потерял контроль над персонажем',
                                 f'-# *Вы потеряли контроль над персонажем ||**{Character(character_id).__str__()}**||*')
            await ctx.respond(embed=embed)

    @char_mgr.command(name='передать-персонажа')
    async def __transfer_character(self, ctx, character_id:int,
                                   new_owner: discord.Option(discord.SlashCommandOptionType.user, required=True)):
        from ArbCore import Player
        from ArbCharacters import Character

        is_admin = self.is_admin_or_moderator(ctx)
        available_characters = Player(ctx.author.id).get_characters_list()

        character = Character(character_id)

        if character_id not in available_characters:
            if not is_admin:
                embed = ErrorEmbed('Неверный ID персонажа', '-# Персонаж с данным ID вам не принадлежит!')
                await ctx.respond(embed=embed)
                return
            else:
                character.set_owner(new_owner.id)
                embed = SuccessEmbed(f'{ctx.author.display_name} передал контроль над персонажем',
                                     f'-# *Игрок {ctx.author.mention} передал контроль над персонажем ||**{character.__str__()}**|| пользователю {new_owner.mention}*')
                await ctx.respond(embed=embed)
                return

    @commands.slash_command(name='отдохнуть')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    @BasicCog.is_group_leader_or_single
    async def __skip_cycles(self, ctx, cycles:discord.Option(int, default=1, min_value=1), character_id:int=None):
        from ArbCharacters import Character
        from ArbLocations import CharacterLocation
        from ArbGroups import Group
        from ArbUIUX import Vote

        max_cycles = Group.can_group_skip_cycles(character_id)

        if max_cycles <= 0:
            embed = ErrorEmbed('Невозможно отдохнуть', f'-# Вы или ваша группа не может расположиться в этом месте для отдыха')
            await ctx.respond(embed=embed)
            return

        group_members = Group.find_group_members_including(character_id)
        if len(group_members) > 1:
            players_id = []
            for member in group_members:
                player = DataManager().select_dict('CHARS_INIT', filter=f'id = {member}')
                if not player:
                    continue
                owner_id = player[0].get('owner')
                if not owner_id:
                    continue
                players_id.append(owner_id)

            vote = Vote('Вы готовы отдохнуть?', ['Да', 'Нет'], players_id, 1)
            result = await vote.start(ctx)

            if result == 'Нет':
                embed = ErrorEmbed('Отказ от отдыха', '-# Ваша группа провела голосование и решила отложить отдых')
                await ctx.respond(embed=embed)
                return

        if cycles < max_cycles:
            max_cycles = cycles

        print(f'Группа {character_id} может пропустить {max_cycles}')

        for member in group_members:
            Character(member).change_cycle(max_cycles)

        chars_names = [Character(member).name for member in group_members]

        embed = SuccessEmbed(f'Отдых', f'*Персонажи **{", ".join(chars_names)}** расположились на отдых на протяжении **{max_cycles} циклов**' + f'{" на локации" if CharacterLocation(Group.get_group_leader_by_character_id(character_id)).entered_location else " вблизи"}' + f" **{CharacterLocation(Group.get_group_leader_by_character_id(character_id)).location.label}***")

        await ctx.respond(embed=embed)

    @commands.slash_command(name='бюджет')
    @BasicCog.character_required
    async def __budget(self, ctx, character_id:int=None):
        from ArbCharacters import Character
        from ArbCore import Server

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        embed = SuccessEmbed(f'',
                             f'**Бюджет:**\n{ct}{int(character.money):,d}')
        embed.set_author(character.name, icon_url=character.picture)
        await ctx.respond(embed=embed)

    @commands.slash_command(name='голосование-группы')
    @BasicCog.character_required
    @BasicCog.is_group_leader_or_single
    async def __vote(self, ctx: discord.ApplicationContext,
                     question: discord.Option(str, min_length=1, max_length=120),
                     duration: discord.Option(int, min_value=1, max_value=10),
                     character_id:int=None):
        from ArbGroups import Group
        from ArbUIUX import Vote

        group_members = Group.find_group_members_including(character_id)

        players_id = []
        for member in group_members:
            player = DataManager().select_dict('CHARS_INIT', filter=f'id = {member}')
            if not player:
                continue
            owner_id = player[0].get('owner')
            if not owner_id:
                continue
            players_id.append(owner_id)

        vote = Vote(question, ['Да', 'Нет'], players_id, duration)
        result = await vote.start(ctx)
        print(result)


class Registration(BasicCog):
    reg = discord.SlashCommandGroup('регистрация', 'Команды регистрации')

    async def rank_choice(ctx: discord.AutocompleteContext):
        from ArbOrgs import Organization, Rank

        org = ctx.options.get('organization')
        org_id = AAC.extract('ORG_INIT', 'label', org, 'id')
        o_org = Organization(org_id)
        ranks = o_org.get_inherited_ranks()

        return [Rank(rank).label for rank in ranks]

    async def gender_choice(ctx: discord.AutocompleteContext):
        race = ctx.options.get('race')
        race_id = AAC.extract('RACES_INIT', 'name', race, 'id') if race else 'Human'
        sex = AAC.extract('RACES_INIT', 'id', race_id, 'sex')
        if sex.lower() == 'диморфизм':
            return ['Мужской', 'Женский']
        elif sex.lower() == 'бесполый':
            return ['Бесполый']
        else:
            return ['Мужской', 'Женский', 'Бесполый']

    async def author_forms(ctx: discord.AutocompleteContext):
        author = ctx.interaction.user.id
        forms = DataManager().select_dict('REGISTRATION', filter=f'user_id = {author}')
        choices = []
        for form in forms:
            character_name = json.loads(form.get('data')).get('name')
            choices.append(f'{form.get("form_id")} - {character_name}')

        return choices

    @reg.command(name='начать-регистрацию')
    async def __start_registration(self, ctx):
        from ArbRegistration import CharacterRegistration
        from ArbCore import Player, Server

        author = ctx.author.id
        chars_list = Player(author).get_all_server_characters(ctx.guild.id)
        if len(chars_list) >= Server(ctx.guild.id).get_max_characters(author) and not BasicCog.is_admin_or_moderator(self, ctx):
            embed = ErrorEmbed('Ошибка регистрации', f'-# Вы достигли максимального количества персонажей на сервере **{ctx.guild.name}**')
            await ctx.respond(embed=embed)
            return

        character_registration = CharacterRegistration(ctx)
        character_registration.form.extend_data('owner', [author])
        character_registration.form.extend_data('update', [datetime.datetime.now().date().strftime('%Y-%m-%d')])
        character_registration.form.extend_data('server', [ctx.guild.id])
        result = await character_registration.start()
        print(result)

    @reg.command(name='создать-шаблон')
    async def __create_form(self, ctx,
                            race: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('RACES_INIT', 'name', 'primitive = 0 AND is_robot = 0'))),
                            organization: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('ORG_INIT', 'label'))),
                            gender: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(gender_choice), required=False),
                            age: discord.Option(int, min_value=20, max_value=70, required=False),
                            worldview: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('WORLDVIEW', 'label')), required=False),
                            rank: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(rank_choice), required=False),
                            name: discord.Option(str, required=False),
                            faction: discord.Option(str, required=False),
                            callsign: discord.Option(str, required=False),
                            picture_url: discord.Option(str, required=False)):

        from ArbGenerator import NameGenerator
        from ArbOrgs import Organization, Rank

        if not gender:
            race_id = AAC.extract('RACES_INIT', 'name', race, 'id') if race else 'Human'
            sex = AAC.extract('RACES_INIT', 'id', race_id, 'sex')
            if sex.lower() == 'диморфизм':
                gender = random.choice(['Мужской', 'Женский'])
            elif sex.lower() == 'бесполый':
                gender = random.choice(['Бесполый'])
            else:
                gender = random.choice(['Мужской', 'Женский', 'Бесполый'])

        name = name if name else NameGenerator(gender, True)
        age = age if age else random.randint(20, 60)
        callsign = f'\nПозывной: {callsign}' if callsign else ''
        picture_url = f'\nКартинка: {picture_url}' if picture_url else ''
        faction = f'\nФракция: {faction}' if faction else ''
        worldview = worldview if worldview else random.choice(DataManager().select_dict('WORLDVIEW')).get('label')

        if not rank:
            org_id = AAC.extract('ORG_INIT', 'label', organization, 'id')
            org = Organization(org_id)
            lowest_rank = Rank(org.get_random_lowest_rank()).label
            rank = f'\nЗвание: {lowest_rank}'
        else:
            rank = f'\nЗвание: {rank}'


        form: str = f'''```
Имя Фамилия: {name}{callsign}
Раса: {race}
Пол: {gender}
Возраст: {age} лет
Мировоззрение: {worldview}
Организация: {organization}{rank}{faction}{picture_url}```
        '''

        embed = SuccessEmbed(f'Шаблон для регистрации персонажа {name}',
                         f'{form}\n-# Вы можете скопировать данный шаблон и прислать его боту во время регистрации персонажа ``/reg start_registration``',
                         footer=ctx.author.display_name,
                         footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @reg.command(name='мои-анкеты')
    async def __my_forms(self, ctx: discord.ApplicationContext, player_id: discord.Option(discord.SlashCommandOptionType.user, required=False)):
        from ArbOrgs import Organization, Rank
        from ArbRaces import Race
        from ArbPsychology import WorldView


        player_id = player_id.id if player_id else ctx.author.id
        db = DataManager()
        forms = db.select_dict('REGISTRATION', filter=f'user_id = {player_id}')
        embeds = []
        for form in forms:
            character_data: dict[str, int | str] = json.loads(form.get("data"))
            name = character_data.get('name')
            callsign = character_data.get('callsign')
            race = character_data.get('race')
            sex = character_data.get('sex')
            age = character_data.get('age')
            worldview = character_data.get('worldview')
            org = character_data.get('org')
            rank = character_data.get('org_lvl')
            faction = character_data.get('frac')
            avatar = character_data.get('avatar')

            desc = f'```'
            desc += f'Имя Фамилия: {name}\n'
            desc += f'Позывной: {callsign}\n' if callsign else ''
            desc += f'Раса: {Race(race).label}\n'
            desc += f'Пол: {sex}\n'
            desc += f'Возраст: {age} лет\n'
            desc += f'Мировоззрение: {WorldView(worldview).label}\n'
            desc += f'Организация: {Organization(org).label}\n' if org else ''
            desc += f'Звание: {Rank(rank).label}\n' if rank else ''
            desc += f'Фракция: {faction}\n' if faction else ''
            desc += f'```'

            embed = ArbEmbed(f'Анкета #{form.get("form_id")} | ОЖИДАЕТ РАССМОТРЕНИЯ',
                             desc,
                             footer=f'{ctx.bot.get_user(character_data.get("owner")).display_name} | {ctx.bot.get_guild(character_data.get("server")).name}',
                             footer_logo=ctx.bot.get_user(character_data.get('owner')).avatar,
                             picture=avatar,
                             logo_url=ctx.bot.get_guild(character_data.get("server")).icon)
            embeds.append(embed)

        view = Paginator(embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @reg.command(name='удалить-анкету')
    async def __delete_my_form(self, ctx: discord.ApplicationContext,
                               form: discord.Option(str, autocomplete=author_forms)):
        from ArbUIUX import InviteView
        form_id = int(form.split(' ')[0])
        character_name_parts = form.split(' ')[1:]
        name = ' '.join(character_name_parts)

        accept = SuccessEmbed(f'Удаление анкеты персонажа {name}',
                              f'*{ctx.author.mention} Вы успешно удалили форму ``#{form_id}`` регистрации персонажа **{name}***',
                              footer=ctx.author.display_name,
                              footer_logo=ctx.author.avatar)
        deny = ErrorEmbed(f'Отмена',
                          f'*{ctx.author.mention} Вы прервали удаление формы ``#{form_id}`` регистрации персонажа **{name}***',
                          footer=ctx.author.display_name,
                          footer_logo=ctx.author.avatar)

        view = InviteView(ctx,
                          accept_label='Подтвердить',
                          deny_label='Отменить',
                          acceptor=ctx,
                          accept_embed=accept,
                          deny_embed=deny)

        embed = ArbEmbed('Подтверждение',
                         f'Вы действительно хотите удалить анкету персонажа **{name}** ``(Форма {form_id})``?')
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed, view=view)
        result = await ctx.bot.wait_for('interaction')

        if result.custom_id == 'Accept':
            DataManager().delete('REGISTRATION', f'form_id = {form_id}')

    @reg.command(name='отправить-биографию')
    async def __send_biography(self,
                               ctx: discord.ApplicationContext,
                               form: discord.Option(str, autocomplete=author_forms),
                               link: discord.Option(str)):
        from ArbCore import Server

        regform_channel = Server(ctx.guild.id).registration_chat
        channel = ctx.bot.get_channel(regform_channel)

        form_id = int(form.split(' ')[0])
        character_name_parts = form.split(' ')[2:]
        name =' '.join(character_name_parts)

        embed = SuccessEmbed(f'Биография {name} отправлена', f'*{ctx.author.mention} Вы успешно отправили ссылку на биографию персонажа **{name}***: ``{link}``',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        DataManager().update('REGISTRATION', {'bio': link}, f'form_id = {form_id}')

        await ctx.respond(embed=embed)

        embed = ArbEmbed(f'Биография {name}',
                         f'> **Отправитель: {ctx.author.mention}**\n'
                         f'> **Ссылка на биографию:** {link}',
                         footer_logo=ctx.guild.icon,
                         footer=ctx.guild.name)

        await channel.send(f'### @everyone', embed=embed)


class CharacterQuests(BasicCog):
    quest = discord.SlashCommandGroup("задания", "Команды для работы с квестами")

    @quest.command(name='мои-задания')
    @BasicCog.character_required
    async def my_quests(self, ctx: discord.ApplicationContext, character_id:int=None):
        from ArbQuests import CharacterQuest

        db = DataManager()
        data = db.select_dict('CHARS_QUESTS', filter=f'id = {character_id}')
        character_quests = []
        for quest in data:
            char_quest = CharacterQuest(character_id, quest.get('quest_id'), data_manager=db)
            character_quests.append(char_quest)

        if not character_quests:
            embed = ArbEmbed(f'Задания {Character(character_id).name}',
                             f'-# (Здесь будут отображаться ваши задани)')
            await ctx.respond(embed=embed)
            return

        char_quest = sorted(character_quests, key=lambda x: (x.status != "Выполняется", x.status))
        quests_desc = [quest.string_quest_desc() for quest in char_quest]
        total_desc = '\n\n'.join(quests_desc)

        embed = ArbEmbed(f'Задания {Character(character_id).name}', f'{total_desc}',
                         footer=f'{Character(character_id).name}',
                         footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @quest.command(name='задание')
    @BasicCog.character_required
    async def current_quest(self, ctx: discord.ApplicationContext, character_id:int=None):
        from ArbQuests import QuestManager

        quest = QuestManager().get_current_quest(character_id)
        if not quest:
            embed = ArbEmbed(f'Задание', f'-# (Здесь будет отображаться информация о текущем задании)',
                             footer=f'{Character(character_id).name}',
                             footer_logo=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        quest_desc = quest.describe_quest()
        quest_tasks = quest.describe_quest_tasks()

        embed = ArbEmbed(f'Задание {quest.get_quest().label}', f'{quest_desc}',
                         logo_url=quest.get_quest().picture,
                         footer=f'{Character(character_id).name}',
                         footer_logo=Character(character_id).picture)

        task_embed = ArbEmbed(f'Задание {quest.get_quest().label}',
                              f'{quest_tasks}',
                              logo_url=quest.get_quest().picture,
                              footer=Character(character_id).name,
                              footer_logo=Character(character_id).picture)
        embeds = [embed, task_embed]
        view = Paginator(embeds, ctx, {1: 'Информация', 2: 'Задачи'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)




class CharacterCombat(BasicCog):
    combat = discord.SlashCommandGroup("бой", "Боевые команды")
    coordinator = combat.create_subgroup("координация", "Команды боевого координатора")
    movement = combat.create_subgroup("движение", "Команды перемещения в бою")
    interact = combat.create_subgroup("действие", "Команды для взаимодействия с объектами")
    detection = combat.create_subgroup("обнаружение", "Команды обнаружения")
    melee = combat.create_subgroup("ближний-бой", 'Команды ближнего боя')
    cmb_range = combat.create_subgroup("дальний-бой", 'Команды дальнего боя')
    cmb_info = combat.create_subgroup("сведения", 'Информация о бое')
    cmb_control = combat.create_subgroup("тактика", 'Команды боевых тактик')

    async def find_battle(self, character_id:int):
        db = DataManager()
        battle_data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {character_id}')
        if not battle_data:
            return None
        else:
            return battle_data[0].get('battle_id')

    async def battle_info(self, ctx, battle_id:int, character_id:int):
        from ArbBattle import Battlefield
        from ArbCharacters import Character

        player_character = Character(character_id)

        battle = Battlefield(battle_id)
        label, battle_info = battle.describe()
        embed = ArbEmbed(f'{label}', battle_info,
                         footer=f'{player_character.name}',
                         footer_logo=player_character.picture)

        await ctx.respond(embed=embed)

    async def battle_teams(self, ctx, battle_id:int, character_id:int):
        from ArbBattle import Battlefield
        from ArbCharacters import Character

        player_character = Character(character_id)

        battle = Battlefield(battle_id)
        battle_info = battle.describe_teams()
        embed = ArbEmbed(f'{battle.label}', battle_info,
                         footer=f'{player_character.name}',
                         footer_logo=player_character.picture)

        await ctx.respond(embed=embed)

    async def get_battle_layers(ctx: discord.AutocompleteContext):
        from ArbCore import Player

        character = ctx.options.get('character_id')
        if not character:
            character = Player(ctx.interaction.user.id).current_character

        battle = Battlefield.get_actor_battle(character)
        battle_layers = Battlefield(battle)

        return [f'{layer_id} - {layer.label}' for layer_id, layer in battle_layers.get_layers()]

    def get_layer_objects(ctx: discord.AutocompleteContext):
        from ArbCore import Player

        character = ctx.options.get('character_id')
        if not character:
            character = Player(ctx.interaction.user.id).current_character

        battle = Battlefield.get_actor_battle(character)
        actor_layer = Actor(character).layer_id
        layer_objects = Layer(actor_layer, battle).get_objects()

        return [f'{obj.id} - {obj.object_type.label}' for obj in layer_objects]

    def get_actors_melees(ctx: discord.AutocompleteContext):
        from ArbCore import Player

        character = ctx.options.get('character_id')
        if not character:
            character = Player(ctx.interaction.user.id).current_character

        actor = Actor(character)
        actor_melees = actor.status().melees
        return [f'{melee_id} - {Character(melee_id).name}' for melee_id in actor_melees]

    async def ammo_type(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbItems import CharacterEquipment
        from ArbWeapons import Weapon

        character = ctx.options.get('character_id')
        if not character:
            character = Player(ctx.interaction.user.id).current_character

        print(character)
        weapon = Weapon(CharacterEquipment(character).weapon().item_id)
        print(weapon)
        weapon_caliber = weapon.caliber
        print(weapon, weapon_caliber)
        return AAC.db_options('AMMO', 'name', f'caliber = "{weapon_caliber}"')

    @cmb_info.command(name='моя-команда')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __my_team(self, ctx, character_id:int=None):
        battle_id = await self.find_battle(character_id)
        battle = Battlefield(battle_id)
        team = BattleTeam.get_actor_team(character_id)
        if not team:
            embed = ErrorEmbed('Команда отсутствует', f'-# В этом бою у вас нет команды...',
                               footer=f'{Character(character_id).name}',
                               footer_logo=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        members = team.fetch_members()
        dead_members = team.get_dead_members()
        total_members = members + dead_members
        print(total_members)

        members_names = [f'- ``[{"НЕАКТИВЕН" if member in dead_members else "АКТИВЕН"}]`` {Character(member).name} ({member}) - ходит {battle.actor_turn_index(member) if battle.actor_turn_index(member) else "||неизвестно||"}/{len(battle.turn_order())}' for member in total_members]

        total_text = '\n'.join(members_names)

        embed = ArbEmbed(f'Команда {team.label} | Бой {battle.label}', total_text,
                         footer=f'{Character(character_id).name}',
                         footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @cmb_info.command(name='текущий-ход')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __my_turn(self, ctx, character_id:int=None):
        battle_id = await self.find_battle(character_id)
        battle = Battlefield(battle_id)
        turn_order = battle.turn_order()
        my_turn = battle.actor_turn_index(character_id)
        current_turn = battle.current_turn_index()

        embed = ArbEmbed(f'Текущий ход: {current_turn} / {len(turn_order)}',
                         f'-# Ваш номер хода - {my_turn}{" **(ВАШ ХОД!)**" if my_turn == current_turn else ""}',
                         footer=f'{Character(character_id).name}',
                         footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)


    @cmb_info.command(name='текущий-бой')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __my_battle(self, ctx, character_id:int=None):
        battle = await self.find_battle(character_id)
        await self.battle_info(ctx, battle, character_id)

    @commands.slash_command(name='осмотреть-оружие')
    @BasicCog.character_required
    async def __expect_weapon(self, ctx, character_id:int=None):
        from ArbWeapons import Weapon
        from ArbAmmo import Ammunition
        from ArbItems import CharacterEquipment
        from ArbSkills import SkillInit
        from ArbDamage import DamageType

        weapon_item = CharacterEquipment(character_id).weapon()
        if not weapon_item:
            embed = ErrorEmbed('Нет оружия', '-# У вас нет экипированного оружия, которое можно осмотреть!')
            await ctx.respond(embed=embed)

        weapon = Weapon(weapon_item.item_id, data_manager=weapon_item.data_manager)

        total_text = f''
        total_text += f'*Тип оружия: **{SkillInit(weapon.weapon_class).label}***'
        total_text += f'\n*Калибр: **{weapon.caliber}***' if weapon.caliber else ''
        total_text += f'\n*Объем магазина: **{weapon.mag_capacity}** патронов*' if weapon.mag_capacity else ''
        total_text += f'\n*Начальная точность атаки: **{weapon.accuracy}%***'
        total_text += f'\n*Темп стрельбы: **{weapon.attacks} выстрелов за атаку***' if weapon.weapon_class != 'ColdSteel' else f'\n*Количество атак: **{weapon.attacks} удара***'
        total_text += f'\n*Издаваемый шум: **{weapon.shot_noise():.2f}% ({weapon.melee_noise():.2f}%)***' if weapon.weapon_class != 'ColdSteel' else f'\n*Издаваемый шум: **{weapon.melee_noise():.2f}%***'
        total_text += f'\n\n-# *Текущая прочность: **{weapon.get_weapon_endurance() * 100}%***'
        total_text += f'\n-# *Цена атаки: **{weapon.action_points} ОД.***'
        total_text += f'\n-# *Цена перезарядки: **{weapon.reload_ap_cost} ОД.***' if weapon.reload_ap_cost else ''

        weapon_embed = ArbEmbed(f'{weapon.label} ({SkillInit(weapon.weapon_class).label})', total_text)

        embeds = [weapon_embed]
        if weapon.get_current_ammotype():
            ammo = Ammunition(weapon.get_current_ammotype())

            ammo_text = f'*Снаряженные патроны: **{ammo.label} ({weapon.get_current_bullets()}шт.)***'
            ammo_text += f'\n***Наносимый урон:***'
            ammo_damage_text = f''
            for damage in ammo.get_damage_info():
                ammo_damage_text += f'\n-# - **{DamageType(damage.get("damage_type")).label} ({DamageType(damage.get("blocked_type")).label})** — {damage.get("min_damage")}-{damage.get("max_damage")} еу. (x{damage.get("critical_multiplier")} с шансом {damage.get("critical_chance")}%)'
            ammo_text += f'{ammo_damage_text}'

            ammo_embed = ArbEmbed('Патроны', ammo_text)
            embeds.append(ammo_embed)

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @cmb_info.command(name=f'боевая-информация')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __combat_info(self, ctx, character_id:int=None):
        character = Character(character_id)
        character_text = character.text_combat_card()

        embed = ArbEmbed(f'Боевое состояние {character.name}', character_text)

        await ctx.respond('', embed=embed)

    @detection.command(name=f'осмотреть')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __combat_lookout(self, ctx, character_id: int=None):
        from ArbBattle import ActorVision
        actor = Actor(character_id)
        vision = ActorVision(actor)

        total_text, chunks = vision.string_vigilance()
        embeds = []
        splited_chunks = ListChunker(5, chunks)
        for chunk in splited_chunks:
            embed = ArbEmbed(f'Обзор местности', '\n'.join(chunk))
            embeds.append(embed)

        view = Paginator(embeds, ctx, ignore_footer=True)

        await ctx.respond('', embed=embeds[0], view=view, ephemeral=True)

    @detection.command(name=f'прислушаться')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __detect_sound(self, ctx, sound_id:int, character_id: int = None):
        actor = Actor(character_id)
        responses = actor.detect_sound(sound_id)

        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i+1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @detection.command(name=f'звуки')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __combat_sounds(self, ctx, character_id: int = None):
        from ArbBattle import ActorSounds
        from ArbUtils.ArbDataParser import ListChunker
        actor = Actor(character_id)
        sounds = ActorSounds(actor)

        total_text = ListChunker(10, sounds.string_sounds())
        embeds = []
        for text in total_text:
            embed = ArbEmbed(f'Звуки боя', ''.join(text))
            embeds.append(embed)

        view = Paginator(embeds, ctx, ignore_footer=True)

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @movement.command(name='перейти-на-слой')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __move_to_layer(self, ctx, layer_id:int, character_id: int=None):
        actor = Actor(character_id)
        responses: ActionManager = actor.move_to_layer(layer_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @movement.command(name='укрыться')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __move_to_object(self, ctx, object_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.move_to_object(object_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @movement.command(name='сбежать')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __escape(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.escape()
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @movement.command(name='полет')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __fly(self, ctx, height: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.fly(height)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_range.command(name='перезарядить')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __reload(self, ctx, ammo_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(ammo_type), required=True), character_id: int = None):
        actor = Actor(character_id)

        ammo_id = AAC.extract('AMMO', 'name', ammo_type, 'id')
        print(ammo_id)
        responses: ActionManager = actor.reload(ammo_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_range.command(name='стрелять')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __range_attack(self, ctx, enemy_id: int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.range_attack(enemy_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

        # view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})
        #
        # await view.update_button()
        # await ctx.respond(embed=embeds[0], view=view)

    @melee.command(name='ударить')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __melee_attack(self, ctx, enemy_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.melee_attack(enemy_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @melee.command(name='боевой-приём')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __race_attack(self, ctx, enemy_id: int = None, attack_id:str=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.race_attack(enemy_id, attack_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @combat.command(name='кинуть-гранату')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __grenade_attack(self, ctx, enemy_id: int = None, grenade_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.throw_grenade(enemy_id, grenade_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_range.command(name='прицелиться')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __set_target(self, ctx, enemy_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_target(enemy_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @melee.command(name='сблизитьтся')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __set_melee_target(self, ctx, enemy_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_melee_target(enemy_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @melee.command(name='отдалиться')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __flee_from_melee(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.flee_from_melee()
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @interact.command(name='с-объектом')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __object_interaction(self, ctx, target_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.interact_with_object(target_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='охотиться')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __hunt(self, ctx, enemy_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_hunt(enemy_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='подавить')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __suppress(self, ctx, cover_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_suppression(cover_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='сдержать')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __contain(self, ctx, layer_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_containment(layer_id)
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='дозор')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __overwatch(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.set_overwatch()
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='ожидать')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __wait(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.waiting()
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)

    @cmb_control.command(name='прекратить')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __stop(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ActionManager = actor.reset_statuses()
        embeds = responses.log

        await embeds.view_responds(ctx)

        await Notification.send_all_notifications(ctx)


    @coordinator.command(name='артудар')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __artillery_strike(self, ctx, layer_id:int, strikes:int = 1, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))

        response = coordinator.artillery_strike(layer_id=layer_id, value=strikes, ammo_id='FragGrenade')
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='подкрепление')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __reinforcement(self, ctx, layer_id: int, units: int = 1, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))

        response = coordinator.reinforcement(layer_id=layer_id, value=units)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='сбросить-мины')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __mines(self, ctx, layer_id: int, mines: int = 1, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.mine_laying(layer_id=layer_id, mine_type=f'APM', value=mines)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='немедленная-эвакуация')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __emergency_evacuation(self, ctx, layer_id: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.emergency_evacuation(layer_id=layer_id)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='сбросить-патроны')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_ammo(self, ctx, layer_id: int, value:int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.supply_ammo(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='сбросить-гранаты')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_grenades(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.supply_grenades(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='сбросить-медпомощь')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_firstaid(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.supply_firstaid(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='сбросить-инструменты')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_toolkit(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        await ctx.respond(embed=ArbEmbed('Координация', f'***Ожидаем подтверждения последним действиями...***'))
        response = coordinator.supply_repair(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])


class InventoryManager(BasicCog):
    inv = discord.SlashCommandGroup("инвентарь", "Команды инвентаря")
    equipment = inv.create_subgroup('экипировать', 'Команды экипировки')

    async def clothes(ctx: discord.AutocompleteContext):
        from ArbItems import Inventory
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        inventory = Inventory.get_inventory_by_character(character)
        clothes_list = inventory.get_items_by_class('Одежда')
        return [f'{item.item_id} - {item.label}' for item in clothes_list]

    async def weapons(ctx: discord.AutocompleteContext):
        from ArbItems import Inventory
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        inventory = Inventory.get_inventory_by_character(character)
        clothes_list = inventory.get_items_by_class('Оружие')
        return [f'{item.item_id} - {item.label}' for item in clothes_list]

    async def items(ctx: discord.AutocompleteContext):
        from ArbItems import Inventory
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        inventory = Inventory.get_inventory_by_character(character)
        clothes_list = inventory.get_items_list()
        return [f'{item.item_id} - {item.label}' for item in clothes_list]

    async def equiped_items(ctx: discord.AutocompleteContext):
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        inventory = CharacterEquipment(character)
        items = inventory.get_equiped_items()
        return [f'{item.item_id} - {item.label}' for item in items]

    async def get_targets_to_use(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbGroups import Group
        from ArbBattle import Actor

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        if not Actor(character, data_manager=db).battle_id:
            group_members = Group.find_group_members_including(character)
            return [f'{member} - {Character(character, data_manager=db).name}' for member in group_members]
        else:
            print('тут')
            actor = Actor(character, data_manager=db)

            nearby_actors = db.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {actor.battle_id} AND layer_id = {actor.layer_id}')
            print(nearby_actors)
            return [f'{member.get("character_id")} - {Character(member.get("character_id"), data_manager=db).name}' for member in nearby_actors]

    @equipment.command(name='надеть')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __equip_clothes(self, ctx,
                              item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(clothes), required=False),
                              character_id: int = None):

        from ArbItems import Item, Inventory
        from ArbItems import CharacterEquipment

        if not item:
            inventory = Inventory.get_inventory_by_character(character_id)
            desc = ''
            for cloth in inventory.get_items_by_class('Одежда'):
                desc += f'- ||``{cloth.item_id}``|| *{cloth.__str__()}*\n'
            embed = ArbEmbed('Одежда в инвентаре', desc)
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        item = int(item.split(' ')[0])
        equipment = CharacterEquipment(character_id)
        equipment.equip_cloth(item)

        embed = SuccessEmbed(f'{Item(item).label} экипирован',
                             f'***{Character(character_id).name}** экипировал **{Item(item).label}***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @equipment.command(name='взять-оружие')
    @BasicCog.character_required
    async def __equip_weapon(self, ctx,
                              item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(weapons), required=False),
                              character_id: int = None):

        from ArbItems import Inventory, Item
        from ArbItems import CharacterEquipment

        if not item:
            inventory = Inventory.get_inventory_by_character(character_id)
            desc = ''
            for cloth in inventory.get_items_by_class('Оружие'):
                desc += f'- ||``{cloth.item_id}``|| *{cloth.__str__()}*\n'
            embed = ArbEmbed('Оружие в инвентаре', desc)
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        item = int(item.split(' ')[0])
        equipment = CharacterEquipment(character_id)
        equipment.equip_weapon(item)

        embed = SuccessEmbed(f'{Item(item).label} экипирован',
                             f'***{Character(character_id).name}** экипировал **{Item(item).label}***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @equipment.command(name='выбросить')
    @BasicCog.character_required
    async def __lost_item(self, ctx,
                          item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(items), required=False),
                          character_id: int = None):
        from ArbItems import Inventory, Item
        if not item:
            inventory = Inventory.get_inventory_by_character(character_id)
            desc = ''
            for cloth in inventory.get_items_list():
                desc += f'- ||``{cloth.item_id}``|| *{cloth.__str__()}*\n'
            embed = ArbEmbed('Инвентарь', desc)
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        item = int(item.split(' ')[0])
        equipment = CharacterEquipment(character_id)
        equipment.unequip_item(item)


        embed = ErrorEmbed(f'{Item(item).label} выброшен из инвентаря',
                             f'***{Character(character_id).name}** выбросил из инвентаря **{Item(item).label}***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        inventory = Inventory.get_inventory_by_character(character_id)
        inventory.delete_item(item)

        await ctx.respond(embed=embed)

    @equipment.command(name='снять')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __unequip(self, ctx,
                        item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(equiped_items), required=False),
                        character_id: int = None):

        from ArbItems import Item, Inventory
        from ArbItems import CharacterEquipment

        if not item:
            inventory = Inventory.get_inventory_by_character(character_id)
            desc = ''
            for cloth in inventory.get_items_by_class('Одежда'):
                desc += f'- ||``{cloth.item_id}``|| *{cloth.__str__()}*\n'
            embed = ArbEmbed('Одежда в инвентаре', desc)
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed)
            return

        item = int(item.split(' ')[0])
        equipment = CharacterEquipment(character_id)
        equipment.unequip_item(item)

        embed = SuccessEmbed(f'{Item(item).label} снят',
                             f'***{Character(character_id).name}** снял с себя **{Item(item).label}***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @equipment.command(name='снять-всё')
    @BasicCog.admin_required
    @BasicCog.not_in_battle
    async def __unequip_all(self, ctx, character_id: int = None):
        equipment = CharacterEquipment(character_id)
        items = equipment.get_equiped_items()
        for item in items:
            equipment.unequip_item(item.item_id)

        embed = SuccessEmbed('Снаряжение снято',
                             f'***{Character(character_id).name}** снял с себя всё снаряжение***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
        await ctx.respond(embed=embed)

    @equipment.command(name='выбрать-всё')
    @BasicCog.admin_required
    @BasicCog.not_in_battle
    async def __lost_all_items(self, ctx, character_id: int = None):
        from ArbItems import Inventory, CharacterEquipment

        equipment = CharacterEquipment(character_id)
        equiped_items = equipment.get_equiped_items()
        for item in equiped_items:
            equipment.unequip_item(item.item_id)

        inventory = Inventory.get_inventory_by_character(character_id)
        items = inventory.get_items_list()
        for item in items:
            inventory.delete_item(item.item_id)

        embed = SuccessEmbed('Снаряжение выброшено',
                             f'***{Character(character_id).name}** выбросило всё снаряжение***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
        await ctx.respond(embed=embed)


    @inv.command(name='использовать-предмет')
    @BasicCog.character_required
    async def __use_item(self, ctx,
                         item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(items), required=True),
                         target: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_targets_to_use), required=False),
                         character_id: int = None):
        from ArbItems import Item, UsableItem


        item_id = BasicCog.prepare_id(item)
        usage = UsableItem(Item(item_id))

        target_id = BasicCog.prepare_id(target) if target else character_id

        respond = usage.use(target_id)

        embeds = respond.get_embeds()
        view = Paginator(embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)




class CharacterSkills(BasicCog):
    skill = discord.SlashCommandGroup("навыки", "Команды управления навыками")

    async def character_skills(ctx: discord.AutocompleteContext):
        from ArbSkills import Skill
        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        skills = Skill.get_skills(character)
        return [skill.label for skill in skills]

    @skill.command(name='навыки-персонажа')
    @BasicCog.character_required
    async def __get_skills(self, ctx, character_id: int = None):
        from ArbSkills import Skill
        from ArbCharacters import CharacterProgress

        skills = Skill.get_skills(character_id)
        total_text = ''
        for skill in skills:
            total_text += f'{skill.__str__()}\n\n'

        character_progress = CharacterProgress(character_id)
        total_text += f'\n-# *Опыт ожидающий распределения: **{character_progress.skills_exp} exp.***\n' \
                      f'-# *Очков навыка для распределения: **{character_progress.skills_points} ОН.***\n' \
                      f'-# *Очков профессионализма для распределения: **{character_progress.skills_mods} ОП.***'

        embed = ArbEmbed(f'Список навыков {Character(character_id).name}', total_text)

        await ctx.respond(embed=embed)

    @skill.command(name='улучшить-навык')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __skill_upgrade(self, ctx,
                              skill: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('SKILL_INIT', 'label'))),
                              exp: discord.Option(float, required=False),
                              skill_points: discord.Option(int, max_value=200, required=False),
                              talant: discord.Option(float, max_value=2, required=False),
                              mastery: discord.Option(float, max_value=2, required=False),
                              character_id: int = None):
        from ArbCharacters import Character, CharacterProgress
        from ArbSkills import Skill

        progress = CharacterProgress(character_id)
        skill_id = AAC.extract('SKILL_INIT', 'label', skill, 'id')
        old_skill = Skill(character_id, skill_id)
        if not old_skill.check_skill_record():
            old_skill.insert_skill()

        max_exp = progress.skills_exp
        max_points = progress.skills_points
        max_modifiers = progress.skills_mods

        character = Character(character_id)

        if exp:
            if exp > max_exp:
                embed = ErrorEmbed('Недостаточно очков опыта',
                                   f'У **{character.name}** недостаточно очков опыта для прокачки **{skill}**',
                                   footer=f'Доступно опыта: {max_exp} exp.')

                await ctx.respond(embed=embed)

            progress.spend_exp_on_skill(skill_id, exp)

        if skill_points:
            if skill_points > max_points:
                embed = ErrorEmbed('Недостаточно очков навыков',
                                   f'У **{character.name}** недостаточно очков навыков для прокачки **{skill}**',
                                   footer=f'Доступно очков навыков: {max_points} ОН.')

                await ctx.respond(embed=embed)

            if skill_points + old_skill.lvl >= 200:
                skill_points = 200 - old_skill.lvl

            progress.spend_skill_points(skill_id, skill_points)

        if talant:
            if talant > max_modifiers:
                embed = ErrorEmbed('Недостаточно очков профессионализма',
                                   f'У **{character.name}** недостаточно очков профессионализма для прокачки таланта **{skill}**',
                                   footer=f'Доступно очков профессионализма: {max_modifiers} ОП.')

                await ctx.respond(embed=embed)

            if talant + old_skill.talant >= 2:
                talant = 2 - old_skill.talant

            progress.spend_talent_points(skill_id, talant)

        if mastery:
            if mastery > max_modifiers:
                embed = ErrorEmbed('Недостаточно очков профессионализма',
                                   f'У **{character.name}** недостаточно очков профессионализма для прокачки мастерства **{skill}**',
                                   footer=f'Доступно очков профессионализма: {max_modifiers} ОП.')

                await ctx.respond(embed=embed)

            if mastery + old_skill.mastery >= 2:
                mastery = 2 - old_skill.mastery

            progress.spend_mastery_points(skill_id, mastery)

        new_skill = Skill(character_id, skill_id)
        embed = SuccessEmbed(f'Прокачка навыка {skill}',
                             f'***Уровень:** {old_skill.lvl} -> {new_skill.lvl}*\n'
                             f'***Талант:** {old_skill.talant} -> {new_skill.talant}*\n'
                             f'***Мастерство:** {old_skill.mastery} -> {new_skill.mastery}*\n'
                             f'***Опыт навыка:** {old_skill.exp} -> {new_skill.exp}*\n\n'
                             f'{new_skill.__str__()}\n\n'
                             f'-# **Осталось:**\n'
                             f'-# Очков опыта: {progress.skills_exp} exp.\n'
                             f'-# Очков навыков: {progress.skills_points} ОН\n'
                             f'-# Очков профессионализма: {progress.skills_mods} ОП.')

        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        await ctx.respond(embed=embed)




class CharacterLocations(BasicCog):

    loc = discord.SlashCommandGroup('локации', 'Команды локации')
    loc_info = loc.create_subgroup('сведения', 'Команды инфомрации о локациях')
    loc_move = loc.create_subgroup('перемещение', 'Команды перемещения между локациями')
    loc_trade = loc.create_subgroup('торговля', 'Команды торговли')
    loc_borrow = loc.create_subgroup('интендант', 'Команды интенданта')
    loc_heal = loc.create_subgroup('медицина', 'Команды медицины')

    async def trader_assort(ctx: discord.AutocompleteContext):
        from ArbVendors import VendorObject
        from ArbItems import ItemTranslate

        choosen_trader = ctx.options.get('trader')
        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{choosen_trader}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)
        vendor_items = []
        for item_id in vendor.get_items().values():
            vendor_items.extend(item_id)

        return [ItemTranslate(item_label, data_manager=db).translation for item_label in vendor_items]

    async def healer_assort(ctx: discord.AutocompleteContext):
        from ArbVendors import MedicineVendor
        from ArbItems import ItemTranslate

        choosen_trader = ctx.options.get('healer')
        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{choosen_trader}"')[0].get('id')
        vendor = MedicineVendor(vendor_id, data_manager=db)
        vendor_items = vendor.get_items().get('implants', [])

        return [ItemTranslate(item_label, data_manager=db).translation for item_label in vendor_items]

    async def traders(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbLocations import CharacterLocation

        if not ctx.options.get('character_id'):
            author_character = Player(ctx.interaction.user.id).current_character
        else:
            author_character = ctx.options.get('character_id')

        traders_on_location = [trader.label for trader in CharacterLocation(author_character).location.get_objects().get('Торговец')]
        return traders_on_location

    async def intendants(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbLocations import CharacterLocation

        if not ctx.options.get('character_id'):
            author_character = Player(ctx.interaction.user.id).current_character
        else:
            author_character = ctx.options.get('character_id')

        traders_on_location = [trader.label for trader in
                               CharacterLocation(author_character).location.get_objects().get('Интендант')]
        return traders_on_location

    async def healers(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbLocations import CharacterLocation

        if not ctx.options.get('character_id'):
            author_character = Player(ctx.interaction.user.id).current_character
        else:
            author_character = ctx.options.get('character_id')

        traders_on_location = [trader.label for trader in
                               CharacterLocation(author_character).location.get_objects().get('Медицина')]
        return traders_on_location

    async def intendant_assort(ctx: discord.AutocompleteContext):
        from ArbVendors import VendorObject
        from ArbItems import ItemTranslate

        choosen_trader = ctx.options.get('intendant')
        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{choosen_trader}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)
        vendor_items = []
        for item_id in vendor.get_items().values():
            vendor_items.extend(item_id)

        return [ItemTranslate(item_label, data_manager=db).translation for item_label in vendor_items]

    async def qualities(ctx: discord.AutocompleteContext):
        db = DataManager()
        return [quality.get("name") for quality in db.select_dict('QUALITY_INIT')]

    async def item_available_materials(ctx: discord.AutocompleteContext):
        from ArbVendors import VendorObject
        from ArbItems import ItemTranslate
        from ArbGenerator import ItemManager

        choosen_trader = ctx.options.get('intendant')
        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{choosen_trader}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)
        vendor_tier = vendor.max_tier

        item_name = ctx.options.get('item')
        item_id = ItemTranslate.find_id_by_name(item_name)

        item_material_type = ItemManager(item_id).get_material_type()
        available_materials = db.select_dict('MATERIALS', filter=f'type = "{item_material_type}" AND tier <= {vendor_tier}')

        return [material.get('name') for material in available_materials]

    async def location_choices(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbLocations import CharacterLocation, Location

        if not ctx.options.get('character_id'):
            author_character = Player(ctx.interaction.user.id).current_character
        else:
            author_character = ctx.options.get('character_id')

        current_location_connections = CharacterLocation(author_character).location.process_connections()
        total_choices = []
        for loc in current_location_connections:
            con = Location(loc.loc_id)
            total_choices.append(f'{con.label}')

        return total_choices

    async def items(ctx: discord.AutocompleteContext):
        from ArbItems import Inventory
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        inventory = Inventory.get_inventory_by_character(character)
        clothes_list = inventory.get_items_list()
        return [f'{item.item_id} - {item.label}' for item in clothes_list]

    async def bodyparts(ctx: discord.AutocompleteContext):
        from ArbHealth import Body, ImplantType
        from ArbItems import ItemTranslate
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        implant = ctx.options['implant']
        db = DataManager()
        implant_id = ItemTranslate.find_id_by_name(implant, db)
        implant_type = ImplantType(implant_id, data_manager=db)

        if not character:
            character = Player(author, data_manager=db).current_character

        body = Body(character, data_manager=db).get_body_elements()
        total_elements = [f'{e.element_id} - {e.label}' for e in body if (not e.check_if_replaced_with_implant()) and (e.type == implant_type.install_slot)]

        return total_elements

    async def implants(ctx: discord.AutocompleteContext):
        from ArbHealth import Body, Implant
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        body = db.select_dict('CHARS_BODY', filter=f'id = {character}')
        total_elements = [f'{i.get("imp_id")} - {Implant(i.get("imp_id")).label}' for i in body]
        return total_elements

    async def viewed_locations(ctx: discord.AutocompleteContext):
        from ArbLocations import CharacterLocation, Location
        from ArbCore import Player

        character_id = ctx.options.get('character_id')
        if not character_id:
            character_id = Player(ctx.interaction.user.id).current_character

        dislocation = CharacterLocation(character_id)

        filtered_locations = dislocation.get_all_viewed_locations()

        return [f'{loc.label}' for loc in filtered_locations]

    def get_viewed_locations(self, character_id:int):
        from ArbLocations import CharacterLocation, Location
        dislocation = CharacterLocation(character_id)

        all_locations = dislocation.graph_all_locations()
        filtered_locations = [loc for loc in all_locations if Location(loc).is_location_viewed(character_id)]
        get_dislocation_connections = [loc.loc_id for loc in dislocation.location.process_connections()]
        get_connections_connections = []
        for loc in get_dislocation_connections:
            for con in Location(loc).process_connections():
                get_connections_connections.append(con.loc_id)

        total_locs = filtered_locations + get_dislocation_connections + get_connections_connections
        total_locs = list(set(total_locs))
        return [Location(loc) for loc in total_locs]

    @loc_info.command(name='регион')
    @BasicCog.character_required
    async def __what_region(self, ctx, character_id:int=None):
        from ArbLocations import Cluster, Location, CharacterLocation
        from ArbUtils.ArbTimedate import TimeManager
        from ArbOrgs import Organization
        from ArbBattle import Weather, DayTime

        location = CharacterLocation(character_id)
        if not location.location.cluster:
            embed = ArbEmbed('Регион неизвестен', '-# Регион персонажа неизвестен, вы находитесь в какой-то глуши и не можете соориентироваться в пространстве')
            await ctx.respond(embed=embed)
            return

        cluster = location.location.cluster
        weather = Weather(cluster.weather)
        time = DayTime(cluster.time) if cluster.time else DayTime(TimeManager().get_current_time_condition())
        locations = [loc for loc in cluster.get_locations() if loc.is_location_viewed(character_id)]
        print(locations)
        owners = {}
        for loc in locations:
            if loc.owner not in owners:
                owners[loc.owner] = []
            owners[loc.owner].append(loc)

        locations_count = len(locations)
        owners_power = {}
        for owner in owners.keys():
            locs = owners.get(owner)
            owners_power[owner] = round(len(locs) / locations_count, 1)

        owners_desc = ''
        for owner in owners_power.keys():
            power = owners_power.get(owner)
            owners_desc += f'*- {Organization(owner).label if owner else "Независимые"}: **{power * 100}%***\n'

        main_embed = ArbEmbed(f'{cluster.label}',
                              f'> ***Время:** {time.label} ({TimeManager().current_time()})*\n'
                            f'> ***Погода:** {weather.label}*\n'
                            f'> ***Температура:** {22 + weather.temperature + time.temperature:+}*\n'
                            f'> ***Сила ветра:** {round(weather.wind_speed*0.465, 1)} м/с*', logo_url=cluster.picture, picture=cluster.map)

        owners_embed = ArbEmbed(f'{cluster.label} | Контроль организаций', f'{owners_desc}')
        view = Paginator([main_embed, owners_embed], ctx, {1: 'Основная информация', 2: 'Организации'})
        await view.update_button()
        await ctx.respond(embed=main_embed, view=view)

    @loc_info.command(name='локации-региона')
    @BasicCog.character_required
    async def __region_locations(self, ctx, character_id:int=None):
        from ArbLocations import CharacterLocation

        location = CharacterLocation(character_id)
        region = location.location.cluster

        filtered_locations = [loc for loc in region.get_locations() if loc.is_location_viewed(character_id)]

        text = []
        for loc in filtered_locations:
            text.append(f'- *{loc.type.label} **{loc.label}***\n - -# *Владелец: **{loc.get_owner().label if loc.owner else "Независимые"}***\n\n')

        if not text:
            embed = ArbEmbed('Локации региона не найдены', '-# В регионе нет ни одной видимой локации')
            await ctx.respond(embed=embed)
            return

        chunked_text = ListChunker(10, text)
        embeds = []
        for chunk in chunked_text:
            embed = ArbEmbed(f'Локации региона ({region.label})', "".join(chunk), picture=region.map)
            embeds.append(embed)

        view = Paginator(embeds, ctx, ignore_footer=True)
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @loc_info.command(name='путь-до-локации')
    @BasicCog.character_required
    async def __path_finder(self, ctx, location: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(viewed_locations)), character_id:int=None):
        from ArbLocations import CharacterLocation, Location

        dislocation = CharacterLocation(character_id)
        end_id = ArbAutoComplete.extract('LOC_INIT', 'label', location, 'id')
        if dislocation.location.id == end_id:
            embed = ArbEmbed('Путь', '-# Вы уже находитесь на выбранной локации, вам не нужно искать дорогу')
            await ctx.respond(embed=embed)
            return

        filtered_locations = [loc.id for loc in dislocation.get_all_viewed_locations()]

        if end_id not in filtered_locations:
            embed = ArbEmbed('Путь не найден', '-# Путь из текущей локации в указанную не найден')
            await ctx.respond(embed=embed)
            return

        shortest_way = dislocation.find_shortest_path(end_id)
        if not shortest_way:
            embed = ArbEmbed('Путь не найден', '-# Путь из текущей локации в указанную не найден')
            await ctx.respond(embed=embed)
            return

        total_locations = [Location(loc) for loc in shortest_way]
        location_names = [f'- {loc.type.label} **{loc.label}** ({loc.get_owner().label if loc.owner else "Независимые"})' for loc in total_locations if loc.id in filtered_locations]
        total_cost = sum([loc.cost for loc in total_locations])
        total_way = ''

        total_way += f'\n-# |\n-# v\n'.join(location_names)

        embed = ArbEmbed('Путь к локации', f'{total_way}', picture=total_locations[-1].picture, footer=f'Очков путешествия необходимо: {total_cost}')
        await ctx.respond(embed=embed)


    @loc_info.command(name='локация')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __where_am_i(self, ctx, character_id:int=None):
        from ArbLocations import CharacterLocation
        location = CharacterLocation(character_id)
        if not location.location:
            embed = ArbEmbed('Местоположение неизвестно', '-# Местоположение персонажа неизвестно, вы находитесь в какой-то глуши и не можете соориентироваться в пространстве')
            await ctx.respond(embed=embed)
            return

        location_tag = ' окрестностей' if not location.entered_location else ''

        location_description = location.describe_location()
        embed = ArbEmbed(f'Осмотр{location_tag} {location.location.label} ({location.location.type.label})', location_description,
                         footer=f'Владелец: {location.location.get_owner().label}', footer_logo=location.location.get_owner().picture, picture=location.location.picture)

        await ctx.respond(embed=embed)

    @loc.command(name='перейти-в')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    @BasicCog.is_group_leader_or_single
    async def __move_to_location(self, ctx,
                                 location: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(location_choices), required=False),
                                 character_id:int=None):
        from ArbLocations import CharacterLocation, Location

        char_loc = CharacterLocation(character_id)
        connections_desc = char_loc.describe_connections()
        near_locations = [loc.loc_id for loc in char_loc.location.process_connections()]
        location_id = ArbAutoComplete.extract('LOC_INIT', 'label', location, 'id')

        if not location_id or location_id not in near_locations:
            embed = ArbEmbed('Доступные для перемещения локации', connections_desc, footer=f'Доступно очков путешествия: {char_loc.movement_points}')
            await ctx.respond(embed=embed)
            return
        else:
            available_by_cost = char_loc.get_available_by_cost_locations().keys()
            if location_id not in available_by_cost:
                embed = ErrorEmbed('Путешествие невозможно',
                                   '-# У вас не хватает очков путешествия для перемещения на локацию!')
                await ctx.respond(embed=embed)
                return
            on_patrol = char_loc.move_to_location(location_id)
            if on_patrol:
                embed = ErrorEmbed('Патруль',
                                   f'*Вы идёте по окрестностям {char_loc.location.type.label.lower()} и натыкаетесь на **{on_patrol.label}** противника, которые застали вас в расплох. Начинается бой!*',
                                   footer=f'Владелец: {char_loc.location.get_owner().label}',
                                   footer_logo=char_loc.location.get_owner().picture)
                await ctx.respond(embed=embed)
                battle = char_loc.start_battle(on_patrol)
                await CharacterCombat(self.bot).battle_info(ctx, battle.battle_id, character_id)
                await CharacterCombat(self.bot).battle_teams(ctx, battle.battle_id, character_id)

            else:
                embed = SuccessEmbed('Перемещение в локацию', f'*{Location(location_id).cluster.move_desc} **{location} ({Location(location_id).type.label})***')
                await ctx.respond(embed=embed)

    @loc_move.command(name='войти-в-локацию')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    @BasicCog.is_group_leader_or_single
    async def __enter_location(self, ctx, character_id:int=None):
        from ArbLocations import CharacterLocation

        char_loc = CharacterLocation(character_id)
        if not char_loc.location:
            embed = ArbEmbed('Местоположение неизвестно', '-# Местоположение персонажа неизвестно, вы находитесь в какой-то глуши и не можете соориентироваться в пространстве')
            await ctx.respond(embed=embed)
            return

        on_patrol = char_loc.enter_location()
        if on_patrol:
            embed = ErrorEmbed('Патруль',
                             f'*Вы идёте по окрестностям {char_loc.location.type.label.lower()} и при приближении к **{char_loc.location.label}** вы натыкаетесь на **{on_patrol.label}** противника, которые застали вас в расплох. Начинается бой!*',
                             footer=f'Владелец: {char_loc.location.get_owner().label}',
                             footer_logo=char_loc.location.get_owner().picture)
            await ctx.respond(embed=embed)
            battle = char_loc.start_battle(on_patrol)
            await CharacterCombat(self.bot).battle_info(ctx, battle.battle_id, character_id)
            await CharacterCombat(self.bot).battle_teams(ctx, battle.battle_id, character_id)
            return

        embed = SuccessEmbed(f'Вход в локацию {char_loc.location.label} ({char_loc.location.type.label})',
                         f'*Вы идёте по окрестностям {char_loc.location.type.label.lower()} и входите в локацию **{char_loc.location.label}***',
                         footer=f'Владелец: {char_loc.location.get_owner().label}',
                         footer_logo=char_loc.location.get_owner().picture)

        await ctx.respond(embed=embed)

    @loc_move.command(name='покинуть-локацию')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    @BasicCog.is_group_leader_or_single
    async def __leave_location(self, ctx, character_id:int=None):
        from ArbLocations import CharacterLocation

        char_loc = CharacterLocation(character_id)
        if not char_loc.location:
            embed = ArbEmbed('Местоположение неизвестно',
                             '-# Местоположение персонажа неизвестно, вы находитесь в какой-то глуши и не можете соориентироваться в пространстве')
            await ctx.respond(embed=embed)
            return

        char_loc.leave_location()
        embed = ArbEmbed(f'Вы покидаете {char_loc.location.label} ({char_loc.location.type.label})',
                         f'*Вы покидаете **{char_loc.location.label}** и оказываетесь в её окрестностях, окрестностях {char_loc.location.type.label.lower()}*',
                         footer=f'Владелец: {char_loc.location.get_owner().label}',
                         footer_logo=char_loc.location.get_owner().picture)

        await ctx.respond(embed=embed)

    @loc_trade.command(name='торговать')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __trade(self, ctx,
                      trader: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(traders), required=True),
                      item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(trader_assort), required=False),
                      character_id: int=None):
        from ArbLocations import CharacterLocation
        from ArbVendors import VendorObject
        from ArbGenerator import ItemManager
        from ArbItems import ItemTranslate, Inventory
        from ArbCore import Server

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        location = CharacterLocation(character_id)

        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{trader}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)

        if not item:
            items_desc = []
            for item, price in vendor.get_price().items():
                items_desc.append(f'- *{ItemTranslate(item).translation} {ct}{int(price):,d}*\n')

            items_chunks = ListChunker(20, items_desc)
            items_embeds = []
            for chunk in items_chunks:
                embed = ArbEmbed(f'Ассортимент {vendor.label} | {location.location.label}', ''.join(chunk))
                items_embeds.append(embed)

            view = Paginator(items_embeds, ctx, ignore_footer=True)
            await view.update_button()
            await ctx.respond(embed=items_embeds[0], view=view)
        else:
            item_id = ItemTranslate.find_id_by_name(item)
            vendor_assort = list(vendor.get_price().keys())
            if item_id not in vendor_assort:
                embed = ErrorEmbed('Такого предмета нет в ассортименте',
                                   f'-# Такого предмета в ассортименте **{vendor.label}** нет!',
                                   footer=f'Текущий баланс: {ct}{character.money}',
                                   footer_logo=character.picture)
                await ctx.respond(embed=embed)
                return

            item_price = vendor.get_item_price(item_id)
            result = character.spend_money(item_price)
            if result:
                inventory = Inventory.get_inventory_by_character(character_id, data_manager=db)
                ItemManager(item_id, inventory=inventory.inventory_id).spawn_item()
                embed = SuccessEmbed(f'Покупка в {vendor.label}', f'*Вы приобрели **{item}** в **{vendor.label}** за {ct}{int(item_price):,d}*',
                                     footer=f'Текущий баланс: {ct}{int(character.money):,d}',
                                     footer_logo=character.picture)
                await ctx.respond(embed=embed)
            else:
                embed = ErrorEmbed('Недостаточно средств', f'-# У вас недостаточно средств для покупки **{item}**!',
                                   footer=f'Текущий бюджет: {ct}{int(character.money):,d}',
                                   footer_logo=character.picture)
                await ctx.respond(embed=embed)

    @loc_borrow.command(name='одолжить')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __borrow(self, ctx,
                       intendant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(intendants), required=True),
                       item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(intendant_assort), required=False),
                       material: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(item_available_materials), required=False),
                       quality: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(qualities), required=False),
                       endurance: discord.Option(int, min_value=1, max_value=100, required=False),
                       character_id: int=None):
        from ArbLocations import CharacterLocation
        from ArbOrgs import Organization
        from ArbVendors import VendorObject
        from ArbGenerator import ItemManager
        from ArbItems import ItemTranslate, Inventory

        character = Character(character_id)
        location = CharacterLocation(character_id)

        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{intendant}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)
        org_id = location.location.owner
        org = Organization(org_id, data_manager=db) if org_id else Organization('Civil', data_manager=db)

        if not item:
            items_desc = []
            for item, price in vendor.get_price().items():
                items_desc.append(f'- *{ItemTranslate(item).translation} {price} очков репутации*\n')

            items_chunks = ListChunker(20, items_desc)
            items_embeds = []
            for chunk in items_chunks:
                embed = ArbEmbed(f'Ассортимент {vendor.label} {org.label}', ''.join(chunk))
                items_embeds.append(embed)

            view = Paginator(items_embeds, ctx, ignore_footer=True)
            await view.update_button()
            await ctx.respond(embed=items_embeds[0], view=view)
        else:
            material_factor = AAC.extract('MATERIALS', 'name', material, 'market_value') * 0.0008 if material else 1
            quality_factor = AAC.extract('QUALITY_INIT', 'name', quality, 'value_factor') if quality else 1
            endurance_factor = round(endurance / 50, 1) if endurance else 1

            item_id = ItemTranslate.find_id_by_name(item)
            item_price = vendor.get_item_price(item_id) * material_factor * quality_factor * endurance_factor

            print(item_id, 'ЦЕНА: ', item_price)

            vendor_assort = list(vendor.get_price().keys())
            if item_id not in vendor_assort:
                embed = ErrorEmbed('Такого предмета нет в ассортименте', f'-# Такого предмета в ассортименте **{vendor.label}** нет!',
                                 footer=f'екущая репутация {org.label}: {org.get_character_reputation(character_id)} очков репутации',
                                 footer_logo=character.picture)
                await ctx.respond(embed=embed)
                return
            result = character.spend_reputation(org_id, item_price)
            if result:
                inventory = Inventory.get_inventory_by_character(character_id, data_manager=db)
                ItemManager(item_id, inventory=inventory.inventory_id,
                            material=AAC.extract('MATERIALS', 'name', material, 'id') if material else None,
                            quality=quality if quality else None,
                            endurance=endurance if endurance else None).spawn_item()
                embed = SuccessEmbed(f'Получение снаряжения {vendor.label} {org.label}',
                                     f'*Вы получили **{item}** у **{vendor.label} {org.label}** за **{item_price} очков репутации***',
                                     footer=f'Текущая репутация: {org.get_character_reputation(character_id)}%',
                                     footer_logo=character.picture)
                await ctx.respond(embed=embed)
            else:
                embed = ErrorEmbed('Недостаточно репутации', f'-# У вас недостаточно репутации у **{org.label}** для получения **{item}**!',
                                   footer=f'Текущая репутация {org.label}: {org.get_character_reputation(character_id)}%',
                                   footer_logo=character.picture)
                await ctx.respond(embed=embed)

    @loc_borrow.command(name='пожертвовать')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __donate(self, ctx,
                       intendant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(intendants), required=True),
                       item: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(items)),
                       character_id: int=None):
        from ArbLocations import CharacterLocation
        from ArbOrgs import Organization
        from ArbVendors import VendorObject
        from ArbItems import Item

        character = Character(character_id)
        location = CharacterLocation(character_id)

        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{intendant}"')[0].get('id')
        vendor = VendorObject(vendor_id, data_manager=db)
        org_id = location.location.owner
        org = Organization(org_id, data_manager=db) if org_id else Organization('Civil', data_manager=db)

        item_id = BasicCog.prepare_id(item)
        item_price = vendor.get_item_donate_price(item_id, character_id)


        org.change_reputation(character_id, item_price)
        Item(item_id).delete_item()
        embed = SuccessEmbed(f'Снаряжение пожертвовано {org.label}',
                             f'***{item}** был пожертвован **{vendor.label} {org.label}** за **{item_price} очков репутации***',
                             footer=f'Текущая репутация: {org.get_character_reputation(character_id)}%',
                             footer_logo=character.picture)
        await ctx.respond(embed=embed)

    @loc_heal.command(name='установить-имплант')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __set_implant(self, ctx,
                            healer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(healers), required=True),
                            implant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(healer_assort), required=True),
                            place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(bodyparts)),
                            character_id: int=None):
        from ArbLocations import CharacterLocation
        from ArbOrgs import Organization
        from ArbVendors import MedicineVendor
        from ArbItems import ItemTranslate
        from ArbHealth import Implant
        from ArbCore import Server

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        location = CharacterLocation(character_id)

        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{healer}"')[0].get('id')
        vendor = MedicineVendor(vendor_id, data_manager=db)
        org_id = location.location.owner
        org = Organization(org_id, data_manager=db) if org_id else Organization('Civil', data_manager=db)

        price_tag = f' очков репутации' if vendor.type == 'Интендант' else ct
        character_balance = character.money if vendor.type == 'Торговец' else org.get_character_reputation(character_id)

        if not implant and place:
            items_desc = []
            for item, price in vendor.get_price().items():
                items_desc.append(f'- *{ItemTranslate(item).translation} {price}{price_tag}*\n')

            items_chunks = ListChunker(20, items_desc)
            items_embeds = []
            for chunk in items_chunks:
                embed = ArbEmbed(f'Ассортимент {vendor.label} {org.label}', ''.join(chunk))
                items_embeds.append(embed)

            view = Paginator(items_embeds, ctx, ignore_footer=True)
            await view.update_button()
            await ctx.respond(embed=items_embeds[0], view=view)
        else:

            item_id = ItemTranslate.find_id_by_name(implant)
            item_price = vendor.get_item_price(item_id)

            print(item_id, 'ЦЕНА: ', item_price, price_tag)

            vendor_assort = list(vendor.get_price().keys())
            if item_id not in vendor_assort:
                embed = ErrorEmbed('Такого импланта нет в ассортименте',
                                   f'-# Такого импланта в ассортименте **{vendor.label}** нет!',
                                   footer=f'Текущая средства: {character_balance}{price_tag}',
                                   footer_logo=character.picture)
                await ctx.respond(embed=embed)
                return
            result = character.spend_reputation(org_id, item_price) if vendor.type == 'Интендант' else character.spend_money(item_price)
            if result:
                Implant.create_implant(character_id, item_id, place.split(' ')[0])
                embed = SuccessEmbed(f'Установление импланта {vendor.label} {org.label}',
                                     f'*Вы установили **{implant}** у **{vendor.label} {org.label}** за **{item_price}{price_tag}***',
                                     footer=f'Текущие средства: {character_balance}%',
                                     footer_logo=character.picture)
                await ctx.respond(embed=embed)
            else:
                embed = ErrorEmbed('Недостаточно средств',
                                   f'-# У вас недостаточно средств у **{org.label}** для установки **{implant}**!',
                                   footer=f'Текущие средства: {character_balance}%',
                                   footer_logo=character.picture)
                await ctx.respond(embed=embed)

    @loc_heal.command(name='вырезать-имплант')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __delete_implant(self, ctx,
                            healer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(healers),
                                                   required=True),
                            implant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(implants),
                                                    required=True),
                            character_id: int = None):
        from ArbLocations import CharacterLocation
        from ArbOrgs import Organization
        from ArbVendors import MedicineVendor
        from ArbDamage import Damage
        from ArbHealth import Implant, BodyElement
        from ArbCore import Server

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        location = CharacterLocation(character_id)

        db = DataManager()
        vendor_id = db.select_dict('LOC_OBJECTS_INIT', filter=f'label = "{healer}"')[0].get('id')
        vendor = MedicineVendor(vendor_id, data_manager=db)
        org_id = location.location.owner
        org = Organization(org_id, data_manager=db) if org_id else Organization('Civil', data_manager=db)

        price_tag = f' очков репутации' if vendor.type == 'Интендант' else ct
        character_balance = character.money if vendor.type == 'Торговец' else org.get_character_reputation(character_id)

        item_id = implant.split(' ')[0]
        print(item_id)
        item_price = vendor.get_item_donate_price(item_id, character_id)

        print(item_id, 'ЦЕНА: ', item_price, price_tag)

        character.change_reputation(org_id, item_price) if vendor.type == 'Интендант' else character.add_money(
            item_price)

        result = True
        if result:
            implant_obj = Implant(item_id, data_manager=db)
            place = implant_obj.place
            Implant.delete_implant(int(item_id))
            element = BodyElement(character_id, place, data_manager=db)
            element.apply_damage(Damage(element.max_health, 'SurgicalCut', 1000, root='Хирургическая операция'))

            embed = SuccessEmbed(f'Удаление импланта {vendor.label} {org.label}',
                                 f'*Вы удалили **{implant}** у **{vendor.label} {org.label}** и получили **{item_price}{price_tag}***',
                                 footer=f'Текущие средства: {character_balance}%',
                                 footer_logo=character.picture)
            await ctx.respond(embed=embed)
        else:
            embed = ErrorEmbed('Недостаточно средств',
                               f'-# У вас недостаточно средств у **{org.label}** для установки **{implant}**!',
                               footer=f'Текущие средства: {character_balance}%',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)




class CharacterGroup(BasicCog):
    group = discord.SlashCommandGroup('группа', 'Команды группы')
    group_info = group.create_subgroup('сведения', 'Сведения о группе')
    group_mng = group.create_subgroup('управление', 'Управление группйо')

    async def group_members(ctx: discord.AutocompleteContext):
        from ArbGroups import Group
        from ArbCore import Player

        character = Character(Player(ctx.interaction.user.id).current_character)
        group = Group.find_group_by_character_id(character.id)
        group_members = [member.get('id') for member in group.fetch_group_members()]
        member_names = []
        for member_id in group_members:
            if member_id != character.id:
                member_names.append(Character(member_id).name)

        return member_names

    async def group_roles(ctx: discord.AutocompleteContext):
        from ArbGroups import GroupRole, Group

        character = Character(Player(ctx.interaction.user.id).current_character)
        group = Group.find_group_by_character_id(character.id)

        character_role = GroupRole(group.get_member_role(character.id))
        if character_role.id == 'Manager':
            roles_list = [role.get('label') for role in DataManager().select_dict('GROUP_ROLES')]
        elif character_role.is_leader:
            roles_list = [role.get('label') for role in DataManager().select_dict('GROUP_ROLES') if role.get('is_leader') in [0, None]]
        else:
            roles_list = [role.get('label') for role in DataManager().select_dict('GROUP_ROLES') if role.get('is_leader') in [0, None]]

        return roles_list


    @group_mng.command(name='изгнать-из-группы')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __banish(self, ctx,
                       member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(group_members)),
                       character_id: int=None):
        from ArbGroups import Group, GroupRole
        from ArbCharacters import Character

        character = Character(character_id)
        group = Group.find_group_by_character_id(character.id)
        if not group:
            embed = ErrorEmbed('Отряд не найден', f'-# **{character.name}** не является членом какого-либо отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        role = GroupRole(group.get_member_role(character_id))
        if not role.is_leader and group.owner_id != character_id:
            embed = ErrorEmbed('Недостаточно прав', f'-# Только лидер или управляющий может выгнать члена отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        member_id = AAC.extract('CHARS_INIT', 'name', member, 'id')
        group.delete_member(member_id)
        member = Character(member_id)

        embed = SuccessEmbed(f'Изгнание из отряда "{group.label}"',
                             f'*Персонаж **{GroupRole(group.get_member_role(character_id)).label} {character.name}** изгнал из отряда **{group.label}** персонажа **{member.name}**.*')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)

    @group_mng.command(name='пригласить-в-группу')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __group_invite(self, ctx, member: discord.Option(discord.SlashCommandOptionType.user),
                             character_id: int=None):
        from ArbCore import Player
        from ArbGroups import Group, GroupRole
        from ArbCharacters import Character

        character = Character(character_id)
        group = Group.find_group_by_character_id(character_id)

        if Player(member.id).current_character is None:
            embed = ErrorEmbed('Приглашение', f'-# *Выбранный игрок {member.mention} не управляет персонажем*')
            await ctx.respond(embed=embed)
            return

        if not group:
            embed = ArbEmbed('Отряд отсутствует',
                             f'-# *Персонаж **{character.name}** не является членом какого-либо отряда*')
            await ctx.respond(embed=embed)
            return

        role = GroupRole(group.get_member_role(character_id))
        if not role.can_invite:
            embed = ErrorEmbed('Недостаточно прав', f'-# У вас недостаточно полномочий чтобы пригласить новых членов отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        embed = ArbEmbed('Приглашение отправлено :clock4:', f'-# Ожидаем решение персонажа...')
        waiting_message = await ctx.respond(embed=embed)

        result = await group.send_invite(ctx, member.id)
        if result.custom_id == 'Accept':
            player = Player(member.id)
            player_character = player.current_character

            group.add_member(player_character)

            await waiting_message.delete_original_response()
            embed = SuccessEmbed('Приглашение',
                                 f'***{role.label} {character.name}** пригласил **{Character(player_character).name}** в отряд **{group.label}***')
            await ctx.send(embed=embed)
        else:
            await waiting_message.delete_original_response()
            embed = ErrorEmbed('Приглашение', f'-# *Приглашение в организацию **{group.label}** отклонено*')
            await ctx.send(embed=embed)

    @group_mng.command(name='распустить-группу')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __group_disband(self, ctx, character_id: int=None):
        from ArbGroups import Group, GroupRole
        from ArbCharacters import Character

        character = Character(character_id)
        group = Group.find_group_by_character_id(character_id)
        if not group:
            embed = ErrorEmbed('Отряд не найден', f'-# **{character.name}** не является членом какого-либо отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        role = GroupRole(group.get_member_role(character_id))
        if group.owner_id != character_id:
            embed = ErrorEmbed('Недостаточно прав', f'-# У вас недостаточно полномочий чтобы расформировать отряд.',
                               footer=character.name,
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        group.disband()
        embed = SuccessEmbed(f'Отряд "{group.label}" расформирован',
                             f'***{role.label} {character.name}** расформировал отряд **{group.label}***')
        embed.set_author(character.name, icon_url=character.picture)
        await ctx.respond(embed=embed)

    @group_info.command(name='сведения-о-группе')
    @BasicCog.character_required
    async def __group_info(self, ctx, character_id: int=None):
        from ArbGroups import Group, GroupRole
        from ArbOrgs import Organization
        from ArbLocations import CharacterLocation

        character = Character(character_id)
        group = Group.find_group_by_character_id(character_id)
        if not group:
            embed = ErrorEmbed('Отряд не найден', f'-# **{character.name}** не является членом какого-либо отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        group_desc = ArbEmbed(f'Отряд "{group.label}"',
                              group.text_info(),
                              footer=f'Членов отряда: {len(group.fetch_group_members())}',
                              footer_logo=character.picture)

        group_members = ArbEmbed(f'Участники отряда "{group.label}"',
                                 group.text_members(),
                                 footer=f'Членов отряда: {len(group.fetch_group_members())}',
                                 footer_logo=character.picture)

        embeds = [group_desc, group_members]
        view = Paginator(embeds, ctx, ignore_footer=False, page_names={1: 'Информация', 2: 'Участники'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @group_mng.command(name='установить-роль')
    @BasicCog.character_required
    @BasicCog.not_in_battle
    async def __set_role(self, ctx,
                         role: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(group_roles)),
                         member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(group_members)),
                         character_id: int=None):
        from ArbGroups import Group, GroupRole
        from ArbCharacters import Character
        character = Character(character_id)
        group = Group.find_group_by_character_id(character_id)
        if not group:
            embed = ErrorEmbed('Отряд не найден', f'-# **{character.name}** не является членом какого-либо отряда.',
                               footer=f'{character.name}',
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        character_role = GroupRole(group.get_member_role(character_id))
        if not character_role.is_leader:
            embed = ErrorEmbed('Недостаточно прав', f'-# У вас недостаточно полномочий чтобы изменить роль члена отряда.',
                               footer=character.name,
                               footer_logo=character.picture)
            await ctx.respond(embed=embed)
            return

        new_role = GroupRole(AAC.extract('GROUP_ROLES', 'label', role, 'id'))
        member = AAC.extract('CHARS_INIT', 'name', member, 'id')
        group.set_member_role(member, new_role.id)

        embed = SuccessEmbed('Роль изменена',
                             f'-# **{character_role.label} {character.name}** изменил роль участника **{Character(member).name}** в отряде **{group.label}** на **{new_role.label}**')
        embed.set_author(character.name, icon_url=character.picture)
        await ctx.respond(embed=embed)








class CharacterOrganization(BasicCog):
    org = discord.SlashCommandGroup("организация", 'Команды организации')
    org_info = org.create_subgroup('сведения', 'Информация об организации')
    org_mng = org.create_subgroup('управление', 'Управление организацией')
    org_group = org.create_subgroup('отряд', 'Управление отрядом')

    async def ranks(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbOrgs import Organization, Rank

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        data = db.select_dict('CHARS_INIT', filter=f'id = {character}')[0]
        org = data.get('org')
        org_lvl = data.get('org_lvl')
        rank_lvl = Rank(org_lvl, data_manager=db).power_rank

        all_ranks = Organization(org, data_manager=db).get_inherited_ranks()
        print('тут', org, org_lvl, all_ranks)
        lower_ranks = [Rank(rank, data_manager=db).label for rank in all_ranks if Rank(rank, data_manager=db).power_rank < rank_lvl]
        print(lower_ranks)

        return lower_ranks

    async def org_members(ctx: discord.AutocompleteContext):
        from ArbOrgs import Rank, Organization
        from ArbCore import Player

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        data = db.select_dict('CHARS_INIT', filter=f'id = {character}')[0]
        org = data.get('org')
        org_lvl = data.get('org_lvl')
        rank_lvl = Rank(org_lvl, data_manager=db).power_rank

        total_members = []
        for member in Organization(org, data_manager=db).get_included_members():
            member_data = db.select_dict('CHARS_INIT', filter=f'id = {member}')[0]
            member_rank = Character(member, data_manager=db).org_lvl
            if not member_rank:
                print(member_data.get('name'))
                total_members.append(member_data.get('name'))
                continue
            member_lvl = Rank(member_rank, data_manager=db).power_rank
            if member_lvl < rank_lvl:
                total_members.append(member_data.get('name'))
            else:
                continue

        print(total_members)

        return total_members

    async def group_members(ctx: discord.AutocompleteContext):
        from ArbGroups import Group
        from ArbCharacters import Character

        group = ctx.options.get('group')
        db = DataManager()

        group_id = AAC.extract('GROUP_INIT', 'label', group, 'id')
        group = Group(group_id, data_manager=db)
        members = [member.get('id') for member in group.fetch_group_members()]

        return [Character(char_id, data_manager=db).name for char_id in members]

    async def get_org_groups(ctx: discord.AutocompleteContext):
        from ArbCore import Player
        from ArbOrgs import Organization

        author = ctx.interaction.user.id
        character = ctx.options['character_id']
        db = DataManager()

        if not character:
            character = Player(author, data_manager=db).current_character

        data = db.select_dict('CHARS_INIT', filter=f'id = {character}')[0]
        org = data.get('org')

        groups = db.select_dict('GROUP_INIT')
        print(groups)
        org_members = Organization(org).get_included_members()
        print(org_members)
        group_labels = []
        for owner in groups:
            if owner.get('owner_id') in org_members:
                group_labels.append(owner.get('label'))

        return group_labels

    @org_info.command(name='моя-организация')
    @BasicCog.character_required
    async def __org_main_info(self, ctx, character_id:int=None):
        from ArbOrgs import Organization
        from ArbCharacters import Character
        from ArbCore import Server
        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует', f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        org = Organization(org_id)
        main_embed = ArbEmbed(f'Информация об организации {org.label}',
                              f'{org.text_org_info()}' + f'> ***Бюджет:** {ct}{int(org.money):,d}*',
                              logo_url=org.picture)

        members_embeds = []
        org_members = ListChunker(20, org.text_org_members())
        for chunk in org_members:
            members_embeds.append(ArbEmbed(f'Члены организации {org.label} | Всего: {len(org.get_all_characters())}', ''.join(chunk)))

        print(members_embeds)

        total_embeds = [main_embed]
        total_embeds.extend(members_embeds)
        view = Paginator(total_embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=main_embed, view=view)

    @org_mng.command(name='пригласить-в-организацию')
    @BasicCog.character_required
    async def __org_join(self, ctx,
                         user: discord.Option(discord.SlashCommandOptionType.user, required=True),
                         character_id:int=None):
        from ArbOrgs import Organization, Rank
        from ArbCharacters import Character
        from ArbCore import Player

        character = Character(character_id)
        org_id = character.org
        rank_id = character.org_lvl

        if user.id == ctx.author.id:
            embed = ErrorEmbed('Приглашение', f'-# *Вы не можете пригласить самого себя в организацию*')
            await ctx.respond(embed=embed)
            return

        if Player(user.id).current_character is None:
            embed = ErrorEmbed('Приглашение', f'-# *Выбранный игрок {user.mention} не управляет персонажем*')
            await ctx.respond(embed=embed)
            return

        if not org_id:
            embed = ArbEmbed('Организация отсутствует', f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        rank = Rank(rank_id)
        if not rank.can_invite:
            embed = ErrorEmbed('Приглашение', f'-# *Вы не можете пригласить нового члена в свою организацию*')
            await ctx.respond(embed=embed)
            return

        org = Organization(org_id)
        embed = ArbEmbed('Приглашение отправлено :clock4:', f'-# Ожидаем решение персонажа...')
        waiting_message = await ctx.respond(embed=embed)

        result = await org.send_invite(ctx, user.id)
        if result.custom_id == 'Accept':
            player = Player(user.id)
            player_character = player.current_character
            org.character_invited(player_character)
            await waiting_message.delete_original_response()
            embed = SuccessEmbed('Приглашение', f'***{character.name}** пригласил **{Character(player_character).name}** в организацию **{org.label}***')
            await ctx.send(embed=embed)
        else:
            await waiting_message.delete_original_response()
            embed = ErrorEmbed('Приглашение', f'-# *Приглашение в организацию **{org.label}** отклонено*')
            await ctx.send(embed=embed)

    @org_mng.command(name='повысить')
    @BasicCog.character_required
    async def __org_promote(self, ctx,
                            rank:discord.Option(str, autocomplete=discord.utils.basic_autocomplete(ranks)),
                            member:discord.Option(str, autocomplete=discord.utils.basic_autocomplete(org_members)),
                            character_id:int=None):

        from ArbOrgs import Organization, Rank

        rank = ArbAutoComplete.extract('ORG_RANKS', 'label', rank, 'id')
        member_id = ArbAutoComplete.extract('CHARS_INIT', 'name', member, 'id')
        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует', f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(character.org_lvl).can_promote:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *Вы не можете повысить или понизить члена организации*')
            await ctx.respond(embed=embed)
            return

        db = DataManager()
        org = Organization(org_id, data_manager=db)

        member = Character(member_id, data_manager=db)
        member_owner = member.owner
        lowest_rank = org.get_random_lowest_rank()
        member_rank = Rank(member.org_lvl, data_manager=db) if member.org_lvl else Rank(lowest_rank, data_manager=db)
        is_promoted = member_rank.power_rank <= Rank(rank, data_manager=db).power_rank

        db.update('CHARS_INIT', {'org_lvl': rank}, f'id = {member_id}')

        if is_promoted:
            embed = SuccessEmbed(f'Повышение | {org.label}',
                                 f'***{Rank(character.org_lvl).label} {character.name}** повысил **{member.name}** до звания/должности **{Rank(rank).label}***')
            embed.set_author(character.name, icon_url=character.picture)
            embed.set_footer(ctx.author.display_name, ctx.author.avatar)
            await ctx.respond(embed=embed)
        else:
            embed = ErrorEmbed(f'Понижение | {org.label}',
                               f'***{Rank(character.org_lvl).label} {character.name}** понизил **{member.name}** до звания/должности **{Rank(rank).label}***')
            embed.set_author(character.name, icon_url=character.picture)
            embed.set_footer(ctx.author.display_name, ctx.author.avatar)
            await ctx.respond(embed=embed)


        if member_owner:
            member_user = ctx.bot.get_user(member_owner)
            if is_promoted:
                embed = SuccessEmbed(f'Повышение | {org.label}', f'***{Rank(character.org_lvl).label} {character.name}** повысил Вас, **{member.name}**, до звания/должности **{Rank(rank).label}***')
                embed.set_author(character.name, icon_url=character.picture)
                embed.set_footer(ctx.author.display_name, ctx.author.avatar)
                await member_user.send(embed=embed)

            else:
                embed = ErrorEmbed(f'Понижение | {org.label}', f'***{Rank(character.org_lvl).label} {character.name}** понизил Вас, **{member.name}**, до звания/должности **{Rank(rank).label}***')
                embed.set_author(character.name, icon_url=character.picture)
                embed.set_footer(ctx.author.display_name, ctx.author.avatar)
                await member_user.send(embed=embed)


    @org_mng.command(name='зарплата')
    @BasicCog.character_required
    async def __org_payday(self, ctx, stake:discord.Option(int, min_value=10, max_value=200, default=100, required=False),
                           character_id:int=None):
        from ArbOrgs import Organization, Rank
        from ArbCharacters import Character
        from ArbCore import Server

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует', f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        org_lvl = character.org_lvl
        if not org_lvl or not Rank(org_lvl).is_leader:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *Вы не можете выплатить зарплату членам организации*')
            await ctx.respond(embed=embed)
            return

        org = Organization(org_id)
        total_characters = org.get_all_characters()
        payed_characters = org.payday(stake)
        if not payed_characters:
            embed = ErrorEmbed('Недостаточно денег', f'-# *Бюджет организации не обладает достаточной суммой для выплаты зарплаты*')
            await ctx.respond(embed=embed)
            return

        embed = SuccessEmbed('Выплата зарплаты', f'***{Rank(org_lvl).label} {character.name}** выплатил зарплату организации **{org.label}** по ставке `{stake}%` от установленной*\n\n'
                                                 f'-# ***Текущий баланс:** {ct}{int(org.money):,d}*\n'
                                                 f'-# *Персонажей получивших зарплату: **{len(payed_characters)} / {len(total_characters)}***',
                             footer=f'{ctx.author.display_name}', footer_logo=f'{ctx.author.avatar}')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)

    @org_mng.command(name='уволить')
    @BasicCog.character_required
    async def __org_fire(self, ctx, member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(org_members)),
                          character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank

        member_id = ArbAutoComplete.extract('CHARS_INIT', 'name', member, 'id')
        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(character.org_lvl).can_invite:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *Вы не можете уволить члена организации*')
            await ctx.respond(embed=embed)
            return

        db = DataManager()
        org = Organization(org_id, data_manager=db)

        member = Character(member_id, data_manager=db)
        member_owner = member.owner

        embed = ErrorEmbed(f'Увольнение | {org.label}',
                             f'***{Rank(character.org_lvl).label} {character.name}** уволил **{Rank(member.org_lvl).label} {member.name}** из организации **{org.label}***')
        embed.set_author(character.name, icon_url=character.picture)
        embed.set_footer(ctx.author.display_name, ctx.author.avatar)
        await ctx.respond(embed=embed)

        if member_owner:
            member_user = ctx.bot.get_user(member_owner)
            embed = ErrorEmbed(f'Увольнение | {org.label}',
                                 f'***{Rank(character.org_lvl).label} {character.name}** уволил Вас, **{Rank(member.org_lvl).label} {member.name}**, из организации **{org.label}***')
            embed.set_author(character.name, icon_url=character.picture)
            embed.set_footer(ctx.author.display_name, ctx.author.avatar)
            await member_user.send(embed=embed)

        db.update('CHARS_INIT', {'org_lvl': None, 'org': None}, f'id = {member_id}')


    @org_mng.command(name='управлять-бюджетом')
    @BasicCog.character_required
    async def __org_manage_budget(self, ctx, amount: discord.Option(int, required=True),
                                  character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank

        ct = Server(ctx.guild.id).currency

        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        org = Organization(org_id)

        rank_id = character.org_lvl
        if amount > 0:
            result = character.spend_money(amount)
            if result:
                org.update_budget(amount)
                embed = SuccessEmbed('Управление бюджетом', f'***{Rank(rank_id).label} {character.name}** успешно внёс ``{ct}{amount}`` на счёт организации **{org.label}***')
                embed.set_author(character.name, icon_url=character.picture)
                embed.set_footer(ctx.author.display_name, ctx.author.avatar)
                await ctx.respond(embed=embed)
            else:
                embed = ErrorEmbed('Недостаточно денег', f'-# *У Вас недостаточно средств для перевода на счёт организации*')
                await ctx.respond(embed=embed)
                return
        else:
            if Rank(rank_id).can_invite:
                character.add_money(-amount)
                org.update_budget(amount)
                embed = SuccessEmbed('Управление бюджетом',
                                     f'***{Rank(rank_id).label} {character.name}** успешно снял ``{ct}{-amount}`` со счёта организации **{org.label}***')
                embed.set_author(character.name, icon_url=character.picture)
                embed.set_footer(ctx.author.display_name, ctx.author.avatar)
                await ctx.respond(embed=embed)
            else:
                embed = ErrorEmbed('Недостаточно полномочий', f'-# *Вы не можете снять деньги со счёта организации*')
                await ctx.respond(embed=embed)
                return

    @org_info.command(name='дипломатия-организации')
    @BasicCog.character_required
    async def __org_relations(self, ctx,
                                    character_id:int=None):
        from ArbOrgs import Organization
        from ArbCharacters import Character

        character = Character(character_id)
        org_id = character.org
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        org = Organization(org_id)
        org_relations = org.text_relations()
        main_embed = ArbEmbed(f'Дипломатический статус {org.label}',
                              f'{org_relations}',
                              logo_url=org.picture)

        await ctx.respond(embed=main_embed)

    @org_group.command(name='сформировать-отряд')
    @BasicCog.character_required
    async def __form_group(self, ctx,
                           label:discord.Option(str),
                           leader:discord.Option(str, autocomplete=discord.utils.basic_autocomplete(org_members), required=False),
                           character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank
        from ArbGroups import Group

        character = Character(character_id)
        org_id = character.org
        rank_id = character.org_lvl
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж {character.name} не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(rank_id).can_group:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *У вас недостаточно полномочий для формирования отряда от лица организации*')
            await ctx.respond(embed=embed)
            return

        leader = AAC.extract('CHARS_INIT', 'name', leader, 'id') if leader else character_id

        group = Group.create(label, character_id)
        embed = SuccessEmbed(f'Новый отряд "{label}" | {Organization(character.org).label}',
                             f'*Новый отряд **{label}** ||(ID: {group.id})|| был сформирован **{Rank(character.org_lvl).label} {character.name}**. Лидером отряда назначен **{Rank(Character(leader).org_lvl).label} {Character(leader).name}***')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)

    @org_group.command(name='добавить-в-отряд')
    @BasicCog.character_required
    async def __org_add_group_member(self, ctx,
                                     group: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_org_groups)),
                                     member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(org_members)),
                                     role: discord.Option(str, autocomplete=AAC.db_call('GROUP_ROLES', 'label'), required=False),
                                     character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank
        from ArbGroups import Group, GroupRole

        character = Character(character_id)
        org_id = character.org
        rank_id = character.org_lvl
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж **{character.name}** не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(rank_id).can_group:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *У Вас недостаточно полномочий для добавления членов отряда от лица организации*')
            await ctx.respond(embed=embed)

        group = Group(AAC.extract('GROUP_INIT', 'label', group, 'id'))
        if not group:
            embed = ErrorEmbed('Отряд отсутствует', f'-# *Персонаж **{character.name}** не является членом ни одного отряда*')
            await ctx.respond(embed=embed)
            return

        member = AAC.extract('CHARS_INIT', 'name', member, 'id')
        role = AAC.extract('GROUP_ROLES', 'label', role, 'id') if role else 'Participant'

        group.add_member(member, role)
        embed = SuccessEmbed(f'Добавление члена в отряд "{group.label}" | {Organization(character.org).label}',
                             f'*Персонаж **{Character(member).name}** был добавлен в отряд **{group.label}**. Должность в отряде: **{GroupRole(role).label}**.*')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)

    @org_mng.command(name='назначить-позывной')
    @BasicCog.character_required
    async def __org_set_nickname(self, ctx,
                                 member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(org_members)),
                                 callsign: discord.Option(str, required=True, min_length=2, max_length=100),
                                 character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank

        character = Character(character_id)
        org_id = character.org
        rank_id = character.org_lvl
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж **{character.name}** не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(rank_id).can_group:
            embed = ErrorEmbed('Недостаточно полномочий',
                               f'-# *У Вас недостаточно полномочий для назначения позывного от лица организации*')
            await ctx.respond(embed=embed)
            return 

        member_id = AAC.extract('CHARS_INIT', 'name', member, 'id')
        member_obj = Character(member_id)
        member_obj.update_record({'callsign': callsign})

        embed = SuccessEmbed(f'Назначение позывного "{callsign}" | {Organization(character.org).label}',
                             f'*Позывной **{callsign}** был назначен **{Character(member_id).name}**.*',
                             footer=Character(character_id).name,
                             footer_logo=Character(character_id).picture)
        await ctx.respond(embed=embed)

    @org_group.command(name='изгнать-из-отряда')
    @BasicCog.character_required
    async def __org_remove_group_member(self, ctx, group: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_org_groups)),
                                     member: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(group_members)),
                                     character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank
        from ArbGroups import Group

        character = Character(character_id)
        org_id = character.org
        rank_id = character.org_lvl
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж **{character.name}** не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(rank_id).can_group:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *У Вас недостаточно полномочий для удаления членов отряда от лица организации*')
            await ctx.respond(embed=embed)

        group = Group(AAC.extract('GROUP_INIT', 'label', group, 'id'))
        if not group:
            embed = ErrorEmbed('Отряд отсутствует', f'-# *Персонаж **{character.name}** не является членом ни одного отряда*')
            await ctx.respond(embed=embed)
            return

        member = Character(AAC.extract('CHARS_INIT', 'name', member, 'id'))
        group.delete_member(member.id)
        embed = SuccessEmbed(f'Удаление из отряда "{group.label}" | {Organization(character.org).label}',
                             f'*Персонаж **{Rank(member.org_lvl).label} {member.name}** насильно покинул отряд **{group.label}**.*')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)

    @org_group.command(name='расформировать-отряд')
    @BasicCog.character_required
    async def __org_disband_group(self, ctx,
                                  group: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_org_groups)),
                                     character_id:int=None):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank
        from ArbGroups import Group

        character = Character(character_id)

        org_id = character.org
        rank_id = character.org_lvl
        if not org_id:
            embed = ArbEmbed('Организация отсутствует',
                             f'-# *Персонаж **{character.name}** не является членом какой-либо организации*')
            await ctx.respond(embed=embed)
            return

        if not Rank(rank_id).can_group:
            embed = ErrorEmbed('Недостаточно полномочий', f'-# *У Вас недостаточно полномочий для удаления членов отряда от лица организации*')
            await ctx.respond(embed=embed)

        group_id = AAC.extract('GROUP_INIT', 'label', group, 'id')
        group = Group(group_id)
        if not group:
            embed = ErrorEmbed('Отряд отсутствует', f'-# *Персонаж **{character.name}** не является членом ни одного отряда*')
            await ctx.respond(embed=embed)
            return

        group.disband()
        embed = SuccessEmbed(f'Расформирование отряда "{group.label}" | {Organization(character.org).label}',
                             f'*Отряд **{group.label}** был расформирован от лица **{Rank(character.org_lvl).label} {character.name}**.*')
        embed.set_author(character.name, icon_url=character.picture)

        await ctx.respond(embed=embed)







def setup(bot):
    bot.add_cog(CharacterMenu(bot))
    bot.add_cog(CharacterCombat(bot))
    bot.add_cog(CharacterLocations(bot))
    bot.add_cog(CharacterOrganization(bot))
    bot.add_cog(Registration(bot))
    bot.add_cog(CharacterGroup(bot))
    bot.add_cog(InventoryManager(bot))
    bot.add_cog(CharacterSkills(bot))
    bot.add_cog(CharacterQuests(bot))