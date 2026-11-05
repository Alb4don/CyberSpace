from pathlib import Path
import pytest
from pydantic import ValidationError
from cybersim.models import Config, Scenario, Observation, Relation
from cybersim.environment import demo
from cybersim.beliefs import Beliefs
from cybersim.paths import truth_paths, PathAnalyzer
from cybersim.engine import Engine
from cybersim.storage import Memory

def test_scenario_rejects_unknown_nodes():
    with pytest.raises(ValidationError):
        Scenario.model_validate({"nodes": [], "edges": [], "start": "missing"})

def test_demo_paths():
    env = demo(Config())
    paths = truth_paths(env, 128)
    assert ("workstation", "gateway", "identity", "database") in paths
    assert ("workstation", "firewall", "database") not in paths

def test_bayes_negative_evidence():
    beliefs = Beliefs()
    key = ("a", "b", Relation.trust)
    beliefs.update(Observation(agent=0, step=0, source="a", destination="b", relation=Relation.trust,
                               present=False, reliability=0.9, epoch=0))
    assert beliefs.probability(key) < 0.2
    beliefs.reset_epoch(1)
    assert beliefs.probability(key) == 0.5

def test_context_filter_rejects_patched():
    env = demo(Config())
    beliefs = Beliefs()
    for agent in range(3):
        for u, v, key in env.graph.edges(keys=True):
            beliefs.update(Observation(agent=agent, step=0, source=u, destination=v,
                                       relation=Relation(key), present=True, reliability=0.95, epoch=0))
    env.graph.nodes["database"]["data"] = env.graph.nodes["database"]["data"].model_copy(update={"patched": True})
    assert all(f.path[-1] != "database" for f in PathAnalyzer(env, beliefs).candidates(0.7, 128))

def test_persistence_and_engine(tmp_path):
    config = Config(steps=10)
    engine = Engine(config, tmp_path / "test.db")
    env, findings, metrics, episode = engine.run()
    assert episode == 1
    assert len(metrics) == 3
    assert all(0 <= m.coverage <= 1 for m in metrics)
    memory = Memory(tmp_path / "test.db")
    assert 0 < memory.prior() < 1
    memory.close()

def test_invalid_config():
    with pytest.raises(ValidationError):
        Config(steps=-1)
