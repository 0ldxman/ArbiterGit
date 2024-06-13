# -*- coding: utf-8 -*-
from dataclasses import dataclass
from ArbDatabase import DataManager
from ArbDamage import Damage, Penetration
from ArbClothes import Clothes
from ArbAmmo import Grenade
from ArbWeapons import Weapon, HandGrenade
from ArbHealth import LocalBodyPart, Body, BodyPart
from ArbSkills import CharacterAttributes
from ArbCharacters import Race, Character
from ArbRoll import TargetRoll
import random


class NaturalConditions:
    pass


@dataclass()
class TargetData:
    id: int | None
    distance: int
    cover: int
    size: float
    armors: dict
    race: str

    def return_main_part(self, data_manager: DataManager = None):
        data_manager = DataManager() if not DataManager else data_manager
        if self.id:
            return Body(self.id, data_manager=data_manager).parent_part
        else:
            return Race(self.race, data_manager=data_manager).parent_part


class CombatManager:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())

    def check_if_npc(self, target_id:int):
        c_owner = self.data_manager.select_dict('CHARS_INIT', filter=f'id = {target_id}')[0].get('owner', None)
        if c_owner is not None:
            return c_owner
        else:
            return None

    def pack_enemy_attributes(self, **kwargs):
        enemy_id = kwargs.get('enemy_id', None)
        if enemy_id:
            enemy_cover = kwargs.get('enemy_cover', 0)
            enemy_distance = kwargs.get('enemy_distance', 100)
            enemy_size = kwargs.get('enemy_size', 1)
            enemy_armors = {}
        else:
            enemy_cover = kwargs.get('enemy_cover', 0)
            enemy_distance = kwargs.get('enemy_distance', 100)
            enemy_size = kwargs.get('enemy_size', 1)
            enemy_armors = kwargs.get('enemy_armors', {})

        return TargetData(enemy_id, enemy_distance, enemy_cover, enemy_size, enemy_armors, kwargs.get('enemy_race', 'Human'))

    def target_attributes(self, target_id:int):
        return CharacterAttributes(target_id, data_manager=self.data_manager)

    def target_skill_roll(self, user_id:int, skill:str):
        c_attr = self.target_attributes(user_id)
        return c_attr.roll_skill(skill)

    def current_weapons_id(self, user_id:int, item_id:int=None) -> list:
        c_weapons_data = self.data_manager.select_dict('CHARS_INVENTORY', filter=f'character_id = {user_id} AND slot = "Оружие"')

        weapons = []
        for i in c_weapons_data:
            weapons.append(i.get('item_id'))

        if item_id is None:
            return weapons
        elif item_id in weapons:
            return [item_id]
        else:
            return []

    def select_random_part(self, **kwargs):
        from ArbCharacters import Race

        enemy_id = kwargs.get('enemy_id', None)
        if enemy_id:
            enemy_main_part = Body(enemy_id, data_manager=self.data_manager).parent_part
        else:
            enemy_main_part = Race(kwargs.get('enemy_race', 'Human'), data_manager=self.data_manager).parent_part

        c_part = BodyPart(enemy_main_part, data_manager=self.data_manager) if kwargs.get('enemy_id', None) is None else LocalBodyPart(enemy_id, enemy_main_part, data_manager=self.data_manager)

        return c_part.choose_random_part()

    def has_melee_weapon(self, target_id:int):
        c_weapons_data = self.data_manager.select_dict('CHARS_INVENTORY',filter=f'character_id = {target_id} AND slot = "Оружие"')

        melee_weapons = []
        for i in c_weapons_data:
            if Weapon(i.get('item_id')).Class == 'ColdSteel':
                melee_weapons.append(i.get('item_id'))

        return melee_weapons

    def calculate_total_damage(self, damages_dict: dict, target: int =None, **kwargs) -> list[dict]:
        c_damages = damages_dict

        random_part, parent_part = self.select_random_part(enemy_id=target, enemy_race=kwargs.get('race', 'Human')) if not 'part_id' in kwargs else (LocalBodyPart(target, kwargs.get('part_id'), data_manager=self.data_manager), None)
        print(kwargs.get('part_id', None), random_part, parent_part)

        total_damage = []

        for damage in c_damages:
            damage_bonus = kwargs.get('damage_bonus', 0) if kwargs.get('damage_bonus', None) is not None else 0
            damage_crit = kwargs.get('crit_damage', 1) if kwargs.get('crit_damage', None) is not None else 1
            penetration_bonus = kwargs.get('penetration_bonus', 0) if kwargs.get('penetration_bonus', None) is not None else 0
            penetration_crit = kwargs.get('crit_penetration', 1) if kwargs.get('crit_penetration', None) is not None else 1

            c_penetration = damage.get('penetration') * penetration_crit + penetration_bonus
            c_damage = damage.get('damage') * damage_crit + damage_bonus

            c_slot = random_part.Slot if parent_part is None else parent_part.Slot

            if target:
                n_damage = BallisticSimulation(target, data_manager=self.data_manager).initiate(c_slot, c_penetration, c_damage)
            else:
                n_damage = BallisticSimulation(target, data_manager=self.data_manager).initiate(c_slot, c_penetration, c_damage, armors_protection=kwargs.get('armors_protection', {}), armors_id=kwargs.get('armors_id', {}))

            if n_damage is not None:
                total_damage.append({'part_id': random_part.ID,
                                     'damage': n_damage})

        return total_damage

    def recive_damage(self, target_id:int, total_damage:list, *, apply_effect:bool=False):
        for damage in total_damage:
            self.write_damage_in_database(target_id, part_id=damage.get('part_id'), damage_list=damage.get('damage'), apply_effect=apply_effect)

    def write_damage_in_database(self, target_id:int, *, part_id:str, damage_list: list[Damage] | Damage, apply_effect:bool=False) -> None:
        part = LocalBodyPart(target_id, part_id, data_manager=self.data_manager)
        part.apply_damage(damage_list, apply_effect)

        self.data_manager.logger.info(f'Персонаж {target_id} получил урон {damage_list}')

    def check_skill(self, skill:str, target_id:int=None, difficulty:int | float=None):
        if target_id:
            return CharacterAttributes(target_id, data_manager=self.data_manager).roll_skill(skill, difficulty=difficulty)
        else:
            return random.randint(0, 100)


