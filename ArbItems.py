import pprint
import random

from ArbDatabase import DataManager, DataModel, DataDict, DataObject, EID, DEFAULT_MANAGER
from ArbMaterial import Material
from ArbQuality import Quality
from abc import ABC, abstractmethod
from ArbResponse import Response, ResponsePool
from dataclasses import dataclass


class Item(DataObject):
    def __init__(self, id: int, **kwargs):
        self.item_id = id

        DataObject.__init__(self, 'ITEMS', EID(id=self.item_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('name', 'Неизвестный предмет')
        self._item_class = self.field('class', 'Разное')
        self._type = self.field('type', None)
        self._material = self.field('material', None)
        self._quality = self.field('quality', None)
        self._endurance = self.field('endurance', 100)
        self._biocode = self.field('biocode', None)
        self._inventory_id = self.field('inventory_id', None)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @label.setter
    def label(self, value: str):
        self._label.save(self.data_manager, value)

    @property
    def item_class(self) -> str:
        return self._item_class.load(self.data_manager)

    @property
    def type(self) -> str:
        return self._type.load(self.data_manager)

    @property
    def material(self) -> Material | None:
        mat = self._material.load(self.data_manager)
        if mat:
            return Material(mat, data_manager=self.data_manager)
        else:
            return None

    @material.setter
    def material(self, value: Material | str):
        if isinstance(value, Material):
            self._material.save(value.material_id, self.data_manager)
        else:
            self._material.save(value, self.data_manager)

    @property
    def quality(self) -> Quality | None:
        qual = self._quality.load(self.data_manager)
        if qual:
            return Quality(qual, data_manager=self.data_manager)
        else:
            return Quality('Нормальное', data_manager=self.data_manager)

    @quality.setter
    def quality(self, value: Quality | str):
        if isinstance(value, Quality):
            self._quality.save(value.label, self.data_manager)
        else:
            self._quality.save(value, self.data_manager)

    @property
    def endurance(self) -> int:
        return self._endurance.load(self.data_manager)

    @endurance.setter
    def endurance(self, value: int):
        self._endurance.set_value(value)

    @property
    def biocode(self) -> int:
        return self._biocode.load(self.data_manager)

    @biocode.setter
    def biocode(self, value: int):
        self._biocode.save(self.data_manager, value)

    @property
    def inventory_id(self) -> int:
        return self._inventory_id.load(self.data_manager)

    @inventory_id.setter
    def inventory_id(self, value: int):
        self._inventory_id.save(self.data_manager, value)

    def set_to_inventory(self, inventory_id: int):
        self.inventory_id = inventory_id

    def delete_from_inventory(self):
        self.inventory_id = None

    def set_name(self, name: str):
        self.label = name

    def set_material(self, material_id: str):
        self.material = material_id

    def set_quality(self, quality_id: str):
        self.quality = quality_id

    def set_endurance(self, endurance: int):
        self.endurance = endurance
        self._endurance.save(self.data_manager, self.endurance)

    def set_biocode(self, biocode: int):
        self.biocode = biocode

    def change_endurance(self, value: int):
        print(f'ИЗМЕНЯЮ ПРОЧНОСТЬ С {self.endurance} + {value}')

        new_endurance = self.endurance + value
        if new_endurance <= 0:
            if self.item_class == 'Одежда':
                if random.randint(1, 100) > 70:
                    self.data_manager.delete('ITEMS', f'id = {self.item_id}')
                    self.data_manager.delete('CHARS_EQUIPMENT', f'item_id = {self.item_id}')
                    return
                else:
                    self.endurance = 0
            else:
                self.data_manager.delete('ITEMS', f'id = {self.item_id}')
                self.data_manager.delete('CHARS_EQUIPMENT', f'item_id = {self.item_id}')
                return

        query = {'endurance': self.endurance}
        self.data_manager.update('ITEMS', query, f'id = {self.item_id}')

        if self.get_endurance() > 1:
            max_endurance = 1 / self.get_endurance() * self.endurance
            query = {'endurance': max_endurance}
            self.endurance = max_endurance
            self.data_manager.update('ITEMS', query, f'id = {self.item_id}')

    def get_max_endurance(self):
        current_percent = self.get_endurance()
        max_endurance = 1 / current_percent * self.endurance

        return max_endurance

    def delete_item(self):
        self.data_manager.delete('ITEMS', f'id = {self.item_id}')
        self.data_manager.delete('CHARS_EQUIPMENT', f'item_id = {self.item_id}')

    def get_endurance(self):
        if self.item_class == 'Одежда':
            max_endurance = DataDict('CLOTHES', f'id = "{self.type}"', data_manager=self.data_manager).get('endurance', 0)
        else:
            max_endurance = 100

        return self.endurance / max_endurance

    def __repr__(self):
        return f'Item.{self.item_id}(type={self.type}, class={self.item_class})'

    def __str__(self):
        if self.item_class == 'Одежда':
            health = f""" {round((self.endurance / self.data_manager.select_dict('CLOTHES', filter=f'id = "{self.type}"')[0].get('endurance')) * 100, 2)}%"""
        else:
            health = f' {round((self.endurance / 100)*100)}%'

        quality = f' ({self.quality.label})' if self.quality else ''
        material_name = f'{self.material.adjective} ' if self.material else ''

        return f'{material_name}{self.label}{quality}{health}'


class ItemTranslate:
    def __init__(self, item_id:str, **kwargs):
        self.item_id = item_id
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)
        self.translation = self.find_label()

    def find_label(self):
        tables = ['WEAPONS', 'CLOTHES', 'ITEMS_INIT', 'AMMO', 'IMPLANTS_INIT']
        translation = None
        for table in tables:
            if self.data_manager.check(table, f'id = "{self.item_id}"'):
                translation = self.data_manager.select_dict(table, filter=f'id = "{self.item_id}"')[0].get('name', None)
                if not translation:
                    translation = self.data_manager.select_dict(table, filter=f'id = "{self.item_id}"')[0].get('label','Неизвестный предмет')
                break

        return translation

    @staticmethod
    def find_id_by_name(name:str, data_manager: DataManager = DEFAULT_MANAGER):
        db = data_manager
        tables = ['WEAPONS', 'CLOTHES', 'ITEMS_INIT', 'AMMO', 'IMPLANTS_INIT']
        translation = None
        for table in tables:
            table_columns = db.get_all_columns(table)
            if 'name' in table_columns:
                if db.check(table, filter=f'name = "{name}"'):
                    translation = db.select_dict(table, filter=f'name = "{name}"')[0].get('id', 'Неизвестный предмет')
                    break
            elif 'label' in table_columns:
                if db.check(table, filter=f'label = "{name}"'):
                    translation = db.select_dict(table, filter=f'label = "{name}"')[0].get('id', 'Неизвестный предмет')
                    break

        return translation


class Inventory(DataObject):
    def __init__(self, inventory_id: int, **kwargs):
        self.inventory_id = inventory_id

        DataObject.__init__(self, 'INVENTORY_INIT', EID(id=self.inventory_id), data_manager = kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный инвентарь')
        self._owner_id = self.field('owner_id', None)
        self._location = self.field('location', None)
        self._type = self.field('type', None)

        self._items = []

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def owner_id(self) -> int:
        return self._owner_id.load(self.data_manager)

    @property
    def location(self) -> str:
        return self._location.load(self.data_manager)

    @property
    def type(self) -> str:
        return self._type.load(self.data_manager)

    @property
    def items_list(self) -> list[Item]:
        if not self._items:
            self._items = self.get_items_list()

        return self._items

    def find_item_by_type(self, item_type:str):
        items = self.items_list
        total_items = []
        for item in items:
            if item.type == item_type:
                total_items.append(item)

        return total_items

    def find_item_by_id(self, item_id:int):
        items = self.items_list
        total_items = []
        for item in items:
            if item.item_id == item_id:
                total_items.append(item)

        return total_items

    def find_item_by_class(self, item_class:str):
        items = self.items_list
        total_items = []
        for item in items:
            if item.item_class == item_class:
                total_items.append(item)

        return total_items

    def find_component_in_items(self, component:str):
        items = self.items_list
        total_items = []
        for item in items:
            if component in UsableItem(item).get_components_dict():
                total_items.append(item)
        return total_items

    def get_items_list(self) -> list[Item]:
        items = []
        founded_items = self.data_manager.select_dict('ITEMS', filter=f'inventory = {self.inventory_id}')
        for item in founded_items:
            items.append(Item(item.get('id'), data_manager=self.data_manager))

        return items

    def get_items_dict(self):
        items = self.items_list
        items_dict = {}

        for item in items:
            items_dict[item.item_id] = item

        return items_dict

    def get_items_by_class(self, type: str):
        items = self.items_list
        total_items = []
        for item in items:
            if item.item_class == type:
                total_items.append(item)

        return total_items

    def add_item(self, item_id: int):
        Item(item_id, data_manager=self.data_manager).set_to_inventory(self.inventory_id)
        self._items = []

    def delete_item(self, item_id: int):
        Item(item_id, data_manager=self.data_manager).delete_from_inventory()
        self._items = []

    def string_inventory(self):
        items = self.items_list
        result = ''
        for item in items:
            result += f'- ||**({item.item_id})**|| *{str(item)}*\n'

        return result

    @classmethod
    def get_inventory_by_character(cls, character_id: int, data_manager: DataManager = DEFAULT_MANAGER) -> 'Inventory':
        data_manager = data_manager
        if data_manager.check('INVENTORY_INIT', filter=f'owner = {character_id} AND loc is NULL'):
            inventory_id = data_manager.select_dict('INVENTORY_INIT', filter=f'owner = {character_id} AND loc is NULL')[0].get('id')
            return cls(inventory_id, data_manager=data_manager)
        else:
            idx = data_manager.maxValue('INVENTORY_INIT', 'id') + 1
            query = {
                'id': idx,
                'label': 'Инвентарь',
                'owner': character_id,
                'loc': None,
                'type': 'Инвентарь'
            }
            data_manager.insert('INVENTORY_INIT', query)

            return cls(idx, data_manager=data_manager)


class CharacterEquipment:
    def __init__(self, character_id: int, **kwargs):
        self.character_id = character_id
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)
        self._items = {}
        self._clothes_items = {}

    @property
    def items(self) -> dict[str, list[Item]]:
        if not self._items:
            self._items = self.items_slots()
        return self._items

    @property
    def clothes_items(self) -> dict[str, list[Item]]:
        if not self._clothes_items:
            self._clothes_items = self.clothes()
        return self._clothes_items

    def get_equiped_items(self) -> list[Item]:
        items = []
        founded_items = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'id = {self.character_id}')
        for item in founded_items:
            items.append(Item(item.get('item_id'), data_manager=self.data_manager))

        return items

    def items_slots(self) -> dict[str, list[Item]]:
        items = self.get_equiped_items()
        slots = {'Оружие': [], 'Одежда': []}

        for item in items:
            if item.item_class in slots:
                slots[item.item_class].append(item)

        return slots

    def weapon(self) -> Item | None:
        items = self.items
        return items.get('Оружие', [])[0] if items.get('Оружие') else None

    def equip_weapon(self, item_id: int) -> None:
        if Item(item_id, data_manager=self.data_manager).item_class != 'Оружие':
            return

        if self.items.get('Оружие'):
            for item in self.items.get('Оружие'):
                self.unequip_item(item.item_id)

        query = {
            'id': self.character_id,
            'item_id': item_id
        }

        self.data_manager.insert('CHARS_EQUIPMENT', query)
        self._items = {}

    def available_clothes_slots(self) -> list[str]:
        from ArbHealth import Body
        slots = Body(self.character_id, data_manager=self.data_manager).get_available_clothes_slots()

        return slots

    def clothes(self) -> dict[str, list[Item]]:
        items = self.items.get('Одежда', [])

        slots = {}
        for item_obj in items:
            cloth_slot = DataDict('CLOTHES', f'id = "{item_obj.type}"', data_manager=self.data_manager).get('slot')
            if not cloth_slot:
                continue
            if cloth_slot not in slots:
                slots[cloth_slot] = []
            slots[cloth_slot].append(item_obj)

        return slots

    def empty_clothes_slots(self) -> list[str]:
        slots = self.available_clothes_slots()
        clothes = self.clothes_items

        return [slot for slot in slots if slot not in clothes]

    def clothes_slots_and_layers(self) -> dict[str, list[str]]:
        clothes = self.clothes_items
        slots_and_layers = {}

        for slot, items in clothes.items():
            layers = []
            for item in items:
                layer = DataDict('CLOTHES', f'id = "{item.type}"', data_manager=self.data_manager).get('layer')
                layers.append(layer)
            slots_and_layers[slot] = layers

        return slots_and_layers

    def get_item_by_layer_and_slot(self, slot:str, layer: int) -> int | None:

        clothes = self.clothes_items
        items_by_slot = clothes.get(slot, [])
        if not items_by_slot:
            return None
        for item in items_by_slot:
            if not self.data_manager.select_dict('CLOTHES', filter=f'id = "{item.type}"')[0].get('layer') == layer:
                continue
            else:
                return item.item_id
        else:
            return None

    def get_inventory(self) -> Inventory:
        return Inventory.get_inventory_by_character(self.character_id, data_manager=self.data_manager)

    def equip_cloth(self, item_id: int) -> None:
        if Item(item_id, data_manager=self.data_manager).item_class != 'Одежда':
            return

        item_data = self.data_manager.select_dict('CLOTHES',filter=f'id = "{Item(item_id, data_manager=self.data_manager).type}"')[0]
        item_layer = item_data.get('layer')
        item_slot = item_data.get('slot')

        replacing_item = self.get_item_by_layer_and_slot(item_slot, item_layer)
        if replacing_item:
            self.unequip_item(replacing_item)

        query = {
            'id': self.character_id,
            'item_id': item_id
        }

        self.data_manager.insert('CHARS_EQUIPMENT', query)
        self._items = {}
        self._clothes_items = {}

    def unequip_item(self, item_id: int) -> None:
        items = [item.get('item_id') for item in self.data_manager.select_dict('CHARS_EQUIPMENT',filter=f'id = {self.character_id}')]
        if item_id in items:
            self.data_manager.delete('CHARS_EQUIPMENT', f'id = {self.character_id} AND item_id = {item_id}')

        self._items = {}
        self._clothes_items = {}

    def string_equipment(self):
        clothes = self.clothes_items
        weapon = self.weapon()

        clothes_string = f''

        for slot, items in clothes.items():
            clothes_string += f'\n-# **{slot}:**\n'
            for item in items:
                clothes_string += f'- *{str(item)}*\n'

        if weapon:
            weapon_string = f'\n-# **Экипированное оружие:**\n- *{str(weapon)}*\n'
        else:
            weapon_string = f'-# **Экипированное оружие:**\n- *Отсутствует*'

        return f'{clothes_string}\n\n{weapon_string}'

    def validate_and_fix_equipment(self) -> None:
        """Проверяет и устраняет конфликты экипировки у персонажа."""
        clothes = self.clothes_slots_and_layers()  # Получаем экипированную одежду по слотам и слоям
        weapons = self.items.get('Оружие', [])  # Получаем экипированное оружие

        # Проверка на несколько предметов в одном слоте и одном слое
        for slot, layers in clothes.items():
            # Если в слоте несколько предметов на одном слое, оставляем случайный предмет, остальные убираем
            unique_layers = set(layers)
            if len(layers) != len(unique_layers):
                for layer in unique_layers:
                    items_on_layer = [item for item in self.clothes_items[slot] if
                                      self.data_manager.select_dict('CLOTHES', filter=f'id = "{item.type}"')[0].get(
                                          'layer') == layer]
                    if len(items_on_layer) > 1:
                        item_to_keep = random.choice(items_on_layer)
                        items_to_remove = [item for item in items_on_layer if item != item_to_keep]

                        for item in items_to_remove:
                            self.unequip_item(item.item_id)

        # Проверка на наличие второго оружия
        if len(weapons) > 1:
            weapon_to_keep = random.choice(weapons)  # Случайным образом выбираем одно оружие
            weapons_to_remove = [weapon for weapon in weapons if weapon != weapon_to_keep]

            for weapon in weapons_to_remove:
                self.unequip_item(weapon.item_id)


