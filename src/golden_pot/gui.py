from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .comparator import compare_directories
from .config import GoldenPotConfig, load_config
from .reporter import write_reports


class GoldenPotApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Golden Pot v0.1 — Folder Comparator")
        self.geometry("840x590")
        self.minsize(720, 500)
        self.base_var = tk.StringVar()
        self.comparison_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "reports"))
        self.config_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready. No files will be modified.")
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Golden Pot", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Compare any two folders safely. Version 0.1 is read-only.",
        ).pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(root)
        form.pack(fill="x")
        self._folder_row(form, 0, "Base folder", self.base_var)
        self._folder_row(form, 1, "Comparison folder", self.comparison_var)
        self._folder_row(form, 2, "Report destination", self.output_var)

        ttk.Label(form, text="Configuration (optional)").grid(
            row=3, column=0, sticky="w", pady=8
        )
        ttk.Entry(form, textvariable=self.config_var).grid(
            row=3, column=1, sticky="ew", padx=10, pady=8
        )
        ttk.Button(form, text="Select file", command=self._select_config).grid(
            row=3, column=2, sticky="ew", pady=8
        )
        form.columnconfigure(1, weight=1)

        self.analyze_button = ttk.Button(
            root, text="Analyze folders", command=self._start_analysis
        )
        self.analyze_button.pack(anchor="w", pady=(18, 10))
        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 10))
        ttk.Label(root, textvariable=self.status_var).pack(anchor="w", pady=(0, 10))
        self.result = tk.Text(root, height=14, wrap="word", state="disabled")
        self.result.pack(fill="both", expand=True)

    def _folder_row(
        self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=10, pady=8
        )
        ttk.Button(
            parent,
            text="Select folder",
            command=lambda: self._select_folder(variable),
        ).grid(row=row, column=2, sticky="ew", pady=8)

    def _select_folder(self, variable: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=variable.get() or None)
        if selected:
            variable.set(selected)

    def _select_config(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select Golden Pot configuration",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self.config_var.set(selected)

    def _start_analysis(self) -> None:
        if not self.base_var.get() or not self.comparison_var.get() or not self.output_var.get():
            messagebox.showwarning("Missing information", "Select all three folders.")
            return
        self.analyze_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set("Analyzing folders...")
        self._set_result("")
        threading.Thread(target=self._analyze_worker, daemon=True).start()
        self.after(100, self._poll_events)

    def _analyze_worker(self) -> None:
        try:
            config = (
                load_config(self.config_var.get())
                if self.config_var.get()
                else GoldenPotConfig()
            )
            report = compare_directories(
                self.base_var.get(), self.comparison_var.get(), config
            )
            paths = write_reports(report, self.output_var.get())
            self.events.put(("success", (report, paths)))
        except Exception as error:
            self.events.put(("error", error))

    def _poll_events(self) -> None:
        try:
            event, payload = self.events.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_events)
            return
        self.progress.stop()
        self.analyze_button.configure(state="normal")
        if event == "error":
            self.status_var.set("Analysis failed.")
            messagebox.showerror("Golden Pot", str(payload))
            return

        report, paths = payload
        summary = report.summary
        keys = ("ADDED", "UNCHANGED", "MODIFIED", "PRESERVED", "PROTECTED", "ERROR", "TOTAL")
        lines = [
            "Analysis completed successfully.",
            "",
            *(f"{key}: {summary[key]}" for key in keys),
            "",
            f"JSON report: {paths[0]}",
            f"Text report: {paths[1]}",
        ]
        self._set_result("\n".join(lines))
        self.status_var.set("Finished. Original folders were not changed.")

    def _set_result(self, text: str) -> None:
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)
        self.result.configure(state="disabled")


def main() -> int:
    app = GoldenPotApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
