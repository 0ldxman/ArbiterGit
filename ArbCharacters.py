import datetime

from ArbDatabase import DataManager, DataModel, DataDict
from ArbHealth import Body
from ArbRoll import Roll
from ArbSkills import SkillInit
from ArbUtils.ArbTimedate import TimeManager
from ArbRaces import Race


class CharacterProgress(DataModel):
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'CHARS_PROGRESS', f'id = {self.id}', data_manager=self.data_manager)

        self.skills_points = self.get('skills', 0) if self.get('skills', None) is not None else 0
        self.skills_mods = self.get('skills_mods', 0) if self.get('skills_mods', None) is not None else 0

        self.lvl = self.get('lvl', 0) if self.get('lvl', None) is not None else 0
        self.skills_exp = self.get('exp', 0) if self.get('exp', None) is not None else 0


    def insert_progress_data(self, skills: int = None, skills_mods:float=None, lvl: int = None, exp: int = None):
        prompt = {
            'id': self.id,
            'skills': skills,
            'skills_mods': skills_mods,
            'lvl': lvl if lvl is not None else 0,
            'exp': exp
        }

        self.data_manager.insert('CHARS_PROGRESS', prompt)

    def update_progress_data(self, skills: int = 0, skills_mods:float=0, lvl: int = 0, exp: int = 0):
        if not self.data_manager.check('CHARS_PROGRESS', filter=f'id = {self.id}'):
            self.insert_progress_data(0, 0, 0, 0)

        prompt = {
            'skills': self.skills_points + skills,
            'skills_mods': self.skills_mods + skills_mods,
            'lvl': self.lvl + lvl,
            'exp': self.skills_exp + exp
        }

        self.data_manager.update('CHARS_PROGRESS', prompt, filter=f'id = {self.id}')


class Character(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('CHARS_INIT', f'id = {self.id}', data_manager=self.data_manager)

        self.custom_id = self.get('custom_id', None)
        self.owner = self.get('owner', None)

        self.name = self.get('name', 'Неизвестный')
        self.callsign = self.get('callsign', '')
        self.age = self.get('age', 30)
        self.race = Race(self.get('race', 'Human'))
        self.sex = self.get('sex', 'Неизвестный пол')

        self.org = self.get('org', None)
        self.org_lvl = self.get('org_lvl', 0)

        self.frac = self.get('frac', None)
        self.frac_lvl = self.get('frac_lvl', 0)

        self.picture = self.get('avatar', '') if self.get('avatar') else ''
        self.update = self.get('updated', None)
        self.server = self.get('server', None)

    def set_last_update_date(self, date:str):
        self.update = date
        self.data_manager.update('CHARS_INIT', {"updated": self.update}, f'id = {self.id}')

    def add_adventure_points(self, adp: int):
        current_adp = self.data_manager.select_dict('CHARS_LOC', filter=f'id = {self.id}')[0].get('move_points', 0)
        if current_adp is None:
            current_adp = 0

        if self.data_manager.check('CHARS_LOC', f'id = {self.id}'):
            self.data_manager.update('CHARS_LOC', {'move_points': current_adp+adp}, filter=f'id = {self.id}')
        else:
            query = {
                'id': self.id,
                'loc_id': None,
                'move_points': current_adp + adp,
                'entered': 0
            }
            self.data_manager.insert('CHARS_LOC', query)

    def get_last_update_difference(self):
        time_manager = TimeManager()
        now = time_manager.today().strftime('%Y-%m-%d')
        last_update = self.update
        time_passed = time_manager.date_difference(last_update, now)
        return time_passed

    def get_next_day_after_update(self):
        time_manager = TimeManager()
        last_update = time_manager.get_date(self.update)
        next_day = time_manager.date_after(days=1, date=last_update.strftime('%Y-%m-%d'))
        return next_day

    def skip_cycle(self):
        from ArbHealth import Body

        Body(self.id, data_manager=self.data_manager).rest()
        self.add_adventure_points(5)

        next_day = self.get_next_day_after_update().strftime('%Y-%m-%d')
        self.set_last_update_date(next_day)

    def change_cycle(self, cycles:int):
        """Сменяет циклы в количестве cycles:int"""

        max_cycles = self.get_last_update_difference()
        if cycles > max_cycles:
            cycles = max_cycles

        for _ in range(cycles):
            self.skip_cycle()

    def text_card(self):
        from ArbOrgs import Organization

        age_text = f'{self.age}'
        age_label = 'год'
        if age_text[-1] in ['2', '3', '4']:
            age_label = 'года'
        elif age_text[-1] in ['5', '6', '7', '8', '9', '0']:
            age_label = 'лет'

        total_text = f'''
***Имя Фамилия:*** *{self.name} {f'"{self.callsign}"' if self.callsign else ''}*
***Раса:*** *{self.race.label}*
***Пол:*** *{self.sex}*
***Возраст:*** *{self.age} {age_label}*

'''
        if self.org:
            total_text += f'***Организация:*** *{Organization(self.org, data_manager=self.data_manager).label}*\n'
        if self.frac:
            total_text += f'***Фракция:*** {self.frac}\n'

        return total_text

    def text_combat_card(self):
        from ArbBattle import Actor, Layer, GameObject

        actor = Actor(self.id, data_manager=self.data_manager)
        combat_info = DataDict('CHARS_COMBAT', f'id = {self.id}', data_manager=self.data_manager)
        total_text = f'''
<:action_points:1251239084144197696> **Очки Действия:** {combat_info.get('ap', 0)} ОД. {f"({combat_info.get('ap_bonus', 0):+} ОД.)" if combat_info.get('ap_bonus') else ''}
<:target:1251276620384305244> **Текущая цель:** {combat_info.get('target') if combat_info.get('target') is not None else 'Отсутствует'} 
:crossed_swords: **Ближний бой с целью:** {combat_info.get('melee_target') if combat_info.get('melee_target') is not None else 'Отсутствует'}
<:coverage:1264244009149272115> **Уровень маскировки:** {actor.disguise():0.2f}%

-# **Текущий слой:**
- {Layer(actor.layer_id, actor.battle_id, data_manager=self.data_manager).label} (``{actor.layer_id}``)
-# **Текущее укрытие:**
- {GameObject(actor.object_id, data_manager=self.data_manager).object_type.label + f' (``{actor.object_id}``)' if actor.object_id else 'Отсутствует'}
'''

        return total_text