class ItemComponent(ABC):
    def __init__(self, item: Item):
        self.item = item

    @abstractmethod
    def use(self, user_id:int, **kwargs):
        pass


class UsableComponent(ItemComponent):
    def __init__(self, item: Item, endurance_reduce:int = 10):
        super().__init__(item)
        self.endurance_reduce = endurance_reduce

    def use(self, user_id: int, **kwargs):
        self.item.change_endurance(-1 * self.endurance_reduce)
        print(f'{self.item.label} ({self.item.item_id}) использовано {user_id}!')

        return Response(True,
                        f'*Вы использовали {self.item.label} на {self.endurance_reduce}%*',
                        'Использование')


class InjuryReduceComponent(ItemComponent):
    def __init__(self, item: Item, damage_points:int = 20):
        super().__init__(item)
        self.damage_reduce = damage_points

    def use(self, user_id:int, **kwargs):
        from ArbHealth import Body
        body = Body(user_id, data_manager=self.item.data_manager)
        injuries = body.get_injuries_list()

        if not injuries:
            return

        damage_points = self.damage_reduce
        while damage_points > 0:
            if not injuries:
                break

            injury = random.choice(injuries)
            if injury.is_scar:
                injuries.remove(injury)
                continue
            damage_reduce = random.randint(1, min(damage_points, injury.damage))
            injury.change_damage(-1 * damage_reduce)
            if injury.damage <= 0:
                injury.delete_record()
                injuries.remove(injury)

            damage_points -= damage_reduce
            print(f'{user_id} снизил повреждение от ранений на {damage_reduce}!')

        return Response(True,
                        f'*Вы залечиваете свои раны ||(восстановлено {self.damage_reduce} единиц урона)|| при помощи {self.item.label}*',
                        'Лечение ранений')


