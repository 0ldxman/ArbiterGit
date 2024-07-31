# -*- coding: utf-8 -*-
import datetime
import math
import pprint
import random
from dataclasses import dataclass
from ArbDatabase import DataManager, DataModel, DataDict
from ArbEventManager import Event, EventHandler, EventManager
from ArbHealth import Body, BodyElement
from ArbSkills import Skill
from ArbSounds import InBattleSound
from ArbItems import CharacterEquipment, Inventory
from ArbDamage import Damage
from abc import ABC, abstractmethod
from ArbResponse import Response, ResponsePool
from ArbItems import Item

from functools import wraps
from collections import Counter


class Weather(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        DataModel.__init__(self, f'WEATHER_CONDS', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label','Неизвестные погодные условия')
        self.rain_intense = self.get('rain_intense', 0)
        self.wind_speed = self.get('wind_speed', 0)
        self.temperature = int(self.get('temp', 0))
        self.visibility = self.get('visibility', 100)
        self.light = self.get('light', 100)
        self.noise = self.get('noise', 0)
        self.description = self.get('desc', '')

    def __repr__(self):
        return f'Weather.{self.id}'

    def __str__(self):
        return f'{self.label}'


class DayTime(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        DataModel.__init__(self, 'DAYTIME_CONDS', f'id = "{self.id}"', data_manager=self.data_manager)
        self.label = self.get('label','Неизвестное время суток')
        self.temperature = int(self.get('temp', 0))
        self.visibility = self.get('visibility', 100)
        self.light = self.get('light', 100)
        self.noise = self.get('noise', 0)
        self.description = self.get('desc', '')

    def __repr__(self):
        return f'Daytime.{self.id}'

    def __str__(self):
        return f'{self.label}'


class Terrain(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager',DataManager())

        DataModel.__init__(self, 'TERRAIN_TYPE', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label','Неизвестная местность')
        self.desc = self.get('desc','')
        self.types = self.get('type', 'Природный')
        self.movement_cost = self.get('movement_cost',1)
        self.visibility = self.get('visibility', 100)
        self.light = self.get('light', 100)
        self.coverage = self.get('coverage', 0) == 1
        self.reachable = self.get('reachable', 1) == 1
        self.banned_transports = self.get('banned_transport','')
        self.object_types = self.get('object_types','Природный')
        self.movement_difficulty = self.get('move_difficulty', 0)
        self.height = self.get('height', 0) if self.get('height', 0) is not None else 0

    def __repr__(self):
        return f'Terrain.{self.id}'

    def __str__(self):
        return f'{self.label}'





class ObjectInteraction(ABC):
    @abstractmethod
    def interact(self, character_id:int, **kwargs) -> Response:
        pass


class ItemSpawner(ObjectInteraction):
    def interact(self, character_id:int, **kwargs) -> Response:
        from ArbGenerator import ItemManager
        from ArbItems import Inventory

        db = kwargs.get('data_manager', DataManager())

        character_inventory = Inventory.get_inventory_by_character(character_id, db).inventory_id
        item = ItemManager(kwargs.get('item_type'), inventory=character_inventory).spawn_item()
        print(item.item_id)

        return Response(True, f'Вы открываете ящик и достаёте {item.label}', 'Ящик с припасами')


class StationaryWeapon(ObjectInteraction):
    def interact(self, character_id:int, **kwargs) -> Response:
        from ArbWeapons import RangeWeapon

        db = kwargs.get('data_manager', DataManager())
        weapon_type = RangeWeapon(kwargs.get('weapon_type'), data_manager=db)
        weapon_bullets = random.choice(weapon_type.get_available_ammo())


        attacker = Actor(character_id, data_manager=db)
        target = Actor(kwargs.get('target'), data_manager=db)

        enemy_cover_id = target.get_object().id if target.get_object() else 0
        enemy_cover = GameObject(enemy_cover_id, data_manager=db).current_protection if enemy_cover_id else 0


        distance_to_enemy = attacker.calculate_total_distance(target.actor_id)

        shot_difficulty = weapon_type.shot_difficulty(distance_to_enemy, enemy_cover)

        shots = weapon_type.attacks

        for _ in range(shots):
            print('attacker', attacker.actor_id)
            roll = attacker.check_skill(weapon_type.weapon_class, shot_difficulty)
            if not roll[0]:
                continue

            raw_damage = weapon_type.random_range_damage(weapon_bullets)
            n_damage = DamageManager(data_manager=db).process_damage(target.actor_id, raw_damage)

            if not n_damage:
                continue

        return Response(True, f'Вы открываете огонь из стационарного оружия {weapon_type.label} по противнику ``{target.actor_id}`` сделав {shots} выстрела(ов)', 'Стационарное оружие')


class UnitSpawner(ObjectInteraction):
    def interact(self, character_id:int, **kwargs) -> Response:
        return Response(True, '', 'Взаимодействие с объектом')


class AmmoBox(ObjectInteraction):
    def interact(self, character_id:int, **kwargs) -> Response:
        from ArbItems import CharacterEquipment
        from ArbWeapons import Weapon

        db = kwargs.get('data_manager', DataManager())

        character_equipment = CharacterEquipment(character_id, data_manager=db)
        weapon_id = character_equipment.weapon()
        if not weapon_id:
            return Response(False, 'У вас нет экипированного оружия', 'Ящик с патронами')

        weapon = Weapon(weapon_id.item_id, data_manager=db)
        if weapon.weapon_class == 'ColdSteel':
            return Response(False, 'В данное оружие нельзя экипировать патроны', 'Ящик с патронами')

        db.update('ITEMS_BULLETS', {'out_of_ammo': None}, f'id = {weapon_id}')

        return Response(True, 'Вы достаёте из ящика с патронами необходимые боеприпасы и снаряжаете ими своё оружие', 'Ящик с патронами')






class ObjectType(DataModel):
    def __init__(self, id:str, **kwargs):
        self.object_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        super().__init__('OBJECT_TYPE', f'object_id = "{self.object_id}"')

        self.label = self.get('label', 'Неизвестный объект')
        self.type = self.get('type', None)
        self.max_slots = self.get('slots', 0)
        self.coverage = self.get('coverage', 0)
        self.protection = self.get('protection', 0)
        self.max_endurance = self.get('endurance', 0)
        self.effect_id = self.get('effect_id', None)
        self.effect_value = self.get('effect_value', None)
        self.height = self.get('height', 0) if self.get('height', 0) is not None else 0
        self.max_uses = self.get('max_uses', 0) if self.get('max_uses') else 0
        self.can_be_captured = self.get('can_be_captured', 0) == 1

    def interact(self, character_id:int, **kwargs):
        enemy = kwargs.get('enemy_id')

        if self.effect_id == 'SpawnItem':
            return ItemSpawner().interact(character_id, item_type=self.effect_value, data_manager=self.data_manager)
        elif self.effect_id == 'Weapon':
            return StationaryWeapon().interact(character_id, weapon_type=self.effect_value, data_manager=self.data_manager, target=enemy)
        elif self.effect_id == 'Ammo':
            return AmmoBox().interact(character_id, data_manager=self.data_manager)
        else:
            return Response(False, 'Объект не поддерживает взаимодействие', 'Взаимодействие с объектом')

    def __repr__(self):
        return f'ObjectType.{self.object_id}'


class GameObject(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'BATTLE_OBJECTS', f'object_id = {self.id}', data_manager=self.data_manager)

        self.layer_id = self.get('layer_id', 0)
        self.battle_id = self.get('battle_id', 0)

        self.uses = self.get('uses', 0) if self.get('uses', None) is not None else 0
        self.captured = self.get('captured', None)

        self.object_type = ObjectType(self.get('object_type'), data_manager=self.data_manager)

        self.current_endurance = self.get('endurance', self.object_type.max_endurance)
        self.current_coverage = self.object_type.coverage * (self.current_endurance / self.object_type.max_endurance)
        self.current_protection = self.object_type.protection * (self.current_endurance / self.object_type.max_endurance)

        self.available_slots = self.object_type.max_slots - len(self.current_characters())

    def interact(self, character_id:int, **kwargs):
        if not self.object_type.max_uses:
            return Response(False, 'Объект недоступен для использования', 'Взаимодействие с объектом')

        if self.uses >= self.object_type.max_uses:
            return Response(False, 'С объектом больше нельзя взаимодействовать (достигнут лимит взаимодействий)', 'Взаимодействие с объектом')

        self.count_uses(1)
        return self.object_type.interact(character_id, **kwargs)

    def count_uses(self, uses:int):
        self.uses += uses
        self.current_uses = max(0, self.object_type.max_uses - self.uses)
        self.data_manager.update('BATTLE_OBJECTS', {'uses': self.uses}, filter=f'object_id = {self.id}')

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

    def enemy_in_object(self, character_id:int):
        character_team = self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {character_id} AND battle_id = {self.battle_id} AND object = {self.id}')[0].get('team_id')
        characters_in_object = self.current_characters()
        for i in characters_in_object:
            if self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {i} AND battle_id = {self.battle_id} AND object = {self.id}')[0].get('team_id') != character_team:
                return True
        else:
            return False

    def recive_damage(self, amount:int):
        self.current_endurance -= amount
        if self.current_endurance <= 0:
            self.delete_object()
        else:
            self.data_manager.update('BATTLE_OBJECTS', {'endurance': self.current_endurance}, f'object_id = {self.id}')

    def delete_object(self):
        chars = self.current_characters()
        if chars:
            for char in chars:
                self.data_manager.update('BATTLE_CHARACTERS',{'object': None}, f'character_id = {char}')

        self.data_manager.delete('BATTLE_OBJECTS',f'object_id = {self.id} AND layer_id = {self.layer_id} AND battle_id = {self.battle_id}')

    def get_captured(self, team_id:int):
        if not self.object_type.can_be_captured:
            return

        self.captured = team_id
        self.data_manager.update('BATTLE_OBJECTS', {'captured': team_id}, f'object_id = {self.id} AND battle_id = {self.battle_id}')

    def edit(self, object_type: str=None, endurance: int=None, uses:int=None, captured:int=None):
        prompt = {
            'object_type': object_type if object_type else self.id,
            'endurance': endurance if endurance is not None else self.current_endurance,
            'uses': uses if uses is not None else self.uses,
            'captured': captured if captured is not None else self.captured
        }

        self.data_manager.update('BATTLE_OBJECTS', prompt, f'object_id = {self.id}')

    def __repr__(self):
        return f'Object.{self.id}.{self.object_type.object_id} ({self.current_endurance}/{self.object_type.max_endurance}DP)'






class TeamRole(DataModel):
    def __init__(self, role_id:str, **kwargs):
        self.role_id = role_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'TEAM_ROLES', f'id = "{self.role_id}"', data_manager=self.data_manager)

        self.initiative_bonus = self.get('initiative', 0)


class BattleTeam(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'BATTLE_TEAMS', f'team_id = {self.id}', data_manager=self.data_manager)

        self.battle_id = self.get('battle_id', None)
        self.label = self.get('label', 'Неизвестная команда')
        self.role = TeamRole(self.get('role'), data_manager=self.data_manager) if self.get('role') is not None else TeamRole('Participants', data_manager=self.data_manager)
        self.commander_id = self.get('commander', None)
        self.coordinator_id = self.get('coordinator', None)
        self.command_points = self.get('com_points', 0)
        self.is_active = self.get('round_activity')

    def add_actor(self, actor_id:int, **kwargs) -> None:
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

            actor = Actor(actor_id, data_manager=self.data_manager)
            actor.set_initiative(actor.roll_initiative())

    def count_participants(self) -> int:
        return self.data_manager.get_count('BATTLE_CHARACTERS','character_id',f'team_id = {self.id} AND battle_id = {self.battle_id}')

    def fetch_members(self) -> list[int]:
        if self.data_manager.check('BATTLE_CHARACTERS', f'team_id = {self.id}'):
            return [member.get('character_id') for member in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'team_id = {self.id}')]
        else:
            return []

    def set_label(self, label:str) -> None:
        self.data_manager.update('BATTLE_TEAMS', {'label': label}, f'team_id = {self.id}')
        self.label = label

    def set_role(self, role:str) -> None:
        self.data_manager.update('BATTLE_TEAMS', {'role': role}, f'team_id = {self.id}')
        self.role = TeamRole(role, data_manager=self.data_manager)

    def set_commander(self, target_id:int) -> None:
        self.data_manager.update('BATTLE_TEAMS', {'commander': target_id}, f'team_id = {self.id}')
        self.commander_id = target_id

    def set_coordinator(self, target_id:int) -> None:
        self.data_manager.update('BATTLE_TEAMS', {'coordinator': target_id}, f'team_id = {self.id}')
        self.coordinator_id = target_id

    def set_activity(self, set: bool) -> None:
        if set:
            self.data_manager.update('BATTLE_TEAMS', {'round_active': 1}, f'team_id = {self.id}')

        else:
            self.data_manager.update('BATTLE_TEAMS', {'round_active': 0}, f'team_id = {self.id}')

    def set_com_points(self, com_points:int) -> None:
        self.data_manager.update('BATTLE_TEAMS', {'com_points': com_points}, f'team_id = {self.id}')


class Coordinator(DataModel):
    def __init__(self, team_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.team_id = team_id

        DataModel.__init__(self, 'BATTLE_TEAMS', f'team_id = {self.team_id}', data_manager=self.data_manager)

        self.id = self.get('coordinator', None)
        self.com_points = self.get('com_points')
        self.battle_id = self.get('battle_id')

        self.is_available = True if self.id is not None else False
        self.is_active = self.get('round_active') == 1

    @staticmethod
    def check_status(message_dead=None, title_dead=None, message_inactive=None, title_inactive=None):
        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                is_dead = Body(self.id, data_manager=self.data_manager).is_dead()[0]
                if is_dead:
                    return ResponsePool(Response(False, message_dead if message_dead else 'Вы погибли и не можете совершать действия координатора', title_dead if title_dead else 'Смерть...'))
                if not self.is_active:
                    return ResponsePool(Response(False, message_inactive if message_inactive else 'Вы не можете сейчас совершить тактическое действие', title_inactive if title_inactive else 'Активность координатора'))
                return method(self, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def require_command_points(cost: int, max_value: int = None):
        max_value = max_value if max_value is not None else 1

        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                # Печать значений перед вызовом метода
                print(f"Decorator wrapper called with args: {args}, kwargs: {kwargs}")

                # Извлечение value из kwargs
                value = kwargs.pop('value', 1)  # Извлечение из kwargs и удаление

                if value > max_value:
                    value = max_value

                # Проверка очков командования
                check_command_points = self.check_com_points(cost * value)
                if not check_command_points:
                    return ResponsePool(Response(False,
                                                 '-# У вас недостаточно очков командования для совершения данного тактического действия',
                                                 'Недостаточно очков командования'))

                # Вычисление и использование очков командования
                self.use_com_point(cost * value)

                # Вызов оригинального метода с обновленным kwargs
                if 'value' in kwargs:
                    return method(self, *args, **kwargs, value=value)
                else:
                    return method(self, *args, **kwargs)

            return wrapper

        return decorator

    def make_sound(self, sound_id:str, layer_id:int, volume:int=None) -> None:
        prompt = {'id': self.data_manager.maxValue('BATTLE_SOUNDS','id')+1,
                  'battle_id': self.battle_id,
                  'actor_id': None,
                  'layer_id': layer_id,
                  'sound_id': sound_id,
                  'round': Battlefield(self.battle_id, data_manager=self.data_manager).round,
                  'volume': volume if volume else random.randint(50,150)}

        self.data_manager.insert('BATTLE_SOUNDS', prompt)

    def get_layer_targets(self, layer_id:int, *,enemies_only:bool=False) -> list[int]:
        c_layer = Layer(layer_id, self.battle_id, data_manager=self.data_manager)
        total_units = c_layer.fetch_characters()

        if not enemies_only:
            return total_units
        else:
            total_list = []
            for unit in total_units:
                if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.battle_id} AND character_id = {unit} AND team_id != {self.team_id}'):
                    total_list.append(unit)
                else:
                    continue

            return total_list

    def get_layer_objects(self, layer_id:int) -> list[GameObject]:
        c_layer = Layer(layer_id, self.battle_id, data_manager=self.data_manager)
        total_objects = c_layer.get_objects()

        return total_objects

    def get_layer(self, layer_id:int):
        c_layer = Layer(layer_id, self.battle_id, data_manager=self.data_manager)
        return c_layer

    def layer_objects_get_damage(self, layer_id:int, total_damage:int) -> None:
        c_objects = self.get_layer_objects(layer_id)
        for i in c_objects:
            i.recive_damage(random.randint(min(0, total_damage), max(0, total_damage)))

    def use_com_point(self, com_points:int) -> None:
        self.com_points -= com_points
        self.data_manager.update('BATTLE_TEAMS', {'com_points': self.com_points}, f'team_id = {self.team_id}')

    def check_com_points(self, cost:int) -> bool:
        if self.com_points >= cost:
            return True
        else:
            return False

    def check_activity(self) -> bool:
        if self.is_active:
            return True
        else:
            return False

    def set_activity(self, set: bool) -> None:
        self.is_active = set
        if set:
            self.data_manager.update('BATTLE_TEAMS', {'round_active': 1}, f'team_id = {self.team_id}')
        else:
            self.data_manager.update('BATTLE_TEAMS', {'round_active': 0}, f'team_id = {self.team_id}')

    def team_members_on_layer(self, layer_id:int) -> list[int]:
        members_on_layer = [member.get('character_id') for member in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id} AND layer_id = {layer_id} AND team_id = {self.team_id}')]
        return members_on_layer

    def get_distance_delta(self):
        return Battlefield(self.battle_id, data_manager=self.data_manager).distance_delta

    def get_characters_on_layer(self, layer_id:int):
        return Layer(layer_id, self.battle_id).get_all_characters_on_layer()

    def describe_action(self, action:str, layer_id:int=None):
        return f'-# Вы {action} в обозначенном секторе **{self.battle_id}-{layer_id if layer_id is not None else random.randint(100, 1000)}-{random.randint(10000,99999)}**'

    @check_status()
    @require_command_points(4, 8)
    def artillery_strike(self, layer_id:int, value:int, ammo_id:str):
        print(f"artillery_strike called with: layer_id={layer_id}, value={value}, ammo_id={ammo_id}")
        from ArbAmmo import Grenade

        damage_manager = DamageManager()

        total_targets = self.get_layer_targets(layer_id)

        ammo = Grenade(ammo_id, data_manager=self.data_manager)
        damaged_layers = ammo.get_damaged_layers(self.get_distance_delta(), layer_id)
        for _ in range(value):
            main_target = random.choice(total_targets)
            strike_damage = ammo.detonate()
            main_damage = strike_damage.get('main_damage', [])

            damage_manager.process_damage(main_target, main_damage)
            is_target_dead = ActorDeath(main_target, self.id, data_manager=self.data_manager).check_death()

            fragments_damage = strike_damage.get('fragments_damage', [])
            fragments_value = strike_damage.get('fragments_value', 0)

            for layer in damaged_layers:
                potential_targets = self.get_characters_on_layer(layer)
                if layer_id == layer:
                    potential_targets.append(main_target)
                for _ in range(fragments_value):
                    if random.randint(0, 100) > 50:
                        frag_target = random.choice(potential_targets)
                        frag = random.choice(fragments_damage)
                        damage_manager.process_damage(frag_target, [frag])
                        is_target_dead = ActorDeath(frag_target, self.id, data_manager=self.data_manager).check_death()
                    else:
                        continue

        self.set_activity(False)

        action = f'вызываете артиллерийский огонь в виде **{value}** боеприпассов **{ammo.label}** и вскоре фиксируете поражение указанного квадрата местности'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Артудар'))

        return response

    def CAS(self, layer_id:int):
        pass

    @check_status()
    @require_command_points(2, 20)
    def mine_laying(self, layer_id:int, mine_type:str, value:int):
        from ArbWeapons import TrapInit

        layer = self.get_layer(layer_id)
        layer.add_trap(mine_type, value=value)

        self.set_activity(False)

        action = f'запускаете несколько снарядов, наполненных {value} минами типа {TrapInit(mine_type, data_manager=self.data_manager).label}, которые разываются прямо над полем боя и осыпаются'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Минирование'))

        return response

    @check_status()
    @require_command_points(10, 5)
    def reinforcement(self, layer_id:int, value:int):

        battle = Battlefield(self.battle_id, data_manager=self.data_manager)
        units = battle.spawn_units(value=value, layer_id=layer_id, team_id=self.team_id)

        self.set_activity(False)

        action = f'отправляете на поле боя летательный аппарат с подкреплением в количестве {value} человек, которые высаживаются'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Подкрепление'))

        return response

    @check_status()
    @require_command_points(15)
    def emergency_evacuation(self, layer_id:int):
        members_on_layer = self.team_members_on_layer(layer_id)

        for member in members_on_layer:
            self.data_manager.delete('BATTLE_CHARACTERS', filter=f'character_id = {member}')

        self.set_activity(False)

        action = f'отправляете транспорт и в срочном порядке эвакуируете ваших бойцов в количестве {len(members_on_layer)} человек'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Срочная эвакуация'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_ammo(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('AmmoCrate', value=value)

        self.set_activity(False)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("AmmoCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Патроны'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_grenades(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('GrenadeCrate', value=value)

        self.set_activity(False)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("GrenadeCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Взрывчатка'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_firstaid(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('MedCrate', value=value)

        self.set_activity(False)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("MedCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Медицинская помощь'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_repair(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('RepairCrate', value=value)

        self.set_activity(False)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("RepairCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Инструменты'))

        return response






class BattleType(ABC):
    def __init__(self, battle: 'Battlefield'):
        self.battle = battle

    def is_last_round(self):
        return self.battle.last_round == self.battle.round

    def get_condition_value(self):
        return self.battle.type_value

    def only_one_team(self):
        actors = self.battle.fetch_actors()
        teams = []

        for actor in actors:
            team_id = Actor(actor, data_manager=self.battle.data_manager)
            if team_id not in teams:
                teams.append(team_id)

        if len(teams) > 1:
            return False

        else:
            return teams[0]

    @abstractmethod
    def check_final_condition(self):
        pass


class OverkillBattle(BattleType):

    def check_final_condition(self):
        only_one_team = self.only_one_team()
        if only_one_team:
            return only_one_team
        elif only_one_team is None:
            return None
        else:
            return False


class CaptureBattle(BattleType):
    def captured_objects(self):
        objects = self.battle.data_manager.select_dict('BATTLE_OBJECTS', f'battle_id = {self.battle.battle_id} AND captured is not NULL')
        return [obj.get('object_id') for obj in objects]

    def check_final_condition(self):
        captured_objects = self.captured_objects()
        if not captured_objects:
            return None

        captured_teams = []
        for object_id in captured_objects:
            team = GameObject(object_id, data_manager=self.battle.data_manager).captured
            captured_teams.append(team)

        team_list = list(set(captured_teams))
        teams_captures = {}

        for team in team_list:
            teams_captures[team] = captured_teams.count(team)

        max_captures = 0
        final_condition = None
        for team in teams_captures:
            if teams_captures[team] > max_captures:
                max_captures = teams_captures[team]
                final_condition = team

        return final_condition


class TransitionBattle(BattleType):
    def check_final_condition(self):
        transiting_team = self.get_condition_value()
        if transiting_team is None:
            return None

        available_team_characters = [member.get('character_id') for member in self.battle.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle.battle_id} AND team_id = {transiting_team}')]
        final_layer = max(list(self.battle.get_layers().keys()))

        team_characters_layers = []
        for member in available_team_characters:
            layer = self.battle.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {member}')[0].get('layer_id')
            team_characters_layers.append(layer)

        if len(team_characters_layers) > 1:
            return None

        if team_characters_layers[0] != final_layer:
            return None

        return transiting_team







class BattleLogger:
    @staticmethod
    def log_event(data_manager: DataManager, battle_id: int, event_type: str, actor_id: int = None, event_description: str = '', target_id: int = None):
        event_id = data_manager.maxValue('BATTLE_EVENTS', 'event_id') + 1
        round = Battlefield(battle_id, data_manager=data_manager).round

        query = {
            'event_id': event_id,
            'battle_id': battle_id,
            'timestamp': datetime.datetime.now(),
            'round': round,
            'actor': actor_id,
            'target': target_id,
            'event': event_type,
            'desc': event_description
        }

        data_manager.insert('BATTLE_EVENTS', query)

        return BattleLog(event_id, data_manager=data_manager)


class BattleLog(DataModel):
    def __init__(self, log_id: int, **kwargs):
        self.log_id = log_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'BATTLE_EVENTS', f'event_id = {self.log_id}', data_manager=self.data_manager)
        self.battle_id = self.get('battle_id', None)
        self.round = self.get('round', None)
        self.actor = self.get('actor', None)
        self.event_type = self.get('event', None)
        self.target = self.get('target', None)
        self.description = self.get('desc', '')
        self.timestamp = self.get('timestamp', None)




class Layer(DataModel):
    def __init__(self, id:int, battle_id:int, **kwargs):
        self.id = id
        self.battle_id = battle_id
        self.data_manager = kwargs.get('data_manager',DataManager())

        DataModel.__init__(self, 'BATTLE_LAYERS', f'id = {self.id} and battle_id = {self.battle_id}', data_manager=self.data_manager)

        self.label = self.get('label','Неизвестная местность')
        self.terrain = Terrain(self.get('terrain_type','Field'), data_manager=self.data_manager)
        self.height = self.get('height', 0) if self.get('height', 0) is not None else 0

    def get_objects(self):
        return [GameObject(i.get('object_id'), layer_id=self.id, battle_id=self.battle_id, data_manager=self.data_manager) for i in self.data_manager.select_dict('BATTLE_OBJECTS', filter=f'layer_id = {self.id} AND battle_id = {self.battle_id}')]

    def get_traps(self):
        from ArbWeapons import Trap
        traps_list = []
        if self.data_manager.check('BATTLE_TRAPS', f'battle_id = {self.battle_id} AND layer_id = {self.id}'):
            for trap in self.data_manager.select_dict('BATTLE_TRAPS',
                                                      filter=f'battle_id = {self.battle_id} AND layer_id = {self.id}'):
                traps_list.append(Trap(trap.get('trap_id'), data_manager=self.data_manager))

        return traps_list

    def get_height(self):
        return self.height + self.terrain.height

    def fetch_characters(self):
        if not self.data_manager.check('BATTLE_CHARACTERS', f'layer_id = {self.id} AND battle_id = {self.battle_id}'):
            return []
        else:
            return [charc.get('character_id') for charc in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'layer_id = {self.id} AND battle_id = {self.battle_id}')]

    def characters_not_in_cover(self):
        characters = self.fetch_characters()
        total_list = []
        for char in characters:
            if DataDict('BATTLE_CHARACTERS', f'character_id = {char}', data_manager=self.data_manager).get('object', None) is None:
                total_list.append(char)
            else:
                continue

        return total_list

    def get_all_characters_on_layer(self):
        if not self.data_manager.check('BATTLE_CHARACTERS', f'layer_id = {self.id} AND battle_id = {self.battle_id}'):
            return []
        else:
            return [charc.get('character_id') for charc in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'layer_id = {self.id} AND battle_id = {self.battle_id}')]

    def add_object(self, object_type:str, endurance:int=None, captured:int=None, value:int=None, uses:int=None):
        value = value if value is not None and value > 0 else 1
        object_id = self.data_manager.maxValue('BATTLE_OBJECTS', 'object_id')

        for i in range(value):
            object_id += 1
            prompt = {'battle_id': self.battle_id,
                      'layer_id': self.id,
                      'object_id': object_id,
                      'object_type': object_type,
                      'endurance': endurance if endurance else ObjectType(object_type, data_manager=self.data_manager).max_endurance,
                      'captured': captured,
                      'uses': uses if uses is not None else 0}

            self.data_manager.insert('BATTLE_OBJECTS', prompt)

    def delete_object(self, object_id:int):
        self.data_manager.delete('BATTLE_OBJECTS', f'object_id = {object_id}')

    def add_trap(self, trap_type:str, buff:int=None, value:int=None):
        value = value if value is not None and value > 0 else 1
        buff = buff if buff is not None else 0
        trap_id = self.data_manager.maxValue('BATTLE_TRAPS', 'trap_id') + 1

        for i in range(value):
            trap_id += 1

            prompt = {
                'battle_id': self.battle_id,
                'layer_id': self.id,
                'trap_id': trap_id,
                'type': trap_type,
                'buff': buff
            }
            self.data_manager.insert('BATTLE_TRAPS', prompt)

    def edit_trap(self, trap_id:int, trap_type:str=None, trap_buff:int=None):
        from ArbWeapons import Trap

        prompt = {
            'type': trap_type if trap_type else Trap(trap_id, data_manager=self.data_manager).trap_type,
            'buff': trap_buff if trap_buff else Trap(trap_id, data_manager=self.data_manager).buff
        }

        self.data_manager.update('BATTLE_TRAPS', prompt, f'trap_id = {trap_id}')

    def delete_trap(self, trap_id:int):
        self.data_manager.delete('BATTLE_TRAPS', f'trap_id = {trap_id}')

    def set_label(self, label:str):
        self.label = label
        self.data_manager.update('BATTLE_LAYERS', {'label': label}, f'id = {self.id} AND battle_id = {self.battle_id}')

    def set_terrain(self, terrain:str):
        self.data_manager.update('BATTLE_LAYERS', {'terrain_type': terrain}, f'id = {self.id} AND battle_id = {self.battle_id}')
        self.terrain = Terrain(terrain, data_manager=self.data_manager)

    def set_height(self, height: int):
        self.height = height
        self.data_manager.update('BATTLE_LAYERS', {'height': height}, f'id = {self.id} AND battle_id = {self.battle_id}')

    def generate_objects(self, value:int=random.randint(3, 20)):
        from ArbGenerator import GenerateObject, GenerateLayer

        generated_objects: list[GenerateObject] = GenerateLayer(self.id, self.battle_id, self.terrain.id, self.height, data_manager=self.data_manager, object_value=value).objects
        for object in generated_objects:
            object.inset_data()

        return generated_objects

    def string_layer(self):
        objects = self.get_objects()
        general_description = f'{self.terrain.desc}'
        objects_description = f'Вы видите '
        if objects:
            objects_description += f', '.join(f'**{obj.object_type.label.lower()} ||( {obj.id} )||**' for obj in objects)
        else:
            objects_description += 'что здесь нет потенциальных укрытий и полезных объектов.'

        return f'-# {general_description}. {objects_description}'


class Battlefield(DataModel):
    def __init__(self, battle_id:int, **kwargs):
        self.battle_id = battle_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'BATTLE_INIT', f'id = {self.battle_id}', data_manager=self.data_manager)
        self.label = self.get('label', 'Неизвестное поле боя')
        self.distance_delta = self.get('distance_delta', 0)
        self.description = self.get('desc', '')
        self.time = DayTime(self.get('time_type'), data_manager=self.data_manager) if self.get('time_type') else DayTime('Day', data_manager=self.data_manager)
        self.weather = Weather(self.get('weather_type'), data_manager=self.data_manager) if self.get('weather_type') else Weather('Sunny', data_manager=self.data_manager)

        self.round = self.get('round', 1) if self.get('round', 1) is not None else 1
        self.key_round_delay = self.get('key_round', 3) if self.get('key_round', 0) is not None else 3
        self.last_round = self.get('last_round', None) if self.get('last_round', 1) is not None else None

        self.battle_type = self.get('battle_type', 'Overkill') if self.get('battle_type', 'Overkill') else 'Overkill'
        self.type_value = self.get('type_value', None)

    def get_layers(self) -> dict[int, Layer]:
        if not self.data_manager.check('BATTLE_LAYERS', f'battle_id = {self.battle_id}'):
            return {}

        layers = self.data_manager.select_dict('BATTLE_LAYERS', filter=f'battle_id = {self.battle_id}')
        layers_dict = {}
        for layer in layers:
            layers_dict[layer.get('id')] = Layer(layer.get('id'), self.battle_id, data_manager=self.data_manager)

        return layers_dict

    def fetch_teams(self) -> list[int]:
        if self.data_manager.check('BATTLE_TEAMS', f'battle_id = {self.battle_id}'):
            teams = self.data_manager.select_dict('BATTLE_TEAMS', filter=f'battle_id = {self.battle_id}')
            return [team.get('team_id') for team in teams]
        else:
            return []

    def fetch_actors(self) -> list[int]:
        if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.battle_id}') is None:
            return []
        else:
            return [c.get('character_id') for c in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id}')]

    def add_actor(self, actor_id: int, **kwargs) -> None:
        if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {actor_id}'):
            prompt = {'battle_id': self.battle_id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative', random.randint(1, 100)),
                      'is_active': None,
                      'height': 0}

            self.data_manager.update('BATTLE_CHARACTERS', prompt, f'character_id = {actor_id}')
        else:
            prompt = {'battle_id': self.battle_id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative', random.randint(1, 100)),
                      'is_active': None,
                      'height': 0}
            self.data_manager.insert('BATTLE_CHARACTERS', prompt)

    def calculate_size(self) -> float:
        layers = self.get_layers()
        min_layer = min(layers.keys())
        max_layer = max(layers.keys())

        return (max_layer - min_layer) * self.distance_delta

    def max_initiative_actor(self) -> int:
        c_list = self.fetch_actors()
        c_actor = None
        max_initiative = 0
        for act in c_list:
            actor = Actor(act, data_manager=self.data_manager)
            if actor.initiative > max_initiative and actor.is_active is None:
                max_initiative = actor.initiative
                c_actor = act

        return c_actor

    def turn_order(self) -> list[int]:
        c_list = self.fetch_actors()
        sorted_actors = sorted(c_list, key=lambda actor: Actor(actor, data_manager=self.data_manager).initiative, reverse=True)
        return [actor for actor in sorted_actors]

    def current_turn_index(self) -> int:
        for index, actor in enumerate(self.turn_order()):
            if Actor(actor, data_manager=self.data_manager).is_active:
                return index
        else:
            return 0

    def actor_turn_index(self, actor_id: int) -> int | None:
        for index, actor in enumerate(self.turn_order()):
            if actor == actor_id:
                return index
        return None

    def delete_actor(self, actor_id: int) -> None:
        self.unable_actor(actor_id)
        self.data_manager.delete('BATTLE_DEAD', f'character_id = {actor_id} and battle_id = {self.battle_id}')

    def unable_actor(self, actor_id: int) -> None:
        self.data_manager.delete('BATTLE_CHARACTERS', f'character_id = {actor_id} and battle_id = {self.battle_id}')

    def dead_actor(self, actor_id: int, killer_id: int = None) -> None:
        actor = Actor(actor_id, data_manager=self.data_manager)

        prompt = {
            'battle_id': self.battle_id,
            'character_id': actor_id,
            'layer_id': actor.layer_id,
            'killer': killer_id,
            'team_id': actor.team_id
        }

        self.data_manager.insert('BATTLE_DEAD', prompt)
        self.unable_actor(actor_id)

    def next_round(self):
        # conds = self.check_condition()
        #
        # if conds.status:
        #     # здесь завершается бой
        #
        #     winner_team = conds.victory_team
        #     if winner_team:
        #         team = BattleTeam(conds.victory_team, self.id)
        #     else:
        #         team = None
        #
        #     if winner_team:
        #         self.winner_exp_gift(1000, winner_team)
        #
        #     self.delete_battle()
        #
        #     return conds, team

        self.round += 1
        self.data_manager.update('BATTLE_INIT', {'round': self.round}, f'id = {self.battle_id}')

        for act in self.fetch_actors():
            actor = Actor(act, data_manager=self.data_manager)
            if self.round % self.key_round_delay == 0:
                new_initiative = actor.roll_initiative()
                actor.set_initiative(new_initiative)
            ActionPoints.character_ap(act, data_manager=self.data_manager).new_round_ap()
            actor.set_active(None)

        teams = self.fetch_teams()

        if teams:
            for team in teams:
                BattleTeam(team, data_manager=self.data_manager).set_activity(True)

        BattleLogger.log_event(self.data_manager, self.battle_id, 'NewCycle', event_description=f'Начинается {self.round} раунд!')

        return False

    def next_actor(self) -> tuple[int | None, int | None]:
        if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.battle_id} AND is_active = 1'):
            active_actor = self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id} AND is_active = 1')[0].get('character_id')
            Actor(active_actor, data_manager=self.data_manager).set_active(False)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'EndTurn', event_description=f'Персонаж {active_actor} завершает свой ход!')

        if self.max_initiative_actor() is not None:
            n_actor = self.max_initiative_actor()
            Actor(n_actor, data_manager=self.data_manager).set_active(True)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'NewTurn', actor_id=n_actor, event_description=f'Персонаж {n_actor} начинает свой ход!')

            return n_actor, None
        else:
            is_last_round = self.next_round()
            if is_last_round:
                return None, is_last_round

            n_actor = self.max_initiative_actor()
            Actor(n_actor, data_manager=self.data_manager).set_active(True)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'NewTurn', actor_id=n_actor, event_description=f'Персонаж {n_actor} начинает свой ход!')

            return n_actor, self.round

    def is_last_actor(self, actor_id: int) -> bool:
        order_list = self.turn_order()
        if actor_id == order_list[-1]:
            return True
        else:
            return False

    def winner_exp_gift(self, exp: int, team_id: int = None, actors_list: list = None):
        from ArbCharacters import Character

        winner_team = team_id
        actors = actors_list

        if winner_team:
            members = BattleTeam(team_id, self.id, data_manager=self.data_manager).fetch_members()
            for member in members:
                Character(member, data_manager=self.data_manager).add_exp(exp)

        if actors:
            for member in actors:
                Character(member, data_manager=self.data_manager).add_exp(exp)

    def create_team(self, label: str, role: str = None) -> BattleTeam:
        if not self.data_manager.check('BATTLE_TEAMS', 'battle_id'):
            c_id = 0
        else:
            c_id = self.data_manager.maxValue('BATTLE_TEAMS', 'team_id', f'battle_id = {self.battle_id}') + 1

        query = {'battle_id': self.battle_id,
                 'team_id': c_id,
                 'label': label,
                 'role': role}

        self.data_manager.insert('BATTLE_TEAMS', query)

        return BattleTeam(c_id, data_manager=self.data_manager)

    def describe_teams(self) -> str:
        total_text = f''
        if not self.fetch_teams():
            return f'*(В данной битве нет организованных сторон)*'

        teams = self.fetch_teams()
        for team_id in teams:
            team = BattleTeam(team_id, data_manager=self.data_manager)
            counted = team.count_participants()
            total_text += f'\n- ``[id {team.id}]`` **{team.label}** — *{round(counted * 0.5)}-{round(counted * 2)} чел.*'
        return total_text

    def describe(self) -> tuple[str, str]:
        name = f'{self.label}' if self.label else f'Сражение {self.battle_id}'
        total_text = f'''
    *Внешние условия:* ***{self.time.label}. {self.weather.label}***
    *Масштаб:* ***{self.calculate_size()}м. ``(ср. {self.distance_delta}м.)``***

    > *— "{self.description}"*

    - **Текущий раунд:** {self.round} ``(сброс инициативы каждые {self.key_round_delay})``
    - **Текущий ход:** {self.current_turn_index() + 1} из {len(self.turn_order())}
    '''
        return name, total_text

    def spawn_units(self, value: int = 1, min_danger:int=0, max_danger:int=0, **kwargs) -> list[int]:
        from ArbGenerator import GenerateCharacter, BaseCfg

        layers = self.get_layers()
        race_id = kwargs.get('race', 'Human')
        org_id = kwargs.get('org_id', None)

        battle_team_id = kwargs.get('team_id', None)

        layer_id = kwargs.get('layer_id', None)
        if layer_id not in layers.keys():
            layer_id = random.choice(list(layers.keys()))

        value = value if value is not None and value > 0 else 1

        new_units = []

        for i in range(value):
            danger = random.randint(min_danger, max_danger)
            base_cfg = BaseCfg(data_manager=self.data_manager,
                               race=race_id,
                               org=org_id)

            new_unit = GenerateCharacter(danger=danger, basicCfg=base_cfg, data_manager=self.data_manager).insert_data()
            new_units.append(new_unit)

        if battle_team_id is not None:
            if not self.data_manager.check('BATTLE_TEAMS', f'team_id = {battle_team_id}'):
                team = self.create_team('Участники битвы', 'Participants').id
            else:
                team = BattleTeam(battle_team_id, data_manager=self.data_manager).id

        else:
            team = None

        for i in new_units:
            self.add_actor(i, team_id=team, layer=layer_id)

        return new_units

    def delete_battle(self) -> None:
        battle_tables = self.data_manager.get_tables_with_prefix('BATTLE_')
        for i in battle_tables:
            if 'battle_id' in self.data_manager.get_all_columns(i):
                self.data_manager.delete(i, f'battle_id = {self.battle_id}')
        self.data_manager.delete('BATTLE_INIT', filter=f'id = {self.battle_id}')

    def update_battle(self, **kwargs) -> None:

        label = kwargs.get('label', self.label)
        distance_delta = kwargs.get('distance', self.distance_delta)
        desc = kwargs.get('desc', self.description)
        time_type = kwargs.get('time', self.time.id)
        weather_type = kwargs.get('weather', self.weather.id)
        round = kwargs.get('round', self.round)
        key_round = kwargs.get('key_round', self.key_round_delay)

        last_round = kwargs.get('last_round', self.last_round)
        battle_type = kwargs.get('battle_type', self.battle_type)
        type_value = kwargs.get('type_value', self.type_value)

        prompt = {
            'label': label,
            'distance_delta': distance_delta,
            'desc': desc,
            'time_type': time_type,
            'weather_type': weather_type,
            'round': round,
            'key_round': key_round,
            'last_round': last_round,
            'battle_type': battle_type,
            'type_value': type_value
        }

        self.data_manager.update('BATTLE_INIT', prompt, f'id = {self.battle_id}')

    def add_layer(self, **kwargs) -> Layer:
        layers = self.get_layers()
        max_layer_id = max(layers.keys()) + 1

        prompt = {
            'battle_id': self.battle_id,
            'id': max_layer_id,
            'label': kwargs.get('label', 'Неизвестная местность'),
            'terrain_type': kwargs.get('terrain_type', 'Field'),
            'height': kwargs.get('height', layers[max_layer_id - 1].height + random.randint(-5, 5))

        }

        self.data_manager.insert('BATTLE_LAYERS', prompt)
        new_layer = Layer(max_layer_id, self.battle_id, data_manager=self.data_manager)

        return new_layer

    def delete_layer(self, layer_id: int) -> None:
        self.data_manager.delete('BATTLE_LAYERS', f'id = {layer_id} AND battle_id = {self.battle_id}')
        self.data_manager.delete('BATTLE_OBJECTS', f'battle_id = {self.battle_id} AND layer_id = {layer_id}')

        def is_any_element_greater_than(numbers, threshold):
            return any(number > threshold for number in numbers)

        layers = self.get_layers()

        if is_any_element_greater_than(layers.keys(), layer_id):
            refresh_list = [i['id'] for i in self.data_manager.select_dict('BATTLE_LAYERS', filter=f'battle_id = {self.battle_id} AND id > {layer_id}')]
            current_id = refresh_list[0] - 1
            for i in refresh_list:
                self.data_manager.update('BATTLE_LAYERS', {'id': current_id}, f'battle_id = {self.battle_id} AND id = {i}')
                self.data_manager.update('BATTLE_OBJECTS', {'layer_id': current_id},
                                         f'battle_id = {self.battle_id} AND layer_id = {i}')
                current_id += 1

    def add_sound(self, sound_type: str, actor_id: int = None, layer_id: int = None, volume: int = None):
        c_id = self.data_manager.maxValue('BATTLE_SOUNDS', 'id') + 1
        prompt = {'id': c_id,
                  'battle_id': self.battle_id,
                  'actor_id': actor_id if actor_id else None,
                  'layer_id': layer_id if layer_id is not None else 0,
                  'sound_id': sound_type,
                  'volume': volume if volume is not None else random.randint(50, 150)}

        self.data_manager.insert('BATTLE_SOUNDS', prompt)

        return InBattleSound(c_id, data_manager=self.data_manager)

    def delete_sound(self, sound_id: int):
        return InBattleSound(sound_id, data_manager=self.data_manager).delete()

    def edit_sound(self, sound_id: int, actor_id: int = None, sound_type: str = None, layer_id: int = None, round: int = None, volume: int = None):
        sound = InBattleSound(sound_id, data_manager=self.data_manager)

        prompt = {'actor_id': actor_id,
                  'sound_id': sound_type if sound_type else sound.sound_type,
                  'layer_id': layer_id if layer_id is not None else sound.layer_id,
                  'volume': volume if volume is not None else sound.volume}

        self.data_manager.update('BATTLE_SOUNDS', prompt, f'id = {sound_id}')

        return sound





