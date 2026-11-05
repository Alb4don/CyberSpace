import math
from itertools import islice
import networkx as nx
from .beliefs import Beliefs
from .environment import Environment
from .models import Finding, Relation

class PathAnalyzer:
    def __init__(self, environment: Environment, beliefs: Beliefs):
        self.environment = environment
        self.beliefs = beliefs
        self.expanded = 0

    def candidates(self, threshold: float, max_paths: int):
        env = self.environment
        graph = nx.DiGraph()
        graph.add_nodes_from(env.graph.nodes)
        for u, v, key, data in env.graph.edges(keys=True, data=True):
            edge = data["data"]
            evidence_key = (u, v, edge.relation)
            probability = self.beliefs.probability(evidence_key)
            if probability >= threshold and self.beliefs.supporters(evidence_key) >= 2:
                if graph.has_edge(u, v):
                    if probability > graph[u][v]["confidence"]:
                        graph[u][v].update(confidence=probability, relation=edge.relation)
                else:
                    graph.add_edge(u, v, confidence=probability, relation=edge.relation,
                                   weight=-math.log(max(probability, 1e-12)))
        targets = sorted(n for n in graph.nodes if env.graph.nodes[n]["data"].target)
        results = []
        for target in targets:
            if target == env.start or not nx.has_path(graph, env.start, target):
                continue
            for path in islice(nx.all_simple_paths(graph, env.start, target, cutoff=min(12, len(graph) - 1)), max_paths):
                self.expanded += len(path)
                if len(results) >= max_paths:
                    return results
                probability = math.prod(graph[a][b]["confidence"] for a, b in zip(path, path[1:]))
                if probability < threshold:
                    continue
                valid = all(env.allowed(a, b, graph[a][b]["relation"]) for a, b in zip(path, path[1:]))
                if valid:
                    results.append(Finding(path=path, confidence=probability, verified=True))
        return results

def truth_paths(environment: Environment, limit: int):
    graph = environment.traversable()
    paths = []
    for node in sorted(graph.nodes):
        if environment.graph.nodes[node]["data"].target and node != environment.start:
            if nx.has_path(graph, environment.start, node):
                for path in islice(nx.all_simple_paths(graph, environment.start, node, cutoff=min(12, len(graph) - 1)), limit):
                    paths.append(tuple(path))
                    if len(paths) >= limit:
                        return set(paths)
    return set(paths)
