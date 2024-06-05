import datetime

from ArbDatabase import DataManager
import pprint
import random
from ArbSkills import TraitsTree, Trait, Skill, Charac


def RandomQuality():
    c_roll = random.randint(1,100)
    if c_roll <= 70:
        return 'Нормальное'
    elif 70 < c_roll:
        if random.randint(0,100) >= 99:
            return random.choice(['Легендарное','Шедевральное'])
        else:
            return random.choice(['Ужасное','Плохое','Хорошее','Отличное'])

def RandomMaterial(material_type:str, **kwargs):
    data_manager = kwargs.get('data_manager', DataManager())
    c_roll = random.randint(1, 100)
    c_materials = [mat['id'] for mat in data_manager.select_dict('MATERIALS','*',f'type = "{material_type}" AND rarity <= {c_roll}')]

    return random.choice(c_materials)


class ItemManager:
    def __init__(self, item_type:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.item_type = item_type
        self.name = kwargs.get('name', self.get_item_name_from_db())
        self.value = kwargs.get('value', 1)
        self.item_material = kwargs.get('material', None)
        self.item_quality = kwargs.get('quality', RandomQuality())
        self.biocode = kwargs.get('biocode', None)
        self.endurance = kwargs.get('endurance', random.randint(50, 100))
        self.item_class = self.get_item_class_from_db()

        self.spawn_item()

        if 'character_id' in kwargs.keys():
            self.character_id = kwargs.get('character_id', None)
            self.slot = kwargs.get('slot', None)
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
            return RandomMaterial(material_type=c_type)
        elif self.data_manager.check('WEAPONS',f'id = "{self.item_type}" AND class = "ColdSteel"'):
            return RandomMaterial(material_type='Металл')
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
        c_prompt = {
            'character_id': self.character_id,
            'item_id': self.id,
            'slot': self.slot
        }
        try:
            self.data_manager.insert('CHARS_INVENTORY', c_prompt)
            self.data_manager.logger.info(f'Предмет {self.item_type} ({self.id}) был успешно добавлен персонажу {self.character_id}')
            return True
        except Exception as e:
            self.data_manager.logger.error(f'При добавлении {self.item_type} ({self.id}) в инвентарь персонажа {self.character_id} произошла ошибка: {e}')
            return False


class WordGenerator:
    def __init__(self):
        self.vowels = ['а', 'о', 'у', 'э', 'е', 'и']
        self.consonants = ['б', 'в', 'г', 'д', 'з', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'х', 'ч', 'ш']

        self.doubles = ['с','л','р','н','б','к','м','п','а']

        self.endings_vowels = ['чк', 'ца', 'вич', 'чик', 'лин', 'шир', 'ль', 'сон', '', 'кт','йт','дж', 'чж']
        self.endings_consonants = ['ер', 'ин', 'ов', 'ан', 'ир', 'ая', 'ев', 'ов', 'ек', 'ив', '', 'инт','инг','окт']

    def add_ending(self, word:str):
        if word[-1] in self.vowels:
            return word + random.choice(self.endings_vowels)
        else:
            return word + random.choice(self.endings_consonants)

    def syllable(self, letters:int=None, last_lettr:str=None):
        c_len = letters if letters else 2
        l_letter = last_lettr if last_lettr else ''

        c_word = ''
        if l_letter:
            if l_letter in self.vowels:
                result_list = [item for item in self.consonants if item not in ['дж','чж','йт']]
                c_word = random.choice(self.consonants)
            else:
                c_word = random.choice(self.vowels)
        else:
            c_word += random.choice(self.vowels + self.consonants) if letters > 1 else random.choice(self.vowels)
        c_len -= 1

        while c_len != 0:
            if c_word[-1] in self.vowels:
                c_word += random.choice(self.consonants)
            else:
                c_word += random.choice(self.vowels)

            if c_word[-1] in self.doubles:
                if random.randint(0, 100) > 80:
                    c_word += c_word[-1]

            c_len -= 1

        return c_word

    def new_word(self, syllables:int=2, ending:bool = True):
        c_word = self.syllable(random.randint(1,3))
        syllables -= 1
        last_len = 0
        for i in range(syllables):
            if last_len < 3 and ('`' not in c_word or ' ' in c_word):
                c_prefix = random.choice(['`']) if random.randint(0, 100) > 80 else ''
            else:
                c_prefix = ''

            c_word += f"{c_prefix}{self.syllable(random.randint(1, 3))}"
        if ending:
            c_word = self.add_ending(c_word)
        else:
            pass

        return c_word


class NewCharacter:
    def __init__(self, **kwargs):
        self.input_pars = {key.lower(): value for key, value in kwargs.items()}

        self.__dict__.update(self.input_pars)
        self.data_manager = self.input_pars.get('data_manager', DataManager())
        self.generate_main_info()

        self.budget = self.input_pars.get('budget', random.randint(50000, 100000))

        self.characteristics = self.input_pars.get('characteristics', self.generate_characteristics())

        self.max_tier = self.input_pars.get('max_tier', 2)
        self.min_tier = self.input_pars.get('min_tier', 0)

        if 'traits' in self.input_pars:
            self.traits = self.input_pars.get('traits')
        else:
            self.traits = self.generate_traits()

        if 'skills' in self.input_pars:
            self.skills_values = self.input_pars.get('skills')
        else:
            self.skills = self.generate_skills()
            self.mastery = self.generate_mastery()
            self.talants = self.generate_talents()

            self.skills_values = {}
            for skill in self.skills.keys():
                self.skills_values[skill] = {'lvl': self.skills[skill],
                                      'talant': self.talants[skill],
                                      'mastery': self.mastery[skill]}


        self.weapon = self.input_pars.get('weapons', self.generate_weapon())
        if self.weapon:
            self.weapon = random.choice(self.weapon).get('id')
        else:
            self.weapon = None

        self.armors = self.input_pars.get('armors', self.generate_armor())

    def generate_main_info(self):
        self.id = self.input_pars.get('id', self.data_manager.maxValue('CHARS_INIT','id') + 1)

        self.name = self.input_pars.get('name',f'{WordGenerator().new_word().capitalize()} {WordGenerator().new_word().capitalize()}')
        self.custom_id = self.input_pars.get('custom_id',None)
        self.owner = self.input_pars.get('owner', None)
        self.callsign = self.input_pars.get('callsign', None)
        self.org = self.input_pars.get('org', None)
        self.org_lvl = self.input_pars.get('org_lvl', None)
        self.fraction = self.input_pars.get('frac', None)
        self.fraction_lvl = self.input_pars.get('frac_lvl', None)
        self.avatar_picture = self.input_pars.get('avatar', None)
        self.update = self.input_pars.get('update', f'{datetime.datetime.now().date()}')
        self.server = self.input_pars.get('server', None)
        self.sex = self.input_pars.get('gender', 'Неизвестно')
        self.age = self.input_pars.get('age', random.randint(25, 45))
        self.race = self.input_pars.get('race', 'Human')

        self.location = self.input_pars.get('location', None)
        self.group_id = self.input_pars.get('group_id', None)

    def generate_characteristics(self):
        c_delta = self.input_pars.get('chars_delta', 0)
        c_bonus = self.input_pars.get('chars_bonus', 0)

        char_points = (self.age - 30) // 5 + c_bonus
        chars_values = {
            'Сила': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Ловкость': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Выносливость': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Реакция': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Привлекательность': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Интеллект': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
            'Уравновешанность': random.randint(max(0, 20 - c_delta), max(0, 20 + c_delta)),
        }

        for char in chars_values.keys():
            char_points += 20 - chars_values[char]

        for char in chars_values.keys():
            if char_points <= 0:
                break
            else:
                c_points = random.randint(min(char_points, 1), max(char_points, 0))
                char_points -= c_points
                chars_values[char] += c_points

        if char_points > 0:
            chars_values[random.choice(list(chars_values.keys()))] += char_points

        chars_values['Связь'] = random.randint(0, 100)

        return chars_values

    def fetch_skills(self):
        return self.data_manager.select_dict('SKILL_INIT')

    def available_traits(self, traits_list: list):
        if not traits_list:
            return [trait[0] for trait in self.data_manager.select('TRAITS_INIT', 'id', 'lvl = 0')]
        else:
            available_traits = []
            for trait_dict in self.data_manager.select_dict('TRAITS_INIT', filter='lvl = 0'):
                trait_id = trait_dict['id']
                if trait_id not in traits_list and trait_dict['exception'] not in traits_list:
                    available_traits.append(trait_id)

            for trait in traits_list:
                trait_data = self.data_manager.select_dict('TRAITS_INIT', filter=f'id = "{trait}"')[0]
                if trait_data:
                    c_tree = trait_data.get('tree')
                    c_traits = TraitsTree(c_tree, current_trait_id=trait).random_next_trait()
                    if c_traits is not None and c_traits['id'] not in traits_list and c_traits.get(
                            'exception') not in traits_list:
                        available_traits.append(c_traits['id'])

            return available_traits

    def generate_skills(self):
        c_bonus = self.input_pars.get('skills_bonus', 0)

        skill_points = 150 + (self.age - 30) // 2 + c_bonus
        skills_values = {}

        skills_info = self.fetch_skills()

        skills_count = self.input_pars.get('skills_count', random.randint(min(skill_points//50, 3), skill_points // 50))

        skills_types = {}
        for skill in skills_info:
            role = skill.get('role')
            if role not in skills_types:
                skills_types[role] = [skill.get('id')]
            else:
                skills_types[role].append(skill.get('id'))

        # Выбор хотя бы одного боевого навыка
        chosen_skill = random.choice(skills_types.get('Ближний бой') + skills_types.get('Стрельба'))

        c_points = random.randint(10, min(skill_points, 100))  # Прокачка хотя бы 10 очков для боевого навыка
        skills_values[chosen_skill] = c_points
        skills_count -= 1
        skill_points -= c_points

        while skills_count > 0 and skill_points > 1:
            c_skill_name = random.choice(list(skills_types[random.choice(list(skills_types.keys()))]))
            if c_skill_name not in skills_values:
                c_points = random.randint(max(0, skill_points // skills_count), min(skill_points, 100))
                skills_values[c_skill_name] = c_points
                skills_count -= 1
                skill_points -= c_points

        if skill_points > 0:
            random_skill = random.choice(list(skills_values.keys()))
            skills_values[random_skill] += skill_points

        return skills_values

    def generate_talents(self):
        talants = 2 - (self.age - 30) // 5
        count_skills = len(list(self.skills.keys()))
        avr_talant = talants / count_skills

        total = {}
        for skill in self.skills:
            total[skill] = 1 + round(random.uniform(min(1, avr_talant), max(1, avr_talant)), 2)

        return total

    def generate_mastery(self):
        mastery = 1 + (self.age - 30) // 5
        count_skills = len(list(self.skills.keys()))
        avr_mastery = mastery / count_skills

        total = {}
        for skill in self.skills:
            total[skill] = 1 + round(random.uniform(min(1, avr_mastery), max(1, avr_mastery)), 2)

        return total

    def generate_traits(self):
        c_bonus = self.input_pars.get('traits_bonus', 0)
        trait_points = 20 + (self.age - 30) // 5 + c_bonus
        c_traits = []
        for i in range(trait_points):
            c_available = self.available_traits(c_traits)
            c_traits.append(random.choice(c_available))

        return c_traits

    def fetch_race_parts(self):
        return self.data_manager.select_dict('RACES_BODY',filter=f'race = "{self.race}"')

    def generate_weapon(self):
        c_parts = self.fetch_race_parts()
        total_slots = 0
        for _ in c_parts:
            total_slots += _.get('weapon_slot',0) if _.get('weapon_slot',0) is not None else 0

        total_weapons = []

        for skill in self.skills.keys():
            if self.data_manager.check('WEAPONS',filter=f'class = "{skill}"'):
                c_weapon_list = self.data_manager.select_dict('WEAPONS',filter=f'class = "{skill}" AND tier <= {self.max_tier} AND tier > {self.min_tier} AND cost <= {self.budget * 0.5}')
                total_weapons += c_weapon_list

        return total_weapons

    def generate_armor(self):
        c_parts = self.fetch_race_parts()
        total_slots = []
        for _ in c_parts:
            if _.get('name') is not None and _.get('name') not in total_slots:
                total_slots.append(_.get('name'))

        avr_cost = (self.budget * 0.5) / len(total_slots)

        total_clothes = {}

        allowed_clothes = {}
        for slot in total_slots:
            c_clothes = self.data_manager.select_dict('CLOTHES',filter=f'slot = "{slot}" AND cost <= {avr_cost} AND tier <= {self.max_tier} AND tier > {self.min_tier}')
            allowed_clothes[slot] = {}

            for cloth in c_clothes:
                if cloth.get('layer',None) in allowed_clothes[slot]:
                    allowed_clothes[slot][cloth.get('layer',None)].append(cloth)
                else:
                    allowed_clothes[slot][cloth.get('layer', None)] = [cloth]

        for slot in allowed_clothes.keys():
            total_clothes[slot] = {}
            for index in allowed_clothes[slot].keys():
                total_clothes[slot][index] = random.choice(allowed_clothes[slot][index])

        return total_clothes

    def generate_equipment(self):
        pass

    def insert_data(self):
        main_info_query = {
            'id': self.id,
            'custom_id': self.custom_id,
            'owner': self.owner,
            'name': self.name,
            'callsign': self.callsign,
            'age': self.age,
            'race': self.race,
            'sex': self.sex,
            'org': self.org,
            'org_lvl': self.org_lvl,
            'frac': self.fraction,
            'frac_lvl': self.fraction_lvl,
            'avatar': self.avatar_picture,
            'update': self.update,
            'server': self.server
        }

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

        self.data_manager.insert('CHARS_INIT',main_info_query)
        self.data_manager.insert('CHARS_COMBAT', combat_info_query)

        for n_skill in self.skills_values.keys():
            s_query = {'id': self.id,
                       'skill_id': n_skill,
                       'lvl': self.skills_values[n_skill]['lvl'],
                       'talant': self.skills_values[n_skill]['talant'],
                       'master': self.skills_values[n_skill]['mastery'],
                       'exp': 0}

            self.data_manager.insert('CHARS_SKILLS', s_query)

        for charac in self.characteristics.keys():
            c_query = {'id': self.id,
                       'char': charac,
                       'lvl': self.characteristics[charac]}
            self.data_manager.insert('CHARS_CHARS', c_query)

        for trait in self.traits:
            t_query = {'id': self.id,
                       'trait': trait}
            self.data_manager.insert('CHARS_TRAITS', t_query)

        if self.weapon:
            ItemManager(self.weapon, character_id=self.id, slot='Оружие')

        for slot in self.armors.keys():
            for layer in self.armors[slot].keys():
                c_item = self.armors[slot][layer]
                ItemManager(c_item['id'], character_id=self.id, slot=c_item.get('slot', None))


#for _ in range(25):
#    print(WordGenerator().new_word(2).capitalize(), WordGenerator().new_word(2).capitalize())