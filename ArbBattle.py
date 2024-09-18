# -*- coding: utf-8 -*-
import datetime
import math
import pprint
import random
from dataclasses import dataclass
from ArbDatabase import DataManager, DataModel, DataDict
from ArbEventManager import Event, EventHandler, EventManager
from ArbHealth import Body, BodyElement
from ArbSkills import Skill, SkillInit
from ArbSounds import InBattleSound
from ArbItems import CharacterEquipment, Inventory
from ArbDamage import Damage
from abc import ABC, abstractmethod
from ArbResponse import Response, ResponsePool, RespondLog, RespondIcon, Notification
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

        self.wp_per_use = self.get('wp_per_use', 0) if self.get('wp_per_use', None) is not None else 0
        self.wp_per_round = self.get('wp_per_round', 0) if self.get('wp_per_round', None) is not None else 0

    def interact(self, character_id:int, **kwargs):
        enemy = kwargs.get('enemy_id')
        actor_team = BattleTeam.get_actor_team(character_id, data_manager=self.data_manager)
        if actor_team and self.wp_per_use:
            actor_team.add_win_points(self.wp_per_use)

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
            'object_type': object_type if object_type else self.object_type.object_id,
            'endurance': endurance if endurance is not None else self.current_endurance,
            'uses': uses if uses is not None else self.uses,
            'captured': captured if captured is not None else self.captured
        }

        self.data_manager.update('BATTLE_OBJECTS', prompt, f'object_id = {self.id}')

    def process_captured(self):
        if not self.captured:
            return

        captured_team = BattleTeam(self.captured, data_manager=self.data_manager)
        if self.object_type.wp_per_round:
            captured_team.add_win_points(self.object_type.wp_per_round)

    def __repr__(self):
        return f'Object.{self.id}.{self.object_type.object_id} ({self.current_endurance}/{self.object_type.max_endurance}DP)'

    def __str__(self):
        return f'{self.object_type.label} ({self.id})'






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
        self.is_active = self.get('round_active')
        self.winpoints = self.get('win_points', 0) if self.get('win_points', None) is not None else 0

    @classmethod
    def get_actor_team(cls, actor_id:int, **kwargs):
        """
               Возвращает объект команды персонажа.

               :param actor_id: Идентификатор актора, чью команду мы ищем.
               :param kwargs: Дополнительные ключевые параметры, ожидается 'data_manager' для ручного назначения DataManager.
               :return: BattleTeam если команда найдена, None если не найдена.
               """

        db = kwargs.get('data_manager', DataManager())
        team = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        dead_team = db.select_dict('BATTLE_DEAD', filter=f'character_id = {actor_id}')

        if team:
            if not team[0].get('team_id'):
                return None
            return BattleTeam(team[0].get('team_id'), data_manager=db)
        elif dead_team:
            if not team[0].get('team_id'):
                return None
            return BattleTeam(dead_team[0].get('team_id'), data_manager=db)
        else:
            return None

    def delete_team(self):
        members = self.fetch_members()
        for member in members:
            self.data_manager.update('BATTLE_CHARACTERS', {'team_id': None}, f'character_id = {member}')
            self.data_manager.update('BATTLE_DEAD', {'team_id': None}, f'character_id = {member}')

        self.delete_record()

    def add_win_points(self, wp:int):
        """
                       Добавляет очки победы для команды.

                       :param wp: Количество добавленных очков победы.
                       """

        self.winpoints += wp
        self.data_manager.update('BATTLE_TEAMS', {'win_points': self.winpoints}, f'team_id = {self.id}')

    def reduce_win_points(self, wp:int):
        """
                               Снижает очки победы для команды.

                               :param wp: Количество сниженных очков победы. Если итоговый self.winpoints окажется меньше 0, то присваивается значение 0.
                               """

        self.winpoints -= wp
        if self.winpoints < 0:
            self.winpoints = 0

        self.data_manager.update('BATTLE_TEAMS', {'win_points': self.winpoints}, f'team_id = {self.id}')

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
            return [member.get('character_id') for member in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'team_id = {self.id} ')]
        else:
            return []

    def get_dead_members(self) -> list[int]:
        if self.data_manager.check('BATTLE_DEAD', f'team_id = {self.id}'):
            return [member.get('character_id') for member in self.data_manager.select_dict('BATTLE_DEAD', filter=f'team_id = {self.id}')]
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

    def count_casulties(self):
        if self.data_manager.check('BATTLE_DEAD', f'team_id = {self.id}'):
            return self.data_manager.get_count('BATTLE_DEAD', 'character_id', f'team_id = {self.id}')
        else:
            return 0

    def compare_casualties(self):
        dead = self.count_casulties()
        participants = self.count_participants()

        total_value = dead + participants

        return round(dead / total_value, 2) if participants else 0



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
                    return method(self, *args, **kwargs, value=value)

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

    def notify_team(self, title:str, content:str, type:str = 'info'):
        team = BattleTeam(self.team_id, data_manager=self.data_manager)
        members = team.fetch_members()
        for member in members:
            Notification.create_notification(title, content, member, type)

    def notify_all_battle(self, title:str, content:str, type:str = 'info'):
        battle = Battlefield(self.battle_id, data_manager=self.data_manager)
        members = battle.fetch_actors()
        for member in members:
            Notification.create_notification(title, content, member, type)

    def air_respond(self, layer_id:int):
        text = f'Вы видите как над {Layer(layer_id, self.battle_id).label} ({layer_id}) что-то было сброшено...'
        self.notify_all_battle('Воздух...', text)

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

        self.notify_all_battle('АРТУДАР!', f'**{Layer(layer_id, self.battle_id).label} ({layer_id}) накрывается ударом артиллерии!**', 'danger')

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

        self.air_respond(layer_id)

        action = f'запускаете несколько снарядов, наполненных {value} минами типа {TrapInit(mine_type, data_manager=self.data_manager).label}, которые разываются прямо над полем боя и осыпаются'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Минирование'))

        return response

    @check_status()
    @require_command_points(2, 5)
    def reinforcement(self, layer_id:int, value:int):

        battle = Battlefield(self.battle_id, data_manager=self.data_manager)
        units = battle.spawn_units(value=value, layer_id=layer_id, team_id=self.team_id)

        self.set_activity(False)
        self.air_respond(layer_id)

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
        self.air_respond(layer_id)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("AmmoCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Патроны'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_grenades(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('GrenadeCrate', value=value)

        self.set_activity(False)
        self.air_respond(layer_id)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("GrenadeCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Взрывчатка'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_firstaid(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('MedCrate', value=value)

        self.set_activity(False)
        self.air_respond(layer_id)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("MedCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Медицинская помощь'))

        return response

    @check_status()
    @require_command_points(4, 3)
    def supply_repair(self, layer_id:int, value:int):

        layer = self.get_layer(layer_id)
        layer.add_object('RepairCrate', value=value)

        self.set_activity(False)
        self.air_respond(layer_id)

        action = f'отправляете летательный аппарат и сбрасываете на поле боя {ObjectType("RepairCrate", data_manager=self.data_manager).label}'
        response = ResponsePool(Response(True, self.describe_action(action, layer_id), 'Снабжение | Инструменты'))

        return response






class BattleType(ABC):
    def __init__(self, battlefield: 'Battlefield', **kwargs):
        self.battle = battlefield
        self.data_manager = kwargs.get('data_manager', DataManager())

    def get_target(self):
        return self.battle.type_value

    def set_overkill(self):
        self.battle.set_battle_type('Overkill')
        self.battle.set_battle_type_target(None)

    def add_extra_rounds(self, extra_rounds:int = 3):
        if self.battle.last_round:
            self.battle.set_last_round(self.battle.last_round + extra_rounds)
        else:
            self.battle.set_last_round(self.battle.round + extra_rounds)

    def get_active_teams(self) -> list[int]:
        actors_teams = [team.get('team_id') for team in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle.battle_id}')]
        actors_teams = list(set(actors_teams))
        if None in actors_teams:
            actors_teams.remove(None)
        return actors_teams

    def get_teams_members_count(self) -> dict[int, int]:
        team_members_count = {}
        for team in self.get_active_teams():
            team_members_count[team] = len(self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'team_id = {team} AND battle_id = {self.battle.battle_id}'))
        return team_members_count

    def get_teams_winpoints(self) -> dict[int, float]:
        teams = self.get_active_teams()
        team_winpoints = {}
        for team in teams:
            team_winpoints[team] = BattleTeam(team, data_manager=self.data_manager).winpoints
        return team_winpoints

    def get_teams_roles(self) -> dict[int, str]:
        teams = self.get_active_teams()
        team_roles = {}
        for team in teams:
            team_roles[team] = BattleTeam(team, data_manager=self.data_manager).role.role_id
        return team_roles

    def single_team_check(self) -> bool:
        teams = self.get_active_teams()
        if len(teams) > 1:
            return False
        else:
            return True

    def last_round_check(self) -> bool:
        if not self.battle.last_round:
            return False

        if self.battle.round >= self.battle.last_round:
            return True
        else:
            return False

    def get_attackers(self):
        teams_roles = self.get_teams_roles()
        attackers = []
        for team, role in teams_roles.items():
            if role == 'Attackers':
                attackers.append(team)

        return attackers

    def get_defenders(self):
        teams_roles = self.get_teams_roles()
        defenders = []
        for team, role in teams_roles.items():
            if role == 'Defenders':
                defenders.append(team)

        return defenders

    @abstractmethod
    def check_battle_end(self) -> bool:
        pass

    @abstractmethod
    def find_winner(self) -> int:
        pass


class Overkill(BattleType):

    def check_battle_end(self) -> bool:
        if self.single_team_check():
            return True

        if not self.last_round_check():
            return False
        else:
            winner_team = self.find_winner()
            if winner_team:
                return True
            else:
                self.add_extra_rounds(3)
                return False

    def find_winner(self) -> list[int] | None:
        members = self.get_teams_members_count()
        max_members = 0

        for team in members:
            if members[team] > max_members:
                max_members = members[team]

        max_count_teams_count = 0
        for team in members:
            if members[team] == max_members:
                max_count_teams_count += 1

        if max_count_teams_count == 1:
            for team in members:
                if members[team] == max_members:
                    return [team]
        else:
            return None


class Elimination(BattleType):
    def check_target_elimination(self) -> bool:
        target_id = self.get_target()
        is_target_dead = Body(target_id, data_manager=self.data_manager).is_dead()[0]
        if is_target_dead:
            return True
        else:
            return False

    def find_winner(self) -> list[int] | None:
        attackers = self.get_attackers()
        defenders = self.get_defenders()

        if self.check_target_elimination():
            return attackers if attackers else None
        else:
            return defenders if defenders else None

    def check_battle_end(self) -> bool:

        if self.single_team_check():
            return True

        if self.find_winner():
            return True
        else:
            self.add_extra_rounds(5)
            return False


class Interception(BattleType):
    def find_winner(self) -> list[int] | None:
        teams_scores = self.get_teams_winpoints()
        max_score = max(teams_scores.values())

        max_score_teams = 0
        for team, score in teams_scores.items():
            if score == max_score:
                max_score_teams += 1

        if max_score_teams == 1:
            for team, score in teams_scores.items():
                if score == max_score:
                    return [team]
        else:
            self.set_overkill()
            return None

    def check_battle_end(self) -> bool:

        if self.single_team_check():
            return True

        if self.find_winner():
            return True
        else:
            self.add_extra_rounds(5)
            return False


class Raid(BattleType):
    def find_winner(self) -> list[int] | None:
        teams_scores = self.get_teams_winpoints()
        max_score = max(teams_scores.values())

        max_score_teams = 0
        for team, score in teams_scores.items():
            if score == max_score:
                max_score_teams += 1

        if max_score_teams == 1:
            for team, score in teams_scores.items():
                if score == max_score:
                    return [team]
        else:
            self.set_overkill()
            return None

    def check_battle_end(self) -> bool:
        if self.single_team_check():
            return True

        if self.find_winner():
            return True
        else:
            self.add_extra_rounds(5)
            return False


class Capture(BattleType):
    def find_winner(self) -> list[int] | None:
        teams_scores = self.get_teams_winpoints()
        max_score = max(teams_scores.values())

        max_score_teams = 0
        for team, score in teams_scores.items():
            if score == max_score:
                max_score_teams += 1

        if max_score_teams == 1:
            for team, score in teams_scores.items():
                if score == max_score:
                    return [team]
        else:
            self.set_overkill()
            return None

    def check_battle_end(self) -> bool:

        if self.single_team_check():
            return True

        if self.find_winner():
            return True
        else:
            self.add_extra_rounds(5)
            return False



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

        return object_id

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
            object.insert_data()

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

    def __str__(self):
        return f'{self.id} - {self.label}'


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

    def get_battle_type(self) -> BattleType:
        """Вовзвращает объект Режима боя указанный в качестве заданного в битве. Если режим боя не задан используется Overkill

        :return: BattleType
        """


        if self.battle_type == 'Overkill':
            return Overkill(self, data_manager=self.data_manager)
        elif self.battle_type == 'Elimination':
            return Elimination(self, data_manager=self.data_manager)
        elif self.battle_type == 'Interception':
            return Interception(self, data_manager=self.data_manager)
        elif self.battle_type == 'Raid':
            return Raid(self, data_manager=self.data_manager)
        elif self.battle_type == 'Capture':
            return Capture(self, data_manager=self.data_manager)
        else:
            return Overkill(self, data_manager=self.data_manager)

    def get_winner(self) -> list[int]:
        """
            Выдаёт список идентификаторов команд-победителей по итогам боя

            :return: list[int]
            """
        winners = self.get_battle_type().find_winner()
        return winners if winners else []

    def set_battle_type(self, battle_type: str):
        """
            Устанавливает режим боя из доступных в базе данных и коде

            :param battle_type: идентификатор режима боя (например: Overkill, Capture, Raid и т.д.)

            """

        self.battle_type = battle_type
        self.data_manager.update('BATTLE_INIT', {'battle_type': self.battle_type}, f'id = {self.battle_id}')

    def set_battle_type_target(self, target):
        """
            Устанавливает цель для режима боя (напримере для ликвидации целью будет идентификатор цели которую нужно убить)

            :param target: (int|str|None) заданная цель режима боя

            :return: str
            """

        self.type_value = target
        self.data_manager.update('BATTLE_INIT', {'type_value': target}, f'id = {self.battle_id}')

    def get_battle_type_label(self) -> str:
        """
            Возвращает название режима боя. Если режим боя задан неверно выдаст название "Столкновение"

            :return: str
            """

        if self.data_manager.check('BATTLE_CONDITIONS', filter=f'id = "{self.battle_type}"'):
            return self.data_manager.select_dict('BATTLE_CONDITIONS', filter=f'id = "{self.battle_type}"')[0].get('label')
        else:
            return self.data_manager.select_dict('BATTLE_CONDITIONS', filter=f'id = "Overkill"')[0].get('label')

    def set_last_round(self, round:int):
        """
            Устанавливает последний раунд в бою

            :param round: Номер последнего раунда

            :return: None
            """

        self.last_round = round
        self.data_manager.update('BATTLE_INIT', {'last_round': round}, f'id = {self.battle_id}')

    def get_layers(self) -> dict[int, Layer]:
        f"""
            Возвращает словарь всех слоёв на поле боя:
            Ключ - Идентификатор слоя\n
            Значение - экземпляр слоя

            :return: dict[int, Layer]
            """

        if not self.data_manager.check('BATTLE_LAYERS', f'battle_id = {self.battle_id}'):
            return {}

        layers = self.data_manager.select_dict('BATTLE_LAYERS', filter=f'battle_id = {self.battle_id}')
        layers_dict = {}
        for layer in layers:
            layers_dict[layer.get('id')] = Layer(layer.get('id'), self.battle_id, data_manager=self.data_manager)

        return layers_dict

    def fetch_teams(self) -> list[int]:
        """
            Возвращает список идентификаторов всех команд на поле боя

            :return: list[int]
            """

        if self.data_manager.check('BATTLE_TEAMS', f'battle_id = {self.battle_id}'):
            teams = self.data_manager.select_dict('BATTLE_TEAMS', filter=f'battle_id = {self.battle_id}')
            return [team.get('team_id') for team in teams]
        else:
            return []

    def fetch_actors(self) -> list[int]:
        """
        Возвращает список идентификаторов всех активных персонажей на поле боя

        :return: list[int]
        """

        if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.battle_id}') is None:
            return []
        else:
            return [c.get('character_id') for c in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id}')]

    def add_actor(self, actor_id: int, **kwargs) -> None:
        """
            Добавляет актора на поле боя.
            Если персонаж уже есть на поле боя - обновляет его параметры боя

            :param actor_id: int - идентификатор персонажа
            :param kwargs: dict - дополнительные параметры актора (layer_id, object, team_id, initiative)
        """

        if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {actor_id}'):
            prompt = {'battle_id': self.battle_id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative', random.randint(1, 100)),
                      'is_active': kwargs.get('is_active', None),
                      'height': kwargs.get('height', 0)}

            self.data_manager.update('BATTLE_CHARACTERS', prompt, f'character_id = {actor_id}')
        else:
            prompt = {'battle_id': self.battle_id,
                      'character_id': actor_id,
                      'layer_id': kwargs.get('layer', 0),
                      'object': kwargs.get('object', None),
                      'team_id': kwargs.get('team_id', None),
                      'initiative': kwargs.get('initiative', random.randint(1, 100)),
                      'is_active': kwargs.get('is_active', None),
                      'height': kwargs.get('height', 0)}
            self.data_manager.insert('BATTLE_CHARACTERS', prompt)

        ActionPoints(ap=0, actor_id=actor_id).new_round_ap()

    def calculate_size(self) -> float:
        """
            Выводит размер поля боя исходя из слоёв и расстояния между слоями (self.distance_delta)

            :return: float - итоговый размер в метрах
        """

        layers = self.get_layers()
        min_layer = min(layers.keys())
        max_layer = max(layers.keys())

        return (max_layer - min_layer) * self.distance_delta

    def max_initiative_actor(self) -> int | None:
        """
            Выводит идентификатор персонажа с максимальной инициативой среди списка !активных! персонажей.
            Если все персонажи завершили свои ходы, выведет None

            :return: int | None - идентификатор персонажа с максимальной инициативой
        """

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
        """
            Выводит упорядоченный список ходов персонажей

            :return: list[int] - список идентификаторов персонажей
        """

        c_list = self.fetch_actors()
        sorted_actors = sorted(c_list, key=lambda actor: Actor(actor, data_manager=self.data_manager).initiative, reverse=True)
        return [actor for actor in sorted_actors]

    def current_turn_index(self) -> int:
        """
            Выводит текущий номер хода

            :return: int - индекс хода персонажа
        """

        for index, actor in enumerate(self.turn_order()):
            if Actor(actor, data_manager=self.data_manager).is_active:
                return index
        else:
            return 0

    def actor_turn_index(self, actor_id: int) -> int | None:
        """
            Выводит каким по счёту ходит персонаж

            :param actor_id: идентификатор персонажа

            :return: int | None - индекс хода персонажа
        """

        for index, actor in enumerate(self.turn_order()):
            if actor == actor_id:
                return index
        return None

    def delete_actor(self, actor_id: int) -> None:
        """
            Полностью удаляет персонажа из битвы (списка активных персонажей и убитых персонажей)

            :param actor_id: идентификатор персонажа

            :return: None
        """

        self.unable_actor(actor_id)
        self.data_manager.delete('BATTLE_DEAD', f'character_id = {actor_id} and battle_id = {self.battle_id}')

    def unable_actor(self, actor_id: int) -> None:
        """
        Удаляет персонажа из списка активных персонажей битвы

        :param actor_id: идентификатор персонажа

        :return: None
        """

        self.data_manager.delete('BATTLE_CHARACTERS', f'character_id = {actor_id} and battle_id = {self.battle_id}')

    def dead_actor(self, actor_id: int, killer_id: int = None, reason:str=None) -> None:
        """
        Записывает персонажа в базу данных в качестве убитого

        :param actor_id: идентификатор убитого персонажа
        :param killer_id: идентификатор убийцы, если присутствует
        :param reason: описание обстоятельства смерти (необязательно)

        :return: None
        """

        actor = Actor(actor_id, data_manager=self.data_manager)

        prompt = {
            'battle_id': self.battle_id,
            'character_id': actor_id,
            'layer_id': actor.layer_id,
            'killer': killer_id,
            'team_id': actor.team_id,
            'reason': reason,
        }

        self.data_manager.insert('BATTLE_DEAD', prompt)
        self.unable_actor(actor_id)

    def process_wp_by_objects(self):
        """
            Обрабатывает все захваченные объекты и выдаёт командам очки победы
        """

        captured_objects = [GameObject(obj.get('object_id'), data_manager=self.data_manager) for obj in self.data_manager.select_dict('BATTLE_OBJECTS', filter=f'battle_id = {self.battle_id} AND captured IS NOT NULL')]
        for obj in captured_objects:
            obj.process_captured()

    def check_battle_ending(self):
        """
                        Проверка, соответвтуют ли текущие условия боя условиям завершения боя (зависит от Режима Боя)

                        :return: True/False
                        """

        from ArbCharacters import CharacterProgress

        battle_type = self.get_battle_type()
        is_ended = battle_type.check_battle_end()
        winners = battle_type.find_winner()
        total_teams = self.fetch_teams()

        alive_participants = [char.get('character_id') for char in self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id}')]
        dead_participants = [char.get('character_id') for char in self.data_manager.select_dict('BATTLE_DEAD', filter=f'battle_id = {self.battle_id}')]

        if not is_ended:
            return False

        if not winners:
            winners = []

        teams_modifiers = {None: 1}

        for team in total_teams:
            is_winner = team in winners
            exp_modifier = 1.2 if is_winner else 0.75
            teams_modifiers[team] = exp_modifier

        for member in alive_participants + dead_participants:
            member_team = BattleTeam.get_actor_team(member, data_manager=self.data_manager)
            kills = self.data_manager.get_count('BATTLE_DEAD', f'character_id', f'killer = {member}')
            kills_exp = 250 * kills * teams_modifiers[member_team.id if member_team else None]
            win_points_exp = member_team.winpoints * 100 if member_team else 0

            CharacterProgress(member, data_manager=self.data_manager).update_progress_data(exp=kills_exp+win_points_exp)

        return True

    def end_battle(self) -> ResponsePool:
        """
                Финальный скрипт окончания боя.
                Выдаёт полученный за бой опыт персонажам.
                Удаляет всю информацию о битве (заканчивает битву)
                Добавляет персонажам информацию о произошедших событиях (смертях, победе/поражении)

                :return: ResponsePool - Информация о завершении боя (победители, проигравшие, потери)
                """
        # TODO: Добавить удаление битвы
        # TODO: Записывание в память персонажа информацию о погибших и о победе/поражении

        winners = self.get_winner()
        if not winners:
            winners = []
        all_teams = self.fetch_teams()
        print(all_teams)
        ending_text = f''
        for team in all_teams:
            team_obj = BattleTeam(team, data_manager=self.data_manager)
            team_casualties = team_obj.compare_casualties()
            print(team, team_casualties, team_obj.get_dead_members(), team_obj.fetch_members())

            if team in winners:
                prefix = ''
                if team_casualties <= 0:
                    prefix = 'Решительная '
                elif 50 < team_casualties <= 70:
                    prefix = 'Тяжелая '
                elif 70 < team_casualties:
                    prefix = 'Пиррова '

                ending_text += f'- *{prefix}Победа {team_obj.label}*\n'
            else:
                prefix = ''
                if team_casualties <= 0:
                    prefix = 'Героическое '
                elif 50 < team_casualties <= 70:
                    prefix = 'Тяжелое '
                elif 70 < team_casualties:
                    prefix = 'Сокрушительное '

                ending_text += f'- *{prefix}Поражение {team_obj.label}*\n'
            ending_text += f'-# *Потери: {team_obj.count_casulties()}*\n-# *Выжившие: {team_obj.count_participants()}*\n\n'

        return ResponsePool(Response(True, ending_text, f'Конец {self.label} ({self.get_battle_type_label()})'))

    def clear_round_sounds(self):
        """
        Очищает звуки раунда
        """
        self.data_manager.delete('BATTLE_SOUNDS', f'battle_id = {self.battle_id}')

    def next_round(self) -> tuple[bool, ResponsePool]:
        """
        Запускает следующий раунд (обновляет инициативу персонажей, просчитывает захваченные точки и выдаёт за них очки победы)
        Если прошедший раунд был последним, запускает проверку окончания боя

        :return: tuple(bool (завершился ли бой), ResponsePool(вывод событий боя))
        """

        self.process_wp_by_objects()

        is_end = self.check_battle_ending()
        if is_end:
            return True, self.end_battle()

        self.round += 1
        self.data_manager.update('BATTLE_INIT', {'round': self.round}, f'id = {self.battle_id}')

        print(self.fetch_actors())
        for act in self.fetch_actors():
            print(act)
            actor = Actor(act, data_manager=self.data_manager)
            print(actor)
            if self.round % self.key_round_delay == 0:
                new_initiative = actor.roll_initiative()
                actor.set_initiative(new_initiative)
            ActionPoints.character_ap(act, data_manager=self.data_manager).new_round_ap()
            actor.set_active(None)

        teams = self.fetch_teams()

        if teams:
            for team in teams:
                BattleTeam(team, data_manager=self.data_manager).set_activity(True)

        self.clear_round_sounds()
        BattleLogger.log_event(self.data_manager, self.battle_id, 'NewCycle', event_description=f'Начинается {self.round} раунд!')

        return False, ResponsePool(Response(True, f'*Начинается {"последний " if self.round == self.last_round else ""}{self.round} раунд!*', 'Сражение продолжается'))

    def next_actor(self) -> ResponsePool:
        from ArbCharacters import Character

        if self.data_manager.check('BATTLE_CHARACTERS', f'battle_id = {self.battle_id} AND is_active = 1'):
            active_actor = self.data_manager.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {self.battle_id} AND is_active = 1')[0].get('character_id')
            Actor(active_actor, data_manager=self.data_manager).set_active(False)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'EndTurn', event_description=f'Персонаж {active_actor} завершает свой ход!')

        if self.max_initiative_actor() is not None:
            n_actor = self.max_initiative_actor()
            Actor(n_actor, data_manager=self.data_manager).set_active(True)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'NewTurn', actor_id=n_actor, event_description=f'Персонаж {n_actor} начинает свой ход!')
            Notification.create_notification('Ваш ход',f'*Ваш персонаж **{Character(n_actor).name}** прямо сейчас ходит в бою **{self.label}***',n_actor)

            return ResponsePool(Response(True, f'*Персонаж ||{Character(n_actor).name}|| начинает свой ход!*', 'Ход'))
        else:
            is_last_round = self.next_round()
            if is_last_round[0]:
                return is_last_round[1]

            n_actor = self.max_initiative_actor()
            Actor(n_actor, data_manager=self.data_manager).set_active(True)
            BattleLogger.log_event(self.data_manager, self.battle_id, 'NewTurn', actor_id=n_actor, event_description=f'Персонаж {n_actor} начинает свой ход!')

            responses = is_last_round[1].responses
            responses.append(Response(True, f'*Персонаж ||{Character(n_actor).name}|| начинает свой ход!*', 'Ход'))
            Notification.create_notification('Ваш ход', f'*Ваш персонаж **{Character(n_actor).name}** прямо сейчас ходит в бою **{self.label}***', n_actor)

            return ResponsePool(responses)

    def is_last_actor(self, actor_id: int) -> bool:
        order_list = self.turn_order()
        if actor_id == order_list[-1]:
            return True
        else:
            return False

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
        self.data_manager.update('LOC_INIT', {'current_battle': None}, filter=f'current_battle = {self.battle_id}')

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

    def add_sound(self, sound_type: str, actor_id: int = None, layer_id: int = None, volume: int = None, content:str = None):
        c_id = self.data_manager.maxValue('BATTLE_SOUNDS', 'id') + 1
        prompt = {'id': c_id,
                  'battle_id': self.battle_id,
                  'actor_id': actor_id if actor_id else None,
                  'layer_id': layer_id if layer_id is not None else 0,
                  'sound_id': sound_type,
                  'volume': volume if volume is not None else random.randint(50, 150),
                  'content': content if content else None}

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

    def __str__(self):
        return f'{self.battle_id} - **{self.label}**'

    @staticmethod
    def revive_actor(character_id:int):
        db = DataManager()
        if not db.check('BATTLE_DEAD', f'character_id = {character_id}'):
            return
        if db.check('CHARS_INJURY', f'id = {character_id}'):
            db.delete('CHARS_INJURY', f'id = {character_id}')

        data = db.select_dict('BATTLE_DEAD', filter=f'character_id = {character_id}')[0]
        db.delete('BATTLE_DEAD', f'character_id = {character_id}')
        query = {'battle_id': data.get('battle_id'),
                 'layer_id': data.get('layer_id'),
                 'character_id': character_id,
                 'team_id': data.get('team_id'),
                 'initiative': 20,
                 'is_active': None,
                 'height':0
                 }
        db.insert('BATTLE_CHARACTERS', query)

    @staticmethod
    def get_active_battles():
        db = DataManager()
        battles = [battle.get('id') for battle in db.select_dict('BATTLE_INIT')]
        return battles

    @staticmethod
    def get_actor_battle(character_id:int):
        db = DataManager()
        battle_id = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {character_id}')
        if not battle_id:
            return None
        else:
            return battle_id[0].get('battle_id')



