from ArbDatabase import DataManager, DataModel, DataObject, EID, DEFAULT_MANAGER
import random


class DamageType(DataObject):
    def __init__(self, damage_id: str, **kwargs):
        self.damage_type_id = damage_id
        super().__init__('DAMAGE_TYPE', EID(id=self.damage_type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный тип урона')
        self._destruction_label = self.field('destruction_label', None)

        self._protection_type = self.field('protection_type', None)
        self._protection_factor = self.field('protection_factor', 0)

        self._min_overkill = self.field('min_overkill', 0)
        self._max_overkill = self.field('max_overkill', 0)

        self._desc = self.field('desc', None)
        self._effect = self.field('effect', None)
        self._effect_time = self.field('effect_chance', 0)

    @property
    def label(self):
        return self._label.load(self.data_manager)

    @property
    def destruction_label(self):
        return self._destruction_label.load(self.data_manager)

    @property
    def protection_type(self):
        return self._protection_type.load(self.data_manager)

    @property
    def protection_factor(self):
        return self._protection_factor.load(self.data_manager)

    @property
    def min_overkill(self):
        return self._min_overkill.load(self.data_manager)

    @property
    def max_overkill(self):
        return self._max_overkill.load(self.data_manager)

    @property
    def desc(self):
        return self._desc.load(self.data_manager)

    @property
    def effect(self):
        effect = self._effect.load(self.data_manager)
        if not effect:
            return None
        return EffectType(effect, data_manager=self.data_manager)

    @property
    def effect_time(self):
        return self._effect_time.load(self.data_manager)

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


class EffectType(DataObject):
    def __init__(self, effect_id: str, **kwargs):
        self.effect_type_id = effect_id

        super(EffectType, self).__init__('EFFECT_INIT', EID(id=self.effect_type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный эффект')
        self._accuracy_penalty = self.field('accuracy', 0)
        self._cover_penalty = self.field('cover', 0)
        self._damage = self.field('damage', 0)
        self._damage_type = self.field('damage_type', None)

    @property
    def label(self):
        return self._label.load(self.data_manager)

    @property
    def accuracy_penalty(self):
        return self._accuracy_penalty.load(self.data_manager)

    @property
    def cover_penalty(self):
        return self._cover_penalty.load(self.data_manager)

    @property
    def damage(self):
        return self._damage.load(self.data_manager)

    @property
    def damage_type(self):
        return self._damage_type.load(self.data_manager)

    def generate_damage(self):
        return Damage(self.damage, self.damage_type, self.label, data_manager=self.data_manager) if self.damage and self.damage_type else None


class Damage(DamageType):
    def __init__(self, damage:int, damage_type:str, penetration:int, blocked_type:str=None, root:str=None, **kwargs):
        self.damage = damage
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)
        super().__init__(damage_type, data_manager=self.data_manager)

        self._penetration = penetration * self.protection_factor
        self._blocked_type = blocked_type if blocked_type else 'Hit'
        self._root = root if root else 'Неизвестно'

    @property
    def penetration(self):
        return self._penetration if self._penetration >= 0 else 0

    @penetration.setter
    def penetration(self, value: int):
        self._penetration = value if value >= 0 else 0

    @property
    def blocked_type(self):
        return self._blocked_type

    @property
    def root(self):
        return self._root

    def __repr__(self):
        return f'DamageType.{self.damage_type_id}({self.damage})'

    def __str__(self):
        return f'({self.root}) {self.damage} урона {self.label}'

    def reduce_penetration(self, armor: int):
        new_penetration = self.penetration - armor
        self.penetration = new_penetration
        return self.penetration

    def convert_to_blocked_type(self, root_penetration: float = None):
        if not root_penetration:
            damage = self.damage
        else:
            damage = int( (self.penetration / root_penetration) * self.damage )

        return Damage(damage, self.blocked_type, self.penetration, self.blocked_type, self.root, data_manager=self.data_manager)


class ProtectionType(DataObject):
    def __init__(self, protection_type_id: str, **kwargs):
        self.protection_type_id = protection_type_id
        super(ProtectionType, self).__init__('PROTECTION_TYPE', EID(id=self.protection_type_id), kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный тип защиты')
        self._protection_factor = self.field('protection_factor', 0)

    @property
    def label(self):
        return self._label.load(self.data_manager)

    @property
    def protection_factor(self):
        return self._protection_factor.load(self.data_manager)