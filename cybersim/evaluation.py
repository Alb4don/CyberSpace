import csv
import time
from pathlib import Path
import networkx as nx
from .environment import Environment
from .models import Config, Metrics
from .paths import truth_paths

def evaluate(environment: Environment, findings, elapsed: float, expanded: int, config: Config):
    truth = truth_paths(environment, config.max_paths)
    found = {tuple(f.path) for f in findings}
    positives = len(found & truth)
    false = len(found - truth)
    agent = Metrics(method="agents", coverage=positives / len(truth) if truth else 0.0,
                    false_positive_rate=false / len(found) if found else 0.0,
                    wall_seconds=elapsed, nodes_expanded=expanded,
                    findings=len(found), ground_truth_paths=len(truth))
    graph = environment.traversable()
    output = [agent]
    for method in ("bfs", "shortest_path"):
        start_time = time.perf_counter()
        results = set()
        count = 0
        for target in graph.nodes:
            if not environment.graph.nodes[target]["data"].target or target == environment.start:
                continue
            try:
                if method == "bfs":
                    predecessor = nx.bfs_predecessors(graph, environment.start)
                    parents = dict(predecessor)
                    if target not in parents:
                        continue
                    path = [target]
                    while path[-1] != environment.start:
                        path.append(parents[path[-1]])
                    path.reverse()
                else:
                    path = nx.shortest_path(graph, environment.start, target)
                results.add(tuple(path))
                count += len(path)
            except nx.NetworkXNoPath:
                pass
        output.append(Metrics(method=method, coverage=len(results & truth) / len(truth) if truth else 0.0,
            false_positive_rate=len(results - truth) / len(results) if results else 0.0,
            wall_seconds=time.perf_counter() - start_time, nodes_expanded=count,
            findings=len(results), ground_truth_paths=len(truth)))
    return output

def export_csv(path: Path, metrics: list[Metrics]):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(Metrics.model_fields))
        writer.writeheader()
        writer.writerows(m.model_dump() for m in metrics)
