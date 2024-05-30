# -*- coding: utf-8 -*-
from ArbDatabase import DataManager
import json


class VehicleModule:
    def __init__(self, module_id:str, **kwargs):
        self.module_id = module_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_data()
        self.vehicle_id = data.get('veh_id', None)
        self.max_health = data.get('health', 0)
        self.capacities = json.loads(data.get('capacities','{}'))
        self.linked_module = data.get('linked', None)
        self.is_fatal = data.get('fatal', False) == 1
        self.requirement = json.loads(data.get('requirement','{}')) if data.get('requirment', None) is not None else None

    def fetch_data(self):
        if self.data_manager.check('VEHICLE_MODULES',f'module_id = "{self.module_id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('VEHICLE_MODULES',filter=f'module_id = "{self.module_id}"')[0]


class VehicleType:
    def __init__(self, veh_id:str, **kwargs):
        self.id = veh_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_main_data()
        self.label = data.get('label', 'Неизвестный транспорт')
        self.type = data.get('type', 'Неизвестный вид техники')
        self.max_crew = data.get('max_crew', 0)
        self.fuel_type = data.get('fuel_type', 'Топливо')

    def fetch_main_data(self):
        if self.data_manager.check('VEHICLE_TYPES',f'id = "{self.id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('VEHICLE_TYPES',filter=f'id = "{self.id}"')[0]
