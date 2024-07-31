import pprint

from ArbDatabase import DataManager, DataModel
from ArbItems import Item
from dataclasses import dataclass
from ArbUtils.ArbDataParser import process_string
from ArbDamage import Damage


class ClothesInit(DataModel):
    def __init__(self, id: str, **kwargs):
        self.cloth_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        super().__init__('CLOTHES', f'id = "{self.cloth_id}"', data_manager=self.data_manager)
        self.label = self.get('name', 'Неизвестная одежда')
        self.slot = self.get('slot', '') if self.get('slot') else ''
        self.coverage = self.get('coverage', '') if self.get('coverage', None) else ''
        self.layer = self.get('layer', 0)
        self.material_type = self.get('material_type', 'Металл')
        self.efficiency = self.get('efficiency', 100) if self.get('efficiency') else 100
        self.insulation_cold = self.get('insulation_cold', 0) if self.get('insulation_cold') else 0
        self.insulation_heat = self.get('insulation_heat', 0) if self.get('insulation_heat') else 0
        self.disguise = self.get('disguise', 0) if self.get('disguise') else 0
        self.cost = self.get('cost', 0) if self.get('cost') else 0
        self.weight = self.get('weight', 0) if self.get('weight') else 0
        self.tier = self.get('tier', 0) if self.get('tier') else 0
        self.max_endurance = self.get('endurance', 100) if self.get('endurance') else 100
        self.skill = self.get('skill', None)
        self.skill_value = self.get('value', None)

    def cover_bodygroups(self):
        slot = self.slot
        coverage = process_string(self.coverage) if self.coverage else []
        total_coverage = [slot]
        total_coverage.extend(coverage)

        return list(set(total_coverage))


class Clothes(Item, ClothesInit):
    def __init__(self, item_id: int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__(item_id, data_manager=self.data_manager)
        self.clothes_id = self.type
        ClothesInit.__init__(self, self.clothes_id, data_manager=self.data_manager)  # Исправлено здесь

        self.protection = {}

    def get_current_endurance(self):
        return self.endurance / self.max_endurance if self.endurance < self.max_endurance else 1

    def armor_protection(self):
        material_protection = self.material.protection_data()

        if not material_protection:
            return {}  # Вернуть пустой словарь, если нет информации о защите материала

        endurance_factor = self.get_current_endurance()
        quality_factor = self.quality.armor_factor
        armor_efficiency = self.efficiency / 100

        protection = {}

        for p in material_protection:
            protection[p] = material_protection[p] * endurance_factor * quality_factor * armor_efficiency

        return protection

    def get_protection(self, protection_id: str):
        return self.armor_protection().get(protection_id, 0)

    def cloth_disguise(self):
        return self.disguise * self.material.disguise_factor * self.get_current_endurance()

    def cloth_skill(self):
        return self.skill, self.skill_value * self.get_current_endurance()

    def __str__(self):
        return f'{self.label} из {self.material.label} ({self.quality.label})'

    def __repr__(self):
        return f'Armor.{self.cloth_id}.{self.material.material_id}.{self.quality.label}'


class CharacterArmor:
    def __init__(self, character_id: int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.character_id = character_id

    def get_equipment(self) -> dict:
        from ArbItems import CharacterEquipment
        return CharacterEquipment(self.character_id, data_manager=self.data_manager).items_slots().get('Одежда', [])

    def get_slot_protection(self, slot:str) -> dict:
        items = self.get_equipment()
        slot_protection = {}

        for item in items:
            cloth = Clothes(item.item_id, data_manager=self.data_manager)
            if slot not in cloth.cover_bodygroups() or 'Все тело' not in cloth.cover_bodygroups():
                continue
            layer = cloth.layer if cloth.slot == slot else cloth.layer + 10

            slot_protection[(layer, cloth.item_id)] = cloth.armor_protection()

        return slot_protection

    def armors_skills(self) -> dict:
        items = self.get_equipment()
        skills = {}
        for item in items:
            cloth = Clothes(item, data_manager=self.data_manager)
            skill, skill_value = cloth.cloth_skill()
            if skill and skill_value:
                if skill not in skills:
                    skills[skill] = skill_value
                else:
                    skills[skill] += skill_value

        return skills

    def ballistic_simulation(self, target_slot: str, damage: Damage) -> Damage | None:
        slot_armor = self.get_slot_protection(target_slot)

        if not slot_armor:
            return damage

        protection_type = damage.protection_type
        max_penetration = damage.penetration

        sorted_armors = dict(sorted(slot_armor.items(), key=lambda item: item[0][0], reverse=True))

        pprint.pprint(sorted_armors)
        for p in sorted_armors:
            layer, armor_id = p
            protection = sorted_armors[p].get(protection_type, 0)
            print(damage.penetration)

            if damage.penetration - protection > 0:
                damage.reduce_penetration(protection)
                Item(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.damage, 2))
            else:
                Item(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.damage * (damage.penetration / max_penetration), 2))
                return None

        if damage.penetration < max_penetration * 0.5:
            return damage.convert_to_blocked_type(max_penetration)
        else:
            return damage

    def calculate_slots_disguise(self):
        items = self.get_equipment()
        slots_disguise = {}

        for item in items:
            cloth = Clothes(item.item_id, data_manager=self.data_manager)
            for bodygroup in cloth.cover_bodygroups():
                if bodygroup not in slots_disguise:
                    slots_disguise[bodygroup] = cloth.cloth_disguise()
                else:
                    slots_disguise[bodygroup] += cloth.cloth_disguise()

        if 'Все тело' in slots_disguise:
            all_body_disguise = slots_disguise['Все тело']
            del(slots_disguise['Все тело'])
            for slot in slots_disguise:
                slots_disguise[slot] += all_body_disguise

        return slots_disguise

    def calculate_disguise(self):
        slots_disguise = self.calculate_slots_disguise()
        if not slots_disguise:
            return 0

        total_disguise = 0

        for disguise in slots_disguise.values():
            total_disguise += disguise

        total_disguise /= len(slots_disguise)

        return round(total_disguise, 2)