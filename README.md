<img width="3188" height="1202" alt="frame (3)" src="https://github.com/user-attachments/assets/517ad8e9-ad22-457d-9538-a9e62d137cd7" />


# Padikula, Padippikula


> A deliberately useless Windows daemon that declares war on studying.


Padikula, Padippikula monitors the active foreground window on Windows 10/11. When it detects a configured PDF, academic website, or educational YouTube channel, it escalates an absurd intervention: audio, target closure, a Windows Action Center distraction toast, and eventually a timed CAPTCHA.


This is a local, user-space hackathon project. It does not install persistence, drivers, security-policy changes, or kernel-level components.

## Features

- Foreground-window detection using deterministic configurable rules.
- PDF, website, and educational YouTube channel matching.
- Browser-tab closure with window-close fallback.
- Escalating non-blocking audio with Windows beep fallback.
- Action Center toast with configurable distraction actions.
- Rotating image CAPTCHA with short timeout.
- System-tray menu with statistics, notification test, and exit.
- Persistent polling loop that continues until stopped from the tray, console, or Task Manager.
- PyInstaller-compatible asset resolution.

## Project Layout

```text
├── main.py                 # daemon loop and offense state
├── detector.py             # foreground-window detection
├── actions.py              # close, toast, and distraction actions
├── audio.py                # audio escalation and fallback
├── captcha.py              # rotating CAPTCHA UI
├── tray.py                 # tray icon and statistics screen
├── utils.py                # resource and JSON helpers
├── config/                 # editable target and CAPTCHA data
├── assets/                 # audio and image assets
├── tests/                  # test workspace
├── build.ps1               # PyInstaller build command
├── project_name.spec       # PyInstaller specification
└── TEST_PLAN.md            # manual verification plan
```

## Setup

PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure

Edit the JSON files in `config/`:

- `websites.json`: study-related domains or title fragments.
- `youtube_channels.json`: educational channel title fragments.
- `distractions.json`: toast action labels and URLs.
- `captcha.json`: image paths, answers, prompts, and time limits.

Add media to `assets/audio/` and `assets/captcha/`.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --verbose
```

The daemon continues polling until `Ctrl+C`, the tray Exit command, or Task Manager termination.

Safe checks:

```powershell
python main.py --self-test
python actions.py --self-test
python audio.py --self-test
python verify_bundle.py
```

## Build

```powershell
.\build.ps1
.\dist\Padikula_Padippikula.exe --self-test
```

Generated `build/`, `dist/`, virtual-environment, and Python-cache files are ignored by Git.

## Safety and Limitations

- Browser tab closure depends on focus and simulated keyboard input.
- `WM_CLOSE` is a graceful request and may be ignored by an application.
- Notifications depend on Windows Action Center being available.
- The project does not disable Task Manager or make itself unkillable.
- The full manual test procedure is documented in [TEST_PLAN.md](TEST_PLAN.md).

## Team

Built by Team Thengakola for TinkerHub Useless Projects.

---
Built for TinkerHub Useless Projects.



