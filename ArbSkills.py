import pprint

from ArbDatabase import *
from ArbHealth import Body
from ArbRoll import RollSkill, RollCharacteristic, RollCapacity
from dataclasses import dataclass


class Charac:
    def __init__(self, name: str):
        self.Name = name

    def Add(self, char_id: int, value: int):
        DataManager().update('CHARS_CHARS', {'skill': f'skill + {value}'}, f'id = {char_id} AND char = "{self.Name}"')

    def Check(self, char_id: int):
        result = DataManager().selectOne('CHARS_CHARS', 'skill', f'char = "{self.Name}" AND id = {char_id}')
        return result[0] if result else 0

    def __str__(self):
        return f'Показатель "{self.Name}"'

    def __repr__(self):
        return f'Charac.{self.Name}'


class Skill:
    def __init__(self, id: str):
        self.ID = id
        skill_data = DataManager().select('SKILL_INIT', f'label, desc, role, char, add_char, capacity, add_capacity',f'id = "{self.ID}"')[0]
        self.Label = skill_data[0]
        self.Desc = skill_data[1]
        self.Role = skill_data[2]
        self.Char = skill_data[3]
        self.AddChar = skill_data[4]
        self.Capacity = skill_data[5]
        self.AddCapacity = skill_data[6]

    def add_level(self, char_id: int, value: int) -> None:
        if DataManager().check('CHARS_SKILLS', filter=f'id = {char_id} AND skill_id = "{self.ID}"'):
            DataManager().update('CHARS_SKILLS', {'lvl': f'lvl + {value}'}, f'id = {char_id} AND skill_id = "{self.ID}"')
        else:
            DataManager().insert('CHARS_SKILLS',{'id': char_id,
                                                 'skill_id': self.ID,
                                                 'lvl': value,
                                                 'master': 1,
                                                 'talant': 1,
                                                 'exp': 0})

    def add_exp(self, char_id:int, value:float) -> None:
        if DataManager().check('CHARS_SKILLS',filter=f'id = {char_id} AND skill_id = "{self.ID}"'):
            DataManager().update('CHARS_SKILLS', {'exp': f'exp + {value}'}, f'id = {char_id} AND skill_id = "{self.ID}"')
        else:
            DataManager().insert('CHARS_SKILLS', {'id': char_id,
                                                  'skill_id': self.ID,
                                                  'lvl':0,
                                                  'master': 1,
                                                  'talant': 1,
                                                  'exp': value})

    def add_mastery(self, char_id: int, value: float) -> None:
        if DataManager().check('CHARS_SKILLS', filter=f'id = {char_id} AND skill_id = "{self.ID}"'):
            DataManager().update('CHARS_SKILLS', {'master': f'master + {value}'}, f'id = {char_id} AND skill_id = "{self.ID}"')
        else:
            DataManager().insert('CHARS_SKILLS', {'id': char_id,
                                                  'skill_id': self.ID,
                                                  'lvl': 0,
                                                  'master': value,
                                                  'talant': 1,
                                                  'exp': value})

    def add_talant(self, char_id: int, value: float) -> None:
        if DataManager().check('CHARS_SKILLS', filter=f'id = {char_id} AND skill_id = "{self.ID}"'):
            DataManager().update('CHARS_SKILLS', {'talant': f'talant + {value}'}, f'id = {char_id} AND skill_id = "{self.ID}"')
        else:
            DataManager().insert('CHARS_SKILLS', {'id': char_id,
                                                  'skill_id': self.ID,
                                                  'lvl': 0,
                                                  'master': 1,
                                                  'talant': value,
                                                  'exp': value})

    def check_level(self, char_id: int) -> float:
        result = DataManager().selectOne('CHARS_SKILLS', 'lvl', f'name = "{self.Label}" AND id = {char_id}')
        return result[0] if result else 0

    def check_talant(self, char_id: int) -> float:
        return DataManager().selectOne('CHARS_SKILLS', 'talant', f'name = "{self.Label}" AND id = {char_id}')[0]

    def check_mastery(self, char_id: int) -> float:
        return DataManager().selectOne('CHARS_SKILLS', 'master', f'name = "{self.Label}" AND id = {char_id}')[0]

    def __str__(self):
        return f'Навык "{self.Label}"'

    def __repr__(self):
        return f'Skill.{self.ID}'