class AddDiseaseComponent(ItemComponent):
    def __init__(self, item: Item, disease_id: str, disease_level: int = 0):
        super().__init__(item)
        self.disease_id = disease_id
        self.disease_level = disease_level

    def use(self, user_id:int, **kwargs):
        from ArbHealth import Disease
        Disease.create_character_disease(user_id, self.disease_id, severity=self.disease_level, data_manager=self.item.data_manager)
        print(f'{user_id} получил заболевание {self.disease_id} на уровне {self.disease_level}%!')

        return Response(False,
                        f'*После использования {self.item.label} вы чувствуете некоторые изменения в самочувствии...*',
                        'Самочувствие')


class BloodRecoveryComponent(ItemComponent):
    def __init__(self, item: Item, bloodout_reducing: float):
        super().__init__(item)
        self.bloodout_reducing = bloodout_reducing

    def use(self, user_id: int, **kwargs):
        from ArbHealth import Body
        body = Body(user_id, data_manager=self.item.data_manager)
        bleedout = body.get_bleedout()

        if not bleedout:
            return

        bleedout.add_severity(-1 * self.bloodout_reducing)
        if bleedout.current_severity <= 0:
            bleedout.delete_record()

        print(f'{user_id} восполнил свою кровь на {self.bloodout_reducing}%!')
        return Response(True,
                        f'*Вы восстановили кровопотерю на {self.bloodout_reducing}% при помощи {self.item.label}*',
                        'Восполнение крови')


