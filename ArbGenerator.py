import datetime
import string

from ArbDatabase import DataManager
import pprint
import random
from ArbUtils.ArbTextgen import CallsGenerator
from typing import List, Dict, Optional
from dataclasses import dataclass
from ArbUtils.ArbDataParser import process_string
import networkx as nx
import matplotlib.pyplot as plt
from itertools import combinations
import re



class RandomQuality:
    @staticmethod
    def generate_quality(needed_quality: str = None) -> str:
        if needed_quality:
            return needed_quality

        c_roll = random.randint(1, 100)
        if c_roll <= 70:
            return 'Нормальное'
        elif 70 < c_roll:
            if random.randint(0, 100) >= 99:
                return random.choice(['Легендарное', 'Шедевральное'])
            else:
                return random.choice(['Ужасное', 'Плохое', 'Хорошее', 'Отличное'])


class RandomMaterial:
    @staticmethod
    def generate_material(material_type: str, tier: int, needed_material: str = None, **kwargs) -> str:
        if needed_material:
            return needed_material

        db = kwargs.get('data_manager', DataManager())
        min_rarity = db.minValue('MATERIALS', 'rarity', f'type = "{material_type}"')

        c_roll = random.randint(min_rarity, 100)
        c_materials = [mat['id'] for mat in db.select_dict('MATERIALS', '*', f'type = "{material_type}" AND rarity <= {c_roll} AND tier <= {tier}')]
        return random.choice(c_materials)




class ItemManager:
    def __init__(self, item_type:str, **kwargs):
        self.item_type = item_type
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.item_table, self.item_class = self.get_item_class()
        self.item_label = kwargs.get('item_label', self.get_item_label())
        max_endurance = self.get_max_endurance()
        self.endurance = kwargs.get('endurance', random.randint(int(max_endurance * 0.4), int(max_endurance)))
        self.quality = RandomQuality.generate_quality(kwargs.get('quality', None))

        self.material_type = kwargs.get('material_type', None)
        self.material_tier = kwargs.get('material_tier', 0)

        self.material = self.generate_material(kwargs.get('material'))
        self.biocode = kwargs.get('biocode', None)
        self.inventory_id = kwargs.get('inventory', None)

    def generate_material(self, material: str=None):
        if material:
            return material

        material_type = self.material_type
        if not material_type:
            if self.item_class == 'Одежда':
                material_type = self.data_manager.select_dict('CLOTHES', filter=f'id = "{self.item_type}"')[0].get('material_type')
            elif self.item_class == 'Оружие':
                material_type = 'Металл'
            elif self.item_class == 'Граната':
                material_type = 'Металл'

        return RandomMaterial.generate_material(material_type, self.material_tier, None, data_manager=self.data_manager)

    def get_item_label(self):
        if self.data_manager.check(self.item_table, f'id = "{self.item_type}"'):
            return self.data_manager.select_dict(self.item_table, filter=f'id = "{self.item_type}"')[0].get('name', 'Неизвестный предмет')
        else:
            return 'Неизвестный предмет'

    def get_item_class(self):
        tables_to_find = ['CLOTHES', 'WEAPONS', 'ITEMS_INIT', 'AMMO']
        item_class = 'Разное'
        item_table = None

        for table in tables_to_find:
            if self.data_manager.check(table, f'id = "{self.item_type}"'):
                if table == 'CLOTHES':
                    item_class = 'Одежда'
                    item_table = 'CLOTHES'
                elif table == 'WEAPONS':
                    item_class = 'Оружие'
                    item_table = 'WEAPONS'
                elif table == 'ITEMS_INIT':
                    item_class = 'Предмет'
                    item_table = 'ITEMS_INIT'
                elif table == 'AMMO':
                    item_class = 'Граната'
                    item_table = 'AMMO'

                break

        else:
            item_class = 'Разное'
            item_table = None

        return item_table, item_class

    def get_max_endurance(self):
        if self.item_table == 'CLOTHES':
            return DataManager().select_dict('CLOTHES', filter=f'id="{self.item_type}"')[0].get('endurance')
        else:
            return 100

    def get_weapon_capacity(self):
        if self.item_table == 'WEAPONS':
            return DataManager().select_dict('WEAPONS', filter=f'id="{self.item_type}"')[0].get('mag')
        else:
            return 0

    def get_weapon_possible_ammo(self):
        from ArbWeapons import RangeWeapon
        if self.item_table == 'WEAPONS':
            return RangeWeapon(self.item_type).get_available_ammo()
        else:
            return []

    def spawn_item(self, equip_to_character: int = None):
        from ArbItems import CharacterEquipment, Item

        item_id = self.data_manager.maxValue('ITEMS', f'id') + 1
        query = {
            'id': item_id,
            'name': self.item_label,
            'type': self.item_type,
            'class': self.item_class,
            'material': self.material,
            'quality': self.quality,
            'endurance': self.endurance,
            'biocode': self.biocode,
            'inventory': self.inventory_id
        }
        self.data_manager.insert('ITEMS', query)

        if self.item_class == 'Оружие':

            mag_query = {
                'id': item_id,
                'bullets': self.get_weapon_capacity(),
                'ammo_id': random.choice(self.get_weapon_possible_ammo()) if self.get_weapon_possible_ammo() else None
            }

            self.data_manager.insert('ITEMS_BULLETS', mag_query)

        if self.item_class == 'Одежда' and equip_to_character:
            character_equipment = CharacterEquipment(equip_to_character, data_manager=self.data_manager)
            character_equipment.equip_cloth(item_id)

        return Item(item_id, data_manager=self.data_manager)











