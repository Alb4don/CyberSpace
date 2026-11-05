import json
from pathlib import Path
import networkx as nx
import numpy as np
from .models import Config, Edge, Node, NodeKind, Relation, Scenario

class Environment:
    def __init__(self, scenario: Scenario, config: Config):
        if len(scenario.nodes) > config.max_nodes or len(scenario.edges) > config.max_edges:
            raise ValueError("Scenario exceeds configured limits")
        self.config = config
        self.graph = nx.MultiDiGraph()
        self.epoch = 0
        for node in scenario.nodes:
            self.graph.add_node(node.id, data=node)
        for edge in scenario.edges:
            self.graph.add_edge(edge.source, edge.destination, key=edge.relation.value, data=edge)
        self.start = scenario.start

    def allowed(self, u: str, v: str, relation: Relation | None = None) -> bool:
        if u not in self.graph or v not in self.graph:
            return False
        a = self.graph.nodes[u]["data"]
        b = self.graph.nodes[v]["data"]
        if not a.active or not b.active or b.patched or not b.vulnerable:
            return False
        edges = self.graph.get_edge_data(u, v, default={})
        return any(e["data"].active and (relation is None or e["data"].relation == relation) for e in edges.values())

    def traversable(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_nodes_from(self.graph.nodes)
        graph.add_edges_from((u, v) for u, v in self.graph.edges() if self.allowed(u, v))
        return graph

    def mutate(self, rng: np.random.Generator):
        candidates = [n for n in self.graph.nodes if n != self.start]
        if not candidates:
            return
        name = candidates[int(rng.integers(len(candidates)))]
        node = self.graph.nodes[name]["data"]
        change = int(rng.integers(3))
        if change == 0:
            self.graph.nodes[name]["data"] = node.model_copy(update={"patched": not node.patched})
        elif change == 1:
            self.graph.nodes[name]["data"] = node.model_copy(update={"active": not node.active})
        else:
            edges = list(self.graph.edges(keys=True))
            if edges:
                u, v, k = edges[int(rng.integers(len(edges)))]
                edge = self.graph[u][v][k]["data"]
                self.graph[u][v][k]["data"] = edge.model_copy(update={"active": not edge.active})
        self.epoch += 1

    @classmethod
    def from_json(cls, path: Path, config: Config):
        if path.stat().st_size > 2_000_000:
            raise ValueError("Scenario file too large")
        scenario = Scenario.model_validate_json(path.read_text(encoding="utf-8"))
        return cls(scenario, config)

def demo(config: Config) -> Environment:
    nodes = [
        Node(id="workstation", kind=NodeKind.host, x=-7.0, y=0.0),
        Node(id="gateway", kind=NodeKind.server, vulnerable=True, x=-3.0, y=2.0),
        Node(id="identity", kind=NodeKind.service, vulnerable=True, x=0.0, y=4.0),
        Node(id="database", kind=NodeKind.server, vulnerable=True, target=True, x=5.0, y=2.0),
        Node(id="backup", kind=NodeKind.server, vulnerable=True, target=True, x=4.0, y=-3.0),
        Node(id="firewall", kind=NodeKind.control, x=-2.0, y=-3.0),
        Node(id="api", kind=NodeKind.service, vulnerable=True, x=0.0, y=-1.0),
    ]
    edges = [Edge(source=a, destination=b, relation=r) for a, b, r in [
        ("workstation", "gateway", Relation.reachability),
        ("gateway", "identity", Relation.trust),
        ("identity", "database", Relation.credential),
        ("gateway", "api", Relation.reachability),
        ("api", "backup", Relation.trust),
        ("workstation", "firewall", Relation.reachability),
        ("firewall", "database", Relation.reachability),
    ]]
    return Environment(Scenario(nodes=nodes, edges=edges, start="workstation"), config)
