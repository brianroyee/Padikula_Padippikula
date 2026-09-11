"""Daemon orchestrator for Padikula, Padippikula."""

from __future__ import annotations

import argparse
import logging
import signal
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from actions import ActionController
from audio import AudioPlayer
from captcha import ImageCaptcha, load_challenge
from detector import ActiveWindow, DetectionResult, StudyDetector
from tray import RuntimeStats, TrayController

LOGGER = logging.getLogger(__name__)


class AudioPort(Protocol):
    def play(self, offense_level: int) -> bool: ...

    def cleanup(self) -> None: ...


class ActionPort(Protocol):
    def close_target(self, window: ActiveWindow, *, browser_tab: bool = True) -> bool: ...

    def notify(self, message: str, *, distraction_index: int = 0) -> bool: ...


class CaptchaPort(Protocol):
    def show(self) -> bool: ...


@dataclass(frozen=True)
class DaemonSettings:
    """Polling and debounce settings for the background loop."""

    poll_interval: float = 1.0
    cooldown_seconds: float = 3.0
    reset_after_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.poll_interval <= 0 or self.cooldown_seconds < 0 or self.reset_after_seconds <= 0:
            raise ValueError("daemon timing settings must be positive")


class Daemon:
    """Coordinate detection and interventions while keeping state centralized."""

    def __init__(
        self,
        *,
        detector: StudyDetector | None = None,
        actions: ActionPort | None = None,
        audio: AudioPort | None = None,
        captcha_factory: Callable[[], CaptchaPort] | None = None,
        settings: DaemonSettings | None = None,
    ) -> None:
        self.detector = detector or StudyDetector()
        self.actions = actions or ActionController()
        self.audio = audio or AudioPlayer()
        self.captcha_factory = captcha_factory or self._default_captcha
        self.settings = settings or DaemonSettings()
        self.offense_level = 0
        self.running = False
        self._last_event_key: tuple[int, str, str] | None = None
        self._last_trigger_at = 0.0
        self._last_offense_at = 0.0
        self.stats = RuntimeStats()
        if hasattr(self.actions, "distraction_count"):
            self.stats.distractions_available = self.actions.distraction_count()
        self._stop_event = threading.Event()
        self.tray = TrayController(
            self.stats,
            on_test_notification=lambda: self.actions.notify("The tray notification test has succeeded."),
            on_exit=self.stop,
        )

    def run(self) -> None:
        """Run until interrupted or ``stop`` is called."""
        self.running = True
        self._stop_event.clear()
        self.tray.start()
        LOGGER.info("Daemon started")
        try:
            while self.running:
                try:
                    self.poll_once()
                except Exception:
                    LOGGER.exception("Polling cycle failed; daemon will continue")
                self._stop_event.wait(self.settings.poll_interval)
        finally:
            self.stop()

    def stop(self) -> None:
        """Request shutdown and release audio resources."""
        self.running = False
        self._stop_event.set()
        self.tray.stop()
        self.audio.cleanup()
        LOGGER.info("Daemon stopped")

    def poll_once(self, now: float | None = None) -> bool:
        """Evaluate and handle one foreground-window snapshot."""
        current_time = time.monotonic() if now is None else now
        self._reset_if_idle(current_time)
        window = self.detector.get_active_window()
        result = self.detector.evaluate(window)
        if not result.detected or window is None:
            return False

        event_key = (window.handle, result.title, result.process_name)
        if event_key == self._last_event_key and current_time - self._last_trigger_at < self.settings.cooldown_seconds:
            return False
        self._last_event_key = event_key
        self._last_trigger_at = current_time
        self._last_offense_at = current_time
        self.stats.attempts_blocked += 1
        self.stats.current_offense = self.offense_level
        if result.target_type.value == "pdf":
            self.stats.pdf_attempts += 1
        elif result.target_type.value == "website":
            self.stats.website_attempts += 1
        elif result.target_type.value == "youtube":
            self.stats.youtube_attempts += 1
        self._intervene(window, result)
        return True

    def _intervene(self, window: ActiveWindow, result: DetectionResult) -> None:
        self.offense_level += 1
        LOGGER.info("Study target detected: %s (%s)", result.target_type.value, result.reason)
        LOGGER.info("Offense level: %s", self.offense_level)
        self.audio.play(self.offense_level)
        self.actions.close_target(window)

        if self.offense_level == 1:
            if self.actions.notify("Ente Vavanekonde ayinne onum avullane...vittukala"):
                self.stats.notifications_sent += 1
            return

        self.stats.captchas_shown += 1
        captcha = self.captcha_factory()
        solved = captcha.show()
        if solved:
            LOGGER.info("CAPTCHA completed; resetting offense state")
            self.offense_level = 0
            self.stats.current_offense = 0
        else:
            LOGGER.info("CAPTCHA expired or was closed by application")

    def _reset_if_idle(self, now: float) -> None:
        if self.offense_level and now - self._last_offense_at >= self.settings.reset_after_seconds:
            LOGGER.info("Offense state reset after inactivity")
            self.offense_level = 0
            self._last_event_key = None

    @staticmethod
    def _default_captcha() -> CaptchaPort:
        return ImageCaptcha(load_challenge())


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def run_self_test() -> None:
    """Exercise first-strike, debounce, and second-strike orchestration safely."""

    class FakeDetector:
        def __init__(self) -> None:
            self.window = ActiveWindow(101, "lecture notes.pdf", "chrome.exe", 7)

        def get_active_window(self) -> ActiveWindow:
            return self.window

        def evaluate(self, window: ActiveWindow) -> DetectionResult:
            return DetectionResult(True, title=window.title, process_name=window.process_name, window_handle=window.handle, reason="self_test")

    class FakeActions:
        def __init__(self) -> None:
            self.notifications = 0
            self.closed = 0

        def close_target(self, _window: ActiveWindow, *, browser_tab: bool = True) -> bool:
            self.closed += 1
            return True

        def notify(self, _message: str, *, distraction_index: int = 0) -> bool:
            self.notifications += 1
            return True

    class FakeAudio:
        def __init__(self) -> None:
            self.levels: list[int] = []

        def play(self, offense_level: int) -> bool:
            self.levels.append(offense_level)
            return True

        def cleanup(self) -> None:
            return None

    class FakeCaptcha:
        def show(self) -> bool:
            return False

    actions = FakeActions()
    audio = FakeAudio()
    daemon = Daemon(
        detector=FakeDetector(),
        actions=actions,
        audio=audio,
        captcha_factory=FakeCaptcha,
        settings=DaemonSettings(cooldown_seconds=2),
    )
    assert daemon.poll_once(now=0.0) is True
    assert daemon.poll_once(now=1.0) is False
    assert daemon.poll_once(now=3.0) is True
    assert daemon.offense_level == 2
    assert actions.notifications == 1
    assert actions.closed == 2
    assert audio.levels == [1, 2]
    print("Daemon self-test: passed")


def install_signal_handlers(daemon: Daemon) -> None:
    """Connect console interrupts to graceful daemon shutdown."""
    signal.signal(signal.SIGINT, lambda _signum, _frame: daemon.stop())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda _signum, _frame: daemon.stop())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Padikula, Padippikula in the background.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    if args.self_test:
        run_self_test()
        return

    daemon = Daemon()
    install_signal_handlers(daemon)
    daemon.run()


if __name__ == "__main__":
    main()