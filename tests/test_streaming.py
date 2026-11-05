from cybersim.engine import Engine
from cybersim.models import Config


def test_stream_frames_and_completion(tmp_path):
    events = list(Engine(Config(steps=12, agents=3, seed=42), tmp_path / 'stream.db').stream())
    frames = [value for kind, value in events if kind == 'frame']
    assert len(frames) == 12
    assert events[-1][0] == 'complete'
    assert all(len(frame['agents']) == 3 for frame in frames)
    assert [frame['step'] for frame in frames] == list(range(1, 13))
    assert frames[9]['epoch'] == 1
    assert all(frame['expanded'] >= 0 for frame in frames)


def test_reproducible_stream(tmp_path):
    def frames(filename):
        return [(value['agents'], value['epoch'], value['expanded']) for kind, value in Engine(
            Config(steps=18, agents=4, seed=123), tmp_path / filename).stream() if kind == 'frame']
    assert frames('a.db') == frames('b.db')
