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
