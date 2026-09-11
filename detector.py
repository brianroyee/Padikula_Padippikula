from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from utils import load_json

LOGGER = logging.getLogger(__name__)

PDF_READER_PROCESSES = {
    "acrordc.exe",
    "acrobat.exe",
    "sumatrapdf.exe",
    "foxitreader.exe",
    "okular.exe",
    "pdfxedit.exe",
}
BROWSER_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
}

try:
    import psutil
    import win32gui
    import win32process
except ImportError:
    psutil = None
    win32gui = None
    win32process = None


class TargetType(str, Enum):
    PDF = "pdf"
    WEBSITE = "website"
    YOUTUBE = "youtube"
    APPLICATION = "application"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ActiveWindow:
    handle: int
    title: str
    process_name: str
    process_id: int


@dataclass(frozen=True)
class DetectionResult:
    detected: bool
    target_type: TargetType = TargetType.UNKNOWN
    title: str = ""
    process_name: str = ""
    window_handle: int = 0
    reason: str = ""


class StudyDetector:
    def __init__(
        self,
        *,
        websites_config: str | Path = "config/websites.json",
        youtube_config: str | Path = "config/youtube_channels.json",
        study_keywords: tuple[str, ...] = (
            "lecture",
            "textbook",
            "engineering",
            "tutorial",
            "course",
            "study",
            "documentation",
        ),
    ) -> None:
        self.domains = self._load_values(websites_config, "domains")
        self.youtube_channels = self._load_values(youtube_config, "channels")
        self.study_keywords = tuple(keyword.casefold() for keyword in study_keywords if keyword.strip())

    @staticmethod
    def _load_values(path: str | Path, key: str) -> tuple[str, ...]:
        payload = load_json(path, default={})
        values = payload.get(key, []) if isinstance(payload, dict) else []
        normalized: list[str] = []
        for value in values if isinstance(values, list) else []:
            if isinstance(value, str):
                normalized.append(value.casefold().strip())
            elif isinstance(value, dict):
                candidate = value.get("domain") or value.get("name") or value.get("channel")
                if candidate:
                    normalized.append(str(candidate).casefold().strip())
        return tuple(value for value in normalized if value)

    def get_active_window(self) -> ActiveWindow | None:
        if win32gui is None or win32process is None or psutil is None:
            LOGGER.warning("Windows detection dependencies are unavailable")
            return None
        try:
            handle = int(win32gui.GetForegroundWindow())
            if not handle:
                return None
            title = win32gui.GetWindowText(handle).strip()
            _, process_id = win32process.GetWindowThreadProcessId(handle)
            process_name = psutil.Process(process_id).name()
            return ActiveWindow(handle, title, process_name.casefold(), process_id)
        except (OSError, psutil.Error, RuntimeError) as error:
            LOGGER.warning("Unable to inspect foreground window: %s", error)
            return None

    def evaluate(self, window: ActiveWindow | None) -> DetectionResult:
        if window is None:
            return DetectionResult(False, reason="foreground_window_unavailable")

        title = window.title
        title_folded = title.casefold()
        process = window.process_name.casefold()
        if self._is_pdf(window, title_folded):
            return self._result(window, TargetType.PDF, "pdf_filename_or_reader")
        if self._matches_any(title_folded, self.domains):
            return self._result(window, TargetType.WEBSITE, "matched_configured_domain")
        if self._matches_youtube(title_folded):
            return self._result(window, TargetType.YOUTUBE, "matched_configured_youtube_channel")
        keyword = next((value for value in self.study_keywords if value in title_folded), None)
        if keyword:
            return self._result(window, TargetType.APPLICATION, f"matched_study_keyword:{keyword}")
        return DetectionResult(False, title=title, process_name=process, window_handle=window.handle)

    def _is_pdf(self, window: ActiveWindow, title: str) -> bool:
        process = window.process_name.casefold()
        if process in PDF_READER_PROCESSES:
            return True
        if ".pdf" in title or "pdf viewer" in title or "pdf document" in title:
            return True
        return process in BROWSER_PROCESSES and any(
            marker in title for marker in ("application/pdf", "chrome pdf viewer", "microsoft edge pdf")
        )

    def _matches_youtube(self, title: str) -> bool:
        return "youtube" in title and self._matches_any(title, self.youtube_channels)

    @staticmethod
    def _matches_any(value: str, candidates: tuple[str, ...]) -> bool:
        return any(candidate in value for candidate in candidates)

    @staticmethod
    def _result(window: ActiveWindow, target_type: TargetType, reason: str) -> DetectionResult:
        return DetectionResult(True, target_type, window.title, window.process_name, window.handle, reason)


def run_detector_test(interval: float = 1.0) -> None:
    detector = StudyDetector()
    print("Press Ctrl+C to stop the detector test.")
    try:
        while True:
            window = detector.get_active_window()
            result = detector.evaluate(window)
            if window is None:
                print("Active Window: unavailable | Detection result: unavailable")
            else:
                print(
                    f"Active Window: {window.handle} | Process: {window.process_name} | "
                    f"Title: {window.title!r} | Detection result: {result.detected} | Reason: {result.reason}"
                )
            time.sleep(max(interval, 0.1))
    except KeyboardInterrupt:
        print("Detector test stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Run the foreground detector test.")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    run_detector_test(args.interval)