# -*- coding: utf-8 -*-
from ArbDatabase import DataManager


class Sound:
    def __init__(self, id:str, **kwargs):
        self.sound_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_data()

        self.label = data.get('label', 'Неизвестный звук')
        self.distance = data.get('distance', 0)
        self.detect_chance = data.get('detect_chance', 0)
        self.round_factor = data.get('round_factor', 1)
        self.description = data.get('desc', 'Неизвестный звук')

    def fetch_data(self):
        if self.data_manager.check('SOUNDS',f'id = "{self.sound_id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('SOUNDS',filter=f'id = "{self.sound_id}"')[0]


class InBattleSound(Sound):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_battle_sound_data()
        self.battle_id = data.get('battle_id', None)
        self.actor_id = data.get('actor_id', None)
        self.sound_type = data.get('sound_id', None)
        self.layer_id = data.get('layer_id', None)
        self.round = data.get('round', None)
        self.volume = data.get('volume', 0)

        super().__init__(self.sound_type, data_manager=self.data_manager)

    def fetch_battle_sound_data(self):
        if self.data_manager.check('BATTLE_SOUNDS',f'id = {self.id}') is None:
            return {}
        else:
            return self.data_manager.select_dict('BATTLE_SOUNDS', filter=f'id = {self.id}')[0]

    def delete(self):
        self.data_manager.delete('BATTLE_SOUNDS',f'id = {self.id}')

    def get_actor_id(self):
        return self.actor_id

    def get_detection_chance(self, distance:int, current_round:int):
        volume_factor = self.volume/100

        round_factor = self.round_factor**(current_round - self.round)
        distance_modificator = max(0,self.distance*volume_factor-distance)/(self.distance*volume_factor)

        total_chance = (self.detect_chance*volume_factor) * distance_modificator * round_factor

        return total_chance

    def __repr__(self):
        return f'BattleSound[{self.id},{self.sound_id}]'