def NameGenerator(gender:str, with_surname:bool = False):
    if gender.lower() in ['м','мужской','мужчина','муж','male','m']:
        name = CallsGenerator('ArbUtils/data_models/male_names.csv').generate_text(use_trigrams=False)
    elif gender.lower() in ['ж','женский','женщина','девушка','жен','female','fem','f']:
        name = CallsGenerator('ArbUtils/data_models/female_names.csv').generate_text(use_trigrams=False)
    elif gender.lower() in ['робот','robot','ai','android', 'механизм', 'mech']:
        return CallsGenerator('ArbUtils/data_models/robot_names.csv').generate_text(use_trigrams=False)
    else:
        name = CallsGenerator('ArbUtils/data_models/male_names.csv').generate_text(use_trigrams=False)

    if with_surname:
        surname = CallsGenerator('ArbUtils/data_models/surnames.csv').generate_text(use_trigrams=False)
    else:
        surname = ''

    return f'{name}' + f' {surname}' if surname else f'{name}'

def TitleGenerator(type:str):
    if type.lower() == 'страна':
        return CallsGenerator('ArbUtils/data_models/countries.csv').generate_text(use_trigrams=False)
    elif type.lower() == 'система':
        return CallsGenerator('ArbUtils/data_models/systems_names.csv').generate_text(use_trigrams=False)
    elif type.lower() == 'город':
        return CallsGenerator('ArbUtils/data_models/towns.csv').generate_text(use_trigrams=False)
    else:
        return CallsGenerator('ArbUtils/data_models/systems_names.csv').generate_text(use_trigrams=False)


def create_inventory(label:str=None, owner:int=None, type:str=None, **kwargs):
    data_manager = kwargs.get('data_manager', DataManager())

    c_id = data_manager.maxValue('INVENTORY_INIT','id') + 1

    prompt = {
        'id': c_id,
        'label': label if label else f'Хранилище {c_id}',
        'owner': owner if owner else None,
        'type': type if type else 'Инвентарь'
    }

    data_manager.insert('INVENTORY_INIT', prompt)

    return c_id



class BaseCfg:
    def __init__(self, name:str=None,
                 callsign:str=None,
                 race:str=None,
                 gender:str=None,
                 age:int=None,
                 org:str=None,
                 org_lvl:int=None,
                 org_rank:str=None,
                 faction:str=None,
                 faction_lvl:int=None,
                 picture:str=None,
                 server_id:int=None,
                 data_manager: DataManager=None):

        self.data_manager = data_manager if data_manager else DataManager()

        self.callsign = callsign if callsign else None
        self.race = race if race else 'Human'
        self.gender = gender if gender else self.generate_gender()
        self.name = name if name else self.generate_name()
        self.age = age if age else random.randint(25, 45)

        self.org = org if org else 'Civil'
        self.org_lvl = org_lvl if org_lvl else 0
        self.org_rank = org_rank if org_rank else self.generate_rank()

        self.faction = faction if faction else None
        self.faction_lvl = faction_lvl if faction_lvl else None

        self.picture = picture if picture else None
        self.server = server_id if server_id else None

    def generate_name(self) -> str:
        from ArbRaces import Race

        race = Race(self.race, data_manager=self.data_manager)
        if race.is_robot:
            return NameGenerator('robot')
        elif race.is_primitive:
            return NameGenerator(self.gender)
        else:
            return NameGenerator(self.gender, with_surname=True)

    def generate_gender(self) -> str:
        from ArbRaces import Race

        race = Race(self.race, data_manager=self.data_manager)

        if race.is_robot:
            return 'Робот'
        else:
            return random.choice(['Мужской', 'Женский'])

    def check_org(self, org:str) -> bool:
        org_ids = [org.get('id') for org in self.data_manager.select_dict('ORG_INIT')]
        return org in org_ids

    def generate_rank(self):
        from ArbOrgs import Organization

        org = Organization(self.org, data_manager=self.data_manager)
        if self.org_lvl:
            return org.get_lvl_rank(self.org_lvl)
        else:
            return org.get_random_lowest_rank()

    def to_dict(self):
        return {
            'name': self.name,
            'callsign': self.callsign,
            'age': self.age,
            'race': self.race,
            'sex': self.gender,
            'org': self.org,
            'org_lvl': self.org_rank,
            'frac': self.faction,
            'frac_lvl': self.faction_lvl,
            'avatar': self.picture,
            'update': datetime.datetime.now().date().strftime('%Y-%m-%d'),
            'server': self.server
        }

    def export_to_text(self):
        text = ""
        if self.name is not None:
            text += f'setName "{self.name}";\n'
        if self.callsign is not None:
            text += f'setCallsign "{self.callsign}";\n'
        if self.race is not None:
            text += f'setRace "{self.race}";\n'
        if self.age is not None:
            text += f'setAge {self.age};\n'
        if self.org is not None:
            text += f'setOrg "{self.org}";\n'
        if self.org_rank is not None:
            text += f'setOrgRank "{self.org_rank}";\n'
        if self.faction is not None:
            text += f'setFaction "{self.faction}";\n'
        if self.faction_lvl is not None:
            text += f'setFactionRank "{self.faction_lvl}";\n'
        if self.picture is not None:
            text += f'setPicture "{self.picture}";\n'
        return text

    @staticmethod
    def import_from_text(text):
        params = {}

        name_match = re.search(r'setName "(.*?)";', text)
        if name_match:
            params['name'] = name_match.group(1)

        callsign_match = re.search(r'setCallsign "(.*?)";', text)
        if callsign_match:
            params['callsign'] = callsign_match.group(1)

        race_match = re.search(r'setRace "(.*?)";', text)
        if race_match:
            params['race'] = race_match.group(1)

        age_match = re.search(r'setAge (\d+);', text)
        if age_match:
            params['age'] = int(age_match.group(1))

        org_match = re.search(r'setOrg "(.*?)";', text)
        if org_match:
            params['org'] = org_match.group(1)

        org_rank_match = re.search(r'setOrgRank "(.*?)";', text)
        if org_rank_match:
            params['org_rank'] = org_rank_match.group(1)

        faction_match = re.search(r'setFaction "(.*?)";', text)
        if faction_match:
            params['faction'] = faction_match.group(1)

        faction_lvl_match = re.search(r'setFactionRank "(.*?)";', text)
        if faction_lvl_match:
            params['faction_lvl'] = faction_lvl_match.group(1)

        picture_match = re.search(r'setPicture "(.*?)";', text)
        if picture_match:
            params['picture'] = picture_match.group(1)

        return BaseCfg(**params)

    def __repr__(self):
        return f'{self.__dict__}'


