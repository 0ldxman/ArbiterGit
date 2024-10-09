from ArbDatabase import DataManager


class Inventory:
    def __init__(self, character_id, *, data_manager:DataManager = None):
        self.character_id = character_id
        self.data_manager = data_manager if data_manager else DataManager()

        self.items = self.get_inventory_items()

    def get_inventory_items(self) -> list[dict] | None:
        items = self.data_manager.select_dict('CHARS_INVENTORY', columns='"item_id", "slot"',
                                         filter=f'character_id = {self.character_id}')

        return items

    def add_item(self, item_id, slot=None):
        if not slot:
            self.data_manager.insert('CHARS_INVENTORY',
                                     columns_values={'character_id': self.character_id, 'item_id': item_id,
                                                     'slot': None})
        else:
            self.data_manager.insert('CHARS_INVENTORY',
                                     columns_values={'character_id': self.character_id, 'item_id': item_id, 'slot': slot})

    def remove_item(self, item_id):
        self.data_manager.delete('CHARS_INVENTORY',
                                 filter=f'item_id = {item_id} AND character_id = {self.character_id}')

    def equip_item(self, item_id, slot):
        self.data_manager.update('CHARS_INVENTORY', columns_values={'slot': slot},
                                 filter=f'item_id = {item_id} AND character_id = {self.character_id}')

    def unequip_item(self, item_id):
        self.data_manager.update('CHARS_INVENTORY', columns_values={'slot': None},
                                 filter=f'item_id = {item_id} AND character_id = {self.character_id}')


class Equipment(Inventory):
    def __init__(self, character_id:int, *, data_manager:DataManager = None):
        super().__init__(character_id, data_manager=data_manager)

        self.equiped = self.get_equipped_items()

    def get_equipped_items(self) -> list:
        return [item for item in self.items if item.get('slot')]

    def get_weapons(self) -> list:
        return [item.get('item_id') for item in self.equiped if item.get('slot') == 'Оружие']

    def get_clothes(self) -> list:
        return [item for item in self.equiped if item.get('slot') not in ['Оружие', 'Патроны', 'Гранаты']]

    def equipment_on_slots(self) -> dict:
        total = {}
        for item in self.get_clothes():
            total.setdefault(item.get('slot'), []).append(item.get('item_id'))
        return total

    def slot_equipment(self, slot_name: str) -> list:
        return self.equipment_on_slots().get(slot_name, [])

