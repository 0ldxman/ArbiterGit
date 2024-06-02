# -*- coding: utf-8 -*-
import datetime
import random
from dataclasses import dataclass
from ArbDatabase import DataManager
from ArbCharacters import CharacterCombat, CharacterAttributes
from ArbHealth import Body
from ArbSounds import InBattleSound
from ArbAttacks import RangeAttack


class Weather:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        data = self.fetch_data()
        self.label = data.get('label','Неизвестные погодные условия')
        self.rain_intense = data.get('rain_intense', 0)
        self.wind_speed = data.get('wind_speed', 0)
        self.temperature = int(data.get('temp', 0))
        self.visibility = data.get('visibility', 100)
        self.light = data.get('light', 100)
        self.noise = data.get('noise', 0)
        self.description = data.get('desc', '')

    def fetch_data(self):
        if self.data_manager.check('WEATHER_CONDS',f'id = "{self.id}"') is None:
            return None
        else:
            return self.data_manager.select_dict('WEATHER_CONDS',filter=f'id = "{self.id}"')[0]

    def __repr__(self):
        return f'Weather.{self.id}'


class DayTime:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        data = self.fetch_data()
        self.label = data.get('label','Неизвестное время суток')
        self.temperature = int(data.get('temp', 0))
        self.visibility = data.get('visibility', 100)
        self.light = data.get('light', 100)
        self.noise = data.get('noise', 0)
        self.description = data.get('desc', '')

    def fetch_data(self):
        if self.data_manager.check('DAYTIME_CONDS',f'id = "{self.id}"') is None:
            return None
        else:
            return self.data_manager.select_dict('DAYTIME_CONDS',filter=f'id = "{self.id}"')[0]

    def __repr__(self):
        return f'Daytime.{self.id}'


class Terrain:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        data = self.fetch_data()
        self.label = data.get('label','Неизвестная местность')
        self.desc = data.get('desc','')
        self.movement_cost = data.get('movement_cost',1)
        self.visibility = data.get('visibility', 100)
        self.light = data.get('light', 100)
        self.coverage = data.get('coverage', 0) == 1
        self.reachable = data.get('reachable', 1) == 1
        self.banned_transports = data.get('banned_transport','')
        self.object_types = data.get('object_types','Природный')
        self.movement_difficulty = data.get('move_difficulty', 0)

    def fetch_data(self):
        if self.data_manager.check('TERRAIN_TYPE',f'id = "{self.id}"') is None:
            return None
        else:
            return self.data_manager.select_dict('TERRAIN_TYPE',filter=f'id = "{self.id}"')[0]

    def __repr__(self):
        return f'Terrain.{self.id}'


class ObjectType:
    def __init__(self, id:str, **kwargs):
        self.object_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестный объект')
        self.type = data.get('type', None)
        self.max_slots = data.get('slots', 0)
        self.coverage = data.get('coverage', 0)
        self.protection = data.get('protection', 0)
        self.max_endurance = data.get('endurance', 0)
        self.effect_id = data.get('effect_id', None)


    def fetch_data(self):
        if self.data_manager.check('OBJECT_TYPE',f'object_id = "{self.object_id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('OBJECT_TYPE',filter=f'object_id = "{self.object_id}"')[0]

    def __repr__(self):
        return f'ObjectType.{self.object_id}'


class GameObject(ObjectType):
    def __init__(self, id:int, layer_id:int, battle_id:int, **kwargs):
        self.id = id
        self.layer_id = layer_id
        self.battle_id = battle_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        object_data = self.fetch_object_data()
        super().__init__(object_data.get('object_type'), data_manager=self.data_manager)
        self.current_endurance = object_data.get('endurance', self.max_endurance)
        self.coverage = self.coverage * (self.current_endurance / self.max_endurance)
        self.protection = self.protection * (self.current_endurance / self.max_endurance)

        self.available_slots = self.max_slots - len(self.current_characters())

    def fetch_object_data(self):
        if self.data_manager.check('BATTLE_OBJECTS',f'battle_id = {self.battle_id} AND layer_id = {self.layer_id} AND object_id = {self.id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_OBJECTS',filter=f'battle_id = {self.battle_id} AND layer_id = {self.layer_id} AND object_id = {self.id}')[0]

    def current_characters(self):
        if self.data_manager.check('BATTLE_CHARACTERS',f'battle_id = {self.battle_id} AND layer_id = {self.layer_id} AND object = {self.id}') is None:
            return []
        else:
            id_list = []
            c_data = self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'battle_id = {self.battle_id} AND layer_id = {self.layer_id} AND object = {self.id}')
            for i in c_data:
                id_list.append(i.get('character_id'))
            return id_list

    def recive_damage(self, amount:int):
        self.current_endurance -= amount
        if self.current_endurance <= 0:
            self.delete_object()
        else:
            self.data_manager.update('BATTLE_OBJECTS', {'endurance': self.current_endurance}, f'object_id = {self.id} AND layer_id = {self.layer_id} AND battle_id = {self.battle_id}')

    def delete_object(self):
        chars = self.current_characters()
        if chars:
            for char in chars:
                self.data_manager.update('BATTLE_CHARACTERS',{'object': None}, f'character_id = {char}')

        self.data_manager.delete('BATTLE_OBJECTS',f'object_id = {self.id} AND layer_id = {self.layer_id} AND battle_id = {self.battle_id}')



    def __repr__(self):
        return f'Object.{self.object_id} ({self.current_endurance}/{self.max_endurance}DP)'