class Trait:
    def __init__(self, id: str, **kwargs):
        self.ID = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.trait_data = self.data_manager.select_dict('TRAITS_INIT', '*', f'id = "{self.ID}"')[0]
        self.trait_effects = self.data_manager.select_dict('TRAITS_BAFFS', filter=f'trait_id = "{self.ID}"')

    def add(self, char_id: int) -> None:
        self.data_manager.insert('CHARS_TRAITS', {'char_id': char_id, 'trait': self.ID})

        for effect in self.trait_effects:
            effect_type = effect.get('type', '')

            if effect_type.endswith('.Char'):
                Charac(effect['parametr']).Add(char_id, effect['value'])
            elif effect_type.endswith('.Skill'):
                Skill(effect['parametr']).add_level(char_id, effect['value'])
            elif effect_type.endswith('.Talant'):
                Skill(effect['parametr']).add_talant(char_id, effect['value'])
            elif effect_type.endswith('.Mastery'):
                Skill(effect['parametr']).add_mastery(char_id, effect['value'])

    def __str__(self):
        return f'Черта "{self.trait_data.get("Name", "")}"'

    def __repr__(self):
        return f'Trait.{self.ID}'


class TraitsTree:
    def __init__(self, tree_name:str, **kwargs):
        self.tree_name = tree_name
        self.data_manager = kwargs.get('data_manager', DataManager())

        self.all_traits = self.data_manager.select_dict('TRAITS_INIT', filter=f'tree = "{self.tree_name}"')

        self.current_trait_id = kwargs.get('current_trait_id', self.all_traits[0].get('id'))
        self.current_lvl = int(self.current_trait_id.split('.')[-1])
        self.branch = self.current_trait_id.split('.')[1] if len(self.current_trait_id.split('.')) == 3 else None

    def tree_branches(self):
        next_lvl = self.current_lvl + 1
        if next_lvl == 12:
            return None
        else:
            total = {}
            for trait in self.all_traits:
                c_branch = trait.get('id').split('.')[1] if len(trait.get('id').split('.')) == 3 else None
                c_lvl = trait.get('lvl', 0)

                if c_branch in total:
                    total[c_branch][c_lvl] = trait.get('id')
                else:
                    total[c_branch] = {c_lvl: trait.get('id')}

            return total

    def next_trait(self):
        return self.data_manager.select_dict('TRAITS_INIT',filter=f'requirment = "{self.current_trait_id}"')

    def random_next_trait(self):
        return random.choice(self.next_trait()) if self.next_trait() else None

    def all_next_traits(self):
        c_list = self.tree_branches()
        if self.branch:
            total = []
            for x in c_list[self.branch].keys():
                if self.current_lvl == 11:
                    return None
                elif x <= self.current_lvl:
                    continue
                else:
                    total.append(c_list[self.branch].get(x))

            return total

        else:
            total = []
            for branch in c_list.keys():
                for x in c_list[branch].keys():
                    if x <= self.current_lvl:
                        continue
                    else:
                        total.append(c_list[branch].get(x))

            return total


class Ability:
    def __init__(self, ability_id, *,data_manager: DataManager = None):
        self.ability_id = ability_id
        self.data_manager = data_manager if data_manager else DataManager()

        self.name = ''
        self.description = ''
        self.type = ''
        self.requirement = {}

        self.load_from_database()

        self.parameters = self.load_parameters()

    def load_from_database(self):
        ability_data = self.data_manager.select_dict('ABILITIES',columns='*',filter=f'id = "{self.ability_id}"')[0]
        if ability_data:
            self.name = ability_data.get('label','')
            self.description = ability_data.get('desc','')
            self.type = ability_data.get('type','')
            self.requirement = ability_data.get('requirement',{})
            self.requirement = json.loads(self.requirement)
        else:
            self.data_manager.logger.error(f"Ability with ID {self.ability_id} not found in the database.")

    def load_parameters(self):
        parameters_data = self.data_manager.select_dict('ABILITIES_PARAMETRS', columns='*',
                                                        filter=f'ability_id = "{self.ability_id}"')
        parameters = {}
        for param in parameters_data:
            param_name = param.get('parametr', '')
            param_value = param.get('value', '')
            parameters[param_name] = param_value
        return parameters



