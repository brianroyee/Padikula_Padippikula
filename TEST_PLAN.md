# Padikula, Padippikula Test Plan

## Safety

The live daemon can close detected study windows. Run it only with unsaved work closed and with a harmless test target ready. The packaged self-test is safe and does not inspect the real foreground window.

## Test Environment

- Windows 10 or Windows 11 x64
- Python environment created from `requirements.txt`
- `pywin32`, `psutil`, `pyautogui`, and `pygame` installed in the active interpreter
- A real CAPTCHA PNG placed under `assets/captcha/`
- At least one MP3 placed under `assets/audio/`
- A browser such as Chrome, Edge, Firefox, or Brave

Run from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Test Case 1: Static Validation

**Command**

```powershell
python -m py_compile *.py
python verify_bundle.py
```

**Expected output**

```text
Bundle resource verification: passed
```

No compilation errors should be reported.

## Test Case 2: Resource Resolver

**Command**

```powershell
python -c "from utils import resource_path; print(resource_path('config/captcha.json'))"
```

**Expected result**

The printed path points to the repository's `config/captcha.json`.

The packaged executable must resolve the same relative path from its bundled resource root.

## Test Case 3: Audio Self-Test

**Command**

```powershell
python audio.py --self-test
```

**Expected output with MP3 assets**

```text
Discovered MP3 tracks: 1
Audio self-test: passed
```

**Expected output without MP3 assets**

```text
Discovered MP3 tracks: 0
Audio self-test: passed
```

A beep or warning is acceptable. The process must not crash.

## Test Case 4: Missing Audio Recovery

Temporarily rename one configured MP3 or leave `assets/audio/` empty.

**Command**

```powershell
python -c "from audio import AudioPlayer; print(AudioPlayer(tracks=['missing.mp3']).play(1))"
```

**Expected result**

A warning about the missing file may appear. The process exits normally and the fallback path is attempted.

## Test Case 5: CAPTCHA Success

Set the first challenge answer in `config/captcha.json` to a known value, for example `42`.

**Command**

```powershell
python captcha.py
```

Enter the configured answer before the timer reaches zero.

**Expected output**

```text
CAPTCHA self-test: solved
```

**Expected UI behavior**

- Frameless centered window
- Always-on-top behavior
- Answer input receives focus
- `Escape`, `Alt+F4`, and the close button do not dismiss it
- Correct answer closes the modal

## Test Case 6: CAPTCHA Expiration

Run the same command but do not enter an answer.

**Expected UI behavior**

- Timer reaches zero
- `TIME EXPIRED` is displayed briefly
- Modal closes
- Process exits normally with an expiration message

## Test Case 7: Detector Synthetic Rules

**Command**

```powershell
python -c "from detector import ActiveWindow, StudyDetector; d=StudyDetector(); d.domains=('geeksforgeeks',); d.youtube_channels=('channel alpha',); print(d.evaluate(ActiveWindow(1, 'lecture notes.pdf', 'chrome.exe', 1))); print(d.evaluate(ActiveWindow(1, 'GeeksForGeeks Arrays', 'chrome.exe', 1))); print(d.evaluate(ActiveWindow(1, 'YouTube Channel Alpha', 'chrome.exe', 1)))"
```

**Expected result**

Three detected results with target types `pdf`, `website`, and `youtube` respectively.

## Test Case 8: Foreground Detector

**Command**

```powershell
python detector.py --interval 1
```

**Expected output**

```text
Active Window: <handle> | Process: <process> | Title: '<title>' | Detection result: False | Reason:
```

Open a configured study target and confirm the result changes to `True` with a reason such as:

```text
Reason: matched_configured_domain
Reason: matched_configured_youtube_channel
Reason: pdf_filename_or_reader
```

Stop with `Ctrl+C`.

## Test Case 9: Safe Action Test

**Command**

```powershell
python actions.py --self-test
```

**Expected result**

With a toast provider installed:

```text
Notification self-test: passed
```

Without one:

```text
Notification self-test: fallback logged
```

No browser or arbitrary process should be closed by this test.

## Test Case 10: Daemon State Machine

**Command**

```powershell
python main.py --self-test
```

**Expected output**

```text
Daemon self-test: passed
```

This verifies first strike, debounce, second strike, audio escalation, and CAPTCHA invocation using test doubles.

## Test Case 11: Packaged Executable

**Command**

```powershell
.\dist\Padikula_Padippikula.exe --self-test
```

**Expected output**

```text
Daemon self-test: passed
```

This confirms the frozen import graph and bootloader start correctly.

## Test Case 12: Controlled End-to-End Flow

1. Put a real MP3 in `assets/audio/`.
2. Put a real PNG in `assets/captcha/`.
3. Add one harmless test domain to `config/websites.json`.
4. Add one distraction URL to `config/distractions.json`.
5. Start the daemon:

```powershell
python main.py --verbose
```

6. Open the configured test website.
7. Confirm offense 1:
   - Audio track 1 plays.
   - The browser tab receives `Ctrl+W`.
   - A notification or notification fallback is logged.
8. Reopen the same website after the cooldown.
9. Confirm offense 2:
   - Audio track 2 plays.
   - The tab closes.
   - CAPTCHA appears.
10. Enter the configured answer or wait for expiration.
11. Stop the daemon with `Ctrl+C`.

**Expected log sequence**

```text
[INFO] Daemon started
[INFO] Study target detected: website (...)
[INFO] Offense level: 1
[INFO] Study target detected: website (...)
[INFO] Offense level: 2
[INFO] CAPTCHA expired or was closed by application
[INFO] Daemon stopped
```

## Known Limitations to Record During Testing

- Browser tab closure depends on the browser remaining focused and accepting simulated keyboard input.
- `WM_CLOSE` is a request; some applications may ignore it.
- Notification action buttons are not currently implemented by `actions.py`; the notification provider fallback only logs when unavailable.
- The default config files contain empty target lists, so detection is intentionally inactive until configured.
- A real CAPTCHA image is required to test image rendering; the repository currently contains only a placeholder file.
