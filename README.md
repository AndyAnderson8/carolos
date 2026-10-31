# Carol AIO

A small all-in-one Windows app that hosts several mini Python tools. It lives in
the system tray: click the icon to open a panel with an on/off switch for each
tool, and click a tool's gear (⚙) to edit its settings in a small popup window.
Right-click the icon to quit.

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
| Pause media on calls | When Edge makes a sound (a call announcing itself), pauses everything that is playing: Spotify, YouTube in other browsers, etc. Only apps that are playing get paused, and Edge itself is left alone so the call isn't touched. Windows only. |

## Configuration

Settings live in `config.yaml` next to `CarolAIO.exe` (the repo root when run
from source). It is created on first run. Click the gear (⚙) on a tool to edit
its settings in the popup (it follows the Windows light/dark setting), or edit the file directly; the running app picks up
hand edits within a second. Invalid values fall back to defaults and are
reported at the bottom of the window.

```yaml
tools:
  call_pause:
    enabled: true
    settings:
      process_name: msedge.exe  # "App that plays the call sound" (pick it in the popup)
      reaction: balanced        # "How quickly to pause": fast, balanced or careful
      threshold: 0.001          # peak level (0-1) counted as audible (config.yaml only)
```

To use a different location, run `CarolAIO.exe --config C:\path\to\config.yaml`
(e.g. in a shortcut) or set the `CAROL_AIO_CONFIG` environment variable.

Tools marked `enabled: true` start automatically when the app opens.

Settings from before the tool was renamed (`edge_audio_pause`) are moved to `call_pause` on load.

## Development

```
pip install -r requirements-dev.txt
black .                                   # formatter (config in pyproject.toml)
mypy                                      # strict type checking
python -m unittest discover -s tests -t .
```

All code is fully type-hinted; CI runs `black --check`, `mypy` and the tests before building the exe.
