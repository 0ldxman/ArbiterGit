import math
import pprint
import random

from ArbDatabase import DataManager, DataModel, DataDict, DataList
from ArbItems import Item
from ArbAmmo import Bullet, Ammunition, Grenade
from ArbDamage import Damage


class WeaponInit(DataModel):
    def __init__(self, weapon_id:str, **kwargs):
        self.weapon_id = weapon_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('WEAPONS', f'id = "{self.weapon_id}"', data_manager=self.data_manager)
        self.label = self.get('name', 'Неизвестное оружие')
        self.weapon_class = self.get('class', None)
        self.slot = self.get('slot', 0)
        self.action_points = self.get('ap', 0)
        self.noise = self.get('noise', 0)
        self.attacks = self.get('attacks', 0)
        self.cost = self.get('cost', 0)
        self.reload_ap_cost = self.get('reload_cost', 0)

    def __repr__(self):
        return f'Weapon.{self.weapon_id}.{self.weapon_class}'


class RangeWeapon(WeaponInit):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        WeaponInit.__init__(self, id, data_manager=self.data_manager)
        range_data = DataDict('WEAPONS', f'id = "{self.weapon_id}"', data_manager=self.data_manager)
        self.mag_capacity = range_data.get('mag', 0)
        self.fire_rate = range_data.get('mode', 0)
        self.accuracy = range_data.get('accuracy', 0)
        self.caliber = range_data.get('caliber','')

    def get_available_ammo(self):
        c_bullets = [bullet.get('id') for bullet in self.data_manager.select_dict('AMMO', filter=f'caliber = "{self.caliber}"')]
        return c_bullets

    def random_range_damage(self, ammo_id:str = None):
        ammo = Bullet(random.choice(self.get_available_ammo()), data_manager=self.data_manager) if not ammo_id else Bullet(ammo_id, data_manager=self.data_manager)
        return ammo.process_bullet()

    def shot_difficulty(self, range: float, cover: float, **kwargs):
        range = abs(range)

        range_factor = range * 0.29 # 0.45
        cover_factor = cover * 0.25
        base_difficulty = 100 - self.accuracy * kwargs.get('endurance', 1)

        total_difficulty = base_difficulty + range_factor + cover_factor

        return round(total_difficulty, 2)



class MeleeWeapon(WeaponInit):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        WeaponInit.__init__(self, id, data_manager=self.data_manager)

        self.melee_attacks = self.attacks if self.weapon_class == 'ColdSteel' else 1

    def get_melee_damage(self):
        melee_damage = DataList('WEAPON_DAMAGE', f'weapon_id = "{self.weapon_id}"', data_manager=self.data_manager)
        return melee_damage


class Weapon(Item, MeleeWeapon, RangeWeapon):
    def __init__(self, item_id:int, **kwargs):
        super().__init__(item_id, data_manager=kwargs.get('data_manager', DataManager()))
        MeleeWeapon.__init__(self, self.type, data_manager=self.data_manager)
        RangeWeapon.__init__(self, self.weapon_id, data_manager=self.data_manager)

    def get_weapon_endurance(self):
        return self.get_endurance() if self.endurance else 0

    def shot_difficulty(self, range: float, cover: float, **kwargs):
        range = abs(range)

        range_factor = range * 0.29 # 0.45
        cover_factor = cover * 0.25
        base_difficulty = 100 - self.accuracy * self.get_weapon_endurance()

        total_difficulty = base_difficulty + range_factor + cover_factor

        return round(total_difficulty, 2)

    def get_magazine_data(self):
        if not self.data_manager.check('ITEMS_BULLETS', f'id = "{self.item_id}"'):
            query = {'id': self.item_id,
                     'bullets': 0,
                     'ammo_id': None}
            self.data_manager.insert('ITEMS_BULLETS', query)

        return DataDict('ITEMS_BULLETS', f'id = "{self.item_id}"', data_manager=self.data_manager)

    def get_magazine_capacity(self):
        return self.mag_capacity

    def reload(self, ammo_id: str = None):
        if not self.can_reload():
            return False

        capacity = self.get_magazine_capacity()
        query = {'bullets': capacity}
        self.data_manager.update('ITEMS_BULLETS', query, f'id = {self.item_id}')

        if ammo_id:
            available_ammo = self.get_available_ammo()
            if ammo_id in available_ammo:
                query = {'ammo_id': ammo_id}
                self.data_manager.update('ITEMS_BULLETS', query, f'id = {self.item_id}')

        return True

    def get_current_bullets(self):
        magazine = self.get_magazine_data()
        return magazine.get('bullets', 0)

    def get_current_ammotype(self):
        magazine = self.get_magazine_data()
        return magazine.get('ammo_id', None)

    def can_reload(self):
        magazine = self.get_magazine_data()
        return magazine.get('out_of_ammo') != 1

    def can_shoot(self):

        if self.weapon_class == 'ColdSteel':
            print('Холодное оружие не может стрелять.')
            return False

        if self.get_current_bullets() == 0:
            print('Нет пули в магазине.')
            return False

        if self.get_current_ammotype() is None:
            print('Нет снаряженного магазина в текущем оружии.')
            return False

        else:
            return self.get_current_bullets()

    def fire(self):
        if not self.can_shoot():
            return []

        current_ammo = Bullet(self.get_current_ammotype(), data_manager=self.data_manager)

        return current_ammo.process_bullet()

    def melee_attack(self):
        damage_info = self.get_melee_damage()
        damage_list = []
        for damage in damage_info:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 - damage.get('critical_chance', 1) else 1

            damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
            if self.material:
                damage_value *= self.material.weapon_factor
            total_damage = Damage(damage_value, damage.get('damage_type', 'Hit'), damage.get('penetration'), damage.get('blocked_type'), self.label, data_manager=self.data_manager)

            damage_list.append(total_damage)
        return damage_list

    def use_bullet(self, n: int):
        current_bullets = self.get_current_bullets()
        self.data_manager.update('ITEMS_BULLETS', {'bullets': current_bullets - n}, f'id = {self.item_id}')

    def shot_noise(self):
        return self.noise

    def melee_noise(self):
        return self.noise