class DamageManager:
    def __init__(self, data_manager: DataManager = None):
        self.data_manager = data_manager if data_manager else DataManager()

    def get_target_user(self, target_id:int):
        users = self.data_manager.select_dict('PLAYERS', filter=f'character_id = {target_id}')
        if not users:
            return []
        else:
            return [user.get('id') for user in users]

    def notify_damaged_users(self, target_id:int, text:str):
        pass

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

    def process_damage(self, target_id:int, shots: list[Damage], **kwargs) -> str:
        damage_list = shots
        total_damage = []

        current_element: BodyElement = self.target_random_element(target_id) if not kwargs.get('bodyelement') else BodyElement(target_id, kwargs.get('bodyelement'), data_manager=self.data_manager)
        armor = self.get_target_armor(target_id)

        for damage in damage_list:
            print('БРОНЯ:', armor)
            n_damage = armor.ballistic_simulation(current_element.body_parts_group, damage)
            if n_damage:
                e_d_pair = (current_element, n_damage)
                total_damage.append(e_d_pair)

        for pair in total_damage:
            self.apply_damage(pair)

        text = '```'
        for pair in total_damage:
            text += f'- {pair[1].__str__()} по {pair[0].label}\n'
        text += '```'

        Notification.create_notification('Получен урон!', text, target_id, 'danger')

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
            return None

        damage_list = []

        enemy_cover_id = self.get_enemy_cover(target_id)
        enemy_cover = GameObject(enemy_cover_id, data_manager=self.data_manager).current_protection if enemy_cover_id else 0
        distance_to_enemy = self.attacker.calculate_total_distance(target_id)

        shot_difficulty = weapon.shot_difficulty(distance_to_enemy, enemy_cover)

        shots = min(weapon.attacks, bullets)

        weapon.use_bullet(shots)

        for _ in range(shots):
            self.attacker.make_sound('GunShot', weapon.shot_noise(), content=f'Вы слышали оглушительный хлопок от выстрела из {SkillInit(weapon.weapon_class).label}, оставивший за собой эхо')

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
            armor_force = self.attacker.get_capacity_or_armor_skill('Force')
            damage_bonus = armor_force / 4

            for _ in range(attacks):
                self.attacker.make_sound('Fight', random.randint(50, 150))
                roll = self.compare_skills(target_id)
                if not roll[0]:
                    continue

                raw_damage = attack.attack(damage_bonus=damage_bonus)
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

    def distance_of_view(self) -> float:
        vision = self.actor.get_body().get_capacity('Vision') / 100
        actor_height = self.actor.get_total_height()

        height_bonus = actor_height * 400

        basic_fov = 5400 + height_bonus

        return basic_fov * vision * self.time_factor * self.weather_factor

    def get_nightvision_baff(self) -> float:
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('NightVision')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('NightVision', 0)

        return max(capacity, armor_bonus)

    def get_recon_baff(self) -> float:
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('Recon')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('Recon', 0)

        return max(capacity, armor_bonus)

    def get_thermal_vision_baff(self) -> float:
        from ArbClothes import CharacterArmor

        capacity = self.actor.get_capacity('ThermalVision')
        armor_bonus = CharacterArmor(self.actor.actor_id, data_manager=self.data_manager).armors_skills().get('ThermalVision', 0)

        return max(capacity, armor_bonus)

    def get_time_factor(self) -> float:
        time_factor = self.actor.get_battle().time.visibility if self.actor.battle_id else 100
        if time_factor < 100:
            night_vision_baff = self.get_nightvision_baff() / 100
            time_penalty = (100 - time_factor) * (1 - night_vision_baff) if night_vision_baff <= 1 else 0

        else:
            time_penalty = 0

        return (100 - time_penalty) / 100

    def get_weather_factor(self) -> float:
        return self.actor.get_battle().weather.visibility/100 if self.actor.battle_id else 1

    def layer_vigilance(self, target_layer: int, distance_delta: float):
        total_distance = abs(target_layer - self.actor.layer_id) * distance_delta
        terrain_coverage = Layer(target_layer, self.actor.battle_id).terrain.visibility / 100
        layer_baff = 0 if self.actor.layer_id != target_layer else 40

        return round((self.dov - total_distance) / self.dov * 100 * self.time_factor * self.weather_factor * terrain_coverage + layer_baff, 2)

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
                object_baff = 20 if Actor(character_id, data_manager=self.data_manager).object_id == self.actor.object_id else 0

                if Actor(character_id, data_manager=self.data_manager).disguise() > vigilance * thermal_vision_baff * recon_baff + object_baff:
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

    def process_actor_vigilance(self, actor_id:int):

        actor = Actor(actor_id, data_manager=self.data_manager)
        team_members = self.actor.get_team().get_dead_members() + self.actor.get_team().fetch_members()
        if actor.actor_id in team_members:
            return f'**{actor.get_character().name}**'
        else:
            return f'||Неизвестный {actor.get_character().race.label.lower()} ({actor_id})||'

    def string_vigilance(self):
        visible_characters = self.get_visible_characters()
        visible_dead_bodies = self.get_visible_dead_bodies()
        visible_layers = self.total_layers_vigilance()

        chunks = []
        total_text = f''
        for layer in sorted(visible_layers.keys()):
            c_layer = Layer(layer, self.actor.battle_id, data_manager=self.data_manager)
            c_characters = visible_characters.get(layer, [])
            if len(c_characters) == 1 and c_characters[0] == self.actor.actor_id:
                c_characters = []

            c_dead_bodies = visible_dead_bodies.get(layer, [])
            characters_text = f'Вы видите силуэты ' if c_characters else 'Вы не замечаете живых существ поблизости'
            dead_bodies_text = f'. Вы видите трупы: ' if c_dead_bodies else ''
            characters_text += f', '.join(self.process_actor_vigilance(char) for char in c_characters if char != self.actor.actor_id)
            dead_bodies_text += f', '.join(self.process_actor_vigilance(char) for char in c_dead_bodies)

            layer_text = f'''
***{c_layer.label} ||(Слой {layer})||*** {'``<--- Вы здесь``' if self.actor.layer_id == layer else ''}
- *Видимость: **{visible_layers.get(layer):0.2f}%***
{c_layer.string_layer()}.
-# {characters_text}{dead_bodies_text}
'''
            total_text += layer_text
            chunks.append(layer_text)

        return total_text, chunks


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

    def trap_checking(self, log: 'ActionManager') -> tuple[bool, RespondLog]:
        current_traps = self.actor.get_layer().get_traps()
        if not current_traps:
            log.action('Преграды', f'Вы успешно продвигаетесь по местности не встречая преград на своем пути...', RespondIcon.success())
            return True, log.log

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
                log.action('Ловушки', f'По мере движения вы натыкаетесь на ловушку ({c_trap.label}), которая активируется прямо рядом с вами!', RespondIcon.danger())
                return False, log.log

        log.action('Преграды', f'Вы успешно продвигаетесь по местности не встречая преград на своем пути...', RespondIcon.success())
        return True, log.log

    def move_forward(self, log: 'ActionManager') -> tuple[bool, RespondLog | None]:
        c_slots = self.get_nearby_layers_id()
        if c_slots[1] is None:
            return False, None

        c_cost = self.movement_cost()
        ap_use_result = self.actor.ap_use(c_cost)

        if not ap_use_result:
            return False, None
        else:
            if self.actor.fly_height == 0:
                success, response = self.trap_checking(log)
                if not success:
                    return success, log.log

            self.set_layer(c_slots[1])
            return True, None

    def move_back(self, log: 'ActionManager') -> tuple[bool, RespondLog | None]:
        c_slots = self.get_nearby_layers_id()
        if c_slots[0] is None:
            return False, None

        c_cost = self.movement_cost()
        ap_use_result = self.actor.ap_use(c_cost)

        if not ap_use_result:
            return False, None
        else:
            if self.actor.fly_height == 0:
                success, response = self.trap_checking(log)
                if not success:
                    return success, log.log

            self.set_layer(c_slots[0])
            return True, None

    def hande_move_event(self, log: 'ActionManager') -> tuple[bool, RespondLog]:
        status = self.actor.status()
        log = log
        log.log = status.trigger_melees(log.log)
        log.log = status.trigger_suppressors(log.log)
        log.log = status.trigger_containers(log.log)

        if random.randint(0, 100) > sum([random.randint(0, 100) for _ in range(len(status.melees))]):
            status.clear_melees(self.actor.actor_id)
        else:
            return False, log.log

        return True, log.log

    def steps_volume(self):
        basic_roll = random.randint(10, 200)
        stealth_mod = self.actor.get_skill('Stealth') * 0.5
        return basic_roll - stealth_mod if basic_roll - stealth_mod > 10 else 10

    def move_to_layer(self, layer_id:int) -> 'ActionManager':
        log = self.actor.AM()

        if layer_id not in self.actor.get_battle().get_layers().keys():
            log.action('Перемещение', 'Этого слоя не существует в данном бою.', RespondIcon.info())
            return log

        if self.actor.layer_id == layer_id:
            log.action('Перемещение', 'Вы уже находитесь на этом слое.', RespondIcon.info())
            return log

        StatusManager.clear_all_statuses(self.actor.actor_id)
        move_success, responses = self.hande_move_event(log)
        if not move_success:
            log.action('Неудачное перемещение', 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают сбежать', RespondIcon.failure())
            return log

        steps_volume = self.steps_volume()

        self.set_object(None)

        if self.actor.layer_id < layer_id:
            for _ in range(layer_id-self.actor.layer_id):
                self.actor.make_sound('Steps', steps_volume)
                movement_success, layer_response = self.move_forward(log)
                log.log = layer_response if layer_response else log.log
                if not movement_success:
                    break

        elif self.actor.layer_id > layer_id:
            for _ in range(self.actor.layer_id-layer_id):
                self.actor.make_sound('Steps', steps_volume)
                movement_success, layer_response = self.move_back(log)
                log.log = layer_response if layer_response else log.log
                if not movement_success:
                    break

        StatusManager.clear_targeters(self.actor.actor_id)

        log.action('Перемещение',
                   f'-# Вы проходите какое-то расстояние и оказываетесь на **{Layer(self.actor.layer_id, self.actor.battle_id, data_manager=self.actor.data_manager).label}** ||**(Слой {self.actor.layer_id})**||. {Layer(self.actor.layer_id, self.actor.battle_id, data_manager=self.actor.data_manager).terrain.desc}',
                   RespondIcon.success())

        return log

    def get_layer_objects(self):
        layer = self.actor.layer_id
        battle = self.actor.battle_id

        return [object_id.get('object_id') for object_id in self.actor.data_manager.select_dict('BATTLE_OBJECTS', filter=f'layer_id = {layer} and battle_id = {battle}')]

    def set_fly_height(self, height: int):
        self.actor.fly_height = height
        self.actor.data_manager.update('BATTLE_CHARACTERS', {'height': height}, f'character_id = {self.actor.actor_id}')

    def fly(self, height: int) -> 'ActionManager':
        from ArbClothes import CharacterArmor

        log = self.actor.AM()

        stat = self.actor.get_body().get_capacity('Flying')
        armors_skills = CharacterArmor(self.actor.actor_id, data_manager=self.actor.data_manager).armors_skills().get('Flying', 0)

        total_value = stat + armors_skills

        if total_value <= 0:
            log.action('Невозможно летать', 'Вы не можете летать', RespondIcon.info())
            return log

        cost = round((height // 10) * ((200 - total_value)/100))

        if height <= 0:
            log.action('Невозможно опуститься', 'Вы не можете опуститься так низко!', RespondIcon.info())
            return log

        cost = 1 if cost <= 0 and height > 0 else cost

        ap_use_result = self.actor.ap_use(cost)

        if not ap_use_result:
            log.action('Невозможно лететь', 'Вам не хватает очков действия для полёта', RespondIcon.failure())
            return log

        self.set_object(None)
        success, responses = self.hande_move_event(self.actor.layer_id)
        if not success:
            response = Response(False, 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают взлететь!', 'Невозможность полета!')
        else:
            response = Response(True, f'Вы летите выше на {height}м.!', 'Полет')
            self.set_fly_height(height)

        log.log.response_to_respond(response)

        return log

    def move_to_object(self, object_id: int = None) -> 'ActionManager':
        log = self.actor.AM()
        layer_objects = self.get_layer_objects()
        if object_id not in layer_objects and object_id is not None:
            log.action('Перемещение к объекту', f'Данного объекта ``({object_id})`` нет в этой местности!', RespondIcon.info())
            return log

        if object_id:
            if GameObject(object_id, data_manager=self.actor.data_manager).available_slots <= 0:
                log.action('Перемещение к объекту', f'У данного объекта нет места, которое можно занять!', RespondIcon.failure())
                return log

        c_cost = round(self.movement_cost() * 0.5)

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            log.action('Перемещение к объекту', 'Вам не хватает очков действия для перемещения', RespondIcon.failure())
            return log

        StatusManager.clear_all_statuses(self.actor.actor_id)
        move_result, responses = self.hande_move_event(log)

        if not move_result:
            log.action('Противники', 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!', RespondIcon.failure())
            return log

        self.set_object(None)

        StatusManager.clear_targeters(self.actor.actor_id)
        self.actor.make_sound('Steps', self.steps_volume())


        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking(log)
            log.log = trap_response
            if not success:
                return log
        else:
            self.actor.fly_height(0)
            log.action('Полет', 'Вы снижаетесь для занимания объекта в качестве укрытия', RespondIcon.info())

        if object_id is not None:
            self.set_object(object_id)

        response = Response(True, f'Вы перемещаетесь к объекту **{GameObject(object_id, data_manager=self.actor.data_manager).object_type.label}** ||({object_id})|| и занимаете в качестве укрытия', 'Перемещение к объекту') if object_id else Response(True, f'Вы успешно покидаете укрытие!', 'Перемещение к объекту')
        log.log.response_to_respond(response)

        return log

    def flee_from_melee(self, log: 'ActionManager') -> RespondLog:
        log = log

        c_cost = round(self.movement_cost() * 0.5)

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            log.action('Ближний бой', 'Вам не хватает очков действия для перемещения', RespondIcon.failure())
            return log.log

        move_result, responses = self.hande_move_event(log)
        log.log = responses

        if not move_result:
            log.action('Ближний бой', 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!', RespondIcon.failure())
            return log.log

        self.actor.make_sound('Steps', self.steps_volume())

        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking(log)
            log.log = trap_response
            if not success:
                return log.log

        self.actor.status().clear_melees(self.actor.actor_id)

        log.action('Ближний бой', 'Вам удаётся отбиться от противника и сбежать из ближнего боя!', RespondIcon.success())

        return log.log

    def escape(self) -> 'ActionManager':
        log = self.actor.AM()
        c_cost = self.movement_cost()

        ap_use = self.actor.ap_use(c_cost)

        if not ap_use:
            log.action('Бег из боя', 'Вам не хватает очков действия для перемещения!', RespondIcon.failure())
            return log

        move_result, responses = self.hande_move_event(log)

        log.log = responses
        if not move_result:
            log.action('Бег из боя', 'Противники, которые находятся с вами в ближнем бою сдерживают вас и не дают переместиться!', RespondIcon.failure())
            return log

        self.set_object(None)

        self.actor.make_sound('Steps', self.steps_volume())

        if self.actor.fly_height == 0:
            success, trap_response = self.trap_checking(log)
            log.log = trap_response
            if not success:
                return log

        self.actor.clear_ap()
        self.actor.status().dead_clear(self.actor.actor_id)
        self.actor.data_manager.delete('BATTLE_CHARACTERS', f'character_id = {self.actor.actor_id}')

        log.action('Побег из боя', '-# Вы пересекаете местность и покидаете поле боя, оставляя сражение позади...', RespondIcon.success())

        return log


class ActionPoints:
    def __init__(self, ap: int=0, **kwargs):
        self.ap = ap
        self.actor_id = kwargs.get('actor_id', 0)
        self.data_manager = kwargs.get('data_manager', DataManager())

    @classmethod
    def character_ap(cls, actor_id:int, data_manager: DataManager = None):
        data_manager = data_manager if data_manager else DataManager()
        record = DataDict('CHARS_COMBAT', f'id = {actor_id}', data_manager=data_manager)
        obj = cls(ap=record.get('ap', 0), data_manager=data_manager, actor_id=actor_id)
        obj.check_record()
        return obj

    def check_record(self):
        if not self.data_manager.check('CHARS_COMBAT', f'id = {self.actor_id}'):
            query = {
                'id': self.actor_id,
                'ap': 0,
                'ap_bonus': 0,
                'supressed': None,
                'hunted': None,
                'contained': None,
                'ready': None,
                'target': None,
                'melee_target': None
            }
            self.data_manager.insert('CHARS_COMBAT', query)

    def add(self, ap: int):
        self.check_record()
        self.ap += ap
        self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')

    def use(self, ap: int):
        self.check_record()
        if self.ap >= ap:
            self.ap -= ap
            self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')
            return True
        else:
            return False

    def new_round_ap(self):
        self.check_record()
        basic_ap = 10

        actor_bonus = Actor(self.actor_id, data_manager=self.data_manager).get_capacity_or_armor_skill('Power') / 10

        ap_bonus = self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.actor_id}')[0].get('ap_bonus')
        ap_bonus = ap_bonus if ap_bonus is not None else 0
        self.data_manager.update('CHARS_COMBAT', {'ap': basic_ap + ap_bonus + actor_bonus, 'ap_bonus': 0}, f'id = {self.actor_id}')


class ActorDeath:
    def __init__(self, target_id:int, killer_id:int=None, reason:str=None, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.target = target_id
        self.killer = killer_id
        self.reason = reason

    def check_death(self):
        body = Body(self.target, data_manager=self.data_manager)
        if body.is_dead()[0]:
            Notification.create_notification('Смерть', f'Персонаж {Actor(self.target).get_character().name} погиб{f"от рук {Actor.get_actor_character(self.killer).name}" if self.killer else ""}...\n-# Причина смерти: {self.reason}', self.target, type='danger')
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

    def get_character(self):
        from ArbCharacters import Character
        character: Character = Character(self.actor_id, data_manager=self.data_manager)
        return character

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
                log = self.AM()
                if self.is_dead():
                    log.action('Смерть', '-# Вы погибли и не можете совершать действия', RespondIcon.danger())
                    return log
                if not self.is_active:
                    log.action('Активность','-# Вы не можете совершать действия не на своём ходу', RespondIcon.failure())
                    return log
                return method(self, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def ap_required(cost:int=1):
        def decorator(method):
            @wraps(method)
            def wrapper(self, *args, **kwargs):
                result = self.ap.action_use(cost)
                if not result:
                    log = self.AM()
                    log.action('Недостаточно ОД', f'-# *У персонажа **{self.get_character().name}** не хватает очков действия!*', RespondIcon.info())
                    return log
                else:
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
        self.status().dead_clear(self.actor_id)
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

    def get_ap(self) -> 'APManager':
        return APManager(self.actor_id, data_manager=self.data_manager)

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

    def get_capacity_or_armor_skill(self, capacity:str) -> int:
        body_capacity = self.get_capacity(capacity) if self.get_capacity(capacity) is not None else 0
        armor_skill = self.get_armor_skill(capacity) if self.get_armor_skill(capacity) is not None else 0
        return max(body_capacity, armor_skill)

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

    def ap_use(self, ap:int) -> bool:
        if not ap:
            ap = 0
        result = self.ap.action_use(ap)
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
        stealth_modificator = 0.75 + stealth_skill_value * 0.005
        stealth_armor_skill = self.get_armor_skill('Stealth')
        stealth_capacity = self.get_capacity('Stealth')

        total_armor_factor = (stealth_armor_skill + clothes_disguise) / 2 if stealth_armor_skill >= clothes_disguise else clothes_disguise

        total_disguise = (total_armor_factor + max(race_disguise, stealth_capacity) + object_disguise) * stealth_modificator

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
    def reload(self, ammo_id:str = None) -> 'ActionManager':
        from ArbWeapons import Weapon
        from ArbAmmo import Ammunition

        log = self.AM()

        weapon_item = self.get_weapon()
        if not weapon_item:
            log.action('Перезарядка', 'У вас нет оружия для перезарядки', RespondIcon.failure())
            return log

        weapon = Weapon(weapon_item.item_id, data_manager=self.data_manager)
        if weapon.weapon_class == 'ColdSteel':
            log.action('Перезарядка', 'Ваше оружие невозможно перезарядить', RespondIcon.failure())
            return log

        cost = weapon.reload_ap_cost
        ap_usage = self.ap_use(cost)

        if not ap_usage:
            log.action('Перезарядка', 'У вас не хватает очков действия для перезарядки', RespondIcon.info())
            return log

        reload_success = weapon.reload(ammo_id)

        if not reload_success:
            log.action('Перезарядка', f'Вы не смогли перезарядить оружие...', RespondIcon.info())
            return log

        equiped_ammo = Ammunition(weapon.get_current_ammotype(), data_manager=self.data_manager)
        text = f'''-# Нажав на фиксатор магазина и выкинув разряженную обойму на землю, попутно доставая второй рукой новую из подсумки. Как только старая обойма вышла из гнезда магазина, вы вставили новую обойму **{equiped_ammo.label}** **(Калибр: {equiped_ammo.caliber}, Тип: {equiped_ammo.type})**, и, зафиксировав ее, вы передергиваете затвор своего оружия - **{weapon.label}**
'''
        log.action('Перезарядка', f'{text}', RespondIcon.success())
        return log

    @actor_status()
    @log_battle_event('Персонаж обнаруживает звук')
    def detect_sound(self, sound_id:int) -> ResponsePool:
        return ActorSounds(self).detect_sound(sound_id)

    @actor_status()
    @log_battle_event('Персонаж переходит в режим ожидания, перенося свои ОД на свой следующий ход')
    def waiting(self) -> 'ActionManager':
        log = self.AM()
        current_ap = self.ap.ap
        self.set_ap_bonus(current_ap)
        self.clear_ap()
        log.action('Ожидание', f'Вы ожидаете следующей возможности для действий и завершаете свой ход...')
        return log

    @actor_status()
    @log_battle_event('Персонаж начинает охоту на другого персонажа')
    def set_hunt(self, enemy_id: int) -> 'ActionManager':
        from ArbWeapons import Weapon
        log = self.AM()
        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['SR', 'AR', 'PST', 'TUR']:
            log.action('Невозможно охотиться', f'У вас нет оружия дальнего боя подходящего для охоты на противника или ваши конечности слишком повреждены чтобы стрелять', RespondIcon.info())
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if not ap_usage:
            log.action('Невозможно охотиться', f'У вас не хватает очков действий для совершения действия', RespondIcon.failure())
            return log


        self.clear_tactical_status()
        self.data_manager.update('CHARS_COMBAT', {'hunted': enemy_id}, f'id = {self.actor_id}')
        log.action('Охота', f'Вы наводитесь на {Actor.get_actor_character(enemy_id).name} и внимательно следите за его действиями, чтобы нанести атаку в удачный момент', RespondIcon.success())
        return log

    @actor_status()
    @log_battle_event('Персонаж начинает подавлять укрытие')
    def set_suppression(self, cover_id: int) -> 'ActionManager':
        from ArbWeapons import Weapon

        log = self.AM()

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['MG', 'AR', 'TUR']:
            log.action('Невозможно подавлять', f'У вас нет оружия дальнего боя подходящего для подавления укрытия или ваши конечности слишком повреждены чтобы стрелять', RespondIcon.failure())
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if not ap_usage:
            log.action('Невозможно подавлять', f'У вас не хватает очков действий для совершения действия', RespondIcon.failure())
            return log

        self.clear_tactical_status()
        self.data_manager.update('CHARS_COMBAT', {'supressed': cover_id}, f'id = {self.actor_id}')

        log.action('Подавление', f'Вы наводитесь на укрытие и начинаете подавлять его огнём не давая возможному противнику шанса высунуться без последствий', RespondIcon.success())
        return log

    @actor_status()
    @log_battle_event('Персонаж начинает подавлять слой')
    def set_containment(self, layer_id: int) -> 'ActionManager':
        from ArbWeapons import Weapon

        log = self.AM()
        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['MG', 'AR', 'TUR']:
            log.action('Невозможно сдерживать', f'У вас нет оружия дальнего боя подходящего для сдерживания слоя или ваши конечности слишком повреждены чтобы стрелять', RespondIcon.info())
            return log

        if layer_id not in [self.layer_id-1, self.layer_id+1, self.layer_id]:
            log.action('Невозможно сдерживать', f'Вы можете сдерживать только текущий слой и ближайшие слои', RespondIcon.info())
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if not ap_usage:
            log.action('Невозможно сдерживать', f'У вас не хватает очков действий для совершения действия', RespondIcon.info())
            return log

        self.clear_tactical_status()
        self.data_manager.update('CHARS_COMBAT', {'contained': layer_id}, f'id = {self.actor_id}')

        log.action('Сдерживание', f'Вы наводитесь и открываете выборочный огонь по всему слою, не давая противнику шанса продвинуться ближе к вам без последствий')
        return log

    @actor_status()
    @log_battle_event('Персонаж переходит в режим дозора')
    def set_overwatch(self) -> 'ActionManager':
        from ArbWeapons import Weapon
        log = self.AM()
        weapon = self.get_weapon()

        if not weapon:
            log.action('Дозор невозможен',
                       f'У вас нет оружия дальнего боя подходящего для сдерживания слоя или ваши конечности слишком повреждены чтобы стрелять',
                       RespondIcon.info())
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if not ap_usage:
            log.action('Дозор невозможен', f'У вас не хватает очков действий для совершения действия',
                       RespondIcon.info())
            return log

        self.clear_tactical_status()
        self.data_manager.update('CHARS_COMBAT', {'ready': 1}, f'id = {self.actor_id}')
        log.action('Дозор', f'Вы внимательно оглядываетесь по сторонам в ожидании атаки противника...', RespondIcon.success())
        return log

    def check_enemy_id(self, enemy_id: int) -> bool:
        if self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {enemy_id} AND battle_id = {self.battle_id}'):
            return True
        else:
            return False

    @actor_status()
    @log_battle_event('Персонаж наводится на новую цель')
    def set_target(self, target_id:int) -> 'ActionManager':
        log = self.AM()

        melees = self.status().melees
        if melees or self.get_melee_target():
            log.action('Ближний бой', f'Персонаж **{self.get_character().name}** находится в ближнем бою и не может прицелиться', RespondIcon.failure())
            return log

        if not self.check_enemy_id(target_id):
            log.action('Цель', 'Персонажа с данным ID нет в текущем бою, вы не можете сделать его своей целью', RespondIcon.failure())
            return log

        self.data_manager.update('CHARS_COMBAT', {'target': target_id}, f'id = {self.actor_id}')
        log.action('Прицеливание', 'Вы наводитесь на предполагаемое местоположение противника и готовы к атаке', RespondIcon.success())
        return log

    @actor_status()
    @log_battle_event('Персонаж навязывает ближний бой противнику')
    def set_melee_target(self, target_id:int) -> 'ActionManager':
        log = self.AM()

        if not self.check_enemy_id(target_id):
            log.action('Ближний бой', 'Персонажа с данным ID нет в текущем бою, вы не можете с ним сблизиться', RespondIcon.failure())
            return log

        if not self.data_manager.check('BATTLE_CHARACTERS', f'character_id = {target_id} AND layer_id = {self.layer_id}'):
            log.action('Ближний бой', 'Цель находится слишком далеко, вы не можете с ней сблизиться!', RespondIcon.failure())
            return log

        if Actor(target_id, data_manager=self.data_manager).fly_height != self.fly_height:
            fly_capacity = self.get_capacity('Flying')
            fly_armor_skill = self.get_armor_skill('Flying')
            if not fly_capacity and not fly_armor_skill:
                log.action('Ближний бой', f'Противник находится в воздухе и вы не можете подняться выше...', RespondIcon.failure())
                return log
            else:
                ActorMovement(self).set_fly_height(Actor(target_id, data_manager=self.data_manager).fly_height)

        melee_targets = self.get_melee_target_from()

        ap_usage = self.ap_use(1) if target_id not in melee_targets else True

        if not ap_usage:
            log.action('Ближний бой', f'У вас не хватает очков действия для совершения действия', RespondIcon.failure())
            return log

        log.log = self.status().trigger_melees(log.log)
        log.log = self.status().trigger_suppressors(log.log)

        self.clear_tactical_status()
        self.clear_targets()

        self.data_manager.update('BATTLE_CHARACTERS', {'object': None}, f'character_id = {self.actor_id}')
        self.data_manager.update('CHARS_COMBAT', {'melee_target': target_id}, f'id = {self.actor_id}')
        Actor(target_id, data_manager=self.data_manager).clear_tactical_status()
        self.data_manager.update('BATTLE_CHARACTERS', {'object': None}, f'character_id = {target_id}')
        self.data_manager.update('CHARS_COMBAT', {'melee_target': self.actor_id}, f'id = {target_id}')

        log.action('Ближний бой',f'{self.get_character().name} сближается с ``{self.get_actor_character(target_id).name}`` и навзяывает ему ближний бой', RespondIcon.success())

        return log

    @actor_status()
    @log_battle_event('Персонаж сбегает из ближнего боя')
    def flee_from_melee(self):
        log = self.AM()
        log.log = ActorMovement(self).flee_from_melee(log)
        return log

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

    def AM(self):
        log = ActionManager(self.actor_id, data_manager=self.data_manager)
        return log

    def status(self):
        return StatusManager(self.actor_id, data_manager=self.data_manager)

    @actor_status()
    @log_battle_event('Персонаж использует своё оружие для дальней атаки')
    def range_attack(self, enemy_id: int = None) -> 'ActionManager':
        from ArbWeapons import Weapon
        log = self.AM()

        enemy_id = self.get_target() if enemy_id is None else enemy_id
        if enemy_id is None:
            log.action('Стрельба невозможна', 'У персонажа нет активной цели для атаки', RespondIcon.failure())
            return log

        weapon = self.get_weapon()

        if not weapon or Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class == 'ColdSteel':
            log.action('Стрельба невозможна', 'У персонажа нет оружия дальнего боя для совершения атаки или ваши конечности слишком повреждены чтобы стрелять', RespondIcon.failure())
            return log

        status = self.status()

        melee_from = status.melees
        print(Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class, Weapon(weapon.item_id, data_manager=self.data_manager))
        if (melee_from or self.get_melee_target()) and Weapon(weapon.item_id, data_manager=self.data_manager).weapon_class not in ['PST', 'SG', 'SMG']:
            log.action('Стрельба невозможна',
                       'Персонаж не может стрелять из данного оружия пока находится в ближнем бою',
                       RespondIcon.failure())
            log.log = self.status().trigger_melees(log.log)
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)

        if not ap_usage:
            log.action('Стрельба невозможна', 'Персонажу не хватает очков действия для совершения данного действия', RespondIcon.failure())
            return log
        print('ДО ТРИГГЕРА', log.log)
        log.log = self.status().trigger_hunters(log.log)
        log.log = self.status().trigger_suppressors(log.log)
        print('ПОСЛЕ ТРИГГЕРА', log.log)

        print(log.__dict__)

        overwatch_response = status.trigger_overwatch(enemy_id, self.actor_id, log)
        print('ДОЗОР:', overwatch_response)
        if overwatch_response:
            log.log = overwatch_response
            return log

        log = log
        print(log.__dict__)

        attack_result = RangeAttack(self, weapon.item_id, data_manager=self.data_manager).attack(enemy_id)

        if attack_result:
            log.action('Стрельба', f'Вы открываете огонь из {weapon.label} по ``{Actor.get_actor_character(enemy_id).name}``!', RespondIcon.success())
        else:
            log.action('Неудачная стрельба',
                       f'Вы открываете огонь из {weapon.label} по ``{Actor.get_actor_character(enemy_id).name}``, но она не увенчалась успехом',
                       RespondIcon.failure())

        if self.is_enemy_dead(enemy_id):
            log.log.response_to_respond(self.respond_if_enemy_dead())

        print(log.__dict__)
        return log


    @actor_status()
    @log_battle_event('Персонаж использует оружие для атаки в ближнем бою')
    def melee_attack(self, enemy_id:int = None) -> 'ActionManager':
        from ArbWeapons import Weapon

        log = self.AM()

        melee_from = self.status().melees
        if enemy_id not in melee_from or enemy_id is None:
            enemy_id = self.get_melee_target()

        if not enemy_id:
            log.action('Атака невозможна', 'У персонажа нет целей для атаки в ближнем бою', RespondIcon.failure())
            return log

        weapon = self.get_weapon()
        if not weapon:
            log.action('Атака невозможна', 'У персонажа нет оружия для совершения атаки или его конечности слишком повреждены чтобы совершить атаку', RespondIcon.failure())
            return log

        ap_usage = self.ap_use(Weapon(weapon.item_id, data_manager=self.data_manager).action_points)
        if not ap_usage:
            log.action('Невозможно атаковать', 'У персонажа недостаточно очков действия для совершения атаки', icon=RespondIcon.failure())
            return log


        log.log = self.status().trigger_melees()
        attack_result = MeleeAttack(self, weapon.item_id, data_manager=self.data_manager).attack(enemy_id)
        if attack_result.success:
            log.action('Ближний бой', f'{self.get_character().name} атакует ``{Actor.get_actor_character(enemy_id).name}`` при помощи {weapon.label} в ближнем бою!', RespondIcon.success())
        else:
            log.action('Ближний бой', f'{self.get_character().name} атакует ``{Actor.get_actor_character(enemy_id).name}`` при помощи {weapon.label} в ближнем бою, но атака не увенчалась успехом', RespondIcon.failure())

        if self.is_enemy_dead(enemy_id):
            log.log.response_to_respond(self.respond_if_enemy_dead())

        return log

    @actor_status()
    @log_battle_event('Персонаж использует расовую атаку')
    def race_attack(self, enemy_id: int = None, race_attack: str=None) -> 'ActionManager':
        from ArbWeapons import RaceAttack

        log = self.AM()

        enemy_id = self.get_melee_target() if enemy_id is None else enemy_id
        enemy_id = self.get_target() if enemy_id is None else enemy_id

        if not enemy_id:
            log.action('Атака невозможна', 'У персонажа нет целей для атаки в ближнем бою', RespondIcon.failure())
            return log


        attacks = self.get_race_attacks(race_attack)
        if not attacks:
            log.action('Невозможно атаковать', f'У вас нет доступных атак, которые вы могли бы применить или у вас нет указанной атаки!', RespondIcon.failure())
            return log

        attack = random.choice(attacks)

        distance_to_enemy = self.calculate_total_distance(enemy_id)
        if distance_to_enemy > RaceAttack(attack, data_manager=self.data_manager).range:
            log.action('Невозможно атаковать', f'Цель находится слишком далеко для совершения расовой атаки!', RespondIcon.failure())
            return log

        ap_usage = self.ap_use(RaceAttack(attack, data_manager=self.data_manager).ap_cost)

        if not ap_usage:
            log.action('Невозможно атаковать', 'У вас не хватает очков действий для совершения действи', RespondIcon.failure())
            return log

        log.log = self.status().trigger_hunters()
        log.log = self.status().trigger_suppressors()

        attack_result = BodyPartAttack(self, attack, data_manager=self.data_manager).attack(enemy_id)
        if attack_result.success:
            log.action('Боевой приём', f'{self.get_character().name} готовится к {RaceAttack(attack, data_manager=self.data_manager).label} и атакует ``{Actor.get_actor_character(enemy_id).name}``!', RespondIcon.success())
        else:
            log.action('Неудачный приём', f'{self.get_character().name} готовится к {RaceAttack(attack, data_manager=self.data_manager).label} и атакует ``{Actor.get_actor_character(enemy_id).name}``, но атака не увенчалась успехом!', RespondIcon.failure())

        if self.is_enemy_dead(enemy_id):
            log.log.response_to_respond(self.respond_if_enemy_dead())

        return log

    @actor_status()
    @log_battle_event('Персонаж бросает гранату')
    def throw_grenade(self, enemy_id: int = None, grenade_id: int=None) -> 'ActionManager':
        log = self.AM()

        melee_from = self.status().melees
        if melee_from or self.get_melee_target():
            log.action('Невозможно бросить гранату', f'Вы не можете бросить гранату находясь в ближнем бою!', RespondIcon.failure())
            return log

        enemy_id = self.get_target() if enemy_id is None else enemy_id
        if not enemy_id:
            log.action('Невозможно бросить гранату', 'У персонажа нет целей для броска', RespondIcon.failure())
            return log

        distance_to_enemy = self.calculate_total_distance(enemy_id)
        if distance_to_enemy > 50:
            log.action('Невозможно бросить гранату', f'Цель находится слишком далеко для броска гранаты', RespondIcon.failure())
            return log

        grenades = self.get_grenades(grenade_id)
        if not grenades:
            log.action('Невозможно бросить гранату', f'У вас нет доступных гранат для броска или у отсутствует указанная граната!', RespondIcon.failure())
            return log

        ap_usage = self.ap_use(3)

        if not ap_usage:
            log.action('Невозможно бросить гранату', 'У вас не хватает очков действия для совершения действия', RespondIcon.failure())
            return log

        log.log = self.status().trigger_hunters(log.log)
        log.log = self.status().trigger_melees(log.log)
        log.log = self.status().trigger_suppressors(log.log)

        grenade = random.choice(grenades)
        grenade_item = Item(grenade, data_manager=self.data_manager)
        attack_result = ThrowGrenade(self, grenade, data_manager=self.data_manager).attack(enemy_id)

        log.action('Бросок гранаты', f'{self.get_character().name} бросает {grenade_item.label} на позицию ``{Actor.get_actor_character(enemy_id).name}``!', RespondIcon.success())

        if self.is_enemy_dead(enemy_id):
            log.log.response_to_respond(self.respond_if_enemy_dead())

        return log

    @actor_status()
    @log_battle_event('Персонаж движется на другой слой')
    def move_to_layer(self, layer_id: int) -> 'ActionManager':
        result = ActorMovement(self).move_to_layer(layer_id)

        return result

    @actor_status()
    @log_battle_event('Персонаж движется к объекту')
    def move_to_object(self, object_id: int) -> 'ActionManager':
        result = ActorMovement(self).move_to_object(object_id)
        return result

    @actor_status()
    @log_battle_event('Персонаж сбегает из боя')
    def escape(self) -> 'ActionManager':
        result = ActorMovement(self).escape()
        return result

    @actor_status()
    @log_battle_event('Персонаж взлетает')
    def fly(self, height) -> 'ActionManager':
        return ActorMovement(self).fly(height)

    @actor_status()
    @log_battle_event('Персонаж взаимодействует с объектом')
    def interact_with_object(self, enemy_id:int=None) -> 'ActionManager':
        log = self.AM()
        object = self.get_object()
        if not object:
            log.action('Взаимодействие с объектом', 'Вы не находитесь рядом с объектом, с которым можно взаимодействовать', RespondIcon.info())
            return log

        ap_usage = self.ap_use(2)

        if not ap_usage:
            log.action('Взаимодействовать невозможно', f'У вас не хватает очков действий для совершения действия', RespondIcon.info())
            return log

        self.make_sound('Interaction', random.randint(50, 150))

        log.log = self.status().trigger_melees(log.log)
        log.log = self.status().trigger_suppressors(log.log)
        result = object.interact(self.actor_id, enemy_id=enemy_id)
        log.log.response_to_respond(result)

        if enemy_id:
            if self.is_enemy_dead(enemy_id):
                log.log.response_to_respond(self.respond_if_enemy_dead())

        return log

    @actor_status()
    def reset_statuses(self) -> 'ActionManager':
        log = self.AM()
        StatusManager.clear_all_statuses(self.actor_id)
        current_tactics = self.status().get_tactics()
        tactics = ''
        for tactic, value in current_tactics.items():
            tactics += f'-# *{tactic} - **{value}***\n'

        log.action('Сброс тактик', f'{self.get_character().name} прекращает использовать текущую тактику:\n{tactics}', RespondIcon.success())
        return log

    @staticmethod
    def get_actor_character(actor_id:int):
        from ArbCharacters import Character
        return Character(actor_id)

    def __repr__(self):
        return f'Actor({self.actor_id})'



class APManager:
    def __init__(self, actor_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager') if kwargs.get('data_manager') else DataManager()
        self.actor_id = actor_id
        data = self.get_ap_data()

        self.ap = data.get('ap')
        self.ap_bonus = data.get('ap_bonus')

    def add_ap(self, amount:int):
        self.ap += amount
        self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')
        return self.ap

    def add_ap_bonus(self, amount:int):
        self.ap_bonus += amount
        self.data_manager.update('CHARS_COMBAT', {'ap_bonus': self.ap_bonus}, f'id = {self.actor_id}')
        return self.ap_bonus

    def convert_ap_to_bonus(self):
        self.ap_bonus += self.ap
        self.data_manager.update('CHARS_COMBAT', {'ap': 0, 'ap_bonus': self.ap_bonus}, f'id = {self.actor_id}')
        self.ap = 0
        return self.ap_bonus

    def action_use(self, cost:int):
        if self.ap >= cost:
            self.ap -= cost
            self.data_manager.update('CHARS_COMBAT', {'ap': self.ap}, f'id = {self.actor_id}')
            return True
        else:
            return False

    def check_record(self):
        if not self.data_manager.check('CHARS_COMBAT', f'id = {self.actor_id}'):
            query = {
                'id': self.actor_id,
                'ap': 0,
                'ap_bonus': 0
            }
            self.data_manager.insert('CHARS_COMBAT', query)

    def get_ap_data(self):
        self.check_record()
        return self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.actor_id}')[0]







class StatusManager(DataModel):
    def __init__(self, actor_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager') if kwargs.get('data_manager') else DataManager()
        self.actor_id = actor_id
        StatusManager.check_record(self.actor_id)
        DataModel.__init__(self, 'CHARS_COMBAT', f'id = {actor_id}', data_manager=self.data_manager)

        self.suppressing_cover = self.get('supressed', None)
        self.hunting_target = self.get('hunted', None)
        self.is_overwatching = self.get('ready', False)
        self.containing_layer = self.get('contained', None)

        self.suppressors = StatusManager.get_actor_suppressors(self.actor_id, data_manager=self.data_manager)
        self.hunters = StatusManager.get_actor_hunters(self.actor_id, data_manager=self.data_manager)
        self.containers = StatusManager.get_actor_containers(self.actor_id, data_manager=self.data_manager)
        self.melees = StatusManager.get_actor_melee(self.actor_id, data_manager=self.data_manager)

    def get_tactics(self):
        tactics = {}
        if self.suppressing_cover is not None:
            tactics['Подавление'] = GameObject(self.suppressing_cover).__str__()
        if self.hunting_target is not None:
            tactics['Охота'] = Actor.get_actor_character(self.hunting_target).name
        if self.is_overwatching is not None:
            tactics['Дозор'] = 'Активен'
        if self.containing_layer is not None:
            tactics['Сдерживание'] = Layer(self.containing_layer, Actor(self.actor_id, data_manager=self.data_manager).battle_id).__str__()

        return tactics

    def range_trigger(self, enemy_id:int, target_id:int) -> Response:
        enemy = Actor(enemy_id)
        weapon = enemy.get_weapon()
        if weapon:
            attack_result = RangeAttack(enemy, weapon.item_id, data_manager=enemy.data_manager).attack(target_id)
        else:
            attack_result = Response(False, f'{enemy.get_character().name} перехватывает вас и атакует издалека, но его атака не увенчалась успехом', 'Неудачный перехват')

        if attack_result:
            return Response(False, f'{enemy.get_character().name} перехватывает вас и атакует издалека!', 'Перехват')
        else:
            return Response(False, f'{enemy.get_character().name} перехватывает вас и атакует издалека, но в этот момент вместо выстрелов вы слышите глухие щелчки', 'Перехват')

    def melee_trigger(self, enemy_id:int, target_id:int) -> Response:
        enemy = Actor(enemy_id)
        weapon = enemy.get_weapon()
        if weapon:
            attack_result = MeleeAttack(enemy, weapon.item_id, data_manager=enemy.data_manager).attack(target_id)
        else:
            attack_result = BodyPartAttack(enemy, random.choice(enemy.get_race_attacks()), data_manager=enemy.data_manager).attack(target_id)

        if attack_result:
            return Response(False, f'{enemy.get_character().name} воспользовавшись моментом атакует вас в ближнем бою!', 'Ближний бой')
        else:
            return Response(False, f'{enemy.get_character().name} воспользовавшись моментом атакует вас в ближнем бою, но его атака провалилась', 'Ближний бой')

    def trigger_hunters(self, respond_log: RespondLog = None) -> RespondLog:
        respond_log = respond_log if respond_log else RespondLog(self.data_manager,
                                                                 footer=Actor(self.actor_id, data_manager=self.data_manager).get_character().name,
                                                                 footer_logo=Actor(self.actor_id, data_manager=self.data_manager).get_character().picture)

        if not self.hunters:
            return respond_log

        for hunter_id in self.hunters:
            result = self.range_trigger(hunter_id, self.actor_id)
            respond_log.response_to_respond(result, 'Охота', RespondIcon.danger())
            StatusManager.clear_hunt(hunter_id)

        return respond_log

    def trigger_suppressors(self, respond_log: RespondLog = None) -> RespondLog:
        respond_log = respond_log if respond_log else RespondLog(self.data_manager,
                                                                 footer=Actor(self.actor_id, data_manager=self.data_manager).get_character().name,
                                                                 footer_logo=Actor(self.actor_id, data_manager=self.data_manager).get_character().picture)

        if not self.suppressors:
            return respond_log

        for suppressor_id in self.suppressors:
            result = self.range_trigger(suppressor_id, self.actor_id)
            respond_log.response_to_respond(result, 'Подавление', RespondIcon.danger())

        return respond_log

    def trigger_containers(self, respond_log: RespondLog = None) -> RespondLog:
        respond_log = respond_log if respond_log else RespondLog(self.data_manager,
                                                                 footer=Actor(self.actor_id, data_manager=self.data_manager).get_character().name,
                                                                 footer_logo=Actor(self.actor_id, data_manager=self.data_manager).get_character().picture)

        if not self.containers:
            return respond_log

        for container_id in self.containers:
            result = self.range_trigger(container_id, self.actor_id)
            respond_log.response_to_respond(result, 'Сдерживание', RespondIcon.danger())

        return respond_log

    def trigger_melees(self, respond_log: RespondLog = None) -> RespondLog:
        respond_log = respond_log if respond_log else RespondLog(self.data_manager,
                                                                 footer=Actor(self.actor_id, data_manager=self.data_manager).get_character().name,
                                                                 footer_logo=Actor(self.actor_id, data_manager=self.data_manager).get_character().picture)

        if not self.melees:
            return respond_log

        for melee_id in self.melees:
            result = self.melee_trigger(melee_id, self.actor_id)
            respond_log.response_to_respond(result, 'Ближний бой', RespondIcon.danger())

        return respond_log

    @staticmethod
    def clear_all_statuses(actor_id:int):
        query = {'hunted': None,
                 'supressed': None,
                 'contained': None,
                 'ready': None}
        db = DataManager()
        db.update('CHARS_COMBAT', query, f'id = {actor_id}')

    @staticmethod
    def clear_target(actor_id:int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'target': None}, f'id = {actor_id}')

    @staticmethod
    def clear_melee_target(actor_id:int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'melee_target': None}, f'id = {actor_id}')

    @staticmethod
    def trigger_overwatch(actor_id:int, attacker_id:int, log: 'ActionManager'):
        db = DataManager()
        data = db.select_dict('CHARS_COMBAT', filter=f'id = {actor_id}')
        if not data:
            StatusManager.check_record(actor_id)

        data = data[0]
        is_ready = int(data.get('ready', False)) if data.get('ready', False) else False
        print('СТАТУС ДОЗОРА:', is_ready)
        if is_ready:
            StatusManager.clear_overwatch(actor_id)
            enemy = Actor(actor_id)
            weapon = enemy.get_weapon()

            attack_result = RangeAttack(enemy, weapon.item_id, data_manager=enemy.data_manager).attack(attacker_id)
            if not attack_result:
                return None
            log.action(f'Дозор противника',f'{enemy.get_character().name}, находясь в дозоре, перехватывает вас и атакует издалека!', RespondIcon.danger())
            return log.log
        else:
            return None

    @staticmethod
    def check_record(actor_id:int):
        db = DataManager()
        if not db.check('CHARS_COMBAT', f'id = {actor_id}'):
            query = {'id': actor_id, 'ap': 0, 'ap_bonus':0}
            db.insert('CHARS_COMBAT', query)

    @staticmethod
    def get_actor_suppressors(actor_id:int, data_manager:DataManager() = None):
        db = DataManager() if not data_manager else data_manager
        data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not data:
            return []
        data = data[0]
        if not data.get('object'):
            return []

        object_id = data.get('object')
        supressors = db.select_dict('CHARS_COMBAT', filter=f'supressed = {object_id}')
        return [sup.get('id') for sup in supressors]

    @staticmethod
    def get_actor_hunters(actor_id:int, data_manager: DataManager = None):
        db = DataManager() if not data_manager else data_manager
        data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not data:
            return []
        data = data[0]

        battle_id = data.get('battle_id')
        potential_hunters = [i.get('character_id') for i in db.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {battle_id}')]

        hunters = []
        for hunter in potential_hunters:
            hunter_data = db.select_dict('CHARS_COMBAT', filter=f'id = {hunter}')
            if not hunter_data:
                continue
            hunter_data = hunter_data[0]
            if hunter_data.get('hunted') == actor_id:
                hunters.append(hunter)

        return hunters

    @staticmethod
    def get_actor_containers(actor_id: int, data_manager: DataManager = None):
        db = DataManager() if not data_manager else data_manager
        data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not data:
            return []
        data = data[0]

        battle_id = data.get('battle_id')
        layer_id = data.get('layer_id')

        potential_containers = [i.get('character_id') for i in
                             db.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {battle_id}')]

        containers = []
        for hunter in potential_containers:
            hunter_data = db.select_dict('CHARS_COMBAT', filter=f'id = {hunter}')
            if not hunter_data:
                continue
            hunter_data = hunter_data[0]
            if hunter_data.get('contained') == layer_id:
                containers.append(hunter)

        return containers

    @staticmethod
    def get_actor_melee(actor_id: int, data_manager: DataManager = None):
        db = DataManager() if not data_manager else data_manager
        data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {actor_id}')
        if not data:
            return []
        data = data[0]

        battle_id = data.get('battle_id')
        potential_melee = [i.get('character_id') for i in db.select_dict('BATTLE_CHARACTERS', filter=f'battle_id = {battle_id}')]

        melees = []
        for hunter in potential_melee:
            hunter_data = db.select_dict('CHARS_COMBAT', filter=f'id = {hunter}')
            if not hunter_data:
                continue
            hunter_data = hunter_data[0]
            if hunter_data.get('melee_target') == actor_id:
                melees.append(hunter)

        return melees

    @staticmethod
    def clear_melees(actor_id: int):
        db = DataManager()
        status = StatusManager(actor_id, data_manager=db)
        for melee in status.melees:
            status.clear_melee_target(melee)

    @staticmethod
    def clear_hunters(actor_id: int):
        db = DataManager()
        status = StatusManager(actor_id, data_manager=db)
        for hunter in status.hunters:
            db.update('CHARS_COMBAT', {'hunted': None}, f'id = {hunter}')

    @staticmethod
    def dead_clear(actor_id: int):
        StatusManager.clear_all_statuses(actor_id)
        StatusManager.clear_melee_target(actor_id)
        StatusManager.clear_melees(actor_id)
        StatusManager.clear_hunters(actor_id)

    @staticmethod
    def clear_hunt(actor_id: int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'hunted': None}, f'id = {actor_id}')

    @staticmethod
    def clear_contained(actor_id: int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'contained': None}, f'id = {actor_id}')

    @staticmethod
    def clear_suppress(actor_id: int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'supressed': None}, f'id = {actor_id}')

    @staticmethod
    def clear_overwatch(actor_id: int):
        db = DataManager()
        db.update('CHARS_COMBAT', {'ready': None}, f'id = {actor_id}')

    @staticmethod
    def clear_targeters(actor_id:int):
        db = DataManager()
        targeters = StatusManager.get_targeters(actor_id)
        for t in targeters:
            db.update('CHARS_COMBAT', {'target': None}, f'id = {t}')

    @staticmethod
    def get_targeters(actor_id:int):
        db = DataManager()
        targeters = db.select_dict('CHARS_COMBAT', filter=f'target = {actor_id}')
        return [t.get('id') for t in targeters]


class ActionManager:
    def __init__(self, actor_id:int, **kwargs):
        self.actor_id = actor_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.log = RespondLog(self.data_manager,
                              footer=Actor(self.actor_id, data_manager=self.data_manager).get_character().name,
                              footer_logo=Actor(self.actor_id, data_manager=self.data_manager).get_character().picture) if not kwargs.get('log') else kwargs.get('log')

    def action(self, title:str, content:str, icon: str = RespondIcon.info()):
        self.log.add_respond(title, content, respond_icon=icon)
