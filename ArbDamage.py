import random
from ArbDatabase import *
from dataclasses import dataclass

class Injury:
    def __init__(self, id: str, **kwargs):
        self.ID = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_data()

        self.Name = data.get('name',None)
        self.InnerName = data.get('inner_label', None)
        self.ScarName = data.get('label_of_scar', None)
        self.ScarInnerName = data.get('label_of_innerscar', None)
        self.PainFactor = data.get('pain_factor', 0)
        self.ScarPain = data.get('scar_pain_factor', 0)
        self.HealingSpeed = data.get('healing_speed', 0)
        self.InfectionChance = data.get('infect_chance', 0)
        self.ScarFactor = data.get('scar_chance', 0)
        self.Bleed = data.get('bleed',0)

    def fetch_data(self) -> dict:
        if self.data_manager.check('INJURY_INIT', filter=f'id = "{self.ID}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('INJURY_INIT', filter=f'id = "{self.ID}"')[0]

    def __repr__(self):
        return f'Injury.{self.ID}'


class DamageType:
    def __init__(self, damage_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager',DataManager())
        self.damage_id = damage_id
        self._load_damage_info()

    def _load_damage_info(self):
        filter = f"id = '{self.damage_id}'"
        damage_info = self.data_manager.select_dict('DAMAGE_TYPE', columns='*', filter=filter)[0]
        if damage_info:
            self.label = damage_info['label']
            self.destruction_label = damage_info['destruction_label']
            self.min_overkill = damage_info['min_overkill']
            self.max_overkill = damage_info['max_overkill']
            self.protection_type = damage_info['protection_type']
            self.protection_factor = damage_info['protection_factor']
            self.desc = damage_info['desc']
            self.effect = damage_info['effect']
            self.effect_time = damage_info['effect_time']
        else:
            raise ValueError(f"DamageType with ID '{self.damage_id}' not found in the database.")

    def get_protection_type(self):
        return self.protection_type

    def __desc__(self):
        return self.desc

    def get_possible_injuries(self):
        injuries = []
        if self.data_manager.check('INJURY_INIT',f'source = "{self.damage_id}"'):
            filter = f"source = '{self.damage_id}'"
            injury_names = self.data_manager.select('INJURY_INIT', columns='id', filter=filter)
            injuries = [Injury(name[0]) for name in injury_names]
        return injuries

    def apply_effect(self, char_id:int):
        return f"Applying {self.effect} to {char_id} effect for {self.effect_time} AP"

    def __repr__(self):
        return f'DamageType.{self.damage_id}'

    def __str__(self):
        return f'Тип урона: {self.label}'


@dataclass()
class Penetration:
    name: str
    value: float
    blocked_type:str

    def __add__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value + other
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        elif self.name == other.name:
            new_value = self.value + other.value
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        else:
            return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value - other
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        elif self.name == other.name:
            new_value = self.value - other.value
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        else:
            return NotImplemented

    def __rsub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value * other
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        elif self.name == other.name:
            new_value = self.value * (other.value/100)
            return Penetration(name=self.name, value=new_value, blocked_type=self.blocked_type)
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.value == other
        elif isinstance(other, Penetration):
            return self.name == other.name and self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.value < other
        elif isinstance(other, Penetration):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.value <= other
        elif isinstance(other, Penetration):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.value > other
        elif isinstance(other, Penetration):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.value >= other
        elif isinstance(other, Penetration):
            return self.value >= other.value
        return NotImplemented


class EffectType:
    def __init__(self, id: str):
        self.data_manager = DataManager()
        self.ID = id
        self.Name = None
        self.AccuracyFactor = None
        self.CoverFactor = None
        self.DamageType = None
        self.Damage = None
        self.Penetration = None

        data = self.fetch_data()

        if data:
            self.Name = data.get('name','')
            self.AccuracyFactor = data.get('accuracy', 0)
            self.CoverFactor = data.get('cover', 0)
            self.DamageType = data.get('damage_type', '')
            self.Damage = data.get('damage', 0)

    def fetch_data(self) -> dict:
        columns = ['accuracy', 'cover', 'damage_type', 'damage','name']
        data = {}

        for col in columns:
            data[col] = self.data_manager.selectOne('EFFECT_INIT', columns=col, filter=f'id = "{self.ID}"')[0]

        return data

    def __repr__(self):
        return f'Effect.{self.ID}'


class Effect(EffectType):
    def __init__(self, effect_id:str, char_id:int):
        super().__init__(effect_id)
        self.Character = char_id
        self.AP = self.data_manager.selectOne('CHAR_EFFECTS','ap',f'id = {self.Character} AND effect = "{self.ID}"')[0]

    def apply_damage(self, part_id:str, char_id:int):
        c_damage = Damage(self.Damage, self.DamageType, root=f'{self.Name}')
        c_damage.add_to_character(part_id, char_id, effect=False)

    def update(self, ap:int):
        self.AP -= ap

    def __repr__(self):
        return f'Effect.{self.ID}'


class Damage:
    def __init__(self, damage:int, damage_type:str, *, root:str=None, **kwargs):
        self.Damage = damage
        self.Type = DamageType(damage_type, data_manager=kwargs.get('data_manager', DataManager()))
        self.data_manager = kwargs.get('data_manager',DataManager())

        if not root:
            self.Root = 'Неизвестно'
        else:
            self.Root = root

    def __repr__(self):
        return f'DamageType.{self.Type.damage_id}({self.Damage})'

    def __str__(self):
        return self.__repr__()

    def __add__(self, other):
        if not isinstance(other, (int, float, Damage)):
            raise ArithmeticError("Правый операнд должен быть типом int или объектом Damage")

        if isinstance(other, (int, float)):
            sc = other
        elif isinstance(other, Damage) and other.Type == self.Type:
            sc = other.Damage
        else:
            raise ArithmeticError("Объект Damage имеет другой тип урона")
        return Damage(self.Damage + sc, self.Type.damage_id, root=self.Root)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            new_value = int(self.Damage * other)
            return Damage(new_value, self.Type.damage_id, root=self.Root)
        elif self.Type == other.name:
            new_value = int(self.Damage * (other.value/100))
            return Damage(new_value, self.Type.damage_id, root=self.Root)
        else:
            return NotImplemented

    def types(self) -> Injury:
        return random.choice(self.Type.get_possible_injuries())

    def add_to_character(self, part_id:str, char_id:int, *, effect:bool=False) -> None:
        db = self.data_manager

        if self.Damage <= 0:
            return None
        else:
            if not db.check('CHARS_INJURY',f'id = {char_id}'):
                c_id = 0
            else:
                c_id = db.maxValue('CHARS_INJURY','id_inj',f'id = {char_id}') + 1

            c_type = self.types()
            bleed_chance = c_type.Bleed * self.Damage
            c_roll = random.randint(0,100)

            if c_roll <= bleed_chance:
                c_bleed = bleed_chance
            else:
                c_bleed = 0

            db.insert('CHARS_INJURY',{'id': char_id,
                                      'id_inj': c_id,
                                      'place': part_id,
                                      'type': c_type.ID,
                                      'root': self.Root,
                                      'damage': self.Damage,
                                      'bleed': c_bleed,
                                      'heal_efficiency':0,
                                      'is_scar': 0})
            if not effect:
                pass
            else:
                self.Type.apply_effect(char_id)

            db.commit_transaction()


