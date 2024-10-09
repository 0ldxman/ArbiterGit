import datetime
import pprint
import random

import discord
from discord.enums import ChannelType
from discord.ext import commands
from discord import default_permissions
from ArbDatabase import DEFAULT_MANAGER, DataManager
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator, SuccessEmbed, ErrorEmbed, InteractiveForm, FormStep, Selection, SelectingForm
from ArbResponse import Response, ResponsePool, Notification

from cogs.BasicCog import BasicCog

from ArbUtils.ArbTimedate import TimeManager
from ArbUtils.ArbDataParser import ListChunker
from ArbCharacterMemory import CharacterMemory
from ArbGenerator import NameGenerator, TitleGenerator, GenerateBattle
from ArbCharacters import Character, CharacterProgress, Race
from ArbHealth import Body
from ArbItems import Inventory, Item, CharacterEquipment
from ArbBattle import Actor, Coordinator, Battlefield, BattleTeam, Layer, GameObject
from ArbDialogues import Dialogue, CharacterMessage
from ArbCore import Player, Server
from ArbRegistration import RegForm
from ArbAutocomplete import AAC


class AdminTools(BasicCog):
    cfg_server = discord.SlashCommandGroup('сервер', 'Команды настройки сервера')
    cfg = discord.SlashCommandGroup('настроить', 'Команды настройки сервера')
    cfg_battle = cfg.create_subgroup('бой', 'Команды боя')
    cfg_character = cfg.create_subgroup('персонаж', 'Команды настройки персонажа')
    register = discord.SlashCommandGroup('проверка-анкет', 'Административные команды редактирования анкеты')
    mng = discord.SlashCommandGroup('управление', 'Команды управления')
    mng_battle = mng.create_subgroup('бой', 'Команды боя')
    mng_dialogue = mng.create_subgroup('диалоги')
    mng_gen = mng.create_subgroup('генерация', 'Команды генерации')
    mng_loc = mng.create_subgroup('локации', 'Команды локаций')
    # tools = discord.SlashCommandGroup('инструменты', 'Разные инструменты администрирования')
    # tools_dmg = tools.create_subgroup('урон', 'Команды нанесения урона')
    # tools_inj = tools.create_subgroup('ранения', 'Команды ранений')
    # tools_dis = tools.create_subgroup('болезни', 'Команды болезней')
    # tools_imp = tools.create_subgroup('импланты', 'Команды имплантов')
    # cfg_dialogue = discord.SlashCommandGroup('диалоги', 'Команды диалогов')
    # cfg_quests = cfg.create_subgroup('задания', 'Команды заданий')
    # cfg_campaigns = cfg.create_subgroup('кампании', 'Команды кампаний и ивентов')

    cur = discord.SlashCommandGroup('курирование', 'Команды курирования')
    cur_items = cur.create_subgroup('вещи', 'Команда вещей')
    cur_rels = cur.create_subgroup('отношения', 'Команды отношений')
    cur_damage = cur.create_subgroup('урон', 'Команды урона')
    cur_injury = cur.create_subgroup('ранения', 'Команды ранений')
    cur_illness = cur.create_subgroup('болезни', 'Команды болезней')
    cur_implant = cur.create_subgroup('импланты', 'Команды имплантов')
    cur_rp = cur.create_subgroup('рп', 'Команды для РП отыгровок')
    cur_skills = cur.create_subgroup('навыки', 'Команды навыков')
    plan = discord.SlashCommandGroup('планирование', 'Команды планирования')
    plan_quests = plan.create_subgroup('задания', 'Команды заданий')
    plan_campaigns = plan.create_subgroup('кампании', 'Команды кампаний и ивентов')

    cfg_location = cfg.create_subgroup('локации', 'Команды настройки локации')

    async def active_battles(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battles = Battlefield.get_active_battles()
        return [f'{battle} - {Battlefield(battle, data_manager=db).label}' for battle in battles]

    async def get_battle_actors(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id, data_manager=db)
        return [f'{actor} - {Character(actor, data_manager=db).name}' for actor in battlefield.fetch_actors()]

    async def get_battle_teams(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id, data_manager=db)
        teams = [f'{team} - {BattleTeam(team, data_manager=db).label}' for team in battlefield.fetch_teams()]
        print(teams)
        return teams

    async def get_battle_layers(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id, data_manager=db)
        return [f'{layer_id} - {layer.label}' for layer_id, layer in battlefield.get_layers().items()]

    async def get_battle_objects(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        objects = db.select_dict('BATTLE_OBJECTS', filter=f'battle_id = {battle_id}')
        total_objects = []
        for obj in objects:
            total_objects.append(f'{obj.get("object_id")} - {GameObject(obj.get("object_id"), data_manager=db).object_type.label} (Слой {obj.get("layer_id")})')

        print(total_objects)

        return total_objects

    async def get_battle_traps(ctx: discord.AutocompleteContext):
        from ArbWeapons import TrapInit

        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        objects = db.select_dict('BATTLE_TRAPS', filter=f'battle_id = {battle_id}')
        total_objects = []
        for obj in objects:
            total_objects.append(
                f'{obj.get("trap_id")} - {TrapInit(obj.get("type")).label} (Слой {obj.get("layer_id")})')

        print(total_objects)

        return total_objects

    async def get_character_bodyparts(ctx: discord.AutocompleteContext):
        from ArbCore import Player

        db = DEFAULT_MANAGER
        character = ctx.options.get('character')
        if not character:
            character = Player(ctx.interaction.user.id, data_manager=db).current_character
        character = BasicCog.prepare_id(character)

        body_parts = Body(character, data_manager=db).get_body_elements()
        return [f'{part.part_id} - {part.label}' for part in body_parts]

    async def get_range_weapons(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        range_weapons = db.select_dict('WEAPONS', filter=f'class != "ColdSteel"')
        return [f'{weapon.get("id")} - {weapon.get("name")}' for weapon in range_weapons]

    async def get_weapons(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        range_weapons = db.select_dict('WEAPONS')
        return [f'{weapon.get("id")} - {weapon.get("name")}' for weapon in range_weapons]

    async def get_race_attacks(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        race = ctx.options.get('race')
        race_id = race.split(' ')[0]

        attacks = db.select_dict('RACES_MELEE', filter=f'race = "{race_id}"')
        return [f'{attack.get("id")} - {attack.get("name")}' for attack in attacks]

    async def get_all_characters(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        print([f'{char.get("id")} - {Character(char.get("id"), data_manager=db).name}' for char in db.select_dict('CHARS_INIT', 'id')])
        return [f'{char.get("id")} - {Character(char.get("id"), data_manager=db).name}' for char in db.select_dict('CHARS_INIT', 'id')]

    async def get_all_races(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        return [f'{race.get("id")} - {Race(race.get("id")).label}' for race in db.select_dict('RACES_INIT')]

    async def get_all_dialogues(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        dialogues = [Dialogue(dialogue.get("id")) for dialogue in db.select_dict('DIALOGUE_INIT')]

        return [f'{d.dialogue_id} - {d.label} ({ctx.bot.get_channel(d.channel).name})' for d in dialogues]

    async def get_all_sounds(ctx: discord.AutocompleteContext):
        from ArbSounds import InBattleSound
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])

        sounds = [InBattleSound(sound.get('id')) for sound in db.select_dict('BATTLE_SOUNDS', filter=f'battle_id = {battle_id}')]
        return [f'{sound.id} - {sound.label} от {Character(sound.actor_id).name if sound.actor_id else "Неизвестно"}' for sound in sounds]

    async def get_layer_objects(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        actor_id = int(ctx.options.get('actor').split(' ')[0])
        actor_layer = Actor(actor_id, data_manager=db).layer_id

        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        layer = ctx.options.get('layer')
        layer_id = int(layer.split(' ')[0]) if layer else actor_layer

        objects = db.select_dict('BATTLE_OBJECTS', filter=f'battle_id = {battle_id} AND layer_id = {layer_id}')
        print(battle_id, layer_id, objects)
        total_objects = []
        for obj in objects:
            total_objects.append(
                f'{obj.get("object_id")} - {GameObject(obj.get("object_id"), data_manager=db).object_type.label} (Слой {obj.get("layer_id")})')

        print(total_objects)

        return total_objects

    async def get_battle_layer_objects(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER

        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        layer = ctx.options.get('layer')
        layer_id = int(layer.split(' ')[0])

        objects = db.select_dict('BATTLE_OBJECTS', filter=f'battle_id = {battle_id} AND layer_id = {layer_id}')
        print(battle_id, layer_id, objects)
        total_objects = []
        for obj in objects:
            total_objects.append(
                f'{obj.get("object_id")} - {GameObject(obj.get("object_id"), data_manager=db).object_type.label} (Слой {obj.get("layer_id")})')

        print(total_objects)

        return total_objects

    async def get_battle_dead(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        battle = ctx.options.get('battle')
        battle_id = int(battle.split(' ')[0])
        return [f'{char.get("character_id")} - {Character(char.get("character_id")).name}' for char in db.select_dict('BATTLE_DEAD', filter=f'battle_id = {battle_id}')]

    async def get_actors_by_actor(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        actor_id = int(ctx.options.get('actor').split(' ')[0])
        battle_id = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not battle_id:
            return []

        battle_id = battle_id[0].get('battle_id')

        actors = db.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {battle_id}')
        print(actors)
        total_actors = []
        for actor in actors:
            total_actors.append(f'{actor.get("character_id")} - {Character(actor.get("character_id")).name}')

        print(total_actors)

        return total_actors

    async def get_layers_by_actor(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        actor_id = int(ctx.options.get('actor').split(' ')[0])
        battle_id = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not battle_id:
            return []

        battle_id = battle_id[0].get('battle_id')

        layers = db.select_dict('BATTLE_LAYERS', filter=f'battle_id = {battle_id}')
        print(layers)
        total_actors = []
        for layer in layers:
            total_actors.append(f'{layer.get("id")} - {Layer(layer.get("id"), battle_id, data_manager=db).label}')

        print(total_actors)

        return total_actors

    async def get_objects_by_actor(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        actor_id = int(ctx.options.get('actor').split(' ')[0])
        battle_id = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not battle_id:
            return []

        battle_id = battle_id[0].get('battle_id')

        layers = db.select_dict('BATTLE_OBJECTS', filter=f'battle_id = {battle_id}')
        print(layers)
        total_actors = []
        for layer in layers:
            total_actors.append(f'{layer.get("object_id")} (Слой {layer.get("layer_id")})- {GameObject(layer.get("object_id")).object_type.label}')

        print(total_actors)

        return total_actors

    async def get_character_injuries(ctx: discord.AutocompleteContext):
        from ArbHealth import Injury, BodyElement

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        db = DEFAULT_MANAGER
        character_injuries = db.select_dict('CHARS_INJURY', filter=f'id = {character_id}')
        injuries = [Injury(inj.get("id_inj"), data_manager=db) for inj in character_injuries]

        return [f'{inj.injury_id} - {inj.injury_type.label} ({inj.damage}) в {BodyElement(character_id, inj.place, data_manager=db).label}' for inj in injuries]

    async def get_character_disease(ctx: discord.AutocompleteContext):
        from ArbHealth import Disease

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        db = DEFAULT_MANAGER
        character_injuries = db.select_dict('CHARS_DISEASE', filter=f'id = {character_id}')
        injuries = [Disease(inj.get("dis_id"), data_manager=db) for inj in character_injuries]
        print(injuries)

        return [f'{inj.disease_id} - {inj.disease_type.label} ({inj.current_severity}%) {inj.place}'
            for inj in injuries]

    async def get_character_implants(ctx: discord.AutocompleteContext):
        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        db = DEFAULT_MANAGER
        implants = [e for e in Body(character_id, data_manager=db).get_body_elements() if e.implant_type]
        return [f'{e.element_id} - {e.label}' for e in implants]

    async def get_character_quests(ctx: discord.AutocompleteContext):
        from ArbQuests import Quest

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        db = DEFAULT_MANAGER
        data = db.select_dict('CHARS_QUESTS', filter=f'id = {character_id}')
        if not data:
            return []
        quests = [Quest(quest.get('quest_id'), data_manager=db) for quest in data]
        return [f'{quest.id} - {quest.label}' for quest in quests]

    async def get_quest_tasks(ctx: discord.AutocompleteContext):
        from ArbQuests import Quest

        quest = ctx.options.get('quest')
        quest_id = quest.split(' ')[0]

        db = DEFAULT_MANAGER
        quest_obj = Quest(quest_id, data_manager=db)
        tasks_dict = quest_obj.get_tasks()
        total_tasks = []
        for phase, tasks in tasks_dict.items():
            for task in tasks:
                total_tasks.append(f'{task.title}#{phase}')

        return total_tasks

    async def get_character_quest_tasks(ctx: discord.AutocompleteContext):
        from ArbQuests import CharacterQuest
        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        quest = ctx.options.get('quest')
        quest_id = quest.split(' ')[0]

        db = DEFAULT_MANAGER
        quest_obj = CharacterQuest(character_id, quest_id, data_manager=db)
        tasks_dict = quest_obj.current_tasks()
        total_tasks = []
        for task in tasks_dict:
            total_tasks.append(f'{task.title}#{task.phase}')

        return total_tasks

    async def get_orgs(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        orgs = db.select_dict('ORG_INIT')
        return [f'{org.get("id")} - {org.get("label")}' for org in orgs]

    async def get_orgs_ranks(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        orgs = db.select_dict('ORG_RANKS')
        return [f'{org.get("id")} - {org.get("label")}' for org in orgs]

    async def get_org_ranks(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        org_id = ctx.options.get('org').split(' ')[0]
        orgs = db.select_dict('ORG_RANKS', filter=f'org = "{org_id}"')
        return [f'{org.get("id")} - {org.get("label")}' for org in orgs]

    async def get_all_quests(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        quests = db.select_dict('QUESTS')
        return [f'{quest.get("id")} - {quest.get("label")} ({quest.get("type")})' for quest in quests]

    async def get_all_campaigns(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        quests = db.select_dict('CAMPAIGN_INIT')
        return [f'{quest.get("id")} - {quest.get("label")} ({quest.get("type")})' for quest in quests]

    async def get_campaign_quests(ctx: discord.AutocompleteContext):
        from ArbQuests import Quest
        db = DEFAULT_MANAGER
        campaign_id = ctx.options.get('campaign').split(' ')[0]
        quests = db.select_dict('CAMPAIGN_QUESTS', filter=f'id = "{campaign_id}"')
        return [f'{quest.get("quest")} - {Quest(quest.get("quest")).label}' for quest in quests]

    async def get_campaign_phases(ctx: discord.AutocompleteContext):
        from ArbQuests import Campaign
        db = DEFAULT_MANAGER
        campaign_id = ctx.options.get('campaign').split(' ')[0]

        campaign_quests = db.select_dict('CAMPAIGN_QUESTS', filter=f'id = "{campaign_id}"')
        campaign_phases_desc = db.select_dict('CAMPAIGN_PHASE', filter=f'campaign_id = "{campaign_id}"')
        print(campaign_id, campaign_quests, campaign_phases_desc)

        len_quests = len(campaign_quests) if campaign_quests else 0
        len_campaign_desc = len(campaign_phases_desc) if campaign_phases_desc else 0
        print(len_quests, len_campaign_desc)

        max_phase = max(len_quests, len_campaign_desc)
        return [i for i in range(max_phase)] if max_phase else [0]

    async def get_quest_rewards(ctx: discord.AutocompleteContext):
        from ArbQuests import Quest
        db = DEFAULT_MANAGER
        quest_id = ctx.options.get('quest').split(' ')[0]
        quest = Quest(quest_id, data_manager=db)
        rewards = quest.get_reward()

        return [f'{reward.reward_type} {reward.value} {reward.split_type}' for reward in rewards]

    async def get_character_group_members(ctx: discord.AutocompleteContext):
        from ArbGroups import Group

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)
        members = Group.find_group_members_including(character_id)

        return [f'{member} - {Character(member).name}' for member in members]

    async def cfg_response(self, ctx, text:str):
        response = SuccessEmbed('Настройка сервера', f'-# *{text}*')
        await ctx.respond(f'', embed=response)

    async def get_all_items(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        items = db.select_dict('ITEMS')
        return [f'{item.get("id")} - {item.get("name")}' for item in items]

    async def get_all_itemtypes(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        weapons = db.select_dict('WEAPONS')
        clothes = db.select_dict('CLOTHES')
        items = db.select_dict('ITEMS_INIT')
        ammo = db.select_dict('AMMO', filter=f'caliber = "Граната"')

        total_items = []
        total_items.extend(weapons)
        total_items.extend(clothes)
        total_items.extend(items)
        total_items.extend(ammo)

        return [f'{item.get("id")} - {item.get("name")}' for item in total_items]

    async def qualities(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        return [quality.get("name") for quality in db.select_dict('QUALITY_INIT')]

    async def item_available_materials(ctx: discord.AutocompleteContext):
        from ArbGenerator import ItemManager

        db = DEFAULT_MANAGER

        item_id = ctx.options.get('item_type').split(' ')[0]

        item_material_type = ItemManager(item_id).get_material_type()
        available_materials = db.select_dict('MATERIALS', filter=f'type = "{item_material_type}"')

        return [material.get('name') for material in available_materials]

    async def get_memories_types(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        return [f'{memory_type.get("id")} - {memory_type.get("label")}' for memory_type in db.select_dict('EVENT_INIT')]

    async def get_character_memories(ctx: discord.AutocompleteContext):
        from ArbCharacterMemory import CharacterMemoryEvent
        db = DEFAULT_MANAGER
        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)

        return [f'{event.get("event_id")} - {CharacterMemoryEvent(event.get("event_id")).label}' for event in db.select_dict('CHARS_MEMORY', filter=f'id = {character_id}')]

    async def get_all_relation_roles(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        return [f'{role.get("id")} - {role.get("label")}' for role in db.select_dict('RELATION_ROLES')]

    async def get_character_relations(ctx: discord.AutocompleteContext):
        from ArbCharacterMemory import CharacterRelations
        db = DEFAULT_MANAGER

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)

        relations = CharacterRelations(character_id, data_manager=db)
        return [f'{encounter_id} - {relation.relation_type.label if not relation.family_type else relation.relation_type.label} {Character(encounter_id).name}' for encounter_id, relation in relations.relations.items()]

    async def get_author_available_extras(ctx: discord.AutocompleteContext):
        from ArbRolePlay import Extra

        author_id = ctx.interaction.user.id
        extras = Extra.get_available_extras(author_id)
        return [f'{extra.tag} - {extra.name}' for extra in extras]

    async def get_regions(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        regions = db.select_dict('LOC_CLUSTER')
        return [f'{reg.get("id")} - {reg.get("label")}' for reg in regions]

    async def get_location_types(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        location_types = db.select_dict('LOC_TYPE')
        return [f'{location_type.get("id")} - {location_type.get("label")}' for location_type in location_types]

    async def get_region_locations(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        region_id = ctx.options.get('region').split(' ')[0]
        locations = db.select_dict('LOC_INIT', filter=f'region = "{region_id}"')
        return [f'{location.get("id")} - {location.get("label")}' for location in locations]

    async def get_all_locations(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        locations = db.select_dict('LOC_INIT')
        return [f'{location.get("id")} - {location.get("label")}' for location in locations]

    async def get_location_connections(ctx: discord.AutocompleteContext):
        from ArbLocations import Location
        loc_id = ctx.options.get('location').split(' ')[0]
        print(loc_id)
        print(Location(loc_id).get_connections())
        connections = [f'{con_id.loc_id} - {Location(con_id.loc_id).label}' for con_id in Location(loc_id).process_connections()]
        return connections

    async def get_time_conds(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        time_conds = db.select_dict('DAYTIME_CONDS')
        return [f'{time_cond.get("id")} - {time_cond.get("label")}' for time_cond in time_conds]

    async def get_weather_conds(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        weather_conds = db.select_dict('WEATHER_CONDS')
        return [f'{weather_cond.get("id")} - {weather_cond.get("label")}' for weather_cond in weather_conds]

    async def get_loc_objects_types(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        objects = db.select_dict('LOC_OBJECTS_INIT')
        return [f'{object.get("id")} - {object.get("label")}' for object in objects]

    async def get_loc_objects(ctx: discord.AutocompleteContext):
        from ArbLocations import LocationObjectType

        db = DEFAULT_MANAGER
        loc_id = ctx.options.get('location').split(' ')[0]
        objects = db.select_dict('LOC_OBJECTS', filter=f'id = "{loc_id}"')
        return [f'{object.get("object_id")} - {LocationObjectType(object.get("type")).label}' for object in objects]

    async def get_all_skills(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        skills = db.select_dict('SKILL_INIT')
        return [f'{skill.get("id")} - {skill.get("label")}' for skill in skills]

    async def get_character_skills(ctx: discord.AutocompleteContext):
        from ArbSkills import SkillInit
        db = DEFAULT_MANAGER

        character = ctx.options.get('character')
        character_id = BasicCog.prepare_id(character)

        skills = db.select_dict('CHARS_SKILLS', filter=f'id = {character_id}')

        return [f'{skill.get("skill_id")} - {SkillInit(skill.get("skill_id")).label}' for skill in skills]

    async def get_templates(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        templates = db.select_dict('GEN_TEMPLATES')
        return [f'{template.get("id")} - {template.get("label")}' for template in templates]

    async def get_group_templates(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        templates = db.select_dict('GROUP_TEMPLATES')
        return [f'{template.get("id")} - {template.get("label")}' for template in templates]

    async def get_all_groups(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        groups = db.select_dict('GROUP_INIT')
        return [f'{group.get("id")} - {group.get("label")}' for group in groups]

    async def get_group_roles(ctx: discord.AutocompleteContext):
        db = DEFAULT_MANAGER
        group_roles = db.select_dict('GROUP_ROLES')
        return [f'{role.get("id")} - {role.get("label")}' for role in group_roles]

    @cfg_server.command(name='установить-валюту', description="Установить игровую валюту на сервере")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_currency(self, ctx, currency_tag: discord.Option(str)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)

        query = {'currency': currency_tag}

        db.update('SERVER_SETTINGS', query, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили знак валюты на сервере: ``{currency_tag}``')

    @cfg_server.command(name='чат-анкет', description="Установить чат, куда будут приходить анкеты игроков")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_regforms_chat(self, ctx, chat: discord.Option(discord.SlashCommandOptionType.channel)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)

        query = {'registration_chat': chat.id}

        db.update('SERVER_SETTINGS', query, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили чат для получения анкет регистрации: ``{chat}``')

    @cfg_server.command(name='ограничение-персонажей', description="Установить максимальное кол-во персонажей для всех игроков сервера")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_server_max_characters(self, ctx, value: discord.Option(discord.SlashCommandOptionType.integer, min_value=1)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)

        query = {'basic_max_characters': value}

        db.update('SERVER_SETTINGS', query, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили базовое максимальное количество персонажей игрока: ``{value}``')

    @cfg_server.command(name='ограничение-персонажей-игрока', description="Установить максимальное кол-во персонажей конкретного игрока")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_player_max_characters(self, ctx,
                                          player: discord.Option(discord.SlashCommandOptionType.user),
                                          value: discord.Option(discord.SlashCommandOptionType.integer, min_value=1)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)

        query = {'max_chars': value}

        db.update('PLAYERS_SERVERS', query, f'server_id = {ctx.guild.id} AND id = {player.id}')
        await self.cfg_response(ctx, f'Вы успешно установили максимальное количество персонажей {player.mention}: ``{value}``')

    @cfg_server.command(name='чат-рп-запросов', description="Установить чат, куда будут приходить РП-запросы игроков")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_response_chat(self, ctx, chat: discord.Option(discord.SlashCommandOptionType.channel)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)
        db.update('SERVER_SETTINGS', {'responses_chat': chat.id}, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили чат для получения запросов: ``{chat}``')

    @cfg_server.command(name='чат-обновлений', description="Чат куда будет приходить информация об обновлениях")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_features_chat(self, ctx, chat: discord.Option(discord.SlashCommandOptionType.channel)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)
        db.update('SERVER_SETTINGS', {'features_chat': chat.id}, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили чат для получения обновлений: ``{chat}``')

    @cfg.command(name='чат-модерации', description="Установить чат администрации")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_moderation_chat(self, ctx, chat: discord.Option(discord.SlashCommandOptionType.channel)):
        db = DEFAULT_MANAGER
        Server.register_server_if_not_exist(ctx.guild.id, data_manager=db)
        db.update('SERVER_SETTINGS', {'moderation_chat': chat.id}, f'id = {ctx.guild.id}')
        await self.cfg_response(ctx, f'Вы успешно установили модераторский чат: ``{chat}``')

    @register.command(name='текущие-анкеты', description="Вывести список активных анкет, ожидающих рассмотрения")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __regform_check(self, ctx,
                        form_id: discord.Option(int, required=False)):
        server = Server(ctx.guild.id)

        regforms = RegForm.get_all_forms_by_server(server.id)
        if not regforms:
            embed = ArbEmbed('Нет активных анкет', '-# На данный момент на сервере отсутствуют активные анкеты для рассмотрения')
            await ctx.respond('', embed=embed)
            return

        if form_id is None:
            embeds = [regform.to_embed() for regform in regforms]
            view = Paginator(embeds, ctx, ignore_footer=True)
            await ctx.respond('', embed=embeds[0], view=view)

        else:
            form = [regform for regform in regforms if regform.form_id == form_id]
            if not form:
                embed = ArbEmbed('Анкета не найдена',
                                 '-# Анкеты с таким ID не существует!')
                await ctx.respond('', embed=embed)
                return
            form = form[0]

            embed = form.to_embed()
            await ctx.respond('', embed=embed)

    @register.command(name='принять-анкету', description="Принять конкретную анкету или все анкеты на сервере")
    @BasicCog.admin_required
    async def __regform_accept(self, ctx,
                               form_id: discord.Option(int, required=False),
                               money: discord.Option(float, required=False, default=30_000),
                               skill_points: discord.Option(int, required=False, default=0),
                               skill_mods_points: discord.Option(float, required=False, default=0),
                               lvl: discord.Option(int, required=False, default=1),
                               exp: discord.Option(float, required=False, default=0)):

        server = Server(ctx.guild.id)
        regforms = RegForm.get_all_forms_by_server(server.id)

        if not regforms:
            embed = ArbEmbed('Нет активных анкет',
                             '-# На данный момент на сервере отсутствуют активные анкеты для рассмотрения')
            await ctx.respond('', embed=embed)
            return

        if form_id is None:
            embed = SuccessEmbed('Анкеты приняты', f'-# Все активные анкеты на сервере были приняты')
            await ctx.respond('', embed=embed)
            for regform in regforms:
                await regform.send_accept_embed(ctx)
                regform.accept(money=money, lvl=lvl, skill_points=skill_points, skill_mods_points=skill_mods_points, exp=exp)
                regform.delete_form()
        else:
            form = [regform for regform in regforms if regform.form_id == form_id]
            if not form:
                embed = ArbEmbed('Анкета не найдена',
                                 '-# Анкеты с таким ID не существует!')
                await ctx.respond('', embed=embed)
                return
            form = form[0]
            await form.send_accept_embed(ctx)
            await form.send_accept_respond(ctx)
            form.accept(money=money, lvl=lvl, skill_points=skill_points, skill_mods_points=skill_mods_points, exp=exp)
            form.delete_form()

    @register.command(name='отклонить-анкету', description="Отклонить конкретную анкету или все анкеты на сервере")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __regform_deny(self, ctx,
                             reason: discord.Option(str, required=True),
                             form_id: discord.Option(int, required=False)):
        server = Server(ctx.guild.id)

        regforms = RegForm.get_all_forms_by_server(server.id)
        if not regforms:
            embed = ArbEmbed('Нет активных анкет',
                             '-# На данный момент на сервере отсутствуют активные анкеты для рассмотрения')
            await ctx.respond('', embed=embed)
            return

        if form_id is None:
            embed = SuccessEmbed('Анкеты отклонены',
                                 f'-# Все активные анкеты на сервере были отклонены по причине:\n```{reason}```')
            await ctx.respond('', embed=embed)
            for regform in regforms:
                await regform.send_deny_embed(ctx, reason)
                regform.delete_form()
        else:
            form = [regform for regform in regforms if regform.form_id == form_id]
            if not form:
                embed = ArbEmbed('Анкета не найдена',
                                 '-# Анкеты с таким ID не существует!')
                await ctx.respond('', embed=embed)
                return
            form = form[0]
            await form.send_deny_embed(ctx, reason)
            await form.send_deny_respond(ctx, reason)
            form.delete_form()

    @commands.slash_command(name='рп-запросы', description="Узнать активные РП-запросы от игроков")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __rp_requests(self, ctx):
        from ArbCore import RPRequest

        requests = RPRequest.get_all_requests(ctx.guild.id)
        embeds = [embed.to_embed(ctx) for embed in requests]
        view = Paginator(embeds, ctx)

        await ctx.respond('', view=view, embed=embeds[0])

    @commands.slash_command(name='закрыть-запрос', description="Закрыть РП-запрос")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __rp_close(self, ctx, request_id: int):
        from ArbCore import RPRequest

        request = RPRequest.get_request_by_id(request_id)
        if request is None:
            embed = ErrorEmbed('Запрос не найден', f'-# Запрос с данным идентификатором ||{request_id}|| не был найден в базе данных!')
            await ctx.respond('', embed=embed)
            return

        request.delete_record()
        embed = SuccessEmbed('Запрос закрыт', f'-# Запрос с идентификатором ||{request_id}|| был успешно закрыт!')
        await ctx.respond('', embed=embed)

    @commands.slash_command(name='закрыть-все-запросы', description="Закрыть все активные РП-запросы")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __close_all_requests(self, ctx):
        from ArbCore import RPRequest

        requests = RPRequest.get_all_requests(ctx.guild.id)
        for request in requests:
            request.delete_record()
        embed = SuccessEmbed('Все запросы закрыты', f'-# Все запросы на сервере **{ctx.guild.name}** были успешно закрыты!')
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-бой', description="Изменить бой")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_battle(self, ctx,
                           battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                           label: discord.Option(str, required=False),
                           desciption: discord.Option(str, required=False),
                           distance: discord.Option(int, required=False),
                           time: discord.Option(str, autocomplete=AAC.db_call('DAYTIME_CONDS', 'label'), required=False),
                           weather: discord.Option(str, autocomplete=AAC.db_call('WEATHER_CONDS', 'label'),required=False),
                           round: discord.Option(int, required=False),
                           key_rounds: discord.Option(int, required=False),
                           last_round: discord.Option(int, required=False),
                           battle_type: discord.Option(str, autocomplete=AAC.db_call('BATTLE_CONDITIONS', 'label'), required=False),
                           battle_type_value: discord.Option(str, required=False)):

        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id)

        label = label if label else battlefield.label
        desciption = desciption if desciption else battlefield.description
        distance = distance if distance else battlefield.distance_delta
        time = AAC.extract('DAYTIME_CONDS', 'label', time, 'id') if time else battlefield.time.id
        weather = AAC.extract('WEATHER_CONDS', 'label', weather, 'id') if weather else battlefield.weather.id
        round = round if round else battlefield.round
        key_rounds = key_rounds if key_rounds else battlefield.key_round_delay
        battle_type = AAC.extract('BATTLE_CONDITIONS', 'lable', battle_type, 'id') if battle_type else battlefield.battle_type
        battle_type_value = battle_type_value if battle_type_value else battlefield.type_value
        last_round = last_round if last_round else battlefield.last_round

        battlefield.update_battle(label=label,
                                  distance=distance,
                                  desc=desciption,
                                  time=time,
                                  weather=weather,
                                  round=round,
                                  key_round=key_rounds,
                                  battle_type=battle_type,
                                  type_value=battle_type_value,
                                  last_round=last_round)

        battlefield = Battlefield(battle_id)
        label, battle_info = battlefield.describe()
        embed = ArbEmbed(f'{label}', battle_info)

        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-слой-боя', description="Изменить настройки слоя выбранного боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_layer(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=True),
                          label: discord.Option(str, required=False),
                          terrain: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TERRAIN_TYPE', 'label')), required=False),
                          height: discord.Option(int, required=False)):
        battle_id = int(battle.split(' ')[0])
        layer_id = int(layer.split(' ')[0])

        battlefield = Battlefield(battle_id)
        layer = battlefield.get_layers().get(layer_id)

        label = label if label else layer.label
        terrain = AAC.extract('TERRAIN_TYPE', 'label', terrain, 'id') if terrain else layer.terrain.id
        height = height if height else layer.height

        layer.update_record({'label': label, 'terrain_type': terrain, 'height': height})
        layer = battlefield.get_layers().get(layer_id)

        embed = ArbEmbed(f'{layer.label}', f'-# > *Тип слоя: **{layer.terrain.label}***\n-# *Высота: **{layer.height}***', footer=f'{battlefield.label}')
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-объект-боя', description="Изменить настройки объекта боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_object(self, ctx,
                           battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                           object: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_objects), required=True),
                           type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('OBJECT_TYPE', 'label')), required=False),
                           endurance: discord.Option(int, required=False),
                           uses: discord.Option(int, required=False),
                           captured: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False)):
        battle_id = int(battle.split(' ')[0])
        object_id = int(object.split(' ')[0])

        battlefield = Battlefield(battle_id)
        object = GameObject(object_id)

        object_type = AAC.extract('OBJECT_TYPE', 'label', type, 'object_id') if type else object.object_type.object_id
        print(object_type)
        endurance = endurance if endurance else object.current_endurance
        uses = uses if uses else object.uses
        captured = captured.split(' ')[0] if captured else object.captured

        object.edit(object_type=object_type,
                    endurance=endurance,
                    uses=uses,
                    captured=captured)

        object = GameObject(object_id)

        embed = ArbEmbed(f'{object.object_type.label} ({object_id})', f'-# > *Тип объекта: **{object.object_type.label}***\n'
                                                                      f'-# > *Прочность: **{object.current_endurance}***\n'
                                                                      f'-# > *Кол-во использований: **{object.uses} / {object.object_type.max_uses}***\n'
                                                                      f'-# > *Захвачен: **{BattleTeam(object.captured).label if object.captured else "||Не захвачен||"}***',
                         footer=f'{battlefield.label}')

        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-команду', description="Изменить настройки команды внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_team(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=True),
                          label: discord.Option(str, required=False),
                          role: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TEAM_ROLES', 'label')), required=False),
                          commander: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                          coordinator: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                          com_points: discord.Option(int, required=False),
                          activity: discord.Option(bool, required=False),
                          dialogue: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_dialogues), required=False),
                          win_points: discord.Option(int, required=False)):

        db = DEFAULT_MANAGER
        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id, data_manager=db)

        team_id = int(team.split(' ')[0])
        team = BattleTeam(team_id, data_manager=db)

        label = label if label else team.label
        role = AAC.extract('TEAM_ROLES', 'label', role, 'id') if role else team.role.role_id
        commander = int(commander.split(' ')[0]) if commander else team.commander_id
        coordinator = int(coordinator.split(' ')[0]) if coordinator else team.coordinator_id
        com_points = com_points if com_points else team.command_points
        activity = int(activity) if activity is not None else team.is_active
        dialogue = int(dialogue.split(' ')[0]) if dialogue else team.get('dialogue_id')

        team.update_record(
            {
            'label': label,
            'role': role,
            'commander': commander,
            'coordinator': coordinator,
            'com_points': com_points,
            'round_active': activity,
            'dialogue_id': dialogue,
            'win_points': win_points,
        })

        team = BattleTeam(team_id, data_manager=db)
        embed = ArbEmbed(f'{team.label} ({team_id})',
                         f'-# > *Роль: **{team.role.get("label")}***\n'
                         f'-# > *Командир: **||{f"{Character(team.commander_id).name} ({team.commander_id})" if team.commander_id else "Отсутствует"}||***\n'
                         f'-# > *Координатор: **||{f"{Character(team.coordinator_id).name} ({team.coordinator_id})" if team.coordinator_id else "Отсутствует"}||***\n'
                         f'-# > *Очков командования: **{team.command_points} ОК.***\n'
                         f'-# > *Активность: **{team.is_active == 1}***\n'
                         f'-# > *Очков победы: **{win_points}***\n'
                         f'-# > *Чат диалога команды: **{ctx.bot.get_channel(Dialogue(team.get("dialogue_id")).channel).mention if team.get("dialogue_id") else "||Отсутствует||"}***',
                         footer=battlefield.label)
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-звук', description="Изменить настройки звука")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_sound(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          sound: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_sounds), required=True),
                          actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                          sound_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('SOUNDS', 'label')), required=False),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False),
                          volume: discord.Option(int, required=False),
                          content: discord.Option(str, required=False)):
        from ArbSounds import InBattleSound

        db = DEFAULT_MANAGER
        battle_id = int(battle.split(' ')[0])
        battlefield = Battlefield(battle_id, data_manager=db)
        sound_id = int(sound.split(' ')[0])
        sound = InBattleSound(sound_id, data_manager=db)

        actor_id = int(actor.split(' ')[0]) if actor else sound.actor_id
        sound_type = AAC.extract('SOUNDS', 'label', sound_type, 'id') if sound_type else sound.sound_id
        layer_id = int(layer.split(' ')[0]) if layer else sound.layer_id
        volume = volume if volume else sound.volume
        content = content if content else sound.content

        sound.update_record({
            'actor_id': actor_id,
            'sound_id': sound_type,
            'layer_id': layer_id,
            'volume': volume,
            'content': content,
        })

        sound = InBattleSound(sound_id, data_manager=db)
        embed = ArbEmbed(f'Звук - {sound.label} ({sound_id})',
                         f'-# > *Персонаж: **||{f"{Character(sound.actor_id).name} ({sound.actor_id})" if sound.actor_id else "Отсутствует"}||***\n'
                         f'-# > *Тип звука: **{sound.label}***\n'
                         f'-# > *Слой: **{sound.layer_id}***\n'
                         f'-# > *Содержание: **{sound.content}***')
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-участника-боя', description="Изменить настройки участника боя")
    @BasicCog.admin_required
    async def __set_actor(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_actors), required=True),
                          team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False),
                          object: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_layer_objects), required=False),
                          initiative: discord.Option(int, required=False),
                          status: discord.Option(str, choices=['Активен', 'Неактивен', 'Ожидает очередь'], required=False),
                          height: discord.Option(int, min_value=0, max_value=1000, required=False)):
        battle_id = int(battle.split(' ')[0])
        actor_id = int(actor.split(' ')[0])

        db = DEFAULT_MANAGER
        actor = Actor(actor_id)

        team_id = team.split(' ')[0] if team else actor.team_id
        layer_id = layer.split(' ')[0] if layer else actor.layer_id
        object_id = object.split(' ')[0] if object else actor.object_id
        initiative = initiative if initiative else actor.initiative
        statuses = {'Активен': 1, 'Неактивен': 0, 'Ожидает очередь': None}
        to_status = {1: 'Активен', 0: 'Неактивен', None: 'Ожидает очередь'}
        status = statuses.get(status) if status else actor.is_active
        height = height if height else actor.fly_height

        actor.update_record({
            'team_id': team_id,
            'layer_id': layer_id,
            'object': object_id,
            'initiative': initiative,
            'is_active': status,
            'height': height})

        actor = Actor(actor_id)
        embed = ArbEmbed(f'Участник боя - {Character(actor_id).name} ({actor_id})',
                         f'-# > *Команда: **{BattleTeam(team_id).label} ({team_id})***\n'
                         f'-# > *Слой: **{Layer(battle_id=battle_id, id=layer_id).label} ({layer_id})***\n'
                         f'-# > *Объект: **{GameObject(object_id).object_type.label if object_id else "||Отсутствует||"} ({object_id})***\n'
                         f'-# > *Инициатива: **{actor.initiative}***\n'
                         f'-# > *Статус: **{to_status.get(actor.is_active)}***\n'
                         f'-# > *Высота полёта: **{actor.fly_height} м.***')
        embed.set_author(Character(actor_id).name, icon_url=Character(actor_id).picture)
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-мертвых', description="Изменить настройки мертвого участника боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_dead(self, ctx,
                         battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                         actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_dead), required=True),
                         layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False),
                         killer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                         team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False),
                         reason: discord.Option(str, required=False)):
        from ArbDatabase import DataModel

        battle_id = int(battle.split(' ')[0])
        actor_id = int(actor.split(' ')[0])
        db = DEFAULT_MANAGER

        dead_data = DataModel('BATTLE_DEAD', f'character_id = {actor_id}', data_manager=db)

        layer_id = int(layer.split(' ')[0]) if layer else dead_data.get('layer_id')
        killer = int(killer.split(' ')[0]) if killer else dead_data.get('killer')
        team_id = team.split(' ')[0] if team else dead_data.get('team_id')
        reason = reason if reason else dead_data.get('reason')

        dead_data.update_record(
            {
                'layer_id': layer_id,
                'killer': killer,
                'team_id': team_id,
                'reason': reason
            })

        embed = ArbEmbed(f'Мёртвый участник боя - {Character(actor_id).name} ({actor_id})',
                         f'-# > *Слой: **{Layer(battle_id=battle_id, id=layer_id).label} ({layer_id})***\n'
                         f'-# > *Убийца: **{Character(killer).name if killer else "Неизвестен"}***\n'
                         f'-# > *Команда: **{BattleTeam(team_id).label if team_id else "Отсутствует"}***\n'
                         f'-# > *Причина смерти: **{reason}***')

        embed.set_author(Character(actor_id).name, icon_url=Character(actor_id).picture)
        await ctx.respond('', embed=embed)

    @cfg_battle.command(name='изменить-ловушку', description="Изменить настройки ловушки боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __set_trap(self, ctx,
                         battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                         trap: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_traps), required=True),
                         layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False),
                         type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TRAPS_INIT', 'label')), required=False),
                         baff: discord.Option(int, min_value=0, max_value=100, required=False)):
        from ArbDatabase import DataModel
        from ArbWeapons import TrapInit

        battle_id = int(battle.split(' ')[0])
        trap_id = int(trap.split(' ')[0])
        db = DEFAULT_MANAGER

        trap_data = DataModel('BATTLE_TRAPS', f'trap_id = {trap_id}')
        layer_id = int(layer.split(' ')[0]) if layer else trap_data.get('layer_id')
        type_id = AAC.extract('TRAPS_INIT', "label", type, "id") if type else trap_data.get('type')
        print(type_id)
        baff = baff if baff else trap_data.get('buff')

        trap_data.update_record(
            {
                'layer_id': layer_id,
                'type': type_id,
                'buff': baff})

        embed = ArbEmbed(f'Ловушка - {TrapInit(type_id).label}',
                         f'-# > *Слой: **{Layer(battle_id=battle_id, id=layer_id).label} ({layer_id})***\n'
                         f'-# > *Тип ловушки: **{TrapInit(type_id).label}***\n'
                         f'-# > *Инженерный бонус: **{baff}%***')

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='создать-ловушку', description="Сознать новую ловушку внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __create_trap(self, ctx,
                            battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                            layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=True),
                            type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TRAPS_INIT', 'label')), required=False),
                            baff: discord.Option(int, min_value=0, max_value=100, required=False),
                            value: discord.Option(int, default=1, required=False)):

        from ArbWeapons import TrapInit

        battle_id = int(battle.split(' ')[0])
        layer_id = int(layer.split(' ')[0])
        type_id = AAC.extract('TRAPS_INIT', "label", type, "id") if type else None
        baff = baff if baff else None

        battlefield = Battlefield(battle_id)
        layer = battlefield.get_layers().get(layer_id)


        layer.add_trap(type_id, baff, value)

        embed = SuccessEmbed('Созданы ловушки',
                             f'*{ctx.author.mention} создал ловушки **{TrapInit(type_id).label}** с бонусом инженерии ``{baff if baff else 0}%`` на слое **{layer.label} ({layer_id})** в количестве``{value}``*',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='добавить-звук', description="Создать новый звук внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_sound(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          sound_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('SOUNDS', 'label')), required=True),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers),required=True),
                          actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_actors), required=False),
                          volume: discord.Option(int, required=False),
                          content: discord.Option(str, required=False)):

        battle_id = BasicCog.prepare_id(battle)
        sound_type_id = AAC.extract('SOUNDS', 'label', sound_type, 'id')
        layer_id = BasicCog.prepare_id(layer)
        actor_id = BasicCog.prepare_id(actor) if actor else None
        volume = volume if volume else random.randint(50, 150)
        content = content if content else None

        battlefield = Battlefield(battle_id)
        sound = battlefield.add_sound(sound_type_id, actor_id, layer_id, volume, content)

        embed = SuccessEmbed('Добавлен звук',
                             f'*{ctx.author.mention} добавил звук **{sound.label} ({sound.id})** громкостью ``{sound.volume}%`` {f"от персонажа **{Character(sound.actor_id).name}** " if actor_id else ""}на слой **{Layer(battle_id=battle_id, id=layer_id).label}**.{f" Содержание: {sound.content}" if sound.content else ""}*')

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-звук', description="Удалить звук боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_sound(self, ctx,
                              battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                              sound: discord.Option(int, autocomplete=discord.utils.basic_autocomplete(get_all_sounds), required=True)):
        from ArbSounds import InBattleSound

        battle_id = BasicCog.prepare_id(battle)
        sound_id = BasicCog.prepare_id(sound)
        sound = InBattleSound(sound_id).delete()

        embed = SuccessEmbed('Удален звук',
                             f'*{ctx.author.mention} удалил звук **{sound.label}** ({sound.id})*{f" от персонажа **{Character(sound.actor_id).name}** " if sound.actor_id else ""}на слою **{Layer(battle_id=battle_id, id=sound.layer_id).label}**.*')

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='добавить-команду', description="Добавить новую команду внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_team(self, ctx,
                         battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                         label: discord.Option(str, required=False, default=f'Неизвестные бойцы'),
                         role: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TEAM_ROLES', 'label')), required=False, default='Участники'),
                         commander: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                         coordinator: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=False),
                         com_points: discord.Option(int, min_value=0, required=False, default=0),
                         activity: discord.Option(bool, required=False, default=True),
                         dialogue: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_dialogues), required=False, default=None),
                         win_points: discord.Option(int, min_value=0, required=False, default=0)):

        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)

        role_id = AAC.extract('TEAM_ROLES', 'label', role, 'id')
        team = battlefield.create_team(label, role_id)
        team.update_record({
            'commander': BasicCog.prepare_id(commander) if commander else None,
            'coordinator': BasicCog.prepare_id(coordinator) if coordinator else None,
            'com_points': com_points,
            'round_active': int(activity),
            'dialogue_id': BasicCog.prepare_id(dialogue) if dialogue else None,
            'win_points': win_points,
        })

        team = BattleTeam(team.id)
        embed = SuccessEmbed(f'Создана команда {team.label} ({team.id})',
                             f'-# > *Роль: **{AAC.extract("TEAM_ROLES", "id", team.role.role_id, "label")}***\n'
                             f'-# > *Командир: **{f"||{Character(team.commander_id).name} ({team.commander_id})||" if team.commander_id else "||Отсутствует||"}***\n'
                             f'-# > *Координатор: **{f"||{Character(team.coordinator_id).name} ({team.coordinator_id})||" if team.coordinator_id else "||Отсутствует||"}***\n'
                             f'-# > *Очки командования: **{team.command_points} ОК.***\n'
                             f'-# > *Активность: **{bool(team.is_active)}***\n'
                             f'-# > *Очков победы: **{team.winpoints}***\n'
                             f'-# > *Диалог команды: **{ctx.guild.get_channel(Dialogue(team.get("dialogue")).channel).mention if team.get("dialogue") else "||Отсутствует||"}***')
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-команду', description="Удалить одну из команд в бою")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_team(self, ctx,
                             battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                             team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=True)):
        team_id = BasicCog.prepare_id(team)
        old_team = BattleTeam(team_id)
        old_team.delete_team()

        embed = SuccessEmbed(f'Удалена команда {old_team.label} ({team_id})',
                             f'*{ctx.author.mention} удалил команду **{old_team.label}** из боя **{battle}**.*',
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='добавить-слой', description="Создать новый слой внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_layer(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          terrain: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TERRAIN_TYPE', 'label')), required=True),
                          label: discord.Option(str, required=False),
                          height: discord.Option(int, required=False, default=0),
                          generate_objects: discord.Option(int, required=False, min_value=0, default=0)):

        from ArbGenerator import GenerateLayer

        battle_id = BasicCog.prepare_id(battle)
        terrain_id = AAC.extract('TERRAIN_TYPE', 'label', terrain, 'id')

        battlefield = Battlefield(battle_id)
        layer_id = max(list(battlefield.get_layers().keys())) + 1 if battlefield.get_layers() else 0

        new_layer = GenerateLayer(battle_id, layer_id, terrain_id, label=label, height=height, num_of_objects=generate_objects if generate_objects else 0)
        new_layer.insert_data()

        embed = SuccessEmbed(f'Создан слой {new_layer.label} ({new_layer.id})',
                             f'-# > *Тип земли: **{terrain}***\n'
                             f'-# > *Название слоя: **{new_layer.label}***\n'
                             f'-# > *Высота слоя: **{new_layer.height}***\n'
                             f'-# > *Количество объектов: **{len(new_layer.objects)}***')
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-слой', description="Удалить слой внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_layer(self, ctx,
                              battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                              layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=True)):

        battle_id = BasicCog.prepare_id(battle)
        layer_id = BasicCog.prepare_id(layer)

        battlefield = Battlefield(battle_id)
        battlefield.delete_layer(layer_id)

        embed = SuccessEmbed(f'Удален слой {layer_id}',
                             f'*{ctx.author.mention} удалил слой **{layer_id}** из боя **{battle}**.*',
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='добавить-объект', description="Создать новый объект внутри боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_object(self, ctx,
                           battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                           layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=True),
                           type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('OBJECT_TYPE', 'label')), required=True),
                           endurance: discord.Option(int, required=False, min_value=1, default=None),
                           uses: discord.Option(int, required=False, default=None),
                           captured: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False, default=None),
                           amount: discord.Option(int, min_value=0, required=False, default=1)):
        from ArbGenerator import GenerateObject

        battle_id = BasicCog.prepare_id(battle)
        layer_id = BasicCog.prepare_id(layer)
        type_id = AAC.extract('OBJECT_TYPE', 'label', type, 'object_id')

        endurance = endurance if endurance else None
        captured_team_id = BasicCog.prepare_id(captured) if captured else None

        for i in range(amount):
            new_object = GenerateObject(type_id, battle_id, layer_id, endurance=endurance, uses=uses, captured=captured_team_id)
            new_object.insert_data()

        embed = SuccessEmbed(f'Создано {amount} объектов {type} на слое {layer}',
                             f'-# > *Тип объекта: **{type}***\n'
                             f'-# > *Стойкость объекта: **{endurance if endurance else "Не указано"}***\n'
                             f'-# > *Использование объекта: **{uses if uses else "Не указано"}***\n'
                             f'-# > *Захвачен командой: **{BattleTeam(captured_team_id).label if captured_team_id else "||Отсутствует||"}***')
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-объект', description="Удалить объект боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_object(self, ctx,
                              battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                              object: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_objects), required=True)):
        battle_id = BasicCog.prepare_id(battle)
        object_id = BasicCog.prepare_id(object)

        old_object = GameObject(object_id)
        old_object.delete_object()

        embed = SuccessEmbed(f'Удален объект {object_id}',
                             f'*{ctx.author.mention} удалил объект **{old_object.object_type.label} ({object_id})** из боя **{battle}**.*',
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-мертвого-участника', description="Удалить мёртвого участника боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_dead(self, ctx,
                            battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                            actor: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_battle_dead))):
        from ArbDatabase import DataModel
        battle_id = BasicCog.prepare_id(battle)
        actor_id = BasicCog.prepare_id(actor)

        model = DataModel('BATTLE_DEAD', f'character_id = {actor_id} AND battle_id = {battle_id}')
        model.delete_record()

        embed = SuccessEmbed(f'Удален мертвый участник {Character(actor_id).name} ({actor_id})',
                             f'*{ctx.author.mention} удалил мертвого участника **{actor}** из боя **{battle}**.*',
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-участника-боя', description="Удалить участника боя (вывести из боя)")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_actor(self, ctx,
                             battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                             actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_actors), required=True)):
        from ArbDatabase import DataModel
        battle_id = BasicCog.prepare_id(battle)
        actor_id = BasicCog.prepare_id(actor)

        model = DataModel('BATTLE_CHARACTERS', f'character_id = {actor_id} AND battle_id = {battle_id}')
        model.delete_record()
        model.data_manager.update('BATTLE_SOUNDS', {'actor_id': None}, f'actor_id = {actor_id}')

        embed = SuccessEmbed(f'Удален участник боя {Character(actor_id).name} ({actor_id})',
                             f'*{ctx.author.mention} удалил участника **{actor}** из боя **{battle}**.*',
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)


    @cfg_battle.command(name='добавить-участника-боя', description="Добавить нового участиника боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_actor(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False, default=None),
                          object: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layer_objects), required=False, default=None),
                          team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False, default=None),
                          initiative: discord.Option(int, min_value=1, required=False, default=random.randint(1, 100)),
                          activity: discord.Option(str, choices=['Активен', 'Неактивен', 'Ожидает очередь'], required=False, default='Ожидает очередь'),
                          height: discord.Option(int, min_value=0, default=0, required=True)):

        battle_id = BasicCog.prepare_id(battle)
        character_id = BasicCog.prepare_id(character)

        layer_id = BasicCog.prepare_id(layer) if layer else 0
        object_id = BasicCog.prepare_id(object) if object else None
        team_id = BasicCog.prepare_id(team) if team else None
        if team_id:
            initiative += BattleTeam(team_id).role.initiative_bonus

        statuses = {'Активен': 1, 'Неактивен': 0, 'Ожидает очередь': None}
        to_status = {1: 'Активен', 0: 'Неактивен', None: 'Ожидает очередь'}

        battlefield = Battlefield(battle_id)
        battlefield.add_actor(character_id, layer=layer_id, team_id=team_id, object=object_id, initiative=initiative, is_active=statuses.get(activity), height=height)

        actor = Actor(character_id)

        embed = SuccessEmbed(f'Добавлен участник боя {Character(character_id).name} ({character_id})',
                             f'-# > *Слой: **{Layer(actor.layer_id, battle_id).label} ({layer_id})***\n'
                             f'-# > *Укрытие: **{f"{GameObject(object_id).object_type.label} ({object_id})" if object_id else "Отсутствует"}***\n'
                             f'-# > *Команда: **{BattleTeam(team_id).label if team_id else "Отсутствует"}***\n'
                             f'-# > *Инициатива: **{actor.initiative}***\n'
                             f'-# > *Активность: **{to_status.get(actor.is_active)}***\n'
                             f'-# > *Высота полёта: **{actor.fly_height} м.***',
                             footer_logo=Character(character_id).picture)
        await ctx.respond(embed=embed)

    @cfg_battle.command(name='добавить-группу-в-бой', description="Ввести в бой существующий отряд")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_group(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          group: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_groups), required=True),
                          layer: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_layers), required=False, default=None),
                          team: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_teams), required=False, default=None),
                          activity: discord.Option(str, choices=['Активен', 'Неактивен', 'Ожидает очередь'], required=False, default='Ожидает очередь')):
        from ArbGroups import Group

        battle_id = BasicCog.prepare_id(battle)
        group_id = BasicCog.prepare_id(group)
        characters = [m.get("id") for m in Group(group_id).fetch_group_members()]

        layer_id = BasicCog.prepare_id(layer) if layer else 0
        object_id = None
        team_id = BasicCog.prepare_id(team) if team else None
        if team_id:
            initiative_baff = BattleTeam(team_id).role.initiative_bonus
        else:
            initiative_baff = 0

        statuses = {'Активен': 1, 'Неактивен': 0, 'Ожидает очередь': None}
        to_status = {1: 'Активен', 0: 'Неактивен', None: 'Ожидает очередь'}

        battlefield = Battlefield(battle_id)
        for member in characters:
            battlefield.add_actor(member, layer=layer_id, team_id=team_id, object=object_id, initiative=random.randint(1, 100) + initiative_baff,
                                  is_active=statuses.get(activity), height=0)
        chars_names = [Character(m).name for m in characters]
        actor = Actor(characters[0])
        embed = SuccessEmbed(f'Добавлены участники боя {battle}',
                             f'**{", ".join(chars_names)}**\n'
                             f'-# > *Слой: **{Layer(actor.layer_id, battle_id).label} ({layer_id})***\n'
                             f'-# > *Команда: **{BattleTeam(team_id).label if team_id else "Отсутствует"}***\n'
                             f'-# > *Активность: **{to_status.get(actor.is_active)}***\n',
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)


    @cfg_battle.command(name='новый-бой', description="Создать новый пустой бой")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __create_battle(self, ctx,
                              label: discord.Option(str, required=False, default='Безымянное сражение'),
                              description: discord.Option(str, required=False, default='Столкновение сторон в жестокой схватке'),
                              distance_delta: discord.Option(int, min_value=1, required=False, default=50),
                              time: discord.Option(str,
                                                   autocomplete=discord.utils.basic_autocomplete(AAC.db_call('DAYTIME_CONDS', 'label')),
                                                   required=False,
                                                   default=AAC.extract('DAYTIME_CONDS', 'id', TimeManager().get_current_time_condition(), 'label')),
                              weather: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('WEATHER_CONDS', 'label')),
                                                      required=False,
                                                      default='Солнечно'),
                              round: discord.Option(int, min_value=1, required=False, default=1),
                              key_round_delay: discord.Option(int, min_value=1, required=False, default=3),
                              last_round: discord.Option(int, min_value=1, required=False, default=None),
                              battle_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('BATTLE_CONDITIONS', 'label')), required=False, default='Столкновение'),
                              battle_type_value: discord.Option(str, required=False, default=None)):

        battle_id = DEFAULT_MANAGER.maxValue('BATTLE_INIT', 'id') + 1
        query = {
            'id': battle_id,
            'label': label,
            'desc': description,
            'distance_delta': distance_delta,
            'time_type': AAC.extract('DAYTIME_CONDS', 'label', time, 'id'),
            'weather_type': AAC.extract('WEATHER_CONDS', 'label', weather, 'id'),
            'round': round,
            'key_round': key_round_delay,
            'last_round': last_round,
            'battle_type': AAC.extract('BATTLE_CONDITIONS', 'label', battle_type, 'id'),
            'type_value': battle_type_value
        }

        DEFAULT_MANAGER.insert('BATTLE_INIT', query)

        embed = SuccessEmbed(f'Создано новое сражение {label} ({battle_id})',
                             f'-# > *Название: **{label}***\n'
                             f'-# > *Описание: **{description}***\n'
                             f'-# > *Расстояние между слоями: **{distance_delta} м.***\n'
                             f'-# > *Время суток: **{time}***\n'
                             f'-# > *Погодные условия: **{weather}***\n'
                             f'-# > *Текущий раунд: **{round}***\n'
                             f'-# > *Сброс инициативы каждые: **{key_round_delay} раундов***\n'
                             f'-# > *Последний раунд: **{last_round if last_round else "Не установлен"}***\n'
                             f'-# > *Тип боя: **{battle_type}***\n'
                             f'-# > *Условие типа боя: **{battle_type_value if battle_type_value else "Не установлено"}***',
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='удалить-бой', description="Удалить один из активных боёв")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_battle(self, ctx, battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True)):

        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)

        battlefield.delete_battle()
        embed = SuccessEmbed(f'Удалено сражение {battlefield.label} ({battle_id})',
                             f'*{ctx.author.mention} успешно удалил сражение {battle}*',
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_battle.command(name='изменить-параметры-участника', description="Изменить настройки участника боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __edit_actor_combat(self, ctx,
                                 actor: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                                 ap: discord.Option(int, min_value=0, max_value=100, required=False, default=None),
                                 ap_bonus: discord.Option(int, min_value=0, max_value=100, required=False, default=None),
                                 current_target: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_actors_by_actor)),
                                 current_melee_target: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_actors_by_actor)),
                                 suppressing: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_objects_by_actor)),
                                 hunting: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_actors_by_actor)),
                                 containing: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_layers_by_actor)),
                                 overwatch: discord.Option(bool, required=False, default=None)):

        from ArbDatabase import DataModel

        character_id = BasicCog.prepare_id(actor)
        battle_id = Battlefield.get_actor_battle(character_id)
        model = DataModel('CHARS_COMBAT', f'id = {character_id}')

        query = {
            'ap': ap if ap is not None else model.get('ap'),
            'ap_bonus': ap_bonus if ap_bonus is not None else model.get('ap_bonus'),
            'target': BasicCog.prepare_id(current_target) if current_target else model.get('target'),
            'melee_target': BasicCog.prepare_id(current_melee_target) if current_melee_target else model.get('melee_target'),
            'ready': overwatch,
            'supressed': BasicCog.prepare_id(suppressing) if suppressing else None,
            'hunted': BasicCog.prepare_id(hunting) if hunting else None,
            'contained': BasicCog.prepare_id(containing) if containing else None
        }
        DEFAULT_MANAGER.update('CHARS_COMBAT', query, f'id = {character_id}')
        model = DataModel('CHARS_COMBAT', f'id = {character_id}')

        embed = SuccessEmbed(f'Изменены параметры участника боя {Character(character_id).name} ({character_id})',
                             f'-# > *Очки действия: **{model.get("ap")} (+{model.get("ap_bonus")})***\n'
                             f'-# > *Текущая цель дальнего боя: **{Character(model.get("target")).name if model.get("target") else "Отсутствует"}***\n'
                             f'-# > *Текущая цель ближнего боя: **{Character(model.get("melee_target")).name if model.get("melee_target") else "Отсутствует"}***\n'
                             f'-# > *Находится в дозоре: **{overwatch}***\n'
                             f'-# > *Подавляет укрытие: **{suppressing if suppressing else "—"}***\n'
                             f'-# > *Сдерживает слой: **{containing if containing else "—"}***\n'
                             f'-# > *Охотится на персонажа: **{hunting if hunting else "—"}***',
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_battle.command(name='следующий-ход', description="Закончить текущий ход и начать новый")
    @BasicCog.admin_required
    async def __next_turn(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                          take_actor_control: discord.Option(bool, default=True, required=False)):

        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)

        result = battlefield.next_actor()
        await Notification.send_all_notifications(ctx)

        if take_actor_control:
            await self.__current_actor(ctx, battle)

        embeds = result.get_embeds()
        view = Paginator(embeds, ctx)
        await view.update_button()

        await ctx.respond(embed=embeds[0], view=view)

    @mng_battle.command(name='закончить-раунд', description="Принудительно закончить текущий раунд")
    @BasicCog.admin_required
    async def __end_round(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True)):
        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)

        is_end, result = battlefield.next_round()
        embeds = result.get_embeds()
        view = Paginator(embeds, ctx)
        await view.update_button()

        await ctx.respond(embed=embeds[0], view=view)

    @mng_battle.command(name='завершить-бой', description="Принудительно завершить бой")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __end_battle(self, ctx,
                          battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True)):
        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)
        result = battlefield.end_battle()
        embeds = result.get_embeds()
        view = Paginator(embeds, ctx)
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @mng_battle.command(name='действующий-персонаж', description="Взять управление над активным персонажем боя")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __current_actor(self, ctx,
                              battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True)):
        from ArbCore import Player

        battle_id = BasicCog.prepare_id(battle)
        current_actor = DEFAULT_MANAGER.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {battle_id} AND is_active = 1')
        if not current_actor:
            await ctx.respond(embed=ErrorEmbed('Нет активного персонажа', '*На текущий момент нет активного персонажа в бою.*'))
            return

        character_id = current_actor[0].get('character_id')
        Player(ctx.author.id).switch_character(character_id)
        await ctx.respond(embed=SuccessEmbed('Управление', f'*{ctx.author.mention}, вы управляете активным персонажем: **{Character(character_id).name} ({character_id})** в бою **{battle}***'), ephemeral=True)

    @mng_battle.command(name='воскресить-персонажа', description="Воскресить персонажа из мертвых в бою")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __revive_character(self, ctx,
                                 battle: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(active_battles), required=True),
                                 character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_battle_dead), required=True)):
        battle_id = BasicCog.prepare_id(battle)
        battlefield = Battlefield(battle_id)
        character_id = BasicCog.prepare_id(character)
        Battlefield.revive_actor(character_id)
        await ctx.respond(embed=SuccessEmbed('Воскрешение', f'***{Character(character_id).name} ({character_id})** воскрес в бою **{battle}***', footer=ctx.author.display_name, footer_logo=ctx.author.avatar))

    @cur_damage.command(name='урон', description="Симулировать получение персонажем урона")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __damage(self, ctx,
                       character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                       damage_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('DAMAGE_TYPE', 'label')), required=True),
                       place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False, default=None),
                       damage: discord.Option(float, min_value=1, required=False, default=random.randint(1, 100)),
                       penetration: discord.Option(int, min_value=0, required=False, default=random.randint(1, 200)),
                       source: discord.Option(str, required=False, default=f'Неизвестно')):
        from ArbBattle import DamageManager
        from ArbDamage import Damage

        db = DEFAULT_MANAGER
        character_id = BasicCog.prepare_id(character)
        dam_type = AAC.extract('DAMAGE_TYPE', 'label', damage_type, 'id')
        bodypart = place.split(' ')[0]

        damage_manager = DamageManager(data_manager=db)

        print(penetration)
        a_damage = Damage(damage, dam_type, penetration=penetration, blocked_type=dam_type, root=source, data_manager=db)
        damage_manager.process_damage(character_id, [a_damage], bodyelement=bodypart)

        embed = ErrorEmbed('Нанесён урон!',
                             f'***{Character(character_id, data_manager=db).name}** получил урон:*\n```{a_damage}```',
                             footer=Character(character_id, data_manager=db).name,
                             footer_logo=Character(character_id, data_manager=db).picture)
        await Notification.send_all_notifications(ctx)

        await ctx.respond(embed=embed)

    @cur_damage.command(name='выстрел', description="Симулировать выстрел по персонажу")
    @BasicCog.admin_required
    async def __shot(self, ctx,
                     character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                     weapon: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_range_weapons), required=True),
                     place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False, default=None),
                     shots: discord.Option(int, min_value=1, max_value=100, required=False, default=None)):
        from ArbWeapons import RangeWeapon
        from ArbBattle import DamageManager
        from ArbSkills import SkillInit

        db = DEFAULT_MANAGER
        damage_manager = DamageManager(data_manager=db)
        character_id = BasicCog.prepare_id(character)
        weapon_id = weapon.split(' ')[0]
        bodypart = place.split(' ')[0] if place else None

        weapon_obj = RangeWeapon(weapon_id, data_manager=db)
        shots = shots if shots else weapon_obj.attacks

        for _ in range(shots):
            damage = weapon_obj.random_range_damage()
            damage_manager.process_damage(character_id, shots=damage, bodyelement=bodypart)

        embed = ErrorEmbed('Выстрел!',
                           f'*По **{Character(character_id, data_manager=db).name}** открыл огонь неизвестный из **{weapon_obj.label} ({SkillInit(weapon_obj.weapon_class, data_manager=db).label})**!*',
                           footer=Character(character_id, data_manager=db).name,
                           footer_logo=Character(character_id, data_manager=db).picture)

        await ctx.respond(embed=embed)

        await Notification.send_all_notifications(ctx)


    @cur_damage.command(name='удар', description="Симулировать удар оружием по персонажу")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __hit(self, ctx,
                    character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                    weapon: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_weapons), required=True),
                    place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=True),
                    attacks: discord.Option(int, min_value=1, max_value=100, required=False, default=None)):
        from ArbWeapons import MeleeWeapon
        from ArbBattle import DamageManager
        from ArbSkills import SkillInit

        db = DEFAULT_MANAGER
        damage_manager = DamageManager(data_manager=db)
        character_id = BasicCog.prepare_id(character)
        weapon_id = weapon.split(' ')[0]
        bodypart = place.split(' ')[0] if place else None

        weapon_obj = MeleeWeapon(weapon_id, data_manager=db)
        attacks = attacks if attacks else weapon_obj.melee_attacks

        for _ in range(attacks):
            damage = weapon_obj.melee_attack()
            damage_manager.process_damage(character_id, shots=damage, bodyelement=bodypart)

        embed = ErrorEmbed('Удар!',
                           f'*Неизвестный атаковал **{Character(character_id, data_manager=db).name}** при помощи **{weapon_obj.label} ({SkillInit(weapon_obj.weapon_class, data_manager=db).label})**!*',
                           footer=Character(character_id, data_manager=db).name,
                           footer_logo=Character(character_id, data_manager=db).picture)

        await ctx.respond(embed=embed)

        await Notification.send_all_notifications(ctx)

    @cur_damage.command(name='боевой-приём', description="Симулировать применение приёма на персонаже")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __race_attack(self, ctx,
                            character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                            race: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_races), required=True),
                            attack: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_race_attacks), required=True),
                            place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False, default=None),
                            attacks: discord.Option(int, min_value=1, max_value=100, required=False, default=None)):
        from ArbWeapons import RaceAttack
        from ArbBattle import DamageManager

        db = DEFAULT_MANAGER
        damage_manager = DamageManager(data_manager=db)
        character_id = BasicCog.prepare_id(character)
        attack_id = attack.split(' ')[0]
        bodypart = place.split(' ')[0] if place else None

        weapon_obj = RaceAttack(attack_id, data_manager=db)
        attacks = attacks if attacks else weapon_obj.attacks

        for _ in range(attacks):
            damage = weapon_obj.attack()
            damage_manager.process_damage(character_id, shots=damage, bodyelement=bodypart)

        embed = ErrorEmbed('Боевой приём!',
                           f'*Неизвестный {race.split(" ")[2].lower()} атаковал **{Character(character_id, data_manager=db).name}** использовав приём **{weapon_obj.label}**!*',
                           footer=Character(character_id, data_manager=db).name,
                           footer_logo=Character(character_id, data_manager=db).picture)

        await ctx.respond(embed=embed)

        await Notification.send_all_notifications(ctx)

    @cur_injury.command(name='удалить-все-ранения', description="Удалить все ранения персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_all_injuries(self, ctx,
                                   character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True)):
        from ArbHealth import Injury
        character_id = BasicCog.prepare_id(character)
        Injury.delete_all_character_injuries(character_id)

        embed = SuccessEmbed(f'Все ранения {Character(character_id).name} удалены',
                             f'*{ctx.author.mention} удалил все ранения персонажа **{Character(character_id).name}***',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_illness.command(name='удалить-все-болезни', description="Удалить все болезни персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_all_diseases(self, ctx,
                                    character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True)):
        from ArbHealth import Disease
        character_id = BasicCog.prepare_id(character)
        Disease.delete_all_character_diseases(character_id)

        embed = SuccessEmbed(f'Все болезни {Character(character_id).name} удалены',
                             f'*{ctx.author.mention} удалил все болезни персонажа **{Character(character_id).name}***',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_implant.command(name='удалить-все-импланты', description="Удалить все импланты персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_all_injuries(self, ctx,
                                    character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(
                                        get_all_characters), required=True)):
        from ArbHealth import Implant
        character_id = BasicCog.prepare_id(character)
        Implant.delete_all_character_implants(character_id)

        embed = SuccessEmbed(f'Все импланты {Character(character_id).name} удалены',
                             f'*{ctx.author.mention} удалил все импланты персонажа **{Character(character_id).name}***',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)


    @cur_injury.command(name='удалить-ранение', description="Удалить конкретное ранение персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_injury(self, ctx,
                              character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                              injury: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_injuries), required=True)):
        from ArbHealth import Injury

        character_id = BasicCog.prepare_id(character)
        injury_id = BasicCog.prepare_id(injury)
        Injury.delete_injury(injury_id)

        embed = SuccessEmbed(f'Ранение удалено',
                             f'*{ctx.author.mention} удалил ранение **{injury}** персонажа **{Character(character_id).name}** из списка ранений*',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)


    @cur_illness.command(name='удалить-болезнь', description="Удалить конкретную болезнь персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_disease(self, ctx,
                              character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                              disease: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_disease), required=True)):
        from ArbHealth import Disease

        character_id = BasicCog.prepare_id(character)
        disease_id = BasicCog.prepare_id(disease)
        Disease.delete_disease(disease_id)

        embed = SuccessEmbed(f'Болезнь удалена',
                             f'*{ctx.author.mention} удалил ранение **{disease}** персонажа **{Character(character_id).name}** из списка болезней*',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_implant.command(name='удалить-имлпант', description="Удалить конкретный имплант персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __delete_implant(self, ctx,
                              character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                              implant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_implants), required=True)):
        from ArbHealth import Implant

        character_id = BasicCog.prepare_id(character)
        implant_id = BasicCog.prepare_id(implant)
        Implant.delete_implant(implant_id)

        embed = SuccessEmbed(f'Имлпант удалён',
                             f'*{ctx.author.mention} удалил имплант **{implant}** персонажа **{Character(character_id).name}** из списка имплантов*',
                             footer=ctx.author.display_name,
                             footer_icon=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_injury.command(name='изменить-ранение', description="Изменить настройки ранения персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __change_injury(self, ctx,
                              character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                              injury: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_injuries), required=True),
                              place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False),
                              injury_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('INJURY_INIT', 'label')), required=False),
                              root: discord.Option(str, min_length=1, max_length=256, required=False, default=None),
                              damage: discord.Option(int, min_value=1, required=False, default=None),
                              heal_efficiency: discord.Option(int, min_value=0, max_value=300, default=None, required=False),
                              is_scar: discord.Option(bool, default=None, required=False)):
        from ArbHealth import Injury

        character_id = BasicCog.prepare_id(character)
        injury_id = BasicCog.prepare_id(injury)
        injury_obj = Injury(injury_id)
        injury_obj.update_record(
            {
                'place': place if place else injury_obj.place,
                'type': AAC.extract('INJURY_INIT', 'label', injury_type, 'id') if injury_type else injury_obj.injury_type.injury_type_id,
                'root': root if root else injury_obj.root,
                'damage': damage if damage else injury_obj.damage,
                'heal_efficiency': heal_efficiency if heal_efficiency else injury_obj.healing_efficiency,
                'is_scar': is_scar if is_scar is not None else int(injury_obj.is_scar)
            })
        injury_obj = Injury(injury_id)

        embed = SuccessEmbed(f'Ранение изменено',
                             f'*{ctx.author.mention} изменил ранение **{injury}** персонажа **{Character(character_id).name}***\n'
                             f'-# *Место ранения: **{injury_obj.get_body_element().label}***\n'
                             f'-# *Тип ранения: **{injury_obj.injury_type.label}***\n'
                             f'-# *Причина ранения: **{injury_obj.root}***\n'
                             f'-# *Эффективность лечения: **{injury_obj.healing_efficiency}%***\n'
                             f'-# *Является шрамом: **{injury_obj.is_scar}***',
                             footer=Character(character_id).name,
                             footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @cur_illness.command(name='изменить-болезнь', description="Изменить настройки болезни персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __change_disease(self, ctx,
                               character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                               disease: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_disease), required=True),
                               place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False, default=None),
                               disease_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('DISEASE_INIT', 'label')), required=False, default=None),
                               severity: discord.Option(float, min_value=1, max_value=100, default=None, required=False),
                               immunity: discord.Option(float, min_value=0, max_value=100, default=None, required=False),
                               healing: discord.Option(float, min_value=0, max_value=300, default=None, required=False)):
        from ArbHealth import Disease
        disease_id = BasicCog.prepare_id(disease)
        character_id = BasicCog.prepare_id(character)
        disease_obj = Disease(disease_id)
        disease_obj.update_record(
            {'place': place if place else disease_obj.place if disease_obj.place != 'Все тело' else None,
             'type': AAC.extract('DISEASE_INIT', 'label', disease_type, 'id') if disease_type else disease_obj.disease_type.disease_type_id,
             'severity': severity if severity else disease_obj.current_severity,
             'immunity': immunity if immunity is not None else disease_obj.current_immunity,
             'healing': healing if healing is not None else disease_obj.healing_efficiency})

        disease_obj = Disease(disease_id)

        embed = SuccessEmbed(f'Болезнь изменена',
                             f'*{ctx.author.mention} изменил болезнь **{disease}** персонажа **{Character(character_id).name}***\n'
                             f'-# *Место болезни: **{disease_obj.get_body_element().label if disease_obj.place != "Все тело" else "Все тело"}***\n'
                             f'-# *Тип болезни: **{disease_obj.disease_type.label}***\n'
                             f'-# *Прогресс болезни: **{disease_obj.current_severity}%***\n'
                             f'-# *Прогресс иммунитета: **{disease_obj.current_immunity}%***\n'
                             f'-# *Эффективность лечения: **{disease_obj.healing_efficiency}%***',
                             footer=Character(character_id).name,
                             footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @cur_implant.command(name='изменить-имлпант', description="Изменить настройки импланта персонажа")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __change_implant(self, ctx,
                               character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                               implant: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_implants), required=True),
                               implant_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('IMPLANT_INIT', 'label')), required=False),
                               place: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts), required=False)):
        from ArbHealth import Implant, BodyPart

        character_id = BasicCog.prepare_id(character)
        implant_id = BasicCog.prepare_id(implant)
        implant_obj = Implant(implant_id)
        implant_obj.update_record({'place': place if place else implant_obj.place,
                                   'implant_type': AAC.extract('IMPLANT_INIT', 'label', implant_type, 'id') if implant_type else implant_obj.type.implant_type_id})

        implant_obj = Implant(implant_id)

        embed = SuccessEmbed(f'Имплант изменён',
                             f'*{ctx.author.mention} изменил имплант **{implant}** персонажа **{Character(character_id).name}***\n'
                             f'-# *Место установки импланта: **{BodyPart(implant_obj.place).label}***\n'
                             f'-# *Тип импланта: **{implant_obj.type.label}***\n',
                             footer=Character(character_id).name,
                             footer_logo=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @cur_injury.command(name='добавить-ранение', description="Добавить персонажу новое ранение")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_injury(self, ctx: discord.ApplicationContext,
                           character: discord.Option(str,
                                                     autocomplete=discord.utils.basic_autocomplete(get_all_characters),
                                                     required=True),
                           injury_type: discord.Option(str,
                                                       autocomplete=discord.utils.basic_autocomplete(AAC.db_call('INJURY_INIT', 'label')),
                                                       required=True),
                           place: discord.Option(str,
                                                 autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts),
                                                 required=True),
                           damage: discord.Option(int, min_value=1, required=True, default=None),
                           root: discord.Option(str, min_length=1, max_length=256, required=False, default='Неизвестно'),
                           heal_efficiency: discord.Option(int, min_value=0, max_value=300, default=0, required=False),
                           is_scar: discord.Option(bool, default=None, required=False)):
        from ArbHealth import Injury, BodyElement

        character_id = BasicCog.prepare_id(character)
        new_injury = Injury.create_injury(character_id,
                                          AAC.extract('INJURY_INIT', 'label', injury_type, 'id'),
                                          place.split(' ')[0],
                                          damage,
                                          root=root,
                                          heal_efficiency=heal_efficiency,
                                          is_scar=is_scar if is_scar else False)

        embed = SuccessEmbed(f'Ранение добавлено',
                             f'*{ctx.author.mention} добавил ранение **{new_injury.injury_type.label}** персонажу **{Character(character_id).name}***\n'
                             f'-# *Место ранения: **{BodyElement(character_id, new_injury.place).label}***\n'
                             f'-# *Тип ранения: **{new_injury.injury_type.label}***\n'
                             f'-# *Урон: **{new_injury.damage}***\n'
                             f'-# *Источник ранения: **{new_injury.root}***\n'
                             f'-# *Эффективность лечения: **{new_injury.healing_efficiency}***\n'
                             f'-# *Является ли шрамом: **{new_injury.is_scar}***')
        await ctx.respond(embed=embed)

    @cur_illness.command(name='добавить-болезнь', description="Добавить персонажу новую болезнь")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_disease(self, ctx: discord.ApplicationContext,
                            character: discord.Option(str,
                                                      autocomplete=discord.utils.basic_autocomplete(get_all_characters),
                                                      required=True),
                            place: discord.Option(str,
                                                  autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts),
                                                  required=True,
                                                  default=None),
                            disease_type: discord.Option(str,
                                                         autocomplete=discord.utils.basic_autocomplete(AAC.db_call('DISEASE_INIT', 'label')),
                                                         required=True,
                                                         default=None),
                            severity: discord.Option(float, min_value=1, max_value=100, default=None, required=False),
                            immunity: discord.Option(float, min_value=0, max_value=100, default=None, required=False),
                            healing: discord.Option(float, min_value=0, max_value=300, default=None, required=False)):
        from ArbHealth import Disease, BodyElement


        character_id = BasicCog.prepare_id(character)

        new_disease = Disease.create_character_disease(character_id, AAC.extract('DISEASE_INIT', 'label', disease_type, 'id'),
                                                       place=place.split(' ')[0] if place else None,
                                                       severity=severity,
                                                       immunity=immunity,
                                                       healing=healing)

        embed = SuccessEmbed(f'Болезнь добавлена',
                             f'*{ctx.author.mention} добавил болезнь **{new_disease.disease_type.label}** персонажу **{Character(character_id).name}***\n'
                             f'-# *Место болезни: **{BodyElement(character_id, new_disease.place).label if new_disease.place not in ["Все тело", None] else new_disease.place}***\n'
                             f'-# *Тип болезни: **{new_disease.disease_type.label}***\n'
                             f'-# *Прогресс болезни: **{new_disease.current_severity}%***\n'
                             f'-# *Прогресс иммунитета: **{new_disease.current_immunity}%***\n'
                             f'-# *Эффективность лечения: **{new_disease.healing_efficiency}%***')

        await ctx.respond(embed=embed)

    @cur_implant.command(name='добавить-имплант', description="Добавить персонажу новый имплант")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __add_implant(self, ctx: discord.ApplicationContext,
                            character: discord.Option(str,
                                                      autocomplete=discord.utils.basic_autocomplete(get_all_characters),
                                                      required=True),
                            implant_type: discord.Option(str,
                                                         autocomplete=discord.utils.basic_autocomplete(AAC.db_call('IMPLANTS_INIT', 'label')),
                                                         required=False),
                            place: discord.Option(str,
                                                  autocomplete=discord.utils.basic_autocomplete(get_character_bodyparts),
                                                  required=False)):
        from ArbHealth import Implant

        character_id = BasicCog.prepare_id(character)
        new_implant = Implant.create_implant(character_id, AAC.extract('IMPLANTS_INIT', 'label', implant_type, 'id'), place=place.split(' ')[0] if place else None)

        embed = SuccessEmbed(f'Имплант добавлен',
                             f'*{ctx.author.mention} добавил имплант **{new_implant.label}** персонажу **{Character(character_id).name}***\n'
                             f'-# *Место установки: **{new_implant.place}***')

        await ctx.respond(embed=embed)



    @mng_dialogue.command(name='начать-диалог', description="Запустить диалог в выбраном чате или текущем")
    @BasicCog.exception_handle
    @BasicCog.admin_required
    async def __create_dialogue(self, ctx: discord.ApplicationContext,
                                label: discord.Option(str, required=False, default=f'Разговор'),
                                channel: discord.Option(discord.SlashCommandOptionType.channel, required=False, default=None)):
        from ArbDialogues import Dialogue

        if not channel:
            channel_id = ctx.channel.id
        else:
            channel_id = channel.id

        dialogue = Dialogue.create_dialogue(label, channel_id)
        embed = SuccessEmbed(f'Диалог создан',
                             f'*{ctx.author.mention} создал новый диалог **{dialogue.label}** в канале **{ctx.bot.get_channel(channel_id).mention}**',
                             footer=dialogue.label,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_dialogue.command(name='закончить-диалог', description="Завершить диалог и проанализировать его")
    @BasicCog.admin_required
    async def __close_dialogue(self, ctx: discord.ApplicationContext, dialogue: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_dialogues), required=True)):
        from ArbDialogues import Dialogue

        dialogue_id = BasicCog.prepare_id(dialogue)
        dialogue_obj = Dialogue(dialogue_id)

        embed = SuccessEmbed(f'Диалог закрыт',
                             f'*{ctx.author.mention} закрыл диалог **{dialogue}**',
                             footer=dialogue_obj.label,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

        await dialogue_obj.delete_dialogue()

    @plan_quests.command(name='выполнить-задачу', description="Выполнить задачу текушего задания персонажа")
    @BasicCog.admin_required
    async def __complete_quest_task(self, ctx: discord.ApplicationContext,
                                    character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                                    quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_quests), required=True),
                                    task: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_quest_tasks), required=True),
                                    for_all_members: discord.Option(bool, required=False, default=True)):
        from ArbQuests import CharacterQuest, QuestManager
        from ArbGroups import Group

        character_id = BasicCog.prepare_id(character)
        quest_id = quest.split(' ')[0]
        quest_manager = QuestManager()
        task_title, task_phase = task.split('#')
        task_phase = int(task_phase)

        if for_all_members:
            character_group_members = Group.find_group_members_including(character_id)
        else:
            character_group_members = [character_id]

        current_phase = CharacterQuest(character_id, quest_id).current_phase

        for member in character_group_members:
            quest_manager.assign_new_quest(member, quest_id, 'Выполняется', current_phase)
            CharacterQuest(member, quest_id).complete_task(task_title, task_phase)

        characters_names = [f'**{Character(char).name}**' for char in character_group_members]

        embed = SuccessEmbed(f'Задача выполнена',
                             f'*{", ".join(characters_names)} выполнили задачу **{task_title}***',
                             footer=quest.split(' ')[2],
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='создать-задание', description="Создать новое задание")
    @BasicCog.admin_required
    async def __create_quest(self, ctx: discord.ApplicationContext,
                             quest_id: discord.Option(str, required=True),
                             label: discord.Option(str, required=True),
                             category: discord.Option(str, required=True,
                                                  choices=['Сюжетный', 'Личный', 'Дополнительный', 'Фракционный',
                                                           'Перехват', 'Стелс', 'Доставка', 'Ликвидация', 'Штурм']),
                             difficulty: discord.Option(int, choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], required=False, default=0),
                             giver: discord.Option(str, required=False,
                                                   autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                             enemy: discord.Option(str, required=False,
                                                   autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                             renewable: discord.Option(bool, required=False, default=False),
                             previous_quest: discord.Option(str,
                                                            autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=False, default=None),
                             description: discord.Option(str, required=False),
                             days_before_end: discord.Option(int, required=False, default=None)):

        from ArbQuests import Quest
        from ArbUtils.ArbTimedate import TimeManager

        db = DEFAULT_MANAGER
        if db.check('QUESTS', filter=f'id = "{quest_id}"'):
            embed = ErrorEmbed('Неверный ID квеста', f'*Уже существует квест с таким же идентификатором. Придумайте новый уникальный идентификатор*',
                               footer=ctx.author.name,
                               footer_logo=ctx.author.avatar)
            await ctx.respond(embed=embed)
            return

        giver_id = giver.split(' ')[0] if giver else None
        enemy_id = enemy.split(' ')[0] if enemy else None
        previous_quest_id = previous_quest.split(' ')[0] if previous_quest else None
        time_to_end = TimeManager().date_after(days=days_before_end).strftime('%Y-%m-%d') if days_before_end else None

        new_quest = Quest.create_quest(quest_id, category, giver_id, label, description, enemy_id, time_to_end, renewable, previous_quest_id, difficulty)

        embed = SuccessEmbed('Задание создано',
                             f'*Задание **{label}** создан успешно:*\n\n{new_quest.describe()}',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='удалить-задание', description="Удалить одно из заданий")
    @BasicCog.admin_required
    async def __delete_quest(self, ctx: discord.ApplicationContext,
                             quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True)):
        from ArbQuests import Quest

        quest_id = quest.split(' ')[0]
        quest_obj = Quest(quest_id)
        quest_obj.delete_quest()

        embed = SuccessEmbed('Задание удалено',
                             f'*Задание **{quest}** удалено успешно*',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='добавить-задачу', description="Добавить новую задачу в задание")
    @BasicCog.admin_required
    async def __add_quest_task(self, ctx: discord.ApplicationContext,
                               quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                               title: discord.Option(str, required=True),
                               phase: discord.Option(int, required=True),
                               description: discord.Option(str, required=False),
                               required: discord.Option(bool, required=False, default=True),
                               visible_before_assign: discord.Option(bool, required=False, default=False)):
        from ArbQuests import Quest

        quest_id = quest.split(' ')[0]
        quest_obj = Quest(quest_id)
        quest_obj.create_task(title, phase, description, required, visible_before_assign)

        embed = SuccessEmbed('Задача создана',
                             f'*Задача **{title}** добавлена успешно к квесту **{quest}**. Текущие задачи:*\n{quest_obj.describe_tasks()}',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='удалить-задачу', description="Удалить задачу выбранного задания")
    @BasicCog.admin_required
    async def __delete_quest_task(self, ctx: discord.ApplicationContext,
                                 quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                                 task: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_quest_tasks), required=True)):

        from ArbQuests import Quest

        quest_id = quest.split(' ')[0]
        task_title, phase = task.split('#')

        Quest(quest_id).delete_task(task_title, phase)

        embed = SuccessEmbed('Задача удалена',
                             f'*Задача **{task}** удалена успешно из квеста **{quest}**. Текущие задачи:*\n\n{Quest(quest_id).describe_tasks()}',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='добавить-награду', description="Добавить награду за выполнение задания")
    @BasicCog.admin_required
    async def __add_quest_reward(self, ctx: discord.ApplicationContext,
                                 quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                                 type: discord.Option(str, required=True, choices=['Деньги', 'Опыт', 'Предмет', 'Репутация', 'ОН', 'ОП', 'Уровень', 'Повышение', 'Доминация', 'Боевой дух', 'Организация', 'Разведка', 'Снабжение', 'Защита', 'Импульс']),
                                 value: discord.Option(str, required=True),
                                 split_type: discord.Option(str, required=False, choices=['Поровну', 'Каждому', 'Лидеру', 'Организации', 'Выдающемуся'], default='Каждому')):
        from ArbQuests import Quest

        quest_id = quest.split(' ')[0]
        quest_obj = Quest(quest_id)
        quest_obj.add_reward(type, value, split_type)

        embed = SuccessEmbed('Награда добавлена',
                             f'*Награда **{split_type} - {type}({value})** добавлена успешно к заданию **{quest}**.*',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='удалить-награду', description="Удалить награду за выполнение задания")
    @BasicCog.admin_required
    async def __delete_quest_reward(self, ctx: discord.ApplicationContext,
                                 quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                                 reward: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_quest_rewards), required=True)):
        from ArbQuests import Quest

        quest_id = quest.split(' ')[0]
        quest = Quest(quest_id)
        reward_type, reward_split, reward_value = reward.split(' ')

        quest.delete_reward(reward_type, reward_split, reward_value)

        embed = SuccessEmbed('Награда удалена',
                             f'*Награда **{reward}** удалена успешно из задания **{quest.label}**.*',
                             footer=ctx.author.name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='изменить-задание', description="Изменить настройки задания")
    @BasicCog.admin_required
    async def __edit_quest(self, ctx: discord.ApplicationContext,
                           quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                           label: discord.Option(str, required=False),
                           category: discord.Option(str, required=False,
                                                    choices=['Сюжетный', 'Личный', 'Дополнительный', 'Фракционный',
                                                             'Перехват', 'Стелс', 'Доставка', 'Ликвидация', 'Штурм'], default=None),
                           difficulty: discord.Option(int, choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], required=False,
                                                      default=None),
                           giver: discord.Option(str, required=False,
                                                 autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                           enemy: discord.Option(str, required=False,
                                                 autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                           renewable: discord.Option(bool, required=False, default=None),
                           previous_quest: discord.Option(str,
                                                          autocomplete=discord.utils.basic_autocomplete(get_all_quests),
                                                          required=False, default=None),
                           description: discord.Option(str, required=False),
                           days_before_end: discord.Option(int, required=False, default=None)):
        from ArbQuests import Quest
        from ArbUtils.ArbTimedate import TimeManager

        quest_id = quest.split(' ')[0]
        quest_obj = Quest(quest_id)
        query = {
            'label': label if label is not None else quest_obj.label,
            'type': category if category is not None else quest_obj.type,
            'difficulty': difficulty if difficulty is not None else quest_obj.difficulty,
            'giver': giver.split(' ')[0] if giver is not None else quest_obj.giver,
            'enemy': enemy.split(' ')[0] if enemy is not None else quest_obj.enemy,
            'renewable': int(renewable) if renewable is not None else int(quest_obj.renewable),
            'desc': description if description is not None else quest_obj.desc,
            'time_of_end': TimeManager().date_after(days=days_before_end).strftime('%Y-%m-%d') if days_before_end else quest_obj.time_of_end
        }
        quest_obj.update_record(query)

        if previous_quest:
            DEFAULT_MANAGER.update('QUESTS', {'next_act': quest_id}, f'id = "{previous_quest.split(" ")[0]}"')

        embed = SuccessEmbed('Задание изменено',
                             f'*Задание **{quest}** изменено успешно.*\n\n{Quest(quest_id).describe()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='назначить-задание', description="Назначить персонажу и его группе задание")
    @BasicCog.admin_required
    async def __assign_quest(self, ctx: discord.ApplicationContext,
                             quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                             character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                             for_all_members: discord.Option(bool, required=False, default=True)):
        from ArbQuests import Quest, QuestManager
        from ArbGroups import Group

        quest_id = quest.split(' ')[0]
        character_id = BasicCog.prepare_id(character)
        if for_all_members:
            character_group_members = Group.find_group_members_including(character_id)
        else:
            character_group_members = [character_id]

        for member in character_group_members:
            QuestManager().assign_new_quest(member, quest_id, 'Выполняется')

        quest_obj = Quest(quest_id)

        characters_names = [f'{Character(char).name}' for char in character_group_members]
        embed = SuccessEmbed('Задание назначено',
                             f'*Задание **{quest}** назначено успешно для персонажей:\n{", ".join(characters_names)}.*\n\n{quest_obj.describe()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_quests.command(name='выдать-награду', description="Выдать персонажу и его группе награду")
    @BasicCog.admin_required
    async def __give_reward(self, ctx: discord.ApplicationContext,
                             character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters), required=True),
                            quest: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_quests), required=True),
                            outstanding: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_character_group_members), required=False)):
        from ArbQuests import Quest, CharacterQuest

        character_id = BasicCog.prepare_id(character)
        quest_id = quest.split(' ')[0]

        quest_obj = Quest(quest_id)
        rewards = quest_obj.describe_rewards()
        char_quest = CharacterQuest(character_id, quest_id)
        outstanding_id = BasicCog.prepare_id(outstanding) if outstanding else character_id

        char_quest.give_quest_reward(outstanding_id)

        embed = ArbEmbed('Награда за выполнение задания',
                         f'*За выполнение задания {quest} были получены следующие награды:*\n{rewards}')

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='создать-кампанию')
    @BasicCog.admin_required
    async def __create_campaign(self, ctx: discord.ApplicationContext,
                                campaign_id: discord.Option(str, required=True),
                                label: discord.Option(str, required=True),
                                category: discord.Option(str, required=True, choices=['Событие', 'Кампания', 'Эскалация'], default='Событие'),
                                description: discord.Option(str, required=False),
                                days_before_end: discord.Option(int, required=False, default=None),
                                enemy_id: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                                required_org: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                                required_lvl: discord.Option(int, required=False, default=None),
                                required_relation_with: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                                news_channel: discord.Option(discord.SlashCommandOptionType.channel, required=False, default=None),
                                picture: discord.Option(str, required=False, default=None)):
        from ArbQuests import Campaign
        from ArbUtils.ArbTimedate import TimeManager

        campaign = Campaign.create_campaign(campaign_id,
                                            label,
                                            category,
                                            description,
                                            enemy=enemy_id.split(' ')[0] if enemy_id else None,
                                            time_of_end=TimeManager().date_after(days=days_before_end).strftime('%Y-%m-%d') if days_before_end else None,
                                            r_lvl=required_lvl,
                                            r_org=required_org.split(' ')[0] if required_org else None,
                                            r_rel=required_relation_with.split(' ')[0] if required_relation_with else None,
                                            news_channel=news_channel.id if news_channel else None,
                                            picture=picture if picture else None)

        embed = SuccessEmbed('Кампания создана',
                             f'*Кампания **{campaign.label}** создана успешно.*\n\n{campaign.describe()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='удалить-кампанию', description="Удалить активную кампанию")
    @BasicCog.admin_required
    async def __delete_campaign(self, ctx: discord.ApplicationContext,
                                campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns))):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        campaign_obj = Campaign(campaign_id)
        campaign_obj.delete_campaign()

        embed = SuccessEmbed('Кампания удалена',
                             f'*Кампания **{campaign}** удалена успешно.*',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='удалить-задание-кампании', description="Удалить связь между заданием и кампанией")
    @BasicCog.admin_required
    async def __delete_quest_from_campaign(self, ctx: discord.ApplicationContext,
                                campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                quest: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_campaign_quests))):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        quest_id = quest.split(' ')[0]

        Campaign(campaign_id).delete_quest(quest_id)

        embed = SuccessEmbed('Задание удалено из кампании',
                             f'*Задание **{quest}** удалено из кампании **{campaign}** успешно.*',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='добавить-задание-кампании', description="Связать задание и кампанию")
    @BasicCog.admin_required
    async def __add_quest_to_campaign(self, ctx: discord.ApplicationContext,
                                      campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                      quest: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_quests)),
                                      phase: discord.Option(int, required=False, min_value=0, default=0),
                                      is_required: discord.Option(bool, required=False, default=True),
                                      phase_delta: discord.Option(int, required=False, default=0)):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        quest_id = quest.split(' ')[0]

        campaign_obj = Campaign(campaign_id)
        campaign_obj.add_quest(quest_id, phase, is_required, phase_delta)

        embed = SuccessEmbed('Задание добавлено в кампанию',
                             f'*Задание **{quest}** добавлено в кампанию **{campaign}** успешно.*\n'
                             f'> -# Фаза квеста: **{phase}**\n'
                             f'> -# Является квест обязательным: **{is_required}**\n'
                             f'> -# Автоматическое смещение фазы при выполнении: **{phase_delta}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='новость-кампании', description="Написать новость в новостной чат кампании")
    @BasicCog.admin_required
    async def __news_in_campaign(self, ctx: discord.ApplicationContext,
                                 campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                 text: discord.Option(str, required=True, max_length=2000, min_length=1),
                                 picture: discord.Option(discord.SlashCommandOptionType.attachment, required=False, default=None),
                                 color: discord.Option(str, choices=['Стандартный', 'Зеленый', 'Красный'], required=False),
                                 title: discord.Option(str, required=False, default='Новости'),
                                 logo_url: discord.Option(str, required=False, default=None),
                                 author: discord.Option(str, required=False, default=None),
                                 author_logo: discord.Option(str, required=False, default=None)):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        campaign_obj = Campaign(campaign_id)
        news_channel = ctx.bot.get_channel(campaign_obj.news_channel_id)

        embed = ArbEmbed(f'{title} | {campaign_obj.label}',
                         text,
                         logo_url=logo_url,
                         picture=picture,
                         footer=author,
                         footer_logo=author_logo)

        if color:
            color_dict = {'Стандартный': (43, 45, 49), 'Зеленый': (87, 242, 135), 'Красный': (237, 66, 69)}
            embed.set_color(color_dict[color])

        await ctx.respond(f'-# {ctx.author.mention}, новость **{title}** успешно отправлена в канал {news_channel.mention}')

        await news_channel.send(f'@here', embed=embed)

    @plan_campaigns.command(name='фиксировать-сведения-кампании', description="Зафиксировать новостной чат кампании")
    @BasicCog.admin_required
    async def __fix_campaign_info(self, ctx: discord.ApplicationContext,
                                  campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                  channel: discord.Option(discord.SlashCommandOptionType.channel, required=False, default=None)):

        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        campaign_obj = Campaign(campaign_id)

        embed = ArbEmbed(f'{campaign_obj.label} ({campaign_obj.type})',
                         f'{campaign_obj.describe()}\n\n{campaign_obj.describe_current_quests()}',
                         logo_url=f'{campaign_obj.picture}')

        news_channel = ctx.bot.get_channel(campaign_obj.news_channel_id) if not channel else ctx.bot.get_channel(channel.id)
        message = await news_channel.send(embed=embed)
        campaign_obj.fixate_message(message.id)
        campaign_obj.update_record({'news_channel': channel.id})

    @plan_campaigns.command(name='параметры-фазы-кампании', description="Задать параметры этапа/фазы кампании")
    @BasicCog.admin_required
    async def __campaign_phase_settings(self, ctx: discord.ApplicationContext,
                                       campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                       phase: discord.Option(int, required=True, min_value=0),
                                       title: discord.Option(str, required=False, default=None),
                                        description: discord.Option(str, required=False, default=None, min_length=1, max_length=2000)):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        campaign_obj = Campaign(campaign_id)

        campaign_obj.add_phase_values(phase, title, description)

        embed = SuccessEmbed('Настройки фазы кампании',
                             f'*Настройки фазы кампании **{campaign_obj.label}** успешно изменены.*\n'
                             f'> -# Номер фазы: **{phase}**\n'
                             f'> -# Заголовок: **{title}**\n'
                             f'> -# Описание: *"{description}"*',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @plan_campaigns.command(name='сменить-фазу-кампании', description="Сменить этап/фазу кампании")
    @BasicCog.admin_required
    async def __change_campaign_phase(self, ctx: discord.ApplicationContext,
                                       campaign: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_campaigns)),
                                       phase: discord.Option(int, required=True, autocomplete=discord.utils.basic_autocomplete(get_campaign_phases))):
        from ArbQuests import Campaign

        campaign_id = campaign.split(' ')[0]
        campaign_obj = Campaign(campaign_id)

        campaign_obj.set_phase(phase)

        embed = SuccessEmbed('Смена фазы кампании',
                             f'*Фаза кампании **{campaign_obj.label}** успешно изменена на **{phase}***.\n{campaign_obj.get_phase(phase).describe_phase()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

        campaign_obj = Campaign(campaign_id)

        embed = ArbEmbed(f'{campaign_obj.label} ({campaign_obj.type})',
                         f'{campaign_obj.describe()}\n\n{campaign_obj.describe_current_quests()}',
                         logo_url=f'{campaign_obj.picture}')

        news_channel = ctx.bot.get_channel(campaign_obj.news_channel_id)
        message = await news_channel.send(embed=embed)
        campaign_obj.fixate_message(message.id)


    @cur_items.command(name='удалить-предмет', description="Удалить предмет")
    @BasicCog.admin_required
    async def __delete_item(self, ctx: discord.ApplicationContext,
                            item: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_items))):
        from ArbItems import Item

        item_id = BasicCog.prepare_id(item)

        item_obj = Item(item_id)
        item_obj.delete_item()

        embed = SuccessEmbed('Удаление предмета',
                             f'*Предмет **{item}** успешно удален!*',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_items.command(name='создать-предмет', description="Создать новый предмет")
    @BasicCog.admin_required
    async def __create_item(self, ctx: discord.ApplicationContext,
                            item_type:discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_itemtypes)),
                            material: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(item_available_materials)),
                            quality: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(qualities)),
                            endurance: discord.Option(int, required=False, min_value=1, max_value=100),
                            character: discord.Option(str, required=False, default=None, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                            autoequip: discord.Option(bool, required=False, default=False)):
        from ArbGenerator import ItemManager
        from ArbItems import Inventory

        item_id = item_type.split(' ')[0]
        material_id = AAC.extract('MATERIALS', 'name', material, 'id') if material else None
        quality = quality if quality else None
        character_id = BasicCog.prepare_id(character) if character is not None else None
        character_inventory = Inventory.get_inventory_by_character(character_id) if character_id is not None else None

        new_item = ItemManager(item_id,
                               material=material_id,
                               quality=quality,
                               endurance=endurance,
                               inventory=character_inventory.inventory_id if character_inventory else None).spawn_item(character_id if character_id is not None and autoequip else None)

        embed = SuccessEmbed(f'Предмет {new_item.label} ({new_item.item_id}) создан!',
                             f'*{ctx.author.mention} создал предмет **{new_item.__str__()}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rels.command(name='создать-воспоминание', description="Создать новое воспоминание персонажа")
    @BasicCog.admin_required
    async def __create_memory(self, ctx: discord.ApplicationContext,
                              character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                              type: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_memories_types)),
                              description: discord.Option(str, required=False, min_length=1, max_length=512, default=None),
                              blamed_character: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                              is_fixed: discord.Option(bool, required=False, default=False),
                              days_ago: discord.Option(int, required=False, default=0)):
        from ArbCharacterMemory import MemoryEvent, CharacterMemoryEvent
        from ArbUtils.ArbTimedate import TimeManager

        character_id = BasicCog.prepare_id(character)
        type_id = type.split(' ')[0]
        blamed_character_id = BasicCog.prepare_id(blamed_character)
        date = TimeManager().date_after(days=-1*days_ago).strftime('%Y-%m-%d')

        new_memory_id = MemoryEvent.create_memory(character_id, type_id, description, blamed_character_id, date, is_fixed)
        new_memory = CharacterMemoryEvent(new_memory_id)

        embed = SuccessEmbed(f'Воспоминание создано',
                             f'*{ctx.author.mention} создал воспоминание **{new_memory.label}***\n'
                             f'-# *Описание: {description}*\n'
                             f'-# *Обвиненный персонаж: **{Character(new_memory.subject).name if new_memory.subject else "||Неизвестно||"}***\n'
                             f'-# *Фиксация воспоминания: **{new_memory.is_fixed}***\n'
                             f'-# *Дата события: **{new_memory.date}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rels.command(name='удалить-воспоминание', description="Удалить одно из воспоминаний")
    @BasicCog.admin_required
    async def __delete_memory(self, ctx: discord.ApplicationContext,
                              character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                              memory: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_memories))):
        from ArbCharacterMemory import CharacterMemoryEvent

        memory_id = BasicCog.prepare_id(memory)
        memory_obj = CharacterMemoryEvent(memory_id)

        memory_obj.delete_memory()

        embed = SuccessEmbed(f'Воспоминание удалено',
                             f'*{ctx.author.mention} удалил воспоминание **{memory_obj.label}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rels.command(name='изменить-воспоминание', description="Изменить настройки воспоминания")
    @BasicCog.admin_required
    async def __edit_memory(self, ctx: discord.ApplicationContext,
                            character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                            memory: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_memories)),
                            memory_type: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_memories_types), default=None),
                            description: discord.Option(str, required=False, min_length=1, max_length=512, default=None),
                            blamed_character: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_all_characters), default=None),
                            is_fixed: discord.Option(bool, required=False, default=None),
                            days_ago: discord.Option(int, required=False, default=None)):
        from ArbCharacterMemory import CharacterMemoryEvent
        from ArbUtils.ArbTimedate import TimeManager

        memory_id = BasicCog.prepare_id(memory)
        memory_obj = CharacterMemoryEvent(memory_id)

        memory_type_id = memory_type.split(' ')[0] if memory_type else memory_obj.event_type
        blamed_character_id = BasicCog.prepare_id(blamed_character) if blamed_character else None
        is_fixed = int(is_fixed) if is_fixed is not None else int(memory_obj.is_fixed)
        date = TimeManager().date_after(days=-1 * days_ago).strftime('%Y-%m-%d') if days_ago is not None else memory_obj.date
        desc = description if description else memory_obj.description

        query = {
            'event_type': memory_type_id,
            'desc': desc,
            'subject_id': blamed_character_id,
            'date': date,
            'fixed': is_fixed
        }
        memory_obj.data_manager.update('CHARS_MEMORY', query, f'event_id = "{memory_id}"')
        memory_obj = CharacterMemoryEvent(memory_id)

        embed = SuccessEmbed(f'Воспоминание изменено',
                             f'*{ctx.author.mention} изменил воспоминание **{memory_obj.label}** персонажа **{character}***\n'
                             f'-# *Описание: {description}*\n'
                             f'-# *Обвиненный персонаж: **{Character(memory_obj.subject).name if memory_obj.subject else "||Неизвестно||"}***\n'
                             f'-# *Фиксация воспоминания: **{memory_obj.is_fixed}***\n'
                             f'-# *Дата события: **{memory_obj.date}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rels.command(name='знакомство', description="Познакомить персонажей")
    @BasicCog.admin_required
    async def __add_friendship(self, ctx: discord.ApplicationContext,
                               character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                               encounter: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                               relation_type: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_all_relation_roles)),
                               family_type: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_all_relation_roles)),
                               trust: discord.Option(int, required=False, default=0),
                               sympathy: discord.Option(int, required=False, default=0),
                               respect: discord.Option(int, required=False, default=0),
                               love: discord.Option(int, required=False, default=0)):
        from ArbCharacterMemory import CharacterRelations

        character_id = BasicCog.prepare_id(character)
        encounter_id = BasicCog.prepare_id(encounter)

        if relation_type or family_type:
            CharacterRelations.create_familiar(character_id,
                                      encounter_id,
                                      relation_type.split(' ')[0] if relation_type else None,
                                      family_type.split(' ')[0] if family_type else None)

        CharacterRelations.create_relation_values(character_id, encounter_id)
        CharacterRelations.update_relations(character_id, encounter_id, trust, sympathy, respect, love)

        relation = CharacterRelations(character_id).relations.get(encounter_id)

        embed = SuccessEmbed(f'Знакомство',
                             f'***{Character(character_id).name}** встретил {relation.relation_type.label if not relation.family_type else relation.family_type.label} **{Character(encounter_id).name}***')
        embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)

        await ctx.respond(embed=embed)

    @cur_rels.command(name='удалить-знакомство', description="Разорвать отношения между персонажами")
    @BasicCog.admin_required
    async def __delete_friendship(self, ctx: discord.ApplicationContext,
                                   character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                                   encounter: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_relations))):
        from ArbCharacterMemory import CharacterRelations

        character_id = BasicCog.prepare_id(character)
        encounter_id = BasicCog.prepare_id(encounter)

        DEFAULT_MANAGER.delete('CHARS_FAMILIARS', f'id = {character_id} AND subject_id = {encounter_id}')
        DEFAULT_MANAGER.delete('CHARS_FAMILIARS', f'id = {encounter_id} AND subject_id = {character_id}')

        embed = SuccessEmbed(f'Знакомство удалено',
                             f'*{ctx.author.mention} удалил знакомство между **{Character(character_id).name}** и **{Character(encounter_id).name}**')

        await ctx.respond(embed=embed)

    @cur_rels.command(name='изменить-отношение', description="Изменить отношение одного персонажа к другому")
    @BasicCog.admin_required
    async def __edit_relations(self, ctx: discord.ApplicationContext,
                               character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                               encounter: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_relations)),
                               relation_type: discord.Option(str, required=False,
                                                             autocomplete=discord.utils.basic_autocomplete(get_all_relation_roles), default=None),
                               family_type: discord.Option(str, required=False,
                                                           autocomplete=discord.utils.basic_autocomplete(get_all_relation_roles), default=None),
                               trust: discord.Option(int, required=False, default=0),
                               sympathy: discord.Option(int, required=False, default=0),
                               respect: discord.Option(int, required=False, default=0),
                               love: discord.Option(int, required=False, default=0)):
        from ArbCharacterMemory import CharacterRelations

        character_id = BasicCog.prepare_id(character)
        encounter_id = BasicCog.prepare_id(encounter)

        old_relation = CharacterRelations(character_id).get_relationship(encounter_id)

        CharacterRelations.update_relations(character_id, encounter_id, trust, sympathy, respect, love)
        char_relation = CharacterRelations(character_id)

        if relation_type:
            char_relation.set_relation_type(encounter_id, relation_type.split(' ')[0])
        if family_type:
            char_relation.set_family_type(encounter_id, family_type.split(' ')[0])

        new_relation = CharacterRelations(character_id).get_relationship(encounter_id)

        old_avg_relation = old_relation.calculate_avg_relation()
        new_avg_relation = new_relation.calculate_avg_relation()

        if old_avg_relation < new_avg_relation:
            embed = SuccessEmbed('Отношение улучшилось',
                                 f'*{ctx.author.mention} изменил отношения **{Character(character_id).name}** к **{Character(encounter_id).name}**, '
                                 f'средний показатель отношений составил **{old_avg_relation}** -> **{new_avg_relation}***')
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed, ephemeral=True)

            Notification.create_notification(f'Отношения с {Character(encounter_id).name}',
                                             f'{Character(character_id).name} улучшил своё отношение к {Character(encounter_id).name}',
                                             character_id,
                                             'success')

            Notification.create_notification(f'Отношения с {Character(character_id).name}',f'Отношения с {Character(character_id).name} улучшились', encounter_id,'success')
            await Notification.send_all_notifications(ctx)

        elif old_avg_relation > new_avg_relation:
            embed = ErrorEmbed('Отношения ухудшились',
                                 f'*{ctx.author.mention} изменил отношение **{Character(character_id).name}** к **{Character(encounter_id).name}**, '
                                 f'средний показатель отношений составил **{old_avg_relation}** -> **{new_avg_relation}***')
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed, ephemeral=True)

            Notification.create_notification(f'Отношения с {Character(encounter_id).name}',
                                             f'{Character(character_id).name} ухудшил своё отношение к {Character(encounter_id).name}', character_id,
                                             'danger')

            Notification.create_notification(f'Отношения с {Character(character_id).name}',
                                             f'Отношения с {Character(character_id).name} ухудшились', encounter_id,
                                             'danger')
            await Notification.send_all_notifications(ctx)

        else:
            embed = ArbEmbed('Отношения не изменились',
                                 f'*{ctx.author.mention} изменил отношение **{Character(character_id).name}** к **{Character(encounter_id).name}**, '
                                 f'средний показатель отношений остался **{old_avg_relation}**')
            embed.set_author(Character(character_id).name, icon_url=Character(character_id).picture)
            await ctx.respond(embed=embed, ephemeral=True)

            Notification.create_notification(f'Отношения с {Character(encounter_id).name}',
                                             f'{Character(character_id).name} изменил своё отношение к {Character(encounter_id).name}',
                                             character_id,
                                             'info')
            Notification.create_notification(f'Отношения с {Character(character_id).name}',
                                             f'Отношения с {Character(character_id).name} изменились...', encounter_id,
                                             'info')
            await Notification.send_all_notifications(ctx)

    @cur_rp.command(name='создать-статиста', description="Создать статиста для отыгровок")
    @BasicCog.admin_required
    async def __create_extra(self, ctx: discord.ApplicationContext,
                             tag: discord.Option(str, required=True),
                             name: discord.Option(str, required=True, max_length=100, min_length=2),
                             picture: discord.Option(str, required=False, default=None),
                             is_private: discord.Option(bool, required=False, default=False)):
        from ArbRolePlay import Extra

        new_extra = Extra.create_extra(tag, name, picture if picture else None, ctx.author.id if is_private else None)

        embed = ArbEmbed(new_extra.name,
                         f'— Я готов к работе и отыгровкам!',
                         logo_url=new_extra.picture)
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rp.command(name='удалить-статиста', description="Удалить статиста для отыгровок")
    @BasicCog.admin_required
    async def __delete_extra(self, ctx: discord.ApplicationContext,
                             tag: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_author_available_extras))):
        from ArbRolePlay import Extra
        tag = tag.split(' ')[0]
        extra = Extra(tag)
        extra.delete_record()

        embed = ArbEmbed(f'Статист "{extra.name}" удален',
                         f'**{ctx.author.mention}** успешно удалил статиста **{extra.name} ({extra.tag})**!')

        await ctx.respond(embed=embed)

    @cur_rp.command(name='фраза-статиста', description="Произнести фразу от лица статиста")
    @BasicCog.admin_required
    async def __extra_phrase(self, ctx: discord.ApplicationContext,
                             tag: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_author_available_extras)),
                             phrase: discord.Option(str, required=True, max_length=2000, min_length=1),
                             picture: discord.Option(discord.SlashCommandOptionType.attachment, required=False)):
        from ArbRolePlay import Extra

        tag = tag.split(' ')[0]
        extra = Extra(tag)

        await extra.say(ctx, phrase, picture.url if picture else None)


    @cfg_location.command(name='создать-локацию', description="Создать новую локацию")
    @BasicCog.admin_required
    async def __create_location(self, ctx: discord.ApplicationContext,
                                region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                                location_id: discord.Option(str, required=True, max_length=100, min_length=2),
                                label: discord.Option(str, required=True, max_length=100, min_length=2),
                                type: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_location_types)),
                                owner: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                                movement_cost: discord.Option(int, required=False, min_value=0, default=2),
                                current_battle: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(active_battles)),
                                picture: discord.Option(str, required=False, default=None),
                                is_covered: discord.Option(bool, required=False, default=None)):
        from ArbLocations import Location

        type_id = type.split(' ')[0]
        region_id = region.split(' ')[0]
        owner_id = owner.split(' ')[0]
        current_battle_id = BasicCog.prepare_id(current_battle) if current_battle else None

        new_location = Location.create_location(location_id,
                                                label, type_id, region_id, owner_id, movement_cost, current_battle_id, picture if picture else None, is_covered)

        embed = SuccessEmbed(f'Локация {label} ({location_id}) создана!',
                             f'-# *Регион: **{new_location.cluster.label}***\n'
                             f'-# *Тип локации: **{new_location.type.label}***\n'
                             f'-# *Владелец: **{new_location.get_owner().label}***\n'
                             f'-# *Цена перемещения: **{new_location.cost}***\n'
                             f'-# *ID-битвы на локации: **{current_battle}***\n'
                             f'-# *Локация скрыта: **{new_location.is_covered}***',
                             logo_url=picture.url if picture else None,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_location.command(name='изменить-локацию', description="Изменить настройки локации")
    @BasicCog.admin_required
    async def __update_location(self, ctx: discord.ApplicationContext,
                                location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                                region: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                                label: discord.Option(str, required=False, max_length=100, min_length=2),
                                type: discord.Option(str, required=False,
                                                     autocomplete=discord.utils.basic_autocomplete(get_location_types)),
                                owner: discord.Option(str, required=False,
                                                      autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                                movement_cost: discord.Option(int, required=False, min_value=0, default=2),
                                current_battle: discord.Option(str, required=False,
                                                               autocomplete=discord.utils.basic_autocomplete(active_battles)),
                                picture: discord.Option(str, required=False, default=None),
                                is_covered: discord.Option(bool, required=False, default=None)):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)

        type_id = type.split(' ')[0] if type else None
        region_id = region.split(' ')[0] if region else None
        owner_id = owner.split(' ')[0] if owner else None
        current_battle_id = BasicCog.prepare_id(current_battle) if current_battle else None

        a_location.location_update(label, type_id, region_id, owner_id, movement_cost, current_battle_id, picture if picture else None, is_covered)

        embed = SuccessEmbed(f'Локация {label} ({location_id}) настроена!',
                             f'-# *Регион: **{a_location.cluster.label}***\n'
                             f'-# *Тип локации: **{a_location.type.label}***\n'
                             f'-# *Владелец: **{a_location.get_owner().label}***\n'
                             f'-# *Цена перемещения: **{a_location.cost}***\n'
                             f'-# *ID-битвы на локации: **{current_battle}***\n'
                             f'-# *Локация скрыта: **{a_location.is_covered}***',
                             logo_url=picture.url if picture else None,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_location.command(name='удалить-локацию', description="Удалить одну из локаций")
    @BasicCog.admin_required
    async def __delete_location(self, ctx: discord.ApplicationContext,
                                location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations))):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)
        a_location.delete_location()

        embed = SuccessEmbed(f'Локация {location_id} удалена!',
                             f'**{ctx.author.mention}** успешно удалил локацию **{location}**!',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_location.command(name='создать-регион', description="Создать новый регион")
    @BasicCog.admin_required
    async def __create_region(self, ctx: discord.ApplicationContext,
                              region_id: discord.Option(str, required=True),
                              label: discord.Option(str, required=True),
                              type: discord.Option(str, required=True, choices=['Регион', 'Комплекс']),
                              time: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_time_conds)),
                              weather: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_weather_conds)),
                              move_description: discord.Option(str, required=False, min_length=10, max_length=1000, default='Вы переместились на локацию'),
                              picture: discord.Option(str, required=False, default=None),
                              map: discord.Option(str, required=False, default=None)):
        from ArbLocations import Cluster
        from ArbBattle import Weather, DayTime

        weather_id = weather.split(' ')[0]
        time_id = time.split(' ')[0] if time else None

        new_cluster = Cluster.create_cluster(region_id,
                                             label,
                                             type,
                                             picture if picture else None,
                                             weather_id,
                                             time_id,
                                             move_description,
                                             map if map else None)

        embed = SuccessEmbed(f'Регион {label} ({region_id}) создан!',
                             f'-# *Тип региона: **{new_cluster.type}***\n'
                             f'-# *Погода: **{Weather(new_cluster.weather).label}***\n'
                             f'-# *Время: **{DayTime(new_cluster.time).label}***\n'
                             f'-# *Описание при перемещении: "{new_cluster.move_desc}"*',
                             picture=new_cluster.map,
                             logo_url=new_cluster.picture,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_loc.command(name='погода-региона', description="Установить погоду региона")
    @BasicCog.admin_required
    async def __weather_region(self, ctx: discord.ApplicationContext,
                               region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                               weather: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_weather_conds))):
        from ArbLocations import Cluster
        from ArbBattle import Weather

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'weather': weather.split(' ')[0]})
        a_cluster = Cluster(region_id)

        embed = SuccessEmbed(f'Погода региона {region} изменена!',
                             f'-# *Новая погода: **{Weather(a_cluster.weather).label}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_loc.command(name='время-региона', description="Зафиксировать/Привязать к реальному (МСК) время региона")
    @BasicCog.admin_required
    async def __time_of_region(self, ctx: discord.ApplicationContext,
                               region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                               time: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_time_conds))):
        from ArbLocations import Cluster
        from ArbBattle import DayTime

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'time': time.split(' ')[0] if time else None})
        a_cluster = Cluster(region_id)

        embed = SuccessEmbed(f'Погода региона {region} изменена!',
                             f'-# *Время суток: **{DayTime(a_cluster.time).label} ({"фиксировано" if time else "Привязано к реальному"})***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_loc.command(name='название-региона', description="Установить название региона")
    @BasicCog.admin_required
    async def __region_name(self, ctx: discord.ApplicationContext,
                               region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                               new_name: discord.Option(str, required=True, min_length=3, max_length=100)):
        from ArbLocations import Cluster

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'label': new_name})

        embed = SuccessEmbed(f'Название региона {region} изменено!',
                             f'-# *Новое название: **{a_cluster.label}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_loc.command(name='описание-региона')
    @BasicCog.admin_required
    async def __region_description(self, ctx: discord.ApplicationContext,
                                     region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                                     new_description: discord.Option(str, required=False, min_length=10, max_length=1000)):
        from ArbLocations import Cluster

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'move_desc': new_description})
        a_cluster = Cluster(region_id)
        embed = SuccessEmbed(f'Описание региона {region} изменено!',
                             f'-# *Новое описание: **{a_cluster.move_desc}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @mng_loc.command(name='изображение-региона', description="Установить изображение (картинку) региона")
    @BasicCog.admin_required
    async def __region_picture(self, ctx: discord.ApplicationContext,
                                    region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                                    new_picture: discord.Option(str, required=False)):
        from ArbLocations import Cluster

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'picture': new_picture if new_picture else None})
        a_cluster = Cluster(region_id)

        embed = SuccessEmbed(f'Изображение региона {region} изменено!',
                             f'-# *Новое изображение:',
                             logo_url=a_cluster.picture,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @mng_loc.command(name='установить-карту-региона', description="Установить карту региона")
    @BasicCog.admin_required
    async def __set_map(self, ctx: discord.ApplicationContext,
                                region: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_regions)),
                                new_map: discord.Option(str, required=False)):
        from ArbLocations import Cluster

        region_id = region.split(' ')[0]
        a_cluster = Cluster(region_id)
        a_cluster.update_record({'map': new_map if new_map else None})
        a_cluster = Cluster(region_id)

        embed = SuccessEmbed(f'Карта региона {region} изменена!',
                             f'-# *Новая карта:',
                             picture=a_cluster.map,
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)


    @cfg_location.command(name='добавить-объект-локации', description="Добавить объект на локацию")
    @BasicCog.admin_required
    async def __add_object_location(self, ctx: discord.ApplicationContext,
                                    location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                                    object_type: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_loc_objects_types)),
                                    label: discord.Option(str, required=False, default=None)):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)

        object_type_id = object_type.split(' ')[0]
        object = a_location.add_object(object_type_id, label)


        embed = SuccessEmbed(f'Объект локации {object.label} ({object.object_id}) добавлен на локацию {location_id}!',
                             f'-# *Название: **{object.label} ({object.object_type})***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_location.command(name='удалить-объект-локации', description="Удалить объект локации")
    @BasicCog.admin_required
    async def __delete_object_location(self, ctx: discord.ApplicationContext,
                                        location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                                        object: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_loc_objects))):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)

        object_id = BasicCog.prepare_id(object)
        a_location.delete_object(object_id)

        embed = SuccessEmbed(f'Объект локации удален!',
                             f'**{ctx.author.mention}** успешно удалил объект локации **{object}**!',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cfg_location.command(name='добавить-путь', description="Добавить путь между локациями")
    @BasicCog.admin_required
    async def __add_path(self, ctx: discord.ApplicationContext,
                         location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                         end_location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                         is_available: discord.Option(bool, required=False, default=True),
                         transports: discord.Option(str, required=False, choices=['Наземный, Воздушный', 'Морской, Воздушный', 'Воздушный', 'Наземный', 'Морской'], default=None)):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)
        end_location_id = end_location.split(' ')[0]
        transports = transports.split(', ') if transports else None

        a_location.add_connection(end_location_id, is_available, transports)

        embed = SuccessEmbed(f'Путь между локациями {location_id} и {end_location_id} добавлен!',
                             f'-# *Доступность: **{is_available}***\n'
                             f'-# *Необходимый транспорт: **{", ".join(transports) if transports else "Транспорт не нужен"}***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)


    @cfg_location.command(name='удалить-путь', description="Удалить путь между локациями")
    @BasicCog.admin_required
    async def __delete_path(self, ctx: discord.ApplicationContext,
                             location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                             end_location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_location_connections))):
        from ArbLocations import Location

        location_id = location.split(' ')[0]
        a_location = Location(location_id)
        end_location_id = end_location.split(' ')[0]
        a_location.delete_connection(end_location_id)

        embed = SuccessEmbed(f'Путь между локациями {location_id} и {end_location_id} удален!',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_rp.command(name='дислокация', description="Телепортировать персонажа и его группу на локацию")
    @BasicCog.admin_required
    async def __dislocation(self, ctx: discord.ApplicationContext,
                            character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                            location: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_locations)),
                            is_entered: discord.Option(bool, required=False, default=False)):
        from ArbLocations import CharacterLocation, Location
        from ArbGroups import Group

        character_id = BasicCog.prepare_id(character)
        character_location = CharacterLocation(character_id)
        location_id = location.split(' ')[0]
        character_location.set_group_location(location_id, is_entered)

        group_members = Group.find_group_members_including(character_id)

        characters_names = [f'{Character(member).name}' for member in group_members]

        embed = SuccessEmbed('Перемещение на локацию',
                             f'***{", ".join(characters_names)}**, {Location(location_id).cluster.move_desc.lower()} **{Location(location_id).label} ({Location(location_id).type.label})***')
        await ctx.respond(embed=embed)

    @cur_skills.command(name='добавить-навык', description="Добавить персонажу новый навык")
    @BasicCog.admin_required
    async def __add_skill(self, ctx: discord.ApplicationContext,
                          character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                          skill: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_skills)),
                          lvl: discord.Option(int, required=False, min_value=0, max_value=250, default=0),
                          talent: discord.Option(float, required=False, min_value=0, max_value=2.5, default=1),
                          mastery: discord.Option(float, required=False, min_value=0, max_value=2.5, default=0.5),
                          exp: discord.Option(float, required=False, min_value=0, default=0)):
        from ArbSkills import Skill

        character_id = BasicCog.prepare_id(character)
        skill_id = skill.split(' ')[0]
        a_skill = Skill(character_id, skill_id)
        a_skill.set_lvl(lvl)
        a_skill.set_talant(talent)
        a_skill.set_mastery(mastery)
        a_skill.set_exp(exp)

        embed = SuccessEmbed('Добавление навыка',
                             f'*Навык **{a_skill.label}** был добавлен персонажу **{Character(character_id).name}*** со следующими параметрами:\n'
                             f'-# *Уровень навыка: **{a_skill.lvl}%***\n'
                             f'-# Талант: **{a_skill.talant*100}%***\n'
                             f'-# Мастерство: **{a_skill.mastery*100}%***\n'
                             f'-# Опыт навыка: **{a_skill.exp} exp.***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_skills.command(name='удалить-навык', description="Удалить навык персонажа")
    @BasicCog.admin_required
    async def __delete_skill(self, ctx: discord.ApplicationContext,
                              character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                              skill: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_skills))):
        from ArbSkills import Skill

        character_id = BasicCog.prepare_id(character)
        skill_id = skill.split(' ')[0]
        Skill(character_id, skill_id).delete_skill()

        embed = SuccessEmbed('Удаление навыка',
                             f'***{Character(character_id).name}*** удалил навык **{skill}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_skills.command(name='изменить-навык', description="Изменить прогресс навыка персонажа")
    @BasicCog.admin_required
    async def __change_skill(self, ctx: discord.ApplicationContext,
                          character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                          skill: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_character_skills)),
                          lvl: discord.Option(int, required=False, min_value=0, max_value=250, default=None),
                          talent: discord.Option(float, required=False, min_value=0, max_value=2.5, default=None),
                          mastery: discord.Option(float, required=False, min_value=0, max_value=2.5, default=None),
                          exp: discord.Option(float, required=False, min_value=0, default=None)):
        from ArbSkills import Skill

        character_id = BasicCog.prepare_id(character)
        skill_id = skill.split(' ')[0]

        a_skill = Skill(character_id, skill_id)

        if lvl:
            a_skill.set_lvl(lvl)

        if talent:
            a_skill.set_talant(talent)

        if mastery:
            a_skill.set_mastery(mastery)

        if exp:
            a_skill.set_exp(exp)

        embed = SuccessEmbed('Изменение навыка',
                             f'*Навык **{a_skill.label}** персонажа **{Character(character_id).name}** был изменен*:\n'
                             f'-# *Уровень навыка: **{a_skill.lvl}%***\n'
                             f'-# Талант: **{a_skill.talant * 100}%***\n'
                             f'-# Мастерство: **{a_skill.mastery * 100}%***\n'
                             f'-# Опыт навыка: **{a_skill.exp} exp.***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @cur_skills.command(name='изменить-прогресс', description="Изменить ОН, ОП и опыт персонажа")
    @BasicCog.admin_required
    async def __skills(self, ctx: discord.ApplicationContext,
                       character: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                       exp: discord.Option(float, required=False, default=0),
                       skill_points: discord.Option(int, required=False, default=0),
                       skill_mods_points: discord.Option(int, required=False, default=0),
                       lvl: discord.Option(int, required=False, default=0)):
        from ArbCharacters import CharacterProgress

        character_id = BasicCog.prepare_id(character)
        character_progress = CharacterProgress(character_id)

        character_progress.update_progress_data(skill_points, skill_mods_points, lvl, exp)

        embed = SuccessEmbed('Изменение прогресса персонажа',
                             f'*Прогресс персонажа **{Character(character_id).name}** был изменен*:\n'
                             f'-# *Опыт: **{character_progress.skills_exp}** exp.*\n'
                             f'-# *Уровень: **{character_progress.lvl}***\n'
                             f'-# *Очки навыков: **{character_progress.skills_points} ОН.***\n'
                             f'-# *Очки профессионализма: **{character_progress.skills_mods} ОП.***',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)


    @mng_gen.command(name='генерация-боя', description="Сгенерирорвать бой")
    @BasicCog.admin_required
    async def __generate_battle(self, ctx:discord.ApplicationContext,
                                label: discord.Option(str, required=False, default='Безымянное сражение'),
                                description: discord.Option(str, required=False, default='Столкновение сторон в жестокой схватке'),
                                distance_delta: discord.Option(int, min_value=1, required=False, default=random.randint(25, 150)),
                                time: discord.Option(str,
                                                   autocomplete=discord.utils.basic_autocomplete(get_time_conds),
                                                   required=False,
                                                   default='Day'),
                                weather: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_weather_conds),
                                                      required=False,
                                                      default='Sunny'),
                                round: discord.Option(int, min_value=1, required=False, default=1),
                                key_round_delay: discord.Option(int, min_value=1, required=False, default=3),
                                last_round: discord.Option(int, min_value=1, required=False, default=None),
                                battle_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('BATTLE_CONDITIONS', 'label')), required=False, default='Столкновение'),
                                battle_type_value: discord.Option(str, required=False, default=None),
                                terrain_categories: discord.Option(str, choices=['Природный', 'Городской', 'Пустынный', 'Руины', 'Комната', 'Военный'], required=False, default=None),
                                terrain_types: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(AAC.db_call('TERRAIN_TYPES', 'label')), required=False, default=None),
                                num_of_layers: discord.Option(int, required=False, default=None)):

        from ArbGenerator import GenerateBattle

        new_battle = GenerateBattle(
            label=label,
            desc=description,
            distance_delta=distance_delta,
            time=time.split(' ')[0],
            weather=weather.split(' ')[0],
            start_round=round,
            key_round=key_round_delay,
            last_round=last_round,
            battle_type=AAC.extract('BATTLE_CONDITIONS', 'label', battle_type, 'id') if battle_type else 'Overkill',
            battle_type_value=battle_type_value,
            num_of_layers=num_of_layers if num_of_layers else random.randint(3, 15),
            terrain_categories=[terrain_categories] if terrain_categories else ['Природный'],
            terrain_types=terrain_types if terrain_types else [],
        )

        new_battle.insert_data()
        battlefield = Battlefield(new_battle.id)

        embed = SuccessEmbed('Генерация боя',
                             f'Бой **{new_battle.label} ({new_battle.id})** был успешно создан.\n'
                             f'-# Сгенерировано слоев: {len(battlefield.get_layers())} (расстояние - {battlefield.distance_delta})\n'
                             f'-# Тип боя: {AAC.extract("BATTLE_CONDITIONS", "id", battlefield.battle_type, "label")}\n'
                             f'-# Природные условия: {battlefield.time.label}, {battlefield.weather.label}\n'
                             f'-# Текущий раунд: {battlefield.round} из {battlefield.last_round} (сброс инициативы каждые {battlefield.key_round_delay} раунда)\n',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_gen.command(name='создать-персонажа', description="Сгенерировать персонажа")
    @BasicCog.admin_required
    async def __generate_unit(self, ctx: discord.ApplicationContext,
                              danger: discord.Option(int, min_value=0, default=random.randint(0, 6), required=False),
                              budget: discord.Option(int, min_value=0, default=None, required=False),
                              name: discord.Option(str, default=None, required=False),
                              age: discord.Option(int, default=None, required=False),
                              callsign: discord.Option(str, default=None, required=False),
                              gender: discord.Option(str, default=None, required=False),
                              race: discord.Option(str, default='Human', autocomplete=discord.utils.basic_autocomplete(get_all_races), required=False),
                              org_id: discord.Option(str, default=None, autocomplete=discord.utils.basic_autocomplete(get_orgs), required=False),
                              org_rank: discord.Option(str, default=None, autocomplete=discord.utils.basic_autocomplete(get_orgs_ranks), required=False),
                              org_lvl: discord.Option(int, default=None, min_value=0, required=False),
                              picture: discord.Option(str, default=None, required=False)):
        from ArbGenerator import CharacterTemplate

        embed = ArbEmbed('Создание персонажа',
                         f'-# Происходит генерация персонажа, ожидайте...')

        message = await ctx.respond(embed=embed)
        time = datetime.datetime.now()
        new_character = CharacterTemplate(danger, budget, ctx.guild.id, race.split(' ')[0] if race else None, org_id.split(' ')[0] if org_id else None, org_rank.split(' ')[0] if org_rank else None, org_lvl, picture=picture if picture else None,
                                          name=name,age=age,callsign=callsign, gender=gender)
        new_character_id = new_character.insert_data()
        print(datetime.datetime.now() - time)
        character = Character(new_character_id)

        embed = SuccessEmbed('Создание персонажа',
                             f'Персонаж **{character.name} ({character.id})** успешно создан\n{character.text_card()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar,
                             logo_url=character.picture)

        await message.edit(embed=embed)

        await ctx.respond(f'Шаблон генерации:\n```python\n{new_character.to_text()}```', ephemeral=True)

        CharacterEquipment(new_character_id).validate_and_fix_equipment()

    @mng_gen.command(name='создать-шаблон', description="Сохранить шаблон генерации персонажа")
    @BasicCog.admin_required
    async def __generate_template(self, ctx: discord.ApplicationContext,
                                  template_id: discord.Option(str, required=True),
                                  label: discord.Option(str, required=True),
                                  content: discord.Option(str, required=True)):
        from ArbGenerator import TemplateManager

        TemplateManager.create_template(template_id, label, content)

        embed = SuccessEmbed('Создание шаблона',
                             f'Шаблон **{label} ({template_id})** успешно создан\n```python\n{content}```',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_gen.command(name='создать-шаблон-группы', description="Сохранить шаблон генерации группы")
    @BasicCog.admin_required
    async def __generate_template_group(self, ctx: discord.ApplicationContext,
                                         template_id: discord.Option(str, required=True),
                                         label: discord.Option(str, required=True)):
        from ArbGenerator import GroupTemplate

        new_temp = GroupTemplate.create_template(template_id, label)
        embed = SuccessEmbed('Создание шаблона группы',
                             f'Шаблон группы **{label} ({template_id})** успешно создан',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @mng_gen.command(name='удалить-шаблон-группы', description="Удалить шаблон генерации группы")
    @BasicCog.admin_required
    async def __update_template_group(self, ctx: discord.ApplicationContext,
                                         template: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_group_templates))):
        from ArbGenerator import GroupTemplate

        GroupTemplate(template.split(' ')[0]).delete_template()

        embed = SuccessEmbed(f'Шаблон группы {template} удален!',
                             f'{ctx.author.mention} удалил шаблон группы **{template}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @mng_gen.command(name='изменить-шаблон-группы', description="Изменить шаблон генерации группы (шаблоны генерации персонажей и их количество)")
    @BasicCog.admin_required
    async def __update_template_group_label(self, ctx: discord.ApplicationContext,
                                            template: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_group_templates)),
                                            unit_template: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_templates)),
                                            value: discord.Option(int, required=True, min_value=0)):
        from ArbGenerator import GroupTemplate

        template = GroupTemplate(template.split(' ')[0])
        template.set_gen_temp(unit_template.split(' ')[0], value)

        embed = SuccessEmbed(f'Изменение шаблона группы {template.label}',
                             f'{ctx.author.mention} изменил шаблон группы **{template.label}**.\nШаблону персонажа **{unit_template}** установлено количество - {value}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)


    @mng_gen.command(name='изменить-шаблон', description="Изменить шаблон генерации персонажа")
    @BasicCog.admin_required
    async def __update_template(self, ctx: discord.ApplicationContext,
                                template: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_templates)),
                                label: discord.Option(str, required=False, default=None),
                                content: discord.Option(str, required=False, default=None)):
        from ArbGenerator import TemplateManager

        template_obj = TemplateManager(template.split(' ')[0])
        template_obj.update_record(
            {
                'label': label if label else template_obj.label,
                'content': template_obj.content if content else template_obj.content
            }
        )
        template_obj = TemplateManager(template.split(' ')[0])
        embed = SuccessEmbed('Изменение шаблона',
                             f'Шаблон **{template_obj.label} {template_obj.id})** успешно изменен\n```python\n{template_obj.content}```',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_gen.command(name='удалить-шаблон', description="Удалить шаблон генерации персонажа")
    @BasicCog.admin_required
    async def __delete_template(self, ctx: discord.ApplicationContext,
                                template: discord.Option(str, required=True, autocomplete=discord.utils.basic_autocomplete(get_templates))):

        from ArbGenerator import TemplateManager

        TemplateManager(template.split(' ')[0]).delete_record()

        embed = SuccessEmbed('Удаление шаблона',
                             f'Шаблон **{template}** успешно удален',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng_gen.command(name='сгенерировать-по-шаблону', description="Сгенерировать персонажа в соответствии с шаблоном (сохраненным или введенным вручную)")
    @BasicCog.admin_required
    async def __list_templates(self, ctx: discord.ApplicationContext,
                               template: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_templates)),
                               content: discord.Option(str, required=False),
                               danger: discord.Option(int, required=False, min_value=0, default=random.randint(0, 6)),
                               name: discord.Option(str, default=None, required=False),
                               age: discord.Option(int, default=None, required=False),
                               callsign: discord.Option(str, default=None, required=False),
                               gender: discord.Option(str, default=None, required=False),
                               org: discord.Option(str, default=None,
                                                      autocomplete=discord.utils.basic_autocomplete(get_orgs),
                                                      required=False),
                               org_rank: discord.Option(str, default=None,
                                                        autocomplete=discord.utils.basic_autocomplete(get_orgs_ranks),
                                                        required=False),
                               picture: discord.Option(str, default=None,
                                                       required=False)
                               ):
        from ArbGenerator import TemplateManager, CharacterTemplate

        template_content = TemplateManager(template.split(' ')[0]).content if template else None
        if not template_content and content:
            template_content = TemplateManager.unwrap_content(content)
            print(template_content)

        if not template_content:
            embed = ErrorEmbed('Ошибка генерации', 'Вы не используете ни шаблон из базы данных ни ручной ввод')
            await ctx.respond(embed=embed)
            return

        new_character = CharacterTemplate.from_text(template_content, danger)
        new_character.basic_info.name = name if name else new_character.basic_info.name
        new_character.basic_info.age = age if age else new_character.basic_info.age
        new_character.basic_info.callsign = callsign if callsign else new_character.basic_info.callsign
        new_character.basic_info.sex = gender if gender else new_character.basic_info.sex
        new_character.basic_info.org = org.split(' ')[0] if org else new_character.basic_info.org
        new_character.basic_info.org_lvl = org_rank.split(' ')[0] if org_rank else new_character.basic_info.org_lvl
        new_character.basic_info.avatar = picture if picture else new_character.basic_info.avatar

        print(new_character.to_text())
        pprint.pprint(new_character.__dict__)

        new_character_id = new_character.insert_data()

        character = Character(new_character_id)
        embed = SuccessEmbed('Создание персонажа',
                             f'Персонаж **{character.name} ({character.id})** успешно создан\n{character.text_card()}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar,
                             logo_url=character.picture)

        await ctx.respond(embed=embed)

        await ctx.respond(f'Шаблон генерации:\n```python\n{new_character.to_text()}```', ephemeral=True)

        CharacterEquipment(new_character_id).validate_and_fix_equipment()

    @mng_gen.command(name='сгенерировать-группу', description="Сгенерировать группу персонажей")
    @BasicCog.admin_required
    async def __generate_group(self, ctx: discord.ApplicationContext,
                               label: discord.Option(str, min_length=2, max_length=50, required=False),
                               template: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_group_templates)),
                               num_of_units: discord.Option(int, required=False, min_value=1, max_value=20),
                               owner: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                               danger: discord.Option(int, min_value=0, required=False),
                               org: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_orgs))):
        from ArbGenerator import GenerateGroup
        from ArbGroups import Group
        from ArbOrgs import Organization

        print(org)

        new_group = GenerateGroup(label, BasicCog.prepare_id(owner) if owner else None, org.split(' ')[0] if org else 'Civil', num_of_units, danger, template.split(' ')[0] if template else None)
        new_group_id = new_group.insert_data()

        group = Group(new_group_id)
        group_members = [m.get('id') for m in group.fetch_group_members()]
        members_names = [f'{Character(m).name} ({m})' for m in group_members]
        embed = SuccessEmbed(f'Новая группа "{group.label}" сгенерирована!',
                             f'Создана группа организации - {Organization(group.get_group_org()).label}. В ней состоят слеудющие персонажи: **{", ".join(members_names)}**',
                             footer=f'Кол-во членов группы: {len(group_members)}')
        embed.set_author(ctx.author.display_name, icon_url=ctx.author.avatar)
        await ctx.respond(embed=embed)


    @cur_rp.command(name='добавить-в-группу', description="Добавить персонажа в группу")
    @BasicCog.admin_required
    async def __add_group_member(self, ctx: discord.ApplicationContext,
                                 character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                                 group: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_groups)),
                                 role: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_group_roles), required=False, default=f'Participant - Член отряда')):
        from ArbGroups import Group

        group_obj = Group(BasicCog.prepare_id(group))
        group_obj.add_member(BasicCog.prepare_id(character), role.split(' ')[0])

        embed = SuccessEmbed(f'Добавление персонажа в группу',
                             f'{ctx.author.mention} добавил **{character}** в группу **{group}** в качестве **{role}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)
        await ctx.respond(embed=embed)

    @cur_rp.command(name='изменить-персонажа', description="Изменить основную информацию о персонаже")
    @BasicCog.admin_required
    async def __change_character(self, ctx: discord.ApplicationContext,
                                 character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters)),
                                 race: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_races), required=False),
                                 gender: discord.Option(str, choices=['Мужской', 'Женский', 'Бесполый', 'Робот'], required=False),
                                 name: discord.Option(str, required=False, min_length=2, max_length=80),
                                 org: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_orgs)),
                                 org_rank: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(get_orgs_ranks)),
                                 avatar: discord.Option(str, required=False),
                                 money: discord.Option(int, required=False)):

        character_id = BasicCog.prepare_id(character)

        char = Character(character_id)

        if race:
            char.race = race.split(' ')[0]

        if gender:
            char.sex = gender

        if name:
            char.name = name

        if org:
            char.org = org.split(' ')[0]

        if org_rank:
            char.org_lvl = org_rank.split(' ')[0]

        if avatar:
            char.picture = avatar

        if money:
            char.money = money

        embed = SuccessEmbed(f'Изменение персонажа',
                             f'{ctx.author.mention} изменил информацию о персонаже **{character}**:\n'
                             f'{char.text_card()}\n-# Бюджет: {char.money}',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar,
                             logo_url=char.picture)
        await ctx.respond(embed=embed)

    @mng.command(name='удалить-персонажа', description="Принудительно удалить персонажа")
    @BasicCog.admin_required
    async def __delete_character(self, ctx: discord.ApplicationContext,
                                 character: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_all_characters))):
        character_id = BasicCog.prepare_id(character)
        Character(character_id).delete_character()

        embed = SuccessEmbed(f'Удаление персонажа',
                             f'{ctx.author.mention} удалил персонажа **{character}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)

    @mng.command(name='удалить-неактивных-персонажей', description="Удалить всех персонажей без хозяина и активного пользователя")
    @BasicCog.admin_required
    async def __delete_unused_characters(self, ctx: discord.ApplicationContext):
        total_characters = Character.delete_unused_characters()

        embed = SuccessEmbed(f'Удаление неиспользуемых персонажей',
                             f'{ctx.author.mention} удалил всех неиспользуемых персонажей в количестве - **{total_characters}**',
                             footer=ctx.author.display_name,
                             footer_logo=ctx.author.avatar)

        await ctx.respond(embed=embed)


    @commands.slash_command(name='admin_test')
    @BasicCog.admin_required
    async def admin_test(self, ctx: discord.ApplicationContext,
                           picture: discord.Option(discord.SlashCommandOptionType.attachment, required=False)):
        await ctx.respond(f'Pong! {ctx.bot.latency}')
        if picture:
            pprint.pprint(picture.ephemeral)
            await ctx.send(picture)


    @cur_rp.command(name='пост', description='Создаёт игровой пост')
    @BasicCog.admin_required
    async def create_post(self, ctx: discord.ApplicationContext,
                          title: discord.Option(str, required=False, min_length=2, max_length=180),
                          color: discord.Option(str, required=False, choices=['Обычный', 'Красный', 'Зеленый'], default='Обычный'),
                          picture: discord.Option(discord.SlashCommandOptionType.attachment, required=False),
                          logo: discord.Option(discord.SlashCommandOptionType.attachment, required=False),
                          author: discord.Option(str, required=False),
                          footer: discord.Option(str, required=False),
                          author_logo: discord.Option(discord.SlashCommandOptionType.attachment, required=False),
                          footer_logo: discord.Option(discord.SlashCommandOptionType.attachment, required=False)):

        response_embed = ArbEmbed('Начато написание поста', '-# Отправьте последующее сообщение. Оно будет преобразовано в пост.\n'
                                                            '### Настройки:\n'
                                                            f'Название - {title}\n'
                                                            f'Цвет - {color}\n'
                                                            f'Автор - {author}\n'
                                                            f'Нижний текст - {footer}\n',
                                  picture=picture.url if picture else None,
                                  logo_url=logo.url if logo else None,
                                  footer_logo=footer_logo.url if footer_logo else None)
        response_embed.set_author(author, icon_url=author_logo)

        response = await ctx.respond(embed=response_embed, ephemeral=True)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            message = await ctx.bot.wait_for('message', check=check)

            if color == 'Обычный':
                embed = ArbEmbed(title, message.content,
                                 picture=picture.url if picture else None,
                                 logo_url=logo.url if logo else None,
                                 footer_logo=footer_logo.url if footer_logo else None,
                                 footer=footer)
                embed.set_author(author, icon_url=author_logo)
            elif color == 'Красный':
                embed = ErrorEmbed(title, message.content,
                                 picture=picture.url if picture else None,
                                 logo_url=logo.url if logo else None,
                                 footer_logo=footer_logo.url if footer_logo else None,
                                 footer=footer)
                embed.set_author(author, icon_url=author_logo)
            elif color == 'Зелёный':
                embed = SuccessEmbed(title, message.content,
                                 picture=picture.url if picture else None,
                                 logo_url=logo.url if logo else None,
                                 footer_logo=footer_logo.url if footer_logo else None,
                                 footer=footer)
                embed.set_author(author, icon_url=author_logo)
            else:
                embed = ArbEmbed(title, message.content,
                                 picture=picture.url if picture else None,
                                 logo_url=logo.url if logo else None,
                                 footer_logo=footer_logo.url if footer_logo else None,
                                 footer=footer)
                embed.set_author(author, icon_url=author_logo)
            await message.delete()
            await ctx.send('', embed=embed)
            await response.delete_original_response()


        except Exception as e:
            embed = ArbEmbed('Произошла ошибка', f'При создании поста произошла ошибка: `{e}`')
            await ctx.respond(embed=embed, ephemeral=True)

    @cur.command(name='кратко')
    @BasicCog.admin_required
    async def __summary(self, ctx: discord.ApplicationContext,
                        channel: discord.Option(discord.SlashCommandOptionType.channel)):
        await ctx.respond(f'Недоступно')

        #
        # from sumy.parsers.plaintext import PlaintextParser
        # from sumy.nlp.tokenizers import Tokenizer
        # from sumy.summarizers.lsa import LsaSummarizer

        # total_text = ''
        # async for message in channel.history(limit=500, oldest_first=True):
        #     if message.author.id != self.bot.user.id:
        #         total_text += message.clean_content + '\n\n'
        #     print(total_text)

        # summarizer = pipeline('summarization')
        #
        # summary_text_chunks = summarizer(total_text, max_length=2000, min_length=30, do_sample=False, language='russian')
        # print(summary_text_chunks)
        #
        # summary_text = summary_text_chunks[0]['summary_text']

        # parser = PlaintextParser.from_string(total_text, Tokenizer('russian'))
        # summarizer = LsaSummarizer()

        # summary = summarizer(parser.document, 5)
        # summary_text = '\n\n'.join(str(sentence) for sentence in summary)
        # await ctx.send(summary_text)

    @cur.command(name='архивировать')
    @BasicCog.admin_required
    async def __archive(self, ctx: discord.ApplicationContext,
                        target_channel: discord.Option(discord.SlashCommandOptionType.channel),
                        archive_channel: discord.Option(discord.SlashCommandOptionType.channel),
                        message_limit: discord.Option(int, required=False, min_value=100, default=None)):
        from ArbRolePlay import DataMessage

        if ctx.author.id != ctx.guild.owner_id and (message_limit is None or message_limit > 5000):
            await ctx.respond('Ограничение на количество сообщений превышено', ephemeral=True)
            return

        await ctx.respond('***Происходит архивация...***', ephemeral=True)

        total_messages = []
        async for message in target_channel.history(limit=message_limit, oldest_first=True):
            print(f'АРХИВАЦИЯ - {message.content}')
            total_messages.append(message)

        data_messages = DataMessage(self.bot, total_messages, archive_channel.id)
        await data_messages.archivate()


def setup(bot):

    bot.add_cog(AdminTools(bot))