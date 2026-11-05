from hypothesis import given, strategies as st
from pydantic import ValidationError
from cybersim.models import Observation, Relation
from cybersim.beliefs import Beliefs

@given(st.floats(min_value=0.5, max_value=0.999, allow_nan=False, allow_infinity=False))
def test_positive_evidence_increases_probability(reliability):
    beliefs = Beliefs()
    key = ("a", "b", Relation.reachability)
    before = beliefs.probability(key)
    beliefs.update(Observation(agent=0, step=0, source="a", destination="b", relation=Relation.reachability,
                               present=True, reliability=reliability, epoch=0))
    assert beliefs.probability(key) >= before

@given(st.binary(max_size=2000))
def test_json_validator_fuzzes_without_crash(payload):
    try:
        Observation.model_validate_json(payload)
    except (ValidationError, ValueError, UnicodeDecodeError):
        pass
