# -*- coding: utf-8 -*-
from ArbDatabase import DataManager


class GroupRole:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_role_data()

        self.label = data.get('label', 'Неизвестная роль')
        self.is_leader = data.get('is_leader', 0) == 1
        self.can_invite = data.get('can_invite', 0) == 1

    def fetch_role_data(self):
        if not self.data_manager.check('GROUP_ROLES', f'id = "{self.id}"'):
            return {}
        else:
            return self.data_manager.select_dict('GROUP_ROLES',filter=f'id = "{self.id}"')[0]

    def __repr__(self):
        return f'GroupRole.{self.id}'


class Group:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_group_data()
        self.label = data.get('label', None)
        self.owner_id = data.get('owner_id', None)

    def fetch_group_data(self):
        if not self.data_manager.check('GROUP_INIT', f'id = {self.id}'):
            return {}
        else:
            return self.data_manager.select_dict('GROUP_INIT', filter=f'id = {self.id}')[0]

    def fetch_group_members(self):
        if not self.data_manager.check('GROUP_CHARS', f'group_id = {self.id}'):
            return []
        else:
            return self.data_manager.select_dict('GROUP_CHARS', filter=f'group_id = {self.id}')

    def group_roles_members(self):
        total_roles = {}
        c_chars = self.fetch_group_members()

        for char in c_chars:
            if char.get('role', None) in c_chars:
                total_roles[char.get('role')] = [char.get('id')]
            else:
                total_roles[char.get('role')].append(char.get('id'))

        return total_roles