import datetime

import discord
from discord.ext import commands
from discord import default_permissions
from ArbDatabase import DataManager
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator, SuccessEmbed, ErrorEmbed, InteractiveForm, FormStep, Selection, SelectingForm
from ArbResponse import Response, ResponsePool

from .BasicCog import BasicCog

from ArbUtils.ArbTimedate import TimeManager
from ArbUtils.ArbDataParser import ListChunker
from ArbCharacterMemory import CharacterMemory, CharacterRelations
from ArbGenerator import NameGenerator, TitleGenerator, GenerateBattle
from ArbCharacters import Character, CharacterProgress, Race
from ArbHealth import Body
from ArbItems import Inventory, Item, CharacterEquipment
from ArbBattle import Actor, Coordinator, Battlefield, BattleTeam, Layer, GameObject
from ArbDialogues import Dialogue, CharacterMessage


class CharacterMenu(BasicCog):

    generate = discord.SlashCommandGroup("generate", "Команды генерации")
    character = discord.SlashCommandGroup("character", 'Команды интерфейса персонажа')
    reg = discord.SlashCommandGroup("reg", 'Команды регистрации')

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


    @character.command(name='main_info')
    @BasicCog.character_required
    async def __character_info(self, ctx, character_id: int = None):
        character_info = Character(character_id)
        character_text = character_info.text_card()

        embed = ArbEmbed(f'Информация о персонаже {character_info.name}', character_text,
                         footer=f'Последняя смена цикла {TimeManager().get_string_timestamp(character_info.update)}\nСервер: {character_info.server}')

        await ctx.respond('', embed=embed)

    @character.command(name='body_info')
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

    @character.command(name=f'inventory')
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

    @character.command(name='relations')
    @BasicCog.character_required
    async def __character_relations(self, ctx, character_id: int=None):

        character_relations = CharacterRelations(character_id)

        relations_text = character_relations.string_relations()
        relations_text = relations_text if relations_text else f'-# *(Здесь будут отображаться знакомые персонажи)*'

        relations_embed = ArbEmbed('Взаимоотношения', relations_text)

        await ctx.respond('', embed=relations_embed)

    @generate.command(name='generate_name')
    async def __generate_name(self, ctx, gender: discord.Option(str, choices=['Мужской', 'Женский', 'Бесполый', 'Робот']),
                              value: discord.Option(int, required=False, default=1)):
        total_names = ''
        for _ in range(value):
            total_names += f'\n {NameGenerator(gender)}'

        embed = ArbEmbed('Сгенерированные имена', total_names)
        await ctx.respond(f'', embed=embed)

    @generate.command(name='generate_titles')
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

    @commands.slash_command(name=f'database_edit')
    @BasicCog.admin_required
    async def database_edit(self, ctx,
                            table: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(tables_list)),
                            column: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(columns_list)),
                            value,
                            filter: discord.Option(str)):

        data_manager = DataManager()
        try:
            rows = data_manager.select_dict(table, filter=filter)
            rows_count = len(rows)
            row_value = rows[0].get(column)
            data_manager.update(table, {column: value}, filter=filter)

            embed = SuccessEmbed(f'Изменение в базе данных',
                                 f'Были внесены **{rows_count}** изменений в таблице `{table}` в колонке `{column}`'
                                 f'\n-# Изменено: ``{row_value}`` на `{value}`.')
            await ctx.respond(embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Изменение в базе данных',
                               f'При изменении значения в таблице `{table}` возникла ошибка:'
                               f'```{e}```')
            await ctx.respond(embed=embed)

    @commands.slash_command(name=f'check_database')
    @BasicCog.admin_required
    async def check_database(self, ctx,
                            table: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(tables_list)),
                            filter: discord.Option(str, required=False),
                            page: discord.Option(int, required=False)):

        data_manager = DataManager()
        rows = data_manager.select_dict(table, filter=filter)
        rows_text = []
        for row in rows:
            row_items = row.items()
            row_text = f''
            for item, value in row_items:
                row_text += f'- ``{item}:`` **{value}**\n'
            rows_text.append(row_text)

        chuked_text = ListChunker(5, rows_text)
        embeds = []
        for chunk in chuked_text:
            chunk_text = '\n\n'.join(chunk)
            embed = ArbEmbed(f'Содержание {table}', chunk_text)
            embeds.append(embed)

        view = Paginator(embeds, ctx, ignore_footer=True)
        await ctx.respond(view=view, embed=embeds[page-1 if page and page <= len(embeds) else 0])

    @reg.command(name='start_registration')
    async def __start_registration(self, ctx):
        from ArbRegistration import CharacterRegistration

        author = ctx.author.id
        character_registration = CharacterRegistration(ctx)
        character_registration.form.extend_data('owner', [author])
        character_registration.form.extend_data('update', [datetime.datetime.now().date().strftime('%Y-%m-%d')])
        character_registration.form.extend_data('server', [ctx.guild.id])
        result = await character_registration.start()

        print(result)


