import pprint
import random

from ArbDatabase import DataManager, DataModel, DataDict
from ArbMaterial import Material
from ArbQuality import Quality


class Item(DataModel):
    def __init__(self, id:int, **kwargs):
        self.item_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'ITEMS', f'id = {self.item_id}', data_manager=self.data_manager)

        self.label = self.get('name', 'Неизвестный предмет')
        self.item_class = self.get('class', 'Разное')
        self.type = self.get('type', None)
        self.material = Material(self.get('material'), data_manager=self.data_manager) if self.get('material') else None
        self.quality = Quality(self.get('quality'), data_manager=self.data_manager) if self.get('quality') else None
        self.endurance = self.get('endurance', 100) if self.get('endurance') else 100
        self.biocode = self.get('biocode', None)
        self.inventory_id = self.get('inventory_id', None)

    def set_to_inventory(self, inventory_id: int):
        query = {'inventory': inventory_id}
        self.update_record(query)
        self.inventory_id = inventory_id

    def delete_from_inventory(self):
        query = {'inventory': None}
        self.update_record(query)
        self.inventory_id = None

    def set_name(self, name: str):
        query = {'name': name}
        self.update_record(query)
        self.label = name

    def set_material(self, material_id: str):
        query = {'material': material_id}
        self.update_record(query)
        self.material = Material(material_id, data_manager=self.data_manager)

    def set_quality(self, quality_id: str):
        query = {'quality': quality_id}
        self.update_record(query)
        self.quality = Quality(quality_id, data_manager=self.data_manager)

    def set_endurance(self, endurance: int):
        query = {'endurance': endurance}
        self.data_manager.update('ITEMS', query, f'id = {self.item_id}')
        self.endurance = endurance

    def set_biocode(self, biocode: int):
        query = {'biocode': biocode}
        self.update_record(query)
        self.biocode = biocode

    def change_endurance(self, value: int):
        self.endurance += value
        if self.endurance < 0:
            if self.item_class == 'Одежда':
                if random.randint(1, 100) > 70:
                    self.data_manager.delete('ITEMS', f'id = {self.item_id}')
                    return
            else:
                self.data_manager.delete('ITEMS', f'id = {self.item_id}')
                return

        query = {'endurance': self.endurance}
        self.data_manager.update('ITEMS', query, f'id = {self.item_id}')

    def delete_item(self):
        self.data_manager.delete('ITEMS', f'id = {self.item_id}')

    def get_endurance(self):
        if self.item_class == 'Одежда':
            max_endurance = DataDict('CLOTHES', f'id = "{self.type}"', data_manager=self.data_manager).get('endurance', 0)
        else:
            max_endurance = 100

        return self.endurance / max_endurance

    def __repr__(self):
        return f'Item.{self.item_id}.{self.type}'

    def __str__(self):
        if self.item_class == 'Одежда':
            health = f""" {round((self.endurance / self.data_manager.select_dict('CLOTHES', filter=f'id = "{self.type}"')[0].get('endurance')) * 100, 2)}%"""
        else:
            health = f' {round((self.endurance / 100)*100)}%'

        quality = f' ({self.quality.label})' if self.quality else ''
        material_name = f'{self.material.adjective} ' if self.material else ''

        return f'{material_name}{self.label}{quality}{health}'


class Inventory(DataModel):
    def __init__(self, inventory_id: int, **kwargs):
        self.inventory_id = inventory_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'INVENTORY_INIT', f'id = {self.inventory_id}', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный инвентарь')
        self.owner_id = self.get('owner_id', None)
        self.location = self.get('location', None)
        self.type = self.get('type', None)

    def find_item_by_type(self, item_type:str):
        items = self.get_items_list()
        total_items = []
        for item in items:
            if item.type == item_type:
                total_items.append(item)

        return total_items

    def find_item_by_id(self, item_id:int):
        items = self.get_items_list()
        total_items = []
        for item in items:
            if item.item_id == item_id:
                total_items.append(item)

        return total_items

    def find_item_by_class(self, item_class:str):
        items = self.get_items_list()
        total_items = []
        for item in items:
            if item.item_class == item_class:
                total_items.append(item)

        return total_items

    def get_items_list(self) -> list[Item]:
        items = []
        founded_items = self.data_manager.select_dict('ITEMS', filter=f'inventory = {self.inventory_id}')
        for item in founded_items:
            items.append(Item(item.get('id'), data_manager=self.data_manager))

        return items

    def get_items_dict(self):
        items = self.get_items_list()
        items_dict = {}

        for item in items:
            items_dict[item.item_id] = item

        return items_dict

    def get_items_by_class(self, type:str):
        items = self.get_items_list()
        total_items = []
        for item in items:
            if item.item_class == type:
                total_items.append(item)

        return total_items

    def add_item(self, item_id: int):
        Item(item_id, data_manager=self.data_manager).set_to_inventory(self.inventory_id)

    def delete_item(self, item_id: int):
        Item(item_id, data_manager=self.data_manager).delete_from_inventory()

    def string_inventory(self):
        items = self.get_items_list()
        result = ''
        for item in items:
            result += f'- ||**({item.item_id})**|| *{str(item)}*\n'

        return result

    @classmethod
    def get_inventory_by_character(cls, character_id: int, data_manager: DataManager = None) -> 'Inventory':
        data_manager = data_manager if data_manager else DataManager()
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
        self.data_manager = kwargs.get('data_manager', DataManager())

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
            slots[item.item_class].append(item)

        return slots

    def weapon(self) -> Item | None:
        items = self.items_slots()
        return items.get('Оружие', [])[0] if items.get('Оружие') else None

    def equip_weapon(self, item_id: int) -> None:
        if Item(item_id, data_manager=self.data_manager).item_class != 'Оружие':
            return

        if self.items_slots().get('Оружие'):
            for item in self.items_slots().get('Оружие'):
                self.unequip_item(item.item_id)

        query = {
            'id': self.character_id,
            'item_id': item_id
        }

        self.data_manager.insert('CHARS_EQUIPMENT', query)

    def available_clothes_slots(self) -> list[str]:
        from ArbHealth import Body
        slots = Body(self.character_id, data_manager=self.data_manager).get_available_clothes_slots()

        return slots

    def clothes(self) -> dict[str, list[Item]]:
        items = self.items_slots().get('Одежда', [])

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
        clothes = self.clothes()

        return [slot for slot in slots if slot not in clothes]

    def clothes_slots_and_layers(self) -> dict[str, list[str]]:
        clothes = self.clothes()
        slots_and_layers = {}

        for slot, items in clothes.items():
            layers = []
            for item in items:
                layer = DataDict('CLOTHES', f'id = "{item.type}"', data_manager=self.data_manager).get('layer')
                layers.append(layer)
            slots_and_layers[slot] = layers

        return slots_and_layers

    def get_item_by_layer_and_slot(self, slot:str, layer: int) -> int | None:

        clothes = self.clothes()
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

    def unequip_item(self, item_id: int) -> None:
        items = [item.get('item_id') for item in self.data_manager.select_dict('CHARS_EQUIPMENT',filter=f'id = {self.character_id}')]
        if item_id in items:
            self.data_manager.delete('CHARS_EQUIPMENT', f'id = {self.character_id} AND item_id = {item_id}')

    def string_equipment(self):
        clothes = self.clothes()
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