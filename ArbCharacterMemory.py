# -*- coding: utf-8 -*-
import datetime
from dataclasses import dataclass
from ArbDatabase import DataManager


class RelationType:
    def __init__(self, relation_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.relation_id = relation_id
        data = self.fetch_relation_role_data()
        self.label = data.get('label', 'Неивзестное отношение')
        self.desc = data.get('desc', 'Нет описания отношений')
        self.trust = data.get('trust', 0)
        self.sympathy = data.get('sympathy', 0)
        self.respect = data.get('respect', 0)
        self.love = data.get('love', 0)

    def fetch_relation_role_data(self):
        if not self.data_manager.check('RELATION_ROLES', f'id = "{self.relation_id}"'):
            return {}
        else:
            return self.data_manager.select_dict('RELATION_ROLES', filter=f'id = "{self.relation_id}"')[0]

    def __repr__(self):
        return f'RelationType.{self.relation_id}'

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
        self.love = data.get('love', 0)

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

    def check_if_timeout(self):
        now = datetime.datetime.today()
        then = datetime.datetime.strptime(self.date, '%Y-%m-%d')

        delta = now - then
        delta = delta.days

        if self.is_fixed:
            return False, delta

        if delta >= self.time_to_forget:
            return True, delta
        else:
            return False, delta

    def forget_if_timeout(self):
        is_forgotten, time = self.check_if_timeout()

        if is_forgotten:
            self.forget()
            return True, time
        else:
            return False, time


@dataclass()
class Relation:
    actor_id: int
    subject_id: int
    relation_type: RelationType
    family_relation_type: RelationType | None
    trust: int
    sympathy: int
    respect: int
    love:int

class CharacterRelations:
    def __init__(self, character_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = character_id

        self.relation_to_character = self.fetch_relation_to_character()
        self.relation_of_character = self.fetch_character_relation()
        self.relationships = self.get_character_relationships()
    def get_character_relationships(self):
        of_character = self.fetch_character_relation()
        to_character = self.fetch_relation_to_character()

        total_relationships = {}
        for i in of_character.keys():
            total_relationships[i] = [of_character[i], None]

        for i in to_character.keys():
            if i not in of_character:
                total_relationships[i] = [None, to_character[i]]
            else:
                total_relationships[i][1] = to_character[i]

        return total_relationships


    def fetch_character_relation(self) -> dict[Relation]:
        if self.data_manager.check('CHARS_RELATIONS',f'id = {self.id}') is None:
            return {}

        relationships = {}
        process_list = self.data_manager.select_dict('CHARS_RELATIONS',filter=f'id = {self.id}')
        for rel in process_list:
            c_rel = Relation(actor_id=self.id,
                             subject_id=rel.get('subject_id', None),
                             relation_type=RelationType(rel.get('relation_id', 'Unknown'), data_manager=self.data_manager) if rel.get('relation_id', None) else None,
                             family_relation_type=RelationType(rel.get('family_id', None), data_manager=self.data_manager) if rel.get('family_id', None) else None,
                             trust=rel.get('trust', 0) if rel.get('trust', None) else 0,
                             sympathy=rel.get('sympathy', 0) if rel.get('sympathy', None) else 0,
                             respect=rel.get('respect', 0) if rel.get('respect', None) else 0,
                             love=rel.get('love', 0) if rel.get('love', None) else 0)

            relationships[rel.get('subject_id', None)] = c_rel

        return relationships

    def fetch_relation_to_character(self):
        if self.data_manager.check('CHARS_RELATIONS', f'subject_id = {self.id}') is None:
            return {}

        relationships = {}
        process_list = self.data_manager.select_dict('CHARS_RELATIONS', filter=f'subject_id = {self.id}')
        for rel in process_list:
            c_rel = Relation(actor_id=rel.get('id', None),
                             subject_id=self.id,
                             relation_type=RelationType(rel.get('relation_id', 'Unknown'), data_manager=self.data_manager) if rel.get('relation_id', None) else None,
                             family_relation_type=RelationType(rel.get('family_id', None), data_manager=self.data_manager) if rel.get('family_id', None) else None,
                             trust=rel.get('trust', 0) if rel.get('trust', None) else 0,
                             sympathy=rel.get('sympathy', 0) if rel.get('sympathy', None) else 0,
                             respect=rel.get('respect', 0) if rel.get('respect', None) else 0,
                             love=rel.get('love', 0) if rel.get('love', None) else 0)

            relationships[rel.get('id', None)] = c_rel

        return relationships

print(CharacterRelations(0).get_character_relationships())