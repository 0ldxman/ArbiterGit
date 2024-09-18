import pprint
import random

from ArbDatabase import DataManager, DataModel, DataDict
from dataclasses import dataclass


class Rank(DataModel):
    def __init__(self, rank_id:str, **kwargs):
        self.rank_id = rank_id
        self.data_manager = kwargs.get('data_manager', DataManager())

        super().__init__('ORG_RANKS', f'id = "{self.rank_id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный ранг')
        self.desc = self.get('desc', 'Нет описания ранга')
        self.power_rank = self.get('lvl', 0)
        self.is_leader = self.get('is_leader', False) == 1
        self.can_invite = self.get('can_invite', False) == 1
        self.can_promote = self.get('can_promote', False) == 1
        self.can_group = self.get('can_group', False) == 1
        self.salary = self.get('salary', 0) if self.get('salary') else 0


class Organization(DataModel):
    def __init__(self, id:str, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        DataModel.__init__(self, 'ORG_INIT', f'id = "{self.id}"')

        self.label = self.get('label', 'Неизвестная организация')
        self.type = self.get('type', 'Неизвестный тип')
        self.parent_org = self.get('parent', None)
        if self.parent_org is not None:
            self.type = f'{self.type} {self.get_parent().label}'

        self.money = self.get('money', 0) if self.get('money') else 0
        self.tech_tier = self.get('tech_tier', 1)
        self.basic_power = self.get('power', 100)
        self.military = self.get('military', 100)
        self.economy = self.get('economy', 100)
        self.mood = self.get('mood', 100)
        self.picture = self.get('picture', None)
        if not self.picture and self.parent_org:
            self.picture = self.get_parent().picture

        self.spawn_point = self.get('spawn_location', None) if self.get('spawn_location') else None
        if not self.spawn_point and self.parent_org:
            self.spawn_point = self.get_parent().spawn_point

    def get_all_characters(self):
        if self.data_manager.check('CHARS_INIT', filter=f'org = "{self.id}"'):
            return [char.get('id') for char in self.data_manager.select_dict('CHARS_INIT', filter=f'org = "{self.id}"')]
        else:
            return []

    def get_included_members(self):
        children_orgs = self.get_children()
        characters = self.get_all_characters()
        for org in children_orgs:
            characters.extend(Organization(org, data_manager=self.data_manager).get_all_characters())

        return characters

    def sort_characters_by_rank(self):
        from ArbCharacters import Character
        characters = self.get_all_characters()
        sorted_characters = {}
        for char_id in characters:
            rank_id = Character(char_id).org_lvl
            rank = Rank(rank_id, data_manager=self.data_manager)
            if rank.rank_id not in sorted_characters:
                sorted_characters[rank.rank_id] = []
            sorted_characters[rank.rank_id].append(char_id)

        return sorted_characters

    def update_budget(self, amount:float):
        self.money += amount
        self.update_record({'money': self.money})

    def payday(self, part:int=100):
        from ArbCharacters import Character

        sorted_characters = self.sort_characters_by_rank()
        payed_characters = []
        for rank_id in sorted_characters.keys():
            rank = Rank(rank_id, data_manager=self.data_manager)
            total_salary = round(rank.salary * (part / 100), 2)
            for character_id in sorted_characters.get(rank_id):
                if self.money - total_salary < 0:
                    break
                character = Character(character_id, data_manager=self.data_manager)
                self.update_budget(-1*total_salary)
                character.add_money(total_salary)
                payed_characters.append(character_id)

        return payed_characters

    def get_all_leaders(self):
        ranks = [Rank(rank, data_manager=self.data_manager) for rank in self.get_inherited_ranks()]
        leader_ranks = [rank.rank_id for rank in ranks if rank.is_leader]
        characters = self.sort_characters_by_rank()

        leaders = []

        for rank in leader_ranks:
            if rank in characters:
                leaders.extend(characters.get('rank', []))

        return leaders

    def get_parent(self) -> 'Organization':
        if self.parent_org:
            return Organization(self.parent_org, data_manager=self.data_manager)
        else:
            return None

    def get_total_power(self):
        total_power = self.basic_power * (self.military/100) * (self.economy/100) * (self.mood/100)
        return total_power

    def fetch_org_ranks(self):
        if self.data_manager.check('ORG_RANKS', f'org = "{self.id}"'):
            return [rank.get('id') for rank in self.data_manager.select_dict('ORG_RANKS', filter=f'org = "{self.id}"')]
        else:
            return []

    def get_inherited_ranks(self):
        ranks = self.fetch_org_ranks()
        if self.parent_org:
            parent_organization = Organization(self.parent_org, data_manager=self.data_manager)
            parent_ranks = parent_organization.get_inherited_ranks()
            ranks.extend(parent_ranks)
        return ranks

    def get_ranks_dict(self):
        ranks = self.get_inherited_ranks()
        ranks_dict = {}
        for rank in ranks:
            rank_obj = Rank(rank, data_manager=self.data_manager)
            if rank_obj.power_rank not in ranks_dict:
                ranks_dict[rank_obj.power_rank] = []

            ranks_dict[rank_obj.power_rank].append(rank)

        return ranks_dict

    def get_random_lowest_rank(self):
        ranks = self.get_inherited_ranks()
        if not ranks:
            return None
        total_ranks = []

        for rank in ranks:
            if Rank(rank, data_manager=self.data_manager).power_rank == 0:
                total_ranks.append(rank)

        return random.choice(total_ranks)

    def get_lvl_rank(self, level: int):
        ranks = self.get_inherited_ranks()
        total_choices = []
        for rank in ranks:
            if Rank(rank, data_manager=self.data_manager).power_rank == level:
                total_choices.append(rank)

        if total_choices:
            return random.choice(total_choices)
        else:
            return self.get_random_lowest_rank()

    def text_org_info(self):
        total_text = f'> ***Тип организации:** {self.type}*\n' \
                     f'> ***Технологический уровень:** {self.tech_tier} тир*\n'

        return total_text

    def text_org_members(self):
        from ArbCharacters import Character

        sorted_characters = self.sort_characters_by_rank()
        min_rank = self.get_random_lowest_rank()
        total_text = []
        for rank_id, characters in sorted_characters.items():
            rank = Rank(rank_id, data_manager=self.data_manager) if rank_id else Rank(min_rank, data_manager=self.data_manager)
            for char in characters:
                total_text.append(f'- *{rank.label} **{Character(char).name}*** ||ID: {char}||\n')

        return total_text

    def character_invited(self, character_id:int):
        lowest_rank = self.get_random_lowest_rank()
        print(lowest_rank)
        self.data_manager.update('CHARS_INIT', {'org': self.id, 'org_lvl': lowest_rank}, f'id = {character_id}')

    async def send_invite(self, ctx, user_id:int):
        from ArbUIUX import SuccessEmbed, InviteView
        from ArbCharacters import Character
        from ArbCore import Player

        player = Player(user_id, data_manager=self.data_manager)
        author = Player(ctx.author.id, data_manager=self.data_manager)

        p_char = player.current_character
        a_char = author.current_character

        embed = SuccessEmbed(f'Приглашение в организацию {self.label}',
                             f'***{Character(a_char).name}** приглашает **{Character(p_char).name}** вступить в организацию **{self.label}**.*\n\n-# ***Вы принимаете приглашение?***',
                             footer=f'{ctx.author.display_name}',
                             footer_logo=ctx.author.avatar)
        embed.set_author(f'{Character(a_char).name}', icon_url=Character(a_char).picture)
        view = InviteView(ctx, accept_label='Принять', deny_label='Отклонить', acceptor=ctx.bot.get_user(user_id))
        await ctx.bot.get_user(user_id).send(embed=embed, view=view)
        result = await ctx.bot.wait_for('interaction')
        return result

    def insert_reputation_if_not_exist(self, character_id:int, rep:int=0, loyalty:int=0):
        if not self.data_manager.check('CHARS_REPUTATION', filter=f'id = {character_id} AND org = "{self.id}"'):
            self.data_manager.insert('CHARS_REPUTATION', {'id': character_id,
                                                      'org': self.id,
                                                      'rep': rep,
                                                      'loyalty': loyalty})

    def get_character_reputation(self, character_id:int):
        self.insert_reputation_if_not_exist(character_id)
        data = self.data_manager.select_dict('CHARS_REPUTATION', filter=f'id = {character_id} AND org = "{self.id}"')[0]
        return data.get('rep', 0)

    def get_character_loyalty(self, character_id:int):
        self.insert_reputation_if_not_exist(character_id)
        data = self.data_manager.select_dict('CHARS_REPUTATION', filter=f'id = {character_id} AND org = "{self.id}"')[0]
        return data.get('loyalty', 0)

    def change_reputation(self, character_id:int, amount:int):
        self.insert_reputation_if_not_exist(character_id)
        current_rep = self.get_character_reputation(character_id)
        new_rep = current_rep + amount
        self.data_manager.update('CHARS_REPUTATION', {'rep': new_rep}, f'id = {character_id} AND org = "{self.id}"')

    def change_loyalty(self, character_id:int, amount:int):
        self.insert_reputation_if_not_exist(character_id)
        current_loyalty = self.get_character_loyalty(character_id)
        new_loyalty = current_loyalty + amount
        self.data_manager.update('CHARS_REPUTATION', {'loyalty': new_loyalty}, f'id = {character_id} AND org = "{self.id}"')

    def relation_to_character(self, character_id:int):
        from ArbCharacters import Character
        char = Character(character_id)
        char_org = char.org
        if char_org == self.id:
            return 100
        else:
            org_relation = self.relation_to_org(char_org)
            if org_relation.in_war:
                return -100
            else:
                return org_relation.relation

    def get_all_parents(self):
        parents = []
        parent = self.get_parent()
        while parent:
            parents.append(parent.id)
            parent = parent.get_parent()
        return parents

    def get_children(self):
        children = []
        for child_id in self.data_manager.select_dict('ORG_INIT', filter=f'parent = "{self.id}"'):
            children.append(child_id.get('id'))
        return children

    def get_all_children(self):
        children = self.get_children()
        passed_children = []
        for child in children:
            passed_children.append(child)
            children.extend(Organization(child).get_children())

        return children

    def get_org_relations(self):
        relations = self.data_manager.select_dict('ORG_RELATIONS', filter=f'id = "{self.id}" OR target = "{self.id}"')
        org_relations = {}
        for relationship in relations:
            rel = OrgRelation(orgs=[relationship.get('id'), relationship.get('target')],
                              relation=relationship.get('relation'),
                              in_war=relationship.get('in_war') == 1,
                              is_ally=relationship.get('is_ally') == 1)

            another_org = [org for org in rel.orgs if org != self.id][0]

            org_relations[another_org] = rel

        children = self.get_all_children()
        for child in children:
            if child not in org_relations:
                org_relations[child] = OrgRelation([self.id, child], 100, False, True)
            else:
                continue

        parents = self.get_all_parents()
        for parent in parents:
            if parent not in org_relations:
                org_relations[parent] = OrgRelation([self.id, parent], 100, False, True)
            else:
                continue

        return org_relations

    def get_total_relations(self):
        total_relations = self.get_org_relations()
        parents = self.get_all_parents()
        enemies = [org for org, rel in self.get_org_relations().items() if rel.in_war]

        for parent in parents:
            parent_org = Organization(parent, data_manager=self.data_manager)
            parent_relations = parent_org.get_org_relations()

            for another_org, rel in parent_relations.items():
                if another_org == self.id:
                    continue

                if another_org not in total_relations:
                    total_relations[another_org] = OrgRelation([self.id, another_org], rel.relation, rel.in_war, rel.is_ally)
                else:
                    total_relations[another_org].relation = int((total_relations[another_org].relation + rel.relation) / 2)
                    total_relations[another_org].in_war = total_relations[another_org].in_war or rel.in_war
                    total_relations[another_org].is_ally = total_relations[another_org].is_ally or rel.is_ally

                if total_relations[another_org].in_war:
                    enemies.append(another_org)

        for enemy in enemies:
            enemy_org = Organization(enemy, data_manager=self.data_manager)
            enemy_relations = enemy_org.get_org_relations()
            parents = enemy_org.get_all_parents()
            children = enemy_org.get_all_children()
            parents_or_children = []
            parents_or_children.extend(parents)
            parents_or_children.extend(children)

            for another_org, rel in enemy_relations.items():
                if another_org == self.id:
                    continue

                is_ally_of_enemy = rel.is_ally
                if another_org in parents_or_children or is_ally_of_enemy:
                    if another_org not in total_relations:
                        total_relations[another_org] = OrgRelation([self.id, another_org], -rel.relation, True, False)
                    else:
                        total_relations[another_org].relation = int((total_relations[another_org].relation - rel.relation) / 2)
                        total_relations[another_org].in_war = True
                        total_relations[another_org].is_ally = False

        return total_relations

    def relation_to_org(self, org_id:str):
        all_relations = self.get_total_relations()
        if org_id in all_relations:
            return all_relations[org_id]
        else:
            return OrgRelation([self.id, org_id], 0, False, False)

    def text_relations(self):
        relations = self.get_total_relations()
        text = ''
        for org_id, rel in relations.items():
            another_org = Organization(org_id, data_manager=self.data_manager)
            if rel.is_ally:
                text += '- *``(Cоюзник)`` '
            elif rel.in_war:
                text += '- *``(ВОЙНА)`` '
            else:
                text += '- *'
            text += f'**{another_org.label}** ({another_org.type})'
            text += f': **{rel.relation}%**'
            text += '*\n\n'

        return text


@dataclass()
class OrgRelation:
    orgs: list[str]
    relation: int
    in_war: bool
    is_ally: bool

    def process_org(self, org_id:str):
        another_org = [org for org in self.orgs if org_id != org]
        return another_org[0]

    def change_org(self, org_id:str, replaced_org:str):
        another_org = self.process_org(replaced_org)
        self.orgs = [another_org, org_id]

    def change_relation(self, new_relation:int):
        self.relation = new_relation