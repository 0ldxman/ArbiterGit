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

    def change_value(self, amount):
        new_value = max(0, self.Value + amount)  # Make sure the value doesn't go below 0
        self.Value = new_value
        if new_value == 0:
            self.delete_item()
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

    def __desc__(self):
        pass

    #def __str__(self):
    #    text = f'{self.Name} из {self.Material.Name[0]} ({self.Quality.Name})'
    #    return text

    #def __repr__(self):
    #    text = f'Item.{self.Type}.{self.Material.ID} ({self.Quality.Name})'
    #    return text