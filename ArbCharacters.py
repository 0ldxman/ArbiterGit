from ArbDatabase import DataManager, DataModel, DataDict
from ArbHealth import Body
from ArbRoll import Roll
from ArbSkills import SkillInit
from ArbUtils.ArbTimedate import TimeManager
from ArbRaces import Race


class CharacterProgress:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        data = self.fetch_progress_data()
        self.characteristic_points = data.get('chars', 0) if data.get('chars', None) is not None else 0
        self.skills_points = data.get('skills', 0) if data.get('skills', None) is not None else 0
        self.traits_points = data.get('traits', 0) if data.get('traits', None) is not None else 0
        self.lvl = data.get('lvl', 0) if data.get('lvl', None) is not None else 0
        self.skills_exp = data.get('exp', 0) if data.get('exp', None) is not None else 0

    def fetch_progress_data(self):
        if self.data_manager.check('CHARS_PROGRESS', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_PROGRESS', filter=f'id = {self.id}')[0]
        else:
            return {}

    def insert_progress_data(self, chars: int = None, skills: int = None, traits: int = None, lvl: int = None, exp: int = None):
        prompt = {
            'id': self.id,
            'chars': chars,
            'skills': skills,
            'traits': traits,
            'lvl': lvl if lvl is not None else 0,
            'exp': exp
        }

        self.data_manager.insert('CHARS_PROGRESS', prompt)

    def update_progress_data(self, chars: int = None, skills: int = None, traits: int = None, lvl: int = None, exp: int = None):
        prompt = {
            'chars': self.characteristic_points + chars,
            'skills': self.skills_points + skills,
            'traits': self.traits_points + traits,
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
        self.update = self.get('update', None)
        self.server = self.get('server', None)

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