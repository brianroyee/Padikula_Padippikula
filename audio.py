"""Resilient, non-blocking audio playback with Windows beep fallback."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path
from collections.abc import Iterable

from utils import asset_path, resource_path

LOGGER = logging.getLogger(__name__)

try:
    import winsound
except ImportError:  # pragma: no cover - only exercised outside Windows
    winsound = None

try:
    import pygame
except ImportError:  # pragma: no cover - depends on environment
    pygame = None


class AudioPlayer:
    """Play escalated tracks without blocking the daemon's polling loop."""

    def __init__(
        self,
        tracks: Iterable[str | Path] | None = None,
        *,
        audio_directory: str | Path = Path("audio"),
        beep_frequency: int = 880,
        beep_duration_ms: int = 180,
    ) -> None:
        if beep_frequency < 37 or beep_frequency > 32767:
            raise ValueError("beep_frequency must be between 37 and 32767 Hz")
        if beep_duration_ms < 1:
            raise ValueError("beep_duration_ms must be positive")

        self._tracks = self._normalize_tracks(tracks, audio_directory)
        self._beep_frequency = beep_frequency
        self._beep_duration_ms = beep_duration_ms
        self._mixer_ready = False
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_tracks(
        tracks: Iterable[str | Path] | None,
        audio_directory: str | Path,
    ) -> list[Path]:
        if tracks is None:
            directory = asset_path(audio_directory)
            if not directory.is_dir():
                return []
            return sorted(
                path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"
            )

        return [resource_path(track) for track in tracks]

    @property
    def tracks(self) -> tuple[Path, ...]:
        """Return the configured tracks in escalation order."""
        return tuple(self._tracks)

    def initialize(self) -> bool:
        """Initialize pygame audio, returning whether the mixer is usable."""
        with self._lock:
            if self._mixer_ready:
                return True
            if pygame is None:
                LOGGER.warning("pygame is unavailable; using Windows beep fallback")
                return False
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                self._mixer_ready = True
                return True
            except pygame.error as error:
                LOGGER.warning("pygame mixer initialization failed: %s", error)
                return False

    def play(self, offense_level: int) -> bool:
        """Play the track for a one-based offense level, or fall back to a beep."""
        if offense_level < 1:
            raise ValueError("offense_level must be at least 1")

        track = self._track_for_level(offense_level)
        if track is not None and self._play_track(track):
            return True
        return self._play_beep()

    def cleanup(self) -> None:
        """Stop playback and release pygame audio resources."""
        if pygame is None:
            return
        with self._lock:
            if not self._mixer_ready:
                return
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except pygame.error as error:
                LOGGER.warning("pygame mixer cleanup failed: %s", error)
            finally:
                self._mixer_ready = False

    def _track_for_level(self, offense_level: int) -> Path | None:
        if not self._tracks:
            LOGGER.warning("No MP3 tracks configured")
            return None
        return self._tracks[min(offense_level - 1, len(self._tracks) - 1)]

    def _play_track(self, track: Path) -> bool:
        if not track.is_file():
            LOGGER.warning("Audio file missing: %s", track)
            return False
        if not self.initialize() or pygame is None:
            return False
        try:
            pygame.mixer.music.load(str(track))
            pygame.mixer.music.play()
            LOGGER.info("Playing audio track: %s", track.name)
            return True
        except (pygame.error, OSError) as error:
            LOGGER.warning("Unable to play audio file %s: %s", track, error)
            return False

    def _play_beep(self) -> bool:
        if winsound is None:
            LOGGER.warning("winsound is unavailable; audio fallback skipped")
            return False
        threading.Thread(target=self._beep_worker, daemon=True).start()
        return True

    def _beep_worker(self) -> None:
        try:
            winsound.Beep(self._beep_frequency, self._beep_duration_ms)
        except (RuntimeError, OSError) as error:
            LOGGER.warning("Windows beep fallback failed: %s", error)


def run_self_test() -> None:
    """Exercise track discovery and fallback playback independently."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    player = AudioPlayer()
    print(f"Discovered MP3 tracks: {len(player.tracks)}")
    result = player.play(1)
    print(f"Audio self-test: {'passed' if result else 'fallback unavailable'}")
    player.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the standalone audio self-test.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("use --self-test to run the audio test")
    run_self_test()