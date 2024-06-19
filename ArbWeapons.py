import math

from ArbDatabase import *
from ArbItems import Item
from ArbAmmo import Bullet, Ammunition, Grenade
from ArbDamage import Damage, Penetration


class WeaponInit:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        weapon_data = self.fetch_data()
        self.weapon_id = id
        print(self.weapon_id)
        if weapon_data is None:
            self.Name = ''
            self.Class = ''
            self.Slot = -1
            self.ActionPoints = 0
            self.Noise = 0
            self.Attacks = 0
            self.Cost = 0
        else:
            self.Name = weapon_data.get('name','')
            self.Class = weapon_data.get('class', '')
            self.Slot = weapon_data.get('slot', -1)
            self.ActionPoints = weapon_data.get('ap', 0)
            self.Noise = weapon_data.get('noise', 0)
            self.Attacks = weapon_data.get('attacks', 0)
            self.Cost = weapon_data.get('cost', 0)
            self.ReloadAPCost = weapon_data.get('reload',0)

    def fetch_data(self) -> dict:
        return self.data_manager.select_dict('WEAPONS', '*', filter=f'id = "{self.weapon_id}"')[0]


class RangeWeapon(WeaponInit):
    def __init__(self, id: str, **kwargs):
        self.weapon_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(id, data_manager=self.data_manager)
        range_data = self.fetch_data_range()

        self.MagSpace = range_data.get('mag', 0)
        self.Mode = range_data.get('mode', '')
        self.Accuracy = range_data.get('accuracy',0)
        self.Caliber = range_data.get('caliber','')

    def fetch_data_range(self) -> dict:
        return self.data_manager.select_dict('WEAPONS', '*', filter=f'id = "{self.weapon_id}"')[0]

    def get_current_ammo(self):
        c_bullets = [bullet.get('id') for bullet in self.data_manager.select_dict('AMMO',filter=f'caliber = "{self.Caliber}"')]
        return Ammunition(random.choice(c_bullets), data_manager=self.data_manager)

    def range_damage(self):
        return self.get_current_ammo().fire()


class MeleeWeapon(WeaponInit):
    def __init__(self, id: str, **kwargs):
        self.weapon_id = id
        self.data_manager = kwargs.get('data_manager',DataManager())
        super().__init__(id, data_manager=self.data_manager)
        damage_data = self._get_damage_info()
        self.weapon_id = self.weapon_id
        self.melee_attack = self.Attacks if self.Class == 'ColdSteel' else 1

        if damage_data:
            self.damage_info = damage_data
        else:
            self.damage_info = []

    def _get_damage_info(self) -> list[dict]:

        damage_info = []
        weapon_damage_data = self.data_manager.select_dict('WEAPON_DAMAGE', '*', filter=f'weapon_id = "{self.weapon_id}"')

        for weapon_damage_entry in weapon_damage_data:
            damage_type = weapon_damage_entry.get('damage_type')
            min_damage = weapon_damage_entry.get('min_damage')
            max_damage = weapon_damage_entry.get('max_damage')
            critical_multiplier = weapon_damage_entry.get('critical_multiplier')
            critical_chance = weapon_damage_entry.get('critical_chance')
            blocked_type = weapon_damage_entry.get('blocked_type')
            penetration = weapon_damage_entry.get('penetration')

            damage_info.append({
                'damage_type': damage_type,
                'min_damage': min_damage,
                'max_damage': max_damage,
                'critical_multiplier': critical_multiplier,
                'critical_chance': critical_chance,
                'blocked_type': blocked_type,
                'penetration': penetration
            })

        return damage_info

    def melee_damage(self):
        damage_list = []
        for damage in self._get_damage_info():
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100*damage.get('critical_chance',1) else 1

            damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
            total_damage = Damage(damage_value, damage.get('damage_type', 'Hit'), root=self.Name, data_manager=self.data_manager)
            protection_type = self.data_manager.select_dict('DAMAGE_TYPE', filter=f'id = "{total_damage.Type.damage_id}"')[0].get('protection_type')

            c_pars = {'damage': total_damage,'penetration': Penetration(name=protection_type, value=damage.get('penetration'), blocked_type=damage.get('blocked_type'))}

            damage_list.append(c_pars)
        return damage_list

    def melee_attacks(self):
        if self.Class == 'ColdSteel':
            return self.Attacks
        else:
            return 1