class HealInjuryComponent(ItemComponent):
    def __init__(self, item: Item, healing_efficiency: float):
        super().__init__(item)
        self.healing_efficiency = healing_efficiency

    def use(self, user_id: int, **kwargs):
        from ArbHealth import Body, Injury
        body = Body(user_id, data_manager=self.item.data_manager)
        injuries: list[Injury] = body.get_injuries_list()

        if not injuries:
            return

        injuries_id = [inj.injury_id for inj in injuries]
        healing_injury = kwargs.get('injury_id')
        if not healing_injury:
            healing_injury = random.choice(injuries_id)

        injury = Injury(healing_injury, data_manager=self.item.data_manager)
        injury.set_healing(self.healing_efficiency)

        print(f'Ранение {healing_injury} было залечено {user_id} на {self.healing_efficiency}!')

        return Response(True, f'*Вы остановили кровотечение {injury.injury_type.label} при помощи {self.item.label}*',
                        'Остановка кровотечения')


class TotalHealingComponent(ItemComponent):
    def __init__(self, item: Item, healing_efficiency: float):
        super().__init__(item)
        self.healing_efficiency = healing_efficiency

    def use(self, user_id:int, **kwargs):
        from ArbHealth import Body
        from ArbSkills import Skill

        owner_id = kwargs.pop('owner_id', None)
        if not owner_id:
            owner_id = user_id

        skill = Skill(owner_id, 'Medicine')

        total_healing = self.healing_efficiency * (0.5 + skill.lvl)
        skill.skill_check()

        body = Body(user_id, data_manager=self.item.data_manager)

        injuries_list = body.get_injuries_list()
        disease_list = [dis for dis in body.get_diseases_list() if dis.disease_type.can_be_treated]
        for i in injuries_list:
            i.set_healing(total_healing)

        for i in disease_list:
            i.set_healing(total_healing)

        print(f'Персонажу {user_id} залечили все ранения и болезни на {self.healing_efficiency}%')

        return Response(True, f'*Вы залечили ранения и болезни при помощи {self.item.label}*','Уход за ранами')


