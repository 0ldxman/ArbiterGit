import pprint
import random

from ArbDatabase import DataManager, DataModel, DataDict
from ArbMaterial import Material
from ArbQuality import Quality
from abc import ABC, abstractmethod
from ArbResponse import Response, ResponsePool


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
            damage_reduce = random.randint(1, min(damage_points, injury.damage))
            injury.change_damage(-1 * damage_reduce)
            if injury.damage <= 0:
                injury.delete_record()

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

        body = Body(user_id, data_manager=self.item.data_manager)

        injuries_list = body.get_injuries_list()
        disease_list = body.get_diseases_list()
        for i in injuries_list:
            i.set_healing(self.healing_efficiency)

        for i in disease_list:
            i.add_healing(self.healing_efficiency)

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
            spawned_item = ItemManager(self.item_type, data_manager=self.item.data_manager).spawn_item(user_id)
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

        body = Body(user_id, data_manager=self.item.data_manager)
        injuries_list = body.get_injuries_list()
        diseases_list = body.get_diseases_list()

        for i in injuries_list + diseases_list:
            i.delete_record()

        print(f'Персонаж {user_id} был воскрешен!')
        return Response(True, f'*Персонаж был воскрешен при помощи {self.item.label}*', 'Воскрешение!')


class RepairComponent(ItemComponent):
    def __init__(self, item: Item, repair_efficiency: int):
        super().__init__(item)
        self.repair_efficiency = repair_efficiency

    def use(self, user_id:int, **kwargs):
        clothes = CharacterEquipment(user_id, data_manager=self.item.data_manager).items_slots().get('Одежда', [])

        cloth_to_repair = Item(kwargs.get('clothes_id'), data_manager=self.item.data_manager) if kwargs.get('clothes_id') is not None else None
        if cloth_to_repair is None:
            cloth_to_repair = random.choice(clothes)

        cloth_to_repair.change_endurance(self.repair_efficiency)

        return Response(True, f'*Вы отремонтировали {cloth_to_repair.label} при помощи {self.item.label}*', 'Ремонт')


class SkipCycleComponent(ItemComponent):
    def __init__(self, item: Item, rest_efficiency: float):
        super().__init__(item)
        self.rest_efficiency = rest_efficiency

    def use(self, user_id:int, **kwargs):
        from ArbCharacters import Character

        rest = Character(user_id, data_manager=self.item.data_manager).change_cycle(1, max_cycles=3, rest_efficiency=self.rest_efficiency)
        print(f'Персонаж {user_id} отдыхает при помощи {self.item.label}')

        return Response(True, f'*Вы немного отдохнули при помощи {self.item.label}...*', 'Отдых')


class UsableItem:
    def __init__(self, item: Item, added_components: list = None):
        self.item = item

        self.components = added_components if added_components is not None else []
        self.get_all_comonents()

    def add_component(self, component: ItemComponent):
        self.components.append(component)

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
            elif component_type == 'SkipCycle':
                comp = SkipCycleComponent(self.item, component_value)
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


# TODO: Добавить предметам в базу данных снижение прочности за использование
# TODO: Добавить проверку возможности коммуникации исходя из предметов инвентаря (наличие рации, КПК, Нотбука)

# print(UsableItem(Item(2004)).use(1))


