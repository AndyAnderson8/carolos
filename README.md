# Carol AIO

A small all-in-one Windows app that hosts several mini Python tools. Each tool
gets an on/off toggle in the main window.

## Run from source

```
python main.py
```

## Build the exe

```
pip install -r requirements-build.txt
python build.py        # -> dist/CarolAIO.exe
```

Pushes to `main`/`dev` also build the exe in GitHub Actions (artifact `CarolAIO`).

## Adding a tool

1. Create a module in `carol_aio/tools/` with a subclass of `carol_aio.tool.Tool`
   (`key`, `name`, `description`, `on_start`, `on_stop`).
2. Append the class to `TOOLS` in `carol_aio/tools/__init__.py`.

## Tools

| Tool | What it does |
| --- | --- |
| Edge Audio Pauser | When Edge starts playing audio, polls for 0.25 s and, if the volume is sustained, presses the media Play/Pause key to pause Spotify/YouTube/etc. Windows only. |

## Configuration

Settings live in `config.yaml` next to `CarolAIO.exe` (the repo root when run
from source). It is created on first run. Click the gear (⚙) on a tool to edit
its settings in the app, or edit the file directly; the running app picks up
hand edits within a second. Invalid values fall back to defaults and are
reported at the bottom of the window.

```yaml
tools:
  edge_audio_pause:
    enabled: true
    settings:
      process_name: msedge.exe
      threshold: 0.02      # peak level (0-1) counted as audible
      burst_window: 0.25   # seconds to poll once audio starts
      burst_poll: 0.02     # seconds between samples
      sustain_ratio: 0.8   # fraction of samples that must be audible
```

To use a different location, run `CarolAIO.exe --config C:\path\to\config.yaml`
(e.g. in a shortcut) or set the `CAROL_AIO_CONFIG` environment variable.

Tools marked `enabled: true` start automatically when the app opens.

## Development

```
pip install -r requirements-dev.txt
black .                                   # formatter (config in pyproject.toml)
mypy                                      # strict type checking
python -m unittest discover -s tests -t .
```

All code is fully type-hinted; CI runs `black --check`, `mypy` and the tests before building the exe.
