
- This is an oracle assisted simulator and should not be interpreted as real world vulnerability detection. 

<img width="1333" height="813" alt="image simulation" src="https://github.com/user-attachments/assets/ae5c69a2-533f-4438-ab55-304bc6032c4b" />

### `Setup`

    python -m venv .venv
    python -m pip install -e '.[test]'
    python -m pytest -q
    python -m cybersim.main --headless
    python -m cybersim.main

- On Windows, activate the virtual environment with `.venv\Scripts\activate` before running pip, or use `.venv\Scripts\python -m pip ...`.

### `Architecture`

- `models.py` contains strict domain schemas; `environment.py` provides a synthetic directed typed multigraph and mutation engine; 
- `agents.py` coordinates autonomous observations; `beliefs.py` stores independent agent evidence; 
- `paths.py` filters and validates candidate paths; `storage.py` persists episodes; 
- `evaluation.py` provides baseline comparisons; `offline.py` models synthetic Scapy packets; 
- `gui.py` provides a responsive desktop interface; 
- `engine.py` orchestrates execution.

### `Live autonomous visualization`

- Launch the GUI from the project root with `python -m cybersim.main`.
- Runs a stepwise simulated exploration on a background thread.
- Colored triangles show the current locations of independently exploring agents.
- Node and edge changes, verified paths, and agent observation events are updated on each frame. 
- The graph uses an isometric style 2D projection of synthetic node coordinates, not a 3D rendering engine.
