# -*- coding: utf-8 -*-
from ArbDatabase import DataManager, DataModel


class GroupRole(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'GROUP_ROLES', f'id = "{self.id}"')

        self.label = self.get('label', 'Неизвестная роль')
        self.is_leader = self.get('is_leader', 0) == 1
        self.can_invite = self.get('can_invite', 0) == 1

    def __repr__(self):
        return f'GroupRole.{self.id}'


class Group(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'GROUP_INIT', f'id = {self.id}', data_manager=self.data_manager)
        self.label = self.get('label', None)
        self.owner_id = self.get('owner_id', None)

    def add_member(self, character_id:int, role:str=None, custom_role_name:str=None):
        role = role if role else 'Participant'
        if not self.data_manager.check('GROUP_ROLES', f'id = "{role}"'):
            role = 'Participant'

        if not self.data_manager.check('GROUP_CHARS', f'id = {character_id}'):
            self.data_manager.insert('GROUP_CHARS', {'id': character_id, 'group_id': self.id, 'role': role, 'custom_role_name': custom_role_name})
        else:
            self.data_manager.update('GROUP_CHARS', {'group_id': self.id, 'role': role, 'custom_role_name': custom_role_name}, f'id = {character_id}')

    def delete_member(self, character_id:int):
        self.data_manager.delete('GROUP_CHARS', f'id = {character_id} AND group_id = {self.id}')

    def set_member_role(self, character_id:int, role:str):
        if self.data_manager.check('GROUP_CHARS', f'id = {character_id} AND group_id = {self.id}'):
            self.data_manager.update('GROUP_CHARS', {'role': role}, f'id = {character_id} AND group_id = {self.id}')

    def fetch_group_members(self):
        if not self.data_manager.check('GROUP_CHARS', f'group_id = {self.id}'):
            return []
        else:
            return self.data_manager.select_dict('GROUP_CHARS', filter=f'group_id = {self.id}')

    def get_avg_skill(self, skill_id:str):
        from ArbSkills import Skill

        members = [member.get('id') for member in self.fetch_group_members()]
        members_count = len(members)
        skill_sum = 0

        for member in members:
            member_skill = Skill(member, skill_id, data_manager=self.data_manager)
            skill_sum += member_skill.lvl

        return round(skill_sum / members_count, 2)

    def get_min_skill(self, skill_id:str):
        from ArbSkills import Skill

        members = [member.get('id') for member in self.fetch_group_members()]
        min_skill = float('inf')

        for member in members:
            member_skill = Skill(member, skill_id, data_manager=self.data_manager)
            min_skill = min(min_skill, member_skill.lvl)

        return min_skill


    def group_roles_members(self):
        total_roles = {}
        c_chars = self.fetch_group_members()

        for char in c_chars:
            if char.get('role') not in total_roles:
                total_roles[char.get('role')] = []

            total_roles[char.get('role')].append(char.get('id'))

        return total_roles

    def get_member_role(self, character_id:int):
        if character_id == self.owner_id:
            return 'Manager'

        if self.data_manager.check('GROUP_CHARS', f'id = {character_id} AND group_id = {self.id}'):
            return self.data_manager.select_dict('GROUP_CHARS', filter=f'id = {character_id}')[0].get('role')
        else:
            return 'Participant'

    async def send_invite(self, ctx, user_id:int):
        from ArbUIUX import SuccessEmbed, InviteView
        from ArbCharacters import Character
        from ArbCore import Player

        player = Player(user_id, data_manager=self.data_manager)
        author = Player(ctx.author.id, data_manager=self.data_manager)

        p_char = player.current_character
        a_char = author.current_character

        embed = SuccessEmbed(f'Приглашение в отряд {self.label}',
                             f'***{Character(a_char).name}** приглашает **{Character(p_char).name}** присоединиться к отряду **{self.label}**.*\n\n-# ***Вы принимаете приглашение?***',
                             footer=f'{ctx.author.display_name}',
                             footer_logo=ctx.author.avatar)
        embed.set_author(f'{Character(a_char).name}', icon_url=Character(a_char).picture)
        view = InviteView(ctx, accept_label='Принять', deny_label='Отклонить', acceptor=ctx.bot.get_user(user_id))
        await ctx.bot.get_user(user_id).send(embed=embed, view=view)
        result = await ctx.bot.wait_for('interaction')
        return result

    def disband(self):
        self.data_manager.delete('GROUP_INIT', f'id = {self.id}')
        self.data_manager.delete('GROUP_CHARS', f'group_id = {self.id}')

    def text_info(self):
        from ArbOrgs import Rank, Organization
        from ArbCharacters import Character
        from ArbLocations import CharacterLocation

        character = Character(self.owner_id)

        text = f'> ***Управляющий:** {Rank(character.org_lvl).label} {character.name}*\n' \
               f'> ***Организация:** {Organization(character.org).label}*\n' \
               f'> ***Местоположение отряда:** {CharacterLocation(self.owner_id).location.label} ({CharacterLocation(self.owner_id).location.cluster.label})*'

        return text

    def text_members(self):
        from ArbCharacters import Character
        from ArbOrgs import Rank

        roles_members = self.group_roles_members()
        text = ''
        for role, members in roles_members.items():
            for member in members:
                character = Character(member)
                text += f'- ``[{GroupRole(role).label}]`` {Rank(character.org_lvl).label} {character.name}\n'

        return text

    @staticmethod
    def find_group_by_character_id(character_id:int):
        db = DataManager()
        group_chars = db.select_dict('GROUP_CHARS', filter=f'id = {character_id}')
        if group_chars:
            return Group(group_chars[0].get('group_id'), data_manager=db)
        else:
            return None

    @staticmethod
    def find_group_members_of_character(character_id:int):
        group = Group.find_group_by_character_id(character_id)
        if group:
            return group.fetch_group_members()
        else:
            return []

    @staticmethod
    def find_group_members_including(character_id:int):
        group = Group.find_group_by_character_id(character_id)
        if group:
            return [member.get('id') for member in group.fetch_group_members()]
        else:
            return [character_id]

    @staticmethod
    def create(label:str, owner_id:int):
        db = DataManager()
        max_id = db.maxValue('GROUP_INIT', 'id') + 1
        group_id = max_id if max_id else 1

        db.insert('GROUP_INIT', {'id': group_id, 'label': label, 'owner_id': owner_id})
        group = Group(group_id, data_manager=db)
        group.add_member(owner_id, 'Commander', None)
        return group

    @staticmethod
    def get_group_leader_by_character_id(character_id:int):
        group = Group.find_group_by_character_id(character_id)
        if group:
            return group.owner_id
        else:
            return character_id

    def get_group_org(self):
        from ArbCharacters import Character

        if self.owner_id is None:
            return 'Civil'

        character = Character(self.owner_id)
        return character.org

    @staticmethod
    def get_group_org_by_character_id(character_id:int):
        from ArbCharacters import Character
        group = Group.find_group_by_character_id(character_id)
        if group:
            return group.get_group_org()
        else:
            return Character(character_id).org if Character(character_id).org else 'Civil'

    @staticmethod
    def can_group_skip_cycles(character_id:int):
        from ArbCharacters import Character
        from ArbLocations import CharacterLocation
        from ArbOrgs import Organization

        group_members = Group.find_group_members_including(character_id)
        group = Group.find_group_by_character_id(character_id)

        members = [member for member in group_members]
        current_location = CharacterLocation(group.owner_id if group else character_id)

        if current_location and current_location.entered_location:
            group_org = Organization(Group.get_group_org_by_character_id(character_id))
            location_org = current_location.location.get_owner().id
            if group_org.relation_to_org(location_org).in_war:
                return 0

            min_cycles = float('inf')
            for member in members:
                member_cycles = Character(member).get_last_update_difference()
                if member_cycles < min_cycles:
                    min_cycles = member_cycles
            return min_cycles

        from ArbItems import Inventory

        min_cycles = float('inf')
        for member in members:
            member_can_sleep = Inventory.get_inventory_by_character(member).find_component_in_items('SkipCycle')
            if not member_can_sleep:
                return 0
            member_cycles = Character(member).get_last_update_difference()
            if min(member_cycles, 3) < min_cycles:
                min_cycles = member_cycles

        return min_cycles
