import math
from collections import defaultdict
from .models import Observation, Relation

class Beliefs:
    def __init__(self, prior: float = 0.5):
        self.prior = min(0.8, max(0.2, prior))
        self.evidence: dict[tuple[str, str, Relation], dict[int, tuple[int, float, int]]] = defaultdict(dict)
        self.epoch = 0

    def reset_epoch(self, epoch: int):
        if epoch != self.epoch:
            self.evidence.clear()
            self.epoch = epoch

    def update(self, observation: Observation):
        self.reset_epoch(observation.epoch)
        key = (observation.source, observation.destination, observation.relation)
        direction = 1 if observation.present else -1
        odds = math.log(observation.reliability / (1 - observation.reliability))
        self.evidence[key][observation.agent] = (direction, odds, observation.step)

    def probability(self, key: tuple[str, str, Relation]) -> float:
        log_odds = math.log(self.prior / (1 - self.prior))
        for direction, odds, _ in self.evidence.get(key, {}).values():
            log_odds += direction * odds
        return 1 / (1 + math.exp(-max(-40, min(40, log_odds))))

    def supporters(self, key):
        return sum(1 for direction, _, _ in self.evidence.get(key, {}).values() if direction > 0)