class RangeAttack:
    def __init__(self, attacker_id:int, target_id:int=None, **kwargs):
        self.attacker = attacker_id
        self.target = target_id

        self.data_manager = kwargs.get('data_manager', DataManager())
        self.combat_manager = CombatManager(data_manager=self.data_manager)

        self.enemy_attributes = self.get_enemy_attributes(kwargs.get('enemy_attributes', {}))

    def get_enemy_attributes(self, enemy_attributes:dict) -> TargetData:
        e_id = self.target
        e_distance = enemy_attributes.get('distance', 0)
        e_cover = enemy_attributes.get('cover', 0)
        e_size = enemy_attributes.get('size', 1)
        e_armors = enemy_attributes.get('armors', {})
        e_race = enemy_attributes.get('race', {})

        return self.combat_manager.pack_enemy_attributes(enemy_id= e_id,
                                                  enemy_distance= e_distance,
                                                  enemy_cover= e_cover,
                                                  enemy_size= e_size,
                                                  enemy_armors= e_armors,
                                                  enemy_race= e_race)

    def check_if_npc(self):
        return CombatManager(data_manager=self.data_manager).check_if_npc(self.attacker)

    def get_shot_difficulty(self, weapon_id:int):
        distance = self.enemy_attributes.distance
        cover = self.enemy_attributes.cover
        size = self.enemy_attributes.size
        horz_factor = None
        total_buff = None
        total_modifier = None

        result = Weapon(weapon_id, data_manager=self.data_manager).AccuracyCheck(distance, cover, size,
                                                                                 horz_factor=horz_factor,
                                                                                 total_buff=total_buff,
                                                                                 total_modifier=total_modifier)

        return result

    def get_current_bullets(self, weapon_id:int=None):
        from ArbItems import Item

        if self.check_if_npc() is None:
            return -1, None

        c_weapon = weapon_id
        if c_weapon is None:
            return 0, None

        if self.data_manager.check('CHARS_MAGAZINE', f'weapon_id = {c_weapon}') is None:
            return 0, None

        c_bullets_id = self.data_manager.select_dict('CHARS_MAGAZINE', filter=f'weapon_id = {c_weapon}')[0].get('magazine_id', None)
        if c_bullets_id:
            return Item(c_bullets_id, data_manager=self.data_manager).Value, c_bullets_id

    def get_current_ammo(self, weapon_id:int):
        from ArbAmmo import Bullet
        from ArbWeapons import WeaponAmmo

        c_bullets_id = self.get_current_bullets(weapon_id)[1]

        if c_bullets_id is None:
            c_bullets = [bullet.get('id') for bullet in self.data_manager.select_dict('AMMO', filter=f'caliber = "{Weapon(weapon_id, data_manager=self.data_manager).Caliber}"')]
            return Bullet(random.choice(c_bullets), data_manager=self.data_manager)
        else:
            return WeaponAmmo(weapon_id, data_manager=self.data_manager).get_ammo_type()

    def calculate_total_attacks(self, weapon_id:int=None, fire_rate:int=None):
        c_weapon = Weapon(weapon_id, data_manager=self.data_manager)

        current_bullets = self.get_current_bullets(weapon_id)

        if c_weapon.Mode == 1:
            fire_rate = 1
        elif c_weapon.Mode == 2:
            fire_rate = 3 if not fire_rate else fire_rate
        elif c_weapon.Mode == 3:
            fire_rate = c_weapon.Attacks if not fire_rate else fire_rate
        else:
            fire_rate = c_weapon.Attacks

        total_attacks = min(fire_rate, current_bullets[0]) if current_bullets[0] > 0 else fire_rate

        return total_attacks

    def initiate(self, weapon_id:int=None) -> tuple:
        c_weapons_id = self.combat_manager.current_weapons_id(self.attacker, weapon_id)

        if c_weapons_id is None:
            return (None, None, None)
        else:
            c_weapon = Weapon(random.choice(c_weapons_id), data_manager=self.data_manager)

        enemy_id = self.target
        total_damage = []
        damage_for_cover = 0
        current_difficulty = self.get_shot_difficulty(c_weapon.ID)
        total_attacks = self.calculate_total_attacks(c_weapon.ID)
        c_current_ammo = self.get_current_ammo(c_weapon.ID)


        for attack in range(total_attacks):
            c_damages = c_current_ammo.process_bullet()
            roll = self.combat_manager.check_skill(c_weapon.Class, self.attacker, difficulty=current_difficulty)
            c_roll = roll

            if c_roll:
                n_damage = self.combat_manager.calculate_total_damage(c_damages, enemy_id)
                total_damage += n_damage
            else:
                damage_for_cover += c_damages['damage'].Damage

        if total_damage and enemy_id:
            self.combat_manager.recive_damage(enemy_id, total_damage)

        c_weapon_loud = c_weapon.total_noise()

        return total_damage, total_attacks, c_weapon_loud, damage_for_cover