class ItemSpawnerComponent(ItemComponent):
    def __init__(self, item: Item, item_type: str, count: int = 1):
        super().__init__(item)
        self.item_type = item_type
        self.count = count

    def use(self, user_id:int, **kwargs):
        from ArbGenerator import ItemManager

        for _ in range(self.count):
            inventory_id = Inventory.get_inventory_by_character(user_id)
            spawned_item = ItemManager(self.item_type, data_manager=self.item.data_manager, inventory=inventory_id.inventory_id).spawn_item()
            print(f'{spawned_item.label} ({spawned_item.item_id}) создано для персонажа {user_id}!')

            return Response(True, f'*Вы создали {spawned_item.label} при помощи {self.item.label}*',
                            'Создание')


class BattleObjectSpawnComponent(ItemComponent):
    def __init__(self, item: Item, object_type: str, count: int = 1):
        super().__init__(item)
        self.battle_object_type = object_type
        self.count = count

    def use(self, user_id: int, **kwargs):
        from ArbBattle import Actor, Layer, ObjectType

        if Actor(user_id, data_manager=self.item.data_manager).battle_id is None:
            return

        actor = Actor(user_id, data_manager=self.item.data_manager)
        layer: Layer = actor.get_layer()
        object_id = None
        for _ in range(self.count):
            object_id = layer.add_object(self.battle_object_type)
            print(f'{self.battle_object_type} ({object_id}) был создан на поле боя {actor.battle_id} персонажем {user_id}!')

        if object_id:
            self.item.data_manager.update('BATTLE_CHARACTERS', {'object': object_id}, f'character_id = {user_id}')

        return Response(True, f'*Вы создали несколько {ObjectType(self.battle_object_type, data_manager=self.item.data_manager).label} при помощи {self.item.label}*', 'Создание объектов')


