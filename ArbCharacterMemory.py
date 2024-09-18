# -*- coding: utf-8 -*-
import datetime
from dataclasses import dataclass
from ArbDatabase import DataManager, DataModel


class RelationType(DataModel):
    def __init__(self, relation_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.relation_id = relation_id

        DataModel.__init__(self, 'RELATION_ROLES', f'id = "{self.relation_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неивзестное отношение')
        self.desc = self.get('desc', 'Нет описания отношений')
        self.trust = self.get('trust', 0) if self.get('trust', 0) else 0
        self.sympathy = self.get('sympathy', 0) if self.get('sympathy', 0) else 0
        self.respect = self.get('respect', 0) if self.get('respect', 0) else 0
        self.love = self.get('love', 0) if self.get('love', 0) else 0

    def __repr__(self):
        return f'RelationType.{self.relation_id}'


class MemoryEvent(DataModel):
    def __init__(self, event_id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.event_type = event_id

        DataModel.__init__(self, 'EVENT_INIT', f'id = "{self.event_type}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестное событие')
        self.event_class = self.get('type', 'Нейтральное')

        self.mood = self.get('mood', 0) if self.get('mood', 0) else 0
        self.relation = self.get('relation', 0) if self.get('relation', 0) else 0
        self.trust = self.get('trust', 0) if self.get('trust', 0) else 0
        self.sympathy = self.get('sympathy', 0) if self.get('sympathy', 0) else 0
        self.respect = self.get('respect', 0) if self.get('respect', 0) else 0
        self.love = self.get('love', 0) if self.get('love', 0) else 0

        self.time_to_forget = self.get('time_to_forget', 0)
        self.description = self.get('desc', 'Неизвестное событие произошло...')

    @staticmethod
    def create_memory(character_id:int, event_type:str, desc:str=None, subject_id:int=None, date:str=None, fixed:bool=False):
        db = DataManager()

        event_id = db.maxValue('CHARS_MEMORY', 'event_id') + 1
        query = {
            'id': character_id,
            'event_id': event_id,
            'event_type': event_type,
            'desc': desc,
            'subject_id': subject_id,
            'date': date if date else datetime.datetime.today().strftime('%Y-%m-%d'),
            'fixed': fixed
        }
        db.insert('CHARS_MEMORY', query)

        return event_id


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

    def delete_memory(self):
        self.data_manager.delete('CHARS_MEMORY', f'event_id = {self.memory_id}')

    def fetch_current_event(self):
        if self.data_manager.check('CHARS_MEMORY', f'event_id = {self.memory_id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('CHARS_MEMORY',filter=f'event_id = {self.memory_id}')[0]

    def forget(self):
        self.data_manager.delete('CHARS_MEMORY', f'event_id = {self.memory_id}')

    def check_if_timeout(self, date:str):
        now = datetime.datetime.strptime(date, '%Y-%m-%d') if date else datetime.datetime.today()
        then = datetime.datetime.strptime(self.date, '%Y-%m-%d')

        delta = now - then
        delta = delta.days

        if self.is_fixed:
            return False, delta

        if delta >= self.time_to_forget:
            return True, delta
        else:
            return False, delta

    def time_delta(self, date:str):
        now = datetime.datetime.strptime(date, '%Y-%m-%d') if date else datetime.datetime.today()
        then = datetime.datetime.strptime(self.date, '%Y-%m-%d')
        delta = now - then

        return delta.days

    def forget_if_timeout(self, date:str):
        is_forgotten, time = self.check_if_timeout(date)

        if is_forgotten:
            self.forget()
            return True, time
        else:
            return False, time

    def fix_memory(self):
        query = {'fixed': 1}
        self.data_manager.update('CHARS_MEMORY', query, f'event_id = {self.memory_id}')

    def unfix_memory(self):
        query = {'fixed': 0}
        self.data_manager.update('CHARS_MEMORY', query, f'event_id = {self.memory_id}')

    def blame(self, character_id:int):
        query = {'subject_id': character_id}
        self.data_manager.update('CHARS_MEMORY', query, f'event_id = {self.memory_id}')

    def unblame(self):
        query = {'subject_id': None}
        self.data_manager.update('CHARS_MEMORY', query, f'event_id = {self.memory_id}')

    def __repr__(self):
        return f'MemoryEvent(id.{self.memory_id}, Type.{self.event_type}, Subject.{self.subject})'


class CharacterMemory:
    def __init__(self, character_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = character_id

    def calculate_mood_effect(self):
        c_events = self.fetch_active_events()
        total_mood = 0
        for event in c_events:
            total_mood += event.mood

        return total_mood

    def fetch_active_events(self):
        if self.data_manager.check('CHARS_MEMORY',f'id = {self.id}') is None:
            return []
        else:
            response = []
            total_events = self.data_manager.select_dict('CHARS_MEMORY', filter=f'id = {self.id}')
            for event in total_events:
                response.append(CharacterMemoryEvent(event.get('event_id'), data_manager=self.data_manager))

            return response

    def group_memory_by_subject(self):
        total_memories = self.fetch_active_events()
        subject_memories = {}
        for memory in total_memories:
            if memory.subject in subject_memories:
                subject_memories[memory.subject].append(memory)
            else:
                subject_memories[memory.subject] = [memory]

        return subject_memories

    def relation_effect_to_subject(self, subject: int):
        trust = 0
        sympathy = 0
        respect = 0
        love = 0
        memories = self.group_memory_by_subject()
        if subject not in memories:
            return {'trust': trust,
                    'sympathy': sympathy,
                    'respect': respect,
                    'love': love}
        else:
            for memory in memories[subject]:
                trust += memory.trust + memory.relation
                sympathy += memory.sympathy + memory.relation
                respect += memory.respect + memory.relation
                love += memory.love + memory.relation

            return {'trust': trust,
                    'sympathy': sympathy,
                    'respect': respect,
                    'love': love}

    def update_memories(self, date:str=None):
        date = date if date else datetime.datetime.today().date().strftime('%Y-%m-%d')

        memories = self.fetch_active_events()
        for memory in memories:
            memory.forget_if_timeout(date)


@dataclass()
class RelationValues:
    trust: int
    sympathy: int
    respect: int
    love: int


@dataclass()
class Relation:
    characters: list
    relation_type: RelationType | None
    family_type: RelationType | None
    trust: int
    sympathy: int
    respect: int
    love: int

    def get_another_subject(self, character_id:int):
        subject_id = None
        for actor in self.characters:
            if actor != character_id:
                subject_id = actor
                break

        return subject_id

    def get_character_id_and_subject_id(self):
        character_id, subject_id = self.characters
        return character_id, subject_id

    def update(self, query:dict):
        character_id, subject_id = self.get_character_id_and_subject_id()
        db = DataManager()
        if db.check('CHARS_RELATIONS', f'id = {character_id} AND subject_id = {subject_id}'):
            db.update('CHARS_RELATIONS', query, f'id = {character_id} AND subject_id = {subject_id}')
        elif db.check('CHARS_RELATIONS', f'id = {subject_id} AND subject_id = {character_id}'):
            db.update('CHARS_RELATIONS', query, f'id = {subject_id} AND subject_id = {character_id}')

    def set_relation(self, relation_id:str | None):
        query = {
            'relation_id': relation_id
        }
        self.update(query)

    def set_family(self, family_id:str | None):
        query = {
            'family_id': family_id
        }
        self.update(query)

    def set_trust(self, trust:int):
        self.trust = trust
        query = {
            'trust': trust
        }
        self.update(query)

    def set_sympathy(self, sympathy:int):
        self.sympathy = sympathy
        query = {
           'sympathy': sympathy
        }
        self.update(query)

    def set_respect(self, respect:int):
        self.respect = respect
        query = {
           'respect': respect
        }
        self.update(query)

    def set_love(self, love:int):
        self.love = love
        query = {
            'love': love
        }
        self.update(query)

    def fetch_memories(self):
        character_id, subject_id = self.get_character_id_and_subject_id()
        character_memories = CharacterMemory(character_id).relation_effect_to_subject(subject_id)
        subject_memories = CharacterMemory(subject_id).relation_effect_to_subject(character_id)

        total_dict = {
            'trust': character_memories.get('trust', 0) + subject_memories.get('trust', 0),
            'sympathy': character_memories.get('sympathy', 0) + subject_memories.get('sympathy', 0),
            'respect': character_memories.get('respect', 0) + subject_memories.get('respect', 0),
            'love': character_memories.get('love', 0) + subject_memories.get('love', 0)
        }

        return total_dict

    def get_total_relations(self):
        memories_effects = self.fetch_memories()

        relation_trust = self.relation_type.trust if self.relation_type else 0
        relation_sympathy = self.relation_type.sympathy if self.relation_type else 0
        relation_respect = self.relation_type.respect if self.relation_type else 0
        relation_love = self.relation_type.love if self.relation_type else 0

        family_trust = self.family_type.trust if self.family_type else 0
        family_sympathy = self.family_type.sympathy if self.family_type else 0
        family_respect = self.family_type.respect if self.family_type else 0
        family_love = self.family_type.love if self.family_type else 0

        relation_values = RelationValues(self.trust + memories_effects.get('trust') + relation_trust + family_trust,
                                         self.sympathy + memories_effects.get('sympathy') + relation_sympathy + family_sympathy,
                                         self.respect + memories_effects.get('respect') + relation_respect + family_respect,
                                         self.love + memories_effects.get('love') + relation_love + family_love)

        return relation_values

    def get_avg_relation(self):
        total_relation = self.get_total_relations()
        return (total_relation.trust + total_relation.sympathy + total_relation.respect + total_relation.love) / 4


class Relations:
    def __init__(self, character_id:int, **kwargs):
        self.id = int(character_id)
        self.data_manager = kwargs.get('data_manager') if kwargs.get('data_manager') else DataManager()

    def fetch_relations(self):
        data = self.data_manager.select_dict('CHARS_RELATIONS', filter=f'id = {self.id} OR subject_id = {self.id}')
        relations = {}
        for relation in data:
            characters = [relation.get('id'), relation.get('subject_id')]
            relation_type = RelationType(relation.get('relation_id'), data_manager=self.data_manager) if relation.get('relation_id') else None
            family_type = RelationType(relation.get('family_id'), data_manager=self.data_manager) if relation.get('family_id') else None
            trust = relation.get('trust') if relation.get('trust') else 0
            sympathy = relation.get('sympathy') if relation.get('sympathy') else 0
            respect = relation.get('respect') if relation.get('respect') else 0
            love = relation.get('love') if relation.get('love') else 0
            rel = Relation(characters, relation_type, family_type, trust, sympathy, respect, love)

            subject = rel.get_another_subject(self.id)
            relations[subject] = rel

        return relations

    def get_relation_to_character(self, character_id:int):
        relations = self.fetch_relations()
        return relations.get(character_id, None)

    def update_relation(self, character_id: int, relation_id:str=None, family_id:str=None, trust:int=None, sympathy:int=None, respect:int=None, love:int=None):
        relation = self.get_relation_to_character(character_id)
        if not relation:
            self.create_familiar(self.id, character_id, relation_id, family_id, trust=trust, sympathy=sympathy, respect=respect, love=love)
            return self.get_relation_to_character(character_id)

        relation.set_relation(relation_id) if relation_id is not None else relation.set_relation(relation.relation_type.relation_id)
        relation.set_family(family_id) if family_id is not None else relation.set_family(relation.family_type.relation_id)
        relation.set_trust(relation.trust + trust) if trust is not None else relation.set_trust(relation.trust)
        relation.set_sympathy(relation.sympathy + sympathy) if sympathy is not None else relation.set_sympathy(relation.sympathy)
        relation.set_respect(relation.respect + respect) if respect is not None else relation.set_respect(relation.respect)
        relation.set_love(relation.love + love) if love is not None else relation.set_love(relation.love)

        return relation

    @staticmethod
    def create_familiar(character_id: int, familiar_id: int, relation_id: str = None, family_id: str = None, **kwargs):
        db = DataManager()

        if db.check('CHARS_RELATIONS', f'id = {character_id} AND subject_id = {familiar_id}'):
            return
        elif db.check('CHARS_RELATIONS', f'id = {familiar_id} AND subject_id = {character_id}'):
            return

        query = {
            'id': character_id,
            'subject_id': familiar_id,
            'relation_id': relation_id,
            'family_id': family_id,
            'trust': kwargs.get('trust', 0) if kwargs.get('trust') else 0,
            'sympathy': kwargs.get('sympathy', 0) if kwargs.get('sympathy') else 0,
            'respect': kwargs.get('respect', 0) if kwargs.get('respect') else 0,
            'love': kwargs.get('love', 0) if kwargs.get('love') else 0
        }
        db.insert('CHARS_RELATIONS', query)

    @staticmethod
    def remove_familiar(character_id: int, familiar_id: int):
        db = DataManager()
        db.delete('CHARS_RELATIONS', f'id = {character_id} AND subject_id = {familiar_id}')
        db.delete('CHARS_RELATIONS', f'subject_id = {character_id} AND id = {familiar_id}')
