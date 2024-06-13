from ArbDatabase import DataManager
from dataclasses import dataclass


class OrgTraitType:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.fetch_trait_data()
        self.label = data.get('label', 'Неизвестный модификатор')
        self.power = data.get('power', 0)
        self.economy = data.get('economy', 0)
        self.military = data.get('military', 0)
        self.mood = data.get('mood', 0)

    def fetch_trait_data(self):
        if self.data_manager.check('ORG_TRAITS_INIT', f'id = "{self.id}"'):
            return self.data_manager.select_dict('ORG_TRAITS_INIT', filter=f'id = "{self.id}"')[0]
        else:
            return {}

@dataclass()
class OrgTrait:
    trait_type: OrgTraitType
    cycles: int


class Organization:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.fetch_org_data()
        self.label = data.get('label', 'Неизвестная организация')
        self.type = data.get('type', 'Неизвестный тип')
        self.parent_org = data.get('parent', None)

        self.tech_tier = data.get('tech_tier', 1)
        self.basic_power = data.get('power', 100)
        self.military = data.get('military', 100)
        self.economy = data.get('economy', 100)
        self.mood = data.get('mood', 100)
        self.calculate_traits_effect()

    def fetch_org_data(self):
        if self.data_manager.check('ORG_INIT',f'id = "{self.id}"'):
            return self.data_manager.select_dict('ORG_INIT', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def get_total_power(self):
        total_power = self.basic_power * (self.military/100) * (self.economy/100) * (self.mood/100)
        return total_power

    def calculate_traits_effect(self):
        traits = self.get_traits()
        for trait in traits:
            self.basic_power += trait.trait_type.power
            self.military += trait.trait_type.military
            self.economy += trait.trait_type.economy
            self.mood += trait.trait_type.mood

    def get_traits(self):
        if self.data_manager.check('ORG_TRAITS',f'id = "{self.id}"'):
            traits = self.data_manager.select_dict('ORG_TRAITS', filter=f'id = "{self.id}"')
            return [OrgTrait(OrgTraitType(trait.get('trait_id'), data_manager=self.data_manager), trait.get('cycles')) for trait in traits]
        else:
            return []