class ResurrectionComponent(ItemComponent):
    def __init__(self, item: Item):
        super().__init__(item)

    def use(self, user_id: int, **kwargs):
        from ArbHealth import Body
        from ArbCharacters import Character

        body = Body(user_id, data_manager=self.item.data_manager)
        injuries_list = body.get_injuries_list()
        diseases_list = body.get_diseases_list()

        for i in injuries_list + diseases_list:
            i.delete_record()

        print(f'Персонаж {user_id} был воскрешен!')
        return Response(True, f'*{Character(user_id).name} был воскрешен при помощи {self.item.label}*', 'Воскрешение!')


class RepairComponent(ItemComponent):
    def __init__(self, item: Item, repair_efficiency: int):
        super().__init__(item)
        self.repair_efficiency = repair_efficiency

    def use(self, user_id:int, **kwargs):
        from ArbSkills import Skill

        owner_id = kwargs.pop('owner_id', None)
        if not owner_id:
            owner_id = user_id

        skill = Skill(owner_id, 'Engineering')

        all_items = Inventory.get_inventory_by_character(user_id).get_items_list()
        for item in all_items:
            if item.item_id == self.item.item_id or item.type == self.item.type:
                all_items.remove(item)

        need_to_repair_clothes = [cloth for cloth in all_items if cloth.get_endurance() < 1]

        cloth_to_repair = Item(kwargs.get('clothes_id'), data_manager=self.item.data_manager) if kwargs.get('clothes_id') is not None else None
        if cloth_to_repair is None:
            cloth_to_repair = random.choice(need_to_repair_clothes)

        repair_percent = -0.25 + (skill.lvl / 100)
        skill.skill_check()

        cloth_to_repair.change_endurance(self.repair_efficiency * repair_percent)

        return Response(True, f'*Вы отремонтировали {cloth_to_repair.label} при помощи {self.item.label}*', 'Ремонт')