class DamageManager:
    def __init__(self, data_manager: DataManager = None):
        self.data_manager = data_manager if data_manager else DataManager()

    def target_random_element(self, target_id:int, *, body_group:str = None) -> BodyElement:
        target_body = Body(target_id, data_manager=self.data_manager)
        body_group = body_group if body_group is not None else random.choice(target_body.all_bodyparts_groups())
        print(body_group)
        return target_body.choose_random_element_from_group(body_group)

    def get_target_armor(self, target_id:int):
        from ArbClothes import CharacterArmor
        return CharacterArmor(target_id, data_manager=self.data_manager)

    def apply_damage(self, element_damage_pair: tuple[BodyElement, Damage]) -> None:
        element, damage = element_damage_pair

        if element.calculate_health() == 0:
            return

        element.apply_damage(damage, True)

    def process_damage(self, target_id:int, shots: list[Damage]) -> str:
        damage_list = shots
        total_damage = []

        current_element: BodyElement = self.target_random_element(target_id)
        armor = self.get_target_armor(target_id)

        for damage in damage_list:

            n_damage = armor.ballistic_simulation(current_element.body_parts_group, damage)
            if n_damage:
                e_d_pair = (current_element, n_damage)
                total_damage.append(e_d_pair)

        for pair in total_damage:
            self.apply_damage(pair)

        text = ''
        for pair in total_damage:
            text += f'- {pair[1].__str__()} по {pair[0].label}\n'

        return text