class MeleeAttack:
    def __init__(self, attacker_id:int, target_id:int=None, **kwargs):
        self.attacker = attacker_id
        self.target = target_id

        self.data_manager = kwargs.get('data_manager', DataManager())
        self.combat_manager = CombatManager(data_manager=self.data_manager)

        self.enemy_attributes = self.get_enemy_attributes(kwargs.get('enemy_attributes', {}))

    def get_enemy_attributes(self, enemy_attributes:dict) -> TargetData:
        e_id = self.target
        e_distance = enemy_attributes.get('distance', 0)
        e_cover = enemy_attributes.get('cover', 0)
        e_size = enemy_attributes.get('size', 1)
        e_armors = enemy_attributes.get('armors', {})
        e_race = enemy_attributes.get('race', {})

        return self.combat_manager.pack_enemy_attributes(enemy_id= e_id,
                                                  enemy_distance= e_distance,
                                                  enemy_cover= e_cover,
                                                  enemy_size= e_size,
                                                  enemy_armors= e_armors,
                                                  enemy_race= e_race)

    def calculate_penetration_bonus(self):
        combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)
        characteristic_bonus = (max(combat.check_characteristic('Ловкость'), combat.check_characteristic('Сила')) - 20) / 2
        armors_bonus = 0

        return characteristic_bonus + armors_bonus

    def calculate_damage_bonus(self):
        combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)
        characteristic_bonus = (combat.check_characteristic('Сила') - 20) / 2
        armors_bonus = 0

        return int(characteristic_bonus + armors_bonus)

    def calculate_crit_bonus(self):
        pass

    def check_skill_issues(self):
        self_combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)

        if self.target:
            enemy_combat = CharacterAttributes(self.target, data_manager=self.data_manager)
            enemy_skill = 'ColdSteel' if self.combat_manager.has_melee_weapon(self.target) else 'MartialArms'
            e_roll = enemy_combat.roll_skill(enemy_skill)
        else:
            e_roll = random.randint(0, 100)

        c_roll = self_combat.roll_skill('ColdSteel', difficulty=e_roll)[0]

        return c_roll

    def calculate_total_attacks(self, weapon_id:int):
        c_weapon = Weapon(weapon_id, data_manager=self.data_manager)
        c_attacks = c_weapon.melee_attacks()

        return c_attacks

    def initiate(self, weapon_id: int = None):
        c_weapons_id = self.combat_manager.current_weapons_id(self.attacker, weapon_id)

        if c_weapons_id is None:
            return (None, None, None)
        else:
            current_weapon_id = random.choice(c_weapons_id)
            c_weapon = Weapon(current_weapon_id, data_manager=self.data_manager)

        enemy_id = self.target
        total_damage = []
        c_attacks = self.calculate_total_attacks(current_weapon_id)

        c_penetration_bonus = self.calculate_penetration_bonus()
        c_damage_bonus = self.calculate_damage_bonus()

        for attack in range(c_attacks):
            c_roll = self.check_skill_issues()
            if c_roll:
                c_damages = c_weapon.melee_damage()
                n_damage = self.combat_manager.calculate_total_damage(c_damages, enemy_id, penetration_bonus=c_penetration_bonus, damage_bonus=c_damage_bonus)
                total_damage += n_damage

        if total_damage and enemy_id:
            self.combat_manager.recive_damage(enemy_id, total_damage)

        c_weapon_loud = c_weapon.total_noise()

        return total_damage, c_attacks, c_weapon_loud


