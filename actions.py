"""Controlled Windows actions for closing targets and launching distractions."""

from __future__ import annotations

import argparse
import logging
import webbrowser
from pathlib import Path

from detector import ActiveWindow
from utils import load_json

LOGGER = logging.getLogger(__name__)
WM_CLOSE = 0x0010

try:
    import pyautogui
    import win32gui
    import win32api
except ImportError:  # pragma: no cover - exercised on non-Windows/dev environments
    pyautogui = None
    win32gui = None
    win32api = None

try:
    from winotify import Notification
except Exception:  # pragma: no cover - unavailable outside Windows
    Notification = None


class ActionController:
    """Perform immediate actions without tracking offense or application state."""

    def __init__(self, distractions_config: str | Path = "config/distractions.json") -> None:
        self.distractions = self._load_distractions(distractions_config)

    @staticmethod
    def _load_distractions(path: str | Path) -> list[dict[str, str]]:
        payload = load_json(path, default={})
        values = payload.get("distractions", []) if isinstance(payload, dict) else []
        result: list[dict[str, str]] = []
        for value in values if isinstance(values, list) else []:
            if isinstance(value, str):
                result.append({"title": "Watch now", "url": value})
            elif isinstance(value, dict) and value.get("url"):
                result.append({"title": str(value.get("title", "Watch now")), "url": str(value["url"])})
        return result

    def close_target(self, window: ActiveWindow, *, browser_tab: bool = True) -> bool:
        """Close a browser tab when possible, otherwise request window closure."""
        process = window.process_name.casefold()
        browsers = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
        try:
            if browser_tab and process in browsers and pyautogui is not None:
                pyautogui.hotkey("ctrl", "w")
                return True
            if win32gui is not None and win32api is not None and window.handle:
                win32api.PostMessage(window.handle, WM_CLOSE, 0, 0)
                return True
        except (OSError, RuntimeError) as error:
            LOGGER.warning("Unable to close target window %s: %s", window.handle, error)
        return False

    def notify(self, message: str, *, distraction_index: int = 0) -> bool:
        """Show a non-modal Windows Action Center toast with an optional action."""
        if Notification is None:
            LOGGER.warning("Windows toast provider unavailable: %s", message)
            return False
        try:
            toast = Notification(
                app_id="Padikula, Padippikula",
                title="Study detected",
                msg=message,
            )
            if self.distractions:
                distraction = self.distractions[distraction_index % len(self.distractions)]
                toast.add_actions(label=distraction["title"], launch=distraction["url"])
            toast.show()
            return True
        except Exception as error:
            LOGGER.warning("Action Center toast failed: %s", error)
            return False

    def distraction_count(self) -> int:
        """Return the number of configured toast actions."""
        return len(self.distractions)

    def launch_distraction(self, index: int = 0) -> bool:
        """Launch one configured distraction URL in the default browser."""
        if not self.distractions:
            LOGGER.warning("No distraction URLs configured")
            return False
        distraction = self.distractions[index % len(self.distractions)]
        try:
            return bool(webbrowser.open(distraction["url"], new=2))
        except (OSError, webbrowser.Error) as error:
            LOGGER.warning("Unable to launch distraction URL: %s", error)
            return False


def run_action_test() -> None:
    """Run a safe action test that only attempts a configured notification."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    controller = ActionController()
    result = controller.notify("Action self-test: study detected.")
    print(f"Notification self-test: {'passed' if result else 'fallback logged'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the safe action self-test.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("use --self-test to run the safe action test")
    run_action_test()