class Attack(ABC):
    @abstractmethod
    def attack(self, target_id: int) -> Response:
        pass


class RangeAttack(Attack):
    def __init__(self, attacker: 'Actor', weapon_id:int, **kwargs):
        self.attacker = attacker
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.weapon_id = weapon_id

    def get_weapon(self):
        from ArbWeapons import Weapon
        return Weapon(self.weapon_id, data_manager=self.data_manager)

    def check_skill(self, skill: str, difficulty: int = None):
        return self.attacker.check_skill(skill, difficulty)

    def get_enemy_cover(self, target_id: int):
        data = DataDict('BATTLE_CHARACTERS', f'character_id = {target_id}', data_manager=self.data_manager)
        return data.get('object_id', None)

    def attack(self, target_id: int) -> Response:
        damage_manager = DamageManager()
        weapon = self.get_weapon()
        bullets = weapon.can_shoot()
        if not bullets:
            return Response(False, 'У вашего оружия нет боезапаса или оно не предназначено для стрельбы.', 'Стрельба невозможна')

        damage_list = []

        enemy_cover_id = self.get_enemy_cover(target_id)
        enemy_cover = GameObject(enemy_cover_id, data_manager=self.data_manager).current_protection if enemy_cover_id else 0
        distance_to_enemy = self.attacker.calculate_total_distance(target_id)

        shot_difficulty = weapon.shot_difficulty(distance_to_enemy, enemy_cover)

        shots = min(weapon.attacks, bullets)

        weapon.use_bullet(shots)

        for _ in range(shots):
            self.attacker.make_sound('GunShot', weapon.shot_noise())

            print('attacker', self.attacker.actor_id)
            roll = self.check_skill(weapon.weapon_class, shot_difficulty)
            if not roll[0]:
                continue

            raw_damage = weapon.fire()
            n_damage = damage_manager.process_damage(target_id, raw_damage)

            if not n_damage:
                continue

            damage_list.append(n_damage)

        total_response = '\n'.join(f'{response}' for response in damage_list)
        is_target_dead = ActorDeath(target_id, self.attacker.actor_id, reason=f'Застрелен из {weapon.label}',data_manager=self.data_manager).check_death()

        return Response(True, f'```{total_response}```', 'Попадания') if total_response else Response(False, f'', 'Попадания')


class MeleeAttack(Attack):
    def __init__(self, attacker: 'Actor', weapon_id:int, **kwargs):
        self.attacker = attacker
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.weapon_id = weapon_id

    def get_weapon(self):
        from ArbWeapons import Weapon
        return Weapon(self.weapon_id, data_manager=self.data_manager)

    def check_skill(self, skill: str, difficulty: int = None):
        return self.attacker.check_skill(skill, difficulty)

    def check_enemy_skill(self, target_id:int, skill: str, difficulty: int = None):
        return Actor(target_id, data_manager=self.data_manager).check_skill(skill, difficulty)

    def compare_skills(self, target_id: int):
        target_skill = self.check_enemy_skill(target_id, 'MartialArms')
        return self.check_skill('ColdSteel', target_skill[1].result)

    def attack(self, target_id: int) -> Response:
        damage_manager = DamageManager()
        weapon = self.get_weapon()
        damage_list = []

        melee_attacks = weapon.melee_attacks
        if not melee_attacks:
            return Response(False, 'У вас нет оружия для атак в ближнем бою!', 'Атака в ближнем бою невозможна')

        for _ in range(melee_attacks):
            self.attacker.make_sound('Fight', weapon.melee_noise())

            roll = self.compare_skills(target_id)
            if not roll[0]:
                continue

            raw_damage = weapon.melee_attack()
            n_damage = damage_manager.process_damage(target_id, raw_damage)

            if not n_damage:
                continue

            damage_list.append(n_damage)

        is_target_dead = ActorDeath(target_id, self.attacker.actor_id, reason=f'Забит досмерти {weapon.label}', data_manager=self.data_manager).check_death()
        total_response = '\n'.join(f'- {response}' for response in damage_list)

        return Response(True, f'```{total_response}```', 'Результат атаки') if total_response else Response(False, f'', 'Результат атаки')


class ThrowGrenade(Attack):
    def __init__(self, attacker: 'Actor', grenade_id: int, **kwargs):
        self.attacker = attacker
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.grenade_id = grenade_id

    def get_grenade(self):
        from ArbWeapons import HandGrenade
        return HandGrenade(self.grenade_id, data_manager=self.data_manager)

    def get_enemy_cover(self, target_id: int):
        data = DataDict('BATTLE_CHARACTERS', f'character_id = {target_id}', data_manager=self.data_manager)
        return data.get('object_id', None)

    def get_enemy_layer(self, target_id: int):
        data = DataDict('BATTLE_CHARACTERS', f'character_id = {target_id}', data_manager=self.data_manager)
        return data.get('layer_id', None)

    def get_characters_without_cover(self, layer_id: int):
        return Layer(layer_id, self.attacker.battle_id, data_manager=self.data_manager).characters_not_in_cover()

    def distance_delta(self):
        return self.attacker.get_battle().distance_delta

    def attack(self, target_id: int) -> Response:
        damage_manager = DamageManager()
        grenade = self.get_grenade()

        # enemy_cover_id = self.get_enemy_cover(target_id)
        # enemy_cover = GameObject(enemy_cover_id, data_manager=self.data_manager).current_protection if enemy_cover_id else 0

        total_damage = []

        damaged_layers = grenade.get_damaged_layers(self.distance_delta(), self.get_enemy_layer(target_id))
        damage_dict = grenade.detonate()
        grenade.delete_item()
        self.attacker.make_sound('Explosion', 100)

        main_damage = damage_dict.get('main_damage', [])

        main_target_damage = damage_manager.process_damage(target_id, main_damage)
        is_target_dead = ActorDeath(target_id, self.attacker.actor_id, reason=f'Взорван {grenade.label}', data_manager=self.data_manager).check_death()

        fragments_damage = damage_dict.get('fragments_damage', [])
        fragments_value = damage_dict.get('fragments_value', 0)

        for layer in damaged_layers:
            potential_targets = self.get_characters_without_cover(layer)
            if self.get_enemy_layer(target_id) == layer:
                potential_targets.append(target_id)
            for _ in range(fragments_value):
                if random.randint(0, 100) > 50:
                    frag_target = random.choice(potential_targets)
                    frag = random.choice(fragments_damage)
                    frag_damage = damage_manager.process_damage(frag_target, [frag])

                    ActorDeath(frag_target, self.attacker.actor_id, reason=f'Погиб от осколков {grenade.label}',data_manager=self.data_manager).check_death()

                    total_damage.append(frag_damage)
                else:
                    continue

        total_damage.append(main_target_damage)

        total_response = '\n'.join(f'- {response}' for response in total_damage)

        return Response(True, f'```{total_response}```', 'Метание гранаты') if total_response else Response(False, f'', 'Метание гранаты')


class BodyPartAttack(Attack):
    def __init__(self, attacker: 'Actor', attack_id: str, **kwargs):
        self.attacker = attacker
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.attack_id = attack_id

    def get_attack(self):
        from ArbWeapons import RaceAttack
        return RaceAttack(self.attack_id, data_manager=self.data_manager)

    def check_skill(self, skill: str, difficulty: int = None):
        return self.attacker.check_skill(skill, difficulty)

    def check_enemy_skill(self, target_id:int, skill: str, difficulty: int = None):
        return Actor(target_id, data_manager=self.data_manager).check_skill(skill, difficulty)

    def compare_skills(self, target_id: int):
        target_skill = self.check_enemy_skill(target_id, 'MartialArms')
        return self.check_skill('MartialArms', target_skill[1].result)

    def get_enemy_cover(self, target_id: int):
        data = DataDict('BATTLE_CHARACTERS', f'character_id = {target_id}', data_manager=self.data_manager)
        return data.get('object_id', None)

    def attack(self, target_id: int) -> Response:
        damage_manager = DamageManager()
        attack = self.get_attack()

        damage_list = []

        attacks = attack.attacks

        if attack.range > 0:
            enemy_cover_id = self.get_enemy_cover(target_id)
            enemy_cover = GameObject(enemy_cover_id, data_manager=self.data_manager).current_protection if enemy_cover_id else 0
            distance_to_enemy = self.attacker.calculate_total_distance(target_id)

            shot_difficulty = attack.attack_difficulty(distance_to_enemy, enemy_cover)

            for _ in range(attacks):
                self.attacker.make_sound('GunShot', random.randint(50, 150))
                roll = self.check_skill('MartialArms', shot_difficulty)
                print(roll)
                if not roll[0]:
                    continue

                raw_damage = attack.attack()
                n_damage = damage_manager.process_damage(target_id, raw_damage)

                if not n_damage:
                    continue

                damage_list.append(n_damage)

        else:
            for _ in range(attacks):
                self.attacker.make_sound('Fight', random.randint(50, 150))
                roll = self.compare_skills(target_id)
                if not roll[0]:
                    continue

                raw_damage = attack.attack()
                n_damage = damage_manager.process_damage(target_id, raw_damage)

                if not n_damage:
                    continue

                damage_list.append(n_damage)

        is_target_dead = ActorDeath(target_id, self.attacker.actor_id, reason=f'Погиб от {attack.label}',data_manager=self.data_manager).check_death()
        total_response = '\n'.join(f'{response}' for response in damage_list)

        return Response(True, f'```{total_response}```', 'Результат атаки') if total_response else Response(False, f'', 'Результат атаки')





class ActorSounds:
    def __init__(self, actor: 'Actor'):
        self.actor = actor
        self.data_manager = actor.data_manager

    def get_all_current_sounds(self) -> list:
        if self.data_manager.check('BATTLE_SOUNDS', f'battle_id = {self.actor.battle_id}'):
            return [sound.get('id') for sound in self.data_manager.select_dict('BATTLE_SOUNDS', filter=f'battle_id = {self.actor.battle_id}')]
        else:
            return []

    def detection_chance(self, sound_id:int) -> int:
        distance_delta = self.actor.get_battle().distance_delta

        sound = InBattleSound(sound_id, data_manager=self.data_manager)
        total_distance = (self.actor.layer_id - sound.layer_id) * distance_delta
        detection_chance = sound.get_detection_chance(total_distance)

        return detection_chance

    def check_sound_availability(self, sound_id:int) -> bool:
        sound = InBattleSound(sound_id, data_manager=self.data_manager)
        if sound.volume <= 0:
            return False
        elif self.detection_chance(sound_id) <= 0:
            return False
        elif sound.sound_id == 'Radio':
            return False
        elif sound.actor_id == self.actor.actor_id:
            return False
        else:
            return True

    def string_sounds(self) -> list[str]:
        sounds = [sound for sound in self.get_all_current_sounds() if self.check_sound_availability(sound)]
        total_text = []

        if not sounds:
            total_text.append(f'-# *(Здесь будут отображаться звуки боя доступные для обнаружения)*')

        for sound in sounds:
            sound_obj = InBattleSound(sound, data_manager=self.data_manager)
            sound_text = f'''
**{sound_obj.label}** ||**( ID: {sound_obj.id} )**||
- *Шанс обнаружения источника: **{self.detection_chance(sound_obj.id):.2f}%***
-# > — "{sound_obj.content if sound_obj.content else sound_obj.description}"
'''
            total_text.append(f'{sound_text}\n')

        return total_text

    def make_sound(self, sound_id:str, volume:int=None, content:str=None) -> None:
        idx = self.data_manager.maxValue('BATTLE_SOUNDS', 'id') + 1

        query = {
            'id': idx,
            'battle_id': self.actor.battle_id,
            'actor_id': self.actor.actor_id,
            'sound_id': sound_id,
            'layer_id': self.actor.layer_id,
            'volume': volume if volume else random.randint(10, 200),
            'content': content
        }

        self.data_manager.insert('BATTLE_SOUNDS', query)

    def get_natural_noise(self) -> float:
        battle = self.actor.get_battle()
        time_noise = battle.time.noise
        weather_noise = battle.weather.noise

        total_penalty = time_noise + weather_noise
        recon = self.get_recon()
        if not recon:
            return total_penalty
        else:
            total_penalty = total_penalty * (100 - recon) if 100 - recon > 0 else 0
            return total_penalty

    def get_recon(self) -> float:
        capacity = self.actor.get_capacity('Recon')
        skill = self.actor.get_armor_skill('Recon')

        return max(capacity, skill)

    def get_hearing(self) -> float:
        return self.actor.get_capacity('Hearing')

    def detect_sound(self, sound_id: int) -> ResponsePool:
        sounds = self.get_all_current_sounds()
        if sound_id not in sounds:
            return ResponsePool(Response(False, '-# Звука с данным идентификатором не существует...', 'Звуковое обнаружение'))

        sound = InBattleSound(sound_id, data_manager=self.data_manager)

        cost = 3
        ap_usage = self.actor.ap_use(cost)

        if not ap_usage:
            return ResponsePool(Response(False, '-# У вас не хватает очков действия для обнаружения звука', 'Звуковое обнаружение'))

        distance = self.actor.distance_to_layer(sound.layer_id)
        detection_chance = sound.get_detection_chance(distance)

        hearing = self.get_hearing() / 100
        detection_penalty = 100 - self.get_natural_noise()

        total_chance = 100 + detection_penalty - detection_chance * hearing

        roll = self.actor.check_skill('Analysis', total_chance)

        if roll[0]:
            if sound.actor_id:
                self.actor.set_target(sound.actor_id)
            return ResponsePool(Response(True, 'Вы обнаруживаете предполагаемое местоположение источника звука и наводитесь, готовясь к атаке!', 'Звуковое обнаружение'))
        else:
            return ResponsePool(Response(False, 'Вы не смогли обнаружить местоположение источника звуа', 'Звуковое обнаружение'))


class ActorVision:
    def __init__(self, actor: 'Actor'):
        self.actor = actor
        self.data_manager = actor.data_manager

        self.time_factor = self.get_time_factor()
        self.weather_factor = self.get_weather_factor()

        self.dov = self.distance_of_view()

    def distance_of_view(self):
        vision = self.actor.get_body().get_capacity('Vision') / 100
        actor_height = self.actor.get_total_height()

        height_bonus = actor_height * 400

        basic_fov = 5400 + height_bonus

        return basic_fov * vision * self.time_factor * self.weather_factor

    def get_nightvision_baff(self):
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('NightVision')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('NightVision', 0)

        return max(capacity, armor_bonus)

    def get_recon_baff(self):
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('Recon')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('Recon', 0)

        return max(capacity, armor_bonus)

    def get_thermal_vision_baff(self):
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('ThermalVision')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('ThermalVision', 0)

        return max(capacity, armor_bonus)

    def get_time_factor(self):
        time_factor = self.actor.get_battle().time.visibility if self.actor.battle_id else 100
        if time_factor < 100:
            night_vision_baff = self.get_nightvision_baff() / 100
            time_penalty = (100 - time_factor) * (1 - night_vision_baff) if night_vision_baff <= 1 else 0

        else:
            time_penalty = 0

        return (100 - time_penalty) / 100

    def get_weather_factor(self):
        return self.actor.get_battle().weather.visibility/100 if self.actor.battle_id else 1

    def layer_vigilance(self, target_layer: int, distance_delta: float):
        total_distance = abs(target_layer - self.actor.layer_id) * distance_delta
        terrain_coverage = Layer(target_layer, self.actor.battle_id).terrain.visibility / 100

        return round((self.dov - total_distance) / self.dov * 100 * self.time_factor * self.weather_factor * terrain_coverage, 2)

    def total_layers_vigilance(self):
        battle = self.actor.get_battle()

        battle_layers = battle.get_layers()
        battle_layers_id = set(battle_layers.keys())
        distance_delta = battle.distance_delta

        current_height = self.actor.get_total_height()

        layers_vigilance = {}
        cached_results = {}

        for i in reversed([i for i in battle_layers_id if i < self.actor.layer_id]):  # обратный проход по слоям
            if i in layers_vigilance:
                break

            if i in cached_results:
                layers_vigilance[i] = cached_results[i]
            else:
                vigilance = self.layer_vigilance(i, distance_delta)
                if vigilance <= 0:
                    break
                layers_vigilance[i] = vigilance
                cached_results[i] = vigilance

            if battle_layers[i].terrain.coverage and i != self.actor.layer_id:
                if current_height - battle_layers[i].get_height() > 10:
                    continue
                else:
                    break
            if battle_layers[i].get_height() - current_height >= 5:
                break

        for i in [i for i in battle_layers_id if i >= self.actor.layer_id]: # проход по слоям
            if i in layers_vigilance:
                break

            if i in cached_results:
                layers_vigilance[i] = cached_results[i]
            else:
                vigilance = self.layer_vigilance(i, distance_delta)
                if vigilance <= 0:
                    break
                layers_vigilance[i] = vigilance
                cached_results[i] = vigilance

            if battle_layers[i].terrain.coverage and i != self.actor.layer_id:
                if current_height - battle_layers[i].get_height() > 10:
                    continue
                else:
                    break
            if battle_layers[i].get_height() - current_height >= 5:
                break

        return layers_vigilance

    def get_visible_characters(self):
        layers_vigilance = self.total_layers_vigilance()
        thermal_vision_baff = 1+self.get_thermal_vision_baff()/100
        recon_baff = 1+self.get_recon_baff()/100

        visible_characters = {}

        for layer_id, vigilance in layers_vigilance.items():
            layer = Layer(layer_id, self.actor.battle_id)
            layer_characters = layer.get_all_characters_on_layer()

            if not layer_characters:
                continue

            visible_characters[layer_id] = []

            for character_id in layer_characters:
                if Actor(character_id, data_manager=self.data_manager).disguise() > vigilance * thermal_vision_baff * recon_baff:
                    continue
                else:
                    visible_characters[layer_id].append(character_id)

        return visible_characters

    def get_visible_dead_bodies(self):
        layers_vigilance = self.total_layers_vigilance()
        total_bodies = {}

        for layer in layers_vigilance:
            dead_bodies = [body.get('character_id') for body in self.data_manager.select_dict('BATTLE_DEAD', filter=f'layer_id = {layer} and battle_id = {self.actor.battle_id}')]
            total_bodies[layer] = dead_bodies

        return total_bodies

    def string_vigilance(self):
        from ArbCharacters import Character

        visible_characters = self.get_visible_characters()
        visible_dead_bodies = self.get_visible_dead_bodies()
        visible_layers = self.total_layers_vigilance()

        total_text = f''
        for layer in sorted(visible_layers.keys()):
            c_layer = Layer(layer, self.actor.battle_id, data_manager=self.data_manager)
            c_characters = visible_characters.get(layer, [])
            c_dead_bodies = visible_dead_bodies.get(layer, [])

            characters_text = f'Вы видите силуэты ' + f', '.join(f'**{Character(char, data_manager=self.data_manager).race.label.lower()} ||( {char} )||**' for char in c_characters if char != self.actor.actor_id) if c_characters else 'Вы не замечаете живых существ поблизости.'
            dead_bodies_text = f'. Вы видите трупы: ' + f', '.join(f'**{Character(char, data_manager=self.data_manager).race.label.lower()} ||( {char} )||**' for char in c_dead_bodies) if c_dead_bodies else ''

            layer_text = f'''
***{c_layer.label} ||(Слой {layer})||*** {'``<--- Вы здесь``' if self.actor.layer_id == layer else ''}
- *Видимость: **{visible_layers.get(layer):0.2f}%***
{c_layer.string_layer()}.
-# {characters_text}{dead_bodies_text}
'''
            total_text += layer_text

        return total_text


