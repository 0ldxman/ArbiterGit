# -*- coding: utf-8 -*-
from ArbDatabase import DataManager


class CrewRole:
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.get_role_data()
        self.label = data.get('label')
        self.can_move = data.get('can_move', 0) == 1
        self.can_attack = data.get('can_attack', 0) == 1
        self.only_one_module = data.get('only_module', 0) == 1

    def get_role_data(self):
        if self.data_manager.check('VEHICLE_ROLES', f'id = "{self.id}"'):
            return self.data_manager.select_dict('VEHICLE_ROLES', filter=f'id = "{self.id}"')[0]
        else:
            return {}


class VehicleModule:
    def __init__(self, module_id:str, **kwargs):
        self.module_id = module_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_data()
        self.vehicle_id = data.get('veh_id', None)
        self.max_health = data.get('health', 0)
        self.capacity = data.get('capacity', None)
        self.capacity_value = data.get('efficiency', 0)
        self.linked_module = data.get('linked', None)
        self.fatality = data.get('fatal', 0)
        self.role = data.get('role', None)
        self.max_crew = data.get('crew', 0)

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
        self.skill = data.get('skill', 'Transport')
        self.max_crew = data.get('max_crew', 0)
        self.fuel_type = data.get('fuel_type', 'Топливо')

        self.corpus_material = data.get('corpus_material', 'Steel')
        self.efficiency = data.get('efficiency', 100)

    def fetch_main_data(self):
        if self.data_manager.check('VEHICLE_TYPES',f'id = "{self.id}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('VEHICLE_TYPES',filter=f'id = "{self.id}"')[0]

    def get_modules(self):
        if self.data_manager.check('VEHICLE_MODULES',f'veh_id = "{self.id}"'):
            return self.data_manager.select_dict('VEHICLE_MODULES',filter=f'id = "{self.id}"')
        else:
            return []


class Vehicle:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        main_data = self.get_main_info()
        self.type = main_data.get('type', None)
        self.owner = main_data.get('owner', None)
        self.closed = main_data.get('closed', 0) == 1

        self.crew = self.get_crew()

    def get_main_info(self):
        if self.data_manager.check('VEHICLE', f'id = {self.id}'):
            return self.data_manager.select_dict('VEHICLE', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_crew(self):
        if self.data_manager.check('VEHICLE_CREW', f'veh_id = {self.id}'):
            return self.data_manager.select_dict('VEHICLE_CREW', filter=f'veh_id = {self.id}')
        else:
            return []