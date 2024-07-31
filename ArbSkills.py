import pprint
import random

from ArbDatabase import DataManager, DataModel
from ArbHealth import Body


class SkillInit(DataModel):
    def __init__(self, id:str, **kwargs):
        self.skill_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('SKILL_INIT', f'id = "{self.skill_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный навык')
        self.capacity = self.get('capacity', None)
        self.add_capacity = self.get('add_capacity', None)
        self.skill_role = self.get('role', 'Разное')
        self.desc = self.get('desc', '')

    def get_character_skill(self, character_id:int):
        return Skill(character_id, self.skill_id, data_manager=self.data_manager)

    def check_character_skill(self, character_id:int, difficulty:int = None):
        skill = self.get_character_skill(character_id)
        return skill.skill_check(difficulty)


class Skill(SkillInit, DataModel):
    def __init__(self, character_id:int, skill_id:str, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        SkillInit.__init__(self, skill_id, data_manager=self.data_manager)
        DataModel.__init__(self, 'CHARS_SKILLS', f'id = {self.character_id} and skill_id = "{skill_id}"', data_manager=self.data_manager)

        self.lvl = self.get('lvl', 0) if self.get('lvl', 0) is not None else 0
        self.talant = self.get('talant', 1) if self.get('talant', 0) is not None else 1
        self.mastery = self.get('master', 1) if self.get('master', 0) is not None else 1
        self.exp = self.get('exp', 0) if self.get('exp', 0) is not None else 0

    def get_capacities(self):
        capacities = Body(self.character_id, data_manager=self.data_manager).calculate_capacities()

        capacity = capacities.get(self.capacity, None)
        add_capacity = capacities.get(self.add_capacity, None)

        return capacity, add_capacity


    def change_lvl(self, lvl:int):
        query = {'lvl': self.lvl + lvl}
        self.update_record(query)
        self.lvl += lvl

    def set_talant(self, talant:float):
        self.talant = talant
        query = {'talant': self.talant}
        self.update_record(query)

    def set_mastery(self, mastery:float):
        self.mastery = mastery
        query = {'mastery': self.mastery}
        self.update_record(query)

    def set_exp(self, exp:float):
        self.exp = exp
        query = {'exp': self.exp}
        self.update_record(query)

    def add_exp(self, exp:float):
        self.exp += exp
        query = {'exp': self.exp}
        self.update_record(query)

    def add_talant(self, talant:float):
        self.talant += talant
        query = {'talant': self.talant}
        self.update_record(query)

    def add_mastery(self, mastery:float):
        self.mastery += mastery
        query = {'mastery': self.mastery}
        self.update_record(query)

    def check_skill_record(self):
        if self.data_manager.check('CHARS_SKILLS', f'id = {self.character_id} and skill_id = "{self.skill_id}"'):
            return True
        else:
            return False

    def insert_skill(self):
        query = {'id': self.character_id,
                  'skill_id': self.skill_id,
                   'lvl': self.lvl,
                   'talant': self.talant,
                  'master': self.mastery,
                   'exp': self.exp}

        self.data_manager.insert('CHARS_SKILLS', query)

    def skill_progression(self, current_lvl: int):
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

        if start_lvl + lvl_plus > int(self.mastery * 100):
            return self.lvl, 0

        return start_lvl + lvl_plus, total_cost

    def upgrade_skill(self, value:float, **kwargs):
        c_talant = self.talant

        total_exp = round(value) * c_talant * kwargs.get('crit_modifier', 1) + kwargs.get('extra', 0)
        total_exp = total_exp * kwargs.get('extra_modifier', 1)

        new_lvl, exp_cost = self.skill_progress_cost(self.lvl, total_exp + self.exp)
        total_exp -= exp_cost

        if not self.check_skill_record():
            self.insert_skill()

        if self.lvl < 100 * self.mastery:
            self.add_exp(round(total_exp, 2))
            self.change_lvl(new_lvl - self.lvl)

    def skill_check(self, difficulty: int = None):
        from ArbRoll import RollCheck

        capacity, add_capacity = self.get_capacities()
        modifiers = (capacity / 100 if capacity is not None else 1, add_capacity / 100 if add_capacity is not None else 1)

        roll = RollCheck(50 + self.lvl, modifiers)

        gained_exp = abs(roll.result - difficulty) * 10 if difficulty else 0.75 * roll.result
        crit_modifier = roll.crit_modifier
        gained_exp *= crit_modifier

        self.upgrade_skill(gained_exp)

        if difficulty is not None:
            return roll.result >= difficulty, roll
        else:
            return roll.result, roll