import pprint

from ArbDatabase import DataManager
from ArbMaterial import Material
from ArbQuality import Quality


class Item:
    def __init__(self, item_id: int, *, data_manager:DataManager = None):
        self.ID = item_id
        if data_manager:
            self.data_manager = data_manager
        else:
            self.data_manager = DataManager()
        c_prompt = self.data_manager.select_dict('ITEMS',filter=f'id = {self.ID}')[0]

        self.Name = c_prompt.get('name','Неизвестно')
        self.Class = c_prompt.get('class','Разное')
        self.Value = c_prompt.get('value',1)
        self.Type = c_prompt.get('type', None)
        self.InventoryID = self.get_inventory()

        if c_prompt.get('material', None):
            self.Material = Material(c_prompt.get('material'), data_manager=self.data_manager)
        else:
            self.Material = None

        if c_prompt.get('quality', None):
            self.Quality = Quality(c_prompt.get('quality'), data_manager=self.data_manager)
        else:
            self.Quality = None

        self.Endurance = c_prompt.get('endurance',100)

    def delete_item(self):
        c_tables = ['ITEMS','CHARS_INVENTORY','CHARS_MAGAZINE']
        c_ids = ['id','item_id','weapon_id','magazine_id']
        for table in c_tables:
            c_pars = self.data_manager.get_all_columns(table)
            for i in c_ids:
                if i in c_pars:
                    if i != 'magazine_id':
                        self.data_manager.delete(table,filter=f'{i} = {self.ID}')
                    else:
                        self.data_manager.update(table,{f'{i}': 'NULL'},filter=f'{i} = NULL')
                else:
                    continue

    def delete(self):
        c_tables = ['ITEMS', 'CHARS_EQUIPMENT', 'INVENTORY_ITEMS']
        c_ids = ['id', 'item_id', 'ammo_id']
        for table in c_tables:
            c_pars = self.data_manager.get_all_columns(table)
            for i in c_ids:
                if i in c_pars:
                    if i != 'ammo_id':
                        self.data_manager.delete(table, filter=f'{i} = {self.ID}')
                    else:
                        self.data_manager.update(table, {f'{i}': None}, filter=f'{i} = {self.ID}')
                else:
                    continue


    def change_value(self, amount):
        new_value = max(0, self.Value + amount)  # Make sure the value doesn't go below 0
        self.Value = new_value
        if new_value == 0:
            self.delete()
        else:
            self.data_manager.update('ITEMS', columns_values={'value': new_value}, filter=f'id = {self.ID}')

    def change_endurance(self, amount):
        new_value = max(0, self.Endurance + amount)
        self.Endurance = new_value
        if new_value == 0:
            self.delete_item()
        else:
            self.data_manager.update('ITEMS', columns_values={'endurance': new_value}, filter=f'id = {self.ID}')

    def equipmentSlot(self) -> dict | None:
        class_slots_mapping = {
            'Оружие': {'table': 'WEAPONS', 'columns': 'slot', 'filter': f'id = "{self.Type}"'},
            'Одежда': {'table': 'CLOTHES', 'columns': 'slot, layer', 'filter': f'id = "{self.Type}"'}
        }

        if self.Class in class_slots_mapping:
            slot_data = self.data_manager.select_dict(class_slots_mapping[self.Class]['table'],
                                                    columns=class_slots_mapping[self.Class]['columns'],
                                                    filter=class_slots_mapping[self.Class]['filter'])[0]
        else:
            return None

        return slot_data

    def owner(self):
        if self.data_manager.check('CHARS_EQUIPMENT', f'item_id = {self.ID}'):
            return self.data_manager.select_dict('CHARS_EQUIPMENT',filter=f'item_id = {self.ID}')[0].get('id')
        else:
            return None

    def get_inventory(self):
        if not self.data_manager.check('INVENTORY_ITEMS',f'id = {self.ID}'):
            return None
        else:
            return self.data_manager.select_dict('INVENTORY_ITEMS', filter=f'id = {self.ID}')[0].get('inventory')

    def delete_from_inventory(self):
        if self.InventoryID:
            self.data_manager.delete('INVENTORY_ITEMS', f'id = {self.ID}')

    def set_to_inventory(self, inventory_id:int):
        if self.InventoryID:
            self.data_manager.update('INVENTORY_ITEMS', {'inventory': inventory_id}, f'id = {self.ID}')
            self.InventoryID = inventory_id
        else:
            self.InventoryID = inventory_id
            self.data_manager.insert('INVENTORY_ITEMS', {'id': self.ID, 'inventory': inventory_id})

    def unequip(self):
        if not self.data_manager.check('CHARS_EQUIPMENT', f'item_id = {self.ID}'):
            return None

        character = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'item_id = {self.ID}')[0].get('id')
        character_inventory = Inventory.get_character_inventory(character, self.data_manager)

        self.data_manager.delete('CHARS_EQUIPMENT', f'item_id = {self.ID}')
        Inventory(character_inventory, data_manager=self.data_manager).add_items(self.ID)

    def equip(self, character_id:int):
        from ArbClothes import CharacterArmors

        if self.Class == 'Одежда':
            info = self.equipmentSlot()
            slot = info.get('slot')
            layer = info.get('layer')
            character_slots = CharacterArmors(character_id, data_manager=self.data_manager).armors_id()

            if layer not in character_slots[slot]:
                self.data_manager.insert('CHARS_EQUIPMENT',{'id': character_id, 'item_id': self.ID, 'slot': slot})
            else:
                Item(character_slots[slot][layer], data_manager=self.data_manager).unequip()
                self.data_manager.insert('CHARS_EQUIPMENT', {'id': character_id, 'item_id': self.ID, 'slot': slot})


        elif self.Class == 'Оружие':
            remaining_slots = CharacterEquipment(character_id, data_manager=self.data_manager).remaining_weapon_slots()
            needed_slots = self.equipmentSlot().get('slot')
            if remaining_slots > needed_slots:
                self.data_manager.insert('CHARS_EQUIPMENT', {'id': character_id, 'item_id': self.ID, 'slot': 'Оружие'})
            else:
                pass

    def reload(self, n:int):
        if self.Value < n:
            total_bullets = self.Value
        else:
            total_bullets = n

        self.change_value(-total_bullets)

        return total_bullets

    def __desc__(self):
        pass

    def __repr__(self):
        return f'Item.{self.Type}'

    def __str__(self):
        if self.Class == 'Одежда':
            health = f""" {round((self.Endurance / self.data_manager.select_dict('CLOTHES', filter=f'id = "{self.Type}"')[0].get('endurance')) * 100, 2)}%"""
        else:
            health = f' {round((self.Endurance/100)*100)}%'

        if self.Class in ['Оружие', 'Одежда']:
            value = ''
        else:
            value = f' x{self.Value} шт.'

        quality = f' ({self.Quality.Name})' if self.Quality else ''
        material_name = f'{self.Material.Adjective} ' if self.Material else ''


        return f'{material_name}{self.Name}{quality}{health}{value}'

    def __eq__(self, other):
        if isinstance(other, int):
            return self.ID == other
        elif isinstance(other, str):
            return self.Type == other
        elif isinstance(other, Item):
            return self.ID == other.ID
        else:
            return None