class SkillInit:
    def __init__(self, skill_id:str, **kwargs):
        self.skill_id = skill_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_skill_data()
        self.label = data.get('label','Неизвестный навык')
        self.characteristic = data.get('char', None)
        self.add_characteristic = data.get('add_char', None)
        self.capacity = data.get('capacity', None)
        self.add_capacity = data.get('add_capacity', None)
        self.description = data.get('desc', '')
        self.role = data.get('role','Другое')

    def fetch_skill_data(self):
        if self.data_manager.check('SKILL_INIT',f'id = "{self.skill_id}"'):
            return self.data_manager.select_dict('SKILL_INIT','*',f'id = "{self.skill_id}"')[0]
        else:
            return {}




@dataclass()
class CharacterCharacteristic:
    name: str
    lvl: int

    def get_character_data(self, character_id:int, data_manager:DataManager):
        data = data_manager.select_dict('CHARS_CHARS',filter=f'id = {character_id} AND char = "{self.name}"')[0]
        self.lvl = data.get('lvl', 0)

    def add_to_character(self, character_id:int, data_manager:DataManager):
        query = {'id': character_id,
                 'char': self.name,
                 'lvl': self.lvl}

        data_manager.insert('CHARS_CHARS',query)

    def update_for_character(self, character_id:int, data_manager:DataManager, *, lvl:int=0):
        self.get_character_data(character_id, data_manager)
        new_lvl = lvl + self.lvl

        query = {'lvl': new_lvl}
        data_manager.update('CHARS_CHARS',query,f'id = {character_id} AND char = "{self.name}"')

@dataclass()
class CharacterSkill:
    name: str
    lvl: int
    exp: float
    talant: float
    mastery: float

    def get_character_data(self, character_id:int, data_manager:DataManager):
        data = data_manager.select_dict('CHARS_SKILLS',filter=f'id = {character_id} AND skill_id = "{self.name}"')[0]
        self.lvl = data.get('lvl', 0)
        self.exp = data.get('exp', 0)
        self.talant = data.get('talant', 1)
        self.mastery = data.get('mastery', 1)

    def add_to_character(self, character_id:int, data_manager:DataManager):
        query = {'id': character_id,
                 'skill_id': self.name,
                 'lvl': self.lvl,
                 'exp': self.exp,
                 'talant': self.talant,
                 'master': self.mastery}

        data_manager.insert('CHARS_SKILLS', query)

    def update_for_character(self, character_id:int, data_manager:DataManager, **kwargs):
        self.get_character_data(character_id, data_manager)

        new_lvl = kwargs.get('lvl', 0) + self.lvl
        new_exp = kwargs.get('exp', 0) + self.exp
        new_talant = kwargs.get('talant',0) + self.talant
        new_mastery = kwargs.get('mastery', 0) + self.mastery

        query = {'lvl': new_lvl,
                 'exp': new_exp,
                 'talant': new_talant,
                 'master': new_mastery}

        data_manager.update('CHARS_SKILLS',query,f'id = {character_id} AND skill_id = "{self.name}"')

@dataclass()
class CharacterTrait:
    name: str


