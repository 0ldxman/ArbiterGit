import pprint
import random
from ArbDatabase import DataManager, DataModel
from ArbDamage import Damage


class Ammunition(DataModel):
    def __init__(self, ammo_id:str, **kwargs):
        self.ammo_id = ammo_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('AMMO', f'id = "{self.ammo_id}"', data_manager=self.data_manager)

        self.label = self.get('name', 'Неизвестный боеприпас')
        self.caliber = self.get('caliber', '')
        self.type = self.get('type', '')
        self.fragments_type = self.get('fragments_type', None)
        self.fragments = self.get('fragments', 0)
        self.in_area = self.get('in_area', 0)

    def get_tier(self):
        return self.get('tier', None)

    def get_cost(self):
        return self.get('cost', 0)

    def get_damage_info(self):
        return self.data_manager.select_dict('AMMO_DAMAGE', filter=f'id = "{self.ammo_id}"')

    def ammo_fire(self):
        damage_info = self.get_damage_info()
        damage_list = []
        for damage in damage_info:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 - damage.get('critical_chance', 1) else 1

            damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
            total_damage = Damage(damage_value, damage.get('damage_type','Hit'), damage.get('penetration'), damage.get('blocked_type'), self.label, data_manager=self.data_manager)

            damage_list.append(total_damage)
        return damage_list


class Bullet(Ammunition):
    def __init__(self, ammo_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(ammo_id, data_manager=self.data_manager)

    def process_bullet(self) -> list[Damage]:
        total_damage = []
        main_damage = self.ammo_fire()
        total_damage.extend(main_damage)
        if self.fragments and self.fragments_type:
            total_damage += Fragments(self.fragments_type, self.fragments, data_manager=self.data_manager).process_fragments_damage()

        return total_damage

    def __repr__(self):
        return f'Bullet.{self.ammo_id}'


class Fragments(Ammunition):
    def __init__(self, fragment_id:str, value:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(fragment_id, data_manager=self.data_manager)
        self.value = value

    def process_fragments_damage(self) -> list[dict]:
        total_damage = []
        if self.value == 0:
            return total_damage

        for i in range(self.value):
            total_damage += self.ammo_fire()

        return total_damage


class Grenade(Ammunition):
    def __init__(self, grenade_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(grenade_id, data_manager=self.data_manager)

    def get_damaged_layers(self, distance_delta:int, current_layer:int):
        damaged_layers_id = [current_layer]
        centered_distance = self.in_area / 2

        layers_delta = round(centered_distance / distance_delta)
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
        total_damage['main_damage'] = self.ammo_fire()
        if self.fragments_type and self.fragments:
            frag_damage, frag_value = self.fragments_damage()
            total_damage['fragments_damage'] = frag_damage
            total_damage['fragments_value'] = frag_value
        else:
            total_damage['fragments_damage'] = []
            total_damage['fragments_value'] = 0

        return total_damage
