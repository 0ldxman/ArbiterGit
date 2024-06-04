import networkx as nx

from ArbDatabase import DataManager
from dataclasses import dataclass
from ArbUtils.ArbNums import specnum
import heapq
import pprint
import networkx
import matplotlib.pyplot as plt
from collections import defaultdict


@dataclass()
class Trail:
    trail_id: int
    start_loc_id: int
    end_loc_id: int
    movement_cost: int
    movement_type: str
    requirement: dict

    @classmethod
    def fetch_trails_by_location(cls, location_id, data_manager):
        total_trails = []
        visited_locations = []

        # ProTip: Собираем все маршруты, начинающиеся в данной локации
        trails = data_manager.select_dict('LOCATION_TRAILS', filter=f'first_loc = {location_id}')
        for trail in trails:
            current_trail = Trail(trail.get('trail_id'), trail.get('first_loc'), trail.get('second_loc'),trail.get('move_cost'), trail.get('move_type'), trail.get('requirement'))
            visited_locations.append(trail.get('second_loc'))
            total_trails.append(current_trail)

        # А теперь собираем обратные маршруты, ведущие в данную локацию
        reversed_trails = data_manager.select_dict('LOCATION_TRAILS', filter=f'second_loc = {location_id}')
        for trail in reversed_trails:
            if trail.get('first_loc') in visited_locations:
                continue
            else:
                current_trail = Trail(trail.get('trail_id'), trail.get('first_loc'), trail.get('second_loc'),trail.get('move_cost'), trail.get('move_type'), trail.get('requirement'))
                visited_locations.append(trail.get('first_loc'))
                total_trails.append(current_trail)

        return total_trails

    @classmethod
    def get_trail_for_edge(cls, from_loc, to_loc, data_manager):
        trail = data_manager.select_dict('LOCATION_TRAILS', filter=f'first_loc={from_loc} and second_loc={to_loc}')
        if not trail:
            trail = data_manager.select_dict('LOCATION_TRAILS',
                                                  filter=f'first_loc={to_loc} AND second_loc={from_loc}')

        if trail:
            return Trail(trail[0]['trail_id'], trail[0]['first_loc'], trail[0]['second_loc'],
                         trail[0]['move_cost'], trail[0]['move_type'], trail[0]['requirement'])
        return None

    def __str__(self):
        return f'Маршрут {specnum(self.trail_id).roman_number} ({self.trail_id}): {self.start_loc_id}-{self.end_loc_id}'


class GraphBuilder:
    def __init__(self, data_manager, start_location:int):
        self.data_manager = data_manager
        self.graph = defaultdict(list)
        self.build_graph(start_location)
    def build_graph(self, location_id):
        self._build_graph_recursive(location_id, set())  # Авамер

    def _build_graph_recursive(self, location_id, visited):
        visited.add(location_id)

        trails = Location(location_id, data_manager=self.data_manager).fetch_trails()

        if location_id not in self.graph:
            self.graph[location_id] = []

        for trail in trails:
            t_loc = trail.end_loc_id if trail.end_loc_id != location_id else trail.start_loc_id

            if t_loc not in self.graph[location_id]:
                self.add_edge(location_id, t_loc, trail.movement_cost)
                if t_loc not in visited:  # Проверяем, что мы не посещали эту локацию ранее
                    self._build_graph_recursive(t_loc, visited)

    def add_edge(self, start_loc_id, end_loc_id, movement_cost):
        self.graph[start_loc_id].append((end_loc_id, movement_cost))

    def vizualize_graph(self):
        G = nx.Graph()

        for node in self.graph.keys():
            G.add_node(node)

            for edge in self.graph[node]:
                linked_node = edge[0]
                distance = edge[1]
                if linked_node not in G.nodes:
                    G.add_node(linked_node)
                if (node, linked_node, {'weight': distance}) not in G.edges:
                    G.add_edge(node, linked_node, weight=distance)

        pos = nx.shell_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='skyblue', font_weight='bold', node_size=1500)

        plt.show()

    def get_graph(self):
        return dict(self.graph)


class ShortestPathFinder:
    def __init__(self, start_location:int, end_location:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.graph = GraphBuilder(self.data_manager, start_location).graph
        self.start_loc = start_location
        self.end_loc = end_location

    def find_shortest_path(self):
        pq = [(0, self.start_loc, [])]
        visited = set()

        while pq:
            (cost, node, path) = heapq.heappop(pq)

            if node not in visited:
                path = path + [node]
                visited.add(node)

                if node == self.end_loc:
                    return cost, path

                for neighbor, edge_cost in self.graph.get(node, []):
                    if neighbor not in visited:
                        heapq.heappush(pq, (cost + edge_cost, neighbor, path))

        return float('inf'), []  # Если путь не найден

    def find_shortest_path_with_trails(self):
        cost, path = self.find_shortest_path()

        path_with_trails = []
        for i in range(len(path) - 1):
            #edge = (path[i], path[i + 1])
            trail = Trail.get_trail_for_edge(path[i], path[i + 1], data_manager=self.data_manager)
            if trail:
                path_with_trails.append(trail)

        return cost, path_with_trails


class Region:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестный регион')
        self.parent_id = data.get('parent_id', None)
        self.hub_location_id = data.get('hub_id', -1)
        self.hub_movement_cost = data.get('hub_movement_cost', 1)
        self.region_movement_cost = data.get('region_movement_cost', 1)

    def fetch_data(self):
        if self.data_manager.check('REGIONS',f'id = {self.id}'):
            return self.data_manager.select_dict('REGIONS', filter=f'id = {self.id}')[0]
        else:
            return {}

    def get_locations_in_region(self):
        locations_in_region = []
        # здесь нужно ваше собственное получение локаций, например, из базы данных
        # предположим, что вы храните информацию о локациях в базе данных с таблицей LOCATION
        location_data = self.data_manager.select_dict('LOCATION_INIT', filter=f'region = {self.id}')

        for location_item in location_data:
            location = Location(id=location_item['id'], data_manager=self.data_manager)
            locations_in_region.append(location)

        return locations_in_region

class Location:
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = id

        data = self.fetch_data()
        self.label = data.get('label', 'Неизвестная локация')
        self.type = data.get('type', None)
        self.region = data.get('region', -1)
        self.org_id = data.get('org_id', None)


    def fetch_data(self):
        if self.data_manager.check('LOCATION_INIT',f'id = {self.id}'):
            return self.data_manager.select_dict('LOCATION_INIT',filter=f'id = {self.id}')[0]
        else:
            return {}

    def fetch_trails(self):
        return Trail.fetch_trails_by_location(self.id, data_manager=self.data_manager)

    def __repr__(self):
        return f'Location({self.id} {self.label})'



print(ShortestPathFinder(1, 6).find_shortest_path_with_trails())