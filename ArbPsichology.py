from ArbDatabase import DataManager
from ArbCharacterMemory import CharacterMemory
from ArbHealth import Body


class WorldView:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестное мировоззрение')
        self.chaotic_vector = data.get('chaotic', None)
        self.kindness_vector = data.get('kindness', None)
        self.tolerance = data.get('tolerate', 0)


    def fetch_data(self):
        if self.data_manager.check('WORLDVIEW', f'id = "{self.id}"'):
            return self.data_manager.select_dict('WORLDVIEW', filter=f'id = "{self.id}"')[0]
        else:
            return {}


class CharacterMood:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        self.mood = 0
        self.mood += self.memories_effect()
        self.mood += self.stress_effect()

    def memories_effect(self):
        return CharacterMemory(self.id, data_manager=self.data_manager).calculate_mood_effect()

    def stress_effect(self):
        if -40 <= self.mood <= 30:
            return 0
        elif 30 < self.mood <= 55:
            return -1
        elif 55 < self.mood <= 80:
            return -2
        elif 80 < self.mood:
            return -3
        elif self.mood < -40:
            return 1
        elif -70 < self.mood <= -40:
            return 2
        else:
            return 3

    def pain_effect(self):
        pain = Body(self.id, data_manager=self.data_manager).calculate_total_pain()
        return -1.5 * pain


class CharacterPsychology:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id
        data = self.fetch_data()
        self.stress = data.get('stress', 0)
        self.worldview = data.get('worldview', None)

    def fetch_data(self):
        if self.data_manager.check('CHARS_PSYCHOLOGY', f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_PSYCHOLOGY', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_worldview(self):
        if self.worldview is None:
            return None
        else:
            return WorldView(self.worldview, data_manager=self.data_manager)