class ActorMovement:
    def __init__(self, actor: 'Actor'):
        self.actor = actor

    def set_layer(self, layer_id:int):
        query = {'layer_id': layer_id}
        self.actor.data_manager.update('BATTLE_CHARACTERS', query, f'character_id = {self.actor.actor_id}')
        self.actor.layer_id = layer_id

    def set_object(self, object_id:int | None):
        query = {'object': object_id}
        self.actor.data_manager.update('BATTLE_CHARACTERS', query, f'character_id = {self.actor.actor_id}')
        self.actor.object_id = object_id

    def movement_cost(self):
        movement_skill = self.actor.get_skill('Movement')
        moving_capacity = self.actor.get_capacity('Moving')
        distance_factor = self.actor.get_battle().distance_delta / 50

        if moving_capacity <= 0:
            return None

        move_factor = (200-moving_capacity)/100

        layer_movement_difficulty = self.actor.get_layer().terrain.movement_difficulty
        layer_movement_cost = self.actor.get_layer().terrain.movement_cost

        return round((1 + (layer_movement_difficulty - movement_skill)/100) * move_factor * layer_movement_cost * distance_factor)

    def get_nearby_layers_id(self):
        forward = self.actor.layer_id + 1
        back = self.actor.layer_id - 1
        if back < 0:
            back = None

        if forward > max(self.actor.get_battle().get_layers().keys()):
            forward = None

        return [back, forward]

    def trap_checking(self):
        current_traps = self.actor.get_layer().get_traps()
        if not current_traps:
            return True, Response(True, f'Вы успешно продвигаетесь по местности не встречая преград на своем пути...', 'Преграды')

        from ArbWeapons import Trap

        checking_count = len(current_traps)//3 if len(current_traps) > 3 else 1
        activations = []

        for _ in range(checking_count):
            character_analysis = self.actor.check_skill('Analysis')[0]
            character_movement = self.actor.check_skill('Movement')[0]

            c_trap: Trap = random.choice(current_traps)

            if c_trap.check_activation(character_analysis, character_movement):
                activations += c_trap.explode()
                total_damage = DamageManager(self.actor.data_manager).process_damage(self.actor.actor_id, activations)

                is_actor_dead = ActorDeath(self.actor.actor_id, None, data_manager=self.actor.data_manager).check_death()
                return False, Response(False, f'По мере движения вы натыкаетесь на ловушку ({c_trap.label}), которая активируется прямо рядом с вами!', 'Ловушки!')

        return True, Response(True, f'Вы успешно продвигаетесь по местности не встречая преград на своем пути...', 'Преграды')

    def move_forward(self):
        c_slots = self.get_nearby_layers_id()
        if c_slots[1] is None:
            return False, None

        c_cost = self.movement_cost()
        ap_use_result = self.actor.ap_use(c_cost)

        if not ap_use_result:
            return False, None
        else:
            if self.actor.fly_height == 0:
                success, response = self.trap_checking()
                if not success:
                    return success, response

            self.set_layer(c_slots[1])
            return True, None

    def move_back(self):
        c_slots = self.get_nearby_layers_id()
        if c_slots[0] is None:
            return False, None

        c_cost = self.movement_cost()
        ap_use_result = self.actor.ap_use(c_cost)

        if not ap_use_result:
            return False, None
        else:
            if self.actor.fly_height == 0:
                success, response = self.trap_checking()
                if not success:
                    return success, response

            self.set_layer(c_slots[0])
            return True, None

    def hande_move_event(self, layer_id:int):
        event = MoveEvent(self.actor, layer_id)
        statuses = self.actor.get_statuses()
        responses = statuses.handle_event('move', event)

        if random.randint(0, 100) > sum([random.randint(0, 100) for _ in range(len(statuses.get_melee_target_from()))]):
            statuses.flee_from_melee()
        else:
            return False, responses

        return True, responses

    def steps_volume(self):
        basic_roll = random.randint(10, 200)
        stealth_mod = self.actor.get_skill('Stealth') * 0.5
        return basic_roll - stealth_mod if basic_roll - stealth_mod > 10 else 10

    def move_to_layer(self, layer_id:int):
        if layer_id not in self.actor.get_battle().get_layers().keys():
            return ResponsePool(Response(False, 'Этого слоя не существует в данном бою.', 'Перемещение'))

        if self.actor.layer_id == layer_id:
            return ResponsePool(Response(False, 'Вы уже находитесь на этом слое', 'Перемещение'))

        move_success, responses = self.hande_move_event(self.actor.layer_id)
        if not move_success:
            return ResponsePool(Response(False, 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают сбежать', 'Неудачное перемещение'))

        steps_volume = self.steps_volume()

        self.set_object(None)

        if self.actor.layer_id < layer_id:
            for _ in range(layer_id-self.actor.layer_id):
                self.actor.make_sound('Steps', steps_volume)
                movement_success, layer_response = self.move_forward()
                if not movement_success:
                    responses.append(layer_response)
                    break
        elif self.actor.layer_id > layer_id:
            for _ in range(self.actor.layer_id-layer_id):
                self.actor.make_sound('Steps', steps_volume)
                movement_success, layer_response = self.move_back()
                if not movement_success:
                    responses.append(layer_response)
                    break

        responses.append(Response(True, f'-# Вы проходите какое-то расстояние и оказываетесь на **{Layer(self.actor.layer_id, self.actor.battle_id, data_manager=self.actor.data_manager).label}** ||**(Слой {self.actor.layer_id})**||. {Layer(self.actor.layer_id, self.actor.battle_id, data_manager=self.actor.data_manager).terrain.desc}','Перемещение'))
        return ResponsePool(responses)

    def get_layer_objects(self):
        layer = self.actor.layer_id
        battle = self.actor.battle_id

        return [object_id.get('object_id') for object_id in self.actor.data_manager.select_dict('BATTLE_OBJECTS', filter=f'layer_id = {layer} and battle_id = {battle}')]

    def set_fly_height(self, height: int):
        self.actor.fly_height = height
        self.actor.data_manager.update('BATTLE_CHARACTERS', {'height': height}, f'character_id = {self.actor.actor_id}')

    def fly(self, height: int):
        from ArbClothes import CharacterArmor

        stat = self.actor.get_body().get_capacity('Flying')
        armors_skills = CharacterArmor(self.actor.actor_id, data_manager=self.actor.data_manager).armors_skills().get('Flying', 0)

        total_value = stat + armors_skills

        if total_value <= 0:
            return ResponsePool(Response(False, 'Вы не можете летать!', 'Невозможно летать!'))

        cost = round((height // 10) * ((200 - total_value)/100))

        if height <= 0:
            return ResponsePool(Response(False, 'Вы не можете опуститься так низко!', 'Невозможно опуститься!'))

        cost = 1 if cost <= 0 and height > 0 else cost

        ap_use_result = self.actor.ap_use(cost)

        if not ap_use_result:
            return ResponsePool(Response(False, 'Вам не хватает очков действия для полета!', 'Невозможно летать!'))
        else:
            self.set_object(None)
            success, responses = self.hande_move_event(self.actor.layer_id)
            if not success:
                response = Response(False, 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают взлететь!', 'Невозможность полета!')
            else:
                response = Response(True, f'Вы летите выше на {height}м.!', 'Полет')
                self.set_fly_height(height)

            responses.append(response)

            return responses

    def move_to_object(self, object_id: int = None):
        layer_objects = self.get_layer_objects()
        if object_id not in layer_objects and object_id is not None:
            return ResponsePool(Response(False, f'Данного объекта ``({object_id})`` нет в этой местности!', 'Перемещение к объекту'))

        if object_id:
            if GameObject(object_id, data_manager=self.actor.data_manager).available_slots <= 0:
                return ResponsePool(Response(False, f'У данного объекта нет места, которое можно занять!'))

        c_cost = round(self.movement_cost() * 0.5)

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            return ResponsePool(Response(False, 'Вам не хватает очков действия для перемещения!', 'Перемещение к объекту'))

        move_result, responses = self.hande_move_event(self.actor.layer_id)

        if not move_result:
            return ResponsePool(Response(False, 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!', 'Противники!'))

        self.set_object(None)

        self.actor.make_sound('Steps', self.steps_volume())

        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking()
            responses.append(trap_response)
            if not success:
                return ResponsePool(responses)
        else:
            self.actor.fly_height(0)
            responses.append(Response(True, 'Вы снижаетесь для занимания объекта в качестве укрытия', 'Полет'))

        if object_id is not None:
            self.set_object(object_id)

        response = Response(True, f'Вы перемещаетесь к объекту **{GameObject(object_id, data_manager=self.actor.data_manager).object_type.label}** ||({object_id})|| и занимаете в качестве укрытия', 'Перемещение к объекту') if object_id else Response(True, f'Вы успешно покидаете укрытие!', 'Перемещение к объекту')
        responses.append(response)

        return ResponsePool(responses)

    def flee_from_melee(self):
        c_cost = round(self.movement_cost() * 0.5)

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            return ResponsePool(Response(False, 'Вам не хватает очков действия для перемещения!', 'Ближний бой'))

        move_result, responses = self.hande_move_event(self.actor.layer_id)

        if not move_result:
            return ResponsePool(Response(False,
                                         'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!',
                                         'Противники!'))

        self.actor.make_sound('Steps', self.steps_volume())

        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking()
            responses.append(trap_response)
            if not success:
                return ResponsePool(responses)

        self.actor.get_statuses().flee_from_melee()

        response = Response(True, f'Вам удаётся отбиться от противника и сбежать из ближнего боя!','Ближний бой')
        responses.append(response)

        return ResponsePool(responses)

    def escape(self):

        c_cost = self.movement_cost()

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            return ResponsePool(
                Response(False, 'Вам не хватает очков действия для перемещения!', 'Побег из боя'))

        move_result, responses = self.hande_move_event(self.actor.layer_id)

        if not move_result:
            return ResponsePool(Response(False,
                                         'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!',
                                         'Противники!'))

        self.set_object(None)

        self.actor.make_sound('Steps', self.steps_volume())

        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking()
            responses.append(trap_response)
            if not success:
                return ResponsePool(responses)

        self.actor.clear_ap()
        self.actor.get_statuses().clear_statuses()
        self.actor.data_manager.delete('BATTLE_CHARACTERS', f'character_id = {self.actor.actor_id}')

        response = Response(True, '-# Вы пересекаете местность и покидаете поле боя, оставляя сражение позади...', 'Побег из боя')
        responses.append(response)

        return ResponsePool(responses)


class ActorTacticalStatus:
    def __init__(self, actor: 'Actor', event_manager: 'EventManager'):
        self.actor = actor
        self.data_manager = actor.data_manager
        self.event_manager = event_manager

        self.actor_attack_trigger()
        self.actor_move_trigger()
        self.actor_object_trigger()

    def get_supressors(self):
        if self.actor.object_id is None:
            return []

        if self.data_manager.check('CHARS_COMBAT', f'supressed = {self.actor.object_id}'):
            return [Actor(actor.get('id'), data_manager=self.data_manager) for actor in self.data_manager.select_dict('CHARS_COMBAT', filter=f'supressed = {self.actor.object_id}')]
        else:
            return []

    def get_hunters(self):
        if self.data_manager.check('CHARS_COMBAT', f'hunted = {self.actor.actor_id}'):
            return [Actor(actor.get('id'), data_manager=self.data_manager) for actor in self.data_manager.select_dict('CHARS_COMBAT', filter=f'hunted = {self.actor.actor_id}')]
        else:
            return []

    def get_containments(self):
        if self.actor.layer_id is None:
            return []

        if self.data_manager.check('CHARS_COMBAT', f'contained = {self.actor.layer_id}'):
            total_actors = []
            potential_actors = [actor.get('id') for actor in self.data_manager.select_dict('CHARS_COMBAT', filter=f'contained = {self.actor.layer_id}')]
            for actor in potential_actors:
                if not self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {actor} AND battle_id = {self.actor.battle_id}'):
                    continue
                else:
                    total_actors.append(Actor(actor, data_manager=self.data_manager))

            return total_actors
        else:
            return []

    def get_in_overwatch(self):
        if self.data_manager.check('CHARS_COMBAT', f'ready = 1 and id = {self.actor.actor_id}'):
            return True
        else:
            return False

    def get_melee_target_from(self):
        if self.data_manager.check('CHARS_COMBAT', f'melee_target = {self.actor.actor_id}'):
            return [Actor(actor.get('id'), data_manager=self.data_manager) for actor in self.data_manager.select_dict('CHARS_COMBAT', filter=f'melee_target = {self.actor.actor_id}')]
        else:
            return []

    def get_enemy_readyness(self, enemy_id:int):
        if self.data_manager.check('CHARS_COMBAT', f'ready = 1 and id = {enemy_id}'):
            return True
        else:
            return False

    def clear_statuses(self):
        hunters = self.get_hunters()
        melee = self.get_melee_target_from()

        for actor in hunters:
            self.data_manager.update('CHARS_COMBAT', {'hunted': None},f'id = {actor.actor_id}')
        for actor in melee:
            self.data_manager.update('CHARS_COMBAT', {'melee_target': None}, f'id = {actor.actor_id}')

        query = {'supressed': None,
                 'hunted': None,
                 'melee_target': None,
                 'contained': None,
                 'ready': None,
                 'target': None}

        self.data_manager.update('CHARS_COMBAT', query, f'id = {self.actor.actor_id}')

    def flee_from_melee(self):
        melee = self.get_melee_target_from()
        for actor in melee:
            self.data_manager.update('CHARS_COMBAT', {'melee_target': None}, f'id = {actor.actor_id}')

        self.data_manager.update('CHARS_COMBAT', {'melee_target': None}, f'id = {self.actor.actor_id}')

    def actor_attack_trigger(self):
        supressors = self.get_supressors()
        hunters = self.get_hunters()
        melee = self.get_melee_target_from()

        sup_handler = SuppresssionHandler(supressors)
        hunt_handler = HuntHandler(hunters)
        melee_handler = MeleeHandler(melee)

        self.event_manager.listen('attack', sup_handler)
        self.event_manager.listen('attack', hunt_handler)
        self.event_manager.listen('attack', melee_handler)

        self.event_manager.listen('melee_attack', hunt_handler)

    def actor_move_trigger(self):
        containments = self.get_containments()
        supressors = self.get_supressors()
        melee = self.get_melee_target_from()

        cont_handler = ContainmentHandler(containments)
        sup_handler = SuppresssionHandler(supressors)
        melee_handler = MeleeHandler(melee)

        self.event_manager.listen('move', cont_handler)
        self.event_manager.listen('move', sup_handler)
        self.event_manager.listen('move', melee_handler)

    def actor_object_trigger(self):
        supressors = self.get_supressors()
        melee = self.get_melee_target_from()
        hunters = self.get_hunters()

        hunt_handler = HuntHandler(hunters)
        sup_handler = SuppresssionHandler(supressors)
        melee_handler = MeleeHandler(melee)

        self.event_manager.listen('object', hunt_handler)
        self.event_manager.listen('object', sup_handler)
        self.event_manager.listen('object', melee_handler)

    def enemy_overwatch_trigger(self, enemy_id:int):
        overwatch = OverwatchHandler([Actor(enemy_id, data_manager=self.data_manager)])
        self.event_manager.listen('attack', overwatch)

    def handle_event(self, event_type:str, event):
        if event_type == 'attack':
            self.enemy_overwatch_trigger(event.target)

        self.event_manager.trigger(event_type, event)

        return self.event_manager.responses


class ActionPoints:
    def __init__(self, ap: int=0, **kwargs):
        self.ap = ap
        self.actor_id = kwargs.get('actor_id', 0)
        self.data_manager = kwargs.get('data_manager', DataManager())

    @classmethod
    def character_ap(cls, actor_id:int, data_manager: DataManager = None):
        data_manager = data_manager if data_manager else DataManager()
        record = DataDict('CHARS_COMBAT', f'id = {actor_id}', data_manager=data_manager)
        return cls(ap=record.get('ap', 0), data_manager=data_manager, actor_id=actor_id)

    def add(self, ap: int):
        self.ap += ap
        self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')

    def use(self, ap: int):
        if self.ap >= ap:
            self.ap -= ap
            self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')
            return True
        else:
            return False

    def new_round_ap(self):
        basic_ap = 10
        ap_bonus = self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.actor_id}')[0].get('ap_bonus')
        ap_bonus = ap_bonus if ap_bonus is not None else 0
        self.data_manager.update('CHARS_COMBAT', {'ap': basic_ap + ap_bonus, 'ap_bonus': 0}, f'id = {self.actor_id}')


class ActorDeath:
    def __init__(self, target_id:int, killer_id:int=None, reason:str=None, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.target = target_id
        self.killer = killer_id
        self.reason = reason

    def check_death(self):
        body = Body(self.target, data_manager=self.data_manager)
        if body.is_dead()[0]:
            Actor(self.target, data_manager=self.data_manager).die(self.killer, self.reason)
            return True
        else:
            return False


class Actor(DataModel):
    def __init__(self, actor_id:int, **kwargs):
        self.actor_id = actor_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.event_manager = kwargs.get('event_manager', EventManager())

        DataModel.__init__(self, 'BATTLE_CHARACTERS', f'character_id = {self.actor_id}', data_manager=self.data_manager)

        self.battle_id = self.get('battle_id', 0) if self.get('battle_id') is not None else None
        self.layer_id = self.get('layer_id', 0) if self.get('layer_id') is not None else None
        self.object_id = self.get('object', 0) if self.get('object') is not None else None

        self.team_id = self.get('team_id', 0) if self.get('team_id') else None

        self.initiative = self.get('initiative', 0) if self.get('initiative') else 0
        self.is_active = self.get('is_active', None)

        self.fly_height = self.get('height', 0) if self.get('height') else 0
        self.ap = self.get_ap()

    def actor_inventory(self):
        from ArbItems import Inventory
        inventory: Inventory = Inventory.get_inventory_by_character(self.actor_id, data_manager=self.data_manager)
        return inventory

    def check_item_type_in_inventory(self, item_type:str):
        inventory: Inventory = self.actor_inventory()
        return inventory.find_item_by_type(item_type)

    @staticmethod
    def actor_status(message_dead=None, title_dead=None, message_inactive=None, title_inactive=None):
        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                if self.is_dead():
                    return ResponsePool(
                        Response(False, message_dead if message_dead else '-# Вы погибли и не можете совершать действия', title_dead if title_dead else 'Смерть...'))
                if not self.is_active:
                    return ResponsePool(Response(False, message_inactive if message_inactive else '-# Вы не можете совершать действия не на своём ходу', title_inactive if title_inactive else 'Активность'))
                return method(self, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def log_battle_event(event_description: str = ''):
        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                result = method(self, *args, **kwargs)
                target_id = kwargs.get('enemy_id', None)  # Получение ID цели из аргументов метода, если есть

                # Логирование события с именем метода как event_type
                BattleLogger.log_event(self.data_manager, self.battle_id, method.__name__, self.actor_id, event_description, target_id)

                return result

            return wrapper

        return decorator

    def delete_all_actor_sounds(self):
        self.data_manager.delete('BATTLE_SOUNDS', f'actor_id = {self.actor_id}')

    def die(self, killer_id:int = None, reason:str=None) -> None:
        BattleLogger.log_event(self.data_manager, self.battle_id, 'Death', actor_id=self.actor_id, event_description=f'Персонаж {self.actor_id} погибает...')
        self.clear_tactical_status()
        self.get_statuses().clear_statuses()
        self.clear_targets()
        self.clear_ap()
        self.delete_all_actor_sounds()

        query = {
            'battle_id': self.battle_id,
            'character_id': self.actor_id,
            'layer_id': self.layer_id,
            'killer': killer_id,
            'team_id': self.team_id,
            'reason': reason if reason else 'Погиб по неизвестным обстоятельствам'
        }
        self.data_manager.insert('BATTLE_DEAD', query)
        self.data_manager.delete('BATTLE_CHARACTERS', f'character_id = {self.actor_id}')

    def is_dead(self) -> bool:
        body = self.get_body()
        if body.is_dead()[0]:
            self.die()
            return True
        else:
            return False

    def is_enemy_dead(self, target_id:int) -> bool:
        if self.data_manager.check('BATTLE_DEAD', f'character_id = {target_id}'):
            return True
        else:
            return False

    def respond_if_enemy_dead(self):
        return Response(True, 'Противник, которого вы атаковали, погиб от вашей руки!', 'Убийство!')

    def get_combat_data(self) -> DataDict:
        return DataDict('CHARS_COMBAT', f'id = {self.actor_id}', data_manager=self.data_manager)

    def get_battle(self) -> Battlefield | None:
        return Battlefield(self.battle_id, data_manager=self.data_manager) if self.battle_id is not None else None

    def get_layer(self) -> Layer | None:
        return Layer(self.layer_id, self.battle_id, data_manager=self.data_manager) if self.layer_id is not None else None

    def get_object(self) -> GameObject | None:
        return GameObject(self.object_id, data_manager=self.data_manager) if self.object_id is not None else None

    def get_team(self) -> BattleTeam | None:
        return BattleTeam(self.team_id, data_manager=self.data_manager) if self.team_id else None

    def get_ap(self) -> ActionPoints:
        return ActionPoints.character_ap(self.actor_id, data_manager=self.data_manager)

    def check_skill(self, skill: str, difficulty: int = None):
        return Skill(self.actor_id, skill, data_manager=self.data_manager).skill_check(difficulty)

    def get_skill(self, skill: str) -> int:
        return Skill(self.actor_id, skill, data_manager=self.data_manager).lvl

    def get_body(self) -> Body:
        return Body(self.actor_id, data_manager=self.data_manager)

    def get_capacity(self, capacity: str) -> int:
        return self.get_body().get_capacity(capacity)

    def get_armor_skill(self, capacity: str) -> int:
        from ArbClothes import CharacterArmor
        skills = CharacterArmor(self.actor_id, data_manager=self.data_manager).armors_skills()

        if capacity not in skills:
            return 0
        else:
            return skills.get(capacity, 0) if skills.get(capacity, None) is not None else 0

    def get_weapon(self) -> Item | None:
        motorics = self.get_capacity('Manipulation')
        if motorics <= 0:
            return None
        return CharacterEquipment(self.actor_id, data_manager=self.data_manager).weapon()

    def get_grenades(self, grenade_id: int = None) -> list[int]:
        grenades = CharacterEquipment(self.actor_id, data_manager=self.data_manager).get_inventory().get_items_by_class('Граната')

        if not grenades:
            return []

        if not grenade_id:
            return [grenade.item_id for grenade in grenades]
        else:
            return [grenade.item_id for grenade in grenades if grenade.item_id == grenade_id]

    def get_race_attacks(self, race_attack: str) -> list:
        body = self.get_body().get_race_attacks()
        if race_attack and race_attack in body:
            return [race_attack]
        else:
            return body

    def get_statuses(self) -> ActorTacticalStatus:
        return ActorTacticalStatus(self, self.event_manager)

    def ap_use(self, ap:int) -> bool:
        result = self.ap.use(ap)
        if result:
            self.get_body().bleeding(ap)

        return result

    def make_sound(self, sound_name: str, volume: int, content:str=None):
        ActorSounds(self).make_sound(sound_name, volume, content)

    def calculate_height_delta(self, enemy_id: int) -> float:
        enemy = Actor(enemy_id, data_manager=self.data_manager)

        actor_height = self.get_total_height()
        enemy_height = enemy.get_total_height()

        total_height = abs(actor_height - enemy_height)

        return total_height

    def calculate_total_distance(self, enemy_id:int) -> float:
        enemy = Actor(enemy_id, data_manager=self.data_manager)

        total_height = self.calculate_height_delta(enemy_id)
        layer_distance = self.distance_to_layer(enemy.layer_id)

        return round(math.sqrt(total_height**2 + layer_distance**2))

    def get_total_height(self) -> float:
        layer_height = self.get_layer().get_height() if self.layer_id is not None else 0
        object_height = self.get_object().object_type.height if self.object_id is not None else 0
        self_height = self.fly_height

        return layer_height + object_height + self_height

    def disguise(self) -> float:
        from ArbClothes import CharacterArmor
        from ArbRaces import Race

        clothes_disguise = CharacterArmor(self.actor_id, data_manager=self.data_manager).calculate_disguise()
        race_disguise = Race(self.get_body().get_character_race(), data_manager=self.data_manager).natural_disguise
        object_disguise = self.get_object().object_type.coverage if self.object_id is not None else 0
        stealth_skill_value = self.get_skill('Stealth')
        stealth_modificator = 1 + stealth_skill_value * 0.005

        total_disguise = (clothes_disguise + race_disguise + object_disguise) * stealth_modificator

        return round(total_disguise, 2)

    def roll_initiative(self) -> int:
        team = BattleTeam(self.team_id, data_manager=self.data_manager) if self.team_id is not None else None

        team_bonus = team.role.initiative_bonus if team else 0

        return round(random.randint(0, 100) + team_bonus)

    def set_initiative(self, initiative: int) -> None:
        self.data_manager.update('BATTLE_CHARACTERS', {'initiative': initiative}, f'character_id = {self.actor_id}')

    def set_active(self, active_status: bool | None) -> None:
        is_active = 1

        if active_status is None:
            is_active = None
        elif active_status:
            is_active = 1
        elif not active_status and active_status is not None:
            is_active = 0

        self.is_active = active_status
        self.data_manager.update('BATTLE_CHARACTERS', {'is_active': is_active}, f'character_id = {self.actor_id}')

    def distance_to_layer(self, layer_id: int) -> float:
        distance_delta = self.get_battle().distance_delta
        return abs(self.layer_id - layer_id) * distance_delta

    def clear_tactical_status(self) -> None:
        query = {
            'hunted': None,
            'supressed': None,
            'contained': None,
            'ready': None
        }
        self.data_manager.update('CHARS_COMBAT', query, f'id = {self.actor_id}')

    def clear_targets(self) -> None:
        query = {
            'target': None,
            'melee_target': None
        }
        self.data_manager.update('CHARS_COMBAT', query, f'id = {self.actor_id}')

    def set_ap_bonus(self, ap:int) -> None:
        self.data_manager.update('CHARS_COMBAT', {'ap_bonus': ap}, f'id = {self.actor_id}')

    def clear_ap(self) -> None:
        self.data_manager.update('CHARS_COMBAT', {'ap': 0}, f'id = {self.actor_id}')

    @actor_status()
    @log_battle_event('Персонаж перезаряжает своё оружие')
    def reload(self, ammo_id:str = None) -> ResponsePool:
        from ArbWeapons import Weapon
        from ArbAmmo import Ammunition

        weapon_item = self.get_weapon()
        if not weapon_item:
            return ResponsePool(Response(False, 'У вас нет оружия для перезарядки', 'Перезарядка'))

        weapon = Weapon(weapon_item.item_id, data_manager=self.data_manager)
        if weapon.weapon_class == 'ColdSteel':
            return ResponsePool(Response(False, 'Ваше оружие невозможно перезарядить', 'Перезарядка'))

        cost = weapon.reload_ap_cost
        ap_usage = self.ap_use(cost)

        if not ap_usage:
            return ResponsePool(Response(False, 'У вас не хватает очков действия для перезарядки', 'Перезарядка'))

        reload_success = weapon.reload(ammo_id)

        if not reload_success:
            return ResponsePool(Response(False, f'Вы не смогли перезарядить оружие...', 'Перезарядка'))

        equiped_ammo = Ammunition(weapon.get_current_ammotype(), data_manager=self.data_manager)
        text = f'''
-# Нажав на фиксатор магазина и выкинув разряженную обойму на землю, попутно доставая второй рукой новую из подсумки. Как только старая обойма вышла из гнезда магазина, вы вставили новую обойму **{equiped_ammo.label}** **(Калибр: {equiped_ammo.caliber}, Тип: {equiped_ammo.type})**, и, зафиксировав ее, вы передергиваете затвор своего оружия - **{weapon.label}**
'''
        return ResponsePool(Response(True, text, 'Перезарядка'))

    @actor_status()
    @log_battle_event('Персонаж обнаруживает звук')
    def detect_sound(self, sound_id:int) -> ResponsePool:
        return ActorSounds(self).detect_sound(sound_id)

    @actor_status()
    @log_battle_event('Персонаж переходит в режим ожидания, перенося свои ОД на свой следующий ход')
    def waiting(self) -> ResponsePool:
        current_ap = self.ap.ap
        self.set_ap_bonus(current_ap)
        self.clear_ap()
        return ResponsePool(Response(True, f'Вы ожидаете следующей возможности для действий и завершаете свой ход...', 'Ожидание'))

    @actor_status()
    @log_battle_event('Персонаж начинает охоту на другого персонажа')
    def set_hunt(self, enemy_id: int) -> ResponsePool:
        from ArbWeapons import Weapon

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['SR', 'AR', 'PST', 'TUR']:
            return ResponsePool(Response(False, f'У вас нет оружия дальнего боя подходящего для охоты на противника или ваши конечности слишком повреждены чтобы стрелять', 'Невозможно охотиться'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if ap_usage:
            self.clear_tactical_status()
            self.data_manager.update('CHARS_COMBAT', {'hunted': enemy_id}, f'id = {self.actor_id}')

            return ResponsePool(Response(True, f'Вы наводитесь на противника и внимательно следите за его действиями, чтобы нанести атаку в удачный момент', 'Охота'))
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно охотиться'))

    @actor_status()
    @log_battle_event('Персонаж начинает подавлять укрытие')
    def set_suppression(self, cover_id: int) -> ResponsePool:
        from ArbWeapons import Weapon

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['MG', 'AR', 'TUR']:
            return ResponsePool(Response(False,f'У вас нет оружия дальнего боя подходящего для подавления укрытия или ваши конечности слишком повреждены чтобы стрелять', 'Невозможно подавлять'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if ap_usage:
            self.clear_tactical_status()
            self.data_manager.update('CHARS_COMBAT', {'supressed': cover_id}, f'id = {self.actor_id}')

            return ResponsePool(Response(True, f'Вы наводитесь на укрытие и начинаете подавлять его огнём не давая возможному противнику шанса высунуться без последствий','Подавление'))
        else:
            return ResponsePool(
                Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно подавлять'))

    @actor_status()
    @log_battle_event('Персонаж начинает подавлять слой')
    def set_containment(self, layer_id: int) -> ResponsePool:
        from ArbWeapons import Weapon

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['MG', 'AR', 'TUR']:
            return ResponsePool(Response(False,f'У вас нет оружия дальнего боя подходящего для сдерживания слоя или ваши конечности слишком повреждены чтобы стрелять', 'Невозможно сдерживать'))

        if layer_id not in [self.layer_id-1, self.layer_id+1, self.layer_id]:
            return ResponsePool(Response(False, f'Вы можете сдерживать только текущий слой и ближайшие слои', 'Невозможно сдерживать'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if ap_usage:
            self.clear_tactical_status()
            self.data_manager.update('CHARS_COMBAT', {'contained': layer_id}, f'id = {self.actor_id}')

            return ResponsePool(Response(True, f'Вы наводитесь и открываете выборочный огонь по всему слою, не давая противнику шанса продвинуться ближе к вам без последствий','Сдерживание'))
        else:
            return ResponsePool(
                Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно сдерживать'))

    @actor_status()
    @log_battle_event('Персонаж переходит в режим дозора')
    def set_overwatch(self) -> ResponsePool:
        from ArbWeapons import Weapon

        weapon = self.get_weapon()

        if not weapon:
            return ResponsePool(Response(False,f'У вас нет оружия дальнего боя для дозора или ваши конечности слишком повреждены чтобы стрелять', 'Дозор невозможен'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if ap_usage:
            self.clear_tactical_status()
            self.data_manager.update('CHARS_COMBAT', {'ready': 1}, f'id = {self.actor_id}')

            return ResponsePool(Response(True, f'Вы внимательно оглядываетесь по сторонам в ожидании атаки противника...','Дозор'))
        else:
            return ResponsePool(
                Response(False, f'У вас не хватает очков действий для совершения действия', 'Дозор невозможен'))

    def check_enemy_id(self, enemy_id: int) -> bool:
        if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {enemy_id} AND battle_id = {self.battle_id}'):
            return True
        else:
            return False

    @actor_status()
    @log_battle_event('Персонаж наводится на новую цель')
    def set_target(self, target_id:int) -> ResponsePool:
        if self.get_melee_target():
            return ResponsePool(Response(False,
                                         f'Вы находитесь в ближнем бою и не можете выбрать другую цель!',
                                         'Ближний бой'))

        if not self.check_enemy_id(target_id):
            return ResponsePool(Response(False,
                                         f'Данного персонажа нет в бою, вы не можете сделать его целью',
                                         'Цель'))

        self.data_manager.update('CHARS_COMBAT', {'target': target_id}, f'id = {self.actor_id}')
        return ResponsePool(Response(True, f'Вы наводитесь на предполагаемое местоположение противника и готовы к атаке', 'Цель'))

    @actor_status()
    @log_battle_event('Персонаж навязывает ближний бой противнику')
    def set_melee_target(self, target_id:int) -> ResponsePool:
        if not self.check_enemy_id(target_id):
            return ResponsePool(Response(False,
                                         f'Данного персонажа нет в бою, вы не можете сделать его целью ближнего боя',
                                         'Ближний бой'))

        if not self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {target_id} AND layer_id = {self.layer_id}'):
            return ResponsePool(Response(False,
                                         f'Вы не находитесь рядом с этим персонажем и не можете навязать ему ближний бой',
                                         'Ближний бой'))

        if Actor(target_id, data_manager=self.data_manager).fly_height != self.fly_height:
            fly_capacity = self.get_capacity('Flying')
            fly_armor_skill = self.get_armor_skill('Flying')
            if not fly_capacity and not fly_armor_skill:
                return ResponsePool(Response(False,
                                             f'Противник находится в воздухе и вы не можете подняться выше...',
                                             'Ближний бой'))
            else:
                ActorMovement(self).set_fly_height(Actor(target_id, data_manager=self.data_manager).fly_height)

        melee_targets = self.get_melee_target_from()

        ap_usage = self.ap_use(1) if target_id not in melee_targets else True

        if ap_usage:
            self.clear_tactical_status()
            self.clear_targets()
            event = MoveEvent(self, self.layer_id)
            responses = self.get_statuses().handle_event('move', event)

            self.data_manager.update('BATTLE_CHARACTERS', {'object': None}, f'character_id = {self.actor_id}')
            self.data_manager.update('CHARS_COMBAT', {'melee_target': target_id}, f'id = {self.actor_id}')
            Actor(target_id, data_manager=self.data_manager).clear_tactical_status()
            self.data_manager.update('BATTLE_CHARACTERS', {'object': None}, f'character_id = {target_id}')
            self.data_manager.update('CHARS_COMBAT', {'melee_target': self.actor_id}, f'id = {target_id}')

            responses.append(Response(True, f'Вы сближаетесь с противником ``{target_id}`` и навязываете ему ближний бой!', 'Ближний бой'))
            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Ближний бой'))

    @actor_status()
    @log_battle_event('Персонаж сбегает из ближнего боя')
    def flee_from_melee(self):
        return ActorMovement(self).flee_from_melee()

    def get_target(self) -> int | None:
        target = self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.actor_id}')[0].get('target', None)
        if target is not None:
            return target
        else:
            return None

    def get_melee_target(self) -> int | None:
        melee_target = self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.actor_id}')[0].get('melee_target', None)
        if melee_target is not None:
            return melee_target
        else:
            return None

    def get_melee_target_from(self):
        if self.data_manager.check('CHARS_COMBAT', f'melee_target = {self.actor_id}'):
            return [actor.get('id') for actor in self.data_manager.select_dict('CHARS_COMBAT', filter=f'melee_target = {self.actor_id}')]
        else:
            return []

    @actor_status()
    @log_battle_event('Персонаж использует своё оружие для дальней атаки')
    def range_attack(self, enemy_id: int = None) -> ResponsePool:
        from ArbWeapons import Weapon

        enemy_id = self.get_target() if enemy_id is None else enemy_id
        if not enemy_id:
            return ResponsePool(Response(False, f'У вас нет цели для атаки!', 'Невозможно стрелять'))

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class == 'ColdSteel':
            return ResponsePool(Response(False, f'У вас нет оружия дальнего боя для совершения атаки или ваши конечности слишком повреждены чтобы стрелять', 'Невозможно стрелять'))

        melee_from = self.get_melee_target_from()
        if (melee_from or self.get_melee_target()) and Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['PST', 'SG', 'SMG']:
            return ResponsePool(Response(False, f'Вы не можете стрелять из данного оружия пока находитесь в ближнем бою!', 'Невозможно стрелять'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if ap_usage:
            event = AttackEvent(self, enemy_id)
            responses = self.get_statuses().handle_event('attack', event)
            attack_result = RangeAttack(self, weapon.item_id, data_manager=self.data_manager).attack(enemy_id)

            if attack_result.success:
                responses.append(Response(True, f'Вы открываете огонь из {weapon.label} по противнику ``{enemy_id}``!', 'Стрельба!'))
            else:
                responses.append(Response(False, f'Вы готовитесь к атаке из {weapon.label} по противнику ``{enemy_id}`` но вам не удается это сделать.', 'Неудачная стрельба'))

            if self.is_enemy_dead(enemy_id):
                responses.append(self.respond_if_enemy_dead())

            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно стрелять'))

    @actor_status()
    @log_battle_event('Персонаж использует оружие для атаки в ближнем бою')
    def melee_attack(self, enemy_id:int = None) -> ResponsePool:
        from ArbWeapons import Weapon

        melee_from = self.get_melee_target_from()
        if enemy_id not in melee_from or enemy_id is None:
            enemy_id = self.get_melee_target()

        if not enemy_id:
            return ResponsePool(Response(False, f'У вас нет целей для атаки в ближнем бою!', 'Невозможно атаковать'))

        weapon = self.get_weapon()
        if not weapon:
            return ResponsePool(Response(False, f'У вас нет оружия для совершения атаки или ваши конечности слишком повреждены чтобы совершить атаку', 'Невозможно атаковать'))

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)
        if ap_usage:
            event = AttackEvent(self, enemy_id)
            responses = self.get_statuses().handle_event('melee_attack', event)
            attack_result = MeleeAttack(self, weapon.item_id, data_manager=self.data_manager).attack(enemy_id)
            if attack_result.success:
                responses.append(Response(True, f'Вы атакуете противника ``{enemy_id}`` при помощи {weapon.label} в ближнем бою!', 'Ближний бой!'))
            else:
                responses.append(Response(False, f'Вы готовитесь к ближней атаке противника ``{enemy_id}`` но вам не удается это сделать.', 'Неудачный ближний бой'))

            if self.is_enemy_dead(enemy_id):
                responses.append(self.respond_if_enemy_dead())

            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно атаковать'))

    @actor_status()
    @log_battle_event('Персонаж использует расовую атаку')
    def race_attack(self, enemy_id: int = None, race_attack: str=None) -> ResponsePool:
        from ArbWeapons import RaceAttack

        enemy_id = self.get_melee_target() if enemy_id is None else enemy_id
        enemy_id = self.get_target() if enemy_id is None else enemy_id

        if not enemy_id:
            return ResponsePool(Response(False, f'У вас нет цели для атаки!', 'Невозможно атаковать'))


        attacks = self.get_race_attacks(race_attack)
        if not attacks:
            return ResponsePool(Response(False, f'У вас нет доступных атак, которые вы могли бы применить или у вас нет указанной атаки!', 'Невозможно атаковать'))

        attack = random.choice(attacks)

        distance_to_enemy = self.calculate_total_distance(enemy_id)
        if distance_to_enemy > RaceAttack(attack, data_manager=self.data_manager).range:
            return ResponsePool(Response(False, f'Цель находится слишком далеко для совершения расовой атаки!', 'Невозможно атаковать'))

        ap_usage = self.ap_use(RaceAttack(attack, data_manager=self.data_manager).ap_cost)

        if ap_usage:
            event = AttackEvent(self, enemy_id)
            responses = self.get_statuses().handle_event('melee_attack', event)

            attack_result = BodyPartAttack(self, attack, data_manager=self.data_manager).attack(enemy_id)
            if attack_result.success:
                responses.append(Response(True, f'Вы готовитесь к {RaceAttack(attack, data_manager=self.data_manager).label} и набрасываетесь на противника ``{enemy_id}``!', 'Атака!'))
            else:
                responses.append(Response(False, f'Вы готовитесь к {RaceAttack(attack, data_manager=self.data_manager).label} и набрасываетесь на противника ``{enemy_id}`` но вам не удается это сделать.', 'Неудачная атака'))

            if self.is_enemy_dead(enemy_id):
                responses.append(self.respond_if_enemy_dead())

            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно атаковать'))

    @actor_status()
    @log_battle_event('Персонаж бросает гранату')
    def throw_grenade(self, enemy_id: int = None, grenade_id: int=None) -> ResponsePool:

        melee_from = self.get_melee_target_from()
        if melee_from or self.get_melee_target():
            return ResponsePool(Response(False, f'Вы не можете бросить гранату находясь в ближнем бою!', 'Невозможно бросить гранату'))

        enemy_id = self.get_target() if enemy_id is None else enemy_id
        if not enemy_id:
            return ResponsePool(Response(False, f'У вас нет цели для атаки!', 'Невозможно бросить гранату'))

        distance_to_enemy = self.calculate_total_distance(enemy_id)
        if distance_to_enemy > 50:
            return ResponsePool(
                Response(False, f'Цель находится слишком далеко для броска гранаты', 'Невозможно бросить гранату'))

        grenades = self.get_grenades(grenade_id)
        if not grenades:
            return ResponsePool(Response(False, f'У вас нет доступных гранат для броска или у отсутствует указанная граната!', 'Невозможно бросить гранату'))

        ap_usage = self.ap_use(3)

        if ap_usage:
            event = AttackEvent(self, enemy_id)
            responses = self.get_statuses().handle_event('attack', event)
            grenade = random.choice(grenades)
            grenade_item = Item(grenade, data_manager=self.data_manager)
            attack_result = ThrowGrenade(self, grenade, data_manager=self.data_manager).attack(enemy_id)
            responses.append(Response(True, f'Вы бросаете {grenade_item.label} в противника ``{enemy_id}``!', 'Бросок гранаты!'))

            if self.is_enemy_dead(enemy_id):
                responses.append(self.respond_if_enemy_dead())

            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно бросить гранату'))

    @actor_status()
    @log_battle_event('Персонаж движется на другой слой')
    def move_to_layer(self, layer_id: int) -> ResponsePool:
        result = ActorMovement(self).move_to_layer(layer_id)

        return result

    @actor_status()
    @log_battle_event('Персонаж движется к объекту')
    def move_to_object(self, object_id: int) -> ResponsePool:
        result = ActorMovement(self).move_to_object(object_id)
        return result

    @actor_status()
    @log_battle_event('Персонаж сбегает из боя')
    def escape(self) -> ResponsePool:
        result = ActorMovement(self).escape()
        return result

    @actor_status()
    @log_battle_event('Персонаж взлетает')
    def fly(self, height) -> ResponsePool:
        return ActorMovement(self).fly(height)

    @actor_status()
    @log_battle_event('Персонаж взаимодействует с объектом')
    def interact_with_object(self, enemy_id:int=None) -> ResponsePool:
        object = self.get_object()
        if not object:
            return ResponsePool(Response(False, 'Вы не находитесь рядом с объектом, с которым можно взаимодействовать', 'Взаимодействие с объектом'))

        ap_usage = self.ap_use(2)

        if ap_usage:
            self.make_sound('Interaction', random.randint(50, 150))

            event = ObjectEvent(self, object_id=object.id)
            responses = self.get_statuses().handle_event('object', event)
            result = object.interact(self.actor_id, enemy_id=enemy_id)
            responses.append(result)

            if enemy_id:
                if self.is_enemy_dead(enemy_id):
                    responses.append(self.respond_if_enemy_dead())

            return ResponsePool(responses)
        else:
            return ResponsePool(Response(False, f'У вас не хватает очков действий для совершения действия', 'Невозможно взаимодействовать с объектом'))

    def __repr__(self):
        return f'Actor({self.actor_id})'









class AttackEvent(Event):
    def __init__(self, actor: 'Actor', target):
        super().__init__(actor)
        self.target = target


class MoveEvent(Event):
    def __init__(self, actor: 'Actor', layer):
        super().__init__(actor)
        self.layer = layer


class ObjectEvent(Event):
    def __init__(self, actor: 'Actor', object_id):
        super().__init__(actor)
        self.object_id = object_id


class HuntHandler(EventHandler):
    def handle(self, event: AttackEvent | ObjectEvent):
        if isinstance(event, AttackEvent | ObjectEvent):
            responses = []

            for hunter in self.actors:
                weapon = hunter.get_weapon()
                if weapon:
                    attack_result = RangeAttack(hunter, weapon.item_id, data_manager=hunter.data_manager).attack(event.source.actor_id)
                    if attack_result.success:
                        response = Response(False, f'Противник ``{hunter.actor_id}``, который следил за вашими действиями, атаковал вас!', 'Охота!')
                        responses.append(response)
                        responses.append(attack_result)
                hunter.data_manager.update('CHARS_COMBAT', {'hunted': None}, f'id = {hunter.actor_id}')

            return responses
        else:
            return []


class SuppresssionHandler(EventHandler):
    def handle(self, event: AttackEvent | MoveEvent | ObjectEvent):
        if isinstance(event, AttackEvent | MoveEvent | ObjectEvent):
            responses = []
            for suppressor in self.actors:
                weapon = suppressor.get_weapon()
                if weapon:
                    attack_result = RangeAttack(suppressor, weapon.item_id, data_manager=suppressor.data_manager).attack(event.source.actor_id)
                    if attack_result.success:
                        response = Response(False, f'Противник ``{suppressor.actor_id}``, подавляющий ваше укрытия атаковал вас!', 'Подавление!')
                        responses.append(response)
                        responses.append(attack_result)

            return responses
        else:
            return []


class ContainmentHandler(EventHandler):
    def handle(self, event: MoveEvent):
        if isinstance(event, MoveEvent):
            responses = []
            for containment in self.actors:
                weapon = containment.get_weapon()
                if weapon:
                    attack_result = RangeAttack(containment, weapon.item_id, data_manager=containment.data_manager).attack(event.source.actor_id)
                    if attack_result.success:
                        response = Response(False, f'Противник ``{containment.actor_id}`` который сдерживал огнем местность, на которой вы находитесь, атаковал вас!', 'Сдерживание!')
                        responses.append(response)
                        responses.append(attack_result)

            return responses
        else:
            return []


class OverwatchHandler(EventHandler):
    def handle(self, event: AttackEvent):
        if isinstance(event, AttackEvent):
            responses = []
            for watcher in self.actors:
                weapon = watcher.get_weapon()
                if weapon:
                    attack_result = RangeAttack(watcher, weapon.item_id, data_manager=watcher.data_manager).attack(event.source.actor_id)
                    if attack_result.success:
                        response = Response(False, f'Противник ``{watcher.actor_id}`` находился в дозоре и контратаковал вас!', 'Дозор!')
                        responses.append(response)
                        responses.append(attack_result)

                    watcher.data_manager.update('CHARS_COMBAT', {'ready': None}, f'id = {watcher.actor_id}')

            return responses
        else:
            return []


class MeleeHandler(EventHandler):
    def handle(self, event: AttackEvent | MoveEvent | ObjectEvent):
        if isinstance(event, AttackEvent | MoveEvent | ObjectEvent):
            responses = []
            for actor in self.actors:
                weapon = actor.get_weapon()
                if weapon:
                    attack_result = MeleeAttack(actor, weapon.item_id, data_manager=actor.data_manager).attack(event.source.actor_id)
                else:
                    attack_result = BodyPartAttack(actor, random.choice(actor.get_race_attacks()), data_manager=actor.data_manager).attack(event.source.actor_id)

                if attack_result.success:
                    response = Response(False, f'Сдерживающий вас в ближнем бою противник ``{actor.actor_id}`` атаковал вас!', 'Ближний бой!')
                    responses.append(response)
                    responses.append(attack_result)

            return responses
        else:
            return []





# time = datetime.datetime.now()
# print(Actor(1).move_to_layer(0))
# print(datetime.datetime.now() - time)

# class ActorCombat:
#     def __init__(self, id:int, **kwargs):
#         self.id = id
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         data = self.fetch_data()
#         self.ap = data.get('ap', 0)
#         self.ap_bonus = data.get('ap_bonus', 0)
#         self.luck = data.get('luck', 0)
#         self.blood_lost = data.get('blood_lost', 0)
#
#         self.supressed = data.get('supressed', None)
#         self.hunted = data.get('hunted', None)
#         self.contained = data.get('contained', None)
#         self.ready = data.get('ready', False) in [1, 'Да', 'да']
#         self.current_target = data.get('target', None)
#         self.movement_points = data.get('movement_points', None) if data.get('movement_points', None) is not None else 0
#
#         self.melee_target = data.get('melee_target', None)
#         self.melee_target_from = self.get_melee_target_from()
#
#         self.supressed_from = self.supresser_id()
#         self.contained_from = self.container_id()
#         self.hunted_from = self.hunter_id()
#
#     def get_melee_target_from(self):
#         if self.data_manager.check('CHARS_COMBAT', f'melee_target = {self.id}'):
#             return [char.get('id') for char in self.data_manager.select_dict('CHARS_COMBAT',filter=f'melee_target = {self.id}')]
#         else:
#             return []
#
#     def fetch_data(self):
#         if self.data_manager.check('CHARS_COMBAT',f'id = {self.id}') is None:
#             return {}
#         else:
#             return self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {self.id}')[0]
#
#     def hunter_id(self):
#         if self.data_manager.check('CHARS_COMBAT',f'hunted = {self.id}') is None:
#             return []
#         else:
#             total_hunters = []
#             for e in self.data_manager.select_dict('CHARS_COMBAT',filter=f'hunted = {self.id}'):
#                 total_hunters.append(e.get('id'))
#
#             return total_hunters
#
#     def supresser_id(self):
#         if self.data_manager.check('CHARS_COMBAT',f'supressed = {self.id}') is None:
#             return None
#         else:
#             total_supressers = []
#             for e in self.data_manager.select_dict('CHARS_COMBAT',filter=f'supressed = {self.id}'):
#                 total_supressers.append(e.get('id'))
#             return total_supressers
#
#     def container_id(self):
#         if not self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {self.id}'):
#             return []
#         data = self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'character_id = {self.id}')[0]
#
#
#
#         c_battle = data.get('battle_id')
#         c_layer = data.get('layer_id')
#         total_containers = []
#         potential_containers = []
#
#         for e in self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'battle_id = {c_battle} AND (layer_id = {c_layer+1} OR {c_layer-1})'):
#             potential_containers.append(e.get('character_id'))
#
#         for e in potential_containers:
#             e_contained = self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {e}')[0].get('contained', None)
#             if e_contained and (e_contained + 1 == c_layer or e_contained - 1 == c_layer):
#                 total_containers.append(e)
#
#         return total_containers
#
#     def is_enemy_ready(self, enemy_id:int):
#         if self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') is None:
#             return False
#         else:
#             status = self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {enemy_id}')[0].get('ready', None)
#             if status:
#                 return True
#             else:
#                 return False
#
#     def set_melee_target(self, enemy_id:int):
#
#         if Actor(enemy_id, data_manager=self.data_manager).height > 0:
#             return False
#
#         if self.ap >= 1:
#             self.ap_use(1)
#             self.clear_statuses()
#             self.data_manager.update('CHARS_COMBAT', {'melee_target': enemy_id}, filter=f'id = {self.id}')
#             self.data_manager.update('CHARS_COMBAT', {'melee_target': self.id}, filter=f'id = {enemy_id}')
#             self.melee_target = enemy_id
#             return True
#         else:
#             return False
#
#     def flee_from_melee(self):
#         self.clear_statuses()
#         if self.melee_target_from:
#             for i in self.melee_target_from:
#                 self.data_manager.update('CHARS_COMBAT',{'melee_target': None},f'id = {i}')
#         else:
#             pass
#
#     def get_current_weapons(self, item_id:int=None):
#         c_weapons_data = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'id = {self.id} AND slot = "Оружие"')
#         weapons = []
#         for i in c_weapons_data:
#             weapons.append(i.get('item_id'))
#
#         if item_id is None:
#             return weapons
#         elif item_id in weapons:
#             return [item_id]
#         else:
#             return []
#
#     def check_if_current_weapon_melee(self, weapon_id:int=None):
#         from ArbWeapons import Weapon
#
#         c_weapon = self.get_current_weapons()
#         if c_weapon is None:
#             return False
#         else:
#             if weapon_id in c_weapon:
#                 c_weapon = weapon_id
#             else:
#                 c_weapon = random.choice(c_weapon)
#
#             c_class = Weapon(c_weapon, data_manager=self.data_manager).Class
#             if c_class == 'ColdSteel':
#                 return True
#             else:
#                 return False
#
#     def ap_new(self) -> int:
#         c_dex = CharacterAttributes(self.id).check_characteristic('Выносливость')
#
#         pain = Body(self.id).calculate_total_pain()
#         cons = Body(self.id).physical_stat('Сознание')
#         bonus = self.ap_bonus
#
#         if pain <= 10:
#             pain = 0
#         else:
#             pain = pain - 10
#
#         ap = round(c_dex / 3) * ((cons - pain) / 100) + bonus
#
#         self.data_manager.update('CHARS_COMBAT', {'ap_bonus': 0}, filter=f'id = {self.id}')
#
#         self.ap += ap
#
#         return ap
#
#     def ap_use(self, ap) -> None:
#         from ArbCharacters import Race, Character
#
#         bleed = Body(self.id).calculate_total_bleeding()
#         blood = Race(Character(self.id).Race).Blood
#
#         c_loss = (bleed / blood) * 100
#
#         c_ap_bloodloss = round((c_loss / 24) / 60, 2)
#
#         total_bloodloss = ap * c_ap_bloodloss
#
#         self.data_manager.update('CHARS_COMBAT', {'blood_lost': self.blood_lost - total_bloodloss},filter=f'id = {self.id}')
#         self.data_manager.update('CHARS_COMBAT', {'ap': self.ap - ap}, filter=f'id = {self.id}')
#         self.ap -= ap
#
#     def ap_cost_usage(self, ap:int):
#         if self.ap >= ap:
#             self.ap_use(ap)
#             return True
#         else:
#             return False
#
#     def waiting(self):
#         ap_bonus = self.ap + self.ap_bonus
#         self.ap = 0
#         self.data_manager.update('CHARS_COMBAT', {'ap_bonus': ap_bonus}, filter=f'id = {self.id}')
#
#     def use_movement_points(self, mp:int):
#         self.movement_points += mp
#         self.data_manager.update('CHARS_COMBAT', {'movement_points': self.movement_points}, f'id = {self.id}')
#
#     def clear_statuses(self):
#         prompt = {'supressed': None,
#                   'hunted': None,
#                   'contained': None,
#                   'ready': None,
#                   'melee_target': None,
#                   'target': None}
#
#         self.data_manager.update('CHARS_COMBAT',prompt,f'id = {self.id}')
#
#     def supress_enemy(self, enemy_id:int):
#         if self.data_manager.check('CHARS_COMBAT', f'id = {enemy_id}') is None:
#             return False
#         else:
#             c_cost = 2
#             if self.ap_cost_usage(c_cost):
#                 self.clear_statuses()
#                 self.data_manager.update('CHARS_COMBAT', {'supressed': enemy_id}, f'id = {self.id}')
#                 self.set_target(enemy_id)
#                 return True
#             else:
#                 return False
#
#     def hunt_enemy(self, enemy_id:int):
#         if self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') is None:
#             return False
#         else:
#             c_cost = 2
#             if self.ap_cost_usage(c_cost):
#                 self.clear_statuses()
#                 self.data_manager.update('CHARS_COMBAT',{'hunted': enemy_id}, f'id = {self.id}')
#                 self.set_target(enemy_id)
#                 return True
#             else:
#                 return False
#
#     def contain_enemy(self, layer_id:int):
#         c_layer = Actor(self.id, data_manager=self.data_manager).current_layer_id
#         c_battle = Actor(self.id, data_manager=self.data_manager).current_battle_id
#
#         if layer_id > c_layer:
#             layer_id = c_layer + 1 if layer_id > c_layer + 1 else c_layer
#         elif layer_id < c_layer:
#             layer_id = c_layer - 1 if layer_id < c_layer - 1 else c_layer
#
#         if self.data_manager.check('BATTLE_LAYERS', f'id = {layer_id} AND battle_id = {c_battle}') is None:
#             return False
#         else:
#             c_cost = 2
#             if self.ap_cost_usage(c_cost):
#                 self.clear_statuses()
#                 self.data_manager.update('CHARS_COMBAT', {'contained': layer_id}, f'id = {self.id}')
#
#                 return True
#             else:
#                 return False
#
#     def overwatch(self):
#         if self.data_manager.check('CHARS_COMBAT',f'id = {self.id}') is None:
#             return False
#         else:
#             c_cost = 2
#             if self.ap_cost_usage(c_cost):
#                 self.clear_statuses()
#                 self.data_manager.update('CHARS_COMBAT', {'ready': 1}, f'id = {self.id}')
#                 return True
#             else:
#                 return False
#
#     def get_prepared(self):
#         c_cost = 2
#         if self.ap_cost_usage(c_cost):
#             self.clear_statuses()
#             self.data_manager.update('CHARS_COMBAT',{'ready': 1}, f'id = {self.id}')
#             return True
#         else:
#             return False
#
#     def set_target(self, enemy_id:int):
#         if not self.data_manager.check('CHARS_COMBAT',f'id = {enemy_id}') or self.melee_target or self.melee_target_from:
#             return False
#         else:
#             self.flee_from_melee()
#             self.data_manager.update('CHARS_COMBAT',{'target': enemy_id}, f'id = {self.id}')
#             return True
#
#     def clear_target(self):
#         self.data_manager.update('CHARS_COMBAT',{'target': None}, f'id = {self.id}')
#
#     def get_target_id(self):
#         if self.current_target:
#             return self.current_target
#         else:
#             return None
#
#     def skip_turn(self):
#         current_bonus = self.ap + self.ap_bonus
#         self.data_manager.update('CHARS_COMBAT',{'ap_boonus': current_bonus}, f'id = {self.id}')
#         self.ap = 0
#
#     def attack_if_in_melee(self):
#         attacked_enemies = []
#
#         if self.melee_target_from:
#             for enemy_id in self.melee_target_from:
#                 if ActorCombat(enemy_id).get_current_weapons():
#                     ActorCombat(enemy_id, data_manager=self.data_manager).melee_attack(self.id, provoked=True)
#                 else:
#                     ActorCombat(enemy_id, data_manager=self.data_manager).race_attack(self.id, provoked=True)
#                 attacked_enemies.append(enemy_id)
#
#         if attacked_enemies:
#             return random.choice(attacked_enemies)
#         else:
#             return None
#
#     def attack_if_hunted(self):
#         attacked_enemies = []
#         if self.hunted_from:
#             for enemy_id in self.hunted_from:
#                 e_combat = ActorCombat(enemy_id, data_manager=self.data_manager)
#                 target = [self.id]
#
#                 if self.melee_target_from:
#                     target += self.melee_target_from
#
#                 if self.melee_target:
#                     target.append(self.melee_target)
#
#                 total_target = random.choice(target)
#                 e_combat.range_attack(total_target, provoked=True, ignore_cover=True)
#                 if total_target == self.id:
#                     attacked_enemies.append(enemy_id)
#
#         if attacked_enemies:
#             return attacked_enemies
#         else:
#             return None
#
#     def attack_if_supressers(self):
#         attacked_enemies = []
#         if self.supressed_from:
#             for enemy_id in self.supressed_from:
#                 ActorCombat(enemy_id, data_manager=self.data_manager).range_attack(self.id, provoked=True)
#
#                 attacked_enemies.append(enemy_id)
#
#         if attacked_enemies:
#             return attacked_enemies
#         else:
#             return None
#
#     def attack_if_contained(self):
#         attacked_enemies = []
#         if self.contained_from:
#             for enemy_id in self.contained_from:
#                 ActorCombat(enemy_id, data_manager=self.data_manager).range_attack(self.id, provoked=True)
#
#                 attacked_enemies.append(enemy_id)
#
#         if attacked_enemies:
#             return attacked_enemies
#         else:
#             return None
#
#     def check_character_owner(self):
#         c_owner = self.data_manager.select_dict('CHARS_INIT',filter=f'id = {self.id}')[0].get('owner', None)
#         if c_owner is not None:
#             return c_owner
#         else:
#             return None
#
#     def get_current_ammo(self, **kwargs):
#
#         if self.check_character_owner() is None:
#             return -1, None
#
#         c_weapon = kwargs.get('weapon_id', None)
#         if c_weapon is None:
#             return 0, None
#
#         if self.data_manager.check('CHARS_EQUIPMENT',f'item_id = {c_weapon}') is None:
#             return 0, None
#
#         c_bullets_id = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'item_id = {c_weapon}')[0]
#         if c_bullets_id:
#             return c_bullets_id.get('bullets'), c_bullets_id.get('ammo_id')
#
#     def get_actor_inventory(self):
#         from ArbItems import Inventory
#
#         c_inventory = Inventory.get_inventory_by_character(self.id, data_manager=self.data_manager)
#         if c_inventory:
#             return c_inventory.get_dict()
#         else:
#             return {}
#
#     def get_current_grenades(self):
#         from ArbAmmo import Ammunition
#         from ArbWeapons import HandGrenade
#
#         if self.check_character_owner() is None:
#             return None
#         else:
#             items = self.get_actor_inventory()
#             total_grenades = {}
#             for item in items:
#                 if items[item].Class == 'Граната':
#                     if Ammunition(items[item].Type, data_manager=self.data_manager).caliber == 'Граната':
#                         total_grenades[item] = HandGrenade(item, data_manager=self.data_manager)
#
#             return total_grenades
#
#     def use_grenade(self, grenade_id:int, value:int=None):
#         from ArbItems import Item
#
#         if not value:
#             value = 1
#
#         grenade = Item(grenade_id, data_manager=self.data_manager)
#         grenade.change_value(-value)
#
#     def use_ammo(self, value:int=None, **kwargs):
#
#         c_weapon = kwargs.get('weapon_id', None)
#         if c_weapon is None:
#             return None
#
#         if self.check_character_owner() is None:
#             return None
#         else:
#             c_ammo = self.get_current_ammo(weapon_id=c_weapon)
#             if c_ammo[0] != -1:
#                 self.data_manager.update('CHARS_EQUIPMENT', {'bullets': c_ammo[0] - value}, filter=f'item_id = {c_weapon}')
#
#     def reload(self, weapon_id:int=None, item_id:int=None):
#         from ArbWeapons import Weapon
#         if weapon_id is None:
#             weapon_id = self.get_current_weapons()
#         if not weapon_id:
#             return None, None
#         else:
#             weapon_id = random.choice(weapon_id)
#
#         c_weapon = Weapon(weapon_id, data_manager=self.data_manager)
#         if c_weapon.ReloadAPCost > self.ap:
#             return False, c_weapon
#         elif not c_weapon.can_be_reloaded():
#             return None, c_weapon
#         else:
#             self.ap_use(c_weapon.ReloadAPCost)
#             return c_weapon.reload(item_id), c_weapon
#
#     def weapon_attack_cost(self, weapon_id: int = None):
#         from ArbWeapons import Weapon
#         c_weapon_id = random.choice(self.get_current_weapons(weapon_id))
#         if c_weapon_id is None:
#             return math.inf
#         else:
#             return Weapon(c_weapon_id, data_manager=self.data_manager).ActionPoints
#
#     def race_attack_cost(self, attack_id:str = None):
#         from ArbHealth import RaceAttack
#         return RaceAttack(attack_id, data_manager=self.data_manager).cost
#
#     def calculate_height_delta(self, enemy_id:int):
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#
#         actor_height = Actor(self.id, data_manager=self.data_manager).calculate_total_height()
#         enemy_height = enemy.calculate_total_height()
#
#         total_height = abs(actor_height - enemy_height)
#
#         return total_height
#
#     def calculate_total_distance(self, enemy_id:int):
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#
#         total_height = self.calculate_height_delta(enemy_id)
#         layer_distance = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
#
#         return round(math.sqrt(total_height**2 + layer_distance**2))
#
#     def calculate_total_cover(self, enemy_id:int):
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#         enemy_cover = enemy.get_current_object().protection if enemy.current_object_id else 0
#         total_height = self.calculate_height_delta(enemy_id)
#
#         return enemy_cover - total_height
#
#     def range_attack(self, enemy_id:int, **kwargs):
#         from ArbCharacters import Character, Race
#         from ArbWeapons import Weapon
#
#         c_weapon = kwargs.get('weapon_id', None)
#         if c_weapon is None:
#             c_weapon = random.choice(self.get_current_weapons())
#
#         if self.check_if_current_weapon_melee(c_weapon):
#             return None, 'Вы понимаете что у вас нет оружия для дальней атаки'
#
#         c_ammo = self.get_current_ammo(weapon_id=c_weapon)
#         if c_ammo[0] == 0:
#             self.make_sound('Click', random.randint(10, 150))
#             return None, 'Вы слышите глухой щелчок и понимаете, что у вас закончились патроны'
#
#         c_cost = self.weapon_attack_cost(c_weapon)
#
#         if c_cost > self.ap and not kwargs.get('provoked', None):
#             return None, 'У вас нет сил и возможности атаковать противника'
#         elif kwargs.get('provoked', None):
#             pass
#         else:
#             self.ap_use(c_cost)
#
#         if self.melee_target_from:
#             c_enemies = self.attack_if_in_melee()
#             if c_enemies:
#                 enemy_id = c_enemies
#
#             if Weapon(c_weapon, data_manager=self.data_manager).Class not in ['SMG', 'PST', 'TUR', 'SG']:
#                 return self.melee_attack(enemy_id, provoked=True)
#
#         if self.hunted_from:
#             self.attack_if_hunted()
#             return None, 'Вы пытаетесь навестись на цель, но вас атакуют противники выцеливавшие вас всё это время'
#
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#         distance_to_enemy = self.calculate_total_distance(enemy_id)
#         e_cover = self.calculate_total_cover(enemy_id)
#         if e_cover >= 0:
#             enemy_coverage = random.randint(0, e_cover) if not kwargs.get('ignore_cover', False) else 0
#         else:
#             enemy_coverage = 0
#
#         enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size
#
#         enemy_attributes = {'distance': distance_to_enemy,
#                             'cover': enemy_coverage,
#                             'size': enemy_size,}
#
#         total_damage, total_attacks, weapon_loudness, damage_for_cover = RangeAttack(self.id, enemy_id, enemy_attributes=enemy_attributes, data_manager=self.data_manager).initiate(c_weapon)
#         #CharacterCombat(self.id, data_manager=self.data_manager).range_attack(c_weapon, enemy_id=enemy_id, enemy_distance= distance_to_enemy, enemy_cover= enemy_coverage,enemy_size= enemy_size, **kwargs)
#
#         if damage_for_cover > 0 and enemy.current_object_id:
#             enemy.get_current_object().recive_damage(damage_for_cover)
#
#         if total_attacks != 0:
#             if c_ammo[0] != -1:
#                 self.use_ammo(total_attacks, weapon_id=c_weapon)
#
#             for i in range(total_attacks):
#                 self.make_sound('GunShot', weapon_loudness)
#         else:
#             self.make_sound('Click', random.randint(10,150))
#
#         return total_damage, f'Вы целитесь, после чего {Weapon(c_weapon).Name} совершает несколько выстрелов!'
#
#     def melee_attack(self, enemy_id:int, **kwargs):
#         from ArbCharacters import Character, Race
#         from ArbWeapons import Weapon
#         from ArbAttacks import MeleeAttack
#
#         c_weapon = kwargs.get('weapon_id', None)
#         if c_weapon is None:
#             c_weapon = random.choice(self.get_current_weapons())
#
#         c_cost = self.weapon_attack_cost(c_weapon)
#
#         if c_cost > self.ap and not kwargs.get('provoked', None):
#             return None, 'У вас нет сил и возможности атаковать противника'
#         elif kwargs.get('provoked', None):
#             pass
#         else:
#             self.ap_use(c_cost)
#
#         #if self.melee_target_from:
#         #    c_enemies = self.attack_if_in_melee()
#         #    if c_enemies:
#         #        enemy_id = c_enemies
#
#         if self.hunted_from:
#             self.attack_if_hunted()
#             return None, 'Вы пытаетесь сблизиться с противником, но вас атакуют враги выцеливавшие вас всё это время'
#
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#         distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
#         if distance_to_enemy > 0:
#             return None, 'Вы понимаете, что противник находится слишком далеко для его атаки в ближнем бою'
#
#         e_cover = enemy.get_current_object()
#         if e_cover:
#             enemy_coverage = e_cover.protection
#         else:
#             enemy_coverage = 0
#
#         enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size
#
#         enemy_attributes = {'distance': distance_to_enemy,
#                             'cover': enemy_coverage,
#                             'size': enemy_size}
#
#         total_damage, total_attacks, weapon_loudness = MeleeAttack(self.id, enemy_id, enemy_attributes=enemy_attributes,
#                                                                    data_manager=self.data_manager).initiate(c_weapon)
#
#         if total_attacks != 0:
#             for i in range(total_attacks):
#                 self.make_sound('Fight', weapon_loudness)
#
#         return total_damage, f'Вы встаёте в боевую стойку, после чего замахиваете {Weapon(c_weapon).Name} и наносите несколько ударов!'
#
#     def race_attack(self, enemy_id:int, **kwargs):
#         from ArbCharacters import Character, Race
#         from ArbHealth import RaceAttack
#         from ArbAttacks import BodyPartAttack
#
#         c_attack = kwargs.get('attack_id', None)
#
#         if not c_attack:
#             c_attack = random.choice(Body(self.id, data_manager=self.data_manager).available_attacks())
#
#         c_cost = self.race_attack_cost(c_attack)
#
#         if c_cost > self.ap and not kwargs.get('provoked', None):
#             return None, 'У вас нет сил и возможности атаковать противника'
#         elif kwargs.get('provoked', None):
#             pass
#         else:
#             self.ap_use(c_cost)
#
#         if self.melee_target_from:
#             c_enemies = self.attack_if_in_melee()
#             if c_enemies:
#                 enemy_id = c_enemies
#
#         if self.hunted_from:
#             self.attack_if_hunted()
#             return None, 'Вы пытаетесь совершить атаку, но вас атакуют противники выцеливавшие вас всё это время'
#
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#         distance_to_enemy = self.calculate_total_distance(enemy_id)
#
#         if RaceAttack(c_attack, data_manager=self.data_manager).range < distance_to_enemy:
#             return None, 'Вы понимаете, что расстояния между вами и противником слишком велико для совершения данной атаки'
#
#         e_cover = self.calculate_total_cover(enemy_id)
#
#         enemy_size = Race(Character(enemy_id, data_manager=self.data_manager).Race, data_manager=self.data_manager).Size
#
#         enemy_attributes = {'distance': distance_to_enemy,
#                             'cover': e_cover,
#                             'size': enemy_size}
#
#         total_damage, total_attacks = BodyPartAttack(self.id, enemy_id, enemy_attributes=enemy_attributes, data_manager=self.data_manager).initiate(c_attack)
#
#         self.make_sound('Fight', random.randint(10, 150))
#
#         return total_damage, f'Вы готовитесь и совершаете {RaceAttack(c_attack).name.lower()} атакуя своего противника'
#
#     def make_sound(self, sound_id:str, volume:int=None):
#         volume = volume if volume is not None else random.randint(10,150)
#
#         Actor(self.id, data_manager=self.data_manager).make_sound(sound_id, volume)
#
#     def throw_grenade(self, enemy_id:int, **kwargs):
#         from ArbAmmo import Grenade
#         from ArbAttacks import Explosion
#
#         if kwargs.get('grenade_id', None) is not None:
#             if not self.get_current_grenades():
#                 return None, 'У вас нет кончились гранаты!'
#             else:
#                 if kwargs.get('grenade_id', None) in self.get_current_grenades():
#                     current_grenade = self.get_current_grenades()[kwargs.get('grenade_id')]
#                 else:
#                     return None, 'У вас нет такой гранаты'
#
#         else:
#             if self.check_character_owner() is not None:
#                 if self.get_current_grenades():
#                     current_grenade = random.choice(list(self.get_current_grenades().values()))
#                 else:
#                     return None, 'У вас нет гранат, которые вы можете использовать'
#             else:
#                 grenades_types = [i.get('id') for i in self.data_manager.select_dict('AMMO', filter=f'caliber = "Граната"')]
#                 current_grenade = Grenade(random.choice(grenades_types), data_manager=self.data_manager)
#
#
#         c_cost = 3
#
#         if c_cost > self.ap and not kwargs.get('provoked', None):
#             return None, 'У вас нет сил и возможности атаковать противника'
#         elif kwargs.get('provoked', None):
#             pass
#         else:
#             self.ap_use(c_cost)
#
#         if self.melee_target_from:
#             self.attack_if_in_melee()
#             return None, 'Вы пытаетесь достать гранату, но это замечают противники находящиеся рядом с вами и атакуют!'
#
#         if self.hunted_from:
#             self.attack_if_hunted()
#             return None, 'Вы пытаетесь достать гранату, но вас атакуют противники выцеливавшие вас всё это время'
#
#         if self.check_character_owner() is not None:
#             self.use_grenade(current_grenade.ID)
#
#         enemy = Actor(enemy_id, data_manager=self.data_manager)
#         distance_to_enemy = Actor(self.id, data_manager=self.data_manager).distance_to_layer(enemy.current_layer_id)
#         if distance_to_enemy > 60:
#             return None
#
#         main_target = [enemy_id]
#         maybe_damaged = []
#
#         e_cover = enemy.get_current_object()
#         if e_cover:
#             main_target += [i for i in e_cover.current_characters() if i != enemy_id]
#
#         current_delta = Actor(self.id, data_manager=self.data_manager).get_current_battle().distance_delta
#         current_layer = Actor(self.id, data_manager=self.data_manager).get_current_layer().id
#         grenade_layers = current_grenade.get_damaged_layers(current_delta, current_layer)
#
#         c_battle_layers_ids = Actor(self.id, data_manager=self.data_manager).get_current_battle().layers.keys()
#
#         for layer in grenade_layers:
#             if layer in c_battle_layers_ids:
#                 maybe_damaged += Layer(layer, Actor(self.id, data_manager=self.data_manager).current_battle_id, data_manager=self.data_manager).characters_not_in_cover()
#
#         total_damage, current_loud, damage_for_cover = Explosion(main_target, maybe_damaged, data_manager=self.data_manager).initiate(current_grenade)
#         self.make_sound('Explosion', current_loud)
#
#         if e_cover:
#             e_cover.recive_damage(damage_for_cover)
#
#         return total_damage, f'Вы одергиваете чеку и бросаете гранату ({current_grenade.name}) в своего противника'
#
#
# class Actor:
#     def __init__(self, id:int, **kwargs):
#         self.id = id
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         battle_data = self.fetch_battle_data()
#         self.current_battle_id = battle_data.get('battle_id', None)
#         self.current_layer_id = battle_data.get('layer_id', None)
#         self.current_object_id = battle_data.get('object', None)
#         self.team_id = battle_data.get('team_id', None)
#
#         self.height = battle_data.get('height', 0) if battle_data.get('height', 0) is not None else 0
#         self.max_view_distance = self.distance_of_view()
#
#         self.initiative = battle_data.get('initiative', 0)
#         self.is_active = battle_data.get('is_active', None)
#
#         self.actor_attributes = self.fetch_attributes()
#
#         self.height = battle_data.get('height', 0) if battle_data.get('height', 0) is not None else 0
#
#     def get_max_movement(self):
#         c_movement = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Movement')
#         return round(1 + (c_movement / 50))
#
#     def get_nearby_layers_id(self):
#         forward = self.current_layer_id + 1
#         back = self.current_layer_id - 1
#         if back < 0:
#             back = None
#
#         if forward > max(self.get_current_battle().layers.keys()):
#             forward = None
#
#         return [back, forward]
#
#     def trap_checking(self):
#         from ArbWeapons import Trap
#         from ArbAttacks import CombatManager
#
#         current_traps = self.get_current_layer().get_traps()
#         if not current_traps:
#             return None
#
#         character_attributes = CharacterAttributes(self.id, data_manager=self.data_manager)
#
#         checking_count = len(current_traps)//3 if len(current_traps) > 3 else 1
#         activations = []
#
#         for _ in range(checking_count):
#             character_analysis = character_attributes.check_skill('Analysis')
#             character_movement = character_attributes.check_skill('Movement')
#             character_reaction = character_attributes.check_characteristic('Реакция')
#
#             c_trap: Trap = random.choice(current_traps)
#
#             if c_trap.check_activation(character_analysis, character_movement, character_reaction):
#                 activations += c_trap.explode()
#
#         total_damage = CombatManager(data_manager=self.data_manager).calculate_total_damage(activations, self.id)
#         CombatManager(data_manager=self.data_manager).recive_damage(self.id, total_damage=total_damage, apply_effect=True)
#
#         return total_damage
#
#     def move_forward(self):
#         c_slots = self.get_nearby_layers_id()
#         if c_slots[1] is None:
#             return False
#
#         c_cost = self.movement_cost()
#         if c_cost > self.actor_attributes.ap:
#             return False
#         else:
#             self.actor_attributes.use_movement_points(1)
#             self.actor_attributes.ap_use(c_cost)
#
#             if self.height == 0:
#                 self.trap_checking()
#
#             self.set_layer(c_slots[1])
#             return True
#
#     def move_back(self):
#         c_slots = self.get_nearby_layers_id()
#         if c_slots[0] is None:
#             return False
#
#         c_cost = self.movement_cost()
#         if c_cost > self.actor_attributes.ap:
#             return False
#         else:
#             self.actor_attributes.use_movement_points(1)
#             self.actor_attributes.ap_use(c_cost)
#
#             if self.height == 0:
#                 self.trap_checking()
#
#             self.set_layer(c_slots[0])
#             return True
#
#     def steps_volume(self):
#         basic_roll = random.randint(10, 200)
#         stealth_mod = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Скрытность') * 0.5
#         return basic_roll - stealth_mod if basic_roll - stealth_mod > 10 else 10
#
#     def move_to_layer(self, layer_id:int):
#         if layer_id not in self.get_current_battle().layers.keys():
#             return False
#
#         if self.current_layer_id == layer_id:
#             return False
#
#         if self.actor_attributes.melee_target_from:
#             self.actor_attributes.attack_if_in_melee()
#             if random.randint(0, 100) > random.randint(0, 100):
#                 return False
#
#         steps_volume = self.steps_volume()
#
#         self.remove_cover()
#         if self.actor_attributes.get_melee_target_from():
#             self.actor_attributes.flee_from_melee()
#
#         if self.current_layer_id < layer_id:
#             for _ in range(layer_id-self.current_layer_id):
#                 if self.move_forward():
#                     self.make_sound('Steps', steps_volume)
#         elif self.current_layer_id > layer_id:
#             for _ in range(self.current_layer_id-layer_id):
#                 if self.move_back():
#                     self.make_sound('Steps', steps_volume)
#
#         return self.current_layer_id
#
#     def make_sound(self, sound_id:str, volume:int=None):
#         prompt = {'id': self.data_manager.maxValue('BATTLE_SOUNDS','id')+1,
#                   'battle_id': self.current_battle_id,
#                   'actor_id': self.id,
#                   'layer_id': self.current_layer_id,
#                   'sound_id': sound_id,
#                   'round': self.get_current_battle().round,
#                   'volume': volume if volume else random.randint(50,150)}
#
#         self.data_manager.insert('BATTLE_SOUNDS', prompt)
#
#     def detect_sound_source(self, sound_id:int):
#         from ArbRoll import RollCapacity
#         if self.actor_attributes.ap < 1:
#             return False
#         else:
#             self.actor_attributes.ap_use(1)
#
#         c_battle = self.get_current_battle()
#
#         c_sound = InBattleSound(sound_id, data_manager=self.data_manager)
#         c_distance = self.distance_to_layer(c_sound.layer_id)
#         c_chance = c_sound.get_detection_chance(c_distance, c_battle.round)
#         c_hearing = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Слух')
#         c_hearing = RollCapacity(c_hearing).dice//2
#
#         roll = CharacterAttributes(self.id, data_manager=self.data_manager).roll_skill('Analysis', difficulty=100-c_chance+c_battle.time.noise+c_battle.weather.noise, buff=c_hearing)
#
#         if roll[0]:
#             self.take_target(c_sound.actor_id)
#             return c_sound.actor_id
#         else:
#             return False
#
#     def list_of_sounds(self):
#         c_list = self.data_manager.select_dict('BATTLE_SOUNDS', filter=f'battle_id = {self.current_battle_id} AND actor_id != {self.id}')
#         return [InBattleSound(sound.get('id'), data_manager=self.data_manager) for sound in c_list]
#
#     def fetch_attributes(self):
#         return ActorCombat(self.id, data_manager=self.data_manager)
#
#     def fetch_battle_data(self):
#         if self.data_manager.check('BATTLE_CHARACTERS',f'character_id = {self.id}') is None:
#             return {}
#         else:
#             return self.data_manager.select_dict('BATTLE_CHARACTERS',filter=f'character_id = {self.id}')[0]
#
#     def get_current_layer(self):
#         if self.current_layer_id is not None:
#             return Layer(self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
#         else:
#             return None
#
#     def get_current_object(self):
#         if self.current_object_id is not None:
#             return GameObject(self.current_object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
#         else:
#             return None
#
#     def get_current_battle(self):
#         if self.current_battle_id is not None:
#             return Battlefield(self.current_battle_id)
#         else:
#             return None
#
#     def take_target(self, enemy_id:int):
#         all_contacts = self.get_all_visible_characters_id()
#         if enemy_id in all_contacts:
#             return ActorCombat(self.id, data_manager=self.data_manager).set_target(enemy_id)
#         else:
#             return False
#
#     def take_supression(self, layer_id:int=None):
#         return ActorCombat(self.id, data_manager=self.data_manager).supress_enemy(layer_id)
#
#     def take_contain(self, enemy_id:int=None):
#         return ActorCombat(self.id, data_manager=self.data_manager).contain_enemy(enemy_id)
#
#     def take_hunt(self, enemy_id:int=None):
#         return ActorCombat(self.id, data_manager=self.data_manager).hunt_enemy(enemy_id)
#
#     def get_ready(self):
#         return ActorCombat(self.id, data_manager=self.data_manager).get_prepared()
#
#     def skip_turn(self):
#         ActorCombat(self.id, data_manager=self.data_manager).skip_turn()
#         self.set_unactive()
#
#     def movement_cost(self):
#         skill = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Передвижение')
#         c_movement = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Перемещение')
#         c_delta = self.get_current_battle().distance_delta / 50
#         if c_movement <= 0:
#             return None
#         else:
#             move_factor = (200-c_movement)/100
#
#         c_difficulty = self.get_current_layer().terrain.movement_difficulty
#         c_base_cost = self.get_current_layer().terrain.movement_cost
#
#         return round((1+(c_difficulty - skill)/100) * move_factor * c_base_cost * c_delta)
#
#     def calculate_slot_disguise(self, slot_name: str):
#         from ArbClothes import Clothes, CharacterArmors
#
#         c_clothes_id = CharacterArmors(self.id, data_manager=self.data_manager).armors_id().get(slot_name, {})
#
#         total_calculation = 0
#         for armor_id in c_clothes_id.values():
#             total_calculation += Clothes(armor_id).cloth_disguise()
#
#         return total_calculation
#
#     def calculate_clothes_disguise(self):
#         from ArbClothes import CharacterArmors
#         from ArbClothes import Clothes
#
#         c_clothes_id = CharacterArmors(self.id, data_manager=self.data_manager).armors_id()
#         c_slots_disguise = {}
#         total_disguise = 0
#
#         for c_slot, armor_ids in c_clothes_id.items():
#             slot_disguise = sum(Clothes(armor_id).cloth_disguise() for armor_id in armor_ids.values())
#             c_slots_disguise[c_slot] = slot_disguise
#             total_disguise += slot_disguise
#
#         if total_disguise == 0 or len(c_clothes_id) == 0:
#             return 0
#         else:
#             return round(total_disguise / len(c_clothes_id))
#
#     def actor_disguise(self):
#         battle = self.get_current_battle()
#         layer = self.get_current_layer()
#         current_object = self.get_current_object()
#
#         if battle is None or layer is None:
#             return 0
#
#         # Сокращение количества запросов к базе данных
#         char_data = self.data_manager.select_dict('CHARS_INIT', filter=f'id = {self.id}')[0]
#         race = char_data.get('race')
#         race_disguise = Race(race, data_manager=self.data_manager).NatureDisguise
#
#         # Предполагается, что эти методы относительно быстрые
#         clothes_disguise = self.calculate_clothes_disguise()
#         stealth_skill = CharacterAttributes(self.id, data_manager=self.data_manager).check_skill('Скрытность')
#
#         # Локальные переменные для вычислений
#         weather_visibility = battle.weather.visibility
#         daytime_visibility = battle.time.visibility
#         terrain_visibility = layer.terrain.visibility
#         object_disguise = current_object.coverage if current_object else 0
#
#         # Вычисление disguise
#         weather_disguise = 1 + (100 - weather_visibility) / 100
#         daytime_disguise = 1 + (100 - daytime_visibility) / 100
#         terrain_disguise = 1 + (100 - terrain_visibility) / 100
#         stealth_mod = 1 + stealth_skill * 0.005
#
#         total_disguise = (race_disguise + clothes_disguise + object_disguise) * weather_disguise * terrain_disguise * daytime_disguise * stealth_mod
#
#         return round(total_disguise, 2)
#
#     def distance_of_view(self):
#         c_eyes = Body(self.id, data_manager=self.data_manager).physical_stat('Зрение')/100
#         height_bonus = 1 + math.sqrt(self.calculate_total_height()) / 5 if self.calculate_total_height() > 0 else 1 - math.sqrt(abs(self.calculate_total_height())) / 5
#         basic_view = 5400 * height_bonus
#         c_battle = self.get_current_battle()
#         if c_battle is None:
#             time_factor = 1
#             weather_factor = 1
#         else:
#             time_factor = c_battle.time.visibility/100
#             weather_factor = c_battle.weather.visibility/100
#
#         return basic_view * c_eyes * time_factor * weather_factor
#
#     def basic_layer_vigilance(self, current_layer: int, target_layer: int, distance_delta:float):
#         total_distance = abs(target_layer - current_layer) * distance_delta
#         return round((self.max_view_distance - total_distance) / self.max_view_distance * 100, 2) if current_layer != target_layer else 100
#
#     def battle_layers_vigilance(self):
#         c_battle = self.get_current_battle()
#         c_layer_id = self.current_layer_id
#         c_battle_layers = c_battle.layers
#         c_battle_layers_id = set(c_battle.layers.keys())
#         c_delta = c_battle.distance_delta
#
#         current_height = self.calculate_total_height()
#
#         layers_vigilance = {}
#         cached_results = {}
#
#         for i in reversed([i for i in c_battle_layers_id if i < c_layer_id]):  # обратный проход по слоям
#             if i in layers_vigilance:
#                 break
#
#             if i in cached_results:
#                 layers_vigilance[i] = cached_results[i]
#             else:
#                 vigilance = self.basic_layer_vigilance(c_layer_id, i, c_delta)
#                 if vigilance <= 0:
#                     break
#                 layers_vigilance[i] = vigilance
#                 cached_results[i] = vigilance
#
#             if c_battle_layers[i].terrain.coverage and i != c_layer_id:
#                 if current_height - c_battle_layers[i].total_height() > 10:
#                     continue
#                 else:
#                     break
#             if c_battle_layers[i].total_height() - current_height >= 5:
#                 break
#
#         for i in [i for i in c_battle_layers_id if i >= c_layer_id]: # проход по слоям
#             if i in layers_vigilance:
#                 break
#
#             if i in cached_results:
#                 layers_vigilance[i] = cached_results[i]
#             else:
#                 vigilance = self.basic_layer_vigilance(c_layer_id, i, c_delta)
#                 if vigilance <= 0:
#                     break
#                 layers_vigilance[i] = vigilance
#                 cached_results[i] = vigilance
#
#             if c_battle_layers[i].terrain.coverage and i != c_layer_id:
#                 if current_height - c_battle_layers[i].total_height() > 10:
#                     continue
#                 else:
#                     break
#             if c_battle_layers[i].total_height() - current_height >= 5:
#                 break
#
#         return layers_vigilance
#
#     def get_characters_on_layer(self, layer_id:int=None):
#         c_layer = layer_id if layer_id is not None else self.current_layer_id
#         if not self.data_manager.check('BATTLE_CHARACTERS',f'layer_id = {c_layer} AND battle_id = {self.current_battle_id}'):
#             return []
#         else:
#             return [Unit(charac.get('character_id')) for charac in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'layer_id = {c_layer} AND battle_id = {self.current_battle_id}')]
#
#     def get_visible_characters_on_layer(self, layer_id:int=None, vigilance: float = None):
#         c_layer = layer_id if layer_id is not None else self.current_layer_id
#         c_characters = self.get_characters_on_layer(layer_id)
#         c_visibility = self.battle_layers_vigilance().get(c_layer, 0) if not vigilance else vigilance
#         if not c_characters:
#             return []
#         else:
#             total_characters = [character for character in c_characters if not( character.id == self.id or character.disguise(self.data_manager) >= c_visibility)]
#
#             return total_characters
#
#     def get_visibile_characters_id(self):
#         total_characters = {}
#         layers = self.battle_layers_vigilance()
#         layers_has_units = set([layer.get('layer_id') for layer in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.current_battle_id}')])
#
#         for layer in layers_has_units:
#             if layer in layers:
#                 total_characters[layer] = self.get_visible_characters_on_layer(layer, vigilance=layers[layer])
#             else:
#                 continue
#
#         return total_characters
#
#     def get_all_visible_characters_id(self):
#         c_characters = self.get_visibile_characters_id()
#         total_chars = []
#         for i in c_characters.keys():
#             total_chars += c_characters[i]
#
#         return total_chars
#
#     def enemies_disguise(self):
#         total_units = self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.current_battle_id} AND character_id != {self.id} AND team_id!= {self.team_id}')
#         total_characters = {unit.get('character_id'): Unit(unit.get('character_id')).disguise(self.data_manager) for unit in total_units}
#         return total_characters
#
#     def get_visible_characters(self):
#         # Получаем видимость всех слоев
#         layers_vigilance = self.battle_layers_vigilance()
#
#         # Получаем всех персонажей в бою и их маскировку
#         all_characters = self.data_manager.select_dict('BATTLE_CHARACTERS',
#                                                        filter=f'battle_id = {self.current_battle_id} AND character_id != {self.id}')
#
#         # Создаем словарь для хранения видимых персонажей по слоям
#         visible_characters_by_layer = {}
#
#         # Создаем словарь для кэширования вычислений видимости
#         calculated_visibility = {}
#
#         for char_data in all_characters:
#             char_id = char_data['character_id']
#             layer_id = char_data['layer_id']
#             team_id = char_data['team_id']
#             disguise = Unit(char_id).disguise(self.data_manager)
#
#             if layer_id not in visible_characters_by_layer:
#                 visible_characters_by_layer[layer_id] = []
#
#             if team_id == self.team_id:
#                 # Добавляем всех союзников в видимые персонажи
#                 visible_characters_by_layer[layer_id].append(char_id)
#             else:
#                 # Проверяем кэш для текущего слоя
#                 if layer_id in calculated_visibility:
#                     vigilance = calculated_visibility[layer_id]
#                 else:
#                     vigilance = layers_vigilance.get(layer_id, 0)
#                     calculated_visibility[layer_id] = vigilance
#
#                 # Проверяем видимость для вражеских персонажей
#                 if disguise < vigilance:
#                     visible_characters_by_layer[layer_id].append(char_id)
#
#         return visible_characters_by_layer
#
#     def distance_to_layer(self, layer_id:int):
#         c_distance_delta = self.get_current_battle().distance_delta
#         move_iterable = abs(layer_id - self.current_layer_id)
#         distance = c_distance_delta * move_iterable
#
#         return distance
#
#     def move_to_object(self, object_id:int=None):
#         layer_objects = self.get_current_layer().objects
#         if object_id not in layer_objects.keys() and object_id is not None:
#             return False
#
#         if object_id:
#             if GameObject(object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager).available_slots <= 0:
#                 return False
#
#         c_cost = round(self.movement_cost() * 0.5)
#         if c_cost > self.actor_attributes.ap:
#             return False
#         else:
#             if self.actor_attributes.melee_target_from:
#                 self.actor_attributes.attack_if_in_melee()
#                 if random.randint(0, 100) > random.randint(0, 100):
#                     return False
#             self.remove_cover()
#             self.actor_attributes.ap_use(c_cost)
#             if object_id is not None:
#                 self.set_cover(object_id)
#             self.make_sound('Steps', self.steps_volume())
#             if self.actor_attributes.get_melee_target_from():
#                 self.actor_attributes.flee_from_melee()
#
#             if self.height == 0:
#                 self.trap_checking()
#             else:
#                 self.set_height(0)
#
#             return True
#
#     def roll_initiative(self, **kwargs):
#         battle_baffs = 0
#
#         pain = Body(self.id, data_manager=self.data_manager).calculate_total_pain()
#         agility = CharacterAttributes(self.id, data_manager=self.data_manager).check_characteristic('Ловкость')
#         reaction = CharacterAttributes(self.id, data_manager=self.data_manager).check_characteristic('Реакция')
#         lvl = CharacterAttributes(self.id, data_manager=self.data_manager).check_progress().get('lvl', 1)
#
#         mind = CharacterAttributes(self.id, data_manager=self.data_manager).check_capacity('Сознание')
#         if mind < 30:
#             mind = 30
#
#         rolls = []
#         for _ in range(lvl):
#             c_roll = random.randint(kwargs.get('min',0) + kwargs.get('min_bonus',0), kwargs.get('max', 100)) + kwargs.get('max_bonus',0)
#             rolls.append(c_roll)
#         total_roll = max(rolls)
#
#         return round(((agility+reaction)/2 + battle_baffs) * (mind/100) + total_roll)
#
#     def set_initiative(self, **kwargs):
#         if self.data_manager.check('BATTLE_CHARACTERS',f'character_id = {self.id}') is None:
#             return None
#         else:
#             c_roll = kwargs.get('initiative', self.roll_initiative(**kwargs))
#             self.data_manager.update('BATTLE_CHARACTERS',{'initiative': c_roll}, f'character_id = {self.id}')
#             self.initiative = c_roll
#
#     def set_active(self):
#         self.data_manager.update('BATTLE_CHARACTERS',{'is_active': 1}, f'character_id = {self.id}')
#
#     def set_unactive(self):
#         self.data_manager.update('BATTLE_CHARACTERS',{'is_active': None}, f'character_id = {self.id}')
#
#     def set_done_active(self):
#         self.data_manager.update('BATTLE_CHARACTERS',{'is_active': 0}, f'character_id = {self.id}')
#
#     def set_team(self, team_id:int=None, team_label:str=None):
#         if team_id is not None:
#             if self.data_manager.check('BATTLE_TEAMS',f'team_id = {team_id} AND battle_id = {self.current_battle_id}') is None:
#                 return None
#             else:
#                 self.data_manager.update('BATTLE_CHARACTERS',{'team_id': team_id}, filter=f'character_id = {self.id}')
#                 self.team_id = team_id
#         else:
#             if self.data_manager.check('BATTLE_TEAMS',f'label = "{team_label}" AND battle_id = {self.current_battle_id}') is None:
#                 return None
#             else:
#                 team_id = self.data_manager.select_dict('BATTLE_TEAMS',filter=f'label = "{team_label}" AND battle_id = {self.current_battle_id}')
#                 self.data_manager.update('BATTLE_CHARACTERS', {'team_id': team_id}, filter=f'character_id = {self.id}')
#                 self.team_id = team_id
#
#     def remove_cover(self):
#         self.data_manager.update('BATTLE_CHARACTERS',{'object': None},f'character_id = {self.id}')
#
#     def set_cover(self, cover_id:int):
#         if not self.data_manager.check('BATTLE_OBJECTS',f'battle_id = {self.current_battle_id} AND layer_id = {self.current_layer_id} AND object_id = {cover_id}'):
#             return False
#         else:
#             if GameObject(cover_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager).available_slots <= 0:
#                 return False
#             else:
#                 self.current_object_id = cover_id
#                 self.data_manager.update('BATTLE_CHARACTERS',{'object': cover_id}, f'character_id = {self.id}')
#
#     def set_layer(self, layer_id:int):
#         self.data_manager.update('BATTLE_CHARACTERS', {'layer_id': layer_id}, f'character_id = {self.id}')
#         self.current_layer_id = layer_id
#
#     def lookout(self):
#         from ArbCharacters import InterCharacter
#         total_text = ''
#         visible_layers = self.battle_layers_vigilance()
#         for i in sorted(visible_layers.keys()):
#             c_layer = Layer(i, self.current_battle_id, data_manager=self.data_manager)
#             total_text += f'\n\n**Слой {i} ({c_layer.label if c_layer.label else c_layer.terrain.label})**{"" if i != self.current_layer_id else " ``<--- Вы находитесь здесь!``"} {c_layer.describe()}'
#             characters = self.get_visible_characters_on_layer(i)
#             if characters:
#                 total_text += '. Здесь вы видите силуэты'
#                 for character in characters:
#                     total_text += f', ``id:{character.id}`` ({Race(InterCharacter(character.id, data_manager=self.data_manager).race).Name})'
#
#         return total_text
#
#     def turn_number(self):
#         current_actor = Battlefield(self.current_battle_id, data_manager=self.data_manager).actor_turn_index(self.id)+1
#         return current_actor
#
#     def current_turn(self):
#         current_actor = Battlefield(self.current_battle_id, data_manager=self.data_manager).current_turn_index()+1
#         return current_actor
#
#     def combat_info(self):
#         data = ActorCombat(self.id, data_manager=self.data_manager)
#         layer = Layer(self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
#         cover = self.get_current_object() if self.current_object_id else None
#         team = BattleTeam(self.team_id, self.current_battle_id, data_manager=self.data_manager) if self.team_id is not None else None
#
#         melee = f'\n> *Вас атакуют в ближнем бою:* ``{data.melee_target_from}``' if data.melee_target_from else ''
#         hunt = f'\n> *Вы выцеливаете:* ``id:{data.hunted}``' if data.hunted else ''
#         contain = f'\n> *Вы подавляете слой:* ``{data.contained}``' if data.contained else ''
#         overwatch = f'\n> *Вы находитесь в дозоре и готовы отразить атаку...*' if data.ready else ''
#
#
#         total_text = f'''
# <:action_points:1251239084144197696> **Очки Действия:** ``{data.ap} ОД. {f'({data.ap_bonus:+} ОД.)' if data.ap_bonus else ''}``
# > *Команда:*   ``{team.label if team else 'Отсутствует'}``
# > *Текущий слой:*  ``{layer.label if layer.label else layer.terrain.label} ({layer.id}) {'``!!! Подавляется огнём !!!``' if data.contained_from else ''}``
# > *Укрытие:*   ``{f'{cover.label} ({cover.id}) — {cover.protection:+.1f}%' if cover else 'Отсутствует'}``
# > *Номер хода:* ``{self.turn_number()} (текущий {self.current_turn()})``
#
# <:target:1251276620384305244> **Текущая цель:** ``{f'id:{data.current_target}' if data.current_target else 'Отсутствует'}``
# {f'> *Ближний бой:* ``{data.melee_target}``' if data.melee_target else ''} {overwatch if overwatch else ''}{melee if melee else ''}{hunt if hunt else ''}{contain if contain else ''}
#
# '''
#         return total_text
#
#     def set_melee_target(self, enemy_id: int):
#         if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {enemy_id} AND battle_id = {self.current_battle_id} AND layer_id = {self.current_layer_id}'):
#             if Actor(enemy_id, data_manager=self.data_manager).height > 0:
#                 return False
#
#             if self.height:
#                 self.set_height(0)
#
#             return ActorCombat(self.id, data_manager=self.data_manager).set_melee_target(enemy_id)
#         else:
#             return False
#
#     def range_attack(self, enemy_id:int=None, weapon_id:int=None):
#         enemy_id = enemy_id if enemy_id is not None else None
#         if enemy_id is None and self.actor_attributes.current_target:
#             enemy_id = self.actor_attributes.current_target
#
#         if enemy_id is not None:
#             return ActorCombat(self.id, data_manager=self.data_manager).range_attack(enemy_id, weapon_id=weapon_id)
#         else:
#             return False
#
#     def melee_attack(self, enemy_id:int=None, weapon_id:int=None):
#         enemy_id = enemy_id if enemy_id else None
#         if enemy_id not in self.actor_attributes.melee_target_from:
#             enemy_id = None
#         if not enemy_id and self.actor_attributes.melee_target:
#             enemy_id = self.actor_attributes.melee_target
#         if not enemy_id and self.actor_attributes.melee_target_from:
#             enemy_id = random.choice(self.actor_attributes.melee_target_from)
#
#         if enemy_id:
#             return ActorCombat(self.id, data_manager=self.data_manager).melee_attack(enemy_id, weapon_id=weapon_id)
#         else:
#             return False
#
#     def race_attack(self, enemy_id:int=None, attack_id:str=None):
#         enemy_id = enemy_id if enemy_id else None
#         if not enemy_id and self.actor_attributes.current_target:
#             enemy_id = self.actor_attributes.current_target
#
#         if enemy_id:
#             return ActorCombat(self.id, data_manager=self.data_manager).race_attack(enemy_id, attack_id=attack_id)
#         else:
#             return False
#
#     def throw_grenade(self, enemy_id:int=None, grenade_id:int=None):
#         enemy_id = enemy_id if enemy_id else None
#         if not enemy_id and self.actor_attributes.current_target:
#             enemy_id = self.actor_attributes.current_target
#
#         if enemy_id:
#             return ActorCombat(self.id, data_manager=self.data_manager).throw_grenade(enemy_id, grenade_id=grenade_id)
#         else:
#             return False
#
#     def reload(self, weapon_id:int=None, item_id:int=None):
#         return self.actor_attributes.reload(weapon_id=weapon_id, item_id=item_id)
#
#     def calculate_total_height(self):
#         layer_height = self.get_current_layer().total_height() if self.current_layer_id is not None else 0
#         object_height = self.get_current_object().height if self.current_object_id is not None else 0
#         self_height = self.height
#
#         return layer_height + object_height + self_height
#
#     def set_height(self, height:int):
#         if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {self.id}'):
#             query = {'height': self.height + height}
#             self.height = self.height + height
#             self.data_manager.update('BATTLE_CHARACTERS', query, f'character_id = {self.id}')
#
#     def fly_height(self, height:int):
#         from ArbHealth import Body
#         from ArbItems import CharacterEquipment
#
#         stats = Body(self.id, data_manager=self.data_manager).physical_stats()
#         armors_skills = CharacterEquipment(self.id, data_manager=self.data_manager).armors_skills()
#         stat_value = stats.get('Полет', 0) if 'Полет' in stats else -1
#         skill_value = armors_skills.get('Полет', 0) if 'Полет' in armors_skills else -1
#
#         if stat_value <= 0 and skill_value <= 0:
#             return False, 'Вы не можете летать'
#
#         total_value = skill_value if stat_value > stat_value else skill_value
#
#         cost = round((height // 10) * ((200 - total_value)/100))
#
#         if height <= 0:
#             return False, 'Вы не можете уйти под землю'
#
#         if cost <= 0 and height > 0:
#             cost = 1
#
#         if self.actor_attributes.ap < cost:
#             return False, 'У вас нет времени и сил, чтобы изменить свою высоту'
#         else:
#             self.remove_cover()
#             self.actor_attributes.ap_use(cost)
#             self.actor_attributes.clear_statuses()
#             self.set_height(height)
#             return True, f'Вы взмываете выше в воздух на {height}м.!'
#
#     def interact_with_current_object(self, **kwargs):
#         if not self.current_object_id:
#             return None, f'Вы не находитесь рядом с объектом, с которым можно взаимодействовать'
#
#         if self.actor_attributes.ap < 2:
#             return None, f'У вас нет сил и времени для того чтобы взаимодействовать с объектом'
#
#
#         obj = GameObject(self.current_object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
#
#         if not obj.effect_id:
#             return None, f'С этим объектом невозможно взаимодействовать'
#         elif obj.enemy_in_object(self.id):
#             return None, f'Вы не можете взаимодействовать с объектом пока рядом находится противник'
#         elif obj.current_uses <= 0:
#             self.actor_attributes.ap_use(2)
#             return None, f'С данным объектом больше нельзя взаимодействовать'
#         else:
#             self.actor_attributes.ap_use(2)
#             obj.count_uses(1)
#             return obj.interaction(self.id, enemy_id=kwargs.get('enemy_id'))
#
#     def capture_object(self):
#         if not self.current_object_id:
#             return None, f'Вы не находитесь рядом с объектом, который можно захватить'
#
#         if self.actor_attributes.ap < 2:
#             return None, f'У вас нет сил и времени для того чтобы захватить объект'
#
#         obj = GameObject(self.current_object_id, self.current_layer_id, self.current_battle_id, data_manager=self.data_manager)
#
#         if not obj.can_be_captured:
#             return None, f'Данный объект невозможно захватить'
#         elif obj.enemy_in_object(self.id):
#             return None, f'Вы не можете захватить объект пока рядом находится противник'
#         elif self.team_id is None:
#             return None, f'У вас нет команды, вы не можете захватывать объекты'
#         elif self.team_id == obj.captured:
#             return None, f'Данный объект уже захвачен вашей командой'
#         else:
#             self.actor_attributes.ap_use(2)
#             obj.get_captured(self.team_id)
#             return True, f'Вы успешно сближаетесь с объектом, проводите некоторые манипуляции и захватываете {obj.label}'
#
#     def get_name(self):
#         from ArbCharacters import Character
#         char = Character(self.id, data_manager=self.data_manager)
#         return f'{char.get_race_name()} {char.Name}'
#
#     def escape_from_battle(self):
#         battle = self.get_current_battle()
#         if not battle:
#             return None, f'Вы не находитесь в бою'
#
#         battle.delete_actor(self.id)
#         return True, f'Вы убегаете прочь с поля боя, оставляя его позади вы не наедетесь вернуться туда снова'
#
#     def waiting(self):
#         total_bonus = self.actor_attributes.ap_bonus + self.actor_attributes.ap
#         self.actor_attributes.waiting()
#         return True, f'Вы стали ожидать момента своего следующего хода. Общий бонус очков действий в следующем ходу: {total_bonus} ОД.'
#
#     def __repr__(self):
#         return f'Actor[ID: {self.id}]'

#
# @dataclass()
# class Unit:
#     id: int
#
#     def get_actor(self, data_manager: DataManager = None):
#         return Actor(self.id, data_manager=data_manager if data_manager else DataManager())
#
#     def disguise(self, data_manager: DataManager = None):
#         return Actor(self.id, data_manager=data_manager if data_manager else DataManager()).actor_disguise()
#
#     def get_actor_combat(self, data_manager: DataManager = None):
#         return ActorCombat(self.id, data_manager=data_manager if data_manager else DataManager())
#
#
# class UnitAI(Actor):
#     def __init__(self, id: int, **kwargs):
#         self.id = id
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         super().__init__(id, data_manager=self.data_manager)
#         self.visible_units = self.get_visible_characters()
#
#     def get_allies(self):
#         if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {self.id}'):
#             return [Unit(unit.get('character_id')) for unit in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'team_id = {self.team_id}') if unit.get('character_id') != self.id]
#         else:
#             return None
#
#     def get_enemies(self):
#         if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {self.id}'):
#             return [Unit(unit.get('character_id')) for unit in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'team_id != {self.team_id}') if unit.get('character_id') != self.id]
#         else:
#             return None
#
#     def get_visible_units(self):
#         return [unit for unit in self.get_visible_characters()]
#
#     def has_target(self):
#         if self.actor_attributes.current_target:
#             return True
#         else:
#             return False
#
#     def target_layer_id(self):
#         target = self.actor_attributes.current_target
#         if target:
#             target_layer = Actor(target, data_manager=self.data_manager).current_layer_id
#             return target_layer
#
#     def distance_to_target(self):
#         target = self.actor_attributes.current_target
#         if target:
#             target_layer = self.target_layer_id()
#             return self.distance_to_layer(target_layer)
#
#     def current_weapon_type(self):
#         from ArbWeapons import Weapon
#
#         weapon_id = self.actor_attributes.get_current_weapons()
#         if weapon_id:
#             weapon = Weapon(weapon_id[0], data_manager=self.data_manager)
#             return weapon.Class
#         else:
#             return None
#
#     def shot_difficulty(self):
#         from ArbWeapons import Weapon
#         from ArbCharacters import Character
#
#         weapon_id = self.actor_attributes.get_current_weapons()[0]
#         weapon = Weapon(weapon_id, data_manager=self.data_manager)
#
#         enemy = Actor(self.actor_attributes.current_target, data_manager=self.data_manager)
#
#         return weapon.AccuracyCheck(self.distance_to_target(), enemy.get_current_object().protection if enemy.current_object_id else 0, Race(Character(enemy.id, data_manager=self.data_manager).Race).Size)
#
#     def random_nearest_target(self):
#         available_id = (self.current_layer_id - 1, self.current_layer_id + 1)
#         nearest_enemies = []
#         if available_id[0] in self.visible_units:
#             nearest_enemies.extend(self.visible_units[available_id[0]])
#
#         if available_id[1] in self.visible_units:
#             nearest_enemies.extend(self.visible_units[available_id[1]])
#
#         if nearest_enemies:
#             random_enemy = random.choice(nearest_enemies)
#             self.actor_attributes.current_target = random_enemy
#             self.take_target(random_enemy)
#             return True
#         else:
#             sound_list = self.list_of_sounds()
#             if sound_list:
#                 random_sound = sound_list[-1]
#                 target = self.detect_sound_source(random_sound.id)
#                 if target:
#                     self.take_target(target)
#                     return True
#                 else:
#                     return False
#
#     def move_to_target(self):
#         target_layer_id = self.target_layer_id()
#         return self.move_to_layer(target_layer_id) == target_layer_id
#
#     def attack_target(self):
#         if not self.has_target():
#             self.random_nearest_target()
#
#         current_weapon_type = self.current_weapon_type
#         distance_to_target = self.distance_to_target()
#         target = self.actor_attributes.current_target
#
#         if current_weapon_type is not None:
#             if distance_to_target > 0:
#                 movement_result = self.move_to_target()
#                 if movement_result:
#                     self.set_melee_target(target)
#                     self.race_attack(target)
#                 else:
#                     return False
#
#                 return self.race_attack(target)
#             else:
#                 self.set_melee_target(target)
#                 return self.race_attack(target)
#
#         if current_weapon_type == 'ColdSteel':
#             if distance_to_target > 0:
#                 movement_result = self.move_to_target()
#                 if movement_result:
#                     self.set_melee_target(target)
#                 else:
#                     return False
#
#                 return self.melee_attack(target)
#             else:
#                 self.set_melee_target(target)
#                 return self.melee_attack(target)
#         else:
#             difficulty_to_attack = self.shot_difficulty()
#             if difficulty_to_attack > 70:
#                 movement_result = self.move_to_target()
#                 if movement_result:
#                     return self.range_attack(target)
#                 else:
#                     return False
#             else:
#                 return self.range_attack(target)



