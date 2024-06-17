from ArbDatabase import DataManager
from ArbItems import Item
from dataclasses import dataclass


class ClothesInit:
    def __init__(self, id: str, *, data_manager: DataManager=None):
        self.cloth_id = id
        if data_manager:
            self.data_manager = data_manager
        else:
            self.data_manager = DataManager()

        clothes_data = self.data_manager.select_dict('CLOTHES', '*', f'id = "{self.cloth_id}"')

        if not clothes_data:
            self.set_default_values()
        else:
            self.fill_clothes_data(clothes_data[0])

    def set_default_values(self):
        self.Name = ''
        self.Slot = None
        self.Layer = 0
        self.Disguise = 0
        self.Cost = 0
        self.Weight = 0
        self.InsulationHeat = 0
        self.InsulationCold = 0
        self.MaterialType = ''
        self.Efficiency = 0
        self.MaxEndurance = 0

    def fill_clothes_data(self, clothes_data):
        self.Name = clothes_data.get('name', '')
        self.Slot = clothes_data.get('slot', None)
        self.Layer = clothes_data.get('layer', 0)
        self.Disguise = clothes_data.get('disguise', 0)
        self.Cost = clothes_data.get('cost', 0)
        self.Weight = clothes_data.get('weight', 0)
        self.InsulationCold = clothes_data.get('insulation_cold', 0)
        self.InsulationHeat = clothes_data.get('insulation_heat', 0)
        self.MaterialType = clothes_data.get('material_type', 0)
        self.Efficiency = clothes_data.get('efficiency', 0)
        self.MaxEndurance = clothes_data.get('endurance', 0)


@dataclass()
class Protection:
    name:str
    value:int

    def __repr__(self):
        return f'Armor.{self.name} ({self.value}%)'

    def __add__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value + other
            return Protection(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value + other.value
            return Protection(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value - other
            return Protection(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value - other.value
            return Protection(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __rsub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value * other
            return Protection(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value * (other.value/100)
            return Protection(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.value == other
        elif isinstance(other, Protection):
            return self.name == other.name and self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.value < other
        elif isinstance(other, Protection):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.value <= other
        elif isinstance(other, Protection):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.value > other
        elif isinstance(other, Protection):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.value >= other
        elif isinstance(other, Protection):
            return self.value >= other.value
        return NotImplemented


class Clothes(Item, ClothesInit):
    def __init__(self, item_id: int, *, data_manager: DataManager = None):
        super(Clothes, self).__init__(item_id, data_manager=data_manager)
        self.clothes_id = self.Type
        ClothesInit.__init__(self, self.clothes_id, data_manager=self.data_manager)  # Исправлено здесь

        self.protection = {}

    def get_current_endurance(self):
        return self.Endurance / self.MaxEndurance

    def armor_protection(self):
        material_protection = self.Material.protection_data()

        if not material_protection:
            return {}  # Вернуть пустой словарь, если нет информации о защите материала

        endurance_factor = self.get_current_endurance()
        quality_protection = self.Quality.ArmorFactor

        armor_efficiency = self.Efficiency / 100

        protection = {}

        for i in material_protection.keys():
            protection[i] = Protection(name=i, value=material_protection[i] * endurance_factor * quality_protection * armor_efficiency)

        return protection

    def cloth_disguise(self):
        return self.Disguise * self.Material.DisguiseFactor * self.get_current_endurance()

    def __str__(self):
        return f'{self.Name} из {self.Material.Name} ({self.Quality.Name})'

    def __repr__(self):
        return f'Armor.{self.cloth_id}.{self.Material.ID}.{self.Quality.Name}'


class CharacterArmors:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

    def armors_id(self) -> dict:
        if not self.data_manager.check('CHARS_EQUIPMENT', f'id = {self.id}'):
            return {}

        c_equipment_data = self.data_manager.select_dict('CHARS_EQUIPMENT',
                                                         filter=f'id = {self.id} AND slot != "Оружие"')
        equipment = {}

        for slot in c_equipment_data:
            c_slot = slot.get('slot')
            c_id = slot.get('item_id')
            c_layer = Clothes(c_id, data_manager=self.data_manager).Layer

            if c_slot not in equipment.keys():
                equipment[c_slot] = {c_layer: c_id}
            else:
                equipment[c_slot][c_layer] = c_id

        return equipment

    def armors_protection(self) -> dict:
        if not self.data_manager.check('CHARS_EQUIPMENT', f'id = {self.id}'):
            return {}

        c_equipment_data = self.data_manager.select_dict('CHARS_EQUIPMENT',
                                                         filter=f'id = {self.id} AND slot != "Оружие"')
        equipment = {}

        for slot in c_equipment_data:
            c_slot = slot.get('slot')
            c_id = slot.get('item_id')
            c_layer = Clothes(c_id, data_manager=self.data_manager).Layer
            if c_slot not in equipment.keys():
                equipment[c_slot] = {c_layer: Clothes(c_id, data_manager=self.data_manager).armor_protection()}
            else:
                equipment[c_slot][c_layer] = Clothes(c_id, data_manager=self.data_manager).armor_protection()

        return equipment



