# -*- coding: utf-8 -*-
from typing import Dict, Any

from ArbDatabase import DataManager, DataModel, DataDict


class Sound(DataModel):
    def __init__(self, id: str, **kwargs):
        self.sound_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'SOUNDS', f'id = "{self.sound_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный звук')
        self.distance = self.get('distance', 0)
        self.detect_chance = self.get('detect_chance', 0)
        self.description = self.get('desc', 'Неизвестный звук')

    @staticmethod
    def create_sound(character_id:int, sound_type:str, volume:int=None, content:str=None):
        db = DataManager()
        if not db.check('BATTLE_CHARACTERS', f'character_id = {character_id}'):
            return None

        battle_data = db.select_dict('BATTLE_CHARACTERS', filter=f'character_id = {character_id}')[0]
        battle_id = battle_data.get('battle_id')
        layer_id = battle_data.get('layer_id')

        sound_id = db.maxValue('BATTLE_SOUNDS', 'id') + 1

        query = {
            'id': sound_id,
            'battle_id': battle_id,
            'layer_id': layer_id,
            'actor_id': character_id,
            'sound_id': sound_type,
            'volume': volume,
            'content': content,
        }
        db.insert('BATTLE_SOUNDS', query)


class InBattleSound(Sound):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = DataDict('BATTLE_SOUNDS', f'id = {self.id}', data_manager=self.data_manager)
        self.battle_id = data.get('battle_id', None)
        self.actor_id = data.get('actor_id', None)
        self.sound_type = data.get('sound_id', None)
        self.layer_id = data.get('layer_id', None)
        self.volume = data.get('volume', 0)
        self.content = data.get('content', '')

        super().__init__(self.sound_type, data_manager=self.data_manager)

    def update_record(self, data: Dict[str, Any]):
        model = DataModel('BATTLE_SOUNDS', f'id = {self.id}')
        model.update_record(data)

    def delete(self):
        self.data_manager.delete('BATTLE_SOUNDS',f'id = {self.id}')

    def get_actor_id(self):
        return self.actor_id

    def get_detection_chance(self, distance: int | float):
        volume_factor = self.volume/100

        distance_modificator = max(0,self.distance*volume_factor-distance)/(self.distance*volume_factor)

        total_chance = (self.detect_chance*volume_factor) * distance_modificator

        return total_chance

    def __repr__(self):
        return f'BattleSound[{self.id},{self.sound_id}]'