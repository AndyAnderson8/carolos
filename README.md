# Carol AIO

A small all-in-one Windows app that hosts several mini Python tools. It lives in
the system tray: click the icon to open a panel with an on/off switch for each
tool, and click a tool's gear (⚙) to edit its settings in a small popup window.
Right-click the icon to quit.

## Run from source

```
python main.py
```

## Build

```
pip install -r requirements-build.txt
winget install JRSoftware.InnoSetup   # once, to build the installer
python build.py                       # -> dist/CarolAIO/ and dist/CarolAIO-Setup-<version>.exe
```

`build.py` runs PyInstaller to produce the app as a folder, then Inno Setup
(`installer/carol_aio.iss`) to wrap it into the installer. Without Inno Setup it still builds
`dist/CarolAIO/` and warns. Pushes to `main`/`dev` also build the installer in GitHub Actions
(artifact `CarolAIO-Setup`).

## Installing and updating

Download `CarolAIO-Setup-<version>.exe` from the Releases page and run it. It installs for your
account (no admin rights) into `%LOCALAPPDATA%\Programs\CarolAIO` by default, and the setup
wizard lets you pick another folder and choose whether to add a desktop and a Start menu
shortcut. The app appears under Settings > Apps, and uninstalling asks whether to keep your
settings. `config.yaml` lives in the install folder and is never touched by upgrades; an existing
`config.yaml` next to the setup file is copied in on a first install. Running a newer setup over
an installed copy upgrades it in place (it stops the running app first).

Updates come from the GitHub Releases page, so the repo has to be public. Carol AIO checks a few
seconds after it starts and, if there is a newer release, shows an **Update now** dialog. That
downloads the new setup (checking its size and SHA-256), quits the app, and runs the setup
silently, which upgrades the app and starts it again. **Check for updates** in the tray menu or
the panel footer runs the same check on demand and says so when you are up to date. Only
published releases count (pre-releases from untagged commits do not). A copy that wasn't
installed with the setup program, including a source run, never updates itself.

Only one copy runs at a time.

## Releases

Every push to `main` publishes a GitHub release with `CarolAIO-Setup-<version>.exe` attached.
The version shown in the panel header and in the release name is:

- the git tag on the commit, if it has one (tag the merge: `git tag v1.2.0 && git push --tags`);
- otherwise the short commit hash, published as a pre-release;
- `dev` when run from source.

Pushing a `v*` tag publishes that release even if it comes after the merge, so tagging
a merge that is already on `main` gives you both a pre-release for the commit and the
tagged release.

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
