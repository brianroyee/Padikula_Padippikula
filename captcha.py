"""Configurable, topmost image CAPTCHA for the second-strike intervention."""

from __future__ import annotations

import argparse
import json
import logging
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils import resource_path

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config") / "captcha.json"
_challenge_positions: dict[Path, int] = {}


@dataclass(frozen=True)
class CaptchaChallenge:
    """One locally configured CAPTCHA challenge."""

    image: Path | None
    answer: str
    time_limit: int
    prompt: str = "Enter the answer before time expires."

    @classmethod
    def from_mapping(cls, value: dict[str, Any], base_path: Path) -> "CaptchaChallenge":
        answer = str(value.get("answer", "")).strip()
        if not answer:
            raise ValueError("captcha answer must not be empty")

        time_limit = int(value.get("time_limit", 5))
        if time_limit < 1:
            raise ValueError("captcha time_limit must be at least 1 second")

        image_name = value.get("image")
        image = None if not image_name else base_path / str(image_name)
        return cls(
            image=image,
            answer=answer,
            time_limit=time_limit,
            prompt=str(value.get("prompt", cls.prompt)),
        )


def load_challenge(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    index: int | None = None,
) -> CaptchaChallenge:
    """Load a configured challenge, rotating through entries by default."""
    resolved_config = resource_path(config_path)
    with resolved_config.open("r", encoding="utf-8") as config_file:
        payload = json.load(config_file)

    challenges = payload.get("challenges")
    if not isinstance(challenges, list) or not challenges:
        raise ValueError("captcha config must contain a non-empty 'challenges' list")

    if index is None:
        selected_index = _challenge_positions.get(resolved_config, 0) % len(challenges)
        _challenge_positions[resolved_config] = selected_index + 1
    else:
        selected_index = index % len(challenges)

    challenge_data = challenges[selected_index]
    if not isinstance(challenge_data, dict):
        raise ValueError("captcha challenge must be a JSON object")
    return CaptchaChallenge.from_mapping(challenge_data, resolved_config.parent)


