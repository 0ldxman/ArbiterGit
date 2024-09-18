import random

from ArbDatabase import DataManager, DataModel, DataDict
from dataclasses import dataclass
from ArbUtils.ArbNums import specnum
import heapq
import pprint
import matplotlib.pyplot as plt
from collections import defaultdict
from ArbGenerator import GenerateBattle
from ArbUtils.ArbTimedate import TimeManager
from ArbUtils.ArbDataParser import process_string
import networkx as nx


# class GraphBuilder:
#     def __init__(self, data_manager, start_location:str):
#         self.data_manager = data_manager
#         self.graph = defaultdict(list)
#         self.build_graph(start_location)
#
#     def build_graph(self, location_id):
#         self._build_graph_recursive(location_id, set())  # Авамер
#
#     def _build_graph_recursive(self, location_id, visited):
#         visited.add(location_id)
#
#         trails = Location(location_id, data_manager=self.data_manager).fetch_trails()
#
#         if location_id not in self.graph:
#             self.graph[location_id] = []
#
#         for trail in trails:
#             t_loc = trail.end_loc_id if trail.end_loc_id != location_id else trail.start_loc_id
#
#             if t_loc not in self.graph[location_id]:
#                 self.add_edge(location_id, t_loc, trail.movement_cost)
#                 if t_loc not in visited:  # Проверяем, что мы не посещали эту локацию ранее
#                     self._build_graph_recursive(t_loc, visited)
#
#     def add_edge(self, start_loc_id, end_loc_id, movement_cost):
#         self.graph[start_loc_id].append((end_loc_id, movement_cost))
#
#     def vizualize_graph(self):
#         G = nx.Graph()
#
#         for node in self.graph.keys():
#             G.add_node(node)
#
#             for edge in self.graph[node]:
#                 linked_node = edge[0]
#                 distance = edge[1]
#                 if linked_node not in G.nodes:
#                     G.add_node(linked_node)
#                 if (node, linked_node, {'weight': distance}) not in G.edges:
#                     G.add_edge(node, linked_node, weight=distance)
#
#         pos = nx.shell_layout(G)
#         nx.draw(G, pos, with_labels=True, node_color='skyblue', font_weight='bold', node_size=1500)
#
#         plt.show()
#
#     def get_graph(self):
#         return dict(self.graph)
#
#
# class ShortestPathFinder:
#     def __init__(self, start_location:str, end_location:str, **kwargs):
#         self.data_manager = kwargs.get('data_manager', DataManager())
#         self.graph = GraphBuilder(self.data_manager, start_location).graph
#         self.start_loc = start_location
#         self.end_loc = end_location
#
#     def find_shortest_path(self):
#         pq = [(0, self.start_loc, [])]
#         visited = set()
#
#         while pq:
#             (cost, node, path) = heapq.heappop(pq)
#
#             if node not in visited:
#                 path = path + [node]
#                 visited.add(node)
#
#                 if node == self.end_loc:
#                     return cost, path
#
#                 for neighbor, edge_cost in self.graph.get(node, []):
#                     if neighbor not in visited:
#                         heapq.heappush(pq, (cost + edge_cost, neighbor, path))
#
#         return float('inf'), []  # Если путь не найден
#
#     def find_shortest_path_with_trails(self):
#         cost, path = self.find_shortest_path()
#
#         path_with_trails = []
#         for i in range(len(path) - 1):
#             #edge = (path[i], path[i + 1])
#             trail = Trail.get_trail_for_edge(path[i], path[i + 1], data_manager=self.data_manager)
#             if trail:
#                 path_with_trails.append(trail)
#
#         return cost, path_with_trails


class LocationObjectType(DataModel):
    def __init__(self, id:str, **kwargs):
        self.type_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'LOC_OBJECTS_INIT', f'id = "{self.type_id}"', data_manager=self.data_manager)

        self.label = self.get('label') if self.get('label') else 'Неизвестный объект'
        self.type = self.get('type') if self.get('type') else None
        self.value = self.get('value') if self.get('value') else None
        self.difficulty = self.get('difficulty') if self.get('difficulty') else 0

    def __repr__(self):
        return f'Object.{self.type_id}({self.type})'