class LayerModificationType:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        data = self.fetch_modifier_effects()
        self.label = data.get('label', 'Неизвестный эффект слоя')
        self.visibility = data.get('visibility', 0) if data.get('visibility', None) else 0
        self.noise = data.get('noise', 0) if data.get('noise', None) else 0
        self.movement_cost = data.get('movement_cost', 0) if data.get('movement_cost', None) else 0
        self.min_damage = data.get('min_damage', 0) if data.get('min_damage', None) else 0
        self.max_damage = data.get('max_damage', 0) if data.get('max_damage', None) else 0
        self.damage_type = data.get('damage_type', None) if data.get('damage_type', None) else 0
        self.penetration = data.get('penetration', 0) if data.get('penetration', None) else 0

    def fetch_modifier_effects(self):
        if self.data_manager.check('MODIFIER_INIT', f'id = "{self.id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('MODIFIER_INIT', filter=f'id = "{self.id}"')[0]

@dataclass()
class LayerModification:
    modifier_type: LayerModificationType
    remaining_rounds: int

    def get_effect_label(self):
        return self.modifier_type.label
    def get_visibility(self):
        return self.modifier_type.visibility

    def get_noise(self):
        return self.modifier_type.noise

    def get_movement_cost(self):
        return self.modifier_type.movement_cost

    def calculate_damage(self, data_manager: DataManager = None):
        from ArbDamage import Damage, Penetration, DamageType
        if not self.modifier_type.damage_type:
            return None, None

        if not data_manager:
            data_manager = DataManager()

        min_damage = self.modifier_type.min_damage
        max_damage = self.modifier_type.max_damage

        penetration_type = DamageType(self.modifier_type.damage_type, data_manager=data_manager).get_protection_type()

        penetration = Penetration(name=penetration_type, value=self.modifier_type.penetration, blocked_type=self.modifier_type.damage_type)

        return Damage(damage=random.randint(min_damage, max_damage), damage_type=self.modifier_type.damage_type,
                      root=self.get_effect_label(), data_manager=data_manager), penetration

    def delete_modifier(self, layer_id:int, battle_id:int, data_manager:DataManager = None):
        data_manager = data_manager if data_manager else DataManager()
        if data_manager.check('BATTLE_LAYERS_MODS', f'layer_id = {layer_id} AND battle_id = {battle_id} AND modifier = "{self.modifier_type.id}"'):
            data_manager.delete('BATTLE_LAYERS_MODS', f'layer_id = {layer_id} AND battle_id = {battle_id} AND modifier = "{self.modifier_type.id}"')

    def set_rounds(self, rounds:int):
        self.remaining_rounds = rounds

    def __repr__(self):
        return f'Mod.{self.modifier_type.id}({self.remaining_rounds})'


class Layer:
    def __init__(self, id:int, battle_id:int, **kwargs):
        self.id = id
        self.battle_id = battle_id
        self.data_manager = kwargs.get('data_manager',DataManager())

        data = self.fetch_data()
        self.label = data.get('label','Неизвестная местность')
        self.terrain = Terrain(data.get('terrain_type','Field'), data_manager=self.data_manager)

        self.objects = self.fetch_objects()

    def fetch_layer_modification(self):
        if self.data_manager.check('BATTLE_LAYERS_MODS',f'layer_id = {self.id} AND battle_id = {self.battle_id}') is None:
            return []
        else:
            total_mods = self.data_manager.select_dict('BATTLE_LAYERS_MODS',filter=f'layer_id = {self.id} AND battle_id = {self.battle_id}')
            response = []
            for mod in total_mods:
                c_type = LayerModificationType(mod.get('modifier'), data_manager=self.data_manager)
                response.append(LayerModification(c_type, mod.get('rounds')))

            return response

    def total_visibility(self):
        c_battle = self.get_battle()
        weather_visibility = c_battle.weather.visibility / 100
        time_visibility = c_battle.time.visibility / 100

        return self.terrain.visibility * weather_visibility * time_visibility

    def total_noise(self):
        c_battle = self.get_battle()
        weather_noise = c_battle.weather.noise
        time_noise = c_battle.time.noise

        return weather_noise + time_noise

    def total_light(self):
        c_battle = self.get_battle()
        weather_light = c_battle.weather.light / 100
        time_light = c_battle.time.light / 100

        return self.terrain.light * weather_light * time_light

    def get_battle(self):
        return Battlefield(self.battle_id, data_manager=self.data_manager)

    def fetch_data(self):
        if self.data_manager.check('BATTLE_LAYERS', f'battle_id = {self.battle_id} AND id = {self.id}') is None:
            return None
        else:
            return self.data_manager.select_dict('BATTLE_LAYERS',filter=f'battle_id = {self.battle_id} AND id = {self.id}')[0]

    def fetch_objects(self):
        c_data = self.data_manager.select_dict('BATTLE_OBJECTS',filter=f'battle_id = {self.battle_id} AND layer_id = {self.id}')
        if not c_data:
            return {}
        else:
            c_list = {}
            for o in c_data:
                c_list[o.get('object_id')] = GameObject(o.get('object_id'), self.id, self.battle_id, data_manager=self.data_manager)

            return c_list

    def fetch_characters(self):
        if not self.data_manager.check('BATTLE_CHARACTERS', f'layer_id = {self.id} AND battle_id = {self.battle_id}'):
            return []
        else:
            return [charc.get('character_id') for charc in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'layer_id = {self.id} AND battle_id = {self.battle_id}')]

    def characters_not_in_cover(self):
        characters = self.fetch_characters()
        total_list = []
        for char in characters:
            if Actor(char, data_manager=self.data_manager).get_current_object():
                continue
            else:
                total_list.append(char)
        return total_list

    def update_mods(self):
        c_mods = self.fetch_layer_modification()
        if c_mods:
            for mod in c_mods:
                c_rounds = mod.remaining_rounds - 1
                if c_rounds == 0:
                    mod.delete_modifier(self.id, self.battle_id, data_manager=self.data_manager)
                else:
                    query = {'rounds': c_rounds}
                    mod.set_rounds(c_rounds)
                    self.data_manager.update('BATTLE_LAYERS_MODS', query, filter=f'layer_id = {self.id} AND battle_id = {self.battle_id} AND modifier = "{mod.modifier_type.id}"')

    def update_layer(self):
        from ArbAttacks import CombatManager

        c_mods = self.fetch_layer_modification()
        if not c_mods:
            return
        characters = self.fetch_characters()

        for mod in c_mods:
            c_damage = mod.calculate_damage(self.data_manager)
            damage_query = [{'damage': c_damage[0],
                             'penetration': c_damage[1]}]

            if c_damage[0] is not None and c_damage[1] is not None:
                for char in characters:
                    total_damage = CombatManager(data_manager=self.data_manager).calculate_total_damage(damage_query, char)
                    CombatManager(data_manager=self.data_manager).recive_damage(char, total_damage, apply_effect=True)

                    self.data_manager.logger.info(f'Персонаж {char} получил урон {total_damage}')

        self.update_mods()

    def describe_objects(self):
        object_text = ''
        if self.objects:
            total_objects = []
            for object in self.objects:
                c_object = self.objects[object]
                total_objects.append(f' {c_object.label}[id:{c_object.id}]')

            object_text += ','.join(total_objects)
        else:
            object_text += ' что здесь довольно пусто и нет выделяющихся объектов или укрытий.'

        return object_text

    def describe(self):
        object_text = self.describe_objects()

        return f'{self.terrain.label}. \n{self.terrain.desc}. Вы видите{object_text}'

    def __repr__(self):
        return f'Battle.{self.battle_id}.Layer.{self.id}'


class EventLogger:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.event_id = self.get_event_id()
        self.battle_id = kwargs.get('battle_id', None)
        self.round = kwargs.get('round', None)
        self.actor_id = kwargs.get('actor', None)
        self.subject_id = kwargs.get('subject_id', None)
        self.action_id = kwargs.get('action_id')
        self.desc = kwargs.get('desc', 'Подробности события неизвестны...')

        self.log_event()

    def log_event(self):
        prompt = {'event_id': self.get_event_id(),
                  'battle_id': self.battle_id,
                  'round': self.round,
                  'actor': self.actor_id,
                  'action_id': self.action_id,
                  'subject_id': self.subject_id,
                  'desc': self.desc}

        self.data_manager.insert('BATTLE_EVENTS',prompt)

    def get_event_id(self):
        c_max_id = self.data_manager.maxValue('BATTLE_EVENTS','event_id')
        return c_max_id + 1