class CharacterInventory:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        self.items = self.fetch_items()
        self.weapons, self.clothes = self.get_equipment_from_items()

        self.clothes_slots = self.proccess_clothes()

    def fetch_items(self):
        if self.data_manager.check('CHARS_INVENTORY', f'character_id = {self.id}'):
            return [Item(item.get('item_id'), data_manager=self.data_manager) for item in self.data_manager.select_dict('CHARS_INVENTORY', filter=f'character_id = {self.id}')]
        else:
            return []

    def get_equipment_from_items(self):
        weapons = []
        clothes = []
        for item in self.items:
            if item.Class not in ['Оружие', 'Одежда']:
                continue
            elif item.Class == 'Оружие':
                weapons.append(item)
            elif item.Class == 'Одежда':
                clothes.append(item)

        return weapons, clothes

    def proccess_clothes(self):
        total_list = self.clothes
        total_slots = {}
        for item in total_list:
            if item.equipmentSlot().get('slot') not in total_slots:
                total_slots[item.equipmentSlot().get('slot')] = [item]
            else:
                total_slots[item.equipmentSlot().get('slot')].append(item)

        return total_slots

    def delete_item(self, item_id:int):
        if self.data_manager.check('CHARS_INVENTORY', f'item_id = {item_id} AND character_id = {self.id}'):
            self.data_manager.delete('CHARS_INVENTORY', filter=f'item_id = {item_id}')

    def describe(self):
        clothes_text = f''
        items_text = f''
        weapons_text = f''

        for slot in self.clothes_slots:
            slot_text = f'**[ {slot} ]:**'
            for item in self.clothes_slots[slot]:
                slot_text += f'\n- *{item.__str__()}*'
            clothes_text += f'\n{slot_text}'

        for weapon in self.weapons:
            weapons_text += f'\n- *{weapon.__str__()}*'

        for item in self.items:
            if item not in self.weapons and item not in self.clothes:
                items_text += f'\n- *{item.__str__()}*'

        return clothes_text, weapons_text, items_text

    def calculate_clothes_weight(self):
        total_weight = 0
        for item in self.clothes:
            total_weight += self.data_manager.select_dict('CLOTHES', filter=f'id = "{item.Type}"')[0].get('weight')

        return total_weight


