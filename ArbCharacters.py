import datetime

from ArbDatabase import DataManager, DataModel, DataDict
from ArbHealth import Body
from ArbRoll import Roll
from ArbSkills import SkillInit
from ArbUtils.ArbTimedate import TimeManager
from ArbRaces import Race
from ArbResponse import Response, ResponsePool


class CharacterProgress(DataModel):
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'CHARS_PROGRESS', f'id = {self.id}', data_manager=self.data_manager)

        self.skills_points = self.get('skills', 0) if self.get('skills', None) is not None else 0
        self.skills_mods = self.get('skills_mods', 0) if self.get('skills_mods', None) is not None else 0

        self.lvl = self.get('lvl', 0) if self.get('lvl', None) is not None else 0
        self.skills_exp = self.get('exp', 0) if self.get('exp', None) is not None else 0

    def insert_progress_data(self, skills: int = None, skills_mods:float=None, lvl: int = None, exp: int = None):
        prompt = {
            'id': self.id,
            'skills': skills,
            'skills_mods': skills_mods,
            'lvl': lvl if lvl is not None else 0,
            'exp': exp
        }

        self.data_manager.insert('CHARS_PROGRESS', prompt)

    def update_progress_data(self, skills: int = 0, skills_mods:float=0, lvl: int = 0, exp: int = 0):
        if not self.data_manager.check('CHARS_PROGRESS', filter=f'id = {self.id}'):
            self.insert_progress_data(0, 0, 0, 0)

        prompt = {
            'skills': self.skills_points + skills,
            'skills_mods': self.skills_mods + skills_mods,
            'lvl': self.lvl + lvl,
            'exp': self.skills_exp + exp
        }
        self.skills_points += skills
        self.skills_mods += skills_mods
        self.lvl += lvl
        self.skills_exp += exp

        self.data_manager.update('CHARS_PROGRESS', prompt, filter=f'id = {self.id}')

    def spend_exp_on_skill(self, skill_id:str, exp: float) -> ResponsePool:
        from ArbSkills import Skill

        skill = Skill(self.id, skill_id, data_manager=self.data_manager)
        if exp < 0:
            return ResponsePool(Response(False, f'-# *Опыт затрачиваемый на прокачку не может быть ниже 0*'))

        if self.skills_exp < exp:
            exp = self.skills_exp

        skill.upgrade_skill(exp)
        self.update_progress_data(exp=-exp)
        return ResponsePool(Response(True, f'*Вы потратили **{exp} единиц опыта** для прокачки навыка "{skill.label}".\n-# Текущий уровень навыка: {skill.lvl}\n-# Текущий опыт навыка: {skill.exp}*'))

    def spend_skill_points(self, skill_id: str, skill_points:int):
        from ArbSkills import Skill

        skill = Skill(self.id, skill_id, data_manager=self.data_manager)
        if skill_points < 0:
            return ResponsePool(Response(False, f'-# *Очки навыков, затрачиваемые на прокачку, не могут быть ниже 0*'))

        if self.skills_points < skill_points:
            skill_points = self.skills_points

        skill.add_lvl(skill_points)
        self.update_progress_data(skills=-skill_points)
        return ResponsePool(Response(True, f'*Вы потратили **{skill_points} очков навыков** для прокачки навыка "{skill.label}".\n-# Текущий уровень навыка: {skill.lvl}*'))

    def spend_talent_points(self, skill_id: str, talent_points:float):
        from ArbSkills import Skill

        skill = Skill(self.id, skill_id, data_manager=self.data_manager)
        if talent_points < 0:
            return ResponsePool(Response(False, f'-# *Очки владения, затрачиваемые на прокачку, не могут быть ниже 0*'))

        if self.skills_mods < talent_points:
            talent_points = self.skills_mods

        skill.add_talant(talent_points)
        self.update_progress_data(skills_mods=-talent_points)
        return ResponsePool(Response(True, f'*Вы потратили **{talent_points} очков владения** для прокачки навыка "{skill.label}".\n-# Текущий талант навыка: {skill.talant}*'))

    def spend_mastery_points(self, skill_id: str, mastery_points:float):
        from ArbSkills import Skill

        skill = Skill(self.id, skill_id, data_manager=self.data_manager)
        if mastery_points < 0:
            return ResponsePool(Response(False, f'-# *Очки владения, затрачиваемые на прокачку, не могут быть ниже 0*'))

        if self.skills_mods < mastery_points:
            mastery_points = self.skills_mods

        skill.add_mastery(mastery_points)
        self.update_progress_data(skills_mods=-mastery_points)
        return ResponsePool(Response(True, f'*Вы потратили **{mastery_points} очков владения** для прокачки навыка "{skill.label}".\n-# Текущее мастерство навыка: {skill.mastery}*'))


