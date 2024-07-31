# -*- coding: utf-8 -*-
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