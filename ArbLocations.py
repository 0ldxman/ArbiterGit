import random

from ArbDatabase import DataManager
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


class LocationObjectType:
    def __init__(self, id:str, **kwargs):
        self.type_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_type_data()
        self.label = data.get('label') if data.get('label') else 'Неизвестный объект'
        self.type = data.get('type') if data.get('type') else None
        self.value = data.get('value') if data.get('value') else None
        self.difficulty = data.get('difficulty') if data.get('difficulty') else 0

    def fetch_type_data(self):
        if self.data_manager.check('LOC_OBJECTS_INIT',filter=f'id = "{self.type_id}"'):
            return self.data_manager.select_dict('LOC_OBJECTS_INIT', filter=f'id = "{self.type_id}"')[0]
        else:
            return {}

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



class LocationType:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.label = data.get('label') if data.get('label') else 'Неизвестный тип локации'
        self.rest = data.get('rest') if data.get('rest') else None
        self.medicine = data.get('medicine') if data.get('medicine') else None
        self.terrain = data.get('terrain') if data.get('terrain') else None
        self.terrain_category = process_string(data.get('terrain_category')) if data.get('terrain_category', None) else None
        self.min_layers = data.get('min_layers') if data.get('min_layers') else 1
        self.max_layers = data.get('max_layers') if data.get('max_layers') else 1
        self.min_distance = data.get('min_distance') if data.get('min_distance') else 20
        self.max_distance = data.get('max_distance') if data.get('max_distance') else 100

        self.patrol = data.get('patrol') if data.get('patrol') else None
        self.trader = data.get('trader') if data.get('trader') else None
        self.intendant = data.get('intendant') if data.get('intendant') else None

    def fetch_data(self):
        if self.data_manager.check('LOC_TYPE',filter=f'id = "{self.id}"'):
            return self.data_manager.select_dict('LOC_TYPE', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def fetch_type_objects(self):
        total_objects = []
        if self.patrol:
            total_objects.append(LocationObjectType(self.patrol, data_manager=self.data_manager))
        if self.trader:
            total_objects.append(LocationObjectType(self.trader, data_manager=self.data_manager))
        if self.intendant:
            total_objects.append(LocationObjectType(self.intendant, data_manager=self.data_manager))

        return total_objects

    def __repr__(self):
        return f'LocationType.{self.id}'


class Location:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.label = data.get('label') if data.get('label') else 'Неизвестное место'
        self.type = LocationType(data.get('type'), data_manager=self.data_manager) if data.get('type') else None
        self.cluster = Cluster(data.get('region'), data_manager=self.data_manager) if data.get('region') else None
        self.owner = data.get('owner') if data.get('owner') else None
        self.cost = data.get('cost') if data.get('cost') else 0
        self.picture = data.get('picture') if data.get('picture') else self.cluster.picture

        self.current_battle = data.get('current_battle') if data.get('current_battle') else None

    def fetch_data(self):
        if self.data_manager.check('LOC_INIT',filter=f'id = "{self.id}"'):
            return self.data_manager.select_dict('LOC_INIT', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def get_connections(self):
        if self.data_manager.check('LOC_CONNECTIONS',filter=f'(loc_id = "{self.id}" OR con_id = "{self.id}") AND available = 1'):
            return self.data_manager.select_dict('LOC_CONNECTIONS', filter=f'(loc_id = "{self.id}" OR con_id = "{self.id}") AND available = 1')
        else:
            return []

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

class Cluster:
    def __init__(self, id:str, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестный регион') if data.get('label') else 'Неизвестный регион'
        self.type = data.get('type', 'Квестовый') if data.get('type') else None
        self.picture = data.get('picture', '') if data.get('picture') else ''
        self.weather = data.get('weather', 'Sunny') if data.get('weather') else 'Sunny'
        self.time = data.get('time', 'Day') if data.get('time') else TimeManager().get_current_time_condition()

    def fetch_data(self):
        if self.data_manager.check('LOC_CLUSTER',filter=f'id = "{self.id}"'):
            return self.data_manager.select_dict('LOC_CLUSTER', filter=f'id = "{self.id}"')[0]
        else:
            return {}

    def fetch_locations(self):
        if self.data_manager.check('LOC_INIT',filter=f'region = "{self.id}"'):
            return self.data_manager.select_dict('LOC_INIT', filter=f'region = "{self.id}"')
        else:
            return []

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

@dataclass()
class LocationConnection:
    loc_id: str | None
    cost: int | None


class CharacterLocation:
    def __init__(self, id:int, **kwargs):
        self.id = id
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.insert_data_if_not_exists()
        data = self.fetch_data()
        self.location = Location(data.get('loc_id'), data_manager=self.data_manager) if data.get('loc_id') else None
        self.movement_points = data.get('move_points') if data.get('move_points') else 0
        self.entered_location = data.get('entered') == 1 if data.get('entered') else False

    def insert_data_if_not_exists(self):
        if not self.data_manager.check('CHARS_LOC',filter=f'id = {self.id}'):
            prompt = {'id': self.id,
                      'loc_id': None,
                      'move_points': 0}
            self.data_manager.insert('CHARS_LOC', prompt)

    def fetch_data(self):
        if self.data_manager.check('CHARS_LOC',filter=f'id = {self.id}'):
            return self.data_manager.select_dict('CHARS_LOC', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_available_locations(self):
        available_locations = self.location.process_connections()

        return available_locations

    def get_available_by_cost_locations(self):
        locations = self.get_available_locations()
        total_locations = {}
        for i in locations:
            if i.cost <= self.movement_points:
                total_locations[i.loc_id] = i.cost

        return total_locations

    def use_movement_points(self, cost:int):
        self.movement_points = self.movement_points - cost
        self.data_manager.update('CHARS_LOC', {'move_points': self.movement_points}, filter=f'id = {self.id}')

    def move_to_location(self, location_id:str):
        locations_with_cost = self.get_available_by_cost_locations()

        if location_id not in locations_with_cost:
            return None

        if locations_with_cost[location_id] > self.movement_points:
            return False

        self.use_movement_points(locations_with_cost[location_id])
        self.location = Location(location_id, data_manager=self.data_manager)

        self.data_manager.update('CHARS_LOC', {'loc_id': location_id}, filter=f'id = {self.id}')

        return True