class Weapon(Item, MeleeWeapon, RangeWeapon):
    def __init__(self, item_id:int,**kwargs):
        super().__init__(item_id, data_manager=kwargs.get('data_manager', DataManager()))
        self.weapon_id = self.Type
        super(MeleeWeapon, self).__init__(self.Type, data_manager=self.data_manager)
        super(RangeWeapon, self).__init__(self.Type, data_manager=self.data_manager)

    def AccuracyCheck(self, range: int, cover: int, size: float, *, horz_factor: float = None,
                      total_buff: float = None, total_modifier: float = None) -> float:
        """Calculate accuracy considering various factors for a ranged weapon shot."""

        # Adjust negative parameters according to specified conditions
        if range < 0:
            range *= -1

        if cover < 0:
            cover = 0

        if size <= 0:
            size = 1

        range_factor = range * 0.165 # 0.45

        if horz_factor:
            range_factor *= horz_factor

        accuracy_modifier = total_buff if total_buff else 0

        accuracy_factor = total_modifier if total_modifier else 1

        endurance_effect = 100 - (self.Endurance / 100) * self.Accuracy
        cover_effect = cover / size

        accuracy = (endurance_effect + range_factor + cover_effect + accuracy_modifier) * accuracy_factor
        print(self.Accuracy, endurance_effect, range_factor, cover_effect, accuracy_modifier)
        accuracy = max(0, accuracy)

        return accuracy

    def current_bullets(self):
        if self.data_manager.check('CHARS_EQUIPMENT',filter=f'item_id = {self.ID}'):
            return self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'item_id = {self.ID}')[0].get('bullets')
        else:
            return -1

    def get_current_ammo(self):
        if self.data_manager.check('CHARS_EQUIPMENT',filter=f'item_id = {self.ID}'):
            ammo = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'item_id = {self.ID}')[0]
            return Ammunition(ammo.get('ammo_id'), data_manager=self.data_manager)
        else:
            c_bullets = [bullet.get('id') for bullet in self.data_manager.select_dict('AMMO',filter=f'caliber = "{self.Caliber}"')]
            return Ammunition(random.choice(c_bullets), data_manager=self.data_manager)

    def possible_ammo_ids(self):
        c_bullets = [bullet.get('id') for bullet in self.data_manager.select_dict('AMMO', filter=f'caliber = "{self.Caliber}"')]
        return c_bullets

    def total_noise(self):
        basic_noise = self.Noise

        return basic_noise

    def range_damage(self):
        return self.get_current_ammo().fire()

    def get_range_attack_cost(self):
        if self.Class == 'ColdSteel':
            return math.inf
        else:
            return self.ActionPoints

    def get_melee_attack_cost(self):
        return self.ActionPoints

    def reload_bullets_count(self):
        space = self.MagSpace
        return space

    def can_be_reloaded(self):
        from ArbItems import Inventory

        owner = self.owner()
        all_ammos = self.data_manager.select_dict('AMMO', filter=f'caliber = "{self.Caliber}"')
        ammo_can_reload = [ammo['id'] for ammo in all_ammos]

        candidates = []
        character_inventory = Inventory.get_character_inventory(owner, self.data_manager)
        inventory = Inventory(character_inventory, data_manager=self.data_manager).get_items()
        for item in inventory:
            if item.Type in ammo_can_reload:
                candidates.append(item)
        if not candidates:
            return None

        return candidates

    def reload(self, ammo_id:int=None):
        from ArbItems import Inventory

        if self.Class == 'ColdSteel':
            return None
        elif self.owner() is None:
            return None

        owner = self.owner()
        all_ammos = self.data_manager.select_dict('AMMO',filter=f'caliber = "{self.Caliber}"')
        ammo_can_reload = [ammo['id'] for ammo in all_ammos]

        if ammo_id:
            if Item(ammo_id, data_manager=self.data_manager).Type in ammo_can_reload:
                bullets = Item(ammo_id, data_manager=self.data_manager).reload(self.reload_bullets_count())
                self.data_manager.update('CHARS_EQUIPMENT',{'bullets': bullets, 'ammo_id': Item(ammo_id, data_manager=self.data_manager).Type},filter=f'item_id = {self.ID}')
            else:
                return None
        else:
            candidates = []
            character_inventory = Inventory.get_character_inventory(owner, self.data_manager)
            inventory = Inventory(character_inventory, data_manager=self.data_manager).get_items()
            for item in inventory:
                if item.Type in ammo_can_reload:
                    candidates.append(item)
            if not candidates:
                return None

            print(candidates)
            candidate: Item = random.choice(candidates)
            bullets = candidate.reload(self.reload_bullets_count())

            self.data_manager.update('CHARS_EQUIPMENT', {'bullets': bullets, 'ammo_id': candidate.Type}, f'item_id = {self.ID}')
            return True