class CharacterAttributes:
    def __init__(self, character_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = character_id

        self.skills = self.skill_list()
        self.characteristics = self.characteristics_list()
        self.traits = self.traits_list()
        self.abilities = {}

    def check_progress(self):
        if not self.data_manager.check('CHARS_PROGRESS',filter=f'id = {self.id}'):
            return {}
        else:
            return self.data_manager.select_dict('CHARS_PROGRESS',filter=f'id = {self.id}')[0]

    def check_capacity(self, capacity:str):
        return Body(self.id).physical_stat(capacity)

    def check_pain(self):
        return Body(self.id).calculate_total_pain()

    def update_data(self):
        self.skills = self.skill_list()
        self.characteristics = self.characteristics_list()
        self.traits = self.traits_list()
        self.abilities = {}

    def fetch_skill_list(self) -> list[dict] | None:
        if self.data_manager.check('CHARS_SKILLS', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_SKILLS',filter=f'id = {self.id}')
        else:
            return None

    def fetch_chars_list(self) -> list[dict] | None:
        if self.data_manager.check('CHARS_CHARS', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_CHARS',filter=f'id = {self.id}')
        else:
            return None

    def fetch_traits(self) -> list[dict] | None:
        if self.data_manager.check('CHARS_TRAITS', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_TRAITS',filter=f'id = {self.id}')
        else:
            return None

    def get_skill_list(self) -> list[str] | None:
        c_skills = self.fetch_skill_list()
        if c_skills is None:
            return None

        c_list = [skill.get('skill_id') for skill in c_skills]
        return c_list

    def get_chars_list(self) -> list[str] | None:
        c_chars = self.fetch_chars_list()
        if c_chars is None:
            return None

        c_list = [char.get('char') for char in c_chars]
        return c_list

    def get_traits_list(self) -> list[str] | None:
        c_traits = self.fetch_traits()
        if c_traits is None:
            return None

        c_list = [trait.get('char') for trait in c_traits]
        return c_list

    def skill_list(self) -> dict[CharacterSkill] | None:
        c_skills = self.fetch_skill_list()
        if c_skills is None:
            return None

        total_skills = {}
        for skill in c_skills:
            total_skills[skill.get('skill_id')] = CharacterSkill(skill.get('skill_id'),
                                                                 skill.get('lvl'),
                                                                 skill.get('exp'),
                                                                 skill.get('talant'),
                                                                 skill.get('mastery'))

        return total_skills

    def characteristics_list(self) -> dict[CharacterCharacteristic] | None:
        c_chars = self.fetch_chars_list()
        if c_chars is None:
            return None

        total_chars = {}
        for char in c_chars:
            total_chars[char.get('char')] = CharacterCharacteristic(char.get('char'), char.get('lvl'))

        return total_chars

    def traits_list(self) -> dict[CharacterTrait] | None:
        c_traits = self.fetch_traits()
        if c_traits is None:
            return None

        total_traits = {}
        for trait in c_traits:
            total_traits[trait.get('trait')] = CharacterTrait(trait.get('trait'))

        return total_traits

    def check_skill(self, skill:str, all_pars=False):
        if skill not in self.skills:
            return 0
        else:
            if not all_pars:
                return self.skills[skill].lvl
            else:
                return self.skills[skill]

    def check_characteristic(self, characteristic:str):
        return self.characteristics[characteristic].lvl if characteristic in self.characteristics else 0

    def check_trait(self, trait:str):
        return self.traits[trait] is not None if trait in self.traits else False

    def get_skill_object(self, skill:str):
        return self.skills[skill] if self.check_skill(skill) else None

    def get_characteristic_object(self, characteristic:str):
        return self.characteristics[characteristic] if self.check_characteristic(characteristic) else None

    def get_trait_object(self, trait:str):
        return self.traits[trait] if self.check_trait(trait) else None

    def update_skill(self, skill:str, **kwargs):
        if skill in self.skills:
            c_skill: CharacterSkill = self.skills[skill]
            c_skill.update_for_character(self.id, self.data_manager,
                                         lvl=kwargs.get('lvl', 0),
                                         exp=kwargs.get('exp', 0),
                                         talant=kwargs.get('talant', 0),
                                         mastery=kwargs.get('mastery', 0))
        else:
            c_skill: CharacterSkill = CharacterSkill(skill, kwargs.get('lvl', 0), kwargs.get('exp', 0), kwargs.get('talant', 1), kwargs.get('mastery', 1))
            c_skill.add_to_character(self.id, self.data_manager)

    def update_characteristic(self, characteristic:str, **kwargs):
        if characteristic in self.characteristics:
            c_char:CharacterCharacteristic = self.characteristics[characteristic]
            c_char.update_for_character(self.id, self.data_manager, lvl=kwargs.get('lvl',0))
        else:
            c_char:CharacterCharacteristic = CharacterCharacteristic(characteristic, kwargs.get('lvl', 1))
            c_char.add_to_character(self.id, self.data_manager)

    def skill_progression(self, current_lvl:int):
        formula = round( 50**(1+current_lvl/100) + current_lvl * 50 )
        return formula

    def skill_progress_cost(self, current_lvl:int, exp:float):
        start_lvl = current_lvl
        exp_cost = 0
        lvl_plus = 0
        total_cost = 0

        while exp > exp_cost:
            n_cost = self.skill_progression(start_lvl + lvl_plus)
            exp_cost += n_cost
            if exp_cost <= exp:
                lvl_plus += 1
                total_cost += n_cost

        return start_lvl + lvl_plus, total_cost

    def upgrade_skill(self, skill:str, value:float, **kwargs):
        if skill in self.skills:
            c_skill:CharacterSkill = self.skills[skill]
            c_talant = c_skill.talant
        else:
            c_talant = 1

        total_exp = round(value) * c_talant * kwargs.get('crit_modifier', 1) + kwargs.get('extra', 0)
        total_exp = total_exp * kwargs.get('extra_modifier', 1)

        new_lvl, exp_cost = self.skill_progress_cost(c_skill.lvl, total_exp+c_skill.exp) if skill in self.skills else self.skill_progress_cost(0, total_exp)
        total_exp -= exp_cost

        if skill in self.skills:
            c_skill.update_for_character(self.id, self.data_manager, exp=round(total_exp, 2), lvl=new_lvl-c_skill.lvl)
        else:
            c_skill: CharacterSkill = CharacterSkill(skill, new_lvl, round(total_exp, 2), 1, 1)
            c_skill.add_to_character(self.id, self.data_manager)

    def upgrade_characteristic(self, characteristic:str, value:int, **kwargs):

        total_value = round(value * kwargs.get('modifier', 1) + kwargs.get('bonus', 0))

        if characteristic in self.characteristics:
            c_char: CharacterCharacteristic = self.characteristics[characteristic]
            c_char.update_for_character(self.id, self.data_manager, lvl=total_value)
        else:
            CharacterCharacteristic(characteristic, total_value).add_to_character(self.id, self.data_manager)

    def roll_skill(self, skill:str, **kwargs):
        if skill in self.skills:
            c_skill: CharacterSkill = self.skills[skill]
        else:
            c_skill: CharacterSkill = CharacterSkill(skill, 0, 0, 1, 1)
        skill_init = SkillInit(skill, data_manager=self.data_manager)

        c_roll = RollSkill(c_skill.lvl,
                           characteristic_value = self.check_characteristic(skill_init.characteristic) if skill_init.characteristic else None,
                           add_characteristic_value= self.check_characteristic(skill_init.add_characteristic) if skill_init.add_characteristic else None,
                           capacity_value = self.check_capacity(skill_init.capacity) if skill_init.capacity else None,
                           add_capacity_value= self.check_capacity(skill_init.add_capacity) if skill_init.add_capacity else None,
                           kwargs = kwargs,
                           pain=self.check_pain())

        if 'difficulty' in kwargs:
            c_result = c_roll.check_difficulty(kwargs.get('difficulty'))
            c_value = c_roll.dice-kwargs.get('difficulty') if c_result else 0
            crit_modifier = c_roll.check_critical_modifier()

            self.upgrade_skill(skill, c_value, crit_modifier=crit_modifier, kwargs=kwargs)
            return c_result, c_roll.roll_characteristic(c_value)

        else:
            return c_roll.dice

    def roll_characteristic(self, characteristic:str, **kwargs):
        if characteristic in self.characteristics:
            c_skill: CharacterCharacteristic = self.characteristics[characteristic]
        else:
            c_skill: CharacterCharacteristic = CharacterCharacteristic(characteristic, 0)

        c_roll = RollCharacteristic(c_skill.lvl,
                           kwargs = kwargs,
                           pain=self.check_pain())

        if 'difficulty' in kwargs:
            c_result = c_roll.check_difficulty(kwargs.get('difficulty'))
            c_value = kwargs.get('difficulty') if c_result else 0
            c_is_crit = c_roll.check_crit()
            if c_is_crit:
                self.upgrade_characteristic(characteristic, random.randint(0,1), kwargs=kwargs)

            return c_result, c_roll.roll_characteristic(c_value)

        else:
            return c_roll.dice

    def roll_capacity(self, capacity:str, **kwargs):
        if self.check_capacity(capacity):
            c_lvl = self.check_capacity(capacity)
        else:
            c_lvl = 0

        c_roll = RollCapacity(c_lvl,
                           kwargs = kwargs,
                           pain=self.check_pain())

        if 'difficulty' in kwargs:
            c_result = c_roll.check_difficulty(kwargs.get('difficulty'))
            c_value = kwargs.get('difficulty') if c_result else 0

            return c_result, c_roll.roll_characteristic(c_value)

        else:
            return c_roll.dice