class BodyPartAttack:
    def __init__(self, attacker_id:int, target_id:int=None, **kwargs):
        self.attacker = attacker_id
        self.target = target_id

        self.data_manager = kwargs.get('data_manager', DataManager())
        self.combat_manager = CombatManager(data_manager=self.data_manager)

        self.enemy_attributes = self.get_enemy_attributes(kwargs.get('enemy_attributes', {}))

    def get_enemy_attributes(self, enemy_attributes:dict) -> TargetData:
        e_id = self.target
        e_distance = enemy_attributes.get('distance', 0)
        e_cover = enemy_attributes.get('cover', 0)
        e_size = enemy_attributes.get('size', 1)
        e_armors = enemy_attributes.get('armors', {})
        e_race = enemy_attributes.get('race', {})

        return self.combat_manager.pack_enemy_attributes(enemy_id= e_id,
                                                  enemy_distance= e_distance,
                                                  enemy_cover= e_cover,
                                                  enemy_size= e_size,
                                                  enemy_armors= e_armors,
                                                  enemy_race= e_race)

    def calculate_penetration_bonus(self):
        combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)
        characteristic_bonus = (max(combat.check_characteristic('Ловкость'), combat.check_characteristic('Сила')) - 20) / 2
        armors_bonus = 0

        return characteristic_bonus + armors_bonus

    def calculate_damage_bonus(self):
        combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)
        characteristic_bonus = (combat.check_characteristic('Сила') - 20) / 2
        armors_bonus = 0

        return characteristic_bonus + armors_bonus

    def return_attack(self, attack_id:str=None):
        from ArbHealth import RaceAttack

        c_body = Body(self.attacker, data_manager=self.data_manager)

        if attack_id is not None:
            if not attack_id in c_body.available_attacks():
                return None
            else:
                c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
                c_body_part = c_body.part_of_attack(attack_id)
        else:
            if not c_body.available_attacks():
                return None
            else:
                attack_id = random.choice(c_body.available_attacks())
                c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
                c_body_part = c_body.part_of_attack(attack_id)

        return attack_id, c_attack, c_body_part

    def check_skill_issues(self):
        self_combat = CharacterAttributes(self.attacker, data_manager=self.data_manager)

        if self.target:
            enemy_combat = CharacterAttributes(self.target, data_manager=self.data_manager)
            enemy_skill = 'ColdSteel' if self.combat_manager.has_melee_weapon(self.target) else 'MartialArms'
            e_roll = enemy_combat.roll_skill(enemy_skill)
        else:
            e_roll = random.randint(0, 100)

        c_roll = self_combat.roll_skill('ColdSteel', difficulty=e_roll)[0]

        return c_roll

    def initiate(self, attack_id:str=None):

        attack_id, c_attack, c_body_part = self.return_attack(attack_id)

        total_damage = []
        enemy_id = self.target

        c_penetration_bonus = self.calculate_penetration_bonus()
        c_damage_bonus = self.calculate_damage_bonus()

        total_attacks = c_attack.main_data.get('attacks', 1)
        for i in range(total_attacks):

            c_roll = self.check_skill_issues()
            if c_roll:
                c_damages = c_body_part.part_attack(attack_id)
                n_damage = self.combat_manager.calculate_total_damage(c_damages, enemy_id,
                                                                      penetration_bonus=c_penetration_bonus,
                                                                      damage_bonus=c_damage_bonus)
                total_damage += n_damage

        if total_damage and enemy_id:
            self.combat_manager.recive_damage(enemy_id, total_damage)

        return total_damage, total_attacks


