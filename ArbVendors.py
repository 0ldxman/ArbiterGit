import pprint

from ArbDatabase import DataManager
from ArbCharacterMemory import CharacterRelations
from ArbGenerator import ItemManager
from ArbUtils.ArbDataParser import string_to_list
from ArbPsychology import WorldView

from abc import ABC, abstractmethod


class VendorAbstract(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def fetch_data(self):
        pass

    @abstractmethod
    def get_items(self):
        pass

    @abstractmethod
    def get_price(self, item_id:str=None, **kwargs):
        pass

    @abstractmethod
    def get_item_price(self, item_id:str):
        pass


class Vendor(VendorAbstract):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.type = data.get('type', 'Торговец') if data.get('type', None) else 'Торговец'
        item_types = data.get('vendor_type', None) if data.get('vendor_type', None) else None
        self.item_types = string_to_list(item_types)

        self.min_tier = data.get('min_tier', 0) if data.get('min_tier', None) is not None else 0
        self.max_tier = data.get('max_tier', 2) if data.get('max_tier', None) is not None else 2
        self.location = data.get('loc', None)

    def fetch_data(self):
        if self.data_manager.check('VENDORS_INIT', f'id = {self.id}'):
            return self.data_manager.select_dict('VENDORS_INIT', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_relation(self, character_id:int):
        all_relations = self.get_all_relations()

        if character_id in all_relations:
            return all_relations.get(character_id).get_relation_of_actor()
        else:
            return None

    def get_all_relations(self):
        return CharacterRelations(self.id, data_manager=self.data_manager).get_character_relationships()

    def get_worldview(self):
        if not self.data_manager.check('CHARS_PSYCHOLOGY', f'id = {self.id}'):
            return WorldView('TrueNeutral', data_manager=self.data_manager)
        else:
            character_worldview = self.data_manager.select_dict('CHARS_PSYCHOLOGY', filter=f'id = {self.id}')[0].get('worldview', None)
            if character_worldview:
                return WorldView(character_worldview, data_manager=self.data_manager)
            else:
                return WorldView('TrueNeutral', data_manager=self.data_manager)

    def get_items(self):
        weapons = [i.get('id') for i in self.data_manager.select_dict('WEAPONS', filter=f'tier >= {self.min_tier} AND tier <= {self.max_tier} AND tier is not NULL')]
        clothes = [i.get('id') for i in self.data_manager.select_dict('CLOTHES', filter=f'tier >= {self.min_tier} AND tier <= {self.max_tier} AND tier is not NULL')]
        items = [i.get('id') for i in self.data_manager.select_dict('ITEMS_INIT', filter=f'tier >= {self.min_tier} AND tier <= {self.max_tier} AND tier is not NULL')]
        ammo = [i.get('id') for i in self.data_manager.select_dict('AMMO', filter=f'tier >= {self.min_tier} AND tier <= {self.max_tier} AND tier is not NULL')]

        total_assort = {'weapons': weapons if 'Оружие' in self.item_types or 'Все' in self.item_types else [],
                        'clothes': clothes if 'Одежда' in self.item_types or 'Все' in self.item_types else [],
                        'items': items if 'Предметы' in self.item_types or 'Все' in self.item_types else [],
                        'ammo': ammo if 'Боеприпасы' in self.item_types or 'Все' in self.item_types else []}

        return total_assort

    def get_relation_discount(self, character_id:int):
        relation = self.get_relation(character_id)
        print(relation)

        total_relation = (relation[0] + relation[1] + relation[2] + relation[3]) / 4

        if relation:
            return round(1 - (total_relation / 200), 2)
        else:
            return 1

    def get_item_price(self, item_id:str=None):
        total_items = self.get_items()
        basic_price = 0

        if item_id in total_items['weapons']:
            basic_price = self.data_manager.select_dict('WEAPONS', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('WEAPONS', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['clothes']:
            basic_price = self.data_manager.select_dict('CLOTHES', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('CLOTHES', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['items']:
            basic_price = self.data_manager.select_dict('ITEMS_INIT', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('ITEMS_INIT', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['ammo']:
            basic_price = self.data_manager.select_dict('AMMO', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('AMMO', filter=f'id = "{item_id}"')[0].get('cost', None) else 0

        if self.type == 'Торговец':
            return basic_price
        else:
            return round(basic_price * 0.001)

    def get_price(self, item_id:str=None, **kwargs):
        character_id = kwargs.get('character_id', None)
        total_items = self.get_items()
        basic_price = {}

        if character_id is not None:
            discount = self.get_relation_discount(character_id)
        else:
            discount = 1

        for i in total_items['weapons']:
            basic_price[i] = self.get_item_price(i) * discount

        for i in total_items['clothes']:
            basic_price[i] = self.get_item_price(i) * discount

        for i in total_items['items']:
            basic_price[i] = self.get_item_price(i) * discount

        for i in total_items['ammo']:
            basic_price[i] = self.get_item_price(i) * discount

        if item_id and item_id in basic_price:
            return basic_price[item_id]
        else:
            return basic_price


class VendorObject(VendorAbstract):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.label = data.get('label', None) if data.get('label', None) else 'Неизвестный торговец'
        self.type = data.get('type', None) if data.get('type', None) else 'Торговец'
        item_types = data.get('value', 'Все') if data.get('value', None) else 'Все'
        self.item_types = string_to_list(item_types)
        self.max_tier = data.get('max_tier', 1) if data.get('max_tier', None) else 1

    def fetch_data(self):
        if self.data_manager.check('LOC_OBJECTS_INIT', f'id = "{self.id}"'):
            return self.data_manager.select_dict('LOC_OBJECTS_INIT', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def get_items(self):
        weapons = [i.get('id') for i in self.data_manager.select_dict('WEAPONS', filter=f'tier <= {self.max_tier} AND tier is not NULL')]
        clothes = [i.get('id') for i in self.data_manager.select_dict('CLOTHES', filter=f'tier <= {self.max_tier} AND tier is not NULL')]
        items = [i.get('id') for i in self.data_manager.select_dict('ITEMS_INIT', filter=f'tier <= {self.max_tier} AND tier is not NULL')]
        ammo = [i.get('id') for i in self.data_manager.select_dict('AMMO', filter=f'tier <= {self.max_tier} AND tier is not NULL')]

        total_assort = {'weapons': weapons if 'Оружие' in self.item_types or 'Все' in self.item_types else [],
                        'clothes': clothes if 'Одежда' in self.item_types or 'Все' in self.item_types else [],
                        'items': items if 'Предметы' in self.item_types or 'Все' in self.item_types else [],
                        'ammo': ammo if 'Боеприпасы' in self.item_types or 'Все' in self.item_types else []}

        return total_assort

    def get_item_price(self, item_id:str=None):
        total_items = self.get_items()
        basic_price = 0

        if item_id in total_items['weapons']:
            basic_price = self.data_manager.select_dict('WEAPONS', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('WEAPONS', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['clothes']:
            basic_price = self.data_manager.select_dict('CLOTHES', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('CLOTHES', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['items']:
            basic_price = self.data_manager.select_dict('ITEMS_INIT', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('ITEMS_INIT', filter=f'id = "{item_id}"')[0].get('cost', None) else 0
        elif item_id in total_items['ammo']:
            basic_price = self.data_manager.select_dict('AMMO', filter=f'id = "{item_id}"')[0].get('cost', 0) if self.data_manager.select_dict('AMMO', filter=f'id = "{item_id}"')[0].get('cost', None) else 0

        if self.type == 'Торговец':
            return basic_price
        else:
            return round(basic_price * 0.001)

    def get_price(self, item_id: str = None, **kwargs):
        total_items = self.get_items()
        basic_price = {}

        for i in total_items['weapons']:
            basic_price[i] = self.get_item_price(i)

        for i in total_items['clothes']:
            basic_price[i] = self.get_item_price(i)

        for i in total_items['items']:
            basic_price[i] = self.get_item_price(i)

        for i in total_items['ammo']:
            basic_price[i] = self.get_item_price(i)

        if item_id and item_id in basic_price:
            return basic_price[item_id]
        else:
            return basic_price

