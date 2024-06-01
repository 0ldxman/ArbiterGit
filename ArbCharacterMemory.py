# -*- coding: utf-8 -*-
import datetime

from ArbDatabase import DataManager


class MemoryEvent:
    def __init__(self, event_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.event_type = event_id
        data = self.fetch_event_data()

        self.label = data.get('label', 'Неизвестное событие')
        self.event_class = data.get('type', 'Нейтральное')

        self.mood = data.get('mood', 0)
        self.relation = data.get('relation', 0)
        self.trust = data.get('trust', 0)
        self.sympathy = data.get('sympathy', 0)
        self.respect = data.get('respect', 0)

        self.time_to_forget = data.get('time_to_forget', 0)
        self.description = data.get('desc', 'Неизвестное событие произошло...')

    def fetch_event_data(self):
        if self.data_manager.check('EVENT_INIT',f'id = "{self.event_type}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('EVENT_INIT',filter=f'id = "{self.event_type}"')[0]


class CharacterMemoryEvent(MemoryEvent):
    def __init__(self, event_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.memory_id = event_id
        data = self.fetch_current_event()
        self.event_type = data.get('event_type', 'MiscNeutral')
        super().__init__(self.event_type, data_manager=self.data_manager)
        self.description = data.get('desc', self.description)

        self.actor = data.get('id', None)
        self.subject = data.get('subject_id', None)
        self.date = data.get('date', None)
        self.is_fixed = data.get('fixed', 0) == 1

    def fetch_current_event(self):
        if self.data_manager.check('CHARS_MEMORY', f'event_id = {self.memory_id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('CHARS_MEMORY',filter=f'event_id = {self.memory_id}')[0]

    def forget(self):
        self.data_manager.delete('CHARS_MEMORY', f'event_id = {self.memory_id}')

    def check_if_forgotten(self):
        if self.is_fixed:
            return False

        now = datetime.datetime.today()
        then = datetime.datetime.strptime(self.date, '%Y-%m-%d')

        delta = now - then
        delta = delta.days

        if delta >= self.time_to_forget:
            return True, delta
        else:
            return False, delta

    def forget_if_forgotten(self):
        is_forgotten, time = self.check_if_forgotten()

        if is_forgotten:
            self.forget()
            return True, time
        else:
            return False, time

# print(CharacterMemoryEvent(0).check_if_forgotten())