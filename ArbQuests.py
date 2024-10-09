import pprint
from typing import Any
from ArbUtils.ArbDataParser import proccess_tasks

from ArbDatabase import DataManager, DataModel
from dataclasses import dataclass


@dataclass()
class Task:
    quest_id: str
    title: str
    desc: str
    phase: int
    is_required: bool
    visible_before_assign: bool

    def add_task(self, data_manager: DataManager):
        if data_manager.check('QUESTS_TASKS', f'id = "{self.quest_id}" AND title = "{self.title}" AND phase = {self.phase}'):
            return

        query = {'id': self.quest_id,
                 'title': self.title,
                 'desc': self.desc,
                 'phase': self.phase,
                 'is_required': self.is_required,
                 'visible_before_assign': self.visible_before_assign}

        data_manager.insert('QUESTS_TASKS', query)

    def delete_task(self, data_manager: DataManager):
        if data_manager.check('QUESTS_TASKS', f'id = "{self.quest_id}" AND title = "{self.title}" AND phase = {self.phase}'):
            data_manager.delete('QUESTS_TASKS', f'id = "{self.quest_id}" AND title = "{self.title}" AND phase = {self.phase}')

    @staticmethod
    def find_task(quest_id:str, title:str, phase:int, data_manager: DataManager):
        if data_manager.check('QUESTS_TASKS', f'id = "{quest_id}" AND title = "{title}" AND phase = {phase}'):
            data = data_manager.select_dict('QUESTS_TASKS', filter=f'id = "{quest_id}" AND title = "{title}" AND phase = {phase}')[0]
            task = Task(quest_id, title, data.get('desc', ''), phase, data.get('is_required', 0) == 1, data.get('visible_before_assign', 0) == 1)
            return task
        else:
            return None

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.title == other.title and self.phase == other.phase and self.quest_id == other.quest_id
        return False


