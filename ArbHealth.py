import pprint

from ArbDatabase import DataManager, DataModel, DataObject, EID, DEFAULT_MANAGER
from ArbRaces import Race

import random
from dataclasses import dataclass
from ArbDamage import Damage, DamageType


class CapacityType(DataObject):
    def __init__(self, capacity_id: str, **kwargs):
        self.capacity_id = capacity_id

        super(CapacityType, self).__init__('CAPACITY_INIT', EID(id=self.capacity_id), kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестная физиология')
        self._description = self.field('description', 'Нет описания способности')
        self._mortality = self.field('mortality', 0)
        self._critical_value = self.field('critical_value', 0)
        self._critical_effect = self.field('critical_effect', None)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def description(self) -> str:
        return self._description.load(self.data_manager)

    @property
    def mortality(self) -> float:
        return self._mortality.load(self.data_manager)

    @property
    def critical_value(self) -> int:
        return self._critical_value.load(self.data_manager)

    @property
    def critical_effect(self) -> str:
        return self._critical_effect.load(self.data_manager)


    def get_affected_capacities(self, capacity_value: float):
        if not self.data_manager.check('CAPACITIES_AFFECTS', f'capacity = "{self.capacity_id}"'):
            return {}

        affects = self.data_manager.select_dict('CAPACITIES_AFFECTS', filter=f'capacity = "{self.capacity_id}"')
        diff = capacity_value - 100

        affected_capacities = {
            affect['affect']: max(min(diff * affect['weight'], affect['max']), -affect['max'])
            for affect in affects
        }

        return affected_capacities

    def __repr__(self):
        return f'Capacity.{self.capacity_id}'


class InjuryType(DataObject):
    def __init__(self, injury_id: str, **kwargs):
        self.injury_type_id = injury_id

        super(InjuryType, self).__init__('INJURY_INIT', EID(id=self.injury_type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._damage_type = self.field('damage_type', None)
        self._label = self.field('label', 'Неизвестная рана')
        self._pain_per_severity = self.field('pain_per_severity', 0)
        self._scar_pain_per_severity = self.field('scar_pain_factor', 0)
        self._bleeding = self.field('bleeding', 0)
        self._treatment = self.field('treatment_per_cycle', 0)
        self._infection_chance = self.field('infection_chance', 0)
        self._scar_chance = self.field('scar_chance', 0)
        self._scar_label = self.field('scar_label', 'Неизвестный шрам')

    @property
    def damage_type(self) -> str:
        return self._damage_type.load(self.data_manager)

    @property
    def damage_type_id(self) -> str:
        return self.damage_type

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def pain_per_severity(self) -> int:
        return self._pain_per_severity.load(self.data_manager)

    @property
    def scar_pain_per_severity(self) -> int:
        return self._scar_pain_per_severity.load(self.data_manager)

    @property
    def bleeding(self) -> int:
        return self._bleeding.load(self.data_manager)

    @property
    def treatment(self) -> int:
        return self._treatment.load(self.data_manager)

    @property
    def infection_chance(self) -> float:
        return self._infection_chance.load(self.data_manager)

    @property
    def scar_chance(self) -> float:
        return self._scar_chance.load(self.data_manager)

    @property
    def scar_label(self) -> str:
        return self._scar_label.load(self.data_manager)


    def destroyed_label(self):
        if self.damage_type:
            return f'{DamageType(self.damage_type, data_manager=self.data_manager).destruction_label}'
        else:
            return f'Уничтожено'

    def __repr__(self):
        return f'Injury.{self.injury_type_id}'


class Injury(DataObject):
    def __init__(self, injury_id: int, **kwargs):
        self.injury_id = injury_id

        DataObject.__init__(self, 'CHARS_INJURY', EID(id_inj=self.injury_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._character_id = self.field('id', None)
        self._place = self.field('place', None)
        self._root = self.field('root', 'Неизвестно')
        self._damage = self.field('damage', 0)
        self._healing_efficiency = self.field('heal_efficiency', 0)
        self._is_scar = self.field('is_scar', 0)
        self._injury_type = self.field('type', None)

    @property
    def character_id(self) -> int:
        return self._character_id.load(self.data_manager)

    @property
    def character(self):
        from ArbCharacters import Character
        character_id = self.character_id
        if character_id is None:
            return None

        return Character(character_id, data_manager=self.data_manager)

    @property
    def place(self) -> str:
        return self._place.load(self.data_manager)

    @property
    def root(self) -> str:
        return self._root.load(self.data_manager)

    @property
    def damage(self) -> int:
        return self._damage.load(self.data_manager)

    @damage.setter
    def damage(self, value: int):
        self._damage.save(self.data_manager, value)

    @property
    def healing_efficiency(self) -> int:
        return self._healing_efficiency.load(self.data_manager)

    @healing_efficiency.setter
    def healing_efficiency(self, value: int):
        self._healing_efficiency.save(self.data_manager, value)

    @property
    def is_scar(self) -> bool:
        return self._is_scar.load(self.data_manager) == 1

    @is_scar.setter
    def is_scar(self, value: bool):
        self._is_scar.save(self.data_manager, int(value))

    @property
    def injury_type(self) -> InjuryType | None:
        injury_type = self._injury_type.load(self.data_manager)
        if not injury_type:
            return None

        return InjuryType(injury_type, data_manager=self.data_manager)

    @property
    def body_element(self) -> 'BodyElement':
        place = self.place
        if not place:
            return None
        return BodyElement(self.character_id, place, data_manager=self.data_manager)


    @classmethod
    def create_injury(cls, character_id:int, injury_type:str, place:str, damage:int, root:str=None, heal_efficiency:int=0, is_scar:bool=False):
        db = DEFAULT_MANAGER
        id_inj = db.maxValue('CHARS_INJURY', 'id_inj') + 1

        query = {
            'id': character_id,
            'id_inj': id_inj,
            'place': place,
            'type': injury_type,
            'damage': damage,
            'root': root,
            'heal_efficiency': heal_efficiency,
            'is_scar': int(is_scar)
        }

        db.insert('CHARS_INJURY', query)
        return cls(id_inj, character_id=character_id, data_manager=db)

    @classmethod
    def get_character_injuries(cls, character_id: int, data_manager: DataManager = DEFAULT_MANAGER, place: str = None) -> dict[str, list['Injury']]:
        db = data_manager

        if place is not None:
            respond = [(Injury(inj_id.get('id_inj'), data_manager=db), inj_id.get('place'))
                       for inj_id in
                       db.select_dict('CHARS_INJURY', filter=f'id = {character_id} AND place = "{place}"')]
        else:
            respond = [(Injury(inj_id.get('id_inj'), data_manager=db), inj_id.get('place'))
                       for inj_id in db.select_dict('CHARS_INJURY', filter=f'id = {character_id}')]

        total_dict = {}
        for injury, place in respond:
            if place not in total_dict:
                total_dict[place] = []
            total_dict[place].append(injury)

        return total_dict

    def calculate_pain(self):
        return self.damage * self.injury_type.pain_per_severity

    def get_body_element(self):
        if not self.place:
            return None
        else:
            return BodyElement(self.character_id, self.place, data_manager=self.data_manager)

    def set_healing(self, value: float):
        self.healing_efficiency = value

    def change_healing(self, value: float):
        new_healing = self.healing_efficiency + value
        self.set_healing(new_healing)

    def set_damage(self, value: float):
        self.damage = value

    def change_damage(self, value: float):
        new_damage = self.damage + value
        self.set_damage(new_damage)

    def get_healing_bonus(self):
        healing_bonus = 0.5 + self.healing_efficiency * 0.01
        return healing_bonus

    def roll_infection(self):
        if self.is_scar:
            return

        infection_chance = self.injury_type.infection_chance
        healing = 1.5 - self.get_healing_bonus()

        if random.randint(1, 100) <= int(infection_chance * healing):
            if not self.data_manager.check('CHARS_DISEASE', filter=f'id = {self.character_id} AND place = "{self.place}" AND type = "Infection"'):
                Disease.create_character_disease(self.character_id, 'Infection', data_manager=self.data_manager, place=self.place)

    def roll_scare(self):
        if random.randint(1, 100) <= int(self.injury_type.scar_chance):
            self.is_scar = True

    def update(self, filtration:int=100):
        filt_bonus = filtration / 100

        damage_recovery_speed = self.injury_type.treatment * self.get_healing_bonus() * filt_bonus

        self.roll_scare()
        self.roll_infection()

        self.change_damage(-1 * damage_recovery_speed)

        if self.damage <= 0:
            self.delete_record()

    def __repr__(self):
        return f'Injury.{self.injury_id} ({self.injury_type.injury_type_id})'

    def __str__(self):
        emoji = ''
        if self.injury_type.bleeding:
            emoji = ' <:bleed:1249850720065425480>'

        if self.healing_efficiency > 0:
            emoji = ' <:healed:1249753146859847760>'

        label = self.injury_type.label if not self.is_scar else self.injury_type.scar_label

        return f'{label} ({self.root}){emoji}'

    @staticmethod
    def delete_all_character_injuries(character_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_INJURY', f'id = {character_id}')

    @staticmethod
    def delete_injury(injury_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_INJURY', f'id_inj = {injury_id}')

    @staticmethod
    def delete_injuries_in_place(character_id:int, place_id:str):
        db = DEFAULT_MANAGER
        db.delete('CHARS_INJURY', f'id = {character_id} AND place = "{place_id}"')


class DiseaseType(DataObject):
    def __init__(self, id: str, **kwargs):
        self.disease_type_id = id
        super(DiseaseType, self).__init__('DISEASE_INIT', EID(id=self.disease_type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестное заболевание')
        self._mortality = self.field('mortality', 0)
        self._severity_per_cycle = self.field('severity_per_cycle', 0)
        self._immunity_per_cycle = self.field('immunity_per_cycle', 0)
        self._can_be_treated = self.field('can_be_treated', 0)
        self._treatment_per_cycle = self.field('treatment_per_cycle', 0)
        self._pain_offset = self.field('pain_offset', 0)
        self._capacity = self.field('capacity', None)
        self._capacity_offset = self.field('capacity_offset', 0)
        self._next_stage = self.field('next_stage', None)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def mortality(self) -> bool:
        return self._mortality.load(self.data_manager) == 1

    @property
    def severity_per_cycle(self) -> float:
        return self._severity_per_cycle.load(self.data_manager)

    @property
    def immunity_per_cycle(self) -> float:
        return self._immunity_per_cycle.load(self.data_manager)

    @property
    def can_be_treated(self) -> bool:
        return self._can_be_treated.load(self.data_manager) == 1

    @property
    def treatment_per_cycle(self) -> float:
        return self._treatment_per_cycle.load(self.data_manager)

    @property
    def pain_offset(self) -> float:
        return self._pain_offset.load(self.data_manager)

    @property
    def capacity(self) -> str:
        return self._capacity.load(self.data_manager)

    @property
    def capacity_id(self) -> str:
        return self.capacity

    @property
    def capacity_offset(self) -> int:
        return self._capacity_offset.load(self.data_manager)

    @property
    def next_stage(self) -> str:
        return self._next_stage.load(self.data_manager)

    def __repr__(self):
        return f'Disease.{self.disease_type_id}'


class Disease(DataObject):
    def __init__(self, disease_id: int, **kwargs):
        self.disease_id = disease_id

        DataObject.__init__(self, 'CHARS_DISEASE', EID(dis_id=self.disease_id), data_manager = kwargs.get('data_manager', DEFAULT_MANAGER))

        self._character_id = self.field('id', None)
        self._place = self.field('place', 'Все тело')
        self._current_severity = self.field('severity', 0)
        self._current_immunity = self.field('immunity', 0)
        self._healing_efficiency = self.field('healing', 0)

        self._disease_type = self.field('type', None)


    @property
    def character_id(self) -> int:
        return self._character_id.load(self.data_manager)

    @property
    def place(self) -> str:
        place = self._place.load(self.data_manager)
        return place if place is not None else 'Все тело'

    @property
    def place_id(self) -> str:
        place = self.place
        return place if place != 'Все тело' else place

    @property
    def current_severity(self) -> float:
        return self._current_severity.load(self.data_manager)

    @current_severity.setter
    def current_severity(self, value):
        self._current_severity.save(self.data_manager, value)

    @property
    def current_immunity(self) -> float:
        return self._current_immunity.load(self.data_manager)

    @current_immunity.setter
    def current_immunity(self, value):
        self._current_immunity.save(self.data_manager, value)

    @property
    def healing_efficiency(self) -> float:
        return self._healing_efficiency.load(self.data_manager)

    @healing_efficiency.setter
    def healing_efficiency(self, value):
        self._healing_efficiency.save(self.data_manager, value)

    @property
    def disease_type(self) -> DiseaseType:
        dis_type = self._disease_type.load(self.data_manager)
        if not dis_type:
            return None
        return DiseaseType(dis_type, data_manager=self.data_manager)

    @property
    def body_element(self) -> 'BodyElement':
        if not self.place_id:
            return None
        else:
            return BodyElement(self.character_id, self.place_id, data_manager=self.data_manager)

    @classmethod
    def get_character_diseases(cls, character_id: int, data_manager: DataManager = None):
        db = data_manager if data_manager is not None else DEFAULT_MANAGER
        respond = [(Disease(dis_id.get('dis_id'), data_manager=db), dis_id.get('place')) for dis_id in db.select_dict('CHARS_DISEASE', filter=f'id = {character_id}')]
        total_dict = {}
        for disease, place in respond:
            place = place if place is not None else 'Все тело'
            if place not in total_dict:
                total_dict[place] = []
            total_dict[place].append(disease)

        return total_dict

    @classmethod
    def create_character_disease(cls, character_id: int, disease_type_id:str, **kwargs):
        db = kwargs.get('data_manager', DEFAULT_MANAGER)
        dis_id = db.maxValue('CHARS_DISEASE', 'dis_id') + 1

        place = kwargs.get('place', None)
        severity = kwargs.get('severity', 0)
        immunity = kwargs.get('immunity', 0)
        healing_efficiency = kwargs.get('healing', 0)

        if db.check('CHARS_DISEASE', f'id = {character_id} AND type = "{disease_type_id}" AND place = "{place}"'):
            return
        elif db.check('CHARS_DISEASE', f'id = {character_id} AND type = "{disease_type_id}" AND place IS NULL') and place is None:
            return

        query = {'id': character_id,
                 'dis_id': dis_id,
                 'place': place,
                 'type': disease_type_id,
                 'severity': severity,
                 'immunity': immunity,
                 'healing': healing_efficiency}

        db.insert('CHARS_DISEASE', query)

        return cls(dis_id, data_manager=db)

    def calculate_pain(self):
        return self.current_severity * self.disease_type.pain_offset

    def add_severity(self, severity: float):
        new_severity = self.current_severity + severity
        self.set_severity(new_severity)

    def add_immunity(self, immunity: float):
        new_immunity = self.current_immunity + immunity
        self.set_immunity(new_immunity)

    def add_healing(self, healing: float):
        new_healing = self.healing_efficiency + healing
        self.set_healing(new_healing)

    def set_immunity(self, immunity: float):
        self.current_immunity = immunity

    def set_healing(self, healing: float):
        self.healing_efficiency = healing

    def set_severity(self, severity: float):
        self.current_severity = severity

    def get_healing_bonus(self):
        # В случае дисбаланса аптечек поменять на 0.5
        healing_bonus = 1 + self.healing_efficiency * 0.01
        return healing_bonus

    def update(self, filtration:int=100):
        treatment = self.disease_type.treatment_per_cycle * self.get_healing_bonus()
        filt_bonus = filtration / 100

        if self.current_severity >= 100 and self.disease_type.mortality:
            print('Я КАКОГО-ТО ХУЯ ТУТ ЗАБЫЛ', self.disease_type.mortality, self.disease_type)
            return

        self.add_immunity(self.disease_type.immunity_per_cycle * self.get_healing_bonus() * filt_bonus)

        if self.current_immunity >= 100:
            self.add_severity(-1 * treatment)
            if self.current_severity > 100:
                self.set_severity(100)

            if self.current_severity <= 0:
                self.delete_record()
        else:
            if self.disease_type.severity_per_cycle > 0:
                print('НА САМОМ ДЕЛЕ ТУТ ЛЕЧУ', self.disease_type, self.disease_type.severity_per_cycle)
                if self.current_severity + self.disease_type.severity_per_cycle < 100:
                    self.add_severity(self.disease_type.severity_per_cycle)
                else:
                    self.set_severity(100)
            else:
                print('ТУТ ЛЕЧУ')
                self.add_severity(self.disease_type.severity_per_cycle)

        if self.current_severity <= 0:
            self.delete_disease(self.disease_id)

    def get_body_element(self):
        if not self.place or self.place == 'Все тело':
            return None
        else:
            return BodyElement(self.character_id, self.place, data_manager=self.data_manager)

    def __repr__(self):
        return f'Disease.{self.disease_id} ({self.disease_type.disease_type_id})'

    def __str__(self):
        emoji = ''

        if self.current_immunity >= 100:
            emoji += ' <:immune:1249787600622063718>'

        return f'{self.disease_type.label} ({self.current_severity:.2f}%){emoji}'

    @staticmethod
    def delete_all_character_diseases(character_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_DISEASE', f'id = {character_id}')

    @staticmethod
    def delete_disease(dis_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_DISEASE', f'dis_id = {dis_id}')


class BodyPart(DataObject):
    def __init__(self, part_id:str, **kwargs):
        super(BodyPart, self).__init__('RACES_BODYPART', EID(part_id=part_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._race = self.field('race', None)
        self._part_id = self.field('part_id', None)
        self._label = self.field('label', 'Неизвестная конечность')
        self._type = self.field('type', None)
        self._body_parts_group = self.field('body_group', None)
        self._weapon_slot = self.field('weapon_slot', 0)
        self._coverage = self.field('coverage', 0)
        self._parent_part = self.field('subpart_of', None)
        self._is_internal = self.field('internal', 0)
        self._max_health = self.field('health', 0)
        self._capacity = self.field('capacity', None)
        self._efficiency = self.field('efficiency', 0)
        self._mortality = self.field('mortality', 0)
        self._bleeding_rate = self.field('bleed_rate', 1)
        self._scar_chance = self.field('scar_chance', 0)
        self._pain_factor = self.field('pain_factor', 1)

    @property
    def race(self) -> str:
        return self._race.load(self.data_manager)

    @property
    def race_id(self) -> str:
        return self.race

    @property
    def part_id(self) -> str:
        return self._part_id.load(self.data_manager)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def type(self) -> str:
        return self._type.load(self.data_manager)

    @property
    def body_parts_group(self) -> str:
        return self._body_parts_group.load(self.data_manager)

    @property
    def weapon_slot(self) -> int:
        return self._weapon_slot.load(self.data_manager)

    @property
    def coverage(self) -> float:
        return self._coverage.load(self.data_manager)

    @property
    def parent_part(self) -> str:
        return self._parent_part.load(self.data_manager)

    @property
    def is_internal(self) -> bool:
        return self._is_internal.load(self.data_manager) == 1

    @property
    def max_health(self) -> float:
        return self._max_health.load(self.data_manager)

    @property
    def capacity(self) -> str:
        return self._capacity.load(self.data_manager)

    @property
    def efficiency(self) -> float:
        return self._efficiency.load(self.data_manager)

    @property
    def mortality(self) -> float:
        return self._mortality.load(self.data_manager)

    @property
    def bleeding_rate(self) -> float:
        return self._bleeding_rate.load(self.data_manager)

    @property
    def scar_chance(self) -> float:
        return self._scar_chance.load(self.data_manager)

    @property
    def pain_factor(self) -> float:
        return self._pain_factor.load(self.data_manager)

    def find_children_bodyparts(self):
        query = f'subpart_of = "{self.part_id}"'
        result = {}
        total_children = self.data_manager.select_dict('RACES_BODYPART', filter=query)

        if not total_children:
            return result

        for child in total_children:
            result[BodyPart(child.get('part_id'), data_manager=self.data_manager)] = BodyPart(child.get('part_id'), data_manager=self.data_manager).find_children_bodyparts()

        return result

    def get_parent_part(self):
        if self.parent_part is None:
            return None
        return BodyPart(self.parent_part, data_manager=self.data_manager)

    def print_body_parts_hierarchy(self, indent=0):
        """
        Рекурсивно выводит иерархию частей тела в виде текста с отступами.
        """
        print('-' * indent + self.label)
        for child_part in self.find_children_bodyparts().keys():
            child_part.print_body_parts_hierarchy(indent + 1)

    def select_random_body_part(self):
        return self._select_random_body_part_recursive(self)

    def _select_random_body_part_recursive(self, current_part):
        # Получаем все дочерние части
        children_parts = list(current_part.find_children_bodyparts().keys())

        # Суммируем общее покрытие для текущей части и её дочерних частей
        total_coverage = current_part.coverage + sum(child.coverage for child in children_parts)

        # Генерируем случайное число в диапазоне от 0 до общего покрытия
        roll = random.uniform(0, total_coverage)

        # Проверяем текущую часть тела
        if roll <= current_part.coverage:
            return current_part

        # Проверяем дочерние части
        cumulative_coverage = current_part.coverage
        for child_part in children_parts:
            cumulative_coverage += child_part.coverage
            if roll <= cumulative_coverage:
                return self._select_random_body_part_recursive(child_part)

        # Если не выбрана ни одна дочерняя часть, возвращаем текущую часть
        return current_part

    def __repr__(self):
        return f'BodyPart.{self.part_id}'


class ImplantType(DataObject):
    def __init__(self, implant_id: str, **kwargs):
        self.implant_type_id = implant_id

        super(ImplantType, self).__init__('IMPLANTS_INIT', EID(id=self.implant_type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный имплант')
        self._install_slot = self.field('slot', None)
        self._is_replacing = self.field('is_replacing', 0)
        self._max_health = self.field('health', 0)
        self._capacity = self.field('capacity', None)
        self._capacity_efficiency = self.field('capacity_offset', 0)
        self._weapon_slot = self.field('weapon_slot', 0)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def install_slot(self) -> str:
        return self._install_slot.load(self.data_manager)

    @property
    def is_replacing(self) -> bool:
        return self._is_replacing.load(self.data_manager) == 1

    @property
    def max_health(self) -> float:
        return self._max_health.load(self.data_manager)

    @property
    def capacity(self) -> str:
        return self._capacity.load(self.data_manager)

    @property
    def capacity_efficiency(self) -> float:
        return self._capacity_efficiency.load(self.data_manager)

    @property
    def weapon_slot(self) -> int:
        return self._weapon_slot.load(self.data_manager)

    def __repr__(self):
        return f'ImplantType.{self.implant_type_id}'


class Implant(DataObject):
    def __init__(self, implant_id: int, **kwargs):
        self.imp_id = implant_id

        super(Implant, self).__init__('CHARS_BODY', EID(imp_id=self.imp_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._character_id = self.field('id', None)
        self._place = self.field('place', None)
        self._type = self.field('type', None)
        self._label = self.field('label', None)

    @property
    def character_id(self) -> int:
        return self._character_id.load(self.data_manager)

    @property
    def character(self):
        from ArbCharacters import Character
        character_id = self.character_id
        return Character(character_id, data_manager=self.data_manager) if character_id is not None else None

    @property
    def place(self) -> str:
        return self._place.load(self.data_manager)

    @property
    def place_id(self) -> str:
        return self.place

    @property
    def body_part(self) -> BodyPart | None:
        if self.place_id:
            return BodyPart(self.place_id, data_manager=self.data_manager)
        else:
            return None

    @property
    def type(self) -> ImplantType | None:
        implant_type = self._type.load(self.data_manager)
        if not implant_type:
            return None
        return ImplantType(implant_type, data_manager=self.data_manager)

    @property
    def label(self) -> str:
        label = self._label.load(self.data_manager)
        if not label:
            implant_type = self.type
            if not implant_type:
                return f'Неизвестный имплант'
            else:
                return implant_type.label
        else:
            return label

    @staticmethod
    def delete_all_character_implants(character_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_BODY', f'id = {character_id}')

    @staticmethod
    def delete_implant(implant_id:int):
        db = DEFAULT_MANAGER
        db.delete('CHARS_BODY', f'imp_id = {implant_id}')

    @classmethod
    def create_implant(cls, character_id:int, implant_type:str, place:str=None, label:str=None):
        db = DEFAULT_MANAGER
        imp_id = db.maxValue('CHARS_BODY', 'imp_id') + 1
        query = {
            'id': character_id,
            'imp_id': imp_id,
            'place': place,
            'type': implant_type,
            'label': label
        }

        db.insert('CHARS_BODY', query)

        new_implant = Implant(imp_id, data_manager=db)
        if new_implant.type.is_replacing and place:
            Injury.delete_injuries_in_place(character_id, place)

        return Implant(imp_id, data_manager=db)


class BodyElement:
    def __init__(self, character_id: int, element_id, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)
        self.element_id = element_id

        self._body_part = None
        self._implant = None

        if self.check_if_element_implant():
            self._implant = Implant(self.element_id, data_manager=self.data_manager)
        else:
            self._body_part = BodyPart(self.element_id, data_manager=self.data_manager)

        implant_id = self.check_element_replaced_with_implant()
        if implant_id:
            self._implant = Implant(implant_id, data_manager=self.data_manager)

    @property
    def body_part(self) -> BodyPart | None:
        return self._body_part

    @property
    def implant(self) -> Implant | None:
        return self._implant

    @property
    def race(self) -> str | None:
        if self._body_part:
            return self._body_part.race
        else:
            return None

    @property
    def race_id(self) -> str:
        return self.race

    @property
    def part_id(self) -> str | None:
        if self._body_part:
            return self._body_part.part_id
        elif self._implant:
            return f'{self._implant.imp_id}'

    @property
    def label(self) -> str:
        if not self._body_part:
            if not self._implant.body_part:
                return self._implant.label
            else:
                return f'{self._implant.label} ({self._implant.body_part.label})'
        else:
            if not self._implant:
                return self._body_part.label
            else:
                return f'{self._body_part.label} ({self._implant.label})'

    @property
    def type(self) -> str | None:
        if self._body_part:
            return self._body_part.type
        else:
            return None

    @property
    def body_parts_group(self) -> str | None:
        if self._body_part:
            return self._body_part.body_parts_group
        elif self._implant:
            return self._implant.body_part.body_parts_group
        else:
            return None

    @property
    def weapon_slot(self) -> int:
        if self._implant:
            return self._implant.type.weapon_slot
        elif self._body_part:
            return self._body_part.weapon_slot
        else:
            return 0

    @property
    def coverage(self) -> float:
        if self._body_part:
            return self._body_part.coverage
        elif self._implant:
            return 1
        else:
            return 0

    @property
    def parent_part(self) -> str | None:
        if self._body_part:
            return self._body_part.parent_part
        elif self._implant:
            return self._implant.place_id
        else:
            return None

    @property
    def is_internal(self) -> bool:
        if self._body_part:
            return self._body_part.is_internal
        else:
            return True

    @property
    def max_health(self) -> float:
        if self._implant:
            return self._implant.type.max_health
        elif self._body_part:
            return self._body_part.max_health
        else:
            return 0

    @property
    def capacity(self) -> str | None:
        if self._implant:
            return self._implant.type.capacity
        elif self._body_part:
            return self._body_part.capacity
        else:
            return None

    @property
    def efficiency(self) -> float:
        if self._implant:
            return self._implant.type.capacity_efficiency
        elif self._body_part:
            return self._body_part.efficiency
        else:
            return 0

    @property
    def mortality(self) -> float:
        if self._body_part:
            return self._body_part.mortality
        else:
            return 0

    @property
    def bleeding_rate(self) -> float:
        if self._implant:
            return 0
        elif self._body_part:
            return self._body_part.bleeding_rate
        else:
            return 0

    @property
    def scar_chance(self) -> float:
        if self._implant:
            return 0
        elif self._body_part:
            return self._body_part.scar_chance
        else:
            return 1

    @property
    def pain_factor(self) -> float:
        if self._implant:
            return 0
        elif self._body_part:
            return self._body_part.pain_factor
        else:
            return 1

    def set_group(self, group:str):
        self.body_parts_group = group

    def check_if_element_implant(self):
        if isinstance(self.element_id, int):
            return True
        else:
            return False

    def check_element_replaced_with_implant(self):
        if not self.data_manager.check('CHARS_BODY', f'id = {self.character_id}'):
            return None
        if self.data_manager.check('CHARS_BODY', f'id = {self.character_id} AND place = "{self.element_id}"'):
            imp_id = self.data_manager.select_dict('CHARS_BODY', filter=f'id = {self.character_id} AND place = "{self.element_id}"')[0].get('imp_id')
            if Implant(imp_id, data_manager=self.data_manager).type.is_replacing:
                return imp_id
            else:
                return None
        else:
            return None

    def calculate_recieved_damage(self):
        damage_on_part = Injury.get_character_injuries(self.character_id, self.data_manager, self.element_id)
        total_damage = sum(injury.damage for injury in damage_on_part.get(self.element_id, []))
        return total_damage

    def calculate_health(self):
        # Проверяем здоровье родительской части
        if self.parent_part:
            parent_health = self.get_parent_health(self.parent_part, self.character_id, self.data_manager)
            if parent_health <= 0:
                # Если родительская часть уничтожена, текущая часть тоже уничтожена
                return 0

        # Рассчитываем здоровье текущей части
        if self.max_health > 0:
            health = (self.max_health - self.calculate_recieved_damage()) / self.max_health
            return max(0, health)
        else:
            return 0

    @classmethod
    def get_parent_health(cls, parent_part: str, character_id:int, data_manager: DataManager = DEFAULT_MANAGER):
        return BodyElement(character_id, parent_part, data_manager=data_manager).calculate_health()

    def calculate_efficiency(self):
        if not self.efficiency:
            return 0

        if self.efficiency > 0:
            return self.efficiency * self.calculate_health()
        else:
            return self.efficiency * (1 - self.calculate_health())

    def find_children_bodyparts(self):
        query = f'subpart_of = "{self.part_id}"'
        result = {}
        total_children = self.data_manager.select_dict('RACES_BODYPART', filter=query)

        if not total_children:
            return result

        for child in total_children:
            result[BodyElement(self.character_id, child.get('part_id'), data_manager=self.data_manager)] = BodyElement(self.character_id, child.get('part_id'), data_manager=self.data_manager).find_children_bodyparts()

        return result

    def select_random_body_part(self):
        return self._select_random_body_part_recursive(self)

    def _select_random_body_part_recursive(self, current_part):
        # Получаем все дочерние части
        children_parts = list(current_part.find_children_bodyparts().keys())

        # Суммируем общее покрытие для текущей части и её дочерних частей
        total_coverage = current_part.coverage + sum(child.coverage for child in children_parts)

        # Генерируем случайное число в диапазоне от 0 до общего покрытия
        roll = random.uniform(0, total_coverage)

        print('КУБИК ВЫБОРА РАНДОМНОЙ ЧАСТИ ТЕЛА:', roll, current_part.coverage, total_coverage, current_part.label)

        # Проверяем текущую часть тела
        if roll <= current_part.coverage:
            return current_part

        # Проверяем дочерние части
        cumulative_coverage = current_part.coverage
        for child_part in children_parts:
            cumulative_coverage += child_part.coverage
            if roll <= cumulative_coverage:
                return self._select_random_body_part_recursive(child_part)

        # Если не выбрана ни одна дочерняя часть, возвращаем текущую часть
        return current_part

    def apply_damage(self, damage: Damage, effect: bool = False):
        if damage.damage <= 0:
            return None

        if self.calculate_health() <= 0:
            return None

        #
        # if self.calculate_overkill(damage.Damage, random.randint(damage.Type.min_overkill, damage.Type.max_overkill)):
        #     damage_label = f'{damage.Type.destruction_label} ({damage.Root})'
        #     self.delete_injuries()
        #     self.apply_implant('Destroyed', damage_label)
        #     return None

        if not self.data_manager.check('CHARS_INJURY', f'id_inj = 0'):
            c_id = 0
        else:
            c_id = self.data_manager.maxValue('CHARS_INJURY', 'id_inj') + 1

        injury_type = damage.random_injury()

        self.data_manager.insert('CHARS_INJURY', {'id': self.character_id,
                                                  'id_inj': c_id,
                                                  'place': self.element_id,
                                                  'type': injury_type,
                                                  'root': damage.root,
                                                  'damage': damage.damage,
                                                  'heal_efficiency': 0,
                                                  'is_scar': 0})
        if not effect:
            pass
        else:
            # damage.apply_effect(self.CharID)
            pass

    def recive_damage(self, *, damage_list: list[Damage] | Damage, apply_effect: bool = False) -> None:
        if isinstance(damage_list, Damage):
            self.apply_damage(damage_list, effect=apply_effect)
        else:
            for dam in damage_list:
                self.apply_damage(dam, effect=apply_effect)

    def get_race_attack(self):
        if self._implant:
            attack = self.data_manager.select_dict('IMPLANTS_MELEE', filter=f'implant_id = "{self._implant.type.implant_type_id}"')
            if not attack:
                return None
            else:
                return attack[0].get('id')

        if self.data_manager.check('RACES_MELEE', f'part_id = "{self.element_id}"'):
            return self.data_manager.select_dict('RACES_MELEE', filter=f'part_id = "{self.element_id}"')[0].get('id')

        return None

    def vital_offset(self):
        if not self.mortality:
            return 0

        recieved_damage = self.calculate_recieved_damage() if self.calculate_recieved_damage() <= self.max_health else self.max_health
        total_offset = self.mortality * (recieved_damage / self.max_health) if self.max_health else self.mortality
        return total_offset

    def replace_with_destroy(self):
        if self.calculate_health() > 0:
            return

        Implant.create_implant(self.character_id, 'Destroyed', self.element_id)
        self.data_manager.delete('CHARS_INJURY', f'id = {self.character_id} AND place = "{self.element_id}"')

    def __repr__(self):
        return f'BodyElement.{self.character_id}.{self.element_id}' + f'{f" {self._implant.type.implant_type_id}" if self._implant else ""}'

    def __str__(self):
        wounds = Injury.get_character_injuries(self.character_id, data_manager=self.data_manager).get(self.element_id, [])
        diseases = Disease.get_character_diseases(self.character_id, data_manager=self.data_manager).get(self.element_id, [])

        text = f'-# [ {self.label} ]:'
        if self.calculate_health() <= 0:
            text += f' {wounds[-1].injury_type.destroyed_label()} ({wounds[-1].root})'
            return f'{text}\n'

        text += '\n'
        for disease in diseases:
            text += f'- *{str(disease)}*\n'

        for wound in wounds:
            text += f'- *{str(wound)}*\n'

        return text


class Body:
    def __init__(self, character_id:int, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)

        self._body_elements = []
        self._injuries = []
        self._diseases = []
        self._pain = None
        self._bleed = None
        self._race_id = None
        self._race = None

    @property
    def body_elements(self):
        if not self._body_elements:
            self._body_elements = self.get_body_elements()
        return self._body_elements

    @property
    def injuries(self):
        if not self._injuries:
            self._injuries = self.fetch_all_injuries()
        return self._injuries

    @property
    def diseases(self):
        if not self._diseases:
            self._diseases = self.fetch_all_diseases()
        return self._diseases

    @property
    def pain(self):
        if self._pain is None:
            self._pain = self.calculate_pain()
        return self._pain

    @property
    def bleed(self):
        if self._bleed is None:
            self._bleed = self.calculate_bleeding()
        return self._bleed

    @property
    def race(self):
        if not self._race_id:
            self._race_id = self.get_character_race()
        return self._race_id

    @property
    def character_race(self):
        if not self._race:
            self._race = Race(self.race, data_manager=self.data_manager)

        return self._race

    def get_character_race(self) -> str | None:
        if self.data_manager.check('CHARS_INIT', f'id = {self.character_id}'):
            return self.data_manager.select_dict('CHARS_INIT', filter=f'id = {self.character_id}')[0].get('race', None)
        else:
            return None

    def get_race_bodyparts(self):
        if not self.race:
            return []

        race = self.character_race
        return race.fetch_bodyparts()

    def get_body_elements(self):
        elements = []
        for part_id in self.get_race_bodyparts():
            elements.append(BodyElement(self.character_id, part_id, data_manager=self.data_manager))

        if self.data_manager.check('CHARS_BODY', f'id = {self.character_id}'):
            implants = self.data_manager.select_dict('CHARS_BODY', filter=f'id = {self.character_id}')
            for implant in implants:
                # if not ImplantType(implant.get('type'), data_manager=self.data_manager).is_replacing or not implant.get('place'):
                #     imp_element = BodyElement(self.character_id, implant.get('imp_id'), data_manager=self.data_manager)
                #     imp_element.set_group(BodyPart(imp_element.parent_part).body_parts_group)
                #     elements.append(imp_element)
                implant_type = ImplantType(implant.get('type'), data_manager=self.data_manager)
                if not implant_type.is_replacing:
                    elements.append(BodyElement(character_id=self.character_id, element_id=implant.get('imp_id'), data_manager=self.data_manager))

        pprint.pprint(elements)

        return elements

    def fetch_all_injuries(self):
        return Injury.get_character_injuries(self.character_id, data_manager=self.data_manager)

    def fetch_all_diseases(self) -> dict[str, list[Disease]]:
        return Disease.get_character_diseases(self.character_id, data_manager=self.data_manager)

    def calculate_pain(self):
        injuries = self.injuries
        diseases = self.diseases
        race = self.character_race

        total_pain = 0
        for key in injuries:
            body_element = BodyElement(self.character_id, key, data_manager=self.data_manager)
            body_part_pain_factor = body_element.pain_factor
            if body_element.calculate_health() <= 0:
                total_pain += 20 * body_part_pain_factor
                continue

            for injury in injuries[key]:
                total_pain += injury.calculate_pain() * body_part_pain_factor

        for key in diseases:
            for disease in diseases[key]:
                total_pain += disease.calculate_pain()

        return (total_pain / race.pain_limit) * race.pain_factor * 100

    def calculate_bleeding(self):
        injuries = self.injuries
        total_bleeding = 0

        blood_pumping = self.get_capacity('BloodPumping')

        for key in injuries:
            for injury in injuries[key]:
                body_element = injury.get_body_element()
                total_bleeding += injury.injury_type.bleeding if injury.healing_efficiency <= 0 and not body_element.implant and not body_element.calculate_health() <= 0 and not injury.is_scar else 0

        return total_bleeding - blood_pumping

    def calculate_capacities(self):
        total_capacities = {}
        for limb in self.body_elements:
            if limb.capacity is None:
                continue

            if limb.capacity not in total_capacities:
                total_capacities[limb.capacity] = limb.calculate_efficiency()
            else:
                total_capacities[limb.capacity] += limb.calculate_efficiency()

        affects = {}
        for capacity, efficiency in total_capacities.items():
            capacity_affect = CapacityType(capacity, data_manager=self.data_manager).get_affected_capacities(efficiency)
            if capacity_affect:
                for cap in capacity_affect:
                    if cap not in affects:
                        affects[cap] = 0
                    affects[cap] += capacity_affect[cap]

        full_body_diseases = self.diseases
        print(total_capacities)
        print(full_body_diseases.get('Все тело', []))
        for dis in full_body_diseases.get('Все тело', []):
            if dis.disease_type.capacity:
                print(total_capacities[dis.disease_type.capacity], dis.disease_type.capacity_offset * dis.current_severity)
                total_capacities[dis.disease_type.capacity] += dis.disease_type.capacity_offset * dis.current_severity

        for capacity in total_capacities:
            if capacity not in affects:
                continue

            total_capacities[capacity] += affects[capacity]

        for capacity in total_capacities:
            if total_capacities[capacity] < 0:
                total_capacities[capacity] = 0

        return total_capacities

    def get_capacity(self, capacity:str):
        total_capacities = self.calculate_capacities()
        return total_capacities.get(capacity, 0)

    def choose_random_element(self):
        main_element = BodyElement(self.character_id, self.character_race.get_main_bodypart(), data_manager=self.data_manager)
        return main_element.select_random_body_part()

    def get_available_clothes_slots(self):
        elements = self.body_elements
        total_list = []
        for element in elements:
            if element.body_parts_group is None:
                continue
            total_list.append(element.body_parts_group)

        return list(set(total_list))

    def get_bleedout(self):
        if self.data_manager.check('CHARS_DISEASE', f'id = {self.character_id} AND type = "BloodLost"'):
            dis_id = self.data_manager.select_dict('CHARS_DISEASE', filter=f'id = {self.character_id} AND type = "BloodLost"')[0].get('dis_id')
            return Disease(dis_id, data_manager=self.data_manager)
        else:
            return None

    def bleeding(self, minutes:int):
        total_bleed = self.bleed
        blood_lost_per_minute = round(total_bleed / 1440, 2)

        if blood_lost_per_minute == 0:
            return

        total_percent = blood_lost_per_minute * minutes
        print(f'ИТОГОВОЕ КРОВОТЕЧЕНИЕ: {total_percent}')
        bleedout = self.get_bleedout()
        if not bleedout:
            print('КРОВОТЕЧЕНИЕ', bleedout)
            if total_percent <= 0:
                pass
            else:
                Disease.create_character_disease(self.character_id, "BloodLost", severity=total_percent, data_manager=self.data_manager)
                print('ДОБАВИЛ')
        else:
            bleedout.add_severity(total_percent)

    def all_bodyparts_groups(self):
        return self.get_available_clothes_slots()

    def get_bodyparts_in_group(self, body_parts_group: str):
        total_elemets = self.body_elements
        total_list = []
        for element in total_elemets:
            if element.body_parts_group == body_parts_group and not element.is_internal:
                total_list.append(element)

        return total_list

    def get_main_group(self):
        main_element = BodyElement(self.character_id,
                                   self.character_race.get_main_bodypart(),
                                   data_manager=self.data_manager)
        return main_element.body_parts_group

    def get_main_part(self):
        main_element = BodyElement(self.character_id, self.race.get_main_bodypart(), data_manager=self.data_manager)
        return main_element

    def choose_random_element_from_group(self, body_parts_group: str):
        parts_in_group = self.get_bodyparts_in_group(body_parts_group)
        if not parts_in_group:
            return None
        main_part: BodyElement = random.choice(parts_in_group)
        return main_part.select_random_body_part()

    def get_race_attacks(self) -> list[str]:
        body_parts_health = {element: element.calculate_health() for element in self.body_elements}
        total_attacks = []
        for element in body_parts_health:
            if body_parts_health[element] <= 0:
                continue

            if element.get_race_attack():
                total_attacks.append(element.get_race_attack())

        return total_attacks

    def string_capacities(self):
        capacities = self.calculate_capacities()
        total_text = ''

        for capacity, efficiency in capacities.items():
            capacity_type = CapacityType(capacity, data_manager=self.data_manager)
            total_text += f'- *{capacity_type.label}* — ***{efficiency:.2f}%***\n'

        return total_text

    def string_pain(self):
        pain = self.pain
        if pain < 0:
            pain = 0

        pain_label = 'Отсутствует'

        if pain < 10:
            pass
        elif 10 <= pain < 30:
            pain_label = 'Незначительная'
        elif 30 <= pain < 55:
            pain_label = 'Умеренная'
        elif 55 <= pain < 80:
            pain_label = 'Сильная'
        elif 80 <= pain < 100:
            pain_label = 'Экстремальная'
        else:
            pain_label = 'Критическая'

        return f'*Ощущаемая боль:* ***{pain_label} ({pain:.2f}%)***'

    def string_bleeding(self):
        bleeding = self.bleed
        hours_to_bleedout = round(2400 / bleeding, 2) if bleeding > 0 else 10000
        minutes_to_bleedout = round((hours_to_bleedout - int(hours_to_bleedout)) * 60)

        return f'*Кровотечение:* ***{bleeding:.1f}%*** ({int(hours_to_bleedout)} ч. {minutes_to_bleedout} мин. до смерти)' if bleeding > 0 else '*Кровотечение:* ***Отсутствует***'

    def string_vital_status(self):
        vital_effects = []
        is_dead = self.is_dead()

        # if is_dead[0]:
        #     vital_effects.append('Мертв')

        vital_effects.extend(is_dead[1])


        return f'*Осложнения:' + f" **{', '.join(vital_effects)}***" if vital_effects else f'*Осложнения: **Отсутствуют***'

    def string_hediff(self):
        body_elements = self.body_elements
        injuries = self.injuries
        diseases = self.diseases

        text = ''

        if 'Все тело' in diseases or 'Все тело' in injuries:
            body_text = f'-# [ Все тело ]:\n'
            body_injuries = injuries.get('Все тело', [])
            body_diseases = diseases.get('Все тело', [])

            for disease in body_diseases:
                body_text += f'- *{str(disease)}*\n'

            for injury in body_injuries:
                body_text += f'- *{str(injury)}*\n'

            text += body_text

        elements = [str(element) for element in body_elements if element.element_id in injuries or element.element_id in diseases]

        for element in elements:
            text += f'\n{element}'

        return text

    def string_bodyparts(self):
        elements = self.body_elements
        body_groups = {}
        total_text = ''

        for element in elements:
            element_text = f'- *{element.label}* — *{element.calculate_health() * 100:.2f}%*\n'
            if element.body_parts_group not in body_groups:
                body_groups[element.body_parts_group] = []
            body_groups[element.body_parts_group].append(element_text)

        for group, parts in body_groups.items():
            total_text += f'-# [ {group if group else "Другое"} ]:\n' + ''.join(parts) + '\n'  # '\n' for clearer output

        return total_text

    def elements_vital_offset(self):
        elements = self.body_elements
        total_vital = 100
        for element in elements:
            total_vital -= element.vital_offset()

        return total_vital if total_vital >= 0 else 0

    def capacity_vital_offset(self):
        capacities = self.calculate_capacities()
        total_vital = 100
        vital_effects = []
        for capacity in capacities:
            cap = CapacityType(capacity, data_manager=self.data_manager)
            if capacities[capacity] < 100:
                total_vital -= (cap.mortality/100) * (100 - capacities[capacity])
                print(cap.label, cap.mortality, capacities[capacity], total_vital)

            if capacities[capacity] <= cap.critical_value:
                vital_effects.append(cap.critical_effect)

        print(capacities, total_vital)

        return total_vital if total_vital >= 0 else 0, vital_effects

    def diseases_vital_offset(self):
        diseases = []
        total_diseases = self.diseases
        for slot in total_diseases:
            diseases.extend(total_diseases[slot])

        total_vital = 0
        for disease in diseases:
            if disease.current_severity > 0 and disease.disease_type.mortality:
                total_vital = disease.current_severity if disease.current_severity > total_vital else total_vital

        return total_vital if total_vital >= 0 else 0

    def is_dead(self) -> tuple[bool, list]:
        capacities_vital, capacities_effects = self.capacity_vital_offset()
        elements_vital = self.elements_vital_offset()
        diseases_vital = 100 - self.diseases_vital_offset()
        pain = self.pain

        if pain > 100:
            capacities_effects.append('Болевой шок')

        print('ПОЧЕМУ УМЕР', self.character_id, elements_vital, capacities_vital, diseases_vital)
        print(f'УМЕРШИЙ: {self.character_id}\n'
              f'СНИЖЕНИЕ ОТ ЭЛЕМЕНТОВ: {elements_vital}\n'
              f'СНИЖЕНИЕ ОТ ФИЗ ПОКАЗАТЕЛЕЙ: {capacities_vital}\n'
              f'СНИЖЕНИЕ ОТ БОЛЕЗНЕЙ: {diseases_vital}')

        if min(elements_vital, capacities_vital, diseases_vital) > 0 and 'Кома' not in capacities_effects and 'Болевой шок' not in capacities_effects:
            return False, capacities_effects
        else:
            if elements_vital == 0 or diseases_vital == 0:
                return True, ['Мертв']
            return True, capacities_effects

    def vital_damage(self) -> float:
        capacities_vital, capacities_effects = self.capacity_vital_offset()
        elements_vital = self.elements_vital_offset()
        diseases_vital = 100 - self.diseases_vital_offset()

        return min(elements_vital, capacities_vital, diseases_vital)

    def get_injuries_list(self) -> list:
        injuries_dict = self.injuries
        injuries = [item for sublist in injuries_dict.values() for item in sublist]
        return injuries

    def get_diseases_list(self) -> list:
        diseases_dict = self.diseases
        diseases = [item for sublist in diseases_dict.values() for item in sublist]
        return diseases

    def rest(self, healing_rate:int=0):
        filtration = self.get_capacity('BloodFiltration')

        injuries: list[Injury] = self.get_injuries_list()
        diseases: list[Disease] = self.get_diseases_list()

        for disease in diseases:
            if disease.healing_efficiency < healing_rate and disease.disease_type.can_be_treated:
                disease.set_healing(healing_rate)
            disease.update(filtration)

        if self.get_bleedout():
            total_bleed = self.get_bleedout()
            self.bleeding(1440)
            if total_bleed.current_severity <= 0:
                total_bleed.delete_disease(total_bleed.disease_id)

        for injury in injuries:
            place = injury.place
            if place:
                if BodyElement(self.character_id, place, data_manager=self.data_manager).calculate_health() <= 0:
                    continue
            if injury.is_scar:
                continue

            if injury.healing_efficiency < healing_rate:
                injury.set_healing(healing_rate)
            injury.update(filtration)


# class BodyPart:
#  def __init__(self, part_id: str, *, data_manager:DataManager=None):
#         self.ID = part_id
#         if data_manager:
#             self.data_manager = data_manager
#         else:
#             self.data_manager = DataManager()
#
#         if self.data_manager.check('RACES_BODY', f'part_id = "{self.ID}"'):
#             self.data_table = 'RACES_BODY'
#             self.id_label = 'part_id'
#         else:
#             self.data_table = 'IMPLANTS_INIT'
#             self.id_label = 'id'
#
#         data = self.fetch_data()
#
#         self.Label = data.get('label', '')
#         self.Slot = data.get('name', '')
#         self.IsInternal = data.get('internal', False)
#         self.LinkedPartID = data.get('linked', None)
#         self.TargetWeight = data.get('target_weight', 1)
#         self.Health = data.get('health', 0)
#         self.ScarChance = data.get('scar_chance', 0)
#         self.Fatality = data.get('fatality', 0)
#         self.BleedFactor = data.get('bleed_factor', 0)
#         self.Capacity = data.get('capacity', '')
#         self.Efficiency = data.get('efficiency', 0)
#         self.IsImplant = self.data_table == 'IMPLANTS_INIT'
#         self.WeaponSlots = data.get('weapon_slot', 0)
#
#         self.can_replace = data.get('can_replace', None)
#
#     def fetch_data(self) -> dict:
#         if self.data_manager.check(self.data_table, filter=f'{self.id_label} = "{self.ID}"') is None:
#             return {}
#         else:
#             return self.data_manager.select_dict(self.data_table, filter=f'{self.id_label} = "{self.ID}"')[0]
#
#     def get_internal_organs(self):
#         organ_table = "RACES_BODY"  # Предположим, что есть таблица с информацией об органах
#         filter = f'linked = "{self.ID}" AND internal = 1'  # Предположим, что связанная часть тела имеет идентификатор item_id
#
#         # Используем метод select_dict для получения информации об органах внутри данной части тела
#         internal_organs = self.data_manager.select_dict(organ_table, columns='*', filter=filter)
#
#         return internal_organs
#
#     def get_external_parts(self):
#         organ_table = "RACES_BODY"  # Предположим, что есть таблица с информацией об органах
#         filter = f'linked = "{self.ID}" AND internal = 0'  # Предположим, что связанная часть тела имеет идентификатор item_id
#
#         # Используем метод select_dict для получения информации об органах внутри данной части тела
#         internal_organs = self.data_manager.select_dict(organ_table, columns='*', filter=filter)
#
#         return internal_organs
#
#     def choose_random_part(self, roll:float=random.randint(0,100)):
#         c_part = random.choice([self, self.choose_random_external_part()])
#         print(c_part, c_part.get_internal_organs())
#         if roll >= 80 and c_part.get_internal_organs():
#             return c_part.choose_random_internal_part(), c_part
#         else:
#             return c_part, None
#
#     def choose_random_internal_part(self):
#         internal_organs = self.get_internal_organs()
#
#         if not internal_organs:
#             return None
#
#         total_weight = sum(organ['target_weight'] for organ in internal_organs)
#         random_weight = random.uniform(0, total_weight)
#
#         current_weight = 0
#         for organ in internal_organs:
#             current_weight += organ['target_weight']
#             if random_weight <= current_weight:
#                 return BodyPart(organ['part_id'], data_manager=self.data_manager)
#
#         return None
#
#     def choose_random_external_part(self):
#         internal_organs = self.get_external_parts()
#         if not internal_organs:
#             return None
#
#         total_weight = sum(organ['target_weight'] for organ in internal_organs)
#         random_weight = random.uniform(0, total_weight)
#
#         current_weight = 0
#         for organ in internal_organs:
#             current_weight += organ['target_weight']
#             if random_weight <= current_weight:
#                 return BodyPart(organ['part_id'],data_manager=self.data_manager)
#
#         return None
#
#     def attacks(self) -> list | None:
#         c_attacks = []
#
#         if self.IsImplant and self.data_manager.check('IMPLANTS_MELEE', f'implant_id = "{self.ID}"'):
#             c_attacks = self.data_manager.select('IMPLANTS_MELEE', columns='id', filter=f'implant_id = "{self.ID}"')
#         elif self.data_manager.check('RACES_MELEE', f'part_id = "{self.ID}"'):
#             c_attacks = self.data_manager.select('RACES_MELEE', columns='id', filter=f'part_id = "{self.ID}"')
#
#         if not c_attacks:
#             return None
#         else:
#             return [attack[0] for attack in c_attacks]
#
#     def get_affected_capacity(self, total_damage: int) -> Capacity | None:
#         if self.Capacity:
#             hp = max(self.Health - total_damage, 0)  # Учитываем уровень повреждений
#             if self.Efficiency >= 0:
#                 affected_value = (hp / self.Health) * self.Efficiency
#             else:
#                 affected_value = ((self.Health - hp) / self.Health) * self.Efficiency
#
#             return Capacity(name=self.Capacity, value=affected_value)
#         else:
#             return None
#
#     def __str__(self):
#         return f'{self.Label} ({self.ID})'
#
#     def __repr__(self):
#         if self.IsImplant:
#             return f'BodyImplant.{self.ID}'
#         else:
#             return f'BodyPart.{self.ID}'
#
#
# class LocalBodyPart(BodyPart):
#     def __init__(self, char_id: int, part_id: str, **kwargs):
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         if isinstance(part_id, int):
#             part = self.data_manager.select_dict('CHARS_BODY',filter=f'imp_id = {part_id}')[0].get('type')
#         else:
#             part = part_id
#
#         super().__init__(part, data_manager=self.data_manager)
#         self.ID = part_id
#
#         self.CharID = char_id
#         self.CurrentHealth = self.Health
#         self.Place = kwargs.get('place', None)
#         self.Label = kwargs.get('label', self.Label)
#
#         self.process_injuries()
#         self.calculate_efficiency()
#         self.process_illnesses()
#
#         self.injuries = []
#         self.fetch_injuries()
#         self.diseases = self.fetch_diseases()
#
#     def process_injuries(self):
#         injuries = self.data_manager.select('CHARS_INJURY', columns='id_inj', filter=f'id = {self.CharID} AND place = "{self.ID}"')
#         if injuries:
#             for injury_id in injuries:
#                 injury_data = self.data_manager.select_dict('CHARS_INJURY', filter=f'id = {self.CharID} AND id_inj = {injury_id[0]}')[0]
#                 self.CurrentHealth -= injury_data.get('damage', 0)
#
#     def fetch_injuries(self):
#         injury_data = self.data_manager.select('CHARS_INJURY',columns='id_inj', filter=f'place = "{self.ID}" AND id = {self.CharID}')
#         for data in injury_data:
#             new_injury = LocalInjury(data[0], self.CharID, data_manager=self.data_manager)
#             self.injuries.append(new_injury)
#
#     def calculate_efficiency(self):
#         if self.Efficiency > 0:
#             self.CurrentEfficiency = self.Efficiency * (self.CurrentHealth / self.Health)
#             if self.CurrentEfficiency < 0:
#                 self.CurrentEfficiency = 0
#
#         else:
#             if self.CurrentHealth == self.Health:
#                 self.CurrentEfficiency = 0
#             else:
#                 self.CurrentEfficiency = self.Efficiency * ((self.Health - self.CurrentHealth) / self.Health)
#
#     def part_health(self):
#         health = self.CurrentHealth/self.Health if self.Health > 0 else 0
#         return health if health > 0 else 0
#
#     def process_illnesses(self):
#         diseases = self.data_manager.select('CHARS_DISEASE', columns='dis_id', filter=f'id = {self.CharID} AND (place = "{self.ID}" OR place is NULL)')
#         print(diseases)
#         if diseases and not self.IsImplant:
#             for disease_id in diseases:
#                 disease = LocalDisease(data_manager=self.data_manager, dis_id=disease_id[0], char_id=self.CharID)
#                 if disease.Place == self.ID:
#                     self.CurrentEfficiency -= disease.Severity * disease.Affect
#                 if disease.Capacity == self.Capacity:
#                     self.CurrentEfficiency -= disease.Severity * disease.Effect
#
#     def fetch_diseases(self):
#         total_list = []
#         diseases = self.data_manager.select_dict('CHARS_DISEASE', filter=f'id = {self.CharID} and (place = "{self.ID}" OR place is NULL)')
#         if diseases and not self.IsImplant:
#             for disease_id in diseases:
#                 disease = LocalDisease(data_manager=self.data_manager, dis_id=disease_id.get('dis_id'), char_id=self.CharID)
#                 total_list.append(disease)
#
#         return total_list
#
#     def calculate_bleeding(self):
#         if not self.IsImplant:
#             total_bleeding = sum(injury.Bleed for injury in self.injuries) * self.BleedFactor
#             return max(0, total_bleeding)
#         else:
#             return 0
#
#     def calculate_pain(self):
#         total_pain = 0
#         for injury in self.injuries:
#             pain_factor = getattr(injury, 'PainFactor', 0)
#             total_pain += (injury.Damage - (injury.Damage * (injury.HealingEfficiency / 70))) * pain_factor
#
#         for ill in self.diseases:
#             total_pain += (ill.Severity - ill.Healing) * ill.PainFactor
#
#         return total_pain if total_pain > 0 else 0
#
#     def affected_capacity(self) -> Capacity | None:
#         if self.Capacity:
#             return Capacity(name=self.Capacity, value=self.CurrentEfficiency)
#         else:
#             return None
#
#     def part_attacks(self):
#         if self.CurrentHealth/self.Health < 0.5:
#             return []
#         else:
#             return self.attacks()
#
#     def get_root_partlabel(self):
#         if not self.IsImplant:
#             return None
#         else:
#             if not self.data_manager.check('CHARS_BODY',f'id = {self.CharID} AND imp_id = {self.ID} AND place = "{self.Place}"'):
#                 return None
#             else:
#                 return BodyPart(self.Place, data_manager=self.data_manager).Label
#
#     def part_attack(self, attack_id:str):
#         if attack_id not in self.attacks():
#             return None
#         else:
#             total_damage = []
#             c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
#             c_damages = c_attack.attack()
#             for damage in c_damages:
#                 c_damage = damage.get('damage') * (self.CurrentHealth/self.Health)
#                 c_penetration = damage.get('penetration') * (self.CurrentHealth/self.Health)
#                 total_damage.append({'damage': c_damage,
#                                      'penetration': c_penetration})
#
#             return total_damage
#
#     def delete_injuries(self):
#         self.data_manager.delete('CHARS_INJURY',f'id = {self.CharID} AND place = "{self.ID}"')
#
#     def calculate_overkill(self, damage:int, overkill_roll:int):
#         if (self.CurrentHealth-damage > 0) or self.Health <= 0:
#             return False
#
#         damage_overkill = damage*(overkill_roll/100)
#
#         overkill_chance = (damage_overkill / self.Health)*100
#         c_roll = random.randint(0, 100)
#         print(overkill_chance, c_roll)
#         if c_roll <= overkill_chance:
#             return True
#         else:
#             return False
#
#     def apply_implant(self, type:str, label:str):
#         if not self.data_manager.check('CHARS_BODY', f'id = {self.CharID}'):
#             c_id = 0
#         else:
#             c_id = self.data_manager.maxValue('CHARS_BODY', 'imp_id', f'id = {self.CharID}') + 1
#
#         query = {'id': self.CharID,
#                  'imp_id': c_id,
#                  'place': self.ID,
#                  'linked': None,
#                  'type': type,
#                  'label': label}
#
#         self.data_manager.insert('CHARS_BODY',query)
#
#     def all_disieases_are_global(self):
#         diseases = self.data_manager.select('CHARS_DISEASE', columns='dis_id', filter=f'id = {self.CharID} AND (place = "{self.ID}" OR place is NULL)')
#         if diseases:
#             for disease_id in diseases:
#                 disease = LocalDisease(disease_id[0], self.CharID, data_manager=self.data_manager)
#                 if disease.Place == self.ID:
#                     return False
#
#         return True
#
#     def apply_damage(self, damage: Damage, effect:bool=False):
#         if damage.Damage <= 0:
#             return None
#
#         if self.calculate_overkill(damage.Damage, random.randint(damage.Type.min_overkill, damage.Type.max_overkill)):
#             damage_label = f'{damage.Type.destruction_label} ({damage.Root})'
#             self.delete_injuries()
#             self.apply_implant('Destroyed', damage_label)
#             return None
#
#         if not self.data_manager.check('CHARS_INJURY', f'id = {self.CharID}'):
#             c_id = 0
#         else:
#             c_id = self.data_manager.maxValue('CHARS_INJURY', 'id_inj', f'id = {self.CharID}') + 1
#
#         c_type = random.choice(damage.Type.get_possible_injuries())
#         bleed_chance = c_type.Bleed * damage.Damage * self.BleedFactor
#         c_roll = random.randint(0, 100)
#
#         if c_roll <= bleed_chance:
#             c_bleed = c_type.Bleed * damage.Damage
#         else:
#             c_bleed = 0
#
#         self.data_manager.insert('CHARS_INJURY', {'id': self.CharID,
#                                                   'id_inj': c_id,
#                                                   'place': self.ID,
#                                                   'type': c_type.ID,
#                                                   'root': damage.Root,
#                                                   'damage': damage.Damage,
#                                                   'bleed': c_bleed,
#                                                   'heal_efficiency': 0,
#                                                   'is_scar': 0})
#         if not effect:
#             pass
#         else:
#             damage.Type.apply_effect(self.CharID)
#
#     def recive_damage(self, *, damage_list: list[Damage] | Damage, apply_effect: bool = False) -> None:
#         if isinstance(damage_list, Damage):
#             self.apply_damage(damage_list, effect=apply_effect)
#         else:
#             for dam in damage_list:
#                 self.apply_damage(dam, effect=apply_effect)
#
#         self.data_manager.logger.info(f'Персонаж {self.ID} получил урон {damage_list}')
#
#     def __str__(self):
#         print(self.get_root_partlabel())
#         if self.IsImplant and self.get_root_partlabel():
#             main_text = f'**[ {self.get_root_partlabel()} ]:** *{self.Label}*\n'
#         else:
#             main_text = f'**[ {self.Label} ]:**\n'
#         if not self.injuries and not self.diseases:
#             return main_text
#         else:
#             injury_text = f''
#             for i in self.diseases:
#                 if i.Place is not None:
#                     injury_text += f'- *{i.Name}*'
#                     if i.Immunity >= 100:
#                         injury_text += ' <:immune:1249787600622063718>\n'
#                     else:
#                         injury_text += '\n'
#
#             for i in self.injuries:
#                 inj_name = i.Name if not self.IsInternal else i.InnerName
#                 if i.IsScar:
#                     inj_name = i.ScarName if not self.IsInternal else i.ScarInnerName
#
#                 injury_text += f'- *{inj_name} ({i.Root})*'
#                 if i.HealingEfficiency:
#                     injury_text += ' <:healed:1249753146859847760>\n'
#                 elif i.Bleed:
#                     injury_text += ' <:bleed:1249850720065425480>\n'
#                 else:
#                     injury_text += '\n'
#
#             if self.all_disieases_are_global() and not self.injuries:
#                 return
#
#             return main_text + injury_text
#
#
#
#
# class LocalInjury(Injury):
#     def __init__(self, inj_id: int, char_id: int, *, data_manager=None):
#         self.InjuryID = inj_id
#         self.CharID = char_id
#         self.data_manager = data_manager if data_manager else DataManager()
#         injury_data = self.my_fetch_data()
#         self.type = injury_data.get('type', '')
#
#         super().__init__(self.type, data_manager=self.data_manager)  # Вызываем суперкласс с типом полученным из базы данных
#
#         self.Place = injury_data.get('place', '')
#         self.Root = injury_data.get('root', '')
#         self.Damage = injury_data.get('damage', 0)
#         self.Bleed = injury_data.get('bleed', 0)
#         self.HealingEfficiency = injury_data.get('heal_efficiency', 0)
#         self.IsScar = injury_data.get('is_scar', False) == 1
#
#     def my_fetch_data(self) -> dict:
#         if self.data_manager.check('CHARS_INJURY',filter=f'id_inj = {self.InjuryID} AND id = {self.CharID}') is None:
#             return {}
#         else:
#             return self.data_manager.select_dict('CHARS_INJURY', filter=f'id_inj = {self.InjuryID} AND id = {self.CharID}')[0]
#
#     def heal(self, heal_efficiency:int):
#         self.HealingEfficiency += heal_efficiency
#         query = {'heal_efficiency': self.HealingEfficiency}
#         self.data_manager.update('CHARS_INJURY', query, f'id_inj = {self.InjuryID}')
#
#     def delete(self):
#         self.data_manager.delete('CHARS_INJURY', filter=f'id = {self.CharID} AND id_inj = {self.InjuryID}')
#
#
# class Disease:
#     def __init__(self, name: str):
#         self.data_manager = DataManager()
#
#         self.ID = name
#         self.Name = None
#         self.PainFactor = None
#         self.Affect = None
#         self.Capacity = None
#         self.Effect = None
#         self.Fatal = False
#         self.StartSeverity = None
#         self.SeveritySpeed = None
#         self.ImmunitySpeed = None
#         self.RecoverySpeed = None
#         self.NextStage = None
#
#         data = self.my_fetch_data()
#
#         if data:
#             self.Name = data.get('name')
#             self.PainFactor = data.get('pain', 0)
#             self.Affect = data.get('affect', 0)
#             self.Capacity = data.get('capacity', 0)
#             self.Effect = data.get('effect', 0)
#             self.Fatal = data.get('fatal', False)
#             self.StartSeverity = data.get('start', 0)
#             self.SeveritySpeed = data.get('severity', 0)
#             self.ImmunitySpeed = data.get('immunity', 0)
#             self.RecoverySpeed = data.get('recover', 0)
#             self.NextStage = data.get('next_stage', '')
#
#     def my_fetch_data(self) -> dict:
#         columns = ['name', 'pain', 'affect', 'capacity', 'effect', 'fatal', 'start', 'severity', 'immunity', 'recover',
#                    'next_stage']
#         data = {}
#
#         for col in columns:
#             data[col] = self.data_manager.selectOne('DISEASE_INIT', columns=col, filter=f'id = "{self.ID}"')[0]
#
#         return data
#
#     def __repr__(self):
#         return self.Name
#
#
# class LocalDisease(Disease):
#     def __init__(self, dis_id: int, char_id: int, *, data_manager=None):
#         self.DiseaseID = dis_id
#         self.CharID = char_id
#         self.data_manager = data_manager if data_manager else DataManager()
#         disease_data = self.fetch_data()
#         self.type = disease_data.get('type','')
#
#         super().__init__(self.type)  # Вызываем суперкласс без передачи аргументов по умолчанию
#
#         self.Place = disease_data.get('place', '')
#         self.Severity = disease_data.get('severity', 0)
#         self.Healing = disease_data.get('healing', 0)
#         self.Immunity = disease_data.get('immunity', 0)
#
#     def fetch_data(self) -> dict:
#         data = {}
#
#         columns = ['type', 'place', 'severity', 'healing', 'immunity']
#         for col in columns:
#             data[col] = self.data_manager.selectOne('CHARS_DISEASE', columns=col, filter=f'id = {self.CharID} AND dis_id = {self.DiseaseID}')[0]
#
#         return data
#
#
# class RaceAttack:
#     def __init__(self, attack_id:str, **kwargs):
#         self.id = attack_id
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         self.damage = self.fetch_damage()
#         self.part_name = self.fetch_body_part_name()
#         self.main_data = self.fetch_main_data()
#         self.cost = self.main_data.get('ap', 0)
#         self.range = self.main_data.get('range', 0)
#         self.name = self.main_data.get('name', 'Неизвестная расовая атака')
#
#     def fetch_main_data(self):
#         if self.data_manager.check('RACES_MELEE', f'id = "{self.id}"'):
#             return self.data_manager.select_dict('RACES_MELEE', filter=f'id = "{self.id}"')[0]
#         elif self.data_manager.check('IMPLANTS_MELEE', f'id = "{self.id}"'):
#             return self.data_manager.select_dict('IMPLANTS_MELEE', filter=f'id = "{self.id}"')[0]
#         else:
#             return {}
#
#     def fetch_body_part_name(self):
#         c_part_id_info = self.data_manager.select_dict('RACES_MELEE', filter=f'id = "{self.id}"')
#         if c_part_id_info:
#             c_part_id = c_part_id_info[0].get('part_id', None)
#         else:
#             c_part_id_info = self.data_manager.select_dict('IMPLANTS_MELEE', filter=f'id = "{self.id}"')
#             if c_part_id_info:
#                 c_part_id = c_part_id_info[0].get('implant_id', None)
#             else:
#                 return None
#
#         if not c_part_id:
#             return None
#         else:
#             if self.data_manager.check('RACES_BODY', f'part_id = "{c_part_id}"'):
#                 c_part_name = self.data_manager.select_dict('RACES_BODY', filter=f'part_id = "{c_part_id}"')[0]
#             elif self.data_manager.check('IMPLANTS_BODY', f'part_id = "{c_part_id}"'):
#                 c_part_name = self.data_manager.select_dict('IMPLANTS_BODY', filter=f'part_id = "{c_part_id}"')[0]
#             else:
#                 c_part_name = {"label": "Неизвестно", "race": "Неизвестно"}
#
#             c_race_name = self.data_manager.select_dict('RACES_INIT', filter=f'id = "{c_part_name.get("race")}"')[0]
#             return f'{c_part_name.get("label", "Неизвестно")} ({c_race_name.get("name", "Неизвестно")})'
#
#     def fetch_damage(self):
#         if self.data_manager.check('RACES_DAMAGE', f'id = "{self.id}"'):
#             return self.data_manager.select_dict('RACES_DAMAGE', filter=f'id = "{self.id}"')
#         elif self.data_manager.check('IMPLANTS_DAMAGE', f'id = "{self.id}"'):
#             return self.data_manager.select_dict('IMPLANTS_DAMAGE', filter=f'id = "{self.id}"')
#         else:
#             return []
#
#     def attack(self) -> list:
#         from ArbDamage import Damage, Penetration
#         damage_list = []
#         for damage in self.damage:
#             crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 * damage.get('critical_chance', 1) else 1
#
#             damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
#             total_damage = Damage(damage_value, damage.get('damage_type', 'Hit'), root=self.part_name,data_manager=self.data_manager)
#
#             protection_type = self.data_manager.select_dict('DAMAGE_TYPE', filter=f'id = "{total_damage.Type.damage_id}"')[0].get('protection_type')
#
#             c_pars = {'damage': total_damage,'penetration': Penetration(name=protection_type, value=damage.get('penetration'), blocked_type=damage.get('blocked_type'))}
#
#             damage_list.append(c_pars)
#         return damage_list
#
#
# class Body:
#     def __init__(self, character_id: int, **kwargs):
#         self.data_manager = kwargs.get('data_manager',DataManager())
#         self.character_id = character_id
#
#         # Получаем информацию о расе персонажа из таблицы CHARS_INIT
#         self.race = self.data_manager.selectOne("CHARS_INIT", columns="race", filter=f"id = {self.character_id}")[0]
#
#         self.body_parts = self.fetch_bodyparts()
#         self.parent_part = self.data_manager.selectOne("RACES_BODY", columns="part_id", filter=f'race = "{self.race}" AND linked is NULL')[0]
#
#     def get_race(self):
#         race = self.data_manager.select_dict('CHARS_INIT',filter=f'id = {self.character_id}')[0]
#         return race.get('race', 'Human')
#
#     def fetch_bodyparts(self):
#         body_parts = []
#         # Получаем список частей тела для данной расы из таблицы RACES_BODY
#         body_parts_data = self.data_manager.select("RACES_BODY", columns="part_id", filter=f'race = "{self.race}"')
#
#         for part_id in body_parts_data:
#             # Проверяем, есть ли имплант, замещающий данную часть тела
#             is_implant_present = self.data_manager.check("CHARS_BODY",
#                                                          f"id = '{self.character_id}' AND place = '{part_id[0]}'")
#             if is_implant_present:
#                 implant_id = self.data_manager.select_dict("CHARS_BODY",
#                                                          filter=f"id = {self.character_id} AND place = '{part_id[0]}'")[0]
#                 part = LocalBodyPart(self.character_id, implant_id.get('imp_id'), data_manager=self.data_manager, place=implant_id.get('place'), label=implant_id.get('label'))  # Заменяем часть тела имплантом
#             else:
#                 part = LocalBodyPart(self.character_id, part_id[0], data_manager=self.data_manager) # Используем оригинальную часть тела
#
#             body_parts.append(part)
#
#         return body_parts
#
#     def physical_stats(self):
#         physical_stats = {}
#
#         # Собираем исходные физические показатели персонажа
#         for part in self.body_parts:
#             if part.Efficiency is None or part.Efficiency == 0:
#                 continue
#
#             if part.Capacity in physical_stats:
#                 if isinstance(physical_stats[part.Capacity], int) or isinstance(physical_stats[part.Capacity], float):
#                     physical_stats[part.Capacity] += part.affected_capacity().value
#                 else:
#                     physical_stats[part.Capacity] += part.affected_capacity()
#             else:
#                 physical_stats[part.Capacity] = part.affected_capacity().value
#
#         # Применяем влияние одних показателей на другие
#         affects_data = self.data_manager.select("CAPACITIES_AFFECTS", columns="name, affect, weight, max")
#
#         for affect_data in affects_data:
#             affecting_capacity = affect_data[0]
#             affected_capacity = affect_data[1]
#             effect_weight = affect_data[2]
#             max_effect = affect_data[3]
#
#             if affecting_capacity in physical_stats and affected_capacity in physical_stats:
#                 affecting_value = physical_stats[affecting_capacity]
#                 affected_value = physical_stats[affected_capacity]
#
#                 delta = (100-affecting_value) * effect_weight
#                 if delta > max_effect:
#                     delta = max_effect
#
#                 if isinstance(affected_value, int) or isinstance(affected_value, float):
#                     physical_stats[affected_capacity] = affected_value - delta
#                 else:
#                     physical_stats[affected_capacity] = Capacity(name=affected_capacity, value=affected_value - delta)
#
#         return physical_stats
#
#     def physical_stat(self, stat_name:str):
#         stats = self.physical_stats()
#         return stats[stat_name] if stat_name in stats else 0
#
#     def calculate_total_bleeding(self):
#
#         bleed_filter = self.physical_stat('Кровообращение')
#
#         total_bleeding = sum(part.calculate_bleeding() for part in self.body_parts)
#         total_bleeding = max(total_bleeding - bleed_filter, 0)
#
#         return total_bleeding
#
#     def time_to_bleed_out(self):
#         c_bleed = self.calculate_total_bleeding()
#         race_blood = self.data_manager.selectOne("RACES_INIT", columns="blood", filter=f"id = '{self.race}'")[0]
#
#         return c_bleed / race_blood
#
#     def calculate_total_pain(self):
#         c_data = self.data_manager.select_dict("RACES_INIT", columns='*', filter=f"id = '{self.race}'")[0]
#         pain_factor = c_data.get('pain_factor', 1)
#         pain_limit = c_data.get('pain_limit', 100)
#
#
#         total_pain = sum(part.calculate_pain() for part in self.body_parts)
#
#         total_pain = (total_pain * pain_factor) / pain_limit
#
#         return total_pain * 100
#
#     def available_attacks(self):
#         total_attacks = []
#         for i in self.body_parts:
#             if i.part_attacks() is not None:
#                 total_attacks += i.part_attacks()
#
#         return total_attacks
#
#     def attacks(self):
#         total_attacks = []
#         for i in self.body_parts:
#             if i.part_attacks() is not None:
#                 total_attacks.append({'part_id': i.ID,
#                                       'attacks': i.part_attacks()})
#
#         return total_attacks
#
#     def part_of_attack(self, attack_id:str):
#         c_attacks = self.available_attacks()
#         c_parts_and_attacks = self.attacks()
#         if attack_id not in c_attacks:
#             return None
#         else:
#             for i in c_parts_and_attacks:
#                 if attack_id in i.get('attacks'):
#                     return LocalBodyPart(self.character_id, i.get('part_id'), data_manager=self.data_manager)
#
#     def parts_health(self) -> dict:
#         total_list = {}
#         for part in self.body_parts:
#             total_list[part] = part.part_health()
#
#         return total_list
#
#     def phisical_stats_print(self):
#         c_stats = self.physical_stats()
#         c_bleeding = self.calculate_total_bleeding()
#         c_pain = self.calculate_total_pain()
#         total_text = ''
#         total_text += f'\n```Статус: {self.vital_signs()["status"]}```\n'
#         for stat in c_stats:
#             total_text += f'\n**{stat}** - *{c_stats[stat] if c_stats[stat] > 0 else 0:.2f}%*'
#
#         total_text += f'\n\n**Кровотечение:** *{c_bleeding:.2f}%* {self.__bleed__()}'
#         total_text += f'\n**Боль:** *{c_pain:.2f}%* ({self.__pain__()})'
#         total_text += f'\n**Жизнеспособность:** *{self.__vital__()}*'
#
#         return total_text
#
#     def get_global_diseases(self):
#         c_diseases = [LocalDisease(dis.get('dis_id'), self.character_id, data_manager=self.data_manager) for dis in self.data_manager.select_dict("CHARS_DISEASE", filter=f"id = {self.character_id} AND place is NULL")]
#
#         return c_diseases
#
#     def __str__(self):
#
#         c_blood_lost = self.__bloodloss__()
#         global_diseases = self.get_global_diseases()
#
#         text = ''
#
#         if c_blood_lost or global_diseases:
#             text += f'\n**[ Все тело ]:**'
#
#             if c_blood_lost != 'Отсутствует':
#                 text += f'*{c_blood_lost}*\n'
#
#             if global_diseases:
#                 for dis in global_diseases:
#                     text += f'\n- *{dis.Name}*'
#                     if dis.Immunity >= 100:
#                         text += ' <:immune:1249787600622063718>'
#                     else:
#                         text += ''
#
#         text += '\n'
#
#         for i in self.body_parts:
#             if i.injuries or i.IsImplant or i.diseases:
#                 if i.__str__():
#                     text += '\n' + i.__str__()
#
#         return text
#
#     def vital_damage(self):
#         c_parts: dict[LocalBodyPart] = self.parts_health()
#         c_vital = 100
#
#         for part in c_parts:
#             if part.IsImplant:
#                 vital_effect = BodyPart(part.Place, data_manager=self.data_manager).Fatality
#             else:
#                 vital_effect = part.Fatality
#             c_health = 1 - c_parts[part]
#             c_vital -= vital_effect * c_health
#
#         return c_vital if c_vital > 0 else 0
#
#     def vital_signs(self):
#         from ArbRaces import Race
#
#         c_alive = True
#         c_active = True
#         c_status = 'В норме'
#
#         c_race = Race(self.race, data_manager=self.data_manager)
#
#         c_vital_damage = 100-self.vital_damage()
#
#         c_blood_lose = (self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {self.character_id}')[0].get('blood_lost')/c_race.Blood)*100
#
#         c_pain = self.calculate_total_pain()
#
#         max_pain = c_race.PainLimit
#
#         if c_pain >= max_pain:
#             c_active = False
#             c_status = 'В отключке'
#
#         if 100 > c_vital_damage >= 85:
#             c_active = False
#             c_status = 'В коме'
#         elif c_vital_damage >= 95:
#             c_alive = False
#
#         if 60 <= c_blood_lose < 80:
#             c_active = False
#             c_status = 'В отключке'
#         elif c_blood_lose >= 80:
#             c_alive = False
#
#         if not c_alive:
#             c_active = False
#             c_status = 'Мертв'
#
#
#         return {'status': c_status,
#                 'alive': c_alive,
#                 'active': c_active}
#
#     def __alive__(self):
#         c_status = self.vital_signs()['alive']
#         if c_status:
#             return True
#         else:
#             return False
#
#     def __pain__(self):
#         c_pain = self.calculate_total_pain()
#
#         if c_pain == 0:
#             output = 'Нет'
#         elif 1 <= c_pain < 15:
#             output = 'Незначительная'
#         elif 15 <= c_pain < 40:
#             output = 'Ощутимая'
#         elif 40 <= c_pain < 80:
#             output = 'Нестерпимая'
#         elif 80 <= c_pain < 100:
#             output = 'Невыносимая'
#         else:
#             output = 'Болевой шок'
#
#         return output
#
#     def __vital__(self):
#         c_vital = self.vital_damage()
#         print(c_vital)
#
#         if c_vital <= 10:
#             output = 'Отсутствует'
#         elif 10 < c_vital <= 35:
#             output = 'Опасно низкая'
#         elif 35 < c_vital <= 75:
#             output = 'Нестабильная'
#         elif c_vital < 75:
#             output = 'Стабильная'
#         else:
#             output = 'Стабильная'
#
#         return output
#
#     def __bleed__(self):
#         from ArbRaces import Race
#         c_bleed = self.calculate_total_bleeding()
#         c_blood = Race(self.race).Blood
#
#         c_loss = (c_bleed/c_blood)*100
#
#
#         if c_loss == 0:
#             c_time = 0
#         else:
#             c_time = round(24/(c_loss/100))
#
#         if c_bleed == 0:
#             output = 'Отсутствует'
#         elif c_loss < 50:
#             output = 'Неопасное'
#         elif 50 <= c_loss < 100:
#             output = 'Ощутимое'
#         elif 100 <= c_loss < 300:
#             output = f'Опасное ({c_time}ч. до смерти)'
#         elif 300 <= c_loss < 800:
#             output = f'Обильное ({c_time}ч. до смерти)'
#         elif 800 <= c_loss < 1200:
#             output = f'Экстремальное ({c_time}ч. до смерти)'
#         else:
#             output = f'Смертельное ({c_time}ч. до смерти)'
#
#         return output
#
#     def __bloodloss__(self):
#         from ArbRaces import Race
#         c_loss = (self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.character_id}')[0].get('blood_lost')/Race(self.race).Blood)*100
#
#         if c_loss == 0:
#             output = 'Отсутствует'
#         elif 0 < c_loss < 20:
#             output = 'Слабая кровопотеря'
#         elif 20 <= c_loss < 45:
#             output = 'Легкая кровопотеря'
#         elif 45 <= c_loss < 60:
#         