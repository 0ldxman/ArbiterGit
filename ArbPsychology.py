import pprint

from ArbDatabase import DataManager, DataModel
from ArbCharacterMemory import CharacterMemory
from ArbHealth import Body


class WorldView(DataModel):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'WORLDVIEW', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестное мировоззрение')
        self.chaotic_vector = self.get('chaotic', 0)
        self.kindness_vector = self.get('kindness', 0)
        self.tolerance = self.get('tolerate', 0)

    def worldview_more_kind(self):
        if self.data_manager.check('WORLDVIEW', f'kindness = {self.kindness_vector + 1}'):
            return self.data_manager.select_dict('WORLDVIEW', filter=f'kindness = {self.kindness_vector + 1}')[0]
        else:
            return None

    def worldview_less_kind(self):
        if self.data_manager.check('WORLDVIEW', f'kindness = {self.kindness_vector - 1}'):
            return self.data_manager.select_dict('WORLDVIEW', filter=f'kindness = {self.kindness_vector - 1}')[0]
        else:
            return None

    def worldview_more_chaotic(self):
        if self.data_manager.check('WORLDVIEW', f'chaotic = {self.chaotic_vector + 1}'):
            return self.data_manager.select_dict('WORLDVIEW', filter=f'chaotic = {self.chaotic_vector + 1}')[0]
        else:
            return None

    def worldview_less_chaotic(self):
        if self.data_manager.check('WORLDVIEW', f'chaotic = {self.chaotic_vector - 1}'):
            return self.data_manager.select_dict('WORLDVIEW', filter=f'chaotic = {self.chaotic_vector - 1}')[0]
        else:
            return None

    def get_worldview_difference(self, worldview_id:str):
        if not self.data_manager.check('WORLDVIEW', f'id = "{worldview_id}"'):
            return {}

        dif_view = self.data_manager.select_dict('WORLDVIEW', filter=f'id = "{worldview_id}"')[0]
        dif_kind = dif_view.get('kindness', 0) - self.kindness_vector
        dif_chaos = dif_view.get('chaotic', 0) - self.chaotic_vector

        return {'kindness': dif_kind, 'chaotic': dif_chaos}

    def nearby_worldviews(self):
        nearby_worldviews = {}
        nearby_worldviews['+kind'] = self.worldview_more_kind()
        nearby_worldviews['-kind'] = self.worldview_less_kind()
        nearby_worldviews['+chaos'] = self.worldview_more_chaotic()
        nearby_worldviews['-chaos'] = self.worldview_less_chaotic()

        return nearby_worldviews

    def total_difference(self, worldview_id:str):
        diffirence = self.get_worldview_difference(worldview_id)
        if not diffirence:
            return None
        else:
            diff_sum = abs(diffirence.get('kindness', 0)) + abs(diffirence.get('chaotic', 0))
            return diff_sum


class CharacterMood:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        self.mood = 0
        self.mood += self.memories_effect()
        self.mood += self.pain_effect()

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
        pain = Body(self.id, data_manager=self.data_manager).calculate_pain()
        print(f'Боль {self.id}', pain)
        return -1.5 * pain

    def escape_chance(self):
        if self.mood > -50:
            return 0

        loyalty = CharacterPsychology(self.id, data_manager=self.data_manager).get_loyalty()
        if -100 < self.mood <= -50:
            return 60-loyalty
        else:
            return 100-loyalty


class CharacterPsychology(DataModel):
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'CHARS_PSYCHOLOGY', f'id = {self.id}', data_manager=self.data_manager)

        self.stress = self.get('stress', 0)
        self.worldview = self.get('worldview', None)

        self.stress += self.get_mood_effect()
        if self.stress < 0:
            self.stress = 0

    def get_worldview(self):
        if self.worldview is None:
            return None
        else:
            return WorldView(self.worldview, data_manager=self.data_manager)

    def get_loyalty(self):
        current_org = self.data_manager.select_dict('CHARS_INIT', filter=f'id = {self.id}')[0].get('org', None)
        if current_org:
            if self.data_manager.check('CHARS_REPUTATION', filter=f'id = {self.id} AND org = "{current_org}"'):
                return self.data_manager.select_dict('CHARS_REPUTATION', filter=f'id = {self.id} AND org = "{current_org}"')[0].get('loyalty')
            else:
                query = {
                    'id': self.id,
                    'rep': 0,
                    'loyalty': 50,
                    'org': current_org
                }
                self.data_manager.insert('CHARS_REPUTATION', query)
                return 50
        else:
            return 0

    def get_mood_effect(self):
        mood = CharacterMood(self.id, data_manager=self.data_manager).stress_effect()
        return mood