class CharacterCombat(BasicCog):
    coordinator = discord.SlashCommandGroup("coordinator", "Команды боевого координатора")
    combat = discord.SlashCommandGroup("combat", "Боевые команды")
    movement = discord.SlashCommandGroup("move", "Команды перемещения в бою")
    interact = discord.SlashCommandGroup("interact", "Команды для взаимодействия с объектами")
    detection = discord.SlashCommandGroup("detection", "Команды обнаружения")

    @commands.slash_command(name='expect_weapon')
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

    @combat.command(name=f'combat_info')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __combat_info(self, ctx, character_id:int=None):
        character = Character(character_id)
        character_text = character.text_combat_card()

        embed = ArbEmbed(f'Боевое состояние {character.name}', character_text)

        await ctx.respond('', embed=embed)

    @detection.command(name=f'lookout')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __combat_lookout(self, ctx, character_id: int=None):
        from ArbBattle import ActorVision
        actor = Actor(character_id)
        vision = ActorVision(actor)

        total_text = vision.string_vigilance()
        embed = ArbEmbed(f'Обзор местности', total_text)

        await ctx.respond('', embed=embed)

    @detection.command(name=f'detect_sound')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __detect_sound(self, ctx, sound_id:int, character_id: int = None):
        actor = Actor(character_id)
        responses = actor.detect_sound(sound_id)

        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i+1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @detection.command(name=f'sounds')
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

    @movement.command(name='to_layer')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __move_to_layer(self, ctx, layer_id:int, character_id: int=None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.move_to_layer(layer_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i+1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @movement.command(name='to_object')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __move_to_object(self, ctx, object_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.move_to_object(object_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @movement.command(name='escape')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __escape(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.escape()
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @movement.command(name='fly')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __fly(self, ctx, height: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.fly(height)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='reload')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __reload(self, ctx, ammo_type:str=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.reload(ammo_type)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='range_attack')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __range_attack(self, ctx, enemy_id: int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.range_attack(enemy_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='melee_attack')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __melee_attack(self, ctx, enemy_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.melee_attack(enemy_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='race_attack')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __race_attack(self, ctx, enemy_id: int = None, attack_id:str=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.race_attack(enemy_id, attack_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='throw_grenade')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __grenade_attack(self, ctx, enemy_id: int = None, grenade_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.throw_grenade(enemy_id, grenade_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='set_target')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __set_target(self, ctx, enemy_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_target(enemy_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='go_to_melee')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __set_melee_target(self, ctx, enemy_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_melee_target(enemy_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='flee_from_melee')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __flee_from_melee(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.flee_from_melee()
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @interact.command(name='object_interaction')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __object_interaction(self, ctx, target_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.interact_with_object(target_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='hunt')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __hunt(self, ctx, enemy_id:int=None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_hunt(enemy_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='suppress')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __suppress(self, ctx, cover_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_suppression(cover_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='contain')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __contain(self, ctx, layer_id: int = None, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_containment(layer_id)
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='overwatch')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __overwatch(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.set_overwatch()
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @combat.command(name='wait')
    @BasicCog.character_required
    @BasicCog.in_battle
    async def __wait(self, ctx, character_id: int = None):
        actor = Actor(character_id)
        responses: ResponsePool = actor.waiting()
        embeds = responses.get_embeds()

        view = Paginator(embeds, ctx, {i + 1: embed.title for i, embed in enumerate(embeds)})

        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)


    @coordinator.command(name='artillery_strike')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __artillery_strike(self, ctx, layer_id:int, strikes:int = 1, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.artillery_strike(layer_id=layer_id, value=strikes, ammo_id='FragGrenade')
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='mines')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __mines(self, ctx, layer_id: int, mines: int = 1, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.mine_laying(layer_id=layer_id, mine_type=f'APM', value=mines)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='emergency_evacuation')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __emergency_evacuation(self, ctx, layer_id: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.emergency_evacuation(layer_id=layer_id)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='supply_ammo')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_ammo(self, ctx, layer_id: int, value:int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.supply_ammo(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='supply_grenades')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_grenades(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.supply_grenades(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='supply_firstaid')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_firstaid(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.supply_firstaid(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])

    @coordinator.command(name='supply_toolkit')
    @BasicCog.character_required
    @BasicCog.character_is_coordinator
    async def __supply_toolkit(self, ctx, layer_id: int, value: int, character_id: int = None):
        team_id = self.is_coordinator(character_id)
        coordinator = Coordinator(team_id)

        response = coordinator.supply_repair(layer_id=layer_id, value=value)
        embeds = response.get_embeds()

        await ctx.respond(embed=embeds[0])




def setup(bot):
    bot.add_cog(CharacterMenu(bot))
    bot.add_cog(CharacterCombat(bot))