class Character(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('CHARS_INIT', f'id = {self.id}', data_manager=self.data_manager)

        self.custom_id = self.get('custom_id', None)
        self.owner = self.get('owner', None)

        self.name = self.get('name', 'Неизвестный')
        self.callsign = self.get('callsign', '')
        self.age = self.get('age', 30)
        self.race = Race(self.get('race', 'Human'))
        self.sex = self.get('sex', 'Неизвестный пол')

        self.org = self.get('org', None)
        self.org_lvl = self.get('org_lvl', 0)

        self.frac = self.get('frac', None)
        self.frac_lvl = self.get('frac_lvl', 0)

        self.picture = self.get('avatar', '') if self.get('avatar') else ''
        self.update = self.get('updated', None)
        self.server = self.get('server', None)
        self.money = self.get('money', None) if self.get('money') else 0

    def set_location_on_spawn(self):
        from ArbOrgs import Organization
        from ArbLocations import CharacterLocation

        org = Organization(self.org, data_manager=self.data_manager)
        loc = org.spawn_point
        if not loc:
            loc = 'Elsewhere'

        CharacterLocation(self.id, data_manager=self.data_manager).set_location(loc, True)

    def set_owner(self, owner_id:int):
        self.owner = owner_id
        self.update_record({'owner': owner_id})

    def set_server(self, server_id:int):
        self.server = server_id
        self.data_manager.update('CHARS_INIT', {"server": self.server}, f'id = {self.id}')

    def set_money(self, money: int):
        self.money = money
        self.data_manager.update('CHARS_INIT', {"money": self.money}, f'id = {self.id}')

    def set_custom_id(self, custom_id: str):
        self.custom_id = custom_id
        self.data_manager.update('CHARS_INIT', {"custom_id": self.custom_id}, f'id = {self.id}')

    def set_name(self, name:str):
        self.name = name
        self.data_manager.update('CHARS_INIT', {"name": self.name}, f'id = {self.id}')

    def set_callsign(self, callsign: str):
        self.callsign = callsign
        self.data_manager.update('CHARS_INIT', {"callsign": self.callsign}, f'id = {self.id}')

    def set_age(self, age: int):
        self.age = age
        self.data_manager.update('CHARS_INIT', {"age": self.age}, f'id = {self.id}')

    def set_race(self, race: str):
        self.race = Race(race, data_manager=self.data_manager)
        self.data_manager.update('CHARS_INIT', {"race": race}, f'id = {self.id}')

    def set_org(self, org: str):
        self.org = org
        self.data_manager.update('CHARS_INIT', {"org": self.org}, f'id = {self.id}')

    def set_org_level(self, rank: str):
        self.org_lvl = rank
        self.data_manager.update('CHARS_INIT', {"org_lvl": self.org_lvl}, f'id = {self.id}')

    def set_frac(self, faction):
        self.frac = faction
        self.data_manager.update('CHARS_INIT', {"frac": self.frac}, f'id = {self.id}')

    def set_frac_level(self, rank: str):
        self.frac_lvl = rank
        self.data_manager.update('CHARS_INIT', {"frac_lvl": self.frac_lvl}, f'id = {self.id}')

    def set_picture(self, picture: str):
        self.picture = picture
        self.data_manager.update('CHARS_INIT', {"avatar": self.picture}, f'id = {self.id}')

    def set_last_update_date(self, date:str):
        self.update = date
        self.update_record({'updated': self.update})

    def add_adventure_points(self, adp: int):
        current_adp = self.data_manager.select_dict('CHARS_LOC', filter=f'id = {self.id}')[0].get('move_points', 0)
        if current_adp is None:
            current_adp = 0

        if self.data_manager.check('CHARS_LOC', f'id = {self.id}'):
            self.data_manager.update('CHARS_LOC', {'move_points': current_adp+adp}, filter=f'id = {self.id}')
        else:
            query = {
                'id': self.id,
                'loc_id': None,
                'move_points': current_adp + adp,
                'entered': 0
            }
            self.data_manager.insert('CHARS_LOC', query)

    def get_last_update_difference(self):
        time_manager = TimeManager()
        now = time_manager.today().strftime('%Y-%m-%d')
        last_update = self.update
        time_passed = time_manager.date_difference(last_update, now)
        return time_passed

    def get_next_day_after_update(self):
        time_manager = TimeManager()
        last_update = time_manager.get_date(self.update)
        next_day = time_manager.date_after(days=1, date=last_update.strftime('%Y-%m-%d'))
        return next_day

    def skip_cycle(self):
        """Расчитывает смену одного цикла, обновляя необходимые параметры
        :return: None
        """

        from ArbHealth import Body
        from ArbCharacterMemory import CharacterMemory
        from ArbLocations import CharacterLocation

        healing_rate = CharacterLocation(self.id, data_manager=self.data_manager).get_healing_rate() if CharacterLocation(self.id, data_manager=self.data_manager).entered_location else 0
        print('ЭФФЕКТИВНОСТЬ ЛЕЧЕНИЯ ЛОКАЦИИ', healing_rate)
        Body(self.id, data_manager=self.data_manager).rest(healing_rate)
        self.add_adventure_points(5)

        next_day = self.get_next_day_after_update().strftime('%Y-%m-%d')
        CharacterMemory(self.id, data_manager=self.data_manager).update_memories(next_day)
        self.set_last_update_date(next_day)

    def change_cycle(self, cycles:int, **kwargs):
        """Сменяет несколько циклов поочерёдно
            :param cycles: Количество циклов
            :return: None
        """

        rest_efficiency = kwargs.get('rest_efficiency', 0) if kwargs.get('rest_efficiency') is not None else 0

        max_cycles = self.get_last_update_difference()
        max_cycle_manually = kwargs.get('max_cycles', max_cycles)
        if max_cycle_manually < max_cycles:
            max_cycles = max_cycle_manually

        if cycles > max_cycles:
            cycles = max_cycles

        for _ in range(cycles):
            self.skip_cycle()

    def text_relations(self):
        from ArbCharacterMemory import Relations
        relations = Relations(self.id, data_manager=self.data_manager).fetch_relations()
        if not relations:
            return []

        total_text = []
        for character_id in relations:
            rel = relations.get(character_id)
            total_rel = rel.get_total_relations()
            text = f'- {rel.relation_type.label if not rel.family_type else rel.family_type.label} **{Character(character_id).name}**\n' \
                   f'> -# *Доверие: {total_rel.trust:+}*\n' \
                   f'> -# *Взаимопонимание: {total_rel.sympathy:+}*\n' \
                   f'> -# *Уважение: {total_rel.respect:+}*\n' \
                   f'> -# *Влечение: {total_rel.love:+}*'
            total_text.append(text)

        return total_text

    def text_memories(self):
        from ArbCharacterMemory import CharacterMemory
        memories = CharacterMemory(self.id, data_manager=self.data_manager).fetch_active_events()
        if not memories:
            return []

        total_text = []
        for memory in memories:
            to_end = f'(Осталось **{memory.time_delta(self.update)} циклов**)' if not memory.is_fixed else '(**Зафиксировано**)'
            blamed = f'' if not memory.subject else f'\n> -# *Виновник - **{Character(memory.subject).name}***'
            text = f'- **"{memory.label}"** {to_end}{blamed}\n> -# *— "{memory.description}"*'
            total_text.append(text)

        return total_text



    def text_card(self):
        from ArbOrgs import Organization, Rank

        age_text = f'{self.age}'
        age_label = 'год'
        if age_text[-1] in ['2', '3', '4']:
            age_label = 'года'
        elif age_text[-1] in ['5', '6', '7', '8', '9', '0']:
            age_label = 'лет'

        name = self.name.split(' ')
        if not self.callsign:
            display_name = ' '.join(name)
        else:
            display_name = name[0] + f' "{self.callsign}"' + ' ' + ' '.join(name[1:])

        total_text = f'''
***Имя Фамилия:*** *{display_name}*
***Раса:*** *{self.race.label}*
***Пол:*** *{self.sex}*
***Возраст:*** *{self.age} {age_label}*

'''
        if self.org:
            total_text += f'***Организация:*** *{Organization(self.org, data_manager=self.data_manager).label}*\n'
        if self.org_lvl:
            total_text += f'***Звание/Должность:** {Rank(self.org_lvl, data_manager=self.data_manager).label}*\n'

        if self.frac:
            total_text += f'***Фракция:** {self.frac}*\n'

        return total_text

    def text_combat_card(self):
        from ArbBattle import Actor, Layer, GameObject

        actor = Actor(self.id, data_manager=self.data_manager)
        combat_info = DataDict('CHARS_COMBAT', f'id = {self.id}', data_manager=self.data_manager)
        total_text = f'''
<:action_points:1251239084144197696> **Очки Действия:** {combat_info.get('ap', 0)} ОД. {f"({combat_info.get('ap_bonus', 0):+} ОД.)" if combat_info.get('ap_bonus') else ''}
<:target:1251276620384305244> **Текущая цель:** {combat_info.get('target') if combat_info.get('target') is not None else 'Отсутствует'} 
:crossed_swords: **Ближний бой с целью:** {combat_info.get('melee_target') if combat_info.get('melee_target') is not None else 'Отсутствует'}
<:coverage:1264244009149272115> **Уровень маскировки:** {actor.disguise():0.2f}%

-# **Текущий слой:**
- {Layer(actor.layer_id, actor.battle_id, data_manager=self.data_manager).label} (``{actor.layer_id}``)
-# **Текущее укрытие:**
- {GameObject(actor.object_id, data_manager=self.data_manager).object_type.label + f' (``{actor.object_id}``)' if actor.object_id else 'Отсутствует'}
'''

        return total_text

    def spend_money(self, cost:float) -> bool:
        """
        Проверяет наличие необходимой суммы, и в случае такаяя сумма есть списывает деньги со счёта персонажа

        :param cost: (float) количество потраченных денег
        :return:
        """

        if self.money < cost:
            return False
        else:
            self.money -= cost
            self.data_manager.update('CHARS_INIT', {'money': self.money}, f'id = {self.id}')
            return True

    def add_money(self, amount: float) -> None:
        """
        Добавляет указанную сумму денег к счёту персонажа

        :param amount: (float) добавляемая сумма
        :return: None
        """

        self.money += amount
        self.data_manager.update('CHARS_INIT', {'money': self.money}, f'id = {self.id}')

    def give_money(self, amount: float, character_id:int=None) -> bool:
        """
        Отдаёт указанную сумму денег персонажу

        :param amount: (float) переданная сумма денег
        :return: None
        """

        amount_check = self.spend_money(amount)
        if not amount_check:
            return False

        if character_id is not None:
            char = Character(character_id, data_manager=self.data_manager)
            char.add_money(amount)
            return True
        else:
            return True

    def change_reputation(self, org_id:str, amount:int):
        from ArbOrgs import Organization
        org = Organization(org_id)
        org.insert_reputation_if_not_exist(self.id)
        org.change_reputation(self.id, amount)

    def change_loyalty(self, org_id:str, amount:int):
        from ArbOrgs import Organization
        org = Organization(org_id)
        org.insert_reputation_if_not_exist(self.id)
        org.change_loyalty(self.id, amount)

    def spend_reputation(self, org_id:str, amount:int):
        from ArbOrgs import Organization
        org = Organization(org_id)
        org.insert_reputation_if_not_exist(self.id)
        current_rep = org.get_character_reputation(self.id)
        if current_rep - amount < -100:
            return False
        else:
            org.change_reputation(self.id, -amount)
            return True

    def get_group(self):
        from ArbGroups import Group
        group = Group.find_group_by_character_id(self.id)
        return group

    def check_organization(self):
        group = self.get_group()
        if not group:
            return self.org if self.org else 'Civil'
        else:
            return Character(group.owner_id).org

    def delete_character(self):
        delete_tables = {
            'BATTLE_CHARACTERS': f'character_id = {self.id}',
            'BATTLE_DEAD': f'character_id = {self.id}',
            'BATTLE_EVENTS': f'actor = {self.id}',
            'BATTLE_SOUNDS': f'actor_id = {self.id}',
            'CHARS_BODY': f'id = {self.id}',
            'CHARS_COMBAT': f'id = {self.id}',
            'CHARS_DISEASE': f'id = {self.id}',
            'CHARS_EFFECTS': f'id = {self.id}',
            'CHARS_EQUIPMENT': f'id = {self.id}',
            'CHARS_INIT': f'id = {self.id}',
            'CHARS_INJURY': f'id = {self.id}',
            'CHARS_INV': f'id = {self.id}',
            'CHARS_LOC': f'id = {self.id}',
            'CHARS_MEMORY': f'id = {self.id}',
            'CHARS_PROGRESS': f'id = {self.id}',
            'CHARS_PSYCHOLOGY': f'id = {self.id}',
            'CHARS_QUESTS': f'id = {self.id}',
            'CHARS_RELATIONS': f'id = {self.id} OR subject_id = {self.id}',
            'CHARS_REPUTATION': f'id = {self.id}',
            'CHARS_SKILLS': f'id = {self.id}',
            'CHARS_TRAITS': f'id = {self.id}',
            'DIALOGUE_MESSAGES': f'character_id = {self.id}',
            'GROUP_CHARS': f'id = {self.id}',
            'INVENTORY_INIT': f'owner = {self.id}',
            'NOTIFICATIONS': f'character_id = {self.id}',
            'VENDORS_INIT': f'id = {self.id}'
        }
        update_tables = {
            'BATTLEFIELD_TEAMS': [f'commander = {self.id}', {'commander': None}],
            'CAMPAIGN_INIT': [f'r_rel = {self.id}', {'r_rel': None}],
            'CHARS_MEMORY': [f'subject_id = {self.id}', {'subject_id': None}],
            'DIVISION_INIT': [f'commander = {self.id}', {'commander': None}],
            'GROUP_INIT': [f'owner_id = {self.id}', {'owner_id': None}],
            'META_INFO': [f'playing_as = {self.id}', {'playing_as': None}],
            'PLAYERS': [f'character_id = {self.id}', {'character_id': None}]
        }

        for table, conditions in delete_tables.items():
            self.data_manager.delete(table, conditions)

        for table, conditions_and_values in update_tables.items():
            conditions, values = conditions_and_values
            self.data_manager.update(table, values, conditions)

    @staticmethod
    def check_owner(character_id:int, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        char = db.select_dict('CHARS_INIT', filter=f'id = {character_id}')
        if not char:
            return False

        if char[0].get('owner'):
            return True
        else:
            return False

    @staticmethod
    def check_active_user(character_id: int, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        char = db.select_dict('PLAYERS', filter=f'character_id = {character_id}')
        if not char:
            return False
        else:
            return True

    @staticmethod
    def check_org_exist(character_id: int, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        char = db.select_dict('CHARS_INIT', filter=f'id = {character_id}')
        if not char:
            return False
        org = char[0].get('org')
        if db.check('ORG_INIT', f'id = "{org}"'):
            return True
        else:
            return False

    @classmethod
    def get_unused_characters(cls, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        all_characters = [i.get("id") for i in db.select_dict('CHARS_INIT')]
        unused_characters = []

        for i in all_characters:
            owner = cls.check_owner(i, db)
            user = cls.check_active_user(i, db)
            org_exist = cls.check_org_exist(i, db)
            print(i, owner, user, org_exist)

            if (cls.check_owner(i, db) or cls.check_active_user(i, db)) and cls.check_org_exist(i, db):
                continue
            else:
                unused_characters.append(i)

        return unused_characters

    @classmethod
    def delete_unused_characters(cls, data_manager: DataManager = None):
        db = data_manager if data_manager else DataManager()
        unused_characters = cls.get_unused_characters(db)
        for character_id in unused_characters:
            Character(character_id, data_manager=db).delete_character()

        return len(unused_characters)

    def __str__(self):
        return f'{self.sex} {self.race.label} {self.name} возрастом {self.age}'