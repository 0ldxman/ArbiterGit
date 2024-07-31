import pprint

from ArbDatabase import DataManager
from ArbOrgs import Organization
from ArbCharacters import Character
from ArbLocations import Location
from dataclasses import dataclass


class BattleCampaign:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.get_battle_campaign_data()
        self.label = data.get('label', 'Неизвестная кампания')
        self.stage = data.get('stage', 1)
        self.last_stage = data.get('last_stage', None)
        self.target = data.get('target', None)
        self.dp_needed = data.get('dp_need', None)

    def get_battle_campaign_data(self):
        if self.data_manager.check('BATTLEFIELD_INIT', f'id = {self.id}'):
            return self.data_manager.select_dict('BATTLEFIELD_INIT', filter=f'id = {self.id}')[0]
        else:
            return {}


class Unit: # информация о юните
    def __init__(self, id: str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.get_unit_data()
        self.label = data.get('label', 'Неизвестный юнит')
        self.type = data.get('type', 'Пехота')
        self.type_class = data.get('class', 'Регулярный')
        self.advancement = data.get('advancement', 1) if data.get('advancement') else 1
        self.experience = data.get('exp', 1) if data.get('exp') else 1
        self.spirit_influence = data.get('spirit', 1) if data.get('spirit') else 1

        self.attack = data.get('attack', 0) if data.get('attack') else 0
        self.defence = data.get('defence', 0) if data.get('defence') else 0
        self.damage = data.get('damage', 0) if data.get('damage') else 0
        self.hp = data.get('hp', 1) if data.get('hp') else 1
        self.movement = data.get('movement', 0) if data.get('movement') else 0
        self.recon = data.get('recon', 0) if data.get('recon') else 0

        self.target_chance = data.get('target_chance', 1) if data.get('target_chance') else 1

    def get_unit_data(self):
        if self.data_manager.check('UNITS', f'id = "{self.id}"'):
            return self.data_manager.select_dict('UNITS', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def __repr__(self):
        return f'UnitType.{self.id}'


class Division: # Подразделение
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.get_division_data()
        self.label = data.get('label', 'Неизвестное подразделение')
        self.org_id = data.get('org', None)
        self.commander_id = data.get('commander', None)
        self.location = data.get('loc', None)

    def get_division_data(self):
        if self.data_manager.check('DIVISION_INIT', f'id = {self.id}'):
            return self.data_manager.select_dict('DIVISION_INIT', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_org(self):
        return Organization(self.org_id, data_manager=self.data_manager)

    def get_commander(self):
        return Character(self.commander_id, data_manager=self.data_manager)

    def get_location(self):
        return Location(self.location, data_manager=self.data_manager)

    def get_units_data(self):
        return self.data_manager.select_dict('DIVISION_UNITS', filter=f'id = {self.id}')

    def get_units_types(self):
        return [Unit(unit_id.get('unit_id'), data_manager=self.data_manager) for unit_id in self.get_units_data()]

    def get_units(self):
        return {unit_data.get('unit_id'): UnitsGroup(self.id, Unit(unit_data.get('unit_id'), data_manager=self.data_manager), unit_data.get('value')) for unit_data in self.get_units_data()}

    def get_total_stats(self):
        total_units = self.get_units()

    def get_division_stats(self):
        division_stats = DivisionAttributes(division_id=self.id, units=self.get_units())
        return division_stats


@dataclass()
class CombatAttributes:
    attack: int
    defence: int
    damage: int
    hp: int
    movement: int
    recon: int


@dataclass()
class UnitsGroup:
    division_id: int
    unit_type: Unit
    value: int

    def get_team_moral(self, data_manager: DataManager = None):
        db = data_manager or DataManager()
        division_org = db.select_dict('DIVISION_INIT', filter=f'id = {self.division_id}')[0].get('org')
        if db.check('BATTLEFIELD_TEAMS', f'org = "{division_org}"'):
            return db.select_dict('BATTLEFIELD_TEAMS', filter=f'org = "{division_org}"')[0].get('spirit')
        else:
            return 50

    def moral_buff(self):
        moral = self.get_team_moral()
        basic_moral_buff = (moral / 50) * self.unit_type.spirit_influence
        return basic_moral_buff

    def exp_buff(self):
        exp = self.unit_type.experience
        return exp

    def advance_buff(self):
        advancement = self.unit_type.advancement
        return advancement

    def get_total_stats(self):
        moral_buff = self.moral_buff()

        attack = self.unit_type.attack * self.value * moral_buff
        defence = self.unit_type.defence * self.value * moral_buff
        damage = self.unit_type.damage * self.value * moral_buff
        hp = self.unit_type.hp * self.value
        movement = self.unit_type.movement * self.value * moral_buff
        recon = self.unit_type.recon * self.value

        combat_stats = CombatAttributes(attack=attack, defence=defence, damage=damage, hp=hp, movement=movement, recon=recon)
        return combat_stats

    def __repr__(self):
        return f'{self.unit_type.id}s (value={self.value}, division={self.division_id})'


@dataclass()
class DivisionAttributes:
    division_id: int
    units: dict[UnitsGroup]

    def __post_init__(self):
        self.stats = self.get_total_stats()

    def get_total_units_value(self):
        return sum(unit.value for unit in self.units.values())

    def get_tactic_buffs(self):
        pass

    def get_total_stats(self):
        values = self.get_total_units_value()

        total_attack = sum(unit.get_total_stats().attack for unit in self.units.values())
        total_defence = sum(unit.get_total_stats().defence for unit in self.units.values())
        total_damage = sum(unit.get_total_stats().damage for unit in self.units.values())
        total_hp = sum(unit.get_total_stats().hp for unit in self.units.values())
        total_movement = round(sum(unit.get_total_stats().movement for unit in self.units.values()) / values, 2)
        total_recon = round(sum(unit.get_total_stats().recon for unit in self.units.values()) / values, 2)

        total_combat_stats = CombatAttributes(attack=total_attack, defence=total_defence, damage=total_damage, hp=total_hp, movement=total_movement, recon=total_recon)

        return total_combat_stats

    def compare_attack(self, defense:float):
        return self.stats.attack / defense if defense else 2

    def compare_defence(self, attack:float):
        return attack / self.stats.defence

    def get_total_damage(self, defense: float):
        return self.stats.damage * self.compare_attack(defense)

pprint.pprint(Division(1).get_division_stats().__dict__)