class BattleEvent:
    def __init__(self, event_id:int, **kwargs):
        self.event_id = event_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_event_data()
        self.battle_id = data.get('battle_id', None)
        self.round = data.get('round', None)
        self.actor = data.get('actor', None)
        self.action_id = data.get('action_id', 'NoneTypeEvent')
        self.subject_id = data.get('subject_id', None)
        self.description = data.get('desc', 'Подробности события неизвестны...')

    def fetch_event_data(self):
        if self.data_manager.check('BATTLE_EVENTS',f'event_id = {self.event_id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_EVENTS',filter=f'event_id = {self.event_id}')[0]

    def __repr__(self):
        return f'{self.action_id}'

    def __str__(self):
        return f'{self.description}'


class TeamRole:
    def __init__(self, role_id:str, **kwargs):
        self.role_id = role_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_teamrole_data()
        self.initiative_bonus = data.get('initiative', 0)

    def fetch_teamrole_data(self):
        if not self.data_manager.check('TEAM_ROLES',f'id = "{self.role_id}"'):
            return {}
        else:
            return self.data_manager.select_dict('TEAM_ROLES', filter=f'id = "{self.role_id}"')[0]


class BattleTeam(TeamRole):
    def __init__(self, id:int, battle_id:int, **kwargs):
        self.id = id
        self.battle_id = battle_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_team_data()
        self.label = data.get('label', 'Неизвестная команда')
        self.role = data.get('role', None)
        super().__init__(self.role if self.role is not None else 'Participants', data_manager=self.data_manager)

    def fetch_team_data(self):
        if not self.data_manager.check('BATTLE_TEAMS',f'battle_id = {self.battle_id} AND team_id = {self.id}'):
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_TEAMS',filter=f'battle_id = {self.battle_id} AND team_id = {self.id}')[0]

    def add_actor(self, actor_id:int, **kwargs):
        if self.data_manager.check('BATTLE_CHARACTERS',f'character_id = {actor_id}'):
            query = {'battle_id': self.battle_id,
                     'layer_id': kwargs.get('layer_id', 0),
                     'object': kwargs.get('object', None),
                     'team_id': self.id}

            self.data_manager.update('BATTLE_CHARACTERS', query, f'character_id = {actor_id}')
        else:
            query = {'battle_id': self.battle_id,
                     'character_id': actor_id,
                     'layer_id': kwargs.get('layer_id', 0),
                     'object': kwargs.get('object', None),
                     'team_id': self.id,
                     'initiative': 0,
                     'is_active': kwargs.get('is_active', None)}

            self.data_manager.insert('BATTLE_CHARACTERS', query)

            Actor(actor_id).set_initiative()


class Battlefield:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_main_data()
        self.label = data.get('label','Сражение')
        self.distance_delta = data.get('distance_delta', 50)
        self.description = data.get('desc', '')
        self.time = DayTime(data.get('time_type','Day'), data_manager=self.data_manager)
        self.weather = Weather(data.get('weather_type','Sunny'), data_manager=self.data_manager)

        self.round = data.get('round', 0)
        self.key_round_delay = data.get('key_round', 3)
        self.layers = self.fetch_layers()

    def fetch_main_data(self):
        if self.data_manager.check('BATTLE_INIT',filter=f'id = {self.id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_INIT',filter=f'id = {self.id}')[0]

    def fetch_layers(self):
        if self.data_manager.check('BATTLE_LAYERS',f'battle_id = {self.id}') is None:
            return {}
        else:
            c_data = self.data_manager.select_dict('BATTLE_LAYERS',filter=f'battle_id = {self.id}')
            total_layers = {}
            for layer in c_data:
                total_layers[layer.get('id')] = Layer(layer.get('id'), self.id, data_manager=self.data_manager)

            return total_layers

    def log_event(self, **kwargs):
        return EventLogger(data_manager=self.data_manager, battle_id=self.id, round=self.round, **kwargs)

    def fetch_actors(self):
        if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.id}') is None:
            return []
        else:
            return [Actor(c['character_id']) for c in self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'battle_id = {self.id}')]

    def add_actor(self, actor_id:int, **kwargs):
        if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {actor_id}'):
            prompt = {'battle_id': self.id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative',Actor(actor_id, data_manager=self.data_manager).roll_initiative()),
                      'is_active': None}

            self.data_manager.update('BATTLE_CHARACTERS',prompt,f'character_id = {actor_id}')
        else:
            prompt = {'battle_id': self.id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative', Actor(actor_id, data_manager=self.data_manager).roll_initiative()),
                      'is_active': None}
            self.data_manager.insert('BATTLE_CHARACTERS', prompt)

    def max_initiative_actor(self):
        c_list = self.fetch_actors()
        c_actor = None
        max_initiative = 0
        for act in c_list:
            if act.initiative > max_initiative and act.is_active is None:
                max_initiative = act.initiative
                c_actor = act

        return c_actor

    def next_round(self):
        self.round += 1
        self.data_manager.update('BATTLE_INIT', {'round': self.round}, f'id = {self.id}')

        if self.layers:
            for i in self.layers:
                self.layers[i].update_layer()

        if self.round % self.key_round_delay == 0:
            for act in self.fetch_actors():
                act.set_initiative()
                act.set_unactive()

        self.log_event(action_id='NewCycle',desc=f'Начинается {self.round} раунд!')
        self.next_actor()

    def next_actor(self):
        if self.data_manager.check('BATTLE_CHARACTERS',f'battle_id = {self.id} AND is_active = 1'):
            c_actor = self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'battle_id = {self.id} AND is_active = 1')[0].get('character_id')
            Actor(c_actor, data_manager=self.data_manager).set_done_active()

        if self.max_initiative_actor():
            n_actor = self.max_initiative_actor()
            n_actor.set_active()
            self.log_event(actor=n_actor.id, action_id='NewTurn', desc='Начинает свой ход!')

    def create_team(self, label:str, role:str=None):
        if not self.data_manager.check('BATTLE_TEAMS','battle_id'):
            c_id = 0
        else:
            c_id = self.data_manager.maxValue('BATTLE_TEAMS','team_id',f'battle_id = {self.id}') + 1

        query = {'battle_id': self.id,
                 'team_id': c_id,
                 'label': label,
                 'role': role}

        self.data_manager.insert('BATTLE_TEAMS',query)

        return BattleTeam(c_id, self.id, data_manager=self.data_manager)


