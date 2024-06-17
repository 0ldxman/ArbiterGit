import pprint

from ArbDatabase import DataManager
from dataclasses import dataclass


@dataclass()
class Task:
    quest_id: str
    title: str
    desc: str
    phase: int
    is_required: bool

    def add_task(self, data_manager:DataManager):
        query = {'id': self.quest_id,
                 'title': self.title,
                 'desc': self.desc,
                 'phase': self.phase,
                 'is_required': self.is_required}

        data_manager.insert('QUESTS_TASKS', query)

    def delete_task(self, data_manager:DataManager):
        data_manager.delete('QUESTS_TASKS', f'id = "{self.quest_id}" AND title = "{self.title}" AND phase = {self.phase}')


@dataclass()
class Reward:
    items: list
    money: int
    exp:int


class Quest:
    def __init__(self, id: str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестный квест')
        self.tyoe = data.get('type', 'Неизвестный тип')
        self.desc = data.get('desc', '')
        self.giver = data.get('giver', None)
        self.enemy = data.get('enemy', None)
        self.status = data.get('status', None)
        self.time_of_end = data.get('time_of_end', None)
        self.renewable = data.get('renewable', 0) == 1
        self.next_act = data.get('next_act', None)

    def fetch_data(self):
        if self.data_manager.check('QUESTS', f'id = "{self.id}"'):
            return self.data_manager.select_dict('QUESTS',filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def get_tasks(self):
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

                if phase in tasks:
                    tasks[phase].append(Task(self.id, title, desc, phase, is_required))
                else:
                    tasks[phase] = [Task(self.id, title, desc, phase, is_required)]

            return tasks

    def add_task(self, title:str, phase:int, is_required:bool, desc:str=None):
        new_task = Task(self.id, title, desc, phase, is_required)
        new_task.add_task(self.data_manager)

    def delete_task(self, title:str, phase:int):
        if self.data_manager.check('QUESTS_TASKS', f'id = "{self.id}" AND title = "{title}" AND phase = {phase}'):
            target_task = Task(self.id, title, '', phase, is_required=False)
            target_task.delete_task(self.data_manager)

    def get_reward(self):
        if not self.data_manager.check('QUESTS_REWARDS', f'id = "{self.id}"'):
            return {}
        else:
            total_items = []
            total_money = 0
            total_exp = 0

            data: list[dict] = self.data_manager.select_dict('QUESTS_REWARDS', filter=f'id = "{self.id}"')
            for reward in data:
                rew_item = reward.get('item', None)
                rew_money = reward.get('money', 0)
                rew_exp = reward.get('exp', 0)

                total_money += rew_money
                total_exp += rew_exp
                if rew_item:
                    total_items.append(rew_item)

            return Reward(total_items, total_money, total_exp)

    def __repr__(self):
        return f'Quest.{self.id}'


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
    reward: Reward


class Campaign:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестное событие')
        self.type = data.get('type', 'Событие')
        self.desc = data.get('desc','')
        self.phase = data.get('phase', 0)
        self.time_of_end = data.get('time_of_end', None)
        self.enemy = data.get('enemy', None)
        self.required_lvl = data.get('r_lvl', 0)
        self.required_org = data.get('r_org', None)
        self.required_relation = data.get('r_rel', None)

    def fetch_data(self):
        if self.data_manager.check('CAMPAIGN_INIT', f'id = "{self.id}"'):
            return self.data_manager.select_dict('CAMPAIGN_INIT', filter=f'id = "{self.id}"')[0]
        else:
            return {}

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

    def get_reward(self):
        if not self.data_manager.check('CAMPAIGN_REWARDS', f'id = "{self.id}"'):
            return {}
        else:
            phases_rewards = {}

            data: list[dict] = self.data_manager.select_dict('CAMPAIGN_REWARDS', filter=f'id = "{self.id}"')
            for reward in data:
                rew_item = reward.get('item', None)
                rew_money = reward.get('money', 0)
                rew_exp = reward.get('exp', 0)

                rew_phase = reward.get('phase', 0)

                if rew_phase not in phases_rewards:
                    phases_rewards[rew_phase] = {'money': rew_money,
                                                 'exp': rew_exp}
                    if rew_item:
                        phases_rewards[rew_phase]['items'] = [rew_item]
                    else:
                        phases_rewards[rew_phase]['items'] = []

                else:
                    phases_rewards[rew_phase]['money'] += rew_money
                    phases_rewards[rew_exp]['exp'] += rew_exp

                    if rew_item:
                        phases_rewards[rew_phase]['items'].append(rew_item)

            total_rewards = {}
            for phase in phases_rewards:
                total_rewards[phase] = Reward(phases_rewards[phase]['items'], phases_rewards[phase]['money'], phases_rewards[phase]['exp'])

            return total_rewards

    def get_phase(self, phase:int):
        quests = self.fetch_phase_quests(phase)
        all_rewards = self.get_reward()
        reward = all_rewards[phase] if phase in all_rewards else None

        total_phase = Phase(self.id, phase, quests, reward)

        return total_phase