class IdentifyCfg:
    def __init__(self,
                 worldview:str = None,
                 stress_points: int=None,
                 reputation: int=None,
                 loyalty: int=None,
                 data_manager: DataManager = None):

        self.data_manager = data_manager if data_manager else DataManager()
        self.worldview = worldview if worldview else self.generate_worldview()
        self.stress_points = stress_points if stress_points else random.randint(0,10)
        self.reputation = reputation if reputation else self.generate_reputation()
        self.loyalty = loyalty if loyalty else self.generate_loyalty()

    def generate_loyalty(self):
        return random.randint(0, 100)

    def generate_reputation(self):
        return random.randint(-500, 500)

    def generate_worldview(self):
        all_worldviews = [view.get('id') for view in self.data_manager.select_dict('WORLDVIEW')]
        if not all_worldviews:
            raise ValueError("No worldviews available in the database.")
        return random.choice(all_worldviews)

    def to_dict(self):
        return {
            'worldview': self.worldview,
            'stress': self.stress_points
        }

    def export_to_text(self):
        text = ''

        if self.worldview is not None:
            text += f'setWorldview "{self.worldview}";\n'
        if self.stress_points is not None:
            text += f'setStressPoints {self.stress_points};\n'
        if self.reputation is not None:
            text += f'setReputation {self.reputation};\n'
        if self.loyalty is not None:
            text += f'setLoyalty {self.loyalty};\n'

        return text

    @staticmethod
    def import_from_text(text):
        params = {}

        worldview_match = re.search(r'setWorldview "(.*?)";', text)
        if worldview_match:
            params['worldview'] = worldview_match.group(1)

        stress_points_match = re.search(r'setStressPoints (\d+);', text)
        if stress_points_match:
            params['stress_points'] = int(stress_points_match.group(1))

        reputation_match = re.search(r'setReputation (\d+);', text)
        if reputation_match:
            params['reputation'] = int(reputation_match.group(1))

        loyalty_match = re.search(r'setLoyalty (\d+);', text)
        if loyalty_match:
            params['loyalty'] = int(loyalty_match.group(1))

        return IdentifyCfg(**params)

    def __repr__(self):
        return f'{self.__dict__}'


class SkillCfg:
    def __init__(self, skill_id: str = None,
                 lvl: int = None,
                 talent: float = None,
                 mastery: float = None,
                 danger_level: int = 0):

        self.skill_id = skill_id if skill_id else ''
        self.talent = talent if talent is not None else self.generate_talent(danger_level)
        self.mastery = mastery if mastery is not None else self.generate_mastery(danger_level)
        self.lvl = lvl if lvl is not None else self.generate_level(danger_level)

    def generate_level(self, danger_level: int) -> int:
        # Уровень навыка основан на уровне опасности: чем выше опасность, тем выше уровень
        max_level = int(100 * self.mastery)
        return random.randint(min(max_level, 1 + danger_level*5), max_level)

    def generate_talent(self, danger_level: int) -> float:
        # Талант основан на уровне опасности: чем выше опасность, тем выше талант
        return round(random.uniform(0.5, 1.0 + danger_level * 0.1), 2)

    def generate_mastery(self, danger_level: int) -> float:
        # Мастерство основано на уровне опасности: чем выше опасность, тем выше мастерство
        return round(random.uniform(0.5, 1.0 + danger_level * 0.1), 2)

    def to_dict(self):
        return {
            'skill_id': self.skill_id,
            'lvl': self.lvl,
            'talant': self.talent,
            'master': self.mastery
        }

    def export_to_text(self):
        text = (
            f'addSkill ("{self.skill_id}", {self.lvl}, {self.talent}, {self.mastery});\n'
        )
        return text

    @staticmethod
    def import_from_text(text):
        match = re.search(r'addSkill \("(.*?)", (\d+), ([\d.]+), ([\d.]+)\);', text)
        if match:
            return SkillCfg(skill_id=match.group(1), lvl=int(match.group(2)), talent=float(match.group(3)), mastery=float(match.group(4)))

    def __repr__(self):
        return f'SkillCfg(id={self.skill_id}, lvl={self.lvl}, talent={self.talent}, mastery={self.mastery})'


class SkillsCfg:
    def __init__(self,
                 skills:list[SkillCfg] = None,
                 available_types:list=None,
                 available_skills:list = None,
                 danger_level: int = 0,
                 num_skills: int = None,
                 data_manager: DataManager = None):

        self.data_manager = data_manager if data_manager else DataManager()

        self.available_skill_types = available_types
        self.available_skills = available_skills

        self.danger_level = danger_level
        self.skills: list[SkillCfg] = skills if skills else []

        self.num_of_skills = num_skills if num_skills else self.get_skill_num_by_danger()

        if not self.skills:
            self.generate_random_skills(self.num_of_skills)

    def get_skill_num_by_danger(self):
        basic_skill_num = 3
        return basic_skill_num + self.danger_level // 2

    def skills_in_type(self):
        return [skill.get('id') for skill in self.data_manager.select_dict('SKILL_INIT') if skill.get('role') if self.available_skill_types]

    def generate_random_skills(self, num_skills: int):
        total_skills = []
        potential_skills = []

        if not self.available_skill_types and not self.available_skills:
            potential_skills = [skill.get('id') for skill in self.data_manager.select_dict('SKILL_INIT')]
        elif self.available_skill_types:
            potential_skills = self.skills_in_type()
        elif self.available_skills:
            potential_skills = self.available_skills

        skill_num = min(num_skills, len(potential_skills))
        for _ in range(skill_num):
            skill_id = random.choice(potential_skills)
            potential_skills.remove(skill_id)
            total_skills.append(SkillCfg(skill_id=skill_id, danger_level=self.danger_level))

        self.skills = total_skills

    def to_dict(self):
        total_dict = {}
        for skill in self.skills:
            total_dict[skill.skill_id] = skill.to_dict()

        return total_dict

    def export_to_text(self):
        text = ''.join(skill.export_to_text() for skill in self.skills)
        return text

    @staticmethod
    def import_from_text(text):
        skills = []
        skill_matches = re.findall(r'addSkill \("(.*?)", (\d+), ([\d.]+), ([\d.]+)\);', text)
        for match in skill_matches:
            skills.append(
                SkillCfg(skill_id=match[0], lvl=int(match[1]), talent=float(match[2]), mastery=float(match[3])))
        return SkillsCfg(skills=skills)

    def __repr__(self):
        return f'{self.to_dict()}'