class WeaponAmmo:
    def __init__(self, weapon_id:int, *, data_manager=None):
        self.weapon_id = weapon_id
        self.data_manager = data_manager if data_manager else DataManager()
        c_data = self.fetch_data()
        if c_data:
            self.magazine_id = c_data.get('magazine_id',None)
            self.current_bullets = c_data.get('current_bullets', 0)

        c_weapon_data = self.load_weapon_data()
        self.max_capacity = c_weapon_data if c_weapon_data else 0

    def get_weapon(self):
        return Item(self.weapon_id)

    def get_current_magazine(self):
        return Item(self.magazine_id)

    def get_ammo_type(self):
        c_item = self.get_current_magazine()
        return Bullet(c_item.Type, data_manager=self.data_manager)

    def load_weapon_data(self):
        c_id = self.get_weapon().Type

        weapon_info = self.data_manager.select_dict('WEAPONS', columns='mag', filter=f'id = "{c_id}"')
        if weapon_info:
            max_capacity = weapon_info[0].get('mag', 0)
            return max_capacity
        else:
            self.data_manager.logger.error("Ошибка получения данных об оружии из таблицы WEAPONS")
            return None

    def fetch_data(self):
        # Загрузка данных об оружии из базы данных
        weapon_info = self.data_manager.select_dict('CHARS_MAGAZINE', columns='*', filter=f'weapon_id = {self.weapon_id}')[0]
        if weapon_info:
            return weapon_info
        else:
            self.data_manager.logger.error("Ошибка получения данных об оружии из таблицы WEAPONS")
            return None

    def reload_magazine(self, new_magazine_id: int = None) -> None:
        if not new_magazine_id:
            # Уменьшаем значение в таблице ITEMS для текущего снаряженного магазина
            current_magazine_item = self.data_manager.select_dict('ITEMS', columns='value', filter=f'id = {self.magazine_id}')
            if current_magazine_item:
                current_value = current_magazine_item[0].get('value', 0)
                self.current_bullets = min(self.max_capacity, current_value)
                new_value = max(0, current_value - self.current_bullets)
                self.data_manager.update('ITEMS', columns_values={'value': new_value}, filter=f'id = {self.magazine_id}')

                self.data_manager.logger.info(f'Магазин {self.magazine_id} перезаряжен в оружии {self.weapon_id}. Кол-во патронов {self.current_bullets}')
            else:
                self.data_manager.logger.error("Ошибка получения информации о текущем магазине из таблицы ITEMS")
        else:
            magazine_item = self.data_manager.select_dict('ITEMS', columns='value', filter=f'id = {new_magazine_id}')
            if magazine_item:
                bullets_value = magazine_item[0].get('value', 0)
                self.current_bullets = min(self.max_capacity, bullets_value)
                new_value = max(0, bullets_value - self.current_bullets)
                self.data_manager.update('ITEMS', columns_values={'value': new_value},
                                         filter=f'id = {new_magazine_id}')

                self.data_manager.update('CHARS_MAGAZINE', columns_values={'magazine_id': new_magazine_id,
                                                                         'current_bullets': self.current_bullets},
                                         filter=f'weapon_id = {self.weapon_id}')
                self.data_manager.logger.info(f'Снаряжен новый магазин {new_magazine_id} в оружие {self.weapon_id}. Кол-во патронов {self.current_bullets}')

            else:
                self.data_manager.logger.error("Ошибка получения информации о магазине из таблицы ITEMS")

    def shoot(self, bullets_used:int) -> None:
        if self.current_bullets >= bullets_used:
            self.current_bullets -= bullets_used
            self.data_manager.update('CHARS_MAGAZINE', columns_values={'current_bullets': self.current_bullets},
                             filter=f'weapon_id = {self.weapon_id}')
            self.data_manager.logger.info(f"Выстрел! Осталось патронов: {self.current_bullets}")

            return None
        else:
            bullets_used = self.current_bullets
            self.current_bullets = 0
            self.data_manager.update('CHARS_MAGAZINE', columns_values={'current_bullets': self.current_bullets},
                                     filter=f'weapon_id = {self.weapon_id}')
            self.data_manager.logger.info(f"Выстрел! Осталось патронов: {self.current_bullets}")
            return bullets_used

    def reload(self, new_magazine_id=None):
        try:
            # Начало транзакции
            self.data_manager.begin_transaction()

            self.reload_magazine(new_magazine_id)

            # Завершение транзакции
            self.data_manager.commit_transaction()
        except Exception as e:
            # Откат транзакции в случае ошибки
            self.data_manager.rollback_transaction()
            self.data_manager.logger.error(f"Ошибка при перезарядке оружия: {e}")

    def get_current_bullets(self):
        return self.current_bullets


class HandGrenade(Item, Grenade):
    def __init__(self, item_id:int, **kwargs):
        super().__init__(item_id, data_manager=kwargs.get('data_manager', DataManager()))
        self.grenade_type = self.Type
        super(Grenade, self).__init__(self.Type, data_manager=self.data_manager)