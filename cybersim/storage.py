import json
import sqlite3
from pathlib import Path
from .models import Observation, Metrics

class Memory:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS episodes (id INTEGER PRIMARY KEY, seed INTEGER NOT NULL, epoch INTEGER NOT NULL, outcome TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, episode INTEGER NOT NULL REFERENCES episodes(id), payload TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY, episode INTEGER NOT NULL, payload TEXT NOT NULL)")
        self.db.commit()

    def prior(self):
        row = self.db.execute("SELECT COUNT(*), SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) FROM episodes").fetchone()
        count, successes = row
        return (2 + (successes or 0)) / (4 + count)

    def save(self, seed: int, epoch: int, observations: list[Observation], metrics: list[Metrics]):
        with self.db:
            cursor = self.db.execute("INSERT INTO episodes(seed,epoch,outcome) VALUES(?,?,?)",
                                     (seed, epoch, "success" if metrics[0].coverage > 0 else "failure"))
            episode = cursor.lastrowid
            self.db.executemany("INSERT INTO observations(episode,payload) VALUES(?,?)",
                                [(episode, o.model_dump_json()) for o in observations])
            self.db.executemany("INSERT INTO evaluations(episode,payload) VALUES(?,?)",
                                [(episode, m.model_dump_json()) for m in metrics])
        return episode

    def close(self):
        self.db.close()
