from __future__ import annotations

import logging
import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None


@dataclass
class RuntimeStats:
    attempts_blocked: int = 0
    pdf_attempts: int = 0
    website_attempts: int = 0
    youtube_attempts: int = 0
    captchas_shown: int = 0
    notifications_sent: int = 0
    distractions_available: int = 0
    current_offense: int = 0


class TrayController:
    def __init__(
        self,
        stats: RuntimeStats,
        *,
        on_test_notification: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self.stats = stats
        self.on_test_notification = on_test_notification
        self.on_exit = on_exit
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if pystray is None or Image is None or ImageDraw is None:
            LOGGER.warning("System tray unavailable; install pystray and Pillow")
            return
        self._thread = threading.Thread(target=self._run, name="tray-icon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    def _run(self) -> None:
        image = Image.new("RGB", (64, 64), "#10201d")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, 58, 58), radius=12, fill="#f4c95d")
        draw.text((18, 20), "P", fill="#10201d")
        menu = pystray.Menu(
            pystray.MenuItem("View statistics", self._show_statistics),
            pystray.MenuItem("Test notification", self._test_notification),
            pystray.MenuItem("Exit", self._exit),
        )
        self._icon = pystray.Icon("Padikula_Padippikula", image, "Padikula, Padippikula", menu)
        self._icon.run()

    def _show_statistics(self, _icon: object, _item: object) -> None:
        threading.Thread(target=self._statistics_window, name="statistics-window", daemon=True).start()

    def _statistics_window(self) -> None:
        root = tk.Tk()
        root.title("Padikula, Padippikula statistics")
        root.configure(background="#10201d")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        frame = tk.Frame(root, background="#10201d", padx=28, pady=24)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="PADIKULA, PADIPPIKULA", background="#10201d", foreground="#f4c95d", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(frame, text="Useless intervention report", background="#10201d", foreground="#f1f5f2", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(8, 18))
        values = (
            ("Study attempts blocked", self.stats.attempts_blocked),
            ("PDF attempts", self.stats.pdf_attempts),
            ("Website attempts", self.stats.website_attempts),
            ("YouTube attempts", self.stats.youtube_attempts),
            ("CAPTCHAs shown", self.stats.captchas_shown),
            ("Notifications sent", self.stats.notifications_sent),
            ("Current offense", self.stats.current_offense),
        )
        for label, value in values:
            row = tk.Frame(frame, background="#1d332e", padx=14, pady=8)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=25, anchor="w", background="#1d332e", foreground="#b8c9c2", font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row, text=str(value), width=6, anchor="e", background="#1d332e", foreground="#f4c95d", font=("Consolas", 12, "bold")).pack(side="right")
        tk.Button(frame, text="CLOSE", command=root.destroy, background="#f4c95d", foreground="#10201d", relief="flat", borderwidth=0, padx=18, pady=8).pack(anchor="e", pady=(18, 0))
        root.mainloop()

    def _test_notification(self, _icon: object, _item: object) -> None:
        self.on_test_notification()

    def _exit(self, _icon: object, _item: object) -> None:
        self.on_exit()
        self.stop()