import pprint

from ArbDatabase import DataManager
import random
from dataclasses import dataclass
from ArbDamage import Injury, Damage


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
            self.id_label = 'part_id'
        else:
            self.data_table = 'IMPLANTS_INIT'
            self.id_label = 'id'

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

        self.can_replace = data.get('can_replace', None)


    def fetch_data(self) -> dict:
        if self.data_manager.check(self.data_table, filter=f'{self.id_label} = "{self.ID}"') is None:
            return {}
        else:
            return self.data_manager.select_dict(self.data_table, filter=f'{self.id_label} = "{self.ID}"')[0]

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
    def __init__(self, char_id: int, part_id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        if isinstance(part_id, int):
            part = self.data_manager.select_dict('CHARS_BODY',filter=f'imp_id = {part_id}')[0].get('type')
        else:
            part = part_id

        super().__init__(part, data_manager=self.data_manager)
        self.ID = part_id

        self.CharID = char_id
        self.CurrentHealth = self.Health
        self.Place = kwargs.get('place', None)
        self.Label = kwargs.get('label', self.Label)

        self.process_injuries()
        self.calculate_efficiency()
        self.process_illnesses()

        self.injuries = []
        self.fetch_injuries()
        self.diseases = self.fetch_diseases()

    def process_injuries(self):
        injuries = self.data_manager.select('CHARS_INJURY', columns='id_inj', filter=f'id = {self.CharID} AND place = "{self.ID}"')
        if injuries:
            for injury_id in injuries:
                injury_data = self.data_manager.select_dict('CHARS_INJURY', filter=f'id = {self.CharID} AND id_inj = {injury_id[0]}')[0]
                self.CurrentHealth -= injury_data.get('damage', 0)

    def fetch_injuries(self):
        injury_data = self.data_manager.select('CHARS_INJURY',columns='id_inj', filter=f'place = "{self.ID}" AND id = {self.CharID}')
        for data in injury_data:
            new_injury = LocalInjury(data[0], self.CharID, data_manager=self.data_manager)
            self.injuries.append(new_injury)

    def calculate_efficiency(self):
        if self.Efficiency > 0:
            self.CurrentEfficiency = self.Efficiency * (self.CurrentHealth / self.Health)
            if self.CurrentEfficiency < 0:
                self.CurrentEfficiency = 0

        else:
            if self.CurrentHealth == self.Health:
                self.CurrentEfficiency = 0
            else:
                self.CurrentEfficiency = self.Efficiency * ((self.Health - self.CurrentHealth) / self.Health)

    def part_health(self):
        health = self.CurrentHealth/self.Health if self.Health > 0 else 0
        return health if health > 0 else 0

    def process_illnesses(self):
        diseases = self.data_manager.select('CHARS_DISEASE', columns='dis_id', filter=f'id = {self.CharID} AND (place = "{self.ID}" OR place = "All")')
        if diseases and not self.IsImplant:
            for disease_id in diseases:
                disease = LocalDisease(data_manager=self.data_manager, dis_id=disease_id[0], char_id=self.CharID)
                if disease.Place == self.ID:
                    self.CurrentEfficiency -= disease.Severity * disease.Affect
                if disease.Capacity == self.Capacity:
                    self.CurrentEfficiency -= disease.Severity * disease.Effect

    def fetch_diseases(self):
        total_list = []
        diseases = self.data_manager.select_dict('CHARS_DISEASE', filter=f'id = {self.CharID} and (place = "{self.ID}" OR place = "All")')
        if diseases and not self.IsImplant:
            for disease_id in diseases:
                disease = LocalDisease(data_manager=self.data_manager, dis_id=disease_id.get('dis_id'), char_id=self.CharID)
                total_list.append(disease)

        return total_list

    def calculate_bleeding(self):
        if not self.IsImplant:
            total_bleeding = sum(injury.Bleed for injury in self.injuries) * self.BleedFactor
            return max(0, total_bleeding)
        else:
            return 0

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

    def get_root_partlabel(self):
        if not self.IsImplant:
            return None
        else:
            if not self.data_manager.check('CHARS_BODY',f'id = {self.CharID} AND imp_id = {self.ID} AND place = "{self.Place}"'):
                return None
            else:
                return BodyPart(self.Place, data_manager=self.data_manager).Label

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

    def delete_injuries(self):
        self.data_manager.delete('CHARS_INJURY',f'id = {self.CharID} AND place = "{self.ID}"')

    def calculate_overkill(self, damage:int, overkill_roll:int):
        if (self.CurrentHealth-damage > 0) or self.Health <= 0:
            return False

        damage_overkill = damage*(overkill_roll/100)

        overkill_chance = (damage_overkill / self.Health)*100
        c_roll = random.randint(0, 100)
        print(overkill_chance, c_roll)
        if c_roll <= overkill_chance:
            return True
        else:
            return False

    def apply_implant(self, type:str, label:str):
        if not self.data_manager.check('CHARS_BODY', f'id = {self.CharID}'):
            c_id = 0
        else:
            c_id = self.data_manager.maxValue('CHARS_BODY', 'imp_id', f'id = {self.CharID}') + 1

        query = {'id': self.CharID,
                 'imp_id': c_id,
                 'place': self.ID,
                 'linked': None,
                 'type': type,
                 'label': label}

        self.data_manager.insert('CHARS_BODY',query)

    def apply_damage(self, damage: Damage, effect:bool=False):
        if damage.Damage <= 0:
            return None

        if self.calculate_overkill(damage.Damage, random.randint(damage.Type.min_overkill, damage.Type.max_overkill)):
            damage_label = f'{damage.Type.destruction_label} ({damage.Root})'
            self.delete_injuries()
            self.apply_implant('Destroyed', damage_label)
            return None

        if not self.data_manager.check('CHARS_INJURY', f'id = {self.CharID}'):
            c_id = 0
        else:
            c_id = self.data_manager.maxValue('CHARS_INJURY', 'id_inj', f'id = {self.CharID}') + 1

        c_type = random.choice(damage.Type.get_possible_injuries())
        bleed_chance = c_type.Bleed * damage.Damage * self.BleedFactor
        c_roll = random.randint(0, 100)

        if c_roll <= bleed_chance:
            c_bleed = c_type.Bleed * damage.Damage
        else:
            c_bleed = 0

        self.data_manager.insert('CHARS_INJURY', {'id': self.CharID,
                                                  'id_inj': c_id,
                                                  'place': self.ID,
                                                  'type': c_type.ID,
                                                  'root': damage.Root,
                                                  'damage': damage.Damage,
                                                  'bleed': c_bleed,
                                                  'heal_efficiency': 0,
                                                  'is_scar': 0})
        if not effect:
            pass
        else:
            damage.Type.apply_effect(self.CharID)

    def recive_damage(self, *, damage_list: list[Damage] | Damage, apply_effect: bool = False) -> None:
        if isinstance(damage_list, Damage):
            self.apply_damage(damage_list, effect=apply_effect)
        else:
            for dam in damage_list:
                self.apply_damage(dam, effect=apply_effect)

        self.data_manager.logger.info(f'Персонаж {self.ID} получил урон {damage_list}')

    def __str__(self):
        print(self.get_root_partlabel())
        if self.IsImplant and self.get_root_partlabel():
            main_text = f'**[ {self.get_root_partlabel()} ]:** *{self.Label}*\n'
        else:
            main_text = f'**[ {self.Label} ]:**\n'
        if not self.injuries and not self.diseases:
            return main_text
        else:
            injury_text = f''
            for i in self.diseases:
                injury_text += f'- *{i.Name}*'
                if i.Immunity >= 100:
                    injury_text += ' <:immune:1249787600622063718>\n'
                else:
                    injury_text += '\n'

            for i in self.injuries:
                inj_name = i.Name if not self.IsInternal else i.InnerName
                if i.IsScar:
                    inj_name = i.ScarName if not self.IsInternal else i.ScarInnerName

                injury_text += f'- *{inj_name} ({i.Root})*'
                if i.HealingEfficiency:
                    injury_text += ' <:healed:1249753146859847760>\n'
                elif i.Bleed:
                    injury_text += ' <:bleed:1249850720065425480>\n'
                else:
                    injury_text += '\n'

            return main_text + injury_text




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
        if self.data_manager.check('CHARS_INJURY',filter=f'id_inj = {self.InjuryID} AND id = {self.CharID}') is None:
            return {}
        else:
            return self.data_manager.select_dict('CHARS_INJURY', filter=f'id_inj = {self.InjuryID} AND id = {self.CharID}')[0]

    def heal(self, heal_efficiency:int):
        self.HealingEfficiency += heal_efficiency
        query = {'heal_efficiency': self.HealingEfficiency}
        self.data_manager.update('CHARS_INJURY', query, f'id_inj = {self.InjuryID}')

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
        self.name = self.main_data.get('name', 'Неизвестная расовая атака')

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

    def get_race(self):
        race = self.data_manager.select_dict('CHARS_INIT',filter=f'id = {self.character_id}')[0]
        return race.get('race', 'Human')

    def fetch_bodyparts(self):
        body_parts = []
        # Получаем список частей тела для данной расы из таблицы RACES_BODY
        body_parts_data = self.data_manager.select("RACES_BODY", columns="part_id", filter=f'race = "{self.race}"')

        for part_id in body_parts_data:
            # Проверяем, есть ли имплант, замещающий данную часть тела
            is_implant_present = self.data_manager.check("CHARS_BODY",
                                                         f"id = '{self.character_id}' AND place = '{part_id[0]}'")
            if is_implant_present:
                implant_id = self.data_manager.select_dict("CHARS_BODY",
                                                         filter=f"id = {self.character_id} AND place = '{part_id[0]}'")[0]
                part = LocalBodyPart(self.character_id, implant_id.get('imp_id'), data_manager=self.data_manager, place=implant_id.get('place'), label=implant_id.get('label'))  # Заменяем часть тела имплантом
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
        return stats[stat_name] if stat_name in stats else 0

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

    def parts_health(self) -> dict:
        total_list = {}
        for part in self.body_parts:
            total_list[part] = part.part_health()

        return total_list

    def phisical_stats_print(self):
        c_stats = self.physical_stats()
        c_bleeding = self.calculate_total_bleeding()
        c_pain = self.calculate_total_pain()
        total_text = ''
        total_text += f'\n```Статус: {self.vital_signs()["status"]}```\n'
        for stat in c_stats:
            total_text += f'\n**{stat}** - *{c_stats[stat] if c_stats[stat] > 0 else 0:.2f}%*'

        total_text += f'\n\n**Кровотечение:** *{c_bleeding:.2f}%* {self.__bleed__()}'
        total_text += f'\n**Боль:** *{c_pain:.2f}%* ({self.__pain__()})'
        total_text += f'\n**Жизнеспособность:** *{self.__vital__()}*'

        return total_text

    def __str__(self):

        c_blood_lost = self.__bloodloss__()

        text = ''
        if c_blood_lost != 'Отсутствует':
            text += f'\n**[ Все тело: ]** *{c_blood_lost}*\n'

        for i in self.body_parts:
            if i.injuries or i.IsImplant or i.diseases:
                text += '\n' + i.__str__()

        return text

    def vital_damage(self):
        c_parts: dict[LocalBodyPart] = self.parts_health()
        c_vital = 100

        for part in c_parts:
            if part.IsImplant:
                vital_effect = BodyPart(part.Place, data_manager=self.data_manager).Fatality
            else:
                vital_effect = part.Fatality
            c_health = 1 - c_parts[part]
            c_vital -= vital_effect * c_health

        return c_vital if c_vital > 0 else 0

    def vital_signs(self):
        from ArbRaces import Race

        c_alive = True
        c_active = True
        c_status = 'В норме'

        c_race = Race(self.race, data_manager=self.data_manager)

        c_vital_damage = 100-self.vital_damage()

        c_blood_lose = (self.data_manager.select_dict('CHARS_COMBAT',filter=f'id = {self.character_id}')[0].get('blood_lost')/c_race.Blood)*100

        c_pain = self.calculate_total_pain()

        max_pain = c_race.PainLimit

        if c_pain >= max_pain:
            c_active = False
            c_status = 'В отключке'

        if 100 > c_vital_damage >= 85:
            c_active = False
            c_status = 'В коме'
        elif c_vital_damage >= 95:
            c_alive = False

        if 60 <= c_blood_lose < 80:
            c_active = False
            c_status = 'В отключке'
        elif c_blood_lose >= 80:
            c_alive = False

        if not c_alive:
            c_active = False
            c_status = 'Мертв'


        return {'status': c_status,
                'alive': c_alive,
                'active': c_active}

    def __alive__(self):
        c_status = self.vital_signs()['alive']
        if c_status:
            return True
        else:
            return False

    def __pain__(self):
        c_pain = self.calculate_total_pain()

        if c_pain == 0:
            output = 'Нет'
        elif 1 <= c_pain < 15:
            output = 'Незначительная'
        elif 15 <= c_pain < 40:
            output = 'Ощутимая'
        elif 40 <= c_pain < 80:
            output = 'Нестерпимая'
        elif 80 <= c_pain < 100:
            output = 'Невыносимая'
        else:
            output = 'Болевой шок'

        return output

    def __vital__(self):
        c_vital = self.vital_damage()
        print(c_vital)

        if c_vital <= 10:
            output = 'Отсутствует'
        elif 10 < c_vital <= 35:
            output = 'Опасно низкая'
        elif 35 < c_vital <= 75:
            output = 'Нестабильная'
        elif c_vital < 75:
            output = 'Стабильная'
        else:
            output = 'Стабильная'

        return output

    def __bleed__(self):
        from ArbRaces import Race
        c_bleed = self.calculate_total_bleeding()
        c_blood = Race(self.race).Blood

        c_loss = (c_bleed/c_blood)*100


        if c_loss == 0:
            c_time = 0
        else:
            c_time = round(24/(c_loss/100))

        if c_bleed == 0:
            output = 'Отсутствует'
        elif c_loss < 50:
            output = 'Неопасное'
        elif 50 <= c_loss < 100:
            output = 'Ощутимое'
        elif 100 <= c_loss < 300:
            output = f'Опасное ({c_time}ч. до смерти)'
        elif 300 <= c_loss < 800:
            output = f'Обильное ({c_time}ч. до смерти)'
        elif 800 <= c_loss < 1200:
            output = f'Экстремальное ({c_time}ч. до смерти)'
        else:
            output = f'Смертельное ({c_time}ч. до смерти)'

        return output

    def __bloodloss__(self):
        from ArbRaces import Race
        c_loss = (self.data_manager.select_dict('CHARS_COMBAT', filter=f'id = {self.character_id}')[0].get('blood_lost')/Race(self.race).Blood)*100

        if c_loss == 0:
            output = 'Отсутствует'
        elif 0 < c_loss < 20:
            output = 'Слабая кровопотеря'
        elif 20 <= c_loss < 45:
            output = 'Легкая кровопотеря'
        elif 45 <= c_loss < 60:
            output = 'Средняя кровопотеря'
        elif 60 <= c_loss < 85:
            output = 'Большая кровопотеря'
        elif 85 <= c_loss < 100:
            output = 'Огромная кровопотеря'
        else:
            output = 'Смертельная кровопотеря'

        return output