@dataclass()
class QuestReward:
    quest_id: str
    reward_type: str
    value: Any
    split_type: str

    def __post_init__(self):
        # Валидация типа распределения для награды
        valid_split_types = {
            'Деньги': ['Поровну', 'Каждому', 'Лидеру', 'Организации', 'Выдающемуся'],
            'Опыт': ['Поровну', 'Каждому', 'Лидеру', 'Выдающемуся'],
            'Предмет': ['Каждому', 'Лидеру', 'Выдающемуся'],
            'Репутация': ['Поровну', 'Каждому', 'Лидеру', 'Выдающемуся'],
            'ОН': ['Поровну', 'Каждому', 'Лидеру', 'Выдающемуся'],
            'ОП': ['Поровну', 'Каждому', 'Лидеру', 'Выдающемуся'],
            'Уровень': ['Каждому', 'Лидеру', 'Выдающемуся'],
            'Повышение': ['Каждому', 'Лидеру', 'Выдающемуся'],
            'Доминация': ['Организации'],
            'Боевой дух': ['Организации'],
            'Организация': ['Организации'],
            'Разведка': ['Организации'],
            'Снабжение': ['Организации'],
            'Защита': ['Организации'],
            'Импульс': ['Организации']
        }

        # Если тип распределения не соответствует типу награды, то меняем его на допустимый
        if self.split_type not in valid_split_types.get(self.reward_type, []):
            raise ValueError(f"Невозможно распределить награду '{self.reward_type}' с типом распределения '{self.split_type}'")

        # Для специфических наград (организационных) автоматически устанавливается тип распределения 'Организации'
        if self.reward_type in ['Доминация', 'Боевой дух', 'Организация', 'Разведка', 'Снабжение', 'Защита', 'Импульс']:
            self.split_type = 'Организации'

        # Для предметов, повышения или уровня, если тип распределения не подходит, меняем его на 'Лидеру'
        if self.reward_type in ['Предмет', 'Повышение', 'Уровень'] and self.split_type in ['Поровну', 'Организации']:
            self.split_type = 'Лидеру'

    def give_reward(self, character_id: int, outstanding_id:int=None):
        from ArbGroups import Group

        # Получаем информацию о группе персонажа
        group_members = Group.find_group_members_including(character_id)
        group_leader = Group.get_group_leader_by_character_id(character_id)
        group_org = Group.get_group_org_by_character_id(character_id)
        outstanding_member = outstanding_id if outstanding_id is not None else group_leader

        # Вызов соответствующего метода в зависимости от типа награды и типа распределения
        if self.split_type == 'Поровну':
            self.give_equally(group_members)
        elif self.split_type == 'Каждому':
            self.give_to_each(group_members)
        elif self.split_type == 'Лидеру':
            self.give_to_leader(group_leader)
        elif self.split_type == 'Организации':
            self.give_to_org(group_org)
        elif self.split_type == 'Выдающемуся':
            self.give_to_outstanding(outstanding_member)

    def give_equally(self, group_members):
        # Разделение награды между всеми участниками
        amount_per_member = round(int(self.value) / len(group_members))
        for member in group_members:
            self.apply_reward(member, amount_per_member)

    def give_to_each(self, group_members):
        # Каждый получает полную награду
        for member in group_members:
            self.apply_reward(member, self.value)

    def give_to_leader(self, leader):
        # Только лидер получает награду
        self.apply_reward(leader, self.value)

    def give_to_org(self, org_id:str):
        self.apply_reward(org_id, self.value)

        # Награда передается организации
        print(f"Организация {org_id} получила награду {self.value} {self.reward_type}")

    def give_to_outstanding(self, character_id:int):
        # Логика выдачи награды выдающемуся члену группы
        self.apply_reward(character_id, self.value)

    def apply_reward(self, character_id, value):
        # Метод для применения награды в зависимости от типа
        print(character_id, value)
        if self.reward_type == 'Деньги':
            if self.split_type == 'Организации':
                self.give_money_to_org(value, character_id)
            else:
                self.give_money(value, character_id)
        elif self.reward_type == 'Опыт':
            self.give_exp(value, character_id)
        elif self.reward_type == 'Предмет':
            self.give_item(value, character_id)
        elif self.reward_type == 'Репутация':
            self.give_reputation(value, character_id, Quest(self.quest_id).giver)
        elif self.reward_type == 'ОН':
            self.give_skill_points(value, character_id)
        elif self.reward_type == 'ОП':
            self.give_skill_mods(value, character_id)
        elif self.reward_type == 'Уровень':
            self.give_lvl(value, character_id)
        elif self.reward_type == 'Повышение':
            self.give_promotion(value, character_id)

        # Добавить другие типы наград здесь
        print(f"Персонаж {character_id} получил {value} {self.reward_type}")

    def find_outstanding_member(self, group_members):
        # Логика нахождения выдающегося члена группы
        # Временная заглушка, возвращающая первого члена группы
        return group_members[0]

    @staticmethod
    def give_money(amount: int, character_id: int):
        from ArbCharacters import Character
        Character(character_id).add_money(int(amount))
        print(f"Персонаж {character_id} получил {amount} денег")

    @staticmethod
    def give_money_to_org(amount: int, org_id: str):
        from ArbOrgs import Organization
        Organization(org_id).update_budget(int(amount))
        print(f"Организация {org_id} получила {amount} денег")

    @staticmethod
    def give_exp(amount: int, character_id: int):
        from ArbCharacters import CharacterProgress
        CharacterProgress(character_id).update_progress_data(exp=int(amount))
        print(f"Персонаж {character_id} получил {amount} опыта")

    @staticmethod
    def give_skill_points(amount: int, character_id: int):
        from ArbCharacters import CharacterProgress
        CharacterProgress(character_id).update_progress_data(skills=int(amount))
        print(f"Персонаж {character_id} получил {amount} ОН")

    @staticmethod
    def give_skill_mods(amount: int, character_id: int):
        from ArbCharacters import CharacterProgress
        CharacterProgress(character_id).update_progress_data(skills_mods=int(amount))
        print(f"Персонаж {character_id} получил {amount} ОП")

    @staticmethod
    def give_lvl(amount: int, character_id: int):
        from ArbCharacters import CharacterProgress
        CharacterProgress(character_id).update_progress_data(lvl=int(amount))
        print(f"Персонаж {character_id} получил {amount} ОП")

    @staticmethod
    def give_item(item_id: str, character_id: int):
        from ArbGenerator import ItemManager
        from ArbItems import Inventory
        inventory_id = Inventory.get_inventory_by_character(character_id).inventory_id
        new_item = ItemManager(item_id, set_max_endurance=True, inventory=inventory_id).spawn_item()
        print(new_item)

    @staticmethod
    def give_reputation(amount: int, character_id: int, org_id:str):
        from ArbOrgs import Organization
        Organization(org_id).change_reputation(character_id, int(amount))

    @staticmethod
    def give_promotion(amount: int, character_id: int):
        from ArbCharacters import Character
        from ArbOrgs import Organization, Rank

        character = Character(character_id)
        org = Organization(character.org)
        character_rank = Rank(character.org_lvl) if character.org_lvl else Rank(org.get_random_lowest_rank())
        org_ranks = org.get_lvl_rank(character_rank.power_rank + int(amount))
        if not org_ranks:
            return
        if Rank(org_ranks).power_rank < character_rank.power_rank:
            return

        character.update_record({'org_lvl': org_ranks})