class EquipmentCfg:
    def __init__(self,
                 race:str=None,
                 clothes: list[str] = None,
                 min_tier:int=None,
                 max_tier: int=None,
                 danger_level: int=0,
                 data_manager: DataManager = None):

        self.budget = 20000 + danger_level * 10000
        self.danger = danger_level
        self.data_manager = data_manager if data_manager else DataManager()
        self.min_tier = min_tier if min_tier is not None else self.get_min_tier()
        self.max_tier = max_tier if max_tier is not None else self.get_max_tier()

        self.race = race
        self.clothes = clothes if clothes else self.generate_clothes()

    def get_min_tier(self):
        danger_tier = {
            -1: 0,
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 1,
            5: 1,
            6: 1,
            7: 2,
            8: 2,
            9: 2,
            10: 3
        }
        return danger_tier.get(self.danger, 0)

    def get_max_tier(self):
        danger_tier = {
            -1: 0,
            0: 1,
            1: 1,
            2: 1,
            3: 1,
            4: 2,
            5: 2,
            6: 3,
            7: 3,
            8: 3,
            9: 4,
            10: 4
        }
        return danger_tier.get(self.danger, self.danger)

    def get_available_slots(self):
        from ArbRaces import Race
        slots = Race(self.race, data_manager=self.data_manager).get_equipment_slots()
        return slots

    def get_available_slot_clothes(self):
        available_clothes = {}
        for slot in self.get_available_slots():
            available_clothes[slot] = [(cloth.get('id'), cloth.get('layer')) for cloth in self.data_manager.select_dict('CLOTHES', filter=f'slot = "{slot}" AND tier >= {self.min_tier} AND tier <= {self.max_tier} AND cost <= {self.budget}')]

        return available_clothes

    def clear_items_by_layer(self, items: list[tuple], layer: int) -> list[tuple]:
        # Удаление предметов по слою
        return [item for item in items if item[1] != layer]

    def generate_clothes(self) -> list[str]:
        total_slots = self.get_available_slot_clothes()
        total_items = []

        for slot, potential_clothes in total_slots.items():
            while potential_clothes:
                cloth = random.choice(potential_clothes)
                total_items.append(cloth[0])
                potential_clothes = self.clear_items_by_layer(potential_clothes, cloth[1])

        return total_items

    def export_to_text(self):
        text = ''.join(f'addGear ("{item}");\n' for item in self.clothes)
        return text

    @staticmethod
    def import_from_text(text):
        clothes = re.findall(r'addGear \("(.*?)"\);', text)
        return EquipmentCfg(clothes=clothes)

    def __repr__(self):
        return f'{self.clothes}'


class WeaponCfg:
    def __init__(self,
                 skills: list[SkillCfg] = None,
                 weapon_id:str=None,
                 min_tier:int=None,
                 max_tier: int=None,
                 danger_level: int=0,
                 data_manager: DataManager = None):
        self.danger_level = danger_level
        self.budget = 30000 + danger_level * 7000
        self.data_manager = data_manager if data_manager else DataManager()
        self.skills = skills
        self.min_tier = min_tier if min_tier is not None else self.get_min_tier()
        self.max_tier = max_tier if max_tier is not None else self.get_max_tier()

        self.weapon_id = weapon_id if weapon_id is not None else self.generate_weapon()

    def get_min_tier(self):
        danger_tier = {
            -1: 0,
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 1,
            5: 1,
            6: 1,
            7: 2,
            8: 2,
            9: 2,
            10: 3
        }
        return danger_tier.get(self.danger_level, 0)

    def get_max_tier(self):
        danger_tier = {
            -1: 0,
            0: 1,
            1: 1,
            2: 1,
            3: 1,
            4: 2,
            5: 2,
            6: 3,
            7: 3,
            8: 3,
            9: 4,
            10: 4
        }
        return danger_tier.get(self.danger_level, self.danger_level)

    def get_available_weapons(self):
        max_skill = self.get_max_combat_skill()
        if not max_skill:
            return ['CombatKnife', 'HighRatePistol']

        available_weapons = [weapon.get('id') for weapon in self.data_manager.select_dict('WEAPONS', filter=f'class = "{max_skill}" AND tier >= {self.min_tier} AND tier <= {self.max_tier} AND cost <= {self.budget}')]

        if not available_weapons:
            available_weapons.append('CombatKnife')
            available_weapons.append('HighRatePistol')

        return available_weapons

    def get_max_combat_skill(self):
        skills = self.skills
        max_skill_lvl = 0
        max_skill = None
        for skill in skills:
            if skill == 'MartialArms':
                continue

            if self.data_manager.check('SKILL_INIT', f'id = "{skill.skill_id}" AND (role = "Стрельба" OR role = "Ближний бой")'):
                if max_skill_lvl < skill.lvl:
                    max_skill = skill.skill_id
                    max_skill_lvl = skill.lvl

        return max_skill

    def generate_weapon(self):
        weapon = random.choice(self.get_available_weapons())
        return weapon

    def export_to_text(self):
        text = f'addWeapon ("{self.weapon_id}");\n'
        return text

    @staticmethod
    def import_from_text(text):
        match = re.search(r'addWeapon \("(.*?)"\);', text)
        if match:
            return WeaponCfg(weapon_id=match.group(1))

    def __repr__(self):
        return f'{self.weapon_id}'