class Explosion:
    def __init__(self, targets_list:list, may_be_damaged:list=None, **kwargs):
        self.targets = targets_list
        self.may_be_damaged = may_be_damaged if may_be_damaged else []
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.combat_manager = CombatManager(data_manager=self.data_manager)

    def initiate(self, grenade: Grenade | HandGrenade, **kwargs):
        enemies_id = self.targets

        may_be_damaged = [TargetRoll(i, random.randint(1, 100)) for i in self.may_be_damaged]
        may_be_damaged.sort(key=lambda x: x.roll)

        total_damage = {}
        damage_for_cover = 0

        grenade_damage = grenade.detonate()
        main_damage = grenade_damage['main_damage']
        fragments_damage = grenade_damage['fragments_damage']
        fragments_value = grenade_damage['fragments_value']

        for dam in main_damage:
            damage_for_cover += dam.get('damage').Damage

        for target in enemies_id:
            c_damage = self.combat_manager.calculate_total_damage(main_damage, target)
            if target not in total_damage:
                total_damage[target] = c_damage
            else:
                total_damage[target] += c_damage

        for target in may_be_damaged:
            if fragments_value <= 0:
                break

            c_fragments = random.randint(0, fragments_value)
            fragments_value -= c_fragments
            current_fragments_damage = random.choices(fragments_damage, k=c_fragments)
            c_damage = self.combat_manager.calculate_total_damage(current_fragments_damage, target.id)
            if target.id not in total_damage:
                total_damage[target.id] = c_damage
            else:
                total_damage[target.id] += c_damage

        if total_damage:
            for target in total_damage:
                self.combat_manager.recive_damage(target, total_damage[target], apply_effect=True)

        c_loud = random.randint(50, 150)

        return total_damage, c_loud, damage_for_cover


class BallisticSimulation:
    def __init__(self, target_id:int | None, **kwargs):
        self.target_id = target_id
        self.data_manager = kwargs.get('data_manager', DataManager())

    def armors_id(self) -> dict:
        if not self.target_id:
            return {}

        if self.data_manager.check('CHARS_INVENTORY',filter=f'character_id = {self.target_id} AND slot != "Оружие"'):
            return {}

        c_equipment_data = self.data_manager.select_dict('CHARS_INVENTORY',filter=f'character_id = {self.target_id} AND slot != "Оружие"')
        equipment = {}

        for slot in c_equipment_data:
            c_slot = slot.get('slot')
            c_id = slot.get('item_id')
            c_layer = Clothes(c_id).Layer

            if c_slot not in equipment.keys():
                equipment[c_slot] = {c_layer: c_id}
            else:
                equipment[c_slot][c_layer] = c_id

        return equipment

    def armors_protection(self) -> dict:
        if not self.target_id:
            return {}

        if self.data_manager.check('CHARS_INVENTORY',filter=f'character_id = {self.target_id} AND slot != "Оружие"'):
            return {}

        c_equipment_data = self.data_manager.select_dict('CHARS_INVENTORY',filter=f'character_id = {self.target_id} AND slot != "Оружие"')
        equipment = {}

        for slot in c_equipment_data:
            c_slot = slot.get('slot')
            c_id = slot.get('item_id')
            c_layer = Clothes(c_id, data_manager=self.data_manager).Layer
            if c_slot not in equipment.keys():
                equipment[c_slot] = {c_layer: Clothes(c_id, data_manager=self.data_manager).armor_protection()}
            else:
                equipment[c_slot][c_layer] = Clothes(c_id, data_manager=self.data_manager).armor_protection()

        return equipment

    def initiate(self, c_slot:str, c_penetration: Penetration, damage: Damage, **kwargs) -> Damage | None:
        n_armors = kwargs.get('armors_protection', self.armors_protection())

        if c_slot not in n_armors:
            return damage

        c_armors = n_armors[c_slot]
        c_armors_id = kwargs.get('armors_id', self.armors_id()[c_slot])
        c_keys = sorted(c_armors.keys(), reverse=True)

        curent_penetration = c_penetration.value
        protection_type = c_penetration.name

        for layer, (armor_id, protection) in zip(c_keys, zip(c_armors_id.values(), c_armors.values())):
            c_protection = protection[protection_type].value

            if curent_penetration - c_protection > 0:
                curent_penetration -= c_protection
                Clothes(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.Damage, 2))
            else:
                Clothes(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.Damage * (curent_penetration / c_penetration.value), 2))
                return None

        if curent_penetration < c_penetration.value * 0.5:
            new_damage = int((curent_penetration / c_penetration.value) * damage.Damage)
            return Damage(new_damage, damage_type=c_penetration.blocked_type, root=damage.Root, data_manager=self.data_manager) if int(new_damage) > 0 else None
        else:
            return damage