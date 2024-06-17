import datetime

from ArbDatabase import DataManager
import pprint
import random
from ArbSkills import TraitsTree, Trait, Skill, Charac
from ArbUtils.ArbTextgen import CallsGenerator
from typing import List, Dict, Optional


def RandomQuality():
    c_roll = random.randint(1,100)
    if c_roll <= 70:
        return 'Нормальное'
    elif 70 < c_roll:
        if random.randint(0,100) >= 99:
            return random.choice(['Легендарное','Шедевральное'])
        else:
            return random.choice(['Ужасное','Плохое','Хорошее','Отличное'])

def RandomMaterial(material_type:str, tier:int, **kwargs):
    data_manager = kwargs.get('data_manager', DataManager())

    min_rarity = data_manager.minValue('MATERIALS','rarity',f'type = "{material_type}"')

    c_roll = random.randint(min_rarity, 100)
    c_materials = [mat['id'] for mat in data_manager.select_dict('MATERIALS','*',f'type = "{material_type}" AND rarity <= {c_roll} AND tier <= {tier}')]

    return random.choice(c_materials)


def NameGenerator(gender:str):
    if gender.lower() in ['м','мужской','мужчина','муж','male','m']:
        name = CallsGenerator('ArbUtils/data_models/male_names.csv').generate_text(use_trigrams=False)
    elif gender.lower() in ['ж','женский','женщина','девушка','жен','female','fem','f']:
        name = CallsGenerator('ArbUtils/data_models/female_names.csv').generate_text(use_trigrams=False)
    elif gender.lower() in ['робот','robot','ai','android']:
        return CallsGenerator('ArbUtils/data_models/robot_names.csv').generate_text(use_trigrams=False)
    else:
        return CallsGenerator('ArbUtils/data_models/male_names.csv').generate_text(use_trigrams=False)

    surname = CallsGenerator('ArbUtils/data_models/surnames.csv').generate_text(use_trigrams=False)

    return f'{name} {surname}'



