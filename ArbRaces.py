import pprint

from ArbDatabase import DataManager, DataModel


class Race(DataModel):
    def __init__(self, id: str, **kwargs):
        self.race_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('RACES_INIT', f'id = "{self.race_id}"', data_manager=self.data_manager)

        self.label = self.get('name') if self.get('name') is not None else 'Неизвестный'
        self.type = self.get('type')
        self.rarity = self.get('rare')
        self.size = self.get('size')
        self.is_primitive = self.get('primitive') == 1
        self.is_robot = self.get('is_robot') == 1
        self.pain_limit = self.get('pain_limit')
        self.pain_factor = self.get('pain_factor')
        self.max_blood = self.get('blood')
        self.stress_factor = self.get('stress_factor')
        self.pregnancy = self.get('pregnancy')
        self.fertility = self.get('fertilit')
        self.natural_disguise = self.get('disguise')

    def fetch_bodyparts(self):
        body_parts = [part.get('part_id') for part in self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}"')]
        return body_parts

    def get_main_bodypart(self):
        main_bodypart = self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}" AND subpart_of is NULL')[0]
        return main_bodypart.get('part_id')

    def get_equipment_slots(self):
        slots = [slot.get('group') for slot in self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}"')]
        return list(set(slots))
