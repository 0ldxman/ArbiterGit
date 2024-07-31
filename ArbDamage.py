from ArbDatabase import DataManager, DataModel
import random

class DamageType(DataModel):
    def __init__(self, damage_id: str, **kwargs):
        self.damage_type_id = damage_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('DAMAGE_TYPE', f'id = "{self.damage_type_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный тип урона')
        self.destruction_label = self.get('destruction_label', None)

        self.protection_type = self.get('protection_type', None)
        self.protection_factor = self.get('protection_factor', 0)

        self.min_overkill = self.get('min_overkill', 0)
        self.max_overkill = self.get('max_overkill', 0)

        self.desc = self.get('desc', None)
        self.effect = EffectType(self.get('effect'), data_manager=self.data_manager) if self.get('effect') else None
        self.effect_time = self.get('effect_chance', 0)

    def possible_injuries(self):
        if not self.data_manager.check('INJURY_INIT', f'damage_type = "{self.damage_type_id}"'):
            return ['Damage']

        possible_injuries = [injury.get('id') for injury in self.data_manager.select_dict('INJURY_INIT', filter=f'damage_type = "{self.damage_type_id}"')]

        return possible_injuries

    def random_injury(self):
        possible_injuries = self.possible_injuries()
        return random.choice(possible_injuries)

    def __repr__(self):
        return f'DamageType.{self.damage_type_id}'

    def __str__(self):
        return f'Тип урона: {self.label}'


class EffectType(DataModel):
    def __init__(self, effect_id: str, **kwargs):
        self.effect_type_id = effect_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('EFFECT_INIT', f'id = "{self.effect_type_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный эффект')
        self.accuracy_penalty = self.get('accuracy', 0)
        self.cover_penalty = self.get('cover', 0)

        self.damage = self.get('damage', 0)
        self.damage_type = self.get('damage_type', None)

    def generate_damage(self):
        return Damage(self.damage, self.damage_type, self.label, data_manager=self.data_manager)


class Damage(DamageType):
    def __init__(self, damage:int, damage_type:str, penetration:int, blocked_type:str=None, root:str=None, **kwargs):
        self.damage = damage
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(damage_type, data_manager=self.data_manager)

        self.penetration = penetration * self.protection_factor
        self.blocked_type = blocked_type if blocked_type else 'Hit'
        self.root = root if root else 'Неизвестно'

    def __repr__(self):
        return f'DamageType.{self.damage_type_id}({self.damage})'

    def __str__(self):
        return f'({self.root}) {self.damage} урона {self.label}'

    def reduce_penetration(self, armor: int):
        self.penetration -= armor
        if self.penetration < 0:
            self.penetration = 0
        return self.penetration

    def convert_to_blocked_type(self, root_penetration: float = None):
        if not root_penetration:
            damage = self.damage
        else:
            damage = int( (self.penetration / root_penetration) * self.damage )

        return Damage(damage, self.blocked_type, self.penetration, self.blocked_type, self.root, data_manager=self.data_manager)


class ProtectionType(DataModel):
    def __init__(self, protection_type_id: str, **kwargs):
        self.protection_type_id = protection_type_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('PROTECTION_TYPE', f'id = "{self.protection_type_id}"', data_manager=self.data_manager)
        self.label = self.get('label', 'Неизвестный тип защиты')
        self.protection_factor = self.get('desc', '')