class HandGrenade(Item, Grenade):
    def __init__(self, item_id:int, **kwargs):
        super().__init__(item_id, data_manager=kwargs.get('data_manager', DataManager()))
        self.grenade_type = self.type
        super(Grenade, self).__init__(self.type, data_manager=self.data_manager)


class TrapInit(DataModel):
    def __init__(self, id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        DataModel.__init__(self, 'TRAPS_INIT', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестная ловушка')
        self.visibility = self.get('visibility', 100)
        self.ammo_id = self.get('ammo_id', None)
        self.activate_chance = self.get('activate_chance', 0) if self.get('activate_chance', None) is not None else 0

    def get_damage_info(self):
        if self.ammo_id:
            return Bullet(self.ammo_id, data_manager=self.data_manager)
        else:
            return None


class Trap(TrapInit):
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.trap_id = id
        data = self.get_combat_data()
        self.trap_type = data.get('type')
        self.buff = data.get('buff', 0) if data.get('buff', None) is not None else 0

        self.battle_id = data.get('battle_id', None)
        self.layer_id = data.get('layer_id', None)

        super().__init__(self.trap_type, data_manager=kwargs.get('data_manager', DataManager()))

    def get_combat_data(self):
        if self.data_manager.check('BATTLE_TRAPS', f'trap_id = {self.trap_id}'):
            return self.data_manager.select_dict('BATTLE_TRAPS', filter=f'trap_id = {self.trap_id}')[0]
        else:
            return {}

    def check_activation(self, character_analysis:int, character_movement:int) -> bool:
        character_score = (character_analysis + character_movement)/2
        trap_score = self.activate_chance + self.buff

        if character_score > trap_score:
            self.delete()
            return False
        else:
            return True

    def delete(self):
        self.data_manager.delete('BATTLE_TRAPS', f'trap_id = {self.trap_id}')

    def explode(self) -> list[Damage]:
        damage_list = self.get_damage_info().process_bullet()
        self.delete()

        return damage_list

    def __repr__(self):
        return f'Trap.{self.trap_type}[id:{self.trap_id}, battle:{self.battle_id}, layer:{self.layer_id}]'


class RaceAttack(DataModel):
    def __init__(self, attack_id:str, **kwargs):
        self.attack_id = attack_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'RACES_MELEE', f'id = "{self.attack_id}"', data_manager=self.data_manager)
        self.label = self.get('name', 'Неизвестный удар') if self.get('name', None) is not None else 'Неизвестный удар'
        self.race = self.get('race', 'Неизвестная раса')
        self.part_id = self.get('part_id', None)
        self.range = self.get('range', 0) if self.get('range', None) is not None else 0
        self.attacks = self.get('attacks', 0)
        self.ap_cost = self.get('ap_cost', 0)

    def get_damage_info(self):
        melee_damage = DataList('RACES_DAMAGE', f'id = "{self.attack_id}"', data_manager=self.data_manager)
        return melee_damage

    def attack_difficulty(self, range: float, cover: float, **kwargs):
        range = abs(range)

        range_factor = range * 0.29  # 0.45
        cover_factor = cover * 0.25
        base_difficulty = 100 - self.range

        total_difficulty = base_difficulty + range_factor + cover_factor

        return round(total_difficulty, 2)


    def attack(self):
        from ArbRaces import Race
        damage_info = self.get_damage_info()
        damage_list = []
        for damage in damage_info:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 - damage.get(
                'critical_chance', 1) else 1

            damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
            total_damage = Damage(damage_value, damage.get('damage_type', 'Hit'), damage.get('penetration'),
                                  damage.get('blocked_type'), f'{Race(self.race, data_manager=self.data_manager).label.lower()} {self.label.lower()}', data_manager=self.data_manager)

            damage_list.append(total_damage)
        return damage_list