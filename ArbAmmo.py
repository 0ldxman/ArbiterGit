import random

from ArbDatabase import DataManager
from ArbDamage import Damage, Penetration

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
            self.fragments = ammo_data.get('fragments', None)
            self.fragments_type = ammo_data.get('fragments_type', None)

            self.damage_info = self._get_damage_info()
        else:
            raise ValueError(f'Ammunition with ID {ammo_id} not found in the database.')

    def _get_damage_info(self):
        ammo_damage_data = self.data_manager.select_dict('AMMO_DAMAGE', filter=f'id = "{self.ammo_id}"')

        return ammo_damage_data

    def fire(self) -> list[dict]:
        damage_list = []
        for damage in self.damage_info:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 - damage.get('critical_chance', 1) else 1

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
    def __init__(self, ammo_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(ammo_id)

    def process_bullet(self):
        total_damage = []
        main_damage = self.fire()
        total_damage += main_damage
        if self.fragments and self.fragments_type:
            total_damage += Fragments(self.fragments_type, self.fragments, data_manager=self.data_manager).process_fragments_damage()

        return total_damage

    def __repr__(self):
        return f'Bullet.{self.ammo_id}'


class Fragments(Ammunition):
    def __init__(self, fragment_id:str, value:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(fragment_id)
        self.value = value

    def process_fragments_damage(self) -> list[dict]:
        total_damage = []
        if self.value == 0:
            return total_damage

        for i in range(self.value):
            total_damage += self.fire()

        return total_damage

class Grenade(Ammunition):
    def __init__(self, grenade_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(grenade_id)

    def get_damaged_layers(self, distance_delta:int, current_layer:int):
        damaged_layers_id = [current_layer]
        centered_distance = self.in_area / 2

        layers_delta = round(centered_distance / distance_delta) # int(centered_distance // distance_delta)
        # print(layers_delta, centered_distance // distance_delta)
        for i in range(layers_delta):
            index = i+1
            damaged_layers_id.append(current_layer + index)
            damaged_layers_id.append(current_layer - index)

        return damaged_layers_id

    def fragments_damage(self):
        if not(self.fragments_type and self.fragments):
            return None
        else:
            fragments_value = random.randint(0, self.fragments)
            return Fragments(self.fragments_type, fragments_value, data_manager=self.data_manager).process_fragments_damage(), fragments_value

    def detonate(self):
        total_damage = {}
        total_damage['main_damage'] = self.fire()
        if self.fragments_type and self.fragments:
            frag_damage, frag_value = self.fragments_damage()
            total_damage['fragments_damage'] = frag_damage
            total_damage['fragments_value'] = frag_value
        else:
            total_damage['fragments_damage'] = []
            total_damage['fragments_value'] = 0

        return total_damage
