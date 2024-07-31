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
        self.trust = data.get('trust', 0) if data.get('trust', 0) else 0
        self.sympathy = data.get('sympathy', 0) if data.get('sympathy', 0) else 0
        self.respect = data.get('respect', 0) if data.get('respect', 0) else 0
        self.love = data.get('love', 0) if data.get('love', 0) else 0

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

        self.mood = data.get('mood', 0) if data.get('mood', 0) else 0
        self.relation = data.get('relation', 0) if data.get('relation', 0) else 0
        self.trust = data.get('trust', 0) if data.get('trust', 0) else 0
        self.sympathy = data.get('sympathy', 0) if data.get('sympathy', 0) else 0
        self.respect = data.get('respect', 0) if data.get('respect', 0) else 0
        self.love = data.get('love', 0) if data.get('love', 0) else 0

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

    def fix_memory(self):
        query = {'fixed': 1}
        self.data_manager.update('CHARS_MEMORY', query, f'event_id = {self.memory_id}')

    def blame(self, character_id:int):
        query = {'subject_id': character_id}
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

@dataclass()
class Relation:
    actor_id: int
    subject_id: int
    relation_type: RelationType
    family_relation_type: RelationType | None
    trust: int
    sympathy: int
    respect: int
    love: int

@dataclass()
class Relationship:
    actor: int
    subject: int

    relation_of_actor: Relation | None
    relation_to_actor: Relation | None

    active_events: list

    def get_relation_of_actor(self):
        trust = 0
        sympathy = 0
        respect = 0
        love = 0

        label = None

        if not self.relation_of_actor:
            return 0, 0, 0, 0, None
        else:
            trust += self.relation_of_actor.trust
            sympathy += self.relation_of_actor.sympathy
            respect += self.relation_of_actor.respect
            love += self.relation_of_actor.love

            if self.relation_of_actor.relation_type:
                trust += self.relation_of_actor.relation_type.trust
                sympathy += self.relation_of_actor.relation_type.sympathy
                respect += self.relation_of_actor.relation_type.respect
                love += self.relation_of_actor.relation_type.love

                label = self.relation_of_actor.relation_type.label

            if self.relation_of_actor.family_relation_type:
                trust += self.relation_of_actor.family_relation_type.trust
                sympathy += self.relation_of_actor.family_relation_type.sympathy
                respect += self.relation_of_actor.family_relation_type.respect
                love += self.relation_of_actor.family_relation_type.love

                label = self.relation_of_actor.family_relation_type.label

            memories_effect = CharacterMemory(self.actor).relation_effect_to_subject(self.subject)
            trust += memories_effect['trust']
            sympathy += memories_effect['sympathy']
            respect += memories_effect['respect']
            love += memories_effect['love']

            return trust, sympathy, respect, love, label

    def get_relation_to_actor(self):
        trust = 0
        sympathy = 0
        respect = 0
        love = 0

        label = None

        if not self.relation_to_actor:
            return 0, 0, 0, 0, None
        else:
            trust += self.relation_to_actor.trust
            sympathy += self.relation_to_actor.sympathy
            respect += self.relation_to_actor.respect
            love += self.relation_to_actor.love

            if self.relation_to_actor.relation_type:
                trust += self.relation_to_actor.relation_type.trust
                sympathy += self.relation_to_actor.relation_type.sympathy
                respect += self.relation_to_actor.relation_type.respect
                love += self.relation_to_actor.relation_type.love

                label = self.relation_to_actor.relation_type.label

            if self.relation_to_actor.family_relation_type:
                trust += self.relation_to_actor.family_relation_type.trust
                sympathy += self.relation_to_actor.family_relation_type.sympathy
                respect += self.relation_to_actor.family_relation_type.respect
                love += self.relation_to_actor.family_relation_type.love

                label = self.relation_to_actor.family_relation_type.label

            memories_effect = CharacterMemory(self.subject).relation_effect_to_subject(self.actor)
            trust += memories_effect['trust']
            sympathy += memories_effect['sympathy']
            respect += memories_effect['respect']
            love += memories_effect['love']

            return trust, sympathy, respect, love, label

    def dict_attributes(self):
        trust, sympathy, respect, love, label = self.get_relation_of_actor()
        s_trust, s_sympathy, s_respect, s_love, s_label = self.get_relation_to_actor()

        total_attributes = {'trust': (trust, s_trust),
                            'sympathy': (sympathy, s_sympathy),
                            'respect': (respect, s_respect),
                            'love': (love, s_love),
                            'label': (label, s_label)}

        return total_attributes

    def __repr__(self):
        from ArbCharacters import Character
        if self.relation_of_actor is None:
            return ''
        else:
            trust, sympathy, respect, love, label = self.get_relation_of_actor()
            s_trust, s_sympathy, s_respect, s_love, s_label = self.get_relation_to_actor()

            return f"""-# - {label} **{Character(self.subject).name}** {sympathy:+} ({s_sympathy:+})"""
            #> Доверие: {trust:+} ({s_trust:+})
            #> Уважение: {respect:+} ({s_respect:+})
            #> Влечение: {love:+} ({s_love:+})\n\n


class CharacterRelations:
    def __init__(self, character_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = character_id

        self.relation_to_character = self.fetch_relation_to_character()
        self.relation_of_character = self.fetch_character_relation()
        self.relationships = self.get_character_relationships()

    def get_character_relationships(self):
        of_character = self.relation_of_character
        to_character = self.relation_to_character

        total_relationships = {}
        for i in of_character.keys():
            total_relationships[i] = [of_character[i], None]

        for i in to_character.keys():
            if i not in of_character:
                total_relationships[i] = [None, to_character[i]]
            else:
                total_relationships[i][1] = to_character[i]

        for i in total_relationships.keys():
            act_relation = total_relationships[i][0]
            s_relation = total_relationships[i][1]

            relationship = Relationship(self.id, i, act_relation, s_relation, [])
            total_relationships[i] = relationship

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

    def string_relations(self):
        relations_str = ''
        for rel in self.relationships.values():
            if rel.__repr__():
                relations_str += rel.__repr__() + '\n'

        return relations_str
