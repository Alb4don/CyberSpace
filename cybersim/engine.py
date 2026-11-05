import time
from pathlib import Path
from .agents import Coordinator
from .beliefs import Beliefs
from .environment import demo, Environment
from .evaluation import evaluate
from .models import Config
from .paths import PathAnalyzer
from .storage import Memory

class Engine:
    def __init__(self, config: Config, database: Path, scenario: Path | None = None):
        self.config = config
        self.database = database
        self.scenario = scenario

    def stream(self):
        memory = Memory(self.database)
        try:
            environment = Environment.from_json(self.scenario, self.config) if self.scenario else demo(self.config)
            beliefs = Beliefs(memory.prior())
            coordinator = Coordinator(environment, beliefs, self.config.seed, self.config.agents)
            started = time.perf_counter()
            for step, positions, events, observations in coordinator.explore(self.config.steps):
                analyzer = PathAnalyzer(environment, beliefs)
                findings = analyzer.candidates(self.config.threshold, self.config.max_paths)
                nodes = [(name, node['data'].x, node['data'].y, node['data'].z, node['data'].target, node['data'].active) for name, node in environment.graph.nodes(data=True)]
                edges = [(u, v, data['data'].active, data['data'].relation.value) for u, v, data in environment.graph.edges(data=True)]
                yield ('frame', {'step': step + 1, 'total': self.config.steps, 'epoch': environment.epoch,
                    'nodes': nodes, 'edges': edges, 'agents': positions, 'events': events[-30:],
                    'paths': [f.model_dump() for f in findings], 'expanded': coordinator.expanded})
            analyzer = PathAnalyzer(environment, beliefs)
            findings = analyzer.candidates(self.config.threshold, self.config.max_paths)
            elapsed = time.perf_counter() - started
            metrics = evaluate(environment, findings, elapsed, coordinator.expanded + analyzer.expanded, self.config)
            episode = memory.save(self.config.seed, environment.epoch, observations, metrics)
            yield ('complete', (environment, findings, metrics, episode))
        finally:
            memory.close()

    def run(self):
        result = None
        for kind, payload in self.stream():
            if kind == 'complete':
                result = payload
        return result