# class SkipCycleComponent(ItemComponent):
#     def __init__(self, item: Item, rest_efficiency: float):
#         super().__init__(item)
#         self.rest_efficiency = rest_efficiency
#
#     def use(self, user_id:int, **kwargs):
#         from ArbCharacters import Character
#
#         rest = Character(user_id, data_manager=self.item.data_manager).change_cycle(1, max_cycles=3, rest_efficiency=self.rest_efficiency)
#         print(f'Персонаж {user_id} отдыхает при помощи {self.item.label}')
#
#         return Response(True, f'*Вы немного отдохнули при помощи {self.item.label}...*', 'Отдых')


@dataclass
class ItemEffects:
    effect_type: str
    value: str | int | float
    count: int | None = None
    chance: int | None = None


class UsableItem:
    def __init__(self, item: Item, added_components: list = None):
        self.item = item

        self.components = added_components if added_components is not None else []
        self.get_all_comonents()

    def add_component(self, component: ItemComponent):
        self.components.append(component)

    def get_components_dict(self):
        total_comps = {}

        if not self.item.data_manager.check('ITEMS_EFFECTS', f'item_id = "{self.item.type}"'):
            return total_comps

        effects = self.item.data_manager.select_dict('ITEMS_EFFECTS', filter=f'item_id = "{self.item.type}"')
        for effect in effects:
            total_comps[effect.get("effect_type")] = ItemEffects(effect.get("effect_type"), effect.get("value"), effect.get("count"), effect.get("chance"))

        return total_comps

    def get_all_comonents(self):
        if not self.item.data_manager.check('ITEMS_EFFECTS', f'item_id = "{self.item.type}"'):
            return []

        effects = self.item.data_manager.select_dict('ITEMS_EFFECTS', filter=f'item_id = "{self.item.type}"')
        for effect in effects:
            component_type = effect.get('effect_type')
            component_value = effect.get('value')
            component_count = effect.get('count')
            component_chance = effect.get('chance', 0) if effect.get('chance', None) is not None else 100
            if random.randint(0, 100) > component_chance:
                continue

            if component_type == 'InjuryReduce':
                comp = InjuryReduceComponent(self.item, component_value)
            elif component_type == 'AddDisease':
                comp = AddDiseaseComponent(self.item, component_value, component_count)
            elif component_type == 'BloodRecovery':
                comp = BloodRecoveryComponent(self.item, component_value)
            elif component_type == 'HealInjury':
                comp = HealInjuryComponent(self.item, component_value)
            elif component_type == 'TotalHealing':
                comp = TotalHealingComponent(self.item, component_value)
            elif component_type == 'ItemSpawner':
                comp = ItemSpawnerComponent(self.item, component_value, component_count)
            elif component_type == 'BattleObjectSpawn':
                comp = BattleObjectSpawnComponent(self.item, component_value, component_count)
            elif component_type == 'Resurrection':
                comp = ResurrectionComponent(self.item)
            elif component_type == 'Repair':
                comp = RepairComponent(self.item, component_value)
            # elif component_type == 'SkipCycle':
            #     comp = SkipCycleComponent(self.item, component_value)
            elif component_type == 'Usable':
                comp = UsableComponent(self.item, component_value)
            else:
                continue

            self.add_component(comp)

    def use(self, user_id: int, **kwargs) -> ResponsePool:
        results = []
        for component in self.components:
            usage_result = component.use(user_id, **kwargs)
            results.append(usage_result)

        return ResponsePool(results)


# TODO: Добавить проверку возможности коммуникации исходя из предметов инвентаря (наличие рации, КПК, Нотбука)

# print(UsableItem(Item(2004)).use(1))
