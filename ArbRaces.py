import pprint

from ArbDatabase import DataManager, DataModel, DataObject, EID, DEFAULT_MANAGER


class Race(DataObject):
    def __init__(self, id: str, **kwargs):
        self.race_id = id

        super(Race, self).__init__('RACES_INIT', EID(id=self.race_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('name', 'Неизвестная раса')
        self._type = self.field('type', None)
        self._rarity = self.field('rare', 1000)
        self._size = self.field('size', 1)
        self._is_primitive = self.field('is_primitive', 1)
        self._is_robot = self.field('is_robot', 0)
        self._pain_limit = self.field('pain_limit', 100)
        self._pain_factor = self.field('pain_factor', 1)
        self._max_blood = self.field('blood', 100)
        self._stress_factor = self.field('stress_factor', 1)
        self._pregnancy = self.field('pregnancy', 0)
        self._fertility = self.field('fertilit', 0)
        self._natural_disguise = self.field('disguise', 0)
        self._race_range = self.field('race_range', '0-1')

    @property
    def label(self):
        return self._label.load(self.data_manager)

    @property
    def name(self):
        return self.label

    @property
    def type(self):
        return self._type.load(self.data_manager)

    @property
    def rarity(self):
        return self._rarity.load(self.data_manager)

    @property
    def size(self):
        return self._size.load(self.data_manager)

    @property
    def is_primitive(self):
        return self._is_primitive.load(self.data_manager) == 1

    @property
    def is_robot(self):
        return self._is_robot.load(self.data_manager) == 1

    @property
    def pain_limit(self):
        return self._pain_limit.load(self.data_manager)

    @property
    def pain_factor(self):
        return self._pain_factor.load(self.data_manager)

    @property
    def max_blood(self):
        return self._max_blood.load(self.data_manager)

    @property
    def stress_factor(self):
        return self._stress_factor.load(self.data_manager)

    @property
    def pregnancy(self):
        return self._pregnancy.load(self.data_manager)

    @property
    def fertility(self):
        return self._fertility.load(self.data_manager)

    @property
    def natural_disguise(self):
        return self._natural_disguise.load(self.data_manager)

    @property
    def race_range(self):
        return self._race_range.load(self.data_manager)

    @property
    def age_range(self):
        return self.race_range

    @property
    def min_age(self):
        min_age = int(self.race_range.split('-')[0])
        if min_age < 0:
            return 0
        return min_age

    @property
    def max_age(self):
        max_age = int(self.race_range.split('-')[1])
        if max_age < self.min_age:
            return self.min_age
        return max_age

    @property
    def race_range_min(self):
        return self.min_age

    @property
    def race_range_max(self):
        return self.max_age

    def compare_age_and_race_range(self, age:int):
        if age < self.race_range_min:
            return 'Юный'
        elif age > self.race_range_max:
            return 'Пожилой'
        else:
            return 'Средних лет'

    def fetch_bodyparts(self):
        body_parts = [part.get('part_id') for part in self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}"')]
        return body_parts

    def get_main_bodypart(self):
        main_bodypart = self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}" AND subpart_of is NULL AND `group` is not NULL')[0]
        return main_bodypart.get('part_id')

    def get_equipment_slots(self):
        slots = [slot.get('group') for slot in self.data_manager.select_dict('RACES_BODYPART', filter=f'race = "{self.race_id}"')]
        return list(set(slots))