class ImageCaptcha:
    """Show a short-lived, frameless CAPTCHA that cannot be normally dismissed."""

    def __init__(
        self,
        challenge: CaptchaChallenge,
        *,
        window_title: str = "Padikula, Padippikula",
    ) -> None:
        self.challenge = challenge
        self.window_title = window_title
        self.completed = False
        self.expired = False
        self._root: tk.Tk | None = None
        self._answer_entry: tk.Entry | None = None
        self._timer_label: tk.Label | None = None
        self._status_label: tk.Label | None = None
        self._remaining = challenge.time_limit
        self._image: tk.PhotoImage | None = None
        self._focus_job: str | None = None

    def show(self) -> bool:
        """Display the CAPTCHA and return whether the answer was correct."""
        if self._root is not None:
            raise RuntimeError("CAPTCHA is already running")

        root = tk.Tk()
        self._root = root
        root.title(self.window_title)
        root.configure(background="#171717")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.overrideredirect(True)
        root.protocol("WM_DELETE_WINDOW", self._ignore_close)
        root.bind("<Escape>", self._ignore_close)
        root.bind("<Alt-F4>", self._ignore_close)
        root.bind("<FocusOut>", self._restore_focus)
        root.bind("<Return>", self._submit)

        self._build_ui(root)
        self._center_window(root, width=660, height=620)
        root.after_idle(self._restore_focus)
        root.after(1000, self._tick)
        root.mainloop()
        self._root = None
        return self.completed

    def close(self) -> None:
        """Close the CAPTCHA from application code without marking it complete."""
        if self._root is not None:
            self._root.destroy()
            self._root = None

    def _build_ui(self, root: tk.Tk) -> None:
        background = "#0d1715"
        panel = "#172522"
        muted = "#a7b8b2"
        accent = "#f4c95d"
        bright = "#f5f7f4"
        frame = tk.Frame(
            root,
            background=background,
            padx=34,
            pady=30,
            highlightbackground="#42645a",
            highlightcolor="#f4c95d",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, background=background)
        header.pack(fill="x")
        tk.Label(
            header,
            text="  OFFENSE 02  ",
            background="#263e37",
            foreground=accent,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=5,
        ).pack(side="left")
        tk.Label(
            header,
            text="PADIKULA, PADIPPIKULA",
            background=background,
            foreground=muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(12, 0))
        self._timer_label = tk.Label(
            header,
            text=self._timer_text(),
            background="#3a3020",
            foreground=accent,
            font=("Consolas", 11, "bold"),
            padx=12,
            pady=6,
        )
        self._timer_label.pack(side="right")

        tk.Label(
            frame,
            text="Your study attempt is blocked.",
            background=background,
            foreground=bright,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", pady=(26, 4))
        tk.Label(
            frame,
            text="Complete this completely unnecessary challenge to continue.",
            background=background,
            foreground=muted,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 18))

        image_panel = tk.Frame(
            frame,
            background=panel,
            padx=18,
            pady=16,
            highlightbackground="#315047",
            highlightthickness=2,
        )
        image_panel.pack(fill="both", expand=True, ipady=5)
        tk.Label(
            image_panel,
            text="CHALLENGE IMAGE",
            background=panel,
            foreground=accent,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        if self.challenge.image is not None:
            try:
                self._image = tk.PhotoImage(file=str(self.challenge.image))
                image_width = self._image.width()
                image_height = self._image.height()
                scale = max((image_width + 479) // 480, (image_height + 230) // 230, 1)
                if scale > 1:
                    self._image = self._image.subsample(scale, scale)
                tk.Label(image_panel, image=self._image, background=panel).pack()
            except (tk.TclError, OSError) as error:
                LOGGER.warning("Unable to load CAPTCHA image %s: %s", self.challenge.image, error)
                self._show_image_error(image_panel)
        else:
            self._show_image_error(image_panel, message="No CAPTCHA image configured")
        tk.Label(
            image_panel,
            text=self.challenge.prompt,
            background=panel,
            foreground=muted,
            font=("Segoe UI", 9, "italic"),
        ).pack(anchor="w", pady=(10, 0))

        answer_card = tk.Frame(
            frame,
            background="#203b34",
            padx=18,
            pady=16,
            highlightbackground="#f4c95d",
            highlightthickness=2,
        )
        answer_card.pack(fill="x", pady=(18, 0))
        tk.Label(
            answer_card,
            text="YOUR ANSWER  •  TYPE HERE",
            background="#203b34",
            foreground="#f4c95d",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            answer_card,
            text="The answer field is ready. Type your answer and press Enter.",
            background="#203b34",
            foreground=muted,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))
        input_row = tk.Frame(answer_card, background="#203b34")
        input_row.pack(fill="x")
        self._answer_entry = tk.Entry(
            input_row,
            relief="solid",
            borderwidth=1,
            background="#f1f5f2",
            foreground="#17211f",
            insertbackground="#17211f",
            font=("Segoe UI", 15, "bold"),
        )
        self._answer_entry.pack(side="left", fill="x", expand=True, ipady=11)
        self._answer_entry.focus_set()
        self._status_label = tk.Label(
            answer_card,
            text="",
            background="#203b34",
            foreground="#d98f8f",
            font=("Segoe UI", 9, "bold"),
        )
        self._status_label.pack(anchor="w", pady=(7, 0))
        tk.Button(
            input_row,
            text="SUBMIT  >",
            command=self._submit,
            background=accent,
            activebackground="#ffe6a0",
            foreground="#17211f",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=12,
        ).pack(side="right", padx=(10, 0))

    @staticmethod
    def _show_image_error(frame: tk.Frame, message: str = "CAPTCHA image unavailable") -> None:
        tk.Label(
            frame,
            text=message,
            width=58,
            height=5,
            background="#2a2a2a",
            foreground="#d98f8f",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

    def _submit(self, _event: tk.Event | None = None) -> str:
        if self._answer_entry is None:
            return "break"
        answer = self._answer_entry.get().strip().casefold()
        if answer == self.challenge.answer.casefold():
            self.completed = True
            self._destroy()
        else:
            self._answer_entry.delete(0, tk.END)
        return "break"

    def _tick(self) -> None:
        if self._root is None or self.completed:
            return
        self._remaining -= 1
        if self._remaining <= 0:
            self.expired = True
            if self._timer_label is not None:
                self._timer_label.configure(text="TIME EXPIRED")
            if self._status_label is not None:
                self._status_label.configure(text="Your study attempt has expired.")
            if self._root is not None:
                self._root.after(1200, self._destroy)
            return
        if self._timer_label is not None:
            self._timer_label.configure(text=self._timer_text())
        self._root.after(1000, self._tick)

    def _timer_text(self) -> str:
        return f"TIME REMAINING: 00:{self._remaining:02d}"

    def _destroy(self) -> None:
        if self._root is not None:
            self._root.destroy()
            self._root = None

    @staticmethod
    def _center_window(root: tk.Tk, *, width: int, height: int) -> None:
        root.update_idletasks()
        x = max((root.winfo_screenwidth() - width) // 2, 0)
        y = max((root.winfo_screenheight() - height) // 2, 0)
        root.geometry(f"{width}x{height}+{x}+{y}")

    @staticmethod
    def _ignore_close(_event: tk.Event | None = None) -> str:
        return "break"

    def _restore_focus(self, _event: tk.Event | None = None) -> str:
        if self._root is not None:
            if self._focus_job is not None:
                self._root.after_cancel(self._focus_job)
            self._focus_job = self._root.after(80, self._apply_focus)
        return "break"

    def _apply_focus(self) -> None:
        self._focus_job = None
        if self._root is None:
            return
        self._root.attributes("-topmost", True)
        self._root.lift()
        self._root.focus_force()
        if self._answer_entry is not None:
            self._answer_entry.focus_set()


def run_self_test(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    """Run the standalone CAPTCHA test with the configured first challenge."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    challenge = load_challenge(config_path)
    result = ImageCaptcha(challenge, window_title="Padikula, Padippikula CAPTCHA self-test").show()
    if result:
        print("CAPTCHA self-test: solved")
    else:
        print("CAPTCHA self-test: expired or closed by application")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the standalone image CAPTCHA test.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    run_self_test(args.config)
