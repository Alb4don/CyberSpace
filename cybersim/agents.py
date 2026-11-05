import networkx as nx
import numpy as np
from .models import Observation

class Coordinator:
    def __init__(self, environment, beliefs, seed, count):
        self.environment = environment
        self.beliefs = beliefs
        self.rng = np.random.default_rng(seed)
        self.count = count
        self.expanded = 0
        self.visits = {}
        self.positions = [environment.start for _ in range(count)]
        self.known = [set([environment.start]) for _ in range(count)]

    def explore(self, steps):
        graph = self.environment.graph
        observations = []
        for step in range(steps):
            changes = []
            if step and step % 9 == 0:
                self.environment.mutate(self.rng)
                self.beliefs.reset_epoch(self.environment.epoch)
                changes.append('Topology changed; evidence reset')
            simple = nx.DiGraph(graph)
            between = nx.betweenness_centrality(simple)
            pagerank = nx.pagerank(simple)
            degree = dict(simple.degree())
            events = []
            for agent in range(self.count):
                current = self.positions[agent]
                nearby = set(graph.successors(current)) | set(graph.predecessors(current)) | {current}
                if len(self.known[agent]) > 1:
                    nearby |= self.known[agent]
                candidates = sorted(nearby)
                weights = np.array([0.02 + between[n] + pagerank[n] + degree[n] / max(1, len(graph)) for n in candidates], dtype=float)
                weights /= np.array([1 + self.visits.get((agent, n), 0) for n in candidates])
                weights /= weights.sum()
                node = candidates[int(self.rng.choice(len(candidates), p=weights))]
                self.positions[agent] = node
                self.known[agent].add(node)
                self.visits[(agent, node)] = self.visits.get((agent, node), 0) + 1
                events.append(f'Agent {agent + 1} exploring {node}')
                for _, destination, key, attributes in graph.out_edges(node, keys=True, data=True):
                    edge = attributes['data']
                    present = self.environment.allowed(node, destination, edge.relation)
                    reliability = 0.9
                    observed = present if self.rng.random() < reliability else not present
                    observation = Observation(agent=agent, step=step, source=node, destination=destination,
                        relation=edge.relation, present=observed, reliability=reliability, epoch=self.environment.epoch)
                    self.beliefs.update(observation)
                    observations.append(observation)
                    self.known[agent].add(destination)
                    self.expanded += 1
                    events.append(f'Agent {agent + 1}: {node} → {destination}: {"positive" if observed else "negative"}')
            yield step, list(self.positions), events + changes, observations

    def run(self, steps, on_observation=None):
        previous = 0
        observations = []
        for _, _, _, observations in self.explore(steps):
            if on_observation:
                for observation in observations[previous:]:
                    on_observation(observation)
            previous = len(observations)
        return observations
