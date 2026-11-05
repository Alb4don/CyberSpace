from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class NodeKind(str, Enum):
    host = "host"
    server = "server"
    service = "service"
    control = "control"

class Relation(str, Enum):
    reachability = "reachability"
    trust = "trust"
    credential = "credential"

class Node(Strict):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    kind: NodeKind
    vulnerable: bool = False
    patched: bool = False
    active: bool = True
    target: bool = False
    x: float = Field(ge=-1000, le=1000, allow_inf_nan=False)
    y: float = Field(ge=-1000, le=1000, allow_inf_nan=False)
    z: float = Field(default=0.0, ge=-1000, le=1000, allow_inf_nan=False)

class Edge(Strict):
    source: str
    destination: str
    relation: Relation
    active: bool = True
    confidence: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)

class Config(Strict):
    seed: int = Field(default=7, ge=0, le=2**32 - 1)
    agents: int = Field(default=3, ge=1, le=16)
    steps: int = Field(default=24, ge=1, le=200)
    threshold: float = Field(default=0.72, gt=0, le=1)
    max_nodes: int = Field(default=256, ge=2, le=2000)
    max_edges: int = Field(default=4096, ge=1, le=1024)
    max_paths: int = Field(default=128, ge=1, le=1024)
    start: str = "workstation"

class Scenario(Strict):
    nodes: list[Node]
    edges: list[Edge]
    start: str

    @model_validator(mode="after")
    def check(self):
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)) or self.start not in ids:
            raise ValueError("Invalid node identifiers or start")
        if any(e.source not in ids or e.destination not in ids for e in self.edges):
            raise ValueError("Edge references unknown node")
        keys = [(e.source, e.destination, e.relation) for e in self.edges]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate typed edge")
        return self

class Observation(Strict):
    agent: int = Field(ge=0, le=15)
    step: int = Field(ge=0)
    source: str
    destination: str
    relation: Relation
    present: bool
    reliability: float = Field(ge=0.5, lt=1, allow_inf_nan=False)
    epoch: int = Field(ge=0)

class Finding(Strict):
    path: list[str] = Field(min_length=2)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    verified: bool

class Metrics(Strict):
    method: str
    coverage: float = Field(ge=0, le=1)
    false_positive_rate: float = Field(ge=0, le=1)
    wall_seconds: float = Field(ge=0)
    nodes_expanded: int = Field(ge=0)
    findings: int = Field(ge=0)
    ground_truth_paths: int = Field(ge=0)