class ItemManager:
    def __init__(self, item_type:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.item_type = item_type
        self.name = kwargs.get('name', self.get_item_name_from_db())
        self.value = kwargs.get('value', 1)
        self.material_tier = kwargs.get('material_tier', 1)
        self.item_material = kwargs.get('material', None)
        self.item_quality = kwargs.get('quality', RandomQuality())
        self.biocode = kwargs.get('biocode', None)
        self.endurance = kwargs.get('endurance', random.randint(50, 100))
        self.item_class = self.get_item_class_from_db()

        self.spawn_item()

        if 'character_id' in kwargs.keys():
            self.character_id = kwargs.get('character_id', None)
            self.slot = kwargs.get('slot', None)
            self.bullets = -1 if kwargs.get('inf_bullets', True) else 0
            print('БЕСК. ПАТРОНЫ', self.bullets, kwargs.get('inf_bullets'))
            self.ammo_id = kwargs.get('ammo_id', None)
            self.inventory = kwargs.get('inventory_id', -1)

            self.add_to_character()

    def get_item_class_from_db(self):
        tables_to_search = ['ITEMS_INIT', 'WEAPONS', 'CLOTHES', 'AMMO']
        for table in tables_to_search:
            if self.data_manager.check(table, f'id = "{self.item_type}"'):
                result = self.data_manager.selectOne(table, 'name', f"id='{self.item_type}'")
                if result:
                    if table == 'ITEMS_INIT':
                        return 'Предмет'
                    elif table == 'WEAPONS':
                        self.item_material = self.random_material()
                        return 'Оружие'
                    elif table == 'CLOTHES':
                        self.item_material = self.random_material()
                        return 'Одежда'
                    elif table == 'AMMO':
                        self.item_quality = None
                        self.item_material = None
                        return 'Боеприпасы'
        return "Другое"

    def random_material(self):
        if self.data_manager.check('CLOTHES',f'id = "{self.item_type}"'):
            c_type = self.data_manager.select_dict('CLOTHES',filter=f'id = "{self.item_type}"')[0].get('material_type', None)
            return RandomMaterial(material_type=c_type, tier=self.material_tier)
        elif self.data_manager.check('WEAPONS',f'id = "{self.item_type}" AND class = "ColdSteel"'):
            return RandomMaterial(material_type='Металл', tier=self.material_tier)
        else:
            return None

    def get_item_name_from_db(self):
        tables_to_search = ['ITEMS_INIT', 'WEAPONS', 'CLOTHES', 'AMMO']
        for table in tables_to_search:
            if self.data_manager.check(table, f'id = "{self.item_type}"'):
                result = self.data_manager.selectOne(table, 'name', f"id='{self.item_type}'")
                if result:
                    return result[0]
        return "Неизвестный предмет"

    def spawn_item(self):
        self.id = int(self.data_manager.maxValue('ITEMS', 'id')) + 1 if self.data_manager.check('ITEMS', 'id') else 0

        item_data = {
            'id': self.id,
            'name': self.name,
            'class': self.item_class,
            'type': self.item_type,
            'value': self.value,
            'material': self.item_material,
            'quality': self.item_quality,
            'endurance': self.endurance,
            'biocode': self.biocode
        }

        try:
            self.data_manager.insert('ITEMS', item_data)
            self.data_manager.logger.info(f'Предмет {self.item_type} ({self.id}) был успешно создан')
            return self.id
        except Exception as e:
            self.data_manager.logger.error(f'При создании {self.item_type} ({self.id}) произошла ошибка: {e}')
            return None

    def add_to_character(self):
        try:
            if self.item_class == 'Одежда':
                c_prompt = {
                    'id': self.character_id,
                    'item_id': self.id,
                    'slot': self.slot,
                    'bullets': None,
                    'ammo_id': None
                }

                self.data_manager.insert('CHARS_EQUIPMENT', c_prompt)
            elif self.item_class == 'Оружие':
                c_prompt = {
                    'id': self.character_id,
                    'item_id': self.id,
                    'slot': self.slot,
                    'bullets': self.bullets,
                    'ammo_id': self.ammo_id
                }

                self.data_manager.insert('CHARS_EQUIPMENT', c_prompt)
            else:
                c_prompt = {
                    'id': self.id,
                    'inventory': self.inventory
                }
                self.data_manager.insert('INVENTORY_ITEMS', c_prompt)

            self.data_manager.logger.info(f'Предмет {self.item_type} ({self.id}) был успешно добавлен персонажу {self.character_id}')
            return True
        except Exception as e:
            self.data_manager.logger.error(f'При добавлении {self.item_type} ({self.id}) в инвентарь персонажа {self.character_id} произошла ошибка: {e}')
            return False


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


class GenerateCharacter:
    BASE_POINTS = 100
    DANGER_MULTIPLIER = 50
    AGE_BONUS_THRESHOLD = 30
    AGE_BONUS_FACTOR = 5
    CP_TO_BUDGET = 500
    BASE_CHARACTERISTIC = 20
    BASE_SKILL = 50
    MAX_SKILLS = 6

    def __init__(self, **kwargs):
        self.input_pars = kwargs
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = kwargs.get('id', self.data_manager.maxValue('CHARS_INIT', 'id')+1)
        self.owner = kwargs.get('owner', None)

        self.gender = kwargs.get('gender', random.choice(['Мужчина', 'Женщина']))
        self.name = kwargs.get('name', NameGenerator(self.gender))
        self.callsign = kwargs.get('callsign', None)
        self.custom_id = kwargs.get('custom_id', None)
        self.age = kwargs.get('age', random.randint(25, 50))
        self.race = kwargs.get('race', 'Human')

        self.org = kwargs.get('org', None)
        self.org_lvl = kwargs.get('org_lvl', None)
        self.frac = kwargs.get('frac', None)
        self.frac_lvl = kwargs.get('frac_lvl', None)

        self.location = kwargs.get('location', None)

        self.avatar = kwargs.get('avatar', None)
        self.update = kwargs.get('update', datetime.datetime.now().date().__str__())
        self.server = kwargs.get('server', None)

        self.danger = kwargs.get('danger', random.randint(1,5))
        self.character_points = self.calculate_character_points(kwargs.get('character_points', 0))

        self.budget = self.calculate_budget()
        self.min_tier = kwargs.get('min_tier', 1)
        self.max_tier = kwargs.get('max_tier', 3)

        self.characteristics = self.generate_characteristics()
        self.skills = self.generate_skills_values()
        self.weapon = self.choose_weapon()
        self.armors = self.generate_armor()

        self.scars = kwargs.get('scars',self.generate_scars(random.randint(1, 5)))

        self.worldview = kwargs.get('worldview', self.generate_worldview())
        self.stress = kwargs.get('stress', random.randint(0, 10))
        rep, loyalty = self.generate_loyalty()

        self.rep = kwargs.get('reputation', rep)
        self.loyalty = kwargs.get('loyalty', loyalty)

    def calculate_character_points(self, bonus:int) -> int:
        base_points = self.BASE_POINTS
        danger_points = self.danger * self.DANGER_MULTIPLIER
        age_bonus = (self.age - self.AGE_BONUS_THRESHOLD) // self.AGE_BONUS_FACTOR if self.age > self.AGE_BONUS_THRESHOLD else 0

        character_points = base_points + danger_points + age_bonus + bonus
        return character_points

    def calculate_budget(self):
        return self.character_points * self.CP_TO_BUDGET

    def generate_characteristics(self) -> dict[str, int]:
        points_available = self.character_points // 4
        base_characteristics = {
            'Сила': self.BASE_CHARACTERISTIC,
            'Ловкость': self.BASE_CHARACTERISTIC,
            'Выносливость': self.BASE_CHARACTERISTIC,
            'Реакция': self.BASE_CHARACTERISTIC,
            'Привлекательность': self.BASE_CHARACTERISTIC,
            'Интеллект': self.BASE_CHARACTERISTIC,
            'Уравновешанность': self.BASE_CHARACTERISTIC,
            'Связь': random.randint(0, 100)
        }

        while points_available > 0:
            for char in base_characteristics.keys():
                if points_available <= 0:
                    break
                if char == 'Связь':
                    continue
                increase = random.randint(1, min(5, points_available))
                base_characteristics[char] += increase
                points_available -= increase

        return base_characteristics

    def fetch_skills(self) -> list[dict]:
        return self.data_manager.select_dict('SKILL_INIT')

    def generate_skills_values(self) -> dict[str, dict[str, float]]:
        skills = self.generate_skills()
        mastery = self.generate_mastery(skills)
        talents = self.generate_talents(skills)

        skills_values = {
            skill: {'lvl': round(min(level, 100 * mastery[skill])), 'talent': talents[skill], 'mastery': mastery[skill]}
            for skill, level in skills.items()
        }

        return skills_values

    def generate_talents(self, skills: dict[str, int]) -> dict[str, float]:
        max_talent = min(2 + self.danger, 2)  # Максимальное значение таланта зависит от уровня опасности
        return {skill: round(random.uniform(0, max_talent), 2) for skill in skills}

    def generate_mastery(self, skills: dict[str, int]) -> dict[str, float]:
        max_mastery = min(2 + self.danger, 2)  # Максимальное значение мастерства зависит от уровня опасности
        return {skill: round(random.uniform(0, max_mastery), 2) for skill in skills}

    def generate_skills(self) -> dict[str, int]:
        skill_points = self.character_points // 2
        skills_values = {}

        skills_info = self.fetch_skills()
        skills_count = min(self.MAX_SKILLS, 2 + self.danger)  # Максимальное количество навыков зависит от уровня опасности

        skills_types = {}
        for skill in skills_info:
            role = skill.get('role')
            if role not in skills_types:
                skills_types[role] = [skill.get('id')]
            else:
                skills_types[role].append(skill.get('id'))

        while skills_count > 0 and skill_points > 1:
            role = random.choice(list(skills_types.keys()))
            c_skill_name = random.choice(skills_types[role])
            if c_skill_name not in skills_values:
                c_points = random.randint(1, min(skill_points, 100))
                skills_values[c_skill_name] = self.BASE_SKILL + c_points
                skills_count -= 1
                skill_points -= c_points

        if skill_points > 0:
            random_skill = random.choice(list(skills_values.keys()))
            skills_values[random_skill] += skill_points

        return skills_values

    def choose_default_weapon(self):
        if not self.org or self.org == 'Civil':
            return None
        else:
            return random.choice(['SpecialPistol','LargeCaliberPistol','HighRatePistol'])

    def choose_weapon(self) -> Optional[str]:
        weapons = self.input_pars.get('weapons', self.generate_weapon())
        return random.choice(weapons).get('id') if weapons else self.choose_default_weapon()

    def fetch_race_parts(self) -> List[Dict[str, str]]:
        return self.data_manager.select_dict('RACES_BODY', filter=f'race = "{self.race}"')

    def generate_weapon(self) -> List[Dict[str, str]]:
        c_parts = self.fetch_race_parts()
        total_slots = sum(_.get('weapon_slot', 0) for _ in c_parts)

        total_weapons = []

        for skill in self.skills.keys():
            if self.data_manager.check('WEAPONS', filter=f'class = "{skill}"'):
                c_weapon_list = self.data_manager.select_dict('WEAPONS',
                                                              filter=f'class = "{skill}" AND tier <= {self.max_tier} AND tier >= {self.min_tier} AND cost <= {self.budget * 0.5} AND slot <= {total_slots}')
                total_weapons += c_weapon_list

        return total_weapons

    def generate_armor(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        c_parts = self.fetch_race_parts()
        print(c_parts)
        total_slots = {_.get('name'): {} for _ in c_parts if _.get('name')}  # Initialize with an empty dictionary for each slot

        if not total_slots:
            return {}

        avr_cost = self.budget * 0.5 / len(total_slots)

        for slot in total_slots.keys():
            total_slots[slot] = {}
            c_clothes = self.data_manager.select_dict('CLOTHES',
                                                      filter=f'slot = "{slot}" AND cost <= {avr_cost} AND tier <= {self.max_tier} AND tier >= {self.min_tier}')
            for cloth in c_clothes:
                layer = cloth.get('layer')
                if layer not in total_slots[slot]:
                    total_slots[slot][layer] = []
                total_slots[slot][layer].append(cloth)

        total_clothes = {slot: {layer: random.choice(clothes) for layer, clothes in layers.items()} for slot, layers in
                         total_slots.items()}

        return total_clothes

    def random_scar(self) -> str:
        parts = self.fetch_race_parts()
        candidates = [part for part in parts if part.get('internal', 1) == 0]
        return random.choice(candidates).get('part_id') if random.randint(0, 100) >= 85 else None

    def generate_scars(self, num:int=1) -> list[str]:
        scars = []
        for _ in range(num):
            part = self.random_scar()
            if part:
                scars.append(part)

        return scars

    def generate_worldview(self):
        worldviews: list[dict] = self.data_manager.select_dict('WORLDVIEW')
        return random.choice(worldviews).get('id')

    def generate_loyalty(self):
        if self.org:
            return random.randint(-100, 100), random.randint(0, 100)
        else:
            return 0, 0

    def insert_data(self):
        main_info_query = {
            'id': self.id,
            'custom_id': self.custom_id,
            'owner': self.owner,
            'name': self.name,
            'callsign': self.callsign,
            'age': self.age,
            'race': self.race,
            'sex': self.gender,
            'org': self.org,
            'org_lvl': self.org_lvl,
            'frac': self.frac,
            'frac_lvl': self.frac_lvl,
            'avatar': self.avatar,
            'update': self.update,
            'server': self.server
        }

        self.data_manager.insert('CHARS_INIT', main_info_query)

        combat_info_query = {
            'id': self.id,
            'ap': 0,
            'ap_bonus': 0,
            'luck': random.randint(0, 100),
            'blood_lost': 0,
            'supressed': None,
            'hunted': None,
            'contained': None,
            'ready': None,
            'target': None,
            'movement_points': 0,
            'melee_target': None
        }

        self.data_manager.insert('CHARS_COMBAT', combat_info_query)

        worldview_query = {
            'id': self.id,
            'worldview': self.worldview,
            'stress': self.stress
        }
        self.data_manager.insert('CHARS_PSYCHOLOGY', worldview_query)

        if self.org:
            loyalty_query = {
                'id': self.id,
                'org': self.org,
                'rep': self.rep,
                'loyalty': self.loyalty
            }
            self.data_manager.insert('CHARS_REPUTATION', loyalty_query)

        for n_skill in self.skills:
            s_query = {'id': self.id,
                       'skill_id': n_skill,
                       'lvl': self.skills[n_skill]['lvl'],
                       'talant': self.skills[n_skill]['talent'],
                       'master': self.skills[n_skill]['mastery'],
                       'exp': 0}

            self.data_manager.insert('CHARS_SKILLS', s_query)

        for charac in self.characteristics.keys():
            c_query = {'id': self.id,
                       'char': charac,
                       'lvl': self.characteristics[charac]}
            self.data_manager.insert('CHARS_CHARS', c_query)

        inventory = create_inventory(f'Инвентарь {self.name}', self.id, 'Инвентарь', data_manager=self.data_manager)

        if self.weapon:
            inf_bullets = True if not self.owner else False
            ItemManager(self.weapon, material_tier=self.max_tier, character_id=self.id, slot='Оружие', endurance=random.randint(50, 100), inventory=inventory, inf_bullets=inf_bullets)

        for slot in self.armors.keys():
            for layer in self.armors[slot].keys():
                c_item = self.armors[slot][layer]
                ItemManager(c_item['id'], material_tier=self.max_tier, character_id=self.id, slot=c_item.get('slot', None), endurance=c_item.get('endurance', 100), inventory=inventory)

        return self.__dict__

pprint.pprint(GenerateCharacter().insert_data())
