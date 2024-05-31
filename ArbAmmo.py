import random

from ArbDatabase import DataManager
from ArbDamage import Damage, Penetration, DamageType

class Ammunition:
    def __init__(self, ammo_id: str, **kwargs):
        self.ammo_id = ammo_id
        self.data_manager = kwargs.get('data_manager',DataManager())
        ammo_data = self.data_manager.select_dict('AMMO', filter=f'id = "{self.ammo_id}"')[0]

        if ammo_data:
            self.name = ammo_data.get('name','')
            self.caliber = ammo_data.get('caliber','')
            self.ammo_type = ammo_data.get('type','')
            self.in_area = ammo_data.get('in_area', 0)

            self.damage_info = self._get_damage_info()
        else:
            raise ValueError(f'Ammunition with ID {ammo_id} not found in the database.')

    def _get_damage_info(self):
        ammo_damage_data = self.data_manager.select_dict('AMMO_DAMAGE', filter=f'id = "{self.ammo_id}"')

        return ammo_damage_data

    def fire(self):
        damage_list = []
        for damage in self.damage_info:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 * damage.get('critical_chance', 1) else 1

            damage_value = random.randint(damage.get('min_damage',0), damage.get('max_damage',0)) * crit_mod
            total_damage = Damage(damage_value, damage.get('damage_type','Hit'), root=self.name, data_manager=self.data_manager)

            protection_type = self.data_manager.select_dict('DAMAGE_TYPE',filter=f'id = "{total_damage.Type.damage_id}"')[0].get('protection_type')

            c_pars = {'damage': total_damage,
                      'penetration': Penetration(name=protection_type, value=damage.get('penetration'), blocked_type=damage.get('blocked_type'))}

            damage_list.append(c_pars)
        return damage_list

    def __str__(self):
        return f'{self.name} (Калибр: {self.caliber}, Тип: {self.ammo_type})'

    def __repr__(self):
        return f'Ammo.{self.ammo_id}'

    def get_damage_info(self):
        return self.damage_info

class Bullet(Ammunition):
    def __init__(self, ammo_id: str):
        super().__init__(ammo_id)

    # def fire(self):
    #     damage_list = []
    #     for damage in self.damage_info:
    #         damage_value = random.randint(damage.get('min_damage',0), damage.get('max_damage',0))
    #         total_damage = Damage(damage_value, damage.get('damage_type','Hit'), root=self.name)
    #         total_penetration = Penetration(DamageType(total_damage.Type).protection_type, damage.get('penetration'), damage.get('blocked_type'))
    #         c_pars = {'damage': total_damage,
    #                   'penetration': total_penetration}
    #         damage_list.append(c_pars)
    #
    #     return damage_list


    def __repr__(self):
        return f'Bullet.{self.ammo_id}'


class Fragment(Ammunition):
    def __init__(self, fragment_id:str):
        super().__init__(fragment_id)

class Grenade(Ammunition):
    def __init__(self, ammo_id: str):
        super().__init__(ammo_id)