class CharacterEquipment:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

    def get_armors_id(self):
        from ArbClothes import CharacterArmors
        print(CharacterArmors(self.id, data_manager=self.data_manager).armors_id())
        return CharacterArmors(self.id, data_manager=self.data_manager).armors_id()

    def get_weapons_id(self):
        if not self.data_manager.check('CHARS_EQUIPMENT', f'id = {self.id} AND slot = "Оружие"'):
            return []

        list_of_weapons = self.data_manager.select_dict('CHARS_EQUIPMENT', filter=f'id = {self.id} AND slot = "Оружие"')
        return [weapon['item_id'] for weapon in list_of_weapons]

    def current_weapon_slots(self):
        from ArbWeapons import Weapon

        slots = 0
        weapons = self.get_weapons_id()
        for weapon in weapons:
            slots += Weapon(weapon, data_manager=self.data_manager).Slot

        return slots

    def max_weapon_slots(self):
        from ArbHealth import Body

        bodyparts = Body(self.id, data_manager=self.data_manager).body_parts
        c_slots = 0
        for bodypart in bodyparts:
            c_slots += bodypart.WeaponSlots

        return c_slots

    def remaining_weapon_slots(self):
        max_slots = self.max_weapon_slots()
        current_slots = self.current_weapon_slots()

        return max_slots-current_slots

    def armors_skills(self):
        from ArbClothes import CharacterArmors

        return CharacterArmors(self.id, data_manager=self.data_manager).armors_skills()

    def describe(self):
        clothes_text = f''
        weapons_text = f''

        armors = self.get_armors_id()
        weapons = self.get_weapons_id()

        for slot in armors:
            slot_text = f'**[ {slot} ]:**'
            values = armors[slot].values()
            for item in values:
                slot_text += f'\n- *{Item(item, data_manager=self.data_manager).__str__()}*'
            clothes_text += f'\n{slot_text}'

        for weapon in weapons:
            weapons_text += f'\n- *{Item(weapon, data_manager=self.data_manager).__str__()}*'

        if not clothes_text:
            clothes_text = '*(У вас нет экипированных вещей)*'

        if not weapons_text:
            weapons_text = '*(У вас нет экипированного оружия)*'

        return clothes_text, weapons_text


class Inventory:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.get_info()
        self.lable = data.get('label', None)
        self.owner = data.get('owner', None)
        self.type = data.get('type', None)

    def get_dict(self):
        items = self.get_items()
        total_dict = {}
        for item in items:
            total_dict[item.ID] = item

        return total_dict

    def find_class_items(self, item_class:str):
        items = self.get_items()
        return [item.ID for item in items if item.Class.lower() == item_class.lower()]

    def find_by_name(self, item_name:str):
        items = self.get_items()
        return [item.ID for item in items if item.Name == item_name]

    def get_info(self):
        if self.data_manager.check('INVENTORY_INIT', f'id = {self.id}'):
            return self.data_manager.select_dict('INVENTORY_INIT', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_items(self):
        if not self.data_manager.check('INVENTORY_ITEMS', f'inventory = {self.id}'):
            return []
        else:
            total_items = self.data_manager.select_dict('INVENTORY_ITEMS', filter=f'inventory = {self.id}')
            return [Item(item['id'], data_manager=self.data_manager) for item in total_items]

    def clear_inventory(self):
        items = self.get_items()
        for item in items:
            item.delete_from_inventory()

    def add_items(self, item_id:int | list):
        if isinstance(item_id, int):
            Item(item_id, data_manager=self.data_manager).set_to_inventory(self.id)
        else:
            for item in item_id:
                Item(item, data_manager=self.data_manager).set_to_inventory(self.id)

    def discard_items(self, item_id: int | list):
        if isinstance(item_id, int):
            Item(item_id, data_manager=self.data_manager).delete_from_inventory()
        else:
            for item in item_id:
                Item(item, data_manager=self.data_manager).delete_from_inventory()

    def delete_items_in_inventory(self):
        items = self.get_items()
        for item in items:
            item.delete()

    def set_label(self, label:str=None):
        self.data_manager.update('INVENTORY_INIT', {'label': label}, f'id = {self.id}')

    def set_owner(self, owner:int=None):
        self.data_manager.update('INVENTORY_INIT', {'owner': owner}, f'id = {self.id}')

    def describe(self):
        items_text = f''
        items = self.get_items()

        for item in items:
            items_text += f'\n- *{item.__str__()}*'

        return items_text


    @classmethod
    def get_character_inventory(cls, character_id:int, data_manager:DataManager):
        if not data_manager.check('CHARS_INV', f'id = {character_id}'):
            return None
        else:
            return data_manager.select_dict('CHARS_INV', filter=f'id = {character_id}')[0].get('inventory')

    @classmethod
    def get_inventory_by_character(cls, character_id:int, data_manager:DataManager):
        inventory_id = Inventory.get_character_inventory(character_id, data_manager)
        if not inventory_id:
            return None
        else:
            return Inventory(inventory_id, data_manager=data_manager)

    def __contains__(self, item):
        if isinstance(item, (Item, int, str)):
            item_list = self.get_items()
            return item in item_list

    def __repr__(self):
        return f'Inventory("{self.lable}", owner={self.owner}, items={self.get_items()})'

    def __len__(self):
        return len(self.get_items())