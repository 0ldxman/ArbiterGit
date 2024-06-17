import math

from ArbDatabase import *
from ArbDamage import Damage, Penetration
from ArbHealth import Body, BodyPart, LocalBodyPart, RaceAttack
from ArbClothes import Clothes
from ArbWeapons import Weapon
from ArbRoll import Roll
from ArbSkills import CharacterAttributes, SkillInit
from ArbUtils.ArbTimedate import TimeManager
from ArbRaces import Race


class Character:
    def __init__(self, ID: int, data_manager: DataManager = None):
        self.ID = ID
        if data_manager is None:
            self.data_manager = DataManager()  # Создание экземпляра DataManager по умолчанию
        else:
            self.data_manager = data_manager
        char_data = self.load_character_information()

        self.CustomID = char_data.get('custom_id')
        self.Owner = char_data.get('owner')
        self.Name = char_data.get('name')
        self.Race = char_data.get('race')
        self.Callsign = char_data.get('callsign')
        self.Sex = char_data.get('sex')
        self.Age = char_data.get('age')

        self.OrgID = char_data.get('org')
        self.OrgLvl = char_data.get('org_lvl')
        self.Fraction = char_data.get('frac')
        self.FractionLvl = char_data.get('frac_lvl')
        self.OrgPosition = char_data.get('org_pos')
        self.FracPosition = char_data.get('frac_pos')

        self.Avatar = char_data.get('avatar')
        self.Updated = char_data.get('update')
        self.Server = char_data.get('server')

    def load_character_information(self) -> dict:
        if self.data_manager.check('CHARS_INIT', f'id = {self.ID}'):
            char_data = self.data_manager.select_dict('CHARS_INIT', filter= f'id = {self.ID}')[0]
            return char_data
        else:
            return {}

    def character_characteristics(self):
        c_pars = self.data_manager.select_dict('CHARS_CHARS',filter=f'id = {self.ID}')
        total_chars = {}
        for i in c_pars:
            total_chars[i.get('char')] = i.get('lvl')

        return total_chars

    def character_characteristic(self, characteristic:str=None):
        if characteristic is None:
            return None
        else:
            return self.character_characteristics()[characteristic]

    def character_skills(self, skill:str=None):
        c_pars = self.data_manager.select_dict('CHARS_SKILLS',filter=f'id = {self.ID}')
        total_chars = {}
        for i in c_pars:
            total_chars[i.get('skill_id')] = i.get('lvl')

        if not skill:
            return total_chars
        else:
            return total_chars.get(skill,0)

    def character_traits(self, trait:str=None):
        c_pars = self.data_manager.select_dict('CHARS_TRAITS',filter=f'id = {self.ID}')
        total_chars = []
        for i in c_pars:
            total_chars.append(i.get('trait'))

        if not trait:
            return total_chars
        else:
            return trait in total_chars

    def delete_character(self):
        c_tables = self.data_manager.get_tables_with_prefix('CHARS_')
        c_tables += ['BATTLE_CHARACTERS', 'CHASE_CHARACTERS', 'STEALTH_CHARACTERS', 'GROUP_CHARS']

        for table in c_tables:
            c_columns = self.data_manager.get_all_columns(table)
            if 'id' or 'character_id' in c_columns:
                if 'id' in c_columns:
                    self.data_manager.delete(table, f'id = {self.ID}')
                elif 'character_id' in c_columns:
                    self.data_manager.delete(table, f'character_id = {self.ID}')

    def roll(self, **kwargs):
        if not 'skill' in kwargs:
            c_skill = kwargs.get('skill_value',0)
        else:
            c_skill = self.character_skills(kwargs.get('skill'))

        if not 'char' in kwargs:
            c_char = kwargs.get('char_value', 0)
        else:
            c_char = self.character_characteristic(kwargs.get('char'))

        if not 'cap' in kwargs:
            c_cap = kwargs.get('cap_value', 100)
        else:
            c_cap = Body(self.ID).physical_stat(kwargs.get('cap', 100))

        if not 'a_char' in kwargs:
            c_a_char = kwargs.get('a_char_value', None)
        else:
            c_a_char = self.character_characteristic(kwargs.get('a_char', None))

        if not 'a_capacity' in kwargs:
            c_a_cap = kwargs.get('a_cap_value', 100)
        else:
            c_a_cap = Body(self.ID).physical_stat(kwargs.get('a_cap', 100))

        if not 'pain' in kwargs:
            c_pain = kwargs.get('pain_value', 0)
        else:
            c_pain = Body(self.ID).calculate_total_pain()

        c_roll = Roll(c_skill, c_char, c_cap, c_a_char, c_a_cap, kwargs.get('stack', False), c_pain)
        c_roll.modify_result(kwargs.get('modifier', 0))
        return c_roll if kwargs.get('difficulty', None) is None else c_roll.checkDif(kwargs.get('difficulty'))

    def cycles_to_skip(self):
        last_update = self.Updated
        today = datetime.datetime.now().date().__str__()
        difference = TimeManager().date_difference(last_update, today)

        return difference


# class CharacterCombat:
#     def __init__(self, id:int, **kwargs):
#         self.id = id
#         self.data_manager = kwargs.get('data_manager', DataManager())
#
#         self.data = self.fetch_combat_data()
#         self.ap = self.data.get('ap',0)
#         self.ap_bonus = self.data.get('ap_bonus',0)
#         self.luck = self.data.get('luck',0)
#         self.blood_lost = self.data.get('blood_losst',0)
#         self.suppresed = self.data.get('suppressed',None)
#         self.hunted = self.data.get('hunted',None)
#         self.contained = self.data.get('contained',None)
#         self.ready = self.data.get('ready',None)
#         self.target = self.data.get('target',None)
#
#     def fetch_combat_data(self):
#         result = self.data_manager.select_dict('CHARS_COMBAT', '*', filter=f'id = {self.id}')
#         if result:  # Проверка, содержатся ли данные
#             return result[0]
#         return {}  # Возвращаем пустой словарь, если данные для id не найдены
#
#     def armors_id(self) -> dict:
#         c_equipment_data = self.data_manager.select_dict('CHARS_INVENTORY',
#                                                          filter=f'character_id = {self.id} AND slot != "Оружие"')
#         equipment = {}
#
#         for slot in c_equipment_data:
#             c_slot = slot.get('slot')
#             c_id = slot.get('item_id')
#             c_layer = Clothes(c_id).Layer
#
#             if c_slot not in equipment.keys():
#                 equipment[c_slot] = {c_layer: c_id}
#             else:
#                 equipment[c_slot][c_layer] = c_id
#
#         return equipment
#
#     def armors_protection(self) -> dict:
#         c_equipment_data = self.data_manager.select_dict('CHARS_INVENTORY',
#                                                          filter=f'character_id = {self.id} AND slot != "Оружие"')
#         equipment = {}
#
#         for slot in c_equipment_data:
#             c_slot = slot.get('slot')
#             c_id = slot.get('item_id')
#             c_layer = Clothes(c_id, data_manager=self.data_manager).Layer
#             if c_slot not in equipment.keys():
#                 equipment[c_slot] = {c_layer: Clothes(c_id, data_manager=self.data_manager).armor_protection()}
#             else:
#                 equipment[c_slot][c_layer] = Clothes(c_id, data_manager=self.data_manager).armor_protection()
#
#         return equipment
#
#     def simulate_penetration(self, c_slot:str, c_penetration: Penetration, damage: Damage, **kwargs) -> Damage | None:
#         n_armors = kwargs.get('armors_protection',self.armors_protection())
#
#         if c_slot not in n_armors:
#             return damage
#
#         c_armors = n_armors[c_slot]
#         c_armors_id = kwargs.get('armors_id',self.armors_id()[c_slot])
#         c_keys = sorted(c_armors.keys(), reverse=True)
#
#         curent_penetration = c_penetration.value
#         protection_type = c_penetration.name
#
#         for layer, (armor_id, protection) in zip(c_keys, zip(c_armors_id.values(), c_armors.values())):
#             c_protection = protection[protection_type].value
#
#             if curent_penetration - c_protection > 0:
#                 curent_penetration -= c_protection
#                 Clothes(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.Damage, 2))
#             else:
#                 Clothes(armor_id, data_manager=self.data_manager).change_endurance(round(-1 * damage.Damage * (curent_penetration / c_penetration.value), 2))
#                 return None
#
#         if curent_penetration < c_penetration.value * 0.5:
#             new_damage = int((curent_penetration / c_penetration.value) * damage.Damage)
#             return Damage(new_damage, damage_type=c_penetration.blocked_type, root=damage.Root, data_manager=self.data_manager) if int(new_damage) > 0 else None
#         else:
#             return damage
#
#     def current_weapons_id(self, item_id:int=None) -> list:
#         c_weapons_data = self.data_manager.select_dict('CHARS_INVENTORY',
#                                                          filter=f'character_id = {self.id} AND slot = "Оружие"')
#
#         weapons = []
#         for i in c_weapons_data:
#             weapons.append(i.get('item_id'))
#
#         if item_id is None:
#             return weapons
#         elif item_id in weapons:
#             return [item_id]
#         else:
#             return []
#
#     def has_melee_weapon(self):
#         c_weapons_data = self.data_manager.select_dict('CHARS_INVENTORY',
#                                                        filter=f'character_id = {self.id} AND slot = "Оружие"')
#
#         melee_weapons = []
#         for i in c_weapons_data:
#             if Weapon(i.get('item_id')).Class == 'ColdSteel':
#                 melee_weapons.append(i.get('item_id'))
#
#         return melee_weapons
#
#     def natural_conditions(self, **kwargs):
#         return {}
#
#     def self_attributes(self):
#         return CharacterAttributes(self.id, data_manager=self.data_manager)
#
#     def weapon_attack_cost(self, weapon_id:int = None):
#         c_weapon_id = random.choice(self.current_weapons_id(weapon_id))
#         if c_weapon_id is None:
#             return math.inf
#         else:
#             return Weapon(c_weapon_id, data_manager=self.data_manager).ActionPoints
#
#     def race_attack_cost(self, attack_id:str = None):
#         return RaceAttack(attack_id, data_manager=self.data_manager).cost
#
#     def range_attack(self, weapon_id:int=None, **kwargs):
#         c_weapon_id = self.current_weapons_id(weapon_id)
#         if c_weapon_id is None:
#             return None
#         else:
#             c_weapon = Weapon(random.choice(c_weapon_id), data_manager=self.data_manager)
#
#         enemy_id = kwargs.get('enemy_id', None)
#         if enemy_id:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = {}
#             enemy_main_part = Body(enemy_id, data_manager=self.data_manager).parent_part
#         else:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = kwargs.get('enemy_armors',{})
#             enemy_main_part = Race(kwargs.get('enemy_race','Human'), data_manager=self.data_manager).parent_part
#
#         natural_conditions = self.natural_conditions()
#
#         current_difficulty = c_weapon.AccuracyCheck(enemy_distance, enemy_cover, enemy_size)
#         total_damage = []
#
#         current_bullets = c_weapon.current_bullets()
#         if c_weapon.Mode == 1:
#             fire_rate = 1
#         elif c_weapon.Mode == 2:
#             fire_rate = 3 if not kwargs.get('fire_rate', None) else kwargs.get('fire_rate')
#         elif c_weapon.Mode == 3:
#             fire_rate = c_weapon.Attacks if not kwargs.get('fire_rate', None) else kwargs.get('fire_rate')
#         else:
#             fire_rate = c_weapon.Attacks
#
#         total_attacks = min(fire_rate, current_bullets) if current_bullets > 0 else fire_rate
#
#         c_current_ammo = c_weapon.get_current_ammo()
#
#         for attack in range(total_attacks):
#             c_damages = c_current_ammo.fire()
#             roll = self.self_attributes().roll_skill(c_weapon.Class, difficulty=current_difficulty)[0]
#             c_roll = roll
#
#             if c_roll:
#                 c_part = BodyPart(enemy_main_part, data_manager=self.data_manager) if kwargs.get('enemy_id', None) is None else LocalBodyPart(enemy_id, enemy_main_part, data_manager=self.data_manager)
#                 random_part, parent_part = c_part.choose_random_part()
#                 for damage in c_damages:
#                     c_penetration = damage.get('penetration')
#                     c_damage = damage.get('damage')
#
#                     c_slot = random_part.Slot if parent_part is None else parent_part.Slot
#
#                     if enemy_id:
#                         n_damage = CharacterCombat(enemy_id, data_manager=self.data_manager).simulate_penetration(c_slot, c_penetration, c_damage)
#                     else:
#                         n_damage = self.simulate_penetration(c_slot, c_penetration, c_damage,
#                                                              armors_protection=enemy_armors)
#
#                     if n_damage is not None:
#                         total_damage.append({'part_id': random_part.ID,
#                                              'damage': n_damage})
#
#         if total_damage and enemy_id is not None:
#             for damage in total_damage:
#                 Character(enemy_id, data_manager=self.data_manager).recive_damage(part_id=damage.get('part_id'),
#                                                   damage_list=damage.get('damage'))
#
#         c_weapon_loud = c_weapon.total_noise()
#
#         return total_damage, total_attacks, c_weapon_loud
#
#     def melee_attack(self, weapon_id:int=None, **kwargs):
#         c_weapon_id = self.current_weapons_id(weapon_id)
#         if c_weapon_id is None:
#             return None
#         else:
#             c_weapon = Weapon(random.choice(c_weapon_id), data_manager=self.data_manager)
#
#         enemy_id = kwargs.get('enemy_id', None)
#         if enemy_id:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = {}
#             enemy_main_part = Body(enemy_id, data_manager=self.data_manager).parent_part
#             enemy_skill = 'ColdSteel' if CharacterCombat(enemy_id, data_manager=self.data_manager).has_melee_weapon() else 'MartialArms'
#             print('Я ТУТ')
#         else:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = kwargs.get('enemy_armors', {})
#             enemy_main_part = Race(kwargs.get('enemy_race', 'Human'), data_manager=self.data_manager).parent_part
#             enemy_skill = random.choice(['MartialArms','ColdSteel'])
#
#         total_damage = []
#
#         c_pain = Body(self.id).calculate_total_pain()
#         c_attacks = c_weapon.melee_attacks()
#
#         c_penetration_bonus = (max(self.self_attributes().check_characteristic('Ловкость'), self.self_attributes().check_characteristic('Сила')) - 20) / 2
#         c_damage_bonus = (self.self_attributes().check_characteristic('Сила') - 20) / 2
#
#         for attack in range(c_attacks):
#             if enemy_id:
#                 e_roll = CharacterCombat(enemy_id, data_manager=self.data_manager).self_attributes().roll_skill(enemy_skill)
#             else:
#                 e_roll = random.randint(0,100)
#
#
#             c_roll = self.self_attributes().roll_skill('ColdSteel', difficulty=e_roll)[0]
#             if c_roll:
#                 c_part = BodyPart(enemy_main_part, data_manager=self.data_manager) if kwargs.get('enemy_id',None) is None else LocalBodyPart(enemy_id, enemy_main_part, data_manager=self.data_manager)
#                 random_part, parent_part = c_part.choose_random_part()
#                 c_damages = c_weapon.melee_damage()
#                 for damage in c_damages:
#                     c_penetration = damage.get('penetration') + c_penetration_bonus
#                     c_damage = damage.get('damage') + int(c_damage_bonus)
#
#                     c_slot = random_part.Slot if parent_part is None else parent_part.Slot
#                     if enemy_id:
#                         n_damage = CharacterCombat(enemy_id, data_manager=self.data_manager).simulate_penetration(c_slot, c_penetration, c_damage)
#                     else:
#                         n_damage = self.simulate_penetration(c_slot, c_penetration, c_damage,armors_protection=enemy_armors)
#
#                     if n_damage is not None:
#                         total_damage.append({'part_id': random_part.ID,
#                                              'damage': n_damage})
#         if total_damage and enemy_id is not None:
#             for damage in total_damage:
#                 Character(enemy_id, data_manager=self.data_manager).recive_damage(part_id=damage.get('part_id'),
#                                                                                   damage_list=damage.get('damage'))
#         c_weapon_loud = c_weapon.total_noise()
#
#         return total_damage, c_attacks, c_weapon_loud
#
#     def race_attack(self, attack_id:str=None, **kwargs):
#         c_body = Body(self.id, data_manager=self.data_manager)
#         if attack_id is not None:
#             if not attack_id in c_body.available_attacks():
#                 return None
#             else:
#                 c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
#                 c_body_part = c_body.part_of_attack(attack_id)
#         else:
#             if not c_body.available_attacks():
#                 return None
#             else:
#                 attack_id = random.choice(c_body.available_attacks())
#                 c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
#                 c_body_part = c_body.part_of_attack(attack_id)
#
#         enemy_id = kwargs.get('enemy_id', None)
#         if enemy_id:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = {}
#             enemy_main_part = Body(enemy_id, data_manager=self.data_manager).parent_part
#             enemy_skill = 'MartialArms'
#             print('Я ТУТ')
#         else:
#             enemy_cover = kwargs.get('enemy_cover', 0)
#             enemy_distance = kwargs.get('enemy_distance', 100)
#             enemy_size = kwargs.get('enemy_size', 1)
#             enemy_armors = kwargs.get('enemy_armors', {})
#             enemy_main_part = Race(kwargs.get('enemy_race', 'Human'), data_manager=self.data_manager).parent_part
#             enemy_skill = 'MartialArms'
#
#         c_penetration_bonus = (max(self.self_attributes().check_characteristic('Ловкость'),
#                                    self.self_attributes().check_characteristic('Сила')) - 20) / 2
#         c_damage_bonus = (self.self_attributes().check_characteristic('Сила') - 20) / 2
#
#         total_damage = []
#
#         total_attacks = c_attack.main_data.get('attacks', 1)
#         for i in range(total_attacks):
#             if enemy_id:
#                 e_roll = CharacterCombat(enemy_id, data_manager=self.data_manager).self_attributes().roll_skill(enemy_skill)
#             else:
#                 e_roll = random.randint(0,100)
#
#             c_roll = self.self_attributes().roll_skill('MartialArms', difficulty=e_roll)[0]
#
#             if c_roll:
#                 c_part = BodyPart(enemy_main_part, data_manager=self.data_manager) if kwargs.get('enemy_id',None) is None else LocalBodyPart(enemy_id, enemy_main_part, data_manager=self.data_manager)
#                 random_part, parent_part = c_part.choose_random_part()
#                 c_damages = c_body_part.part_attack(attack_id)
#                 for damage in c_damages:
#                     c_penetration = damage.get('penetration') + c_penetration_bonus
#                     c_damage = damage.get('damage') + int(c_damage_bonus)
#
#                     c_slot = random_part.Slot if parent_part is None else parent_part.Slot
#
#                     if enemy_id:
#                         n_damage = CharacterCombat(enemy_id, data_manager=self.data_manager).simulate_penetration(
#                             c_slot, c_penetration, c_damage)
#                     else:
#                         n_damage = self.simulate_penetration(c_slot, c_penetration, c_damage,
#                                                              armors_protection=enemy_armors)
#
#                     if n_damage is not None:
#                         total_damage.append({'part_id': random_part.ID,
#                                              'damage': n_damage})
#
#         if total_damage and enemy_id is not None:
#             for damage in total_damage:
#                 Character(enemy_id, data_manager=self.data_manager).recive_damage(part_id=damage.get('part_id'),
#                                                                                   damage_list=damage.get('damage'))
#
#         return total_damage, total_attacks
#
#     def vehicle_attack(self):
#         pass