class Quest(DataModel):
    def __init__(self, id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'QUESTS', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный квест')
        self.type = self.get('type', 'Неизвестный тип')
        self.desc = self.get('desc', '')
        self.difficulty = self.get('difficulty', 0) if self.get('difficulty') else 0
        self.giver = self.get('giver', None)
        self.enemy = self.get('enemy', None)
        self.status = self.get('status', None)
        self.time_of_end = self.get('time_of_end', None)
        self.renewable = self.get('renewable', 0) == 1
        self.next_act = self.get('next_act', None)
        self.picture = self.get('picture', None)

    def get_tasks(self) -> dict[int, list[Task]]:
        if not self.data_manager.check('QUESTS_TASKS', f'id = "{self.id}"'):
            return {}
        else:
            tasks = {}
            data: list[dict] = self.data_manager.select_dict('QUESTS_TASKS', filter=f'id = "{self.id}"')
            for task_data in data:
                phase = task_data.get('phase', 0)
                title = task_data.get('title', 'Задача')
                desc = task_data.get('desc', '')
                is_required = task_data.get('is_required', 0) == 1
                visible_before_assign = task_data.get('visible_before_assign', 0) == 1

                if phase in tasks:
                    tasks[phase].append(Task(self.id, title, desc, phase, is_required, visible_before_assign))
                else:
                    tasks[phase] = [Task(self.id, title, desc, phase, is_required, visible_before_assign)]

            tasks = dict(sorted(tasks.items(), reverse=True))

            return tasks

    def get_reward(self) -> list[QuestReward]:
        if not self.data_manager.check('QUESTS_REWARDS', f'id = "{self.id}"'):
            return []
        else:
            total_rewards = []
            data: list[dict] = self.data_manager.select_dict('QUESTS_REWARDS', filter=f'id = "{self.id}"')
            for reward in data:
                rew = QuestReward(self.id, reward.get('type'), reward.get('value'), reward.get('split_type'))
                total_rewards.append(rew)
            return total_rewards

    def __repr__(self):
        return f'Quest.{self.id}'

    @staticmethod
    def create_quest(id:str, type:str, giver_id:str, label:str=None, desc:str=None, enemy_id:str=None, time_of_end:str=None, renewable:str=None, previous_quest_id:str=None, difficulty:int=0, picture:str=None) -> 'Quest':
        query = {'id': id,
                 'type': type,
                 'giver': giver_id,
                 'label': label,
                 'desc': desc,
                 'enemy': enemy_id,
                 'time_of_end': time_of_end,
                 'renewable': renewable,
                 'status': 'Не выполнено',
                 'difficulty': difficulty,
                 'picture': picture}

        DataManager().insert('QUESTS', query)
        if previous_quest_id and DataManager().check('QUESTS', f'id = "{previous_quest_id}"'):
            DataManager().update('QUESTS', {'next_act': id}, f'id = "{previous_quest_id}"')

        return Quest(id)

    def create_task(self, title:str, phase:int, desc:str=None, is_required:bool=False, visible_before_assign:bool=False) -> Task:
        task = Task(self.id, title, desc, phase, is_required, visible_before_assign)
        task.add_task(self.data_manager)

        return task

    def delete_task(self, title:str, phase:int) -> None:
        Task(self.id, title, '', phase, False, False).delete_task(self.data_manager)

    def complete_quest(self) -> None:
        self.data_manager.update('QUESTS', {'status': 'Выполнено'}, f'id = "{self.id}"')

    def describe(self) -> str:
        from ArbOrgs import Organization

        main_info = f'''
*— "{self.desc}"*      
### **Сложность: {self.difficulty}**
> -# Работодатель: **{Organization(self.giver).label if self.giver else "||Неизвестно||"}**
> -# Тип: **{self.type}**
> -# Противник: **{Organization(self.enemy).label if self.enemy else "||Неизвестно||"}**'''
        if self.time_of_end:
            main_info += f'\n> -# Срок: **{self.time_of_end}**'

        return main_info

    def describe_tasks(self) -> str:
        tasks = self.get_tasks()

        text = ''

        for phase, tasks_list in tasks.items():
            for task in tasks_list:
                task_label = f'(ДОП) {task.title}' if not task.is_required else f'{task.title}<:required:1265820311069134939>'
                text += f'- **{task_label}**\n - -# *— "{task.desc}"*\n\n'

        return text

    def describe_rewards(self) -> str:
        rewards = self.get_reward()
        text = ''
        for reward in rewards:
            text += f'- ***{reward.reward_type}({reward.value})** ``{reward.split_type}``*\n'

        return text

    def delete_quest(self):
        self.data_manager.delete('QUESTS', f'id = "{self.id}"')
        self.data_manager.delete('QUESTS_TASKS', f'id = "{self.id}"')
        self.data_manager.delete('QUESTS_REWARDS', f'id = "{self.id}"')
        self.data_manager.delete('CHARS_QUESTS', f'quest_id = "{self.id}"')
        self.data_manager.update('QUESTS', {'next_act': None}, f'next_act = "{self.id}"')

    def add_reward(self, type:str, value:str, split_type:str = 'Всем'):
        if self.data_manager.check('QUESTS_REWARDS', f'id = "{self.id}" AND type = "{type}" AND split_type = "{split_type}"'):
            self.data_manager.update('QUESTS_REWARDS', {'type': type, 'value': value, 'split_type': split_type}, f'id = "{self.id}" AND type = "{type}" AND split_type = "{split_type}"')
        else:
            self.data_manager.insert('QUESTS_REWARDS', {'id': self.id, 'type': type, 'value': value,'split_type': split_type})

    def delete_reward(self, type:str, value:str, split_type:str):
        self.data_manager.delete('QUESTS_REWARDS', f'id = "{self.id}" AND type = "{type}" AND value = "{value}" AND split_type = "{split_type}"')

    def get_campaign(self):
        if self.data_manager.check('CAMPAIGN_QUESTS', f'quest = "{self.id}"'):
            campaign_id = self.data_manager.select_dict('CAMPAIGN_QUESTS', filter=f'quest = "{self.id}"')[0].get('id')
            return Campaign(campaign_id, data_manager=self.data_manager)
        else:
            return None

    @staticmethod
    def get_campaign_by_quest(quest_id:str):
        db = DataManager()
        if db.check('CAMPAIGN_QUESTS', f'quest = "{quest_id}"'):
            campaign_id = db.select_dict('CAMPAIGN_QUESTS', filter=f'quest = "{quest_id}"')[0].get('id')
            return Campaign(campaign_id, data_manager=db)
        else:
            return None

class QuestChain:
    def __init__(self, start_quest_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.start_quest = Quest(start_quest_id, data_manager=self.data_manager)

        self.chain = self.fetch_quests_in_chain()

    def fetch_quests_in_chain(self):
        total_chain = [self.start_quest]

        flag = False

        current_quest = self.start_quest
        while not flag:
            if not current_quest.next_act:
                flag = True
                break
            else:
                next_quest = Quest(current_quest.next_act, data_manager=self.data_manager)
                total_chain.append(next_quest)
                current_quest = next_quest

        return total_chain


@dataclass()
class CampaignQuest:
    campaign_id: str
    quest: Quest
    phase: int
    is_required: bool
    phase_delta: int


@dataclass()
class Phase:
    campaign_id: str
    phase: int
    quests: list[CampaignQuest]
    title: str
    desc: str

    def describe_phase(self):
        text = f'''
### {self.title}
*— "{self.desc}"*

'''
        for quest in self.quests:
            text += f'- {"**(ДОП)** " if not quest.is_required else ""}{quest.quest.label} — ``{quest.quest.status}``\n-# **Влияние на эскалацию: {quest.phase:+}**\n-# *"{quest.quest.desc}"*\n\n'

        return text


class Campaign(DataModel):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'CAMPAIGN_INIT', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестное событие')
        self.type = self.get('type', 'Событие')
        self.desc = self.get('desc','')
        self.phase = self.get('phase', 0)
        self.time_of_end = self.get('time_of_end', None)
        self.enemy = self.get('enemy', None)
        self.required_lvl = self.get('r_lvl', 0)
        self.required_org = self.get('r_org', None)
        self.required_relation = self.get('r_rel', None)
        self.news_channel_id = self.get('news_channel', None)
        self.main_message_id = self.get('main_message', None)
        self.picture = self.get('picture', None)

    def describe(self):
        from ArbOrgs import Organization
        desc = self.get_phase_desc(self.phase)
        desc = self.desc if not desc else desc

        text = f'''### {self.get_phase_title(self.phase)}
-# Срок до {self.time_of_end if self.time_of_end else "||Неизвестно||"}
-# Противник: {Organization(self.enemy, data_manager=self.data_manager).label if self.enemy else '||Неизвестен||'}

*— "{desc if desc else "Описание события отсутствует"}"*
'''
        return text

    def describe_current_quests(self):
        quests = self.get_phase(self.phase).quests
        text = '### Список заданий:\n'
        for quest in quests:
            text += f'- {"" if quest.quest.status != "Выполнено" else "~~"}' \
                    f'**{"(ДОП) " if not quest.is_required else ""}{quest.quest.label}**' \
                    f'{"" if quest.quest.status != "Выполнено" else "~~"}' \
                    f'\n - -# **Сложность: {quest.quest.difficulty}/10**\n - -# "{quest.quest.desc if quest.quest.desc else "||Подробности неизвестны||"}"\n\n'
        return text

    def fixate_message(self, message_id:int):
        self.update_record({'main_message': message_id})

    def fetch_all_quests(self):
        if not self.data_manager.check('CAMPAIGN_QUESTS', f'id = "{self.id}"'):
            return {}
        else:
            quests = {}
            data: list[dict] = self.data_manager.select_dict('CAMPAIGN_QUESTS', filter=f'id = "{self.id}"')
            for quest in data:
                quest_id = Quest(quest.get('quest'), data_manager=self.data_manager)
                phase = quest.get('phase')
                is_required = quest.get('is_required', 0) == 1
                phase_delta = quest.get('phase_delta', 0)

                current_quest = CampaignQuest(self.id, quest_id, phase, is_required, phase_delta)

                if phase in quests:
                    quests[phase].append(current_quest)
                else:
                    quests[phase] = [current_quest]

            return quests

    def fetch_phase_quests(self, phase:int):
        if not self.data_manager.check('CAMPAIGN_QUESTS', f'id = "{self.id}"'):
            return {}
        else:
            total_quests = self.fetch_all_quests()
            if phase in total_quests:
                return total_quests[phase]
            else:
                return []

    def get_phase(self, phase:int):
        quests = self.fetch_phase_quests(phase)
        phase_title = self.get_phase_title(phase)
        phase_desc = self.get_phase_desc(phase)
        total_phase = Phase(self.id, phase, quests, phase_title, phase_desc)

        return total_phase

    def get_current_phase(self):
        phase = self.get_phase(self.phase)
        return phase

    def get_phase_data(self, phase:int):
        data = self.data_manager.select_dict('CAMPAIGN_PHASE', filter=f'campaign_id = "{self.id}" AND phase = {phase}')
        if not data:
            return {}
        else:
            return data[0]

    def get_phase_title(self, phase:int):
        data = self.get_phase_data(phase)
        return data.get('title', f'Этап {phase}')

    def get_phase_desc(self, phase:int):
        data = self.get_phase_data(phase)
        return data.get('desc', f'{self.desc}')

    def add_quest(self, quest_id:str, phase:int, is_required:bool=False, phase_delta:int=0):
        if not self.data_manager.check('QUESTS', f'id = "{quest_id}"'):
            return

        if self.data_manager.check('CAMPAIGN_QUESTS', f'quest = "{quest_id}"'):
            return

        query = {
            'id': self.id,
            'quest': quest_id,
            'phase': phase,
            'is_required': is_required,
            'phase_delta': phase_delta
        }
        self.data_manager.insert('CAMPAIGN_QUESTS', query)

    def get_campaign_quest(self, quest_id:str):
        if not self.data_manager.check('CAMPAIGN_QUESTS', f'quest = "{quest_id}" AND id = "{self.id}"'):
            return None

        data = self.data_manager.select_dict('CAMPAIGN_QUESTS', filter=f'quest = "{quest_id}" AND id = "{self.id}"')[0]

        return CampaignQuest(self.id, Quest(quest_id, data_manager=self.data_manager), data.get('phase'), data.get('is_required') == 1, data.get('phase_delta'))

    def delete_quest(self, quest_id:str):
        self.data_manager.delete('CAMPAIGN_QUESTS', f'quest = "{quest_id}" AND id = "{self.id}"')

    def delete_campaign(self):
        self.data_manager.delete('CAMPAIGN_INIT', f'id = "{self.id}"')
        self.data_manager.delete('CAMPAIGN_QUESTS', f'id = "{self.id}"')

    def set_phase(self, phase: int):
        self.data_manager.update('CAMPAIGN_INIT', {'phase': phase}, f'id = "{self.id}"')

    def change_phase(self, phase_delta:int):
        self.set_phase(self.phase + phase_delta)

    def check_character_availability(self, character_id:int):
        from ArbCharacters import Character, CharacterProgress
        from ArbCharacterMemory import Relations

        character = Character(character_id, data_manager=self.data_manager)
        lvl_check = CharacterProgress(character_id, data_manager=self.data_manager).lvl >= self.required_lvl if self.required_lvl else True
        org_check = character.org == self.required_org if self.required_org else True
        rel_check = Relations(character_id, data_manager=self.data_manager).get_relation_to_character(self.required_relation).get_avg_relation() >= 30 if self.required_relation else True

        if lvl_check and org_check and rel_check:
            return True
        else:
            return False

    def check_phase_complete(self):
        quests = self.fetch_phase_quests(self.phase)
        required_quests = [quest for quest in quests if quest.is_required]
        completed_quests = [quest for quest in required_quests if quest.quest.status == 'Выполнено']
        return len(completed_quests) == len(required_quests)

    def next_phase(self):
        if self.check_phase_complete():
            self.change_phase(1)
            return True
        else:
            return False

    def add_phase_values(self, phase:int, title:str=None, desc:str=None):
        query = {
            'campaign_id': self.id,
            'phase': phase,
            'title': title,
            'desc': desc
        }

        if self.data_manager.check('CAMPAIGN_PHASE', f'campaign_id = "{self.id}" AND phase = {phase}'):
            self.data_manager.update('CAMPAIGN_PHASE',query, f'campaign_id = "{self.id}" AND phase = {phase}')
        else:
            self.data_manager.insert('CAMPAIGN_PHASE', query)

        return self.get_phase(phase)


    @classmethod
    def create_campaign(cls, id:str, label:str, type:str, desc:str=None, phase:int=0, time_of_end:str=None, enemy:str=None, r_lvl:int=0, r_org:str=None, r_rel:int=None, news_channel:int=None, picture:str=None):
        query = {
            'id': id,
            'label': label,
            'type': type,
            'desc': desc,
            'phase': phase,
            'time_of_end': time_of_end,
            'enemy': enemy,
            'r_lvl': r_lvl,
            'r_org': r_org,
            'r_rel': r_rel,
            'news_channel': news_channel,
            'picture': picture
        }
        DataManager().insert('CAMPAIGN_INIT', query)

        return Campaign(id)

class CharacterQuest(DataModel):
    def __init__(self, character_id:int, quest_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.character_id = character_id
        self.quest_id = quest_id

        print(self.quest_id)
        DataModel.__init__(self, 'CHARS_QUESTS', f'id = {self.character_id} AND quest_id = "{self.quest_id}"', data_manager=self.data_manager)

        self.status = self.get('status', 'Не назначен')
        self.current_phase = self.get('phase', 0)
        self.completed_tasks = proccess_tasks(self.get('completed_tasks', ''), ', ') if self.get('completed_tasks', '') else []

    def get_quest(self) -> Quest:
        return Quest(self.quest_id, data_manager=self.data_manager)

    def get_character(self):
        from ArbCharacters import Character
        return Character(self.character_id, data_manager=self.data_manager)

    def current_tasks(self) -> list[Task]:
        quest = self.get_quest()
        tasks = quest.get_tasks()

        current_tasks = tasks.get(self.current_phase, [])
        completed_tasks = self.get_completed_tasks()
        total_tasks = [task for task in current_tasks if task not in completed_tasks]
        return total_tasks

    def check_phase_done(self) -> bool:
        current_tasks = self.current_tasks()
        required_tasks = []

        for task in current_tasks:
            if task.is_required:
                required_tasks.append(task)

        if len(required_tasks) >= 1:
            return False
        else:
            return True

    def next_phase(self) -> None:
        self.set_phase(self.current_phase + 1)

    def compete_previous_phases(self, phase:int) -> None:
        self.set_phase(phase)
        tasks = self.get_quest().get_tasks()
        for phase, total_tasks in tasks.items():
            if phase < self.current_phase:
                for task in total_tasks:
                    if task.is_required:
                        self.set_task_done(task.title, phase)

    def set_phase(self, phase:int):
        max_phases = max(list(self.get_quest().get_tasks()))
        self.current_phase = phase
        self.update_record({'phase': self.current_phase})

        if self.current_phase > max_phases:
            self.status = 'Завершен'
            self.update_record({'status': self.status})
            self.complete_quest()

    def set_task_done(self, title:str, phase:int):
        completed_tasks = self.completed_tasks
        if f'{title}#{phase}' not in completed_tasks:
            completed_tasks.append(f'{title}#{phase}')
            self.completed_tasks = completed_tasks
            self.update_record({'completed_tasks': ', '.join(self.completed_tasks)})

    def complete_task(self, title: str, phase: int) -> None:
        self.set_task_done(title, phase)
        if phase > self.current_phase:
            self.compete_previous_phases(phase)
            self.set_phase(phase)

        if self.check_phase_done():
            self.next_phase()

    def get_completed_tasks(self) -> list[Task]:
        if not self.completed_tasks:
            return []
        completed_tasks = []
        for task in self.completed_tasks:
            title, phase = task.split('#')
            task_data = Task.find_task(self.quest_id, title, int(phase), self.data_manager)
            if task_data:
                completed_tasks.append(task_data)

        return completed_tasks

    def complete_quest(self) -> None:
        campaign = self.get_quest().get_campaign()
        if campaign:
            campaign_effect = campaign.get_campaign_quest(self.quest_id)
            if campaign_effect.phase_delta != 0:
                campaign.change_phase(campaign_effect.phase_delta)

        quest = self.get_quest()
        if not quest.renewable:
            self.status = 'Выполнено'
            self.update_record({'status': self.status})
            quest.complete_quest()
        if self.get_quest().next_act:
            QuestManager(data_manager=self.data_manager).assign_new_quest(self.character_id, quest.next_act, 'Назначено')

    def string_quest_desc(self):
        from ArbOrgs import Organization

        quest = self.get_quest()
        total_phases = max(list(quest.get_tasks().keys())) if quest.get_tasks() else 0
        desc = f'- **{quest.label}** — {self.status}\n> -# Работодатель: **{Organization(quest.giver).label if quest.giver else "||Неизвестно||"}**\n> -# Выполнено на **{round(self.current_phase/total_phases*100, 1) if total_phases else 100}**%'
        return desc

    def describe_quest(self):
        quest = self.get_quest()

        return quest.describe()

    def describe_quest_tasks(self):
        quest = self.get_quest()
        tasks = quest.get_tasks()
        current_tasks = self.current_tasks()
        completed_tasks = self.get_completed_tasks()

        print(tasks)

        text = ''
        for phase, tasks_list in tasks.items():
            for task in tasks_list:
                if task.phase > self.current_phase and not task.visible_before_assign:
                    continue

                task_label = f'(ДОП) {task.title}' if not task.is_required else f'{task.title}<:required:1265820311069134939>'

                if task in current_tasks:
                    text += f'- **{task_label}**\n - -# *— "{task.desc}"*\n\n'
                elif task in completed_tasks:
                    text += f'- ~~**{task_label}**~~\n\n'
                else:
                    text += f'- **{task_label}**\n - -# *— "{task.desc}"*\n\n'

        return text

    def give_quest_reward(self, outstanding_id:int=None):
        quest = self.get_quest()

        rewards = quest.get_reward()
        for reward in rewards:
            reward.give_reward(self.character_id, outstanding_id)

        if not quest.renewable:
            quest.delete_quest()
        else:
            self.data_manager.delete('CHARS_QUESTS', f'quest_id = "{self.quest_id}" AND status = "Выполнено"')


class QuestManager:
    def __init__(self, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager()) if kwargs.get('data_manager') else DataManager()

    def assign_new_quest(self, character_id:int, quest_id:str, status:str='Не выполняется', current_phase:int=None) -> Quest:
        if DataManager().check('CHARS_QUESTS', f'id = {character_id} AND quest_id = "{quest_id}"'):
            return Quest(quest_id, data_manager=self.data_manager)


        quest = Quest(quest_id)
        min_phase = min(list(quest.get_tasks().keys())) if quest.get_tasks() else 0

        query = {
            'id': character_id,
            'quest_id': quest_id,
            'phase': current_phase if current_phase is not None else min_phase,
            'completed_tasks': None,
            'status': status
        }
        self.data_manager.insert('CHARS_QUESTS', query)

        return Quest(quest_id, data_manager=self.data_manager)

    def take_quest(self, character_id:int, quest_id:str):
        self.data_manager.update('CHARS_QUESTS', {'status': 'Назначено'}, f'id = {character_id} AND status = "Выполняется"')
        self.data_manager.update('CHARS_QUESTS', {'status': 'Выполняется'}, f'id = {character_id} AND quest_id = "{quest_id}"')

    def get_current_quest(self, character_id:int):
        data = self.data_manager.select_dict('CHARS_QUESTS', filter=f'id = {character_id} AND status = "Выполняется"')
        if not data:
            return None

        return CharacterQuest(character_id, data[0].get('quest_id'), data_manager=self.data_manager)