class RelationsCfg:
    pass


class GroupCfg:
    pass


class MemoriesCfg:
    pass


class GenerateCharacter:
    def __init__(self,
                 danger:int=0,
                 basicCfg: BaseCfg = None,
                 identifyCfg: IdentifyCfg = None,
                 skillsCfg: SkillsCfg = None,
                 equipmentCfg: EquipmentCfg = None,
                 weaponCfg: WeaponCfg = None,
                 relationsCfg: RelationsCfg = None,
                 groupCfg: GroupCfg = None,
                 data_manager: DataManager = None):

        self.data_manager = data_manager if data_manager else DataManager()
        self.basicCfg = basicCfg if basicCfg else BaseCfg(data_manager=self.data_manager)
        self.identifyCfg = identifyCfg if identifyCfg else IdentifyCfg(data_manager=self.data_manager)

        self.skillsCfg = skillsCfg if skillsCfg else SkillsCfg(data_manager=self.data_manager, danger_level=danger)

        self.equipmentCfg = equipmentCfg if equipmentCfg else EquipmentCfg(race=self.basicCfg.race, data_manager=self.data_manager, danger_level=danger)
        self.weaponCfg = weaponCfg if weaponCfg else WeaponCfg(skills=self.skillsCfg.skills, data_manager=self.data_manager, danger_level=danger)

        self.relationsCfg = relationsCfg if relationsCfg else RelationsCfg()
        self.groupCfg = groupCfg if groupCfg else GroupCfg()

    def insert_data(self, owner_id:int = None):
        character_id = self.data_manager.maxValue('CHARS_INIT', 'id') + 1

        basic_info = self.basicCfg.to_dict()
        basic_query = {'id': character_id,
                       'owner': owner_id}
        basic_query.update(basic_info)
        self.data_manager.insert('CHARS_INIT', basic_query)

        identity_info = self.identifyCfg.to_dict()
        identity_query = {'id': character_id}
        identity_query.update(identity_info)
        self.data_manager.insert('CHARS_PSYCHOLOGY', identity_query)

        skills_info = self.skillsCfg.to_dict()
        for skill in skills_info:
            skill_query = {'id': character_id,
                           'exp': 0}
            skill_query.update(skills_info[skill])
            self.data_manager.insert('CHARS_SKILLS', skill_query)

        inventory = create_inventory(f'Инвентарь {self.basicCfg.name}', character_id, type=f'Инвентарь', data_manager=self.data_manager)

        equipment_info = self.equipmentCfg.clothes
        for gear in equipment_info:
            ItemManager(gear, data_manager=self.data_manager, inventory=inventory).spawn_item(character_id)


        weapon_info = self.weaponCfg.weapon_id
        ItemManager(weapon_info, data_manager=self.data_manager, inventory=inventory).spawn_item(character_id)

        return character_id

    def export_to_text(self):
        text = (
                self.basicCfg.export_to_text() +
                self.identifyCfg.export_to_text() +
                self.skillsCfg.export_to_text() +
                self.equipmentCfg.export_to_text() +
                self.weaponCfg.export_to_text()
        )
        return text

    @staticmethod
    def import_from_text(text):
        base_cfg = BaseCfg.import_from_text(text)
        identify_cfg = IdentifyCfg.import_from_text(text)
        skills_cfg = SkillsCfg.import_from_text(text)
        equipment_cfg = EquipmentCfg.import_from_text(text)
        weapon_cfg = WeaponCfg.import_from_text(text)

        return GenerateCharacter(
            basicCfg=base_cfg,
            identifyCfg=identify_cfg,
            skillsCfg=skills_cfg,
            equipmentCfg=equipment_cfg,
            weaponCfg=weapon_cfg
        )



class GenerateObject:
    def __init__(self, object_type: str, battle_id: int, layer_id: int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.object_type = object_type
        self.battle_id = battle_id
        self.layer_id = layer_id
        self.captured_team_id = kwargs.get('captured', None)

    def get_available_id(self):
        if self.data_manager.check('BATTLE_OBJECTS', f'object_id'):
            return self.data_manager.maxValue('BATTLE_OBJECTS', 'object_id') + 1
        else:
            return 0

    def get_endurance(self):
        if self.data_manager.check('OBJECT_TYPE', f'object_id = "{self.object_type}"'):
            return self.data_manager.select_dict('OBJECT_TYPE', f'object_id = "{self.object_type}"')[0].get('endurance')
        else:
            return 0

    def insert_data(self):
        query = {
            'battle_id': self.battle_id,
            'layer_id': self.layer_id,
            'object_id': self.get_available_id(),
            'object_type': self.object_type,
            'endurance': self.get_endurance(),
            'uses': 0,
            'captured': self.captured_team_id
        }

        self.data_manager.insert('BATTLE_OBJECTS', query)

    def __repr__(self):
        return f'GenObject.{self.object_type}'




class GenerateLayer:
    def __init__(self, battle_id:int, layer_id:int, terrain_type:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = layer_id
        self.battle_id = battle_id
        self.terrain_type = terrain_type
        self.label = kwargs.get('label', self.get_terrain_type_label())
        self.height = kwargs.get('height', 0)

        self.num_of_objects = kwargs.get('num_of_objects', random.randint(0, 15))
        self.objects = kwargs.get('objects', [])

        self.generate_objects()


    def get_terrain_type_label(self):
        if self.data_manager.check('TERRAIN_TYPE', f'id = "{self.terrain_type}"'):
            return self.data_manager.select_dict('TERRAIN_TYPE', f'id = "{self.terrain_type}"')[0].get('label')
        else:
            return 'Неизвестная местность'

    def get_object_category(self):
        return self.data_manager.select_dict('TERRAIN_TYPE', filter=f'id = "{self.terrain_type}"')[0].get('object_types')

    def get_available_objects(self):
        object_category = self.get_object_category()
        objects = [obj.get('object_id') for obj in self.data_manager.select_dict('OBJECT_TYPE', filter=f'type = "{object_category}"')]
        return objects

    def add_object(self, genered_object: GenerateObject):
        self.objects.append(genered_object)

    def generate_objects(self):
        total_len = self.num_of_objects - len(self.objects)
        if total_len <= 0:
            return

        available_types = self.get_available_objects()
        for i in range(total_len):
            object_type = random.choice(available_types)
            gen_object = GenerateObject(object_type, self.battle_id, self.id, data_manager=self.data_manager)
            self.add_object(gen_object)

    def insert_data(self):
        query = {
            'battle_id': self.battle_id,
            'id': self.id,
            'label': self.label,
            'terrain_type': self.terrain_type,
            'height': self.height,
                 }

        self.data_manager.insert('BATTLE_LAYERS', query)

        for obj in self.objects:
            obj.insert_data()

    def __repr__(self):
        return f'GenLayer.{self.id}.{self.terrain_type}(objects={self.objects})'



class GenerateBattle:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = self.get_battle_id()
        self.label = kwargs.get('label', f'Сражение {self.id}')
        self.distance_delta = kwargs.get('distance_delta', round(random.randint(50, 200), -1))
        self.desc = kwargs.get('desc', '')
        self.time = kwargs.get('time', 'Day')
        self.weather = kwargs.get('weather', 'Sunny')
        self.start_round = kwargs.get('start_round', 1)
        self.last_round = kwargs.get('last_round', None)
        self.key_round = kwargs.get('key_round', random.randint(3, 5))
        self.battle_type = kwargs.get('battle_type', 'Overkill')
        self.battle_type_value = kwargs.get('battle_type_value', None)

        self.terrain_categories = kwargs.get('terrain_categories', [])
        self.terrain_types = kwargs.get('terrain_types', [])
        if not self.terrain_categories and not self.terrain_types:
            self.terrain_types = self.get_terrain_types('Природный')

        if self.terrain_categories:
            total_types = []
            for i in self.terrain_categories:
                total_types.extend(self.get_terrain_types(i))
            self.terrain_types.extend(total_types)

        self.num_of_layers = kwargs.get('num_of_layers', random.randint(5, 20))
        self.layers: list[GenerateLayer] = []
        self.generate_layers()
        self.generate_special_objects()

    def get_battle_id(self):
        if self.data_manager.check('BATTLE_INIT', 'id'):
            return self.data_manager.maxValue('BATTLE_INIT', 'id') + 1
        else:
            return 1

    def get_terrain_types(self, terrain_category: str):
        if self.data_manager.check('TERRAIN_TYPE', f'type = "{terrain_category}"'):
            return [ter.get('id') for ter in self.data_manager.select_dict('TERRAIN_TYPE', filter=f'type = "{terrain_category}"')]
        else:
            return []

    def generate_layer(self, layer_id:int, height:int, terrain_type:str, objects: list = None):
        layer = GenerateLayer(
            battle_id=self.id,
            layer_id=layer_id,
            terrain_type=terrain_type,
            height=height,
            data_manager=self.data_manager,
            objects=objects if objects is not None else []
        )
        self.layers.append(layer)
        return layer

    def generate_layers(self):
        last_height = 0
        for i in range(self.num_of_layers):
            terrain_type = random.choice(self.terrain_types)
            self.generate_layer(i, last_height, terrain_type)
            last_height += random.randint(-5, 5)

    def generate_special_objects(self):
        object_type = ''
        num_of_objects = 0

        if self.battle_type == 'Interception':
            object_type = [obj.get('object_id') for obj in self.data_manager.select_dict('OBJECT_TYPE', filter=f'type = "Перехват"')]
            num_of_objects = random.randint(3, 7)
        elif self.battle_type == 'Capture':
            object_type = [obj.get('object_id') for obj in self.data_manager.select_dict('OBJECT_TYPE', filter=f'type = "Захват"')]
            num_of_objects = random.randint(2, 5)

        if object_type and num_of_objects > 0:
            print(object_type, num_of_objects)

            for _ in range(num_of_objects):
                layer: GenerateLayer = random.choice(self.layers)
                o_type = random.choice(object_type)
                object = GenerateObject(o_type, self.id, layer.id)
                layer.add_object(object)

    def insert_data(self):
        query = {
            'id': self.id,
            'label': self.label,
            'distance_delta': self.distance_delta,
            'desc': self.desc,
            'time_type': self.time,
            'weather_type': self.weather,
            'round': self.start_round,
            'key_round': self.key_round,
            'last_round': self.last_round,
            'battle_type': self.battle_type,
            'type_value': self.battle_type_value
        }
        self.data_manager.insert('BATTLE_INIT', query)

        for layer in self.layers:
            layer.insert_data()

    def set_label(self, label):
        self.label = label

    def set_distance_delta(self, distance_delta):
        self.distance_delta = distance_delta

    def set_desc(self, desc):
        self.desc = desc

    def set_time(self, time):
        self.time = time

    def set_weather(self, weather):
        self.weather = weather

    def set_start_round(self, start_round):
        self.start_round = start_round

    def set_last_round(self, last_round):
        self.last_round = last_round

    def set_key_round(self, key_round):
        self.key_round = key_round

    def set_battle_type(self, battle_type):
        self.battle_type = battle_type
        self.generate_special_objects()

    def add_layer(self, terrain_type, height, num_of_objects):
        layer_id = len(self.layers)
        layer = GenerateLayer(self.id, layer_id, terrain_type, height=height, num_of_objects=num_of_objects,
                              data_manager=self.data_manager)
        self.layers.append(layer)

    def add_object_to_layer(self, layer_id, object_type, captured_team_id=None):
        if 0 <= layer_id < len(self.layers):
            obj = GenerateObject(object_type, self.id, layer_id, captured=captured_team_id,
                                 data_manager=self.data_manager)
            self.layers[layer_id].add_object(obj)


class GenerateTeam:
    def __init__(self, battle_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.battle_id = battle_id
        self.id = self.get_current_id()
        self.label = kwargs.get('label', 'Неизвестная команда')
        self.role = kwargs.get('role', 'Participants')
        self.commander = kwargs.get('commander', None)
        self.coordinator = kwargs.get('coordinator', None)
        self.com_points = kwargs.get('com_points', 0)
        self.round_active = kwargs.get('round_active', 1)

        self.members_value = kwargs.get('members_value', None)
        self.members_race = kwargs.get('members_race', 'Human')
        self.members_org_id = kwargs.get('members_org', None)
        self.members_layer = kwargs.get('members_layer', 0)
        self.generate_commander = kwargs.get('generate_commander', False)
        self.generate_coordinator = kwargs.get('generate_coordinator', False)

    def get_current_id(self):
        if self.data_manager.check('BATTLE_TEAMS', 'team_id'):
            return self.data_manager.maxValue('BATTLE_TEAMS', 'team_id') + 1
        else:
            return 1

    def generate_units(self):
        if self.members_value:
            for _ in range(self.members_value):
                print('Создаю персонажа...')
                new_unit = GenerateCharacter(race=self.members_race, org=self.members_org_id)
                new_unit.insert_data()

                prompt = {
                    'battle_id': self.battle_id,
                    'character_id': new_unit.id,
                    'layer_id': self.members_layer,
                    'object': None,
                    'initiative': random.randint(1, 100),
                    'is_active': 0,
                    'height': 0,
                    'team_id': self.id
                }

                self.data_manager.insert('BATTLE_CHARACTERS', prompt)

        if self.generate_coordinator:
            new_unit = GenerateCharacter(race=self.members_race, org=self.members_org_id)
            new_unit.insert_data()
            self.coordinator = new_unit.id

        if self.generate_commander:
            new_unit = GenerateCharacter(race=self.members_race, org=self.members_org_id)
            new_unit.insert_data()
            self.commander = new_unit.id

            prompt = {
                'battle_id': self.battle_id,
                'character_id': new_unit.id,
                'layer_id': self.members_layer,
                'object': None,
                'initiative': random.randint(1, 100),
                'is_active': 0,
                'height': 0,
                'team_id': self.id
            }

            self.data_manager.insert('BATTLE_CHARACTERS', prompt)

    def insert_data(self):
        query = {
            'battle_id': self.battle_id,
            'team_id': self.id,
            'label': self.label,
            'role': self.role,
            'commander': self.commander,
            'coordinator': self.coordinator,
            'com_points': self.com_points,
            'round_active': self.round_active
        }

        self.data_manager.insert('BATTLE_TEAMS', query)

        self.generate_units()





class GenerateLocation:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.label = kwargs.get('label', 'Неизвестное место')
        self.type = kwargs.get('type', 'Village') if kwargs.get('type') else 'Village'
        self.region = kwargs.get('region', None)
        self.owner = kwargs.get('owner', None)
        self.movement_cost = kwargs.get('cost', None)
        self.current_battle_id = kwargs.get('battle_id', None)
        self.picture = kwargs.get('picture', '')

    def insert_data(self):
        prompt = {'id': self.id,
                  'label': self.label,
                  'type': self.type,
                  'region': self.region,
                  'owner': self.owner,
                  'cost': self.movement_cost,
                  'current_battle': self.current_battle_id,
                  'picture': self.picture}

        self.data_manager.insert('LOC_INIT', prompt)

    def __repr__(self):
        return f'Location.{self.region}.{self.id}[{self.label}]'


class GenerateCluster:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.label = kwargs.get('label', 'Неизвестный регион')
        self.type = kwargs.get('type', 'Открытый')
        self.time = kwargs.get('time', None)
        self.weather = kwargs.get('weather', None)
        self.picture = kwargs.get('picture', '')
        self.movement_desc = kwargs.get('desc', None)

        self.cluster_pattern = kwargs.get('cluster_pattern', 'Регион')
        self.proxy_cluster_value = kwargs.get('cluster_value', random.randint(2, 4))
        self.locations_value = kwargs.get('locations_value', random.randint(5, 10))
        self.owners = process_string(kwargs.get('owners', '')) if kwargs.get('owners') else []

        self.proxy_clusters = []
        last_id = 0
        for _ in range(self.proxy_cluster_value):
            self.proxy_clusters.append(self.generate_proxy_cluster(last_id))
            last_id = int(self.proxy_clusters[-1][-1].id.split('.')[-1]) + 1

        self.total_graphs = self.generate_graph_for_proxy()
        self.transit_locations = self.generate_transit_locations()
        self.graph = self.combine_graphs(self.total_graphs)

    def get_location_types(self):
        if self.data_manager.check('LOC_TYPE',filter=f'cluster_type = "{self.cluster_pattern}"'):
            return self.data_manager.select_dict('LOC_TYPE', filter=f'cluster_type = "{self.cluster_pattern}"')
        else:
            return []

    def get_transition_types(self):
        if self.data_manager.check('LOC_TYPE',filter=f'cluster_type = "{self.cluster_pattern}-транзит"'):
            return self.data_manager.select_dict('LOC_TYPE', filter=f'cluster_type = "{self.cluster_pattern}-транзит"')
        else:
            return []

    def generate_proxy_cluster(self, last_location_id:int=None):
        loc_types = self.get_location_types()
        total_locations = []

        last_location_id = last_location_id if last_location_id is None else last_location_id

        for _ in range(self.locations_value):
            loc_id = f'{self.id}.{last_location_id + _}'
            print(loc_types)
            loc_type = random.choice(loc_types)
            loc_label = f"{loc_type.get('label')} {TitleGenerator('Город')}" if self.cluster_pattern == 'Регион' else f'{loc_type.get("label")} {random.choice(string.ascii_uppercase)}{random.randint(1, 20)}'
            new_location = self.generate_location(loc_id, loc_type.get('id'), loc_label)
            total_locations.append(new_location)

        return total_locations

    def generate_location(self, id:str, type:str, label:str):
        new_location = GenerateLocation(id=id,
                                        type=type,
                                        label=label,
                                        data_manager=self.data_manager,
                                        region=self.id,
                                        owner=random.choice(self.owners) if self.owners else None,
                                        cost=random.randint(1, 6) if self.cluster_pattern == 'Регион' else 0)

        return new_location

    def replace_nodes_with_locations(self, graph, locations):
        """
        Заменяет вершины числового графа на соответствующие локации из списка.

        :param graph: Граф NetworkX с числовыми вершинами от 0 до n.
        :param locations: Список локаций, где индекс списка соответствует вершине в графе.
        :return: Новый граф NetworkX с замененными вершинами.
        """
        # Создаем новый граф того же типа (Graph, DiGraph, etc.)
        new_graph = nx.Graph()

        # Добавляем вершины с новыми именами
        mapping = {i: locations[i] for i in range(len(locations))}
        new_graph.add_nodes_from(mapping.values())

        # Добавляем ребра с новыми именами вершин
        for u, v in graph.edges():
            new_graph.add_edge(mapping[u], mapping[v])

        return new_graph

    def generate_graph_for_proxy(self):
        total_proxies = self.proxy_clusters
        total_graphs = []

        for _ in range(len(total_proxies)):
            n_graph = nx.turan_graph(len(total_proxies[_]), random.randint(2, 3))

            new_graph = self.replace_nodes_with_locations(n_graph, total_proxies[_])
            total_graphs.append(new_graph)

        return total_graphs

    def combine_graphs(self, graphs: list):
        """
        Объединяет список графов в один граф.

        :param graphs: Список графов NetworkX.
        :return: Новый объединенный граф NetworkX.
        """
        # Проверяем, что список графов не пуст
        if not graphs:
            raise ValueError("Список графов пуст.")

        # Создаем новый граф того же типа, что и первый граф в списке
        combined_graph = nx.Graph()

        # Проходим по всем графам и добавляем их узлы и ребра в combined_graph
        for graph in graphs:
            combined_graph.add_nodes_from(graph.nodes(data=True))
            combined_graph.add_edges_from(graph.edges(data=True))

        for transit_type in self.transit_locations:
            proccesed_locations = []

            for loc in self.transit_locations[transit_type]:
                combined_graph.add_node(loc[0])
                proccesed_locations.append(loc[0])

            combined_transitions = list(combinations(proccesed_locations, 2))
            for pair in combined_transitions:
                combined_graph.add_edge(pair[0], pair[1])

            for loc in self.transit_locations[transit_type]:
                chosen_loc_of_cluster = random.choice(self.proxy_clusters[loc[1]])
                combined_graph.add_edge(loc[0], chosen_loc_of_cluster)
                self.proxy_clusters[loc[1]].append(loc[0])

        return combined_graph

    def generate_transit_locations(self):
        """
        Генерирует транзитные локации и связывает их между собой.

        :param num_clusters: Количество кластеров.
        :param transit_types: Список доступных типов транзитных локаций.
        :return: Словарь с транзитными локациями и их связями.
        """
        transit_locations = {}
        total_clusters = self.proxy_clusters
        total_trans_types = self.get_transition_types()

        last_id = int(total_clusters[-1][-1].id.split('.')[-1]) + 1
        num_transit = random.randint(1, len(total_trans_types))
        selected_transit_types = random.sample(total_trans_types, num_transit)

        for i in range(len(total_clusters)):
            # Случайным образом выбираем количество транзитных локаций

            # Создаем транзитные локации и их связи
            for transit_type in selected_transit_types:
                if transit_type.get('id') not in transit_locations:
                    transit_locations[transit_type.get('id')] = []
                transit_label = f"{transit_type.get('label')} {TitleGenerator('Город')}" if self.cluster_pattern == 'Регион' else f'{transit_type.get("label")} {random.choice(string.ascii_uppercase)}{random.randint(1, 20)}'
                new_transit_location = self.generate_location(f'{self.id}.{last_id}', transit_type.get('id'), transit_label)
                transit_locations[transit_type.get('id')].append((new_transit_location, i))
                last_id += 1

        # if len(transit_locations.keys()) > 1 and len(total_clusters) > 2:
        #     mutation = random.randint(0, len(transit_locations) - 1)
        #     for i in range(mutation):
        #         transit_type_to_remove = random.choice(list(transit_locations.keys()))
        #         transit_list = transit_locations[transit_type_to_remove]
        #         num_to_remove = random.randint(1, round(len(transit_list)/2))
        #         indices_to_remove = random.sample(range(len(transit_list)), num_to_remove)
        #
        #         print(transit_type_to_remove, indices_to_remove)
        #
        #         for index in sorted(indices_to_remove, reverse=True):
        #             del transit_list[index]
        #         transit_locations[transit_type_to_remove] = transit_list

        return transit_locations

    def insert_data(self):
        prompt = {'id': self.id,
                  'label': self.label,
                  'time': self.time,
                  'weather': self.weather,
                  'picture': self.picture,
                  'move_desc': self.movement_desc}

        self.data_manager.insert('LOC_CLUSTER', prompt)

        for cluster in self.proxy_clusters:
            for loc in cluster:
                loc.insert_data()

        for edge in self.graph.edges:
            prompt = {'loc_id': edge[0].id,
                      'con_id': edge[1].id,
                      'available': 1,
                      'transport': None}

            self.data_manager.insert('LOC_CONNECTIONS', prompt)



