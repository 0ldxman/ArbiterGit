import datetime
import string

from ArbDatabase import DataManager, DataModel
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
        print(material_type, tier, min_rarity)

        c_roll = random.randint(min_rarity, 100)
        c_materials = [mat['id'] for mat in db.select_dict('MATERIALS', '*', f'type = "{material_type}" AND rarity <= {c_roll} AND tier <= {tier}')]
        return random.choice(c_materials)




class ItemManager:
    def __init__(self, item_type: str, **kwargs):
        self.item_type = item_type
        self.data_manager = kwargs.get('data_manager', DataManager())

        # Предварительно запрашиваем данные предмета
        self.item_table, self.item_class = self.get_item_class()
        item_data = self.data_manager.select_dict(self.item_table, filter=f'id = "{self.item_type}"')[0]
        self.item_label = item_data.get('name', 'Неизвестный предмет')

        self.endurance = self.calculate_endurance(item_data, kwargs.get('endurance'), kwargs.get('set_max_endurance'))

        self.quality = RandomQuality.generate_quality(kwargs.get('quality', None))
        self.material_type = item_data.get('material_type') or self.get_material_type()

        self.material = self.generate_material(kwargs.get('material')) if self.material_type else None
        self.biocode = kwargs.get('biocode', None)
        self.inventory_id = kwargs.get('inventory', None)

    def calculate_endurance(self, item_data, endurance_percent, set_max_endurance):
        max_endurance = item_data.get('endurance', 100)
        if set_max_endurance:
            return max_endurance
        return endurance_percent / 100 * max_endurance if endurance_percent else random.randint(int(max_endurance * 0.4), int(max_endurance))

    def get_item_class(self):
        query = """
        SELECT 'CLOTHES' AS table_name, 'Одежда' AS item_class
        FROM CLOTHES WHERE id = ?
        UNION
        SELECT 'WEAPONS', 'Оружие'
        FROM WEAPONS WHERE id = ?
        UNION
        SELECT 'ITEMS_INIT', 'Предмет'
        FROM ITEMS_INIT WHERE id = ?
        UNION
        SELECT 'AMMO', 'Граната'
        FROM AMMO WHERE id = ?
        """

        result = self.data_manager.raw_execute(query, (self.item_type,) * 4, fetch='one')

        if result:
            item_table, item_class = result
        else:
            item_table, item_class = None, 'Разное'

        return item_table, item_class

    def get_material_type(self):
        if self.item_class == 'Одежда':
            material_type = self.data_manager.select_dict('CLOTHES', filter=f'id = "{self.item_type}"')[0].get('material_type')
        elif self.item_class == 'Оружие':
            material_type = 'Оружейный'
        elif self.item_class == 'Граната':
            material_type = 'Оружейный'
        else:
            material_type = None

        return material_type

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

        print(material_type, self.item_class)

        return RandomMaterial.generate_material(material_type, 3, None, data_manager=self.data_manager)

    def get_item_label(self):
        if self.data_manager.check(self.item_table, f'id = "{self.item_type}"'):
            return self.data_manager.select_dict(self.item_table, filter=f'id = "{self.item_type}"')[0].get('name', 'Неизвестный предмет')
        else:
            return 'Неизвестный предмет'

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

    @staticmethod
    def get_weapon_capacity_static(weapon_id:str, data_manager:DataManager = DataManager()):
        if data_manager.check('WEAPONS', filter=f'id = "{weapon_id}"'):
            return data_manager.select_dict('WEAPONS', filter=f'id="{weapon_id}"')[0].get('mag')
        else:
            return 0

    @staticmethod
    def get_weapon_possible_ammo_static(weapon_id:str, data_manager:DataManager = DataManager()):
        from ArbWeapons import RangeWeapon
        return RangeWeapon(weapon_id, data_manager=data_manager).get_available_ammo()

    @staticmethod
    def batch_spawn_items(item_data: list[dict], data_manager: DataManager, equip_to_character: int = None):
        inventory_id = item_data[0].get('inventory') if item_data[0].get('inventory') else None

        item_tuples = [
            (item['name'], item['type'], item['class'], item['material'],
             item['quality'], item['endurance'], item['biocode'], item['inventory'])
            for item in item_data
        ]

        with data_manager.connection as conn:
            cursor = conn.cursor()
            try:
                last_item_id = data_manager.maxValue('ITEMS', 'id') + 1

                # Пакетная вставка данных в таблицу ITEMS
                cursor.executemany('''INSERT INTO ITEMS (name, type, class, material, quality, endurance, biocode, inventory)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', item_tuples)

                # Экипируем предметы и вставляем данные о пулях для оружия
                equip_tuples = []
                bullet_tuples = []

                if equip_to_character:
                    from ArbItems import CharacterEquipment

                    for idx, item in enumerate(item_data):
                        item_id = last_item_id + idx  # Последовательный ID предмета
                        if item['class'] == 'Оружие':
                            # Добавляем данные о пулях для оружия в batch
                            bullets = ItemManager.get_weapon_capacity_static(item['type'], data_manager)
                            possible_ammo = ItemManager.get_weapon_possible_ammo_static(item['type'], data_manager)
                            ammo_id = random.choice(possible_ammo) if possible_ammo else None
                            bullet_tuples.append((item_id, bullets, ammo_id))

                            # Экипируем оружие на персонажа
                            equip_tuples.append((equip_to_character, item_id))

                        elif item['class'] == 'Одежда':
                            # Экипируем одежду на персонажа
                            equip_tuples.append((equip_to_character, item_id))

                # Пакетная вставка данных в таблицу ITEMS_BULLETS
                if bullet_tuples:
                    cursor.executemany('''INSERT INTO ITEMS_BULLETS (id, bullets, ammo_id) VALUES (?, ?, ?)''',
                                       bullet_tuples)

                # Пакетная вставка данных в таблицу CHARS_EQUIPMENT
                if equip_tuples:
                    cursor.executemany('''INSERT INTO CHARS_EQUIPMENT (id, item_id) VALUES (?, ?)''', equip_tuples)

                conn.commit()

            except Exception as e:
                conn.rollback()
                data_manager.logger.error(f"Error during batch insertion: {e}")
                raise
            finally:
                cursor.close()

        return inventory_id

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

            if equip_to_character:
                character_equipment = CharacterEquipment(equip_to_character, data_manager=self.data_manager)
                character_equipment.equip_weapon(item_id)

        if self.item_class == 'Одежда' and equip_to_character:
            character_equipment = CharacterEquipment(equip_to_character, data_manager=self.data_manager)
            character_equipment.equip_cloth(item_id)

        return Item(item_id, data_manager=self.data_manager)

    def to_dict(self):
        query = {
            'name': self.item_label,
            'type': self.item_type,
            'class': self.item_class,
            'material': self.material,
            'quality': self.quality,
            'endurance': self.endurance,
            'biocode': self.biocode,
            'inventory': self.inventory_id
        }
        return query










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



class SkillTemplate:
    def __init__(self, skill_id:str, lvl:int, talent:float=1, mastery:float=0):
        self.skill_id = skill_id
        self.lvl = lvl
        self.talent = talent
        self.mastery = mastery

    def to_text(self):
        return f'AddSkill("{self.skill_id}", {self.lvl}, {self.talent}, {self.mastery})'

    def to_dict(self, character_id:int=None):
        return {
            'id': character_id,
            'skill_id': self.skill_id,
            'lvl': self.lvl,
            'talant': self.talent,
            'master': self.mastery
        }

    def save_to_db(self, character_id:int, data_manager:DataManager = None):
        skill_data = self.to_dict(character_id)
        db = data_manager if data_manager else DataManager()
        db.insert('CHARS_SKILLS', skill_data)

    @staticmethod
    def generate_level(danger_level: int, mastery:float=1) -> int:
        # Уровень навыка основан на уровне опасности: чем выше опасность, тем выше уровень
        max_level = int(100 * mastery)
        return random.randint(min(max_level, 1 + danger_level*5), max_level)

    @staticmethod
    def generate_talent(danger_level: int) -> float:
        # Талант основан на уровне опасности: чем выше опасность, тем выше талант
        return round(random.uniform(0.5, 1.0 + danger_level * 0.1), 2)

    @staticmethod
    def generate_mastery(danger_level: int) -> float:
        # Мастерство основано на уровне опасности: чем выше опасность, тем выше мастерство
        return round(random.uniform(0.5, 1.0 + danger_level * 0.1), 2)


    @classmethod
    def generate_skill(cls, danger:int=0, skill_id:str=None, banned_skills:list[str]=None, data_manager:DataManager=None, total_skills:str=None):
        db = data_manager if data_manager else DataManager()

        if not banned_skills:
            banned_skills = []
        else:
            banned_skills = banned_skills

        total_skills = total_skills if total_skills else [skill.get("id") for skill in db.select_dict('SKILL_INIT')]
        for skill in banned_skills:
            if skill in total_skills:
                total_skills.remove(skill)

        skill_id = skill_id if skill_id and skill_id not in banned_skills else random.choice(total_skills)
        mastery = SkillTemplate.generate_mastery(danger)
        talent = SkillTemplate.generate_talent(danger)
        lvl = SkillTemplate.generate_level(danger, mastery)

        return SkillTemplate(skill_id, lvl, talent, mastery)

    @staticmethod
    def generate_skills(danger: int = 0, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()

        skill_amount = 3 + danger // 2
        all_skills = [skill.get("id") for skill in db.select_dict('SKILL_INIT')]

        generated_skills = []
        total_skills = []
        for _ in range(skill_amount):
            new_skill = SkillTemplate.generate_skill(danger, data_manager=db, banned_skills=generated_skills, total_skills=all_skills)
            generated_skills.append(new_skill.skill_id)
            total_skills.append(new_skill)

        return total_skills

    @classmethod
    def import_from_text(cls, text:str):
        # Parse skill data from text and create SkillTemplate objects
        # Example text: AddSkill("Close Combat", 1, 0.8, 0.75)
        skill_data = re.findall(r'AddSkill\("(.*?)", (\d+), ([\d\.]+), ([\d\.]+)\)', text)

        return [SkillTemplate(skill_id, int(lvl), float(talent), float(mastery)) for skill_id, lvl, talent, mastery in skill_data]


class BasicTemplate:
    def __init__(self,
                 race_id:str='Human',
                 owner_id:int=None,
                 name:str=None,
                 callsign:str=None,
                 gender:str=None,
                 age:int=None,
                 org_id:str=None,
                 org_lvl:int=None,
                 org_rank:str=None,
                 faction:str=None,
                 faction_lvl:int=None,
                 picture:str=None,
                 server_id:int=None,
                 budget:int=None,
                 danger:int=0,
                 data_manager: DataManager=None):

        self.data_manager = data_manager if data_manager else DataManager()
        self.race = race_id
        self.sex = gender if gender else self.generate_gender(self.race, self.data_manager)
        self.name = name if name else self.generate_name(self.race, self.sex, self.data_manager)
        self.age = age if age else self.generate_age(self.race, self.data_manager)
        self.callsign = callsign if callsign else self.generate_callsign(self.name, self.age, self.data_manager)

        self.org = org_id if org_id else 'Civil'
        self.org_lvl = org_rank if org_rank else self.generate_rank(self.org, org_lvl, self.data_manager)
        self.frac = faction
        self.frac_lvl = faction_lvl

        self.avatar = picture
        self.server_id = server_id
        self.budget = budget if budget else self.generate_budget(danger)
        self.owner_id = owner_id

    @staticmethod
    def generate_budget(danger:int=0):
        return round(random.uniform(10000, 100000) * (1 + danger * 0.1), 2)

    @staticmethod
    def generate_callsign(name:str, age:int=None, data_manager:DataManager = None):
        db = data_manager if data_manager else data_manager

        return None

    @staticmethod
    def generate_age(race_id:str, data_manager: DataManager = None) -> int:
        db = data_manager if data_manager else DataManager()
        min_age, max_age = db.select_dict('RACES_INIT', filter=f'id = "{race_id}"')[0]['age_range'].split('-')
        return random.randint(int(min_age), int(max_age))

    @staticmethod
    def check_org_existance(org_id:str, data_manager: DataManager =None) -> bool:
        db = data_manager if data_manager else DataManager()
        org_ids = [org.get('id') for org in db.select_dict('ORG_INIT')]
        return org_id in org_ids

    @staticmethod
    def generate_rank(org_id:str, org_lvl:int=0, data_manager: DataManager = None) -> str:
        from ArbOrgs import Organization
        db = data_manager if data_manager else DataManager()
        org = Organization(org_id, data_manager=db)

        if org_lvl:
            return org.get_lvl_rank(org_lvl)
        else:
            return org.get_random_lowest_rank()

    @staticmethod
    def generate_name(race_id:str, gender:str, data_manager:DataManager=None):
        from ArbRaces import Race
        db = data_manager if data_manager else DataManager()

        race = Race(race_id, data_manager=db)
        if race.is_robot:
            return NameGenerator('robot')
        elif race.is_primitive:
            return NameGenerator(gender)
        else:
            return NameGenerator(gender, with_surname=True)

    @staticmethod
    def generate_gender(race_id:str, data_manager:DataManager = None) -> str:
        from ArbRaces import Race
        db = data_manager if data_manager else DataManager()

        race = Race(race_id, data_manager=db)

        if race.is_robot:
            return 'Робот'
        else:
            return random.choice(['Мужской', 'Женский'])

    def to_text(self):
        total_info = self.to_dict()
        total_text = ''
        for key, value in total_info.items():
            total_text += f'set{key.capitalize()} - {value}\n' if value else ''

        return total_text

    @classmethod
    def import_from_text(cls, text: str, data_manager: Optional[DataManager] = None):
        # Create a dictionary from the text
        print(text)
        data = {}
        for line in text.strip().split('\n'):
            if line.startswith('set'):
                key, value = re.split(r' - ', line[3:], 1)
                data[key.lower()] = value

        # Create a BasicTemplate instance from the extracted data
        pprint.pprint(data)

        return cls(
            race_id=data.get('race', 'Human'),
            name=data.get('name'),
            callsign=data.get('callsign'),
            gender=data.get('sex'),
            age=int(data.get('age')) if data.get('age') else None,
            org_id=data.get('org'),
            org_lvl=data.get('org_lvl') if data.get('org_lvl') else None,
            org_rank=data.get('org_rank') if data.get('org_rank') else None,
            faction=data.get('frac'),
            faction_lvl=int(data.get('frac_lvl')) if data.get('frac_lvl') else None,
            picture=data.get('avatar'),
            server_id=int(data.get('server')) if data.get('server') else None,
            data_manager=data_manager,
            budget=float(data.get('money')) if data.get('money') else None,
            owner_id=int(data.get('owner_id')) if data.get('owner_id') else None
        )

    def to_dict(self, character_id:int=None):
        return {
            'id': character_id,
            'owner': self.owner_id,
            'name': self.name,
            'callsign': self.callsign,
            'age': self.age,
            'race': self.race,
            'sex': self.sex,
            'org': self.org,
            'org_lvl': self.org_lvl,
            'frac': self.frac,
            'frac_lvl': self.frac_lvl,
            'avatar': self.avatar,
            'updated': datetime.datetime.now().date().strftime('%Y-%m-%d'),
            'server': self.server_id,
            'money': self.budget
        }

    def save_to_db(self, character_id:int, data_manager:DataManager = None):
        skill_data = self.to_dict(character_id)
        db = data_manager if data_manager else DataManager()
        db.insert('CHARS_INIT', skill_data)


class ItemTemplate:
    def __init__(self,
                 item_type:str,
                 material_id:str=None,
                 quality:str=None,
                 endurance:int=None,
                 biocode:int=None):
        self.item_type = item_type
        self.material = material_id if material_id else None
        self.quality = quality if quality else None
        self.endurance = endurance if endurance else None
        self.biocode = biocode if biocode else None

    def to_text(self):
        # Форматируем данные в указанный формат
        components = [
            f"mat:{self.material}" if self.material else "",
            f"q:{self.quality}" if self.quality else "",
            f"e:{self.endurance}" if self.endurance else "",
            f"bc:{self.biocode}" if self.biocode is not None else ""
        ]
        components_str = ','.join(filter(None, components))
        return f"AddItem.{self.item_type}({components_str})"

    @classmethod
    def from_text(cls, text: str):
        # Разбираем текстовый формат обратно в объект ItemTemplate
        import re
        match = re.match(r"AddItem\.(.*?)\((.*?)\)", text)
        if not match:
            raise ValueError("Invalid text format for ItemTemplate")

        item_type = match.group(1)
        components = match.group(2).split(',')
        data = dict(component.split(':', 1) for component in components if ':' in component)

        return cls(
            item_type=item_type,
            material_id=data.get('mat') if data.get('mat') else None,
            quality=data.get('q') if data.get('q') else None,
            endurance=int(data.get('e')) if data.get('e') else None,
            biocode=int(data.get('bc')) if 'bc' in data else None
        )

    @classmethod
    def list_from_text(cls, text: str) -> List['ItemTemplate']:
        # Регулярное выражение для поиска паттернов AddItem.<item_type>(<components>)
        pattern = r"AddItem\.(.*?)\((.*?)\)"
        matches = re.findall(pattern, text)

        items = []
        for item_type, components in matches:
            # Создание текста для конструктора ItemTemplate
            item_text = f"AddItem.{item_type}({components})"
            try:
                item = cls.from_text(item_text)
                items.append(item)
            except ValueError as e:
                print(f"Error parsing item from text: {e}")

        return items

    def save_to_db(self, character_id:int, data_manager: DataManager = None, equip:bool=False):
        from ArbItems import Inventory
        db = data_manager if data_manager else DataManager()
        inventory = Inventory.get_inventory_by_character(character_id, data_manager=db)
        new_item = ItemManager(self.item_type, material=self.material, quality=self.quality, endurance=self.endurance, biocode=self.biocode, inventory=inventory.inventory_id, data_manager=db).spawn_item(character_id if equip else None)

        return new_item.item_id

    def to_query(self, inventory_id:int, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        query = ItemManager(self.item_type, material=self.material, quality=self.quality, endurance=self.endurance,
                               biocode=self.biocode, inventory=inventory_id, data_manager=db).to_dict()

        return query

    @staticmethod
    def list_to_query(character_id:int, items:list['ItemTemplate'], data_manager: DataManager = None):
        from ArbItems import Inventory
        db = data_manager if data_manager else DataManager()
        inventory_id = Inventory.get_inventory_by_character(character_id, data_manager=db).inventory_id
        items_query = []
        for item in items:
            items_query.append(item.to_query(inventory_id, db))

        return items_query

    @staticmethod
    def save_list_to_db(character_id:int, items: list['ItemTemplate'], data_manager: DataManager = None, equip:bool=False):
        from ArbItems import Inventory
        db = data_manager if data_manager else DataManager()
        inventory = Inventory.get_inventory_by_character(character_id, data_manager=db)
        for item in items:
            ItemManager(item.item_type, material=item.material, quality=item.quality, endurance=item.endurance, biocode=item.biocode, inventory=inventory.inventory_id, data_manager=db).spawn_item(character_id if equip else None)

    @staticmethod
    def get_min_tier(danger:int=0):
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
        return danger_tier.get(danger, 0)

    @staticmethod
    def get_max_tier(danger:int=0):
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
        return danger_tier.get(danger, danger)

    @staticmethod
    def get_available_slots(race_id:str, data_manager:DataManager = None):
        db = data_manager if data_manager else DataManager()
        from ArbRaces import Race
        slots = Race(race_id, data_manager=db).get_equipment_slots()
        return slots

    @staticmethod
    def get_available_slot_clothes(race_id:str, danger:int=0, budget:int=30_000, data_manager:DataManager = None):
        db = data_manager if data_manager else DataManager()
        min_tier = ItemTemplate.get_min_tier(danger)
        max_tier = ItemTemplate.get_max_tier(danger)

        available_clothes = {}
        for slot in ItemTemplate.get_available_slots(race_id, data_manager=db):
            available_clothes[slot] = [(cloth.get('id'), cloth.get('layer')) for cloth in db.select_dict('CLOTHES',
                                                                     filter=f'slot = "{slot}" AND tier >= {min_tier} AND tier <= {max_tier} AND cost <= {budget}')]

        return available_clothes

    @staticmethod
    def clear_items_by_layer(items: List[tuple], layer: int) -> List[tuple]:
        return [item for item in items if item[1] != layer]

    @staticmethod
    def generate_clothes(race_id: str, danger: int = 0, budget: int = 30_000, data_manager: DataManager = None) -> List[str]:
        db = data_manager if data_manager else DataManager()
        total_slots = ItemTemplate.get_available_slot_clothes(race_id, danger, budget, db)
        total_items = []
        for slot, potential_clothes in total_slots.items():
            while potential_clothes:
                cloth = random.choice(potential_clothes)
                total_items.append(cloth[0])
                potential_clothes = ItemTemplate.clear_items_by_layer(potential_clothes, cloth[1])
        return total_items

    @staticmethod
    def get_available_weapons(skills:list[SkillTemplate], danger:int=0, budget:int=30_000, data_manager:DataManager=None):
        db = data_manager if data_manager else DataManager()

        max_skill = ItemTemplate.get_max_combat_skill(skills, data_manager)
        min_tier = ItemTemplate.get_min_tier(danger)
        max_tier = ItemTemplate.get_max_tier(danger)

        if not max_skill:
            return ['SpecialPistol']

        available_weapons = [weapon.get('id') for weapon in db.select_dict('WEAPONS', filter=f'class = "{max_skill}" AND tier >= {min_tier} AND tier <= {max_tier} AND cost <= {budget}')]

        if not available_weapons:
            available_weapons.append('CombatKnife')
            available_weapons.append('HighRatePistol')

        return available_weapons

    @staticmethod
    def get_max_combat_skill(skills: list[SkillTemplate], data_manager:DataManager=None):
        db = data_manager if data_manager else DataManager()

        max_skill_lvl = 0
        max_skill = None
        for skill in skills:
            print(skills, skill, skill.skill_id)
            if skill.skill_id == 'MartialArms':
                continue

            if db.check('SKILL_INIT', f'id = "{skill.skill_id}" AND (role = "Стрельба" OR role = "Ближний бой")'):
                if max_skill_lvl < skill.lvl:
                    max_skill = skill.skill_id
                    max_skill_lvl = skill.lvl

        return max_skill

    @staticmethod
    def generate_weapon(skills:list[SkillTemplate], danger:int=0, budget:int=30_000, data_manager:DataManager=None):
        weapon = random.choice(ItemTemplate.get_available_weapons(skills, danger, budget, data_manager))
        return weapon

    @classmethod
    def generate_gears(cls, race_id:str, skills:list[SkillTemplate], danger:int=0, budget:int=30_000, data_manager:DataManager=None):
        db = data_manager if data_manager else DataManager()
        weapon = ItemTemplate.generate_weapon(skills, danger, budget, db)
        clothes = ItemTemplate.generate_clothes(race_id, danger, budget, db)
        total_items_types = []
        total_items_types.append(weapon)
        total_items_types.extend(clothes)

        return [ItemTemplate(item) for item in total_items_types]

    def export_to_text(self):
        clothes_text = ''.join(f'AddItem.{cloth}()\n' for cloth in self.clothes)
        weapon_text = f'AddItem.{self.weapon_id}()\n'
        return clothes_text + weapon_text


class WorldviewTemplate:
    def __init__(self, worldview_id:str, stress_points:int=None):
        self.worldview = worldview_id
        self.stress = stress_points

    def save_to_db(self, character_id:int, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        query = {
            'id': character_id,
            'worldview': self.worldview,
            'stress': self.stress
        }
        db.insert('CHARS_PSYCHOLOGY', query)

    @staticmethod
    def get_stress_points() -> int:
        return random.randint(0, 10)

    @classmethod
    def generate_worldview(cls, data_manager:DataManager = None) -> 'WorldviewTemplate':
        db = data_manager if data_manager else DataManager()
        worldview_ids = [world.get("id") for world in db.select_dict('WORLDVIEW')]
        stress_points = WorldviewTemplate.get_stress_points()
        return cls(worldview_id=random.choice(worldview_ids), stress_points=stress_points)

    def export_to_text(self):
        return f'SetWorldview("{self.worldview}")\nSetStressPoints({self.stress})\n'

    @classmethod
    def import_from_text(cls, text: str) -> 'WorldviewTemplate':
        # Используем регулярные выражения для извлечения значений
        worldview_match = re.search(r'SetWorldview\("(.*?)"\)', text)
        stress_points_match = re.search(r'SetStressPoints\((\d+)\)', text)

        if not worldview_match:
            return cls.generate_worldview()

        worldview_id = worldview_match.group(1)
        stress_points = int(stress_points_match.group(1)) if stress_points_match else None

        return cls(worldview_id=worldview_id, stress_points=stress_points)


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
            'updated': datetime.datetime.now().date().strftime('%Y-%m-%d'),
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


class CharacterTemplate:
    def __init__(self, danger: int = 0, budget: int = None, server_id: int = None,
                 race: str = None, org_id: str = None, org_rank: str = None,
                 org_lvl: int = None, basic_template: BasicTemplate = None,
                 skills: list[SkillTemplate] = None, items: list[ItemTemplate] = None,
                 worldview: WorldviewTemplate = None, picture: str = None, data_manager: DataManager = None, name: str = None, age: int = None, callsign: str = None, gender: str = None):
        self.data_manager = data_manager if data_manager else DataManager()

        self.danger = danger if danger >= 0 else 0
        self.basic_info = basic_template if basic_template else BasicTemplate(race_id=race if race else 'Human',
                                                                              gender=gender,
                                                                              org_id=org_id if org_id else 'Civil',
                                                                              org_rank=org_rank if org_rank else None,
                                                                              org_lvl=org_lvl if org_lvl else 0,
                                                                              server_id=server_id,
                                                                              danger=danger,
                                                                              picture=picture if picture else None,
                                                                              name=name if name else None,
                                                                              age=age if age else None,
                                                                              callsign=callsign if callsign else None,
                                                                              data_manager=self.data_manager)
        self.worldview = worldview if worldview else WorldviewTemplate.generate_worldview(self.data_manager)
        self.skills = skills if skills else SkillTemplate.generate_skills(danger, self.data_manager)
        budget = budget if budget else round(random.uniform(30000, 100000) * (1 + danger * 0.1), 2)
        self.items = items if items else ItemTemplate.generate_gears(self.basic_info.race, self.skills, self.danger,
                                                                     budget, self.data_manager)

    def insert_data(self) -> int:
        character_id = self.data_manager.maxValue('CHARS_INIT', 'id') + 1
        self.basic_info.save_to_db(character_id, self.data_manager)
        self.worldview.save_to_db(character_id, self.data_manager)
        for skill in self.skills:
            skill.save_to_db(character_id, self.data_manager)

        items_queries = ItemTemplate.list_to_query(character_id, self.items, data_manager=self.data_manager)
        ItemManager.batch_spawn_items(items_queries, self.data_manager, character_id)
        self.set_spawn_location(character_id, self.data_manager)

        return character_id

    @staticmethod
    def set_spawn_location(character_id:int, data_manager:DataManager = None):
        from ArbCharacters import Character

        db = data_manager if data_manager else DataManager()
        Character(character_id, data_manager=db).set_location_on_spawn()


    @classmethod
    def from_text(cls, text: str, danger: int = 0, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        main_info = BasicTemplate.import_from_text(text, db)
        if not main_info:
            main_info = None
        worldview = WorldviewTemplate.import_from_text(text)
        if not worldview:
            worldview = None
        skills = SkillTemplate.import_from_text(text)
        if not skills:
            skills = None
        items = ItemTemplate.list_from_text(text)
        if not items:
            items = None
        return cls(danger,
                   basic_template=main_info,
                   skills=skills,
                   items=items,
                   worldview=worldview,
                   data_manager=db)

    def to_text(self) -> str:
        text = self.basic_info.to_text()
        text += '\n'
        text += self.worldview.export_to_text()
        text += '\n'
        for skill in self.skills:
            text += skill.to_text()
            text += '\n'

        text += '\n'
        for item in self.items:
            text += item.to_text()
            text += '\n'

        return TemplateManager.beauty_wrap(text)


class TemplateManager(DataModel):
    def __init__(self, id:str, data_manager:DataManager=None):
        self.data_manager = data_manager if data_manager else DataManager()
        self.id = id
        
        DataModel.__init__(self, 'GEN_TEMPLATES', f'id = "{self.id}"')
        self.label = self.get('label', self.id)
        self.content = self.get('content')
        self.content = self.unwrap_content(self.content)

    @classmethod
    def create_template(cls, template_id:str, label:str, content:str, data_manager:DataManager=None):
        db = data_manager if data_manager else DataManager()

        query = {
            'id': template_id,
            'label': label,
            'content': TemplateManager.wrap_content(content)
        }
        db.insert('GEN_TEMPLATES', query)
        return cls(template_id, db)

    @staticmethod
    def wrap_content(text:str):
        content = text.split('\n')
        filtered_content = [chunk for chunk in content if chunk]
        new_content = ';'.join(filtered_content)

        return new_content

    @staticmethod
    def unwrap_content(text:str):
        content = text.split('; ')
        new_content = '\n'.join(content)

        return new_content

    @staticmethod
    def beauty_wrap(text:str):
        content = text.split('\n')
        filtered_content = [chunk for chunk in content if chunk]
        new_content = ';\n'.join(filtered_content)

        return new_content

    def delete_template(self):
        self.delete_record()


class GroupTemplate(DataModel):
    def __init__(self, id:str, data_manager:DataManager = None):
        self.data_manager = data_manager if data_manager else DataManager()
        self.id = id

        DataModel.__init__(self, 'GROUP_TEMPLATES', f'id = "{self.id}"')
        self.label = self.get('label', self.id)

    def delete_template(self):
        self.delete_record()
        self.data_manager.delete('GROUP_TEMPLATES_CONTENT', filter=f'id = "{self.id}"')

    def get_templates(self):
        templates = {}
        if self.data_manager.check('GROUP_TEMPLATES_CONTENT', filter=f'id = "{self.id}"'):
            records = self.data_manager.select_dict('GROUP_TEMPLATES_CONTENT', filter=f'id = "{self.id}"')
            for rec in records:
                if rec.get('template') not in templates:
                    templates[rec.get('template')] = 0
                templates[rec.get('template')] += rec.get('value')
        return templates

    @classmethod
    def create_template(cls, template_id: str, label: str, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()

        query = {
            'id': template_id,
            'label': label
        }
        db.insert('GROUP_TEMPLATES', query)
        return cls(template_id, db)

    def add_gen_temp(self, gen_template_id:str, value:int=1):
        query = {
            'id': self.id,
            'template': gen_template_id,
            'value': value
        }
        self.data_manager.insert('GROUP_TEMPLATES_CONTENT', query)

    def set_gen_temp(self, gen_template_id:str, value:int):
        templates = self.get_templates()
        if gen_template_id in templates:
            if value == 0:
                self.data_manager.delete('GROUP_TEMPLATES_CONTENT', f'id = "{self.id}" AND template = "{gen_template_id}"')
                return
            self.data_manager.update('GROUP_TEMPLATES_CONTENT', {'value': value}, f'id = "{self.id}" AND template = "{gen_template_id}"')
        else:
            if value != 0:
                self.add_gen_temp(gen_template_id, value)


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

    def insert_data(self, owner_id:int = None, money:float=30_000, skill_points:int=0, skill_mods_points:float=0, lvl:int=0, exp:float=0, location_id:str=None):
        from ArbOrgs import Organization


        character_id = self.data_manager.maxValue('CHARS_INIT', 'id') + 1

        basic_info = self.basicCfg.to_dict()
        basic_query = {'id': character_id,
                       'owner': owner_id,
                       'money': money}
        basic_query.update(basic_info)

        print(basic_query)

        self.data_manager.insert('CHARS_INIT', basic_query)

        combat_query = {'id': character_id,
                        'ap': 0,
                        'ap_bonus': 0,
                        'supressed': None,
                        'hunted': None,
                        'ready': None,
                        'target': None,
                        'melee_target': None}
        self.data_manager.insert('CHARS_COMBAT', combat_query)


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

        progress_query = {
            'id': character_id,
            'skills': skill_points,
            'skills_mods': skill_mods_points,
            'lvl': lvl,
            'exp': exp
        }
        self.data_manager.insert('CHARS_PROGRESS', progress_query)

        if not location_id:
            location_id = Organization(self.basicCfg.org, data_manager=self.data_manager).spawn_point

        location_query = {
            'id': character_id,
            'loc_id': location_id,
            'move_points': 2,
            'entered': 1
        }
        self.data_manager.insert('CHARS_LOC', location_query)

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
        self.endurance = kwargs.get('endurance', None)
        self.uses = kwargs.get('uses', 0)

    def get_available_id(self):
        objects = self.data_manager.select_dict('BATTLE_OBJECTS')
        if not objects:
            return 0
        else:
            return self.data_manager.maxValue('BATTLE_OBJECTS', 'object_id') + 1

    def get_endurance(self):
        if self.data_manager.check('OBJECT_TYPE', f'object_id = "{self.object_type}"'):
            print(self.object_type, self.data_manager.select_dict('OBJECT_TYPE', filter=f'object_id = "{self.object_type}"'))
            return self.data_manager.select_dict('OBJECT_TYPE', filter=f'object_id = "{self.object_type}"')[0].get('endurance')
        else:
            return 0

    def insert_data(self):
        query = {
            'battle_id': self.battle_id,
            'layer_id': self.layer_id,
            'object_id': self.get_available_id(),
            'object_type': self.object_type,
            'endurance': self.get_endurance() if not self.endurance else self.endurance,
            'uses': self.uses if self.uses else 0,
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
        self.label = kwargs.get('label', self.get_terrain_type_label()) if kwargs.get('label') else self.get_terrain_type_label()
        self.height = kwargs.get('height', 0)

        self.num_of_objects = kwargs.get('num_of_objects', random.randint(0, 15))
        self.objects = kwargs.get('objects', [])

        self.generate_objects()

    def get_terrain_type_label(self):
        if self.data_manager.check('TERRAIN_TYPE', f'id = "{self.terrain_type}"'):
            return self.data_manager.select_dict('TERRAIN_TYPE', filter=f'id = "{self.terrain_type}"')[0].get('label')
        else:
            return 'Неизвестная местность'

    def get_object_category(self):
        category = self.data_manager.select_dict('TERRAIN_TYPE', filter=f'id = "{self.terrain_type}"')
        if category:
            return category[0].get('object_types')
        else:
            return 'Хранилище'

    def get_available_objects(self):
        object_category = self.get_object_category()
        objects = [obj.get('object_id') for obj in self.data_manager.select_dict('OBJECT_TYPE', filter=f'type = "{object_category}"')]
        if not objects:
            return [obj.get('object_id') for obj in self.data_manager.select_dict('OBJECT_TYPE', filter=f'type = "Хранилище"')]

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
        self.terrain_types = kwargs.get('terrain_types', []) if kwargs.get('terrain_types') else []
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
        pprint.pprint(self.__dict__)

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

        self.members_activity = kwargs.get('members_activity', None)
        self.danger = kwargs.get('danger', random.choice([2, 4]))
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
        from ArbBattle import ActionPoints

        if self.members_value:
            for _ in range(self.members_value):
                print('Создаю персонажа...')
                basicCfg = BaseCfg(org=self.members_org_id, race=self.members_race)

                new_unit = GenerateCharacter(basicCfg=basicCfg, danger=self.danger, data_manager=self.data_manager)
                new_unit_id = new_unit.insert_data()

                prompt = {
                    'battle_id': self.battle_id,
                    'character_id': new_unit_id,
                    'layer_id': self.members_layer,
                    'object': None,
                    'initiative': random.randint(1, 100),
                    'is_active': self.members_activity,
                    'height': 0,
                    'team_id': self.id
                }

                self.data_manager.insert('BATTLE_CHARACTERS', prompt)
                ActionPoints(ap=0, actor_id=new_unit_id).new_round_ap()

        if self.generate_coordinator:
            basicCfg = BaseCfg(org=self.members_org_id, race=self.members_race)

            new_unit = GenerateCharacter(basicCfg=basicCfg, danger=self.danger, data_manager=self.data_manager)
            new_unit_id = new_unit.insert_data()

            self.coordinator = new_unit_id
            self.data_manager.update('BATTLE_TEAMS', {'coordinator': new_unit_id}, f'team_id = {self.id}')

        if self.generate_commander:
            basicCfg = BaseCfg(org=self.members_org_id, race=self.members_race)

            new_unit = GenerateCharacter(basicCfg=basicCfg, danger=self.danger, data_manager=self.data_manager)
            new_unit.insert_data()
            new_unit_id = new_unit.insert_data()

            prompt = {
                'battle_id': self.battle_id,
                'character_id': new_unit_id,
                'layer_id': self.members_layer,
                'object': None,
                'initiative': random.randint(1, 100),
                'is_active': None,
                'height': 0,
                'team_id': self.id
            }

            self.data_manager.insert('BATTLE_CHARACTERS', prompt)
            self.data_manager.update('BATTLE_TEAMS', {'commander':  new_unit_id}, f'team_id = {self.id}')
            ActionPoints(ap=0, actor_id=new_unit_id).new_round_ap()

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


class GenerateGroup:
    def __init__(self, label:str, owner:int=None, org_id:str=None, units:int=None, danger:int=None, template:str=None, data_manager:DataManager = None):
        self.data_manager = data_manager if data_manager else DataManager()
        self.label = label
        self.owner = owner if owner else None
        self.org_id = org_id if org_id else None
        self.template = template if template else None

        self.num_of_units = units if units else random.randint(5, 10)
        self.danger = danger if danger else random.randint(2, 6)

    def generate_units(self):
        if self.template is None:
            total_chars = []
            for char in range(self.num_of_units):
                char_template = CharacterTemplate(org_id=self.org_id, danger=self.danger, data_manager=self.data_manager)
                total_chars.append(char_template)
            return total_chars
        else:
            templates = GroupTemplate(self.template, data_manager=self.data_manager).get_templates()
            print(templates)
            total_chars = []
            for temp, value in templates.items():
                for _ in range(value):
                    content = TemplateManager(temp, data_manager=self.data_manager).content
                    char_template = CharacterTemplate.from_text(content, danger=self.danger, data_manager=self.data_manager)

                    if self.org_id:
                        char_template.basic_info.org = self.org_id
                        char_template.basic_info.org_lvl = char_template.basic_info.generate_rank(self.org_id, data_manager=self.data_manager)

                    total_chars.append(char_template)

            return total_chars

    def insert_data(self):
        from ArbItems import CharacterEquipment
        group_id = self.data_manager.maxValue('GROUP_INIT', 'id') + 1

        chars = self.generate_units()
        chars_ids = []
        for char in chars:
            char_id = char.insert_data()
            CharacterEquipment(char_id, data_manager=self.data_manager).validate_and_fix_equipment()
            chars_ids.append(char_id)
        captain = random.choice(chars_ids)

        group_query = {
            'id': group_id,
            'label': self.label,
            'owner_id': self.owner if self.owner else captain
        }
        self.data_manager.insert('GROUP_INIT', group_query)
        for char in chars_ids:
            query = {
                'id': char,
                'group_id': group_id,
                'role': 'Participant' if char != captain else 'Commander'
            }
            self.data_manager.insert('GROUP_CHARS', query)

        return group_id




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
