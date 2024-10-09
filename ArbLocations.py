import datetime
import random

from ArbDatabase import DataManager, DataModel, DEFAULT_MANAGER, DataObject, EID
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
from ArbOrgs import Organization
from typing import Union


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


class LocationObjectType(DataObject):
    def __init__(self, id:str, **kwargs):
        self.type_id = id

        DataObject.__init__(self, 'LOC_OBJECTS_INIT', EID(id=self.type_id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный объект')
        self._type = self.field('type', None)
        self._value = self.field('value', None)
        self._difficulty = self.field('difficulty', 0)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def type(self) -> str:
        return self._type.load(self.data_manager)

    @property
    def value(self) -> Union[int, float, str]:
        return self._value.load(self.data_manager)

    @property
    def difficulty(self) -> int:
        return self._difficulty.load(self.data_manager)


    def __repr__(self):
        return f'Object.{self.type_id}({self.type})'


class LocationObject(LocationObjectType):
    def __init__(self, id:int, **kwargs):
        self.object_id = id
        self.data_manager = kwargs.get('data_manager', DEFAULT_MANAGER)
        data = self.fetch_data()
        self.object_type = data.get('type') if data.get('type') else 'Cache'

        super().__init__(self.object_type, data_manager=self.data_manager)
        self.location = data.get('id') if data.get('id') else None
        self.custom_label = data.get('label') if data.get('label') else self.label

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


class LocationType(DataObject):
    def __init__(self, id:str, **kwargs):
        self.id = id

        DataObject.__init__(self, 'LOC_TYPE', EID(id=self.id), data_manager=kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный тип локации')
        self._rest = self.field('rest', 0)
        self._medicine = self.field('medicine', 0)
        self._terrain = self.field('terrain', None)
        self._terrain_category = self.field('terrain_category', None)
        self._min_layers = self.field('min_layers', 1)
        self._max_layers = self.field('max_layers', 1)
        self._min_distance = self.field('min_distance', 20)
        self._max_distance = self.field('max_distance', 100)

        self._patrol = self.field('patrol', None)
        self._trader = self.field('trader', None)
        self._intendant = self.field('intendant', None)
        self._healer = self.field('healer', None)

        self._is_covered = self.field('is_covered', 0)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def rest(self) -> int:
        return self._rest.load(self.data_manager)

    @property
    def medicine(self) -> int:
        return self._medicine.load(self.data_manager)

    @property
    def terrain(self) -> str:
        return self._terrain.load(self.data_manager)

    @property
    def terrain_category(self) -> list[str]:
        terrains = self._terrain_category.load(self.data_manager)
        if terrains:
            return process_string(terrains)

    @property
    def min_layers(self) -> int:
        layers = self._min_layers.load(self.data_manager)
        if layers < 1:
            return 1
        return layers

    @property
    def max_layers(self) -> int:
        layers = self._max_layers.load(self.data_manager)
        if layers < self.min_layers:
            return self.min_layers
        return layers

    @property
    def min_distance(self) -> int:
        distance = self._min_distance.load(self.data_manager)
        if distance < 1:
            return 1
        return distance

    @property
    def max_distance(self) -> int:
        distance = self._max_distance.load(self.data_manager)
        if distance < self.min_distance:
            return self.min_distance
        return distance

    @property
    def patrol(self) -> str:
        return self._patrol.load(self.data_manager)

    @property
    def trader(self) -> str:
        return self._trader.load(self.data_manager)

    @property
    def intendant(self) -> str:
        return self._intendant.load(self.data_manager)

    @property
    def healer(self) -> str:
        return self._healer.load(self.data_manager)

    @property
    def is_covered(self) -> bool:
        return bool(self._is_covered.load(self.data_manager))

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


class Location(DataObject):
    def __init__(self, id:str, **kwargs):
        self.id = id

        DataObject.__init__(self, 'LOC_INIT', EID(id = self.id), kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестное место')
        self._type = self.field('type', None)
        self._cluster = self.field('region', None)
        self._owner = self.field('owner', None)
        self._cost = self.field('cost', 0)
        self._picture = self.field('picture', None)
        self._current_battle_id = self.field('current_battle', None)
        self._is_covered = self.field('is_covered', None)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @label.setter
    def label(self, value: str):
        self._label.save(self.data_manager, value)

    @property
    def type(self) -> Union[LocationType, None]:
        type_id = self._type.load(self.data_manager)
        if type_id:
            return LocationType(type_id, data_manager=self.data_manager)
        else:
            return None

    @type.setter
    def type(self, value: str):
        self._type.save(self.data_manager, value)

    @property
    def cluster(self) -> Union[None, 'Cluster']:
        cluster_id = self._cluster.load(self.data_manager)
        if cluster_id:
            return Cluster(cluster_id, data_manager=self.data_manager)
        else:
            return None

    @cluster.setter
    def cluster(self, value: str):
        self._cluster.save(self.data_manager, value)

    @property
    def owner(self) -> str:
        return self._owner.load(self.data_manager)

    @owner.setter
    def owner(self, value: str):
        self._owner.save(self.data_manager, value)

    @property
    def cost(self) -> int:
        return self._cost.load(self.data_manager)

    @cost.setter
    def cost(self, value: int):
        self._cost.save(self.data_manager, value)

    @property
    def picture(self) -> str:
        picture_url = self._picture.load(self.data_manager)
        if not picture_url:
            return self.cluster.picture if self.cluster else None
        return picture_url

    @picture.setter
    def picture(self, value: str):
        self._picture.save(self.data_manager, value)

    @property
    def current_battle(self) -> int:
        return self._current_battle_id.load(self.data_manager)

    @current_battle.setter
    def current_battle(self, value: int):
        self._current_battle_id.save(self.data_manager, value)

    @property
    def is_covered(self) -> bool:
        is_covered = self._is_covered.load(self.data_manager)
        if is_covered is None:
            return self.type.is_covered
        else:
            return bool(is_covered)

    @is_covered.setter
    def is_covered(self, value: bool):
        self._is_covered.save(self.data_manager, int(value))

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
        total_connections = self.get_connections()  # Получаем список всех соединений
        connections = []

        for connection in total_connections:
            # Проверяем, является ли id соединения текущей локацией или другой
            if connection.get('loc_id') == self.id:
                con_id = connection.get('con_id')
            else:
                con_id = connection.get('loc_id')

            # Добавляем словарь для хранения id и транспорта
            connections.append({
                'loc_id': con_id,
                'transport': connection.get('transport')  # Добавляем транспорт
            })

        # Убираем дубликаты
        unique_connections = {con['loc_id']: con for con in connections}.values()

        # Создаем список соединений с добавлением транспорта
        connected_locations = [
            LocationConnection(con['loc_id'], Location(con['loc_id'], data_manager=self.data_manager).cost, con['transport']) for con in unique_connections
        ]

        return connected_locations

    def connected_location(self):
        cons = self.process_connections()
        return [con.loc_id for con in cons]

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


class Cluster(DataObject):
    def __init__(self, id:str, **kwargs):
        self.id = id
        DataObject.__init__(self, 'LOC_CLUSTER', EID(id=self.id), kwargs.get('data_manager', DEFAULT_MANAGER))

        self._label = self.field('label', 'Неизвестный регион')
        self._type = self.field('type', None)
        self._picture = self.field('picture', None)
        self._weather = self.field('weather', 'Sunny')
        self._time = self.field('time', TimeManager().get_current_time_condition())
        self._move_desc = self.field('move_desc', 'Вы переместились на локацию')
        self._map = self.field('map', None)

    @property
    def label(self) -> str:
        return self._label.load(self.data_manager)

    @property
    def type(self) -> Union[str, None]:
        return self._type.load(self.data_manager)

    @property
    def picture(self) -> Union[str, None]:
        return self._picture.load(self.data_manager)

    @property
    def weather(self) -> str:
        return self._weather.load(self.data_manager)

    @property
    def time(self) -> str:
        return self._time.load(self.data_manager)

    @property
    def move_desc(self) -> str:
        return self._move_desc.load(self.data_manager)

    @property
    def map(self) -> str:
        return self._map.load(self.data_manager)

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
        return f'Region.{self.id}'

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
        DEFAULT_MANAGER.insert('LOC_CLUSTER', query)
        return cls(cluster_id)


@dataclass()
class LocationConnection:
    loc_id: str | None
    cost: int | None
    required_transport: str = None

    def is_available(self, character_id:int):
        return True


class CharacterLocation(DataObject):
    def __init__(self, id:int, **kwargs):
        self.id = id

        DataObject.__init__(self, 'CHARS_LOC', EID(id=self.id), kwargs.get('data_manager', DEFAULT_MANAGER))
        self.insert_data_if_not_exists()

        self._location_id = self.field('loc_id', None)
        self._move_points = self.field('move_points', 0)
        self._entered = self.field('entered', 0)

    @property
    def location_id(self) -> Union[str, None]:
        return self._location_id.load(self.data_manager)

    @location_id.setter
    def location_id(self, new_location_id: Union[str, None]):
        self._location_id.save(self.data_manager, new_location_id)

    @property
    def location(self) -> Union[Location, None]:
        loc_id = self._location_id.load(self.data_manager)
        if loc_id is None:
            return None
        return Location(loc_id, data_manager=self.data_manager)

    @location.setter
    def location(self, new_location: Union[str, Location, None]):
        if isinstance(new_location, Location):
            new_location = new_location.id

        self._location_id.save(self.data_manager, new_location)

    @property
    def movement_points(self) -> int:
        return self._move_points.load(self.data_manager)

    @movement_points.setter
    def movement_points(self, new_points: int):
        self._move_points.save(self.data_manager, new_points)

    @property
    def entered_location(self) -> bool:
        return self._entered.load(self.data_manager) == 1

    @entered_location.setter
    def entered_location(self, new_value: Union[bool, int]):
        if isinstance(new_value, bool):
            new_value = int(new_value)
        self._entered.save(self.data_manager, new_value)

    def get_all_viewed_locations(self):
        all_locations = self.graph_all_locations()
        filtered_locations = [loc for loc in all_locations if Location(loc, data_manager=self.data_manager).is_location_viewed(self.id)]
        get_dislocation_connections = [loc.loc_id for loc in self.location.process_connections()]
        get_connections_connections = []
        for loc in get_dislocation_connections:
            for con in Location(loc, data_manager=self.data_manager).process_connections():
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

    def check_location_is_viewed(self, location_id:str):
        if location_id in self.location.connected_location():
            return True
        loc = Location(location_id, data_manager=self.data_manager)
        return loc.is_location_viewed(self.id)

    def graph_linked_locations(self):
        # Используем множество для отслеживания уже посещенных локаций
        visited = set()

        # Инициализируем граф с текущей локацией
        graph = {self.location.id: self.location.process_connections()}

        # Стек для обработки локаций
        stack = [self.location.id]

        # Добавляем начальную локацию в множество посещённых
        visited.add(self.location.id)

        while stack:
            # Берем текущую локацию из стека
            current_loc_id = stack.pop()

            # Получаем все соединения для этой локации
            connections = graph[current_loc_id]

            for con in connections:
                # Проверяем, если локация ещё не была посещена
                if not con.is_available(self.id):
                    continue

                if con.loc_id not in visited:
                    # Добавляем новую локацию в граф и стек
                    graph[con.loc_id] = Location(con.loc_id, data_manager=self.data_manager).process_connections()

                    # Добавляем в стек для дальнейшей обработки
                    stack.append(con.loc_id)

                    # Помечаем как посещённую
                    visited.add(con.loc_id)

        return graph

    def get_viewed_locations(self, region_id: str = None):
        total_locs = Cluster(region_id, data_manager=self.data_manager).fetch_locations() if region_id else self.data_manager.select_dict('LOC_INIT')
        locs = [loc.get('id') for loc in total_locs]

        start_time = datetime.datetime.now()

        viewed_locations = []

        # Кэшируем организации и их отношения
        relations_cache = {}

        for loc in locs:
            location = Location(loc, data_manager=self.data_manager)

            # Проверка, покрыта ли локация
            if not location.is_covered:
                viewed_locations.append(loc)
                continue

            owner_org = location.get_owner()

            if not owner_org:
                owner_org = Organization('Civil', data_manager=self.data_manager)

            if owner_org.id not in relations_cache:
                relations_cache[owner_org.id] = owner_org.relation_to_character(self.id)

            # Если отношение больше 60, добавляем локацию в просмотренные
            if relations_cache[owner_org.id] >= 60:
                viewed_locations.append(loc)

        print(datetime.datetime.now() - start_time)

        return [loc for loc in viewed_locations]

    def create_graph(self):
        graph = self.graph_linked_locations()

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

    def create_only_viewed_graph(self):
        viewed_locations = [loc for loc in self.get_viewed_locations()]
        graph = self.graph_linked_locations()
        viewed_graph = {loc: graph[loc] for loc in graph if loc in viewed_locations}

        G = nx.Graph()
        for node in viewed_graph:
            node_label = Location(node, data_manager=self.data_manager).id
            G.add_node(Location(node, data_manager=self.data_manager).id)
            for edge in graph[node]:
                linked_node = Location(edge.loc_id, data_manager=self.data_manager).id

                distance = edge.cost
                if linked_node not in G.nodes:
                    G.add_node(linked_node)
                if (node, linked_node, {'weight': distance}) not in G.edges:
                    G.add_edge(node_label, linked_node, weight=distance)

        print(viewed_graph)

        return G

    def find_shortest_path(self, loc_id:str):
        graph = self.create_only_viewed_graph()
        print(graph)
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