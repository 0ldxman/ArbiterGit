import random

from ArbDatabase import DataManager, DataModel, DataDict
from dataclasses import dataclass


class Rank(DataModel):
    def __init__(self, rank_id:str, **kwargs):
        self.rank_id = rank_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        super().__init__('ORG_RANKS', f'id = "{self.rank_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный ранг')
        self.desc = self.get('desc', 'Нет описания ранга')
        self.power_rank = self.get('lvl', 0)
        self.is_leader = self.get('is_leader', False) == 1
        self.can_invite = self.get('can_invite', False) == 1
        self.can_promote = self.get('can_promote', False) == 1
        self.can_group = self.get('can_group', False) == 1


class Organization(DataModel):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'ORG_INIT', f'id = "{self.id}"')

        self.label = self.get('label', 'Неизвестная организация')
        self.type = self.get('type', 'Неизвестный тип')
        self.parent_org = self.get('parent', None)

        self.tech_tier = self.get('tech_tier', 1)
        self.basic_power = self.get('power', 100)
        self.military = self.get('military', 100)
        self.economy = self.get('economy', 100)
        self.mood = self.get('mood', 100)

    def get_total_power(self):
        total_power = self.basic_power * (self.military/100) * (self.economy/100) * (self.mood/100)
        return total_power

    def fetch_org_ranks(self):
        if self.data_manager.check('ORG_RANKS', f'org = "{self.id}"'):
            return [rank.get('id') for rank in self.data_manager.select_dict('ORG_RANKS', filter=f'org = "{self.id}"')]
        else:
            return []

    def get_inherited_ranks(self):
        ranks = self.fetch_org_ranks()
        if self.parent_org:
            parent_organization = Organization(self.parent_org, data_manager=self.data_manager)
            parent_ranks = parent_organization.get_inherited_ranks()
            ranks.extend(parent_ranks)
        return ranks

    def get_random_lowest_rank(self):
        ranks = self.get_inherited_ranks()
        if not ranks:
            return None
        total_ranks = []

        for rank in ranks:
            if Rank(rank, data_manager=self.data_manager).power_rank == 0:
                total_ranks.append(rank)

        return random.choice(total_ranks)

    def get_lvl_rank(self, level: int):
        ranks = self.get_inherited_ranks()
        total_choices = []
        for rank in ranks:
            if Rank(rank, data_manager=self.data_manager).power_rank == level:
                total_choices.append(rank)

        if total_choices:
            return random.choice(total_choices)
        else:
            return self.get_random_lowest_rank()