class LocationObject(LocationObjectType):
    def __init__(self, id:int, **kwargs):
        self.object_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.object_type = data.get('type') if data.get('type') else 'Cache'

        super().__init__(self.object_type, data_manager=self.data_manager)
        self.location = data.get('id') if data.get('id') else None
        self.label = data.get('label') if data.get('label') else self.label

    def fetch_data(self):
        if self.data_manager.check('LOC_OBJECTS',filter=f'object_id = {self.object_id}'):
            return self.data_manager.select_dict('LOC_OBJECTS', filter=f'object_id = {self.object_id}')[0]
        else:
            return {}

    def delete_object(self):
        self.data_manager.delete('LOC_OBJECTS', filter=f'object_id = {self.object_id}')

    def get_location(self):
        if self.location:
            return Location(self.location, data_manager=self.data_manager)
        else:
            return None


class LocationType(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'LOC_TYPE', key_filter=f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label') if self.get('label') else 'Неизвестный тип локации'
        self.rest = self.get('rest') if self.get('rest') else None
        self.medicine = self.get('medicine') if self.get('medicine') else None
        self.terrain = self.get('terrain') if self.get('terrain') else None
        self.terrain_category = process_string(self.get('terrain_category')) if self.get('terrain_category', None) else None
        self.min_layers = self.get('min_layers') if self.get('min_layers') else 1
        self.max_layers = self.get('max_layers') if self.get('max_layers') else 1
        self.min_distance = self.get('min_distance') if self.get('min_distance') else 20
        self.max_distance = self.get('max_distance') if self.get('max_distance') else 100

        self.patrol = self.get('patrol') if self.get('patrol') else None
        self.trader = self.get('trader') if self.get('trader') else None
        self.intendant = self.get('intendant') if self.get('intendant') else None
        self.healer = self.get('healer') if self.get('healer') else None

        self.is_covered = bool(self.get('is_covered')) if self.get('is_covered') else False

    def fetch_type_objects(self):
        total_objects = []
        if self.patrol:
            total_objects.append(LocationObjectType(self.patrol, data_manager=self.data_manager))
        if self.trader:
            total_objects.append(LocationObjectType(self.trader, data_manager=self.data_manager))
        if self.intendant:
            total_objects.append(LocationObjectType(self.intendant, data_manager=self.data_manager))
        if self.healer:
            total_objects.append(LocationObjectType(self.healer, data_manager=self.data_manager))

        return total_objects

    def __repr__(self):
        return f'LocationType.{self.id}'


class Location(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'LOC_INIT', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label') if self.get('label') else 'Неизвестное место'
        self.type = LocationType(self.get('type'), data_manager=self.data_manager) if self.get('type') else None
        self.cluster = Cluster(self.get('region'), data_manager=self.data_manager) if self.get('region') else None
        self.owner = self.get('owner') if self.get('owner') else None
        self.cost = int(self.get('cost')) if self.get('cost') else 0
        print(self.__dict__)
        self.picture = self.get('picture') if self.get('picture') else self.cluster.picture

        self.current_battle = self.get('current_battle') if self.get('current_battle') else None
        self.is_covered = bool(self.get('is_covered')) if self.get('is_covered') is not None else self.type.is_covered

    def delete_location(self):
        self.data_manager.delete('LOC_INIT', filter=f'id = "{self.id}"')
        self.data_manager.delete('LOC_CONNECTIONS', filter=f'loc_id = "{self.id}"')
        self.data_manager.delete('LOC_CONNECTIONS', filter=f'con_id = "{self.id}"')
        self.data_manager.delete('LOC_OBJECTS', filter=f'id = "{self.id}"')

    def get_owner(self):
        from ArbOrgs import Organization

        if self.owner:
            return Organization(self.owner, data_manager=self.data_manager)
        else:
            return None

    def is_location_viewed(self, character_id:int):
        if not self.is_covered:
            return True

        from ArbOrgs import Organization

        owner_org = self.get_owner()
        if not owner_org:
            owner_org = Organization('Civil', data_manager=self.data_manager)

        org_relation_to_character = owner_org.relation_to_character(character_id)
        if org_relation_to_character >= 60:
            return True
        else:
            return False





    def get_connections(self):
        if self.data_manager.check('LOC_CONNECTIONS',filter=f'(loc_id = "{self.id}" OR con_id = "{self.id}") AND available = 1'):
            return self.data_manager.select_dict('LOC_CONNECTIONS', filter=f'(loc_id = "{self.id}" OR con_id = "{self.id}") AND available = 1')
        else:
            return []

    def add_connection(self, loc_id:str, is_available:bool=True, transports:list[str] = None):
        if self.data_manager.check('LOC_CONNECTIONS', f'loc_id = "{self.id}" AND con_id = "{loc_id}"') or self.data_manager.check('LOC_CONNECTIONS', f'loc_id = "{loc_id}" AND con_id = "{self.id}"'):
            return

        query = {
            'loc_id': self.id,
            'con_id': loc_id,
            'available': int(is_available),
            'transport': ', '.join(transports) if transports else None
        }
        self.data_manager.insert('LOC_CONNECTIONS', query)

    def delete_connection(self, loc_id:str):
        self.data_manager.delete('LOC_CONNECTIONS', filter=f'(loc_id = "{self.id}" AND con_id = "{loc_id}") OR (loc_id = "{loc_id}" AND con_id = "{self.id}")')

    def process_connections(self):
        total_connections = self.get_connections()
        connections = []
        for connection in total_connections:
            if connection.get('loc_id') == self.id:
                connections.append(connection.get('con_id'))
            else:
                connections.append(connection.get('loc_id'))

        connections = list(set(connections))

        connected_locations = [LocationConnection(con, Location(con, data_manager=self.data_manager).cost) for con in connections]

        return connected_locations

    def minimal_cost_connections(self):
        connections = self.process_connections()
        connections = sorted(connections, key=lambda x: x.cost)
        return connections

    def vizualize_connections(self):
        connections = self.process_connections()
        G = nx.Graph()
        for node in connections:
            G.add_node(node.loc_id)
            G.add_edge(self.id, node.loc_id, weight=node.cost)

        nx.draw_spring(G, with_labels=True, node_size=100, node_color='skyblue', edge_color='grey', font_size=12, font_color='black')
        plt.show()
        return connections

    def get_objects(self):
        total_objects = {}
        type_objects = self.type.fetch_type_objects()
        for obj in type_objects:
            # pprint.pprint(obj.__dict__)
            if obj.type not in total_objects:
                total_objects[obj.type] = [obj]
            else:
                total_objects[obj.type].append(obj)

        location_objects = [LocationObject(obj.get('object_id'), data_manager=self.data_manager) for obj in self.data_manager.select_dict('LOC_OBJECTS', filter=f'id = "{self.id}"')]
        for obj in location_objects:
            # pprint.pprint(obj.__dict__)
            if obj.type not in total_objects:
                total_objects[obj.type] = [obj]
            else:
                total_objects[obj.type].append(obj)

        return total_objects

    def add_object(self, type_id:str, label:str=None):
        object_id = self.data_manager.maxValue('LOC_OBJECTS', 'object_id') + 1
        query = {
            'id': self.id,
            'type': type_id,
            'label': label,
            'object_id': object_id
        }
        self.data_manager.insert('LOC_OBJECTS', query)

        return LocationObject(object_id)

    def delete_object(self, object_id:int):
        self.data_manager.delete('LOC_OBJECTS', filter=f'id = "{self.id}" AND object_id = {object_id}')

    def set_current_battle(self, battle_id:int):
        self.current_battle = battle_id
        self.data_manager.update('LOC_INIT', {'current_battle': battle_id}, f'id = "{self.id}"')

    def start_battle(self):
        total_patrols = self.get_objects().get('Противник', None)
        if not total_patrols:
            return None

        new_battle = GenerateBattle(data_manager=self.data_manager,
                                    layer_value = random.randint(self.type.min_layers, self.type.max_layers),
                                    distance_delta = random.randint(self.type.min_distance, self.type.max_distance),
                                    weather = self.cluster.weather,
                                    time = self.cluster.time,
                                    label=f'{self.type.label} {self.label} сражение',
                                    available_types=self.type.terrain_category,
                                    terrain=self.type.terrain,
                                    onlu_one_type=True if not self.type.terrain_category else False)

        pprint.pprint(new_battle.__dict__)

    def __repr__(self):
        return f'Location.{self.type.id}.{self.id}'

    @classmethod
    def create_location(cls, location_id:str, label:str, type:str, region:str, owner:str, cost:int=2, current_battle_id:int=None, picture:str=None, is_covered:bool=False):
        query = {
            'id': location_id,
            'label': label,
            'type': type,
            'region': region,
            'owner': owner,
            'cost': cost,
            'current_battle': current_battle_id,
            'picture': picture,
            'is_covered': is_covered
        }
        DataManager().insert('LOC_INIT', query)
        return cls(location_id)

    def location_update(self,
                        label:str=None,
                        type:str=None,
                        region:str=None,
                        owner:str=None,
                        cost:int=None,
                        current_battle_id:int=None,
                        picture:str=None,
                        is_covered:bool=None):

        self.label = label if label else self.label
        self.type = LocationType(type, data_manager=self.data_manager) if type else self.type
        self.cluster = Cluster(region, data_manager=self.data_manager) if region else self.cluster
        self.owner = owner if owner else self.owner
        self.cost = cost if cost is not None else self.cost
        self.current_battle = current_battle_id if current_battle_id is not None else self.current_battle
        self.picture = picture if picture else self.picture
        self.is_covered = is_covered if is_covered is not None else self.is_covered

        query = {
            'label': self.label,
            'type': self.type.id,
            'region': self.cluster.id,
            'owner': self.owner,
            'cost': self.cost,
            'current_battle': self.current_battle,
            'picture': self.picture,
            'is_covered': is_covered if is_covered is not None else self.get("is_covered", None)
        }

        self.data_manager.update('LOC_INIT', query, filter=f'id = "{self.id}"')


class Cluster(DataModel):
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        DataModel.__init__(self, 'LOC_CLUSTER', f'id = "{self.id}"', data_manager=self.data_manager)

        self.label = self.get('label', 'Неизвестный регион') if self.get('label') else 'Неизвестный регион'
        self.type = self.get('type', 'Квестовый') if self.get('type') else None
        self.picture = self.get('picture', '') if self.get('picture') else ''
        self.weather = self.get('weather', 'Sunny') if self.get('weather') else 'Sunny'
        self.time = self.get('time', 'Day') if self.get('time') else TimeManager().get_current_time_condition()
        self.move_desc = self.get('move_desc', 'Вы переместились на локацию') if self.get('move_desc') else 'Вы перестились на локацию'
        self.map = self.get('map', '') if self.get('map') else ''

    def fetch_locations(self):
        if self.data_manager.check('LOC_INIT',filter=f'region = "{self.id}"'):
            return self.data_manager.select_dict('LOC_INIT', filter=f'region = "{self.id}"')
        else:
            return []

    def get_locations(self):
        locations = self.fetch_locations()
        return [Location(location.get('id'), data_manager=self.data_manager) for location in locations]

    def graph_locations(self):
        locations = self.fetch_locations()
        graph = {}
        for location in locations:
            graph[location.get('id')] = Location(location.get('id'), data_manager=self.data_manager).process_connections()

        return graph

    def visualize_graph_locations(self):
        graph = self.graph_locations()

        G = nx.Graph()
        for node in graph:
            node_label = Location(node, data_manager=self.data_manager).label
            G.add_node(Location(node, data_manager=self.data_manager).label)
            for edge in graph[node]:
                linked_node = Location(edge.loc_id, data_manager=self.data_manager).label

                distance = edge.cost
                if linked_node not in G.nodes:
                    G.add_node(linked_node)
                if (node, linked_node, {'weight': distance}) not in G.edges:
                    G.add_edge(node_label, linked_node, weight=distance)

        nx.draw_networkx(G, with_labels=True, node_color='skyblue', edge_color='Grey', node_size=50, font_size=7)

        plt.show()

    def delete_region(self):
        self.data_manager.delete('LOC_CLUSTER', filter=f'id = "{self.id}"')
        total_locations = self.fetch_locations()
        print(total_locations)
        for i in total_locations:
            self.data_manager.delete('LOC_CONNECTIONS', filter=f'(loc_id = "{i.get("id")}" OR con_id = "{i.get("id")}")')
        self.data_manager.delete('LOC_INIT', filter=f'region = "{self.id}"')

    def __repr__(self):
        return f'Cluster.{self.id}'

    @classmethod
    def create_cluster(cls, cluster_id:str, label:str, type:str, picture:str=None, weather:str='Sunny', time:str=None, move_desc:str='Вы переместились на локацию', map:str=None):
        query = {
            'id': cluster_id,
            'label': label,
            'type': type,
            'picture': picture,
            'weather': weather,
            'time': time,
           'move_desc': move_desc,
            'map': map
        }
        DataManager().insert('LOC_CLUSTER', query)
        return cls(cluster_id)


@dataclass()
class LocationConnection:
    loc_id: str | None
    cost: int | None


class CharacterLocation(DataModel):
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.insert_data_if_not_exists()

        DataModel.__init__(self, f'CHARS_LOC', f'id = {self.id}', data_manager=self.data_manager)

        self.location = Location(self.get('loc_id'), data_manager=self.data_manager) if self.get('loc_id') else None
        self.movement_points = self.get('move_points') if self.get('move_points') else 0
        self.entered_location = self.get('entered') == 1 if self.get('entered') else False

    def get_all_viewed_locations(self):
        all_locations = self.graph_all_locations()
        filtered_locations = [loc for loc in all_locations if Location(loc).is_location_viewed(self.id)]
        get_dislocation_connections = [loc.loc_id for loc in self.location.process_connections()]
        get_connections_connections = []
        for loc in get_dislocation_connections:
            for con in Location(loc).process_connections():
                get_connections_connections.append(con.loc_id)

        total_locs = filtered_locations + get_dislocation_connections + get_connections_connections
        total_locs = list(set(total_locs))
        return [Location(loc) for loc in total_locs]

    def graph_all_locations(self):
        locations = self.data_manager.select_dict('LOC_INIT')
        graph = {}
        for location in locations:
            graph[location.get('id')] = Location(location.get('id'),
                                                 data_manager=self.data_manager).process_connections()

        return graph

    def create_graph(self):
        graph = self.graph_all_locations()

        G = nx.Graph()
        for node in graph:
            node_label = Location(node, data_manager=self.data_manager).id
            G.add_node(Location(node, data_manager=self.data_manager).id)
            for edge in graph[node]:
                linked_node = Location(edge.loc_id, data_manager=self.data_manager).id

                distance = edge.cost
                if linked_node not in G.nodes:
                    G.add_node(linked_node)
                if (node, linked_node, {'weight': distance}) not in G.edges:
                    G.add_edge(node_label, linked_node, weight=distance)

        return G

    def find_shortest_path(self, loc_id:str):
        graph = self.create_graph()
        source = self.location.id
        target = Location(loc_id, data_manager=self.data_manager).id

        try:
            return nx.shortest_path(graph, source=source, target=target, weight='weight')
        except nx.NetworkXNoPath:
            return []

    def get_healing_rate(self):
        location_objects = self.location.get_objects()
        total_healing_rate = 0
        for obj in location_objects.get('Медицина', []):
            print(obj)
            print(obj.difficulty, obj.type, obj.value, obj.value == 'Интендант')
            total_healing_rate = max(total_healing_rate, obj.difficulty * 40) if obj.value == 'Интендант' else total_healing_rate

        print(total_healing_rate)

        return total_healing_rate

    def traders_assort(self):
        from ArbVendors import VendorObject

        location_objects = self.location.get_objects()
        traders = [VendorObject(trader.type_id, data_manager=self.data_manager) for trader in location_objects.get('Торговец', [])]
        total_assort = {}
        for trader in traders:
            trader_assort = trader.get_price()
            for item in trader_assort:
                if item not in total_assort:
                    total_assort[item] = trader_assort[item]
                else:
                    total_assort[item] = min(trader_assort.get(item), total_assort.get(item))

        return total_assort

    def set_location(self, location_id:str, is_entered:bool = False):
        self.insert_data_if_not_exists()
        self.data_manager.update('CHARS_LOC', {'loc_id': location_id, 'entered': int(is_entered)}, filter=f'id = {self.id}')
        self.location = Location(location_id, data_manager=self.data_manager)
        self.entered_location = is_entered

    def insert_data_if_not_exists(self):
        if not self.data_manager.check('CHARS_LOC',filter=f'id = {self.id}'):
            prompt = {'id': self.id,
                      'loc_id': None,
                      'move_points': 0}
            self.data_manager.insert('CHARS_LOC', prompt)

    def get_available_locations(self):
        available_locations = self.location.process_connections()

        return available_locations

    def get_available_by_cost_locations(self):
        locations = self.get_available_locations()
        total_locations = {}
        for i in locations:
            print(i.cost, self.movement_points)
            if i.cost <= self.movement_points:
                total_locations[i.loc_id] = i.cost

        return total_locations

    def use_movement_points(self, cost:int):
        self.movement_points = self.movement_points - cost
        self.data_manager.update('CHARS_LOC', {'move_points': self.movement_points}, filter=f'id = {self.id}')

    def get_character_group(self):
        from ArbCharacters import Character
        character_group = Character(self.id, data_manager=self.data_manager).get_group()
        return character_group

    def character_org(self):
        from ArbCharacters import Character

        character = Character(self.id, data_manager=self.data_manager)
        return character.check_organization()

    def set_group_location(self, location_id:str, is_entered:bool=False):
        from ArbGroups import Group
        group_members = Group.find_group_members_including(self.id)
        for member in group_members:
            char_loc = CharacterLocation(member, data_manager=self.data_manager)
            char_loc.set_location(location_id, is_entered)

    def check_if_enemy_location(self):
        character_org = self.character_org()
        location_owner = self.location.get_owner()

        relation_to_character = location_owner.relation_to_org(character_org)

        if relation_to_character.in_war:
            return True
        elif relation_to_character.relation <= -50:
            return True
        elif relation_to_character.is_ally:
            return False
        else:
            return False

    def get_patrols_on_location(self):
        is_enemy_location = self.check_if_enemy_location()
        if not is_enemy_location:
            return []

        patrols = self.location.get_objects().get('Противник', [])
        return patrols

    def patrol_contact_check(self):
        patrols = self.get_patrols_on_location()
        if not patrols:
            return None

        my_group = self.get_character_group()
        if my_group:
            avg_skill = my_group.get_avg_skill('Stealth')
        else:
            from ArbSkills import Skill
            avg_skill = Skill(self.id, 'Stealth', data_manager=self.data_manager).lvl

        for patrol in patrols:
            detect_chance = patrol.value * patrol.difficulty * 2
            if detect_chance >= random.randint(-50, 50) + avg_skill:
                return patrol
        else:
            return None

    def start_battle(self, patrol: LocationObjectType) -> 'Battlefield':
        from ArbGenerator import GenerateBattle, GenerateTeam
        from ArbBattle import Battlefield

        size = random.randint(self.location.type.min_layers, self.location.type.max_layers)
        distance = round(random.randint(self.location.type.min_distance, self.location.type.max_distance), -1)
        daytime = self.location.cluster.time
        weather = self.location.cluster.weather
        terrain_type = self.location.type.terrain if self.location.type.terrain else None
        terrain_category = self.location.type.terrain_category if self.location.type.terrain_category else []
        print(terrain_type, terrain_category)

        new_battle = GenerateBattle(distance_delta=distance,
                                    num_of_layers=size,
                                    time=daytime,
                                    weather=weather,
                                    data_manager=self.data_manager,
                                    label=f'Контакт близ {self.location.label}',
                                    terrain_types=[terrain_type] if terrain_type else None,
                                    terrain_categories=terrain_category)

        battle_id = new_battle.id
        battlefield = Battlefield(battle_id)
        new_battle.insert_data()

        enemy_team = GenerateTeam(battle_id, label=f'Патруль {self.location.label}',
                                  role='Ambushers',
                                  members_value=patrol.value,
                                  danger=patrol.difficulty,
                                  generate_commander=True,
                                  members_org=self.location.owner,
                                  members_activity=None,
                                  round_active=1,
                                  members_layer=random.randint(0, size))
        enemy_team.insert_data()

        character_group = self.get_character_group()
        if character_group:
            characters = character_group.fetch_group_members()
            team_label = character_group.label
        else:
            characters = [self.id]
            team_label = 'Попаданцы'

        characters_team = battlefield.create_team(team_label, role='Defenders')
        for character in characters:
            print(character)
            battlefield.add_actor(character.get('id'), team_id=characters_team.id)

        return battlefield

    def move_to_location(self, location_id:str):
        locations_with_cost = self.get_available_by_cost_locations()
        patrol_check = self.patrol_contact_check()
        if patrol_check:
            self.use_movement_points(locations_with_cost[location_id])
            self.leave_location()
            self.set_group_location(location_id)
            return patrol_check

        # if location_id not in locations_with_cost:
        #     return None
        #
        # if locations_with_cost[location_id] > self.movement_points:
        #     return False

        self.use_movement_points(locations_with_cost[location_id])
        self.leave_location()
        self.set_group_location(location_id)

        return None

    def describe_location(self) -> str:
        from ArbOrgs import Organization
        total_text = f'> ***Название:** {self.location.label}*' \
                     f'\n> ***Регион:** {self.location.cluster.label}*' \
                     f'\n> ***Владелец:** {Organization(self.location.owner, data_manager=self.data_manager).label} ({Organization(self.location.owner, data_manager=self.data_manager).type})*\n\n### *На локации вы видите:*\n'
        total_objects = self.location.get_objects()

        for obj_type in total_objects:
            type_desc = f''
            for obj in total_objects[obj_type]:
                type_desc += f'*- ({obj_type}) {obj.label}*\n'

            total_text += type_desc

        return total_text

    def describe_connections(self):
        connections = self.location.process_connections()
        total_connections = ''
        for connection in connections:
            total_connections += f'- ***{Location(connection.loc_id, data_manager=self.data_manager).label} ({Location(connection.loc_id, data_manager=self.data_manager).type.label}):** {connection.cost} очков путешествия*\n'

        return total_connections

    def enter_location(self):
        patrol_check = self.patrol_contact_check()
        if patrol_check:
            self.set_group_location(self.location.id, True)
            return patrol_check

        self.set_group_location(self.location.id, True)
        return None

    def leave_location(self):
        self.entered_location = False
        self.set_group_location(self.location.id, False)