class InterCharacter:
    def __init__(self, character_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = character_id

        data = self.fetch_character_data()
        self.custom_id = data.get('custom_id', self.id)
        self.owner = data.get('owner', None)
        self.callsign = data.get('callsign', '')
        self.age = data.get('age', 30)
        self.name = data.get('name', 'Неизвестный')
        self.race = data.get('race', 'Human')
        self.sex = data.get('sex', 'Неизвестно')

        self.org = data.get('org', None)
        self.org_lvl = data.get('org_lvl', None)
        self.frac = data.get('frac', None)
        self.frac_lvl = data.get('frac_lvl', None)

        self.avatar = data.get('avatar', None)
        self.updated = data.get('update', None)
        self.server = data.get('server', None)

    def fetch_character_data(self):
        if self.data_manager.check('CHARS_INIT', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_INIT',filter=f'id = {self.id}')[0]
        else:
            return {}

    def fetch_race_data(self):
        pass

    def fetch_health_data(self):
        injury_text = self.data_manager.select_dict(f'CHARS_INJURY', filter=f'id = {self.id}')
        diseses_text = self.data_manager.select_dict(f'CHARS_DISEASE', filter=f'id = {self.id}')
        return injury_text, diseses_text

    def fetch_combat_data(self):
        pass

    def fetch_inventory_data(self):
        pass

    def fetch_gears_data(self):
        pass

    def fetch_location_data(self):
        pass

    def fetch_memories(self):
        pass

    def fetch_relations(self):
        pass

    def fetch_worldview(self):
        pass

    def fetch_group_data(self):
        pass

    def fetch_progress(self):
        pass

    def fetch_skills(self):
        attrs = CharacterAttributes(self.id, data_manager=self.data_manager)
        chars = attrs.characteristics_list()
        skills = attrs.skill_list()

        chars_text = ''
        for char in chars:
            if char != 'Связь':
                chars_text += f'\n> **{chars[char].name}** - {chars[char].lvl}'

        skill_text = ''
        print(skills)
        for skill in skills:
            print(skill)
            talant_emoji = ''
            if 1.5 > skills[skill].talant >= 1.25:
                talant_emoji = ' <:talant_25:1250156284792144096> '
            elif 1.75 > skills[skill].talant >= 1.5:
                talant_emoji = ' <:talant_50:1250156286633443379> '
            elif 2 > skills[skill].talant >= 1.75:
                talant_emoji = ' <:talant_75:1250156288697045164> '
            elif skills[skill].talant >= 2:
                talant_emoji = ' <:talant_100:1250156290630615140> '

            mastery_emoji = ''
            if 1.5 > skills[skill].mastery >= 1.25:
                mastery_emoji = '<:mastery_25:1250160742716543196> '
            elif 1.75 > skills[skill].mastery >= 1.5:
                mastery_emoji = '<:mastery_50:1250160740648615998> '
            elif 2 > skills[skill].mastery >= 1.75:
                mastery_emoji = '<:mastery_75:1250160738933149757> '
            elif skills[skill].mastery >= 2:
                mastery_emoji = '<:mastery_100:1250160736651444314> '

            skill_text += f'\n> {mastery_emoji}**{skills[skill].get_skill_label(self.data_manager)}**{talant_emoji} — {skills[skill].lvl}% ({skills[skill].exp:.2f})'

        return chars_text, skill_text

    def cycles_to_skip(self):
        return Character(self.id, data_manager=self.data_manager).cycles_to_skip()

    def __str__(self):
        year_marker = 'лет'
        if self.age:
            if self.age%10 in [2,3,4]:
                year_marker = 'года'
            elif self.age%10 in [1]:
                year_marker = 'год'

        text = f"""
**Имя Фамилия:** {self.name} {f'"{self.callsign}"' if self.callsign else ''}
**Раса:** {Race(self.race).Name}
**Пол:** {self.sex}
**Возраст:** {self.age} {year_marker}

{f'**Организация:** {self.org}' if self.org else ''}
{f'**Фракция:** {self.frac}' if self.frac else ''}
        """
        return text