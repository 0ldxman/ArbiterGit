from ArbDatabase import DataManager
import random
from dataclasses import dataclass
from ArbDamage import Injury


@dataclass
class Capacity:
    name: str
    value: float  # Значение физического показателя в %

    def __repr__(self):
        return f'{self.name} ({self.value:.2f}%)'

    def __add__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value + other
            return Capacity(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value + other.value
            return Capacity(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value - other
            return Capacity(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value - other.value
            return Capacity(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __rsub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            new_value = self.value * other
            return Capacity(name=self.name, value=new_value)
        elif self.name == other.name:
            new_value = self.value * (other.value/100)
            return Capacity(name=self.name, value=new_value)
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.value == other
        elif isinstance(other, Capacity):
            return self.name == other.name and self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.value < other
        elif isinstance(other, Capacity):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.value <= other
        elif isinstance(other, Capacity):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.value > other
        elif isinstance(other, Capacity):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.value >= other
        elif isinstance(other, Capacity):
            return self.value >= other.value
        return NotImplemented


class BodyPart:
    def __init__(self, part_id: str, *, data_manager:DataManager=None):
        self.ID = part_id
        if data_manager:
            self.data_manager = data_manager
        else:
            self.data_manager = DataManager()

        if self.data_manager.check('RACES_BODY', f'part_id = "{self.ID}"'):
            self.data_table = 'RACES_BODY'
        else:
            self.data_table = 'IMPLANTS_INIT'

        data = self.fetch_data()

        self.Label = data.get('label', '')
        self.Slot = data.get('name', '')
        self.IsInternal = data.get('internal', False)
        self.LinkedPartID = data.get('linked', None)
        self.TargetWeight = data.get('target_weight', 1)
        self.Health = data.get('health', 0)
        self.ScarChance = data.get('scar_chance', 0)
        self.Fatality = data.get('fatality', 0)
        self.BleedFactor = data.get('bleed_factor', 0)
        self.Capacity = data.get('capacity', '')
        self.Efficiency = data.get('efficiency', 0)
        self.IsImplant = self.data_table == 'IMPLANTS_INIT'
        self.WeaponSlots = data.get('weapon_slot', 0)

    def fetch_data(self) -> dict:
        columns = ['label', 'name', 'internal', 'linked', 'target_weight', 'health', 'scar_chance', 'fatality',
                   'bleed_factor', 'capacity', 'efficiency', 'weapon_slot']
        data = {}

        for col in columns:
            data[col] = self.data_manager.selectOne(self.data_table, columns=col, filter=f'part_id = "{self.ID}"')[0]
        return data

    def get_internal_organs(self):
        organ_table = "RACES_BODY"  # Предположим, что есть таблица с информацией об органах
        filter = f'linked = "{self.ID}" AND internal = 1'  # Предположим, что связанная часть тела имеет идентификатор item_id

        # Используем метод select_dict для получения информации об органах внутри данной части тела
        internal_organs = self.data_manager.select_dict(organ_table, columns='*', filter=filter)

        return internal_organs

    def get_external_parts(self):
        organ_table = "RACES_BODY"  # Предположим, что есть таблица с информацией об органах
        filter = f'linked = "{self.ID}" AND internal = 0'  # Предположим, что связанная часть тела имеет идентификатор item_id

        # Используем метод select_dict для получения информации об органах внутри данной части тела
        internal_organs = self.data_manager.select_dict(organ_table, columns='*', filter=filter)

        return internal_organs

    def choose_random_part(self, roll:float=random.randint(0,100)):
        c_part = random.choice([self, self.choose_random_external_part()])
        print(c_part, c_part.get_internal_organs())
        if roll >= 80 and c_part.get_internal_organs():
            return c_part.choose_random_internal_part(), c_part
        else:
            return c_part, None

    def choose_random_internal_part(self):
        internal_organs = self.get_internal_organs()

        if not internal_organs:
            return None

        total_weight = sum(organ['target_weight'] for organ in internal_organs)
        random_weight = random.uniform(0, total_weight)

        current_weight = 0
        for organ in internal_organs:
            current_weight += organ['target_weight']
            if random_weight <= current_weight:
                return BodyPart(organ['part_id'], data_manager=self.data_manager)

        return None

    def choose_random_external_part(self):
        internal_organs = self.get_external_parts()
        if not internal_organs:
            return None

        total_weight = sum(organ['target_weight'] for organ in internal_organs)
        random_weight = random.uniform(0, total_weight)

        current_weight = 0
        for organ in internal_organs:
            current_weight += organ['target_weight']
            if random_weight <= current_weight:
                return BodyPart(organ['part_id'],data_manager=self.data_manager)

        return None

    def attacks(self) -> list | None:
        c_attacks = []

        if self.IsImplant and self.data_manager.check('IMPLANTS_MELEE', f'implant_id = "{self.ID}"'):
            c_attacks = self.data_manager.select('IMPLANTS_MELEE', columns='id', filter=f'implant_id = "{self.ID}"')
        elif self.data_manager.check('RACES_MELEE', f'part_id = "{self.ID}"'):
            c_attacks = self.data_manager.select('RACES_MELEE', columns='id', filter=f'part_id = "{self.ID}"')

        if not c_attacks:
            return None
        else:
            return [attack[0] for attack in c_attacks]

    def get_affected_capacity(self, total_damage: int) -> Capacity | None:
        if self.Capacity:
            hp = max(self.Health - total_damage, 0)  # Учитываем уровень повреждений

            if self.Efficiency >= 0:
                affected_value = (hp / self.Health) * self.Efficiency
            else:
                affected_value = ((self.Health - hp) / self.Health) * self.Efficiency

            return Capacity(name=self.Capacity, value=affected_value)
        else:
            return None

    def __str__(self):
        return f'{self.Label} ({self.ID})'

    def __repr__(self):
        if self.IsImplant:
            return f'BodyImplant.{self.ID}'
        else:
            return f'BodyPart.{self.ID}'


class LocalBodyPart(BodyPart):
    def __init__(self, char_id: int, part_id: str, *, data_manager=None):
        super().__init__(part_id, data_manager=data_manager)
        self.CharID = char_id
        self.CurrentHealth = self.Health
        self.data_manager = data_manager if data_manager else DataManager()

        self.process_injuries()
        self.calculate_efficiency()
        self.process_illnesses()

        self.injuries = []
        self.fetch_injuries()

    def process_injuries(self):
        injuries = self.data_manager.select('CHARS_INJURY', columns='id_inj', filter=f'id = {self.CharID} AND place = "{self.ID}"')
        if injuries:
            for injury_id in injuries:
                injury_data = self.data_manager.select_dict('CHARS_INJURY', columns='damage', filter=f'id_inj = {injury_id[0]}')[0]
                self.CurrentHealth -= injury_data.get('damage', 0)

    def fetch_injuries(self):
        injury_data = self.data_manager.select('CHARS_INJURY',columns='id_inj', filter=f'place = "{self.ID}" AND id = {self.CharID}')
        for data in injury_data:
            new_injury = LocalInjury(data[0], self.CharID,data_manager=self.data_manager)
            self.injuries.append(new_injury)

    def calculate_efficiency(self):
        if self.Efficiency > 0:
            self.CurrentEfficiency = self.Efficiency * (self.CurrentHealth / self.Health)
        else:
            if self.CurrentHealth == self.Health:
                self.CurrentEfficiency = 0
            else:
                self.CurrentEfficiency = self.Efficiency * ((self.Health - self.CurrentHealth) / self.Health)

    def process_illnesses(self):
        diseases = self.data_manager.select('CHARS_DISEASE', columns='dis_id', filter=f'id = {self.CharID}')
        if diseases:
            for disease_id in diseases:
                disease = LocalDisease(data_manager=self.data_manager, dis_id=disease_id[0], char_id=self.CharID)
                if disease.Place == self.ID:
                    self.CurrentEfficiency -= disease.Severity * disease.Affect
                if disease.Capacity == self.Capacity:
                    self.CurrentEfficiency -= disease.Severity * disease.Effect

    def calculate_bleeding(self):
        total_bleeding = sum(injury.Bleed for injury in self.injuries) * self.BleedFactor
        return max(0, total_bleeding)

    def calculate_pain(self):
        total_pain = 0
        for injury in self.injuries:
            pain_factor = getattr(injury, 'PainFactor', 0)
            total_pain += (injury.Damage - (injury.Damage * (injury.HealingEfficiency / 70))) * pain_factor

        return total_pain

    def affected_capacity(self) -> Capacity | None:
        if self.Capacity:
            return Capacity(name=self.Capacity, value=self.CurrentEfficiency)
        else:
            return None

    def part_attacks(self):
        if self.CurrentHealth/self.Health < 0.5:
            return []
        else:
            return self.attacks()

    def part_attack(self, attack_id:str):
        if attack_id not in self.attacks():
            return None
        else:
            total_damage = []
            c_attack = RaceAttack(attack_id, data_manager=self.data_manager)
            c_damages = c_attack.attack()
            for damage in c_damages:
                c_damage = damage.get('damage') * (self.CurrentHealth/self.Health)
                c_penetration = damage.get('penetration') * (self.CurrentHealth/self.Health)
                total_damage.append({'damage': c_damage,
                                     'penetration': c_penetration})

            return total_damage


class LocalInjury(Injury):
    def __init__(self, inj_id: int, char_id: int, *, data_manager=None):
        self.InjuryID = inj_id
        self.CharID = char_id
        self.data_manager = data_manager if data_manager else DataManager()
        injury_data = self.my_fetch_data()
        self.type = injury_data.get('type', '')

        super().__init__(self.type, data_manager=self.data_manager)  # Вызываем суперкласс с типом полученным из базы данных

        self.Place = injury_data.get('place', '')
        self.Root = injury_data.get('root', '')
        self.Damage = injury_data.get('damage', 0)
        self.Bleed = injury_data.get('bleed', 0)
        self.HealingEfficiency = injury_data.get('heal_efficiency', 0)
        self.IsScar = injury_data.get('is_scar', False) == 1

    def my_fetch_data(self) -> dict:
        data = {}
        columns = ['type', 'place', 'root', 'damage', 'bleed', 'heal_efficiency', 'is_scar']
        for col in columns:
            data[col] = self.data_manager.selectOne('CHARS_INJURY', columns=col, filter=f'id_inj = {self.InjuryID} AND id = {self.CharID}')[0]

        return data

    def delete(self):
        self.data_manager.delete('CHARS_INJURY', filter=f'id = {self.CharID} AND id_inj = {self.InjuryID}')


class Disease:
    def __init__(self, name: str):
        self.data_manager = DataManager()

        self.ID = name
        self.Name = None
        self.PainFactor = None
        self.Affect = None
        self.Capacity = None
        self.Effect = None
        self.Fatal = False
        self.StartSeverity = None
        self.SeveritySpeed = None
        self.ImmunitySpeed = None
        self.RecoverySpeed = None
        self.NextStage = None

        data = self.my_fetch_data()

        if data:
            self.Name = data.get('name')
            self.PainFactor = data.get('pain', 0)
            self.Affect = data.get('affect', 0)
            self.Capacity = data.get('capacity', 0)
            self.Effect = data.get('effect', 0)
            self.Fatal = data.get('fatal', False)
            self.StartSeverity = data.get('start', 0)
            self.SeveritySpeed = data.get('severity', 0)
            self.ImmunitySpeed = data.get('immunity', 0)
            self.RecoverySpeed = data.get('recover', 0)
            self.NextStage = data.get('next_stage', '')

    def my_fetch_data(self) -> dict:
        columns = ['name', 'pain', 'affect', 'capacity', 'effect', 'fatal', 'start', 'severity', 'immunity', 'recover',
                   'next_stage']
        data = {}

        for col in columns:
            data[col] = self.data_manager.selectOne('DISEASE_INIT', columns=col, filter=f'id = "{self.ID}"')[0]

        return data

    def __repr__(self):
        return self.Name


class LocalDisease(Disease):
    def __init__(self, dis_id: int, char_id: int, *, data_manager=None):
        self.DiseaseID = dis_id
        self.CharID = char_id
        self.data_manager = data_manager if data_manager else DataManager()
        disease_data = self.fetch_data()
        self.type = disease_data.get('type','')

        super().__init__(self.type)  # Вызываем суперкласс без передачи аргументов по умолчанию

        self.Place = disease_data.get('place', '')
        self.Severity = disease_data.get('severity', 0)
        self.Healing = disease_data.get('healing', 0)
        self.Immunity = disease_data.get('immunity', 0)

    def fetch_data(self) -> dict:
        data = {}

        columns = ['type', 'place', 'severity', 'healing', 'immunity']
        for col in columns:
            data[col] = self.data_manager.selectOne('CHARS_DISEASE', columns=col, filter=f'id = {self.CharID} AND dis_id = {self.DiseaseID}')[0]

        return data


class RaceAttack:
    def __init__(self, attack_id:str, **kwargs):
        self.id = attack_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.damage = self.fetch_damage()
        self.part_name = self.fetch_body_part_name()
        self.main_data = self.fetch_main_data()
        self.cost = self.main_data.get('ap', 0)
        self.range = self.main_data.get('range', 0)

    def fetch_main_data(self):
        if self.data_manager.check('RACES_MELEE', f'id = "{self.id}"'):
            return self.data_manager.select_dict('RACES_MELEE', filter=f'id = "{self.id}"')[0]
        elif self.data_manager.check('IMPLANTS_MELEE', f'id = "{self.id}"'):
            return self.data_manager.select_dict('IMPLANTS_MELEE', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def fetch_body_part_name(self):
        c_part_id_info = self.data_manager.select_dict('RACES_MELEE', filter=f'id = "{self.id}"')
        if c_part_id_info:
            c_part_id = c_part_id_info[0].get('part_id', None)
        else:
            c_part_id_info = self.data_manager.select_dict('IMPLANTS_MELEE', filter=f'id = "{self.id}"')
            if c_part_id_info:
                c_part_id = c_part_id_info[0].get('implant_id', None)
            else:
                return None

        if not c_part_id:
            return None
        else:
            if self.data_manager.check('RACES_BODY', f'part_id = "{c_part_id}"'):
                c_part_name = self.data_manager.select_dict('RACES_BODY', filter=f'part_id = "{c_part_id}"')[0]
            elif self.data_manager.check('IMPLANTS_BODY', f'part_id = "{c_part_id}"'):
                c_part_name = self.data_manager.select_dict('IMPLANTS_BODY', filter=f'part_id = "{c_part_id}"')[0]
            else:
                c_part_name = {"label": "Неизвестно", "race": "Неизвестно"}

            c_race_name = self.data_manager.select_dict('RACES_INIT', filter=f'id = "{c_part_name.get("race")}"')[0]
            return f'{c_part_name.get("label", "Неизвестно")} ({c_race_name.get("name", "Неизвестно")})'

    def fetch_damage(self):
        if self.data_manager.check('RACES_DAMAGE', f'id = "{self.id}"'):
            return self.data_manager.select_dict('RACES_DAMAGE', filter=f'id = "{self.id}"')
        elif self.data_manager.check('IMPLANTS_DAMAGE', f'id = "{self.id}"'):
            return self.data_manager.select_dict('IMPLANTS_DAMAGE', filter=f'id = "{self.id}"')
        else:
            return []

    def attack(self) -> list:
        from ArbDamage import Damage, Penetration
        damage_list = []
        for damage in self.damage:
            crit_mod = damage.get('critical_multiplier', 1) if random.randint(0, 100) >= 100 * damage.get('critical_chance', 1) else 1

            damage_value = random.randint(damage.get('min_damage', 0), damage.get('max_damage', 0)) * crit_mod
            total_damage = Damage(damage_value, damage.get('damage_type', 'Hit'), root=self.part_name,data_manager=self.data_manager)

            protection_type = self.data_manager.select_dict('DAMAGE_TYPE', filter=f'id = "{total_damage.Type.damage_id}"')[0].get('protection_type')

            c_pars = {'damage': total_damage,'penetration': Penetration(name=protection_type, value=damage.get('penetration'), blocked_type=damage.get('blocked_type'))}

            damage_list.append(c_pars)
        return damage_list


class Body:
    def __init__(self, character_id: int, **kwargs):
        self.data_manager = kwargs.get('data_manager',DataManager())
        self.character_id = character_id

        # Получаем информацию о расе персонажа из таблицы CHARS_INIT
        self.race = self.data_manager.selectOne("CHARS_INIT", columns="race", filter=f"id = {self.character_id}")[0]

        self.body_parts = self.fetch_bodyparts()
        self.parent_part = self.data_manager.selectOne("RACES_BODY", columns="part_id", filter=f'race = "{self.race}" AND linked is NULL')[0]

    def fetch_bodyparts(self):
        body_parts = []
        # Получаем список частей тела для данной расы из таблицы RACES_BODY
        body_parts_data = self.data_manager.select("RACES_BODY", columns="part_id", filter=f'race = "{self.race}"')

        for part_id in body_parts_data:
            # Проверяем, есть ли имплант, замещающий данную часть тела
            is_implant_present = self.data_manager.check("CHARS_BODY",
                                                         f"id = '{self.character_id}' AND place = '{part_id[0]}'")
            if is_implant_present:
                implant_id = self.data_manager.selectOne("CHARS_BODY", columns="imp_id",
                                                         filter=f"id = {self.character_id} AND place = '{part_id[0]}'")[0]
                part = LocalBodyPart(self.character_id, implant_id, data_manager=self.data_manager)  # Заменяем часть тела имплантом
            else:
                part = LocalBodyPart(self.character_id, part_id[0], data_manager=self.data_manager) # Используем оригинальную часть тела

            body_parts.append(part)

        return body_parts

    def physical_stats(self):
        physical_stats = {}

        # Собираем исходные физические показатели персонажа
        for part in self.body_parts:
            if part.Efficiency is None or part.Efficiency == 0:
                continue

            if part.Capacity in physical_stats:
                if isinstance(physical_stats[part.Capacity], int) or isinstance(physical_stats[part.Capacity], float):
                    physical_stats[part.Capacity] += part.affected_capacity().value
                else:
                    physical_stats[part.Capacity] += part.affected_capacity()
            else:
                physical_stats[part.Capacity] = part.affected_capacity().value

        # Применяем влияние одних показателей на другие
        affects_data = self.data_manager.select("CAPACITIES_AFFECTS", columns="name, affect, weight, max")

        for affect_data in affects_data:
            affecting_capacity = affect_data[0]
            affected_capacity = affect_data[1]
            effect_weight = affect_data[2]
            max_effect = affect_data[3]

            if affecting_capacity in physical_stats and affected_capacity in physical_stats:
                affecting_value = physical_stats[affecting_capacity]
                affected_value = physical_stats[affected_capacity]

                delta = (100-affecting_value) * effect_weight
                if delta > max_effect:
                    delta = max_effect

                if isinstance(affected_value, int) or isinstance(affected_value, float):
                    physical_stats[affected_capacity] = affected_value - delta
                else:
                    physical_stats[affected_capacity] = Capacity(name=affected_capacity, value=affected_value - delta)

        return physical_stats

    def physical_stat(self, stat_name:str):
        stats = self.physical_stats()
        return stats[stat_name]

    def calculate_total_bleeding(self):

        bleed_filter = self.physical_stat('Кровообращение')

        total_bleeding = sum(part.calculate_bleeding() for part in self.body_parts)
        total_bleeding = max(total_bleeding - bleed_filter, 0)

        return total_bleeding

    def time_to_bleed_out(self):
        c_bleed = self.calculate_total_bleeding()
        race_blood = self.data_manager.selectOne("RACES_INIT", columns="blood", filter=f"id = '{self.race}'")[0]

        return c_bleed / race_blood

    def calculate_total_pain(self):
        c_data = self.data_manager.select_dict("RACES_INIT", columns='*', filter=f"id = '{self.race}'")[0]
        pain_factor = c_data.get('pain_factor', 1)
        pain_limit = c_data.get('pain_limit', 100)


        total_pain = sum(part.calculate_pain() for part in self.body_parts)

        print(total_pain, pain_limit, pain_factor)
        total_pain = (total_pain * pain_factor) / pain_limit

        return total_pain * 100

    def available_attacks(self):
        total_attacks = []
        for i in self.body_parts:
            if i.part_attacks() is not None:
                total_attacks += i.part_attacks()

        return total_attacks

    def attacks(self):
        total_attacks = []
        for i in self.body_parts:
            if i.part_attacks() is not None:
                total_attacks.append({'part_id': i.ID,
                                      'attacks': i.part_attacks()})

        return total_attacks

    def part_of_attack(self, attack_id:str):
        c_attacks = self.available_attacks()
        c_parts_and_attacks = self.attacks()
        if attack_id not in c_attacks:
            return None
        else:
            for i in c_parts_and_attacks:
                if attack_id in i.get('attacks'):
                    return LocalBodyPart(self.character_id, i.get('part_id'), data_manager=self.data_manager)