class ActorCombat:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.ap = data.get('ap',0)
        self.ap_bonus = data.get('ap_bonus', 0)
        self.luck = data.get('luck', 0)
        self.blood_lost = data.get('blood_lost', 0)

        self.supressed = data.get('supressed', None)
        self.hunted = data.get('hunted', None)
        self.contained = data.get('contained', None)
        self.ready = data.get('ready', False) in [1, 'Да', 'да']
        self.current_target = data.get('target', None)
        self.movement_points = data.get('movement_points', None) if data.get('movement_points', None) is not None else 0

        self.melee_target = data.get('melee_target', None)
        self.melee_target_from = self.get_melee_target_from()

        self.supressed_from = self.supresser_id()
        self.contained_from = self.container_id()
        self.hunted_from = self.hunter_id()

    def get_melee_target_from(self):
        if self.data_manager.check('CHARS_COMBAT', f'melee_target = {self.id}'):
            return [char.get('id') for char in self.data_manager.select_dict('CHARS_COMBAT',filter=f'melee_target = {self.id}')]
        else:
            return []

    def fetch_data(self):
        if self.data_manager.check('CHARS_COMBAT',f'id = {self.id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {self.id}')[0]

    def hunter_id(self):
        if self.data_manager.check('CHARS_COMBAT',f'hunted = {self.id}') is None:
            return None
        else:
            total_hunters = []
            for e in self.data_manager.select_dict('CHARS_COMBAT',filter=f'hunted = {self.id}'):
                total_hunters.append(e.get('id'))

            return total_hunters

    def supresser_id(self):
        if self.data_manager.check('CHARS_COMBAT',f'supressed = {self.id}') is None:
            return None
        else:
            total_supressers = []
            for e in self.data_manager.select_dict('CHARS_COMBAT',filter=f'supressed = {self.id}'):
                total_supressers.append(e.get('id'))
            return total_supressers

    def container_id(self):
        data = self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'character_id = {self.id}')[0]
        c_battle = data.get('battle_id')
        c_layer = data.get('layer_id')
        total_containers = []
        potential_containers = []

        for e in self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'battle_id = {c_battle} AND (layer_id = {c_layer+1} OR {c_layer-1})'):
            potential_containers.append(e.get('character_id'))

        for e in potential_containers:
            e_contained = self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {e}')[0].get('contained', None)
            if e_contained and (e_contained + 1 == c_layer or e_contained - 1 == c_layer):
                total_containers.append(e)

        return total_containers

    def is_enemy_ready(self, enemy_id:int):
        if self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') is None:
            return False
        else:
            status = self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {enemy_id}')[0].get('ready', None)
            if status:
                return True
            else:
                return False

    def set_melee_target(self, enemy_id:int):
        self.data_manager.update('CHARS_COMBAT', {'melee_target': enemy_id}, filter=f'id = {self.id}')
        self.melee_target = enemy_id

    def flee_from_melee(self):
        if self.melee_target_from:
            for i in self.melee_target_from:
                self.data_manager.update('CHARS_COMBAT',{'melee_target': None},f'id = {i}')
        else:
            pass

    def get_current_weapons(self):
        return CharacterCombat(self.id, data_manager=self.data_manager).current_weapons_id()

    def check_if_current_weapon_melee(self, weapon_id:int=None):
        from ArbWeapons import Weapon

        c_weapon = self.get_current_weapons()
        if c_weapon is None:
            return False
        else:
            if weapon_id in c_weapon:
                c_weapon = weapon_id
            else:
                c_weapon = random.choice(c_weapon)

            c_class = Weapon(c_weapon, data_manager=self.data_manager).Class
            if c_class == 'ColdSteel':
                return True
            else:
                return False

    def ap_new(self) -> int:
        c_dex = CharacterAttributes(self.id).check_characteristic('Выносливость')

        pain = Body(self.id).calculate_total_pain()
        cons = Body(self.id).physical_stat('Сознание')
        bonus = self.ap_bonus

        if pain <= 10:
            pain = 0
        else:
            pain = pain - 10

        ap = round(c_dex / 3) * ((cons - pain) / 100) + bonus

        self.data_manager.update('CHARS_COMBAT', {'ap_bonus': 0}, filter=f'id = {self.id}')

        self.ap += ap

        return ap

    def ap_use(self, ap) -> None:
        from ArbCharacters import Race, Character

        bleed = Body(self.id).calculate_total_bleeding()
        blood = Race(Character(self.id).Race).Blood

        c_loss = (bleed / blood) * 100

        c_ap_bloodloss = round((c_loss / 24) / 60, 2)

        total_bloodloss = ap * c_ap_bloodloss

        print(self.ap - ap)

        self.data_manager.update('CHARS_COMBAT', {'blood_lost': self.blood_lost - total_bloodloss},filter=f'id = {self.id}')
        self.data_manager.update('CHARS_COMBAT', {'ap': self.ap - ap}, filter=f'id = {self.id}')
        self.ap -= ap

    def ap_cost_usage(self, ap:int):
        if self.ap >= ap:
            self.ap_use(ap)
            return True
        else:
            return False

    def use_movement_points(self, mp:int):
        self.movement_points += mp
        self.data_manager.update('CHARS_COMBAT', {'movement_points': self.movement_points}, f'id = {self.id}')

    def clear_statuses(self):
        prompt = {'supressed': None,
                  'hunted': None,
                  'contained': None,
                  'ready': None,
                  'melee_target': None,
                  'target': None}

        self.data_manager.update('CHARS_COMBAT',prompt,f'id = {self.id}')

    def supress_enemy(self, enemy_id:int):
        if self.data_manager.check('CHARS_COMBAT', f'id = {enemy_id}') is None:
            return False
        else:
            c_cost = 2
            if self.ap_cost_usage(c_cost):
                self.clear_statuses()
                self.data_manager.update('CHARS_COMBAT', {'supressed': enemy_id}, f'id = {self.id}')
                self.set_target(enemy_id)
                return True
            else:
                return False

    def hunt_enemy(self, enemy_id:int):
        if self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') is None:
            return False
        else:
            c_cost = 2
            if self.ap_cost_usage(c_cost):
                self.clear_statuses()
                self.data_manager.update('CHARS_COMBAT',{'hunted': enemy_id}, f'id = {self.id}')
                self.set_target(enemy_id)
                return True
            else:
                return False

    def contain_enemy(self, layer_id:int):
        c_layer = Actor(self.id, data_manager=self.data_manager).current_layer_id
        c_battle = Actor(self.id, data_manager=self.data_manager).current_battle_id

        if layer_id > c_layer:
            layer_id = c_layer + 1 if layer_id > c_layer + 1 else c_layer
        elif layer_id < c_layer:
            layer_id = c_layer - 1 if layer_id < c_layer - 1 else c_layer

        if self.data_manager.check('BATTLE_LAYERS', f'id = {layer_id} AND battle_id = {c_battle}') is None:
            return False
        else:
            c_cost = 2
            if self.ap_cost_usage(c_cost):
                self.clear_statuses()
                self.data_manager.update('CHARS_COMBAT', {'contained': layer_id}, f'id = {self.id}')

                return True
            else:
                return False

    def get_prepared(self):
        c_cost = 2
        if self.ap_cost_usage(c_cost):
            self.clear_statuses()
            self.data_manager.update('CHARS_COMBAT',{'ready': 1}, f'id = {self.id}')
            return True
        else:
            return False

    def set_target(self, enemy_id:int):
        if self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') is None:
            return False
        else:
            self.data_manager.update('CHARS_COMBAT',{'target': enemy_id}, f'id = {self.id}')
            return True

    def clear_target(self):
        self.data_manager.update('CHARS_COMBAT',{'target': None}, f'id = {self.id}')

    def get_target_id(self):
        if self.current_target:
            return self.current_target
        else:
            return None

    def skip_turn(self):
        current_bonus = self.ap + self.ap_bonus
        self.data_manager.update('CHARS_COMBAT',{'ap_boonus': current_bonus}, f'id = {self.id}')
        self.ap = 0

    def attack_if_in_melee(self):
        attacked_enemies = []

        if self.melee_target_from:
            for enemy_id in self.melee_target_from:
                if ActorCombat(enemy_id).get_current_weapons():
                    ActorCombat(enemy_id, data_manager=self.data_manager).melee_attack(self.id, provoked=True)
                else:
                    ActorCombat(enemy_id, data_manager=self.data_manager).race_attack(self.id, provoked=True)
                attacked_enemies.append(enemy_id)

        if attacked_enemies:
            return random.choice(attacked_enemies)
        else:
            return None

    def attack_if_hunted(self):
        attacked_enemies = []
        if self.hunted_from:
            for enemy_id in self.hunted_from:
                e_combat = ActorCombat(enemy_id, data_manager=self.data_manager)
                target = [self.id]

                if self.melee_target_from:
                    target += self.melee_target_from

                if self.melee_target:
                    target.append(self.melee_target)

                total_target = random.choice(target)
                e_combat.range_attack(total_target, provoked=True, ignore_cover=True)
                if total_target == self.id:
                    attacked_enemies.append(enemy_id)

        if attacked_enemies:
            return attacked_enemies
        else:
            return None

    def attack_if_supressers(self):
        attacked_enemies = []
        if self.supressed_from:
            for enemy_id in self.supressed_from:
                ActorCombat(enemy_id, data_manager=self.data_manager).range_attack(self.id, provoked=True)

                attacked_enemies.append(enemy_id)

        if attacked_enemies:
            return attacked_enemies
        else:
            return None

    def attack_if_contained(self):
        attacked_enemies = []
        if self.contained_from:
            for enemy_id in self.contained_from:
                ActorCombat(enemy_id, data_manager=self.data_manager).range_attack(self.id, provoked=True)

                attacked_enemies.append(enemy_id)

        if attacked_enemies:
            return attacked_enemies
        else:
            return None

    def check_character_owner(self):
        c_owner = self.data_manager.select_dict('CHARS_INIT',filter=f'id = {self.id}')[0].get('owner', None)
        if c_owner is not None:
            return c_owner
        else:
            return None

    def get_current_ammo(self, **kwargs):
        from ArbItems import Item

        if self.check_character_owner() is None:
            return -1, None

        c_weapon = kwargs.get('weapon_id', None)
        if c_weapon is None:
            return 0, None

        if self.data_manager.check('CHARS_MAGAZINE',f'weapon_id = {c_weapon}') is None:
            return 0, None

        c_bullets_id = self.data_manager.select_dict('CHARS_MAGAZINE', filter=f'weapon_id = {c_weapon}')[0].get('magazine_id', None)
        if c_bullets_id:
            return Item(c_bullets_id, data_manager=self.data_manager).Value, c_bullets_id

    def get_actor_inventory(self):
        from ArbItems import Item
        if self.data_manager.check('CHARS_INVENTORY',f'character_id = {self.id}') is None:
            return {}
        else:
            total_items = {}
            for item in self.data_manager.select_dict('CHARS_INVENTORY', f'character_id = {self.id}'):
                total_items[item.get('item_id')] = Item(item.get('item_id'), data_manager=self.data_manager)

            return total_items
    def get_current_grenades(self):
        from ArbAmmo import Ammunition
        from ArbWeapons import HandGrenade

        if self.check_character_owner() is None:
            return None
        else:
            items = self.get_actor_inventory()
            total_grenades = {}
            for item in items:
                if items[item].Class == 'Боеприпасы':
                    if Ammunition(items[item].Type, data_manager=self.data_manager).caliber == 'Граната':
                        total_grenades[item] = HandGrenade(item, data_manager=self.data_manager)

            return total_grenades

    def use_ammo(self, value:int=None, **kwargs):
        from ArbItems import Item

        c_weapon = kwargs.get('weapon_id', None)
        if c_weapon is None:
            return None

        if self.check_character_owner() is None:
            return None
        else:
            c_ammo = self.get_current_ammo(weapon_id=c_weapon)
            if c_ammo[0] != -1:
                Item(c_ammo[1], data_manager=self.data_manager).change_value(-1*value if value else -1)

    def range_attack(self, enemy_id:int, **kwargs):
        from ArbCharacters import Character, Race
        from ArbWeapons import Weapon

        c_weapon = kwargs.get('weapon_id', None)
        if c_weapon is None:
            c_weapon = random.choice(CharacterCombat(self.id, data_manager=self.data_manager).current_weapons_id())

        if self.check_if_current_weapon_melee(c_weapon):
            return None

        c_ammo = self.get_current_ammo(weapon_id=c_weapon)
        if c_ammo[0] == 0:
            return None

        c_cost = CharacterCombat(self.id, data_manager=self.data_manager).weapon_attack_cost(c_weapon)

        if c_cost > self.ap and not kwargs.get('provoked', None):
            return None
        elif kwargs.get('provoked', None):
            pass
        else:
            self.ap_use(c_cost)

        if self.melee_target_from:
            c_enemies = self.attack_if_in_melee()
            if c_enemies:
                enemy_id = c_enemies

            if Weapon(c_weapon, data_manager=self.data_manager).Class not in ['SMG', 'PST', 'TUR', 'SG']:
                return self.melee_attack(enemy_id, provoked=True)

        if self.hunted_from:
            self.attack_if_hunted()
            return None

        enemy = Actor(enemy_id, data_manager=self.data_manager)
        distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
        e_cover = enemy.get_current_object()
        if e_cover:
            enemy_coverage = random.randint(0, e_cover.protection) if not kwargs.get('ignore_cover', False) else 0
        else:
            enemy_coverage = 0

        enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size

        enemy_attributes = {'distance': distance_to_enemy,
                            'cover': enemy_coverage,
                            'size': enemy_size,}

        total_damage, total_attacks, weapon_loudness, damage_for_cover = RangeAttack(self.id, enemy_id, enemy_attributes=enemy_attributes, data_manager=self.data_manager).initiate(c_weapon)
        #CharacterCombat(self.id, data_manager=self.data_manager).range_attack(c_weapon, enemy_id=enemy_id, enemy_distance= distance_to_enemy, enemy_cover= enemy_coverage,enemy_size= enemy_size, **kwargs)

        if damage_for_cover > 0 and e_cover:
            e_cover.recive_damage(damage_for_cover)

        if total_attacks != 0:
            if c_ammo[0] != -1:
                self.use_ammo(total_attacks)

            for i in range(total_attacks):
                self.make_sound('GunShot', weapon_loudness)
        else:
            self.make_sound('Click', random.randint(10,150))

        return total_damage

    def melee_attack(self, enemy_id:int, **kwargs):
        from ArbCharacters import Character, Race
        from ArbAttacks import MeleeAttack

        c_weapon = kwargs.get('weapon_id', None)
        if c_weapon is None:
            c_weapon = random.choice(CharacterCombat(self.id, data_manager=self.data_manager).current_weapons_id())

        c_cost = CharacterCombat(self.id, data_manager=self.data_manager).weapon_attack_cost(kwargs.get(c_weapon))

        if c_cost > self.ap and not kwargs.get('provoked', None):
            return None
        elif kwargs.get('provoked', None):
            pass
        else:
            self.ap_use(c_cost)

        if self.melee_target_from:
            c_enemies = self.attack_if_in_melee()
            if c_enemies:
                enemy_id = c_enemies

        if self.hunted_from:
            self.attack_if_hunted()
            return None

        enemy = Actor(enemy_id, data_manager=self.data_manager)
        distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
        if distance_to_enemy > 0:
            return None

        e_cover = enemy.get_current_object()
        if e_cover:
            enemy_coverage = e_cover.protection
        else:
            enemy_coverage = 0

        enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size

        enemy_attributes = {'distance': distance_to_enemy,
                            'cover': enemy_coverage,
                            'size': enemy_size}

        total_damage, total_attacks, weapon_loudness = MeleeAttack(self.id, enemy_id, enemy_attributes=enemy_attributes,
                                                                   data_manager=self.data_manager).initiate(c_weapon)

        if total_attacks != 0:
            for i in range(total_attacks):
                self.make_sound('Fight', weapon_loudness)

        return total_damage

    def race_attack(self, enemy_id:int, **kwargs):
        from ArbCharacters import Character, Race
        from ArbHealth import RaceAttack
        from ArbAttacks import BodyPartAttack

        c_attack = kwargs.get('attack_id', None)

        if not c_attack:
            c_attack = random.choice(Body(self.id, data_manager=self.data_manager).available_attacks())

        c_cost = CharacterCombat(self.id, data_manager=self.data_manager).race_attack_cost(c_attack)

        if c_cost > self.ap and not kwargs.get('provoked', None):
            return None
        elif kwargs.get('provoked', None):
            pass
        else:
            self.ap_use(c_cost)

        if self.melee_target_from:
            c_enemies = self.attack_if_in_melee()
            if c_enemies:
                enemy_id = c_enemies

        if self.hunted_from:
            self.attack_if_hunted()
            return None

        enemy = Actor(enemy_id, data_manager=self.data_manager)
        distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
        if RaceAttack(c_attack, data_manager=self.data_manager).range < distance_to_enemy:
            return None

        e_cover = enemy.get_current_object()
        if e_cover:
            enemy_coverage = e_cover.protection
        else:
            enemy_coverage = 0

        enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size

        enemy_attributes = {'distance': distance_to_enemy,
                            'cover': enemy_coverage,
                            'size': enemy_size}

        total_damage, total_attacks = BodyPartAttack(self.id, enemy_id, enemy_attributes=enemy_attributes, data_manager=self.data_manager).initiate(c_attack)

        self.make_sound('Fight', random.randint(10, 150))

        return total_damage

    def make_sound(self, sound_id:str, volume:int=None):
        volume = volume if volume is not None else random.randint(10,150)

        Actor(self.id, data_manager=self.data_manager).make_sound(sound_id, volume)

    def throw_grenade(self, enemy_id:int, **kwargs):
        from ArbAmmo import Grenade
        from ArbAttacks import Explosion

        if kwargs.get('grenade_id', None) is not None:
            current_grenade = self.get_current_grenades()[kwargs.get('grenade_id')]
        else:
            if self.check_character_owner() is not None:
                return None
            else:
                grenades_types = [i.get('id') for i in self.data_manager.select_dict('AMMO', filter=f'caliber = "Граната"')]
                current_grenade = Grenade(random.choice(grenades_types), data_manager=self.data_manager)


        print(current_grenade.ammo_id)
        c_cost = 3

        if c_cost > self.ap and not kwargs.get('provoked', None):
            return None
        elif kwargs.get('provoked', None):
            pass
        else:
            self.ap_use(c_cost)

        if self.melee_target_from:
            self.attack_if_in_melee()
            return None

        if self.hunted_from:
            self.attack_if_hunted()
            return None

        enemy = Actor(enemy_id, data_manager=self.data_manager)
        distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
        if distance_to_enemy > 60:
            return None

        main_target = [enemy_id]
        maybe_damaged = []

        e_cover = enemy.get_current_object()
        if e_cover:
            main_target += [i for i in e_cover.current_characters() if i != enemy_id]

        current_delta = Actor(self.id, data_manager=self.data_manager).get_current_battle().distance_delta
        current_layer = Actor(self.id, data_manager=self.data_manager).get_current_layer().id
        grenade_layers = current_grenade.get_damaged_layers(current_delta, current_layer)

        c_battle_layers_ids = Actor(self.id, data_manager=self.data_manager).get_current_battle().layers.keys()

        for layer in grenade_layers:
            if layer in c_battle_layers_ids:
                maybe_damaged += Layer(layer, Actor(self.id, data_manager=self.data_manager).current_battle_id, data_manager=self.data_manager).characters_not_in_cover()

        total_damage, current_loud, damage_for_cover = Explosion(main_target, maybe_damaged, data_manager=self.data_manager).initiate(current_grenade)
        self.make_sound('Explotion', current_loud)

        if e_cover:
            e_cover.recive_damage(damage_for_cover)

        return total_damage


class Actor:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.combat_data = self.fetch_combat_data()
        battle_data = self.fetch_battle_data()
        self.current_battle_id = battle_data.get('battle_id', None)
        self.current_layer_id = battle_data.get('layer_id', None)
        self.current_object_id = battle_data.get('object', None)
        self.team_id = battle_data.get('team_id', None)

        self.max_view_distance = self.distance_of_view()

        self.initiative = battle_data.get('initiative', 0)
        self.is_active = battle_data.get('is_active', None)

        self.actor_attributes = self.fetch_attributes()

    def get_max_movement(self):
        c_movement = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Movement')
        return round(1 + (c_movement / 50))

    def get_nearby_layers_id(self):
        forward = self.current_layer_id + 1
        back = self.current_layer_id - 1
        if back < 0:
            back = None

        if forward > max(self.get_current_battle().layers.keys()):
            forward = None

        return [back, forward]

    def move_forward(self):
        c_slots = self.get_nearby_layers_id()
        if c_slots[1] is None:
            return False

        c_cost = self.movement_cost()
        if c_cost > self.actor_attributes.ap:
            return False
        else:
            self.actor_attributes.use_movement_points(1)
            self.actor_attributes.ap_use(c_cost)
            self.set_layer(c_slots[1])
            return True

    def move_back(self):
        c_slots = self.get_nearby_layers_id()
        if c_slots[0] is None:
            return False

        c_cost = self.movement_cost()
        if c_cost > self.actor_attributes.ap:
            return False
        else:
            self.actor_attributes.use_movement_points(1)
            self.actor_attributes.ap_use(c_cost)
            self.set_layer(c_slots[0])
            return True

    def steps_volume(self):
        return random.randint(10, 100)

    def move_to_layer(self, layer_id:int):
        if layer_id not in self.get_current_battle().layers.keys():
            return False

        if self.current_layer_id == layer_id:
            return False

        steps_volume = self.steps_volume()

        self.remove_cover()

        if self.current_layer_id < layer_id:
            for _ in range(layer_id-self.current_layer_id):
                self.move_forward()
            self.make_sound('Steps', steps_volume)
        elif self.current_layer_id > layer_id:
            for _ in range(self.current_layer_id-layer_id):
                self.move_back()
            self.make_sound('Steps', steps_volume)

        if self.actor_attributes.get_melee_target_from():
            self.actor_attributes.flee_from_melee()

        return self.current_layer_id

    def make_sound(self, sound_id:str, volume:int=None):
        prompt = {'id': self.data_manager.maxValue('BATTLE_SOUNDS','id')+1,
                  'battle_id': self.current_battle_id,
                  'actor_id': self.id,
                  'layer_id': self.current_layer_id,
                  'sound_id': sound_id,
                  'round': self.get_current_battle().round,
                  'volume': volume if volume else random.randint(50,150)}

        self.data_manager.insert('BATTLE_SOUNDS', prompt)

    def detect_sound_source(self, sound_id:int):
        from ArbRoll import RollCapacity
        c_battle = self.get_current_battle()

        c_sound = InBattleSound(sound_id, data_manager=self.data_manager)
        c_distance = self.distance_to_layer(c_sound.layer_id)
        c_chance = c_sound.get_detection_chance(c_distance, c_battle.round)
        c_hearing = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Слух')

        if RollCapacity(c_hearing).dice >= 100-c_chance+c_battle.time.noise+c_battle.weather.noise:
            self.take_target(c_sound.actor_id)
            return c_sound.actor_id
        else:
            return False

    def fetch_attributes(self):
        return ActorCombat(self.id, data_manager=self.data_manager)

    def fetch_combat_data(self):
        return CharacterCombat(self.id, data_manager=self.data_manager)

    def fetch_battle_data(self):
        if self.data_manager.check('BATTLE_CHARACTERS',f'character_id = {self.id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'character_id = {self.id}')[0]

    def get_current_layer(self):
        if self.current_layer_id is not None:
            return Layer(self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
        else:
            return None

    def get_current_object(self):
        if self.current_object_id is not None:
            return GameObject(self.current_object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
        else:
            return None

    def get_current_battle(self):
        if self.current_battle_id is not None:
            return Battlefield(self.current_battle_id)
        else:
            return None

    def take_target(self, enemy_id:int):
        ActorCombat(self.id, data_manager=self.data_manager).set_target(enemy_id)

    def take_supression(self, layer_id:int=None):
        return ActorCombat(self.id, data_manager=self.data_manager).supress_enemy(layer_id)

    def take_contain(self, enemy_id:int=None):
        return ActorCombat(self.id, data_manager=self.data_manager).contain_enemy(enemy_id)

    def take_hunt(self, enemy_id:int=None):
        return ActorCombat(self.id, data_manager=self.data_manager).hunt_enemy(enemy_id)

    def get_ready(self):
        return ActorCombat(self.id, data_manager=self.data_manager).get_prepared()

    def skip_turn(self):
        ActorCombat(self.id, data_manager=self.data_manager).skip_turn()
        self.set_unactive()

    def movement_cost(self):
        skill = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Передвижение')
        c_movement = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Перемещение')
        c_delta = self.get_current_battle().distance_delta / 50
        if c_movement <= 0:
            return None
        else:
            move_factor = (200-c_movement)/100

        c_difficulty = self.get_current_layer().terrain.movement_difficulty
        c_base_cost = self.get_current_layer().terrain.movement_cost

        return round((1+(c_difficulty - skill)/100) * move_factor * c_base_cost * c_delta)

    def calculate_slot_disguise(self, slot_name:str):
        from ArbClothes import Clothes
        c_clothes_id = self.combat_data.armors_id()[slot_name]
        total_calculation = 0
        for i in c_clothes_id.keys():
            total_calculation += Clothes(c_clothes_id[i]).cloth_disguise()
        return total_calculation

    def calculate_clothes_disguise(self):
        c_clothes_id = self.combat_data.armors_id()
        c_slots_disguise = {}
        total_disguise = 0
        for c_slot in c_clothes_id.keys():
            slot_disguise = self.calculate_slot_disguise(c_slot)
            c_slots_disguise[c_slot] = slot_disguise
            total_disguise += slot_disguise

        if total_disguise == 0 or len(c_clothes_id.keys()) == 0:
            return 0
        else:
            return round(total_disguise / len(c_clothes_id.keys()))

    def actor_disguise(self):
        from ArbCharacters import Character, Race
        clothes_disguise = self.calculate_clothes_disguise()
        race_disguise = Race(Character(self.id, data_manager=self.data_manager).Race, data_manager=self.data_manager).NatureDisguise
        weather_disguise = 1+(100-self.get_current_battle().weather.visibility)/100 if self.get_current_battle() is not None else 1
        daytime_disguise = 1+(100-self.get_current_battle().time.visibility)/100 if self.get_current_object() is not None else 1
        terrain_disguise = 1+(100-self.get_current_layer().terrain.visibility)/100 if self.get_current_layer() is not None else 1
        object_disguise = self.get_current_object().coverage if self.get_current_object() is not None else 0

        return round((race_disguise+clothes_disguise+object_disguise)*weather_disguise*terrain_disguise*daytime_disguise, 2)

    def distance_of_view(self):
        c_eyes = Body(self.id, data_manager=self.data_manager).physical_stat('Зрение')/100
        basic_view = 5400
        c_battle = self.get_current_battle()
        if c_battle is None:
            time_factor = 1
            weather_factor = 1
        else:
            time_factor = c_battle.time.visibility/100
            weather_factor = c_battle.weather.visibility/100

        return basic_view * c_eyes * time_factor * weather_factor

    def basic_layer_vigilance(self, current_layer: int, target_layer: int, distance_delta):
        total_distance = abs(target_layer - current_layer) * distance_delta
        return round((self.max_view_distance - total_distance) / self.max_view_distance * 100, 2) if current_layer != target_layer else 100

    def battle_layers_vigilance(self):
        c_battle = self.get_current_battle()
        c_layer_id = self.get_current_layer().id
        c_battle_layers = c_battle.layers
        c_battle_layers_id = set(c_battle.layers.keys())
        c_delta = c_battle.distance_delta

        layers_vigilance = {}
        cached_results = {}

        for i in reversed([i for i in c_battle_layers_id if i < c_layer_id]):
            if i in layers_vigilance:
                break

            if i in cached_results:
                layers_vigilance[i] = cached_results[i]
            else:
                vigilance = self.basic_layer_vigilance(c_layer_id, i, c_delta)
                layers_vigilance[i] = vigilance
                cached_results[i] = vigilance

            if c_battle_layers[i].terrain.coverage and i != c_layer_id:
                break

        for i in [i for i in c_battle_layers_id if i >= c_layer_id]:
            if i in layers_vigilance:
                break

            if i in cached_results:
                layers_vigilance[i] = cached_results[i]
            else:
                vigilance = self.basic_layer_vigilance(c_layer_id, i, c_delta)
                layers_vigilance[i] = vigilance
                cached_results[i] = vigilance

            if c_battle_layers[i].terrain.coverage and i != c_layer_id:
                break

        return layers_vigilance

    def get_characters_on_layer(self, layer_id:int=None):
        c_layer = layer_id if layer_id is not None else self.current_layer_id
        if not self.data_manager.check('BATTLE_CHARACTERS',f'layer_id = {c_layer} AND battle_id = {self.current_battle_id}'):
            return []
        else:
            return [charac.get('character_id') for charac in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'layer_id = {c_layer} AND battle_id = {self.current_battle_id}')]

    def get_visible_characters_on_layer(self, layer_id:int=None):
        c_layer = layer_id if layer_id is not None else self.current_layer_id
        c_characters = self.get_characters_on_layer(layer_id)
        c_visibility = self.battle_layers_vigilance()[c_layer]
        if not c_characters:
            return []
        else:
            total_characters = []
            for character in c_characters:
                if character == self.id:
                    continue

                if Actor(character, data_manager=self.data_manager).actor_disguise() >= c_visibility:
                    pass
                else:
                    total_characters.append(character)

            return total_characters

    def get_visibile_characters_id(self):
        total_characters = {}
        layers = self.battle_layers_vigilance()

        for layer in layers:
            total_characters[layer] = self.get_visible_characters_on_layer(layer)

        return total_characters

    def get_all_visible_characters_id(self):
        c_characters = self.get_visibile_characters_id()
        total_chars = []
        for i in c_characters.keys():
            total_chars += c_characters[i]

        return total_chars

    def distance_to_layer(self, layer_id:int):
        c_distance_delta = self.get_current_battle().distance_delta
        move_iterable = abs(layer_id - self.current_layer_id)
        distance = c_distance_delta * move_iterable

        return distance

    def move_to_object(self, object_id:int):
        layer_objects = self.get_current_layer().objects
        if object_id not in layer_objects.keys():
            return False

        if GameObject(object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager).available_slots <= 0:
            return False

        c_cost = round(self.movement_cost() * 0.5)
        if c_cost > self.actor_attributes.ap:
            return False
        else:
            self.remove_cover()
            self.actor_attributes.ap_use(c_cost)
            self.set_cover(object_id)
            self.make_sound('Steps', self.steps_volume())
            if self.actor_attributes.get_melee_target_from():
                self.actor_attributes.flee_from_melee()
            return True

    def roll_initiative(self, **kwargs):
        battle_baffs = 0

        pain = Body(self.id, data_manager=self.data_manager).calculate_total_pain()
        agility = CharacterAttributes(self.id, data_manager=self.data_manager).check_characteristic('Ловкость')
        reaction = CharacterAttributes(self.id, data_manager=self.data_manager).check_characteristic('Реакция')
        lvl = CharacterAttributes(self.id, data_manager=self.data_manager).check_progress().get('lvl', 1)

        mind = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Сознание')
        if mind < 30:
            mind = 30

        rolls = []
        for _ in range(lvl):
            c_roll = random.randint(kwargs.get('min',0) + kwargs.get('min_bonus',0), kwargs.get('max', 100)) + kwargs.get('max_bonus',0)
            rolls.append(c_roll)
        total_roll = max(rolls)

        return round(((agility+reaction)/2 + battle_baffs) * (mind/100) + total_roll)

    def set_initiative(self, **kwargs):
        if self.data_manager.check('BATTLE_CHARACTERS',f'character_id = {self.id}') is None:
            return None
        else:
            c_roll = kwargs.get('initiative', self.roll_initiative(**kwargs))
            self.data_manager.update('BATTLE_CHARACTERS',{'initiative': c_roll}, f'character_id = {self.id}')
            self.initiative = c_roll

    def set_active(self):
        self.data_manager.update('BATTLE_CHARACTERS',{'is_active': 1}, f'character_id = {self.id}')

    def set_unactive(self):
        self.data_manager.update('BATTLE_CHARACTERS',{'is_active': None}, f'character_id = {self.id}')

    def set_done_active(self):
        self.data_manager.update('BATTLE_CHARACTERS',{'is_active': 0}, f'character_id = {self.id}')

    def set_team(self, team_id:int=None, team_label:str=None):
        if team_id is not None:
            if self.data_manager.check('BATTLE_TEAMS',f'team_id = {team_id} AND battle_id = {self.current_battle_id}') is None:
                return None
            else:
                self.data_manager.update('BATTLE_CHARACTERS',{'team_id': team_id}, filter=f'character_id = {self.id}')
                self.team_id = team_id
        else:
            if self.data_manager.check('BATTLE_TEAMS',f'label = "{team_label}" AND battle_id = {self.current_battle_id}') is None:
                return None
            else:
                team_id = self.data_manager.select_dict('BATTLE_TEAMS',filter=f'label = "{team_label}" AND battle_id = {self.current_battle_id}')
                self.data_manager.update('BATTLE_CHARACTERS', {'team_id': team_id}, filter=f'character_id = {self.id}')
                self.team_id = team_id

    def remove_cover(self):
        self.data_manager.update('BATTLE_CHARACTERS',{'object': None},f'character_id = {self.id}')

    def set_cover(self, cover_id:int):
        if not self.data_manager.check('BATTLE_OBJECTS',f'battle_id = {self.current_battle_id} AND layer_id = {self.current_layer_id} AND object_id = {cover_id}'):
            return False
        else:
            if GameObject(cover_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager).available_slots <= 0:
                return False
            else:
                self.data_manager.update('BATTLE_CHARACTERS',{'object': cover_id}, f'character_id = {self.id}')

    def set_layer(self, layer_id:int):
        self.data_manager.update('BATTLE_CHARACTERS', {'layer_id': layer_id}, f'character_id = {self.id}')
        self.current_layer_id = layer_id

    def __repr__(self):
        return f'Actor[ID: {self.id}]'
