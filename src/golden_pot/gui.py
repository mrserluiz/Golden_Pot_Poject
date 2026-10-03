from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .comparator import compare_directories
from .branding import LOGO_PNG_BASE64
from .config import GoldenPotConfig, load_config
from .i18n import LANGUAGES, detect_language, translate
from .merger import create_merged_folder
from .reporter import write_reports


class GoldenPotApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("900x700")
        self.minsize(720, 500)
        self.language = detect_language()
        self.language_var = tk.StringVar(value=LANGUAGES[self.language])
        self.base_var = tk.StringVar()
        self.comparison_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "reports"))
        self.merged_var = tk.StringVar(value=str(Path.cwd() / "GoldenPot-UpdatedTexture"))
        self.config_var = tk.StringVar()
        self.status_var = tk.StringVar(value=self._t("ready"))
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.logo_image: tk.PhotoImage | None = None
        self.header_logo: tk.PhotoImage | None = None
        self._load_images()
        self._build_ui()

    def _t(self, key: str) -> str:
        return translate(self.language, key)

    def _load_images(self) -> None:
        try:
            self.logo_image = tk.PhotoImage(data=LOGO_PNG_BASE64)
            self.iconphoto(True, self.logo_image)
            self.header_logo = self.logo_image
        except tk.TclError:
            self.logo_image = None
            self.header_logo = None

    def _build_ui(self) -> None:
        self.title(self._t("title"))
        if hasattr(self, "root_frame"):
            self.root_frame.destroy()
        root = self.root_frame = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 18))
        if self.header_logo is not None:
            ttk.Label(header, image=self.header_logo).pack(side="left", padx=(0, 14))
        heading = ttk.Frame(header)
        heading.pack(side="left", fill="x", expand=True)
        ttk.Label(heading, text="Golden Pot", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(heading, text=self._t("subtitle")).pack(anchor="w")
        language_box = ttk.Frame(header)
        language_box.pack(side="right", anchor="ne")
        ttk.Label(language_box, text=self._t("language")).pack(anchor="e")
        selector = ttk.Combobox(
            language_box, textvariable=self.language_var,
            values=tuple(LANGUAGES.values()), state="readonly", width=13,
        )
        selector.pack(anchor="e", pady=(4, 0))
        selector.bind("<<ComboboxSelected>>", self._change_language)

        form = ttk.Frame(root)
        form.pack(fill="x")
        self._folder_row(form, 0, self._t("base_folder"), self.base_var)
        self._folder_row(form, 1, self._t("comparison_folder"), self.comparison_var)
        self._folder_row(form, 2, self._t("report_destination"), self.output_var)
        self._folder_row(form, 3, self._t("merged_destination"), self.merged_var)

        ttk.Label(form, text=self._t("configuration")).grid(
            row=4, column=0, sticky="w", pady=8
        )
        ttk.Entry(form, textvariable=self.config_var).grid(
            row=4, column=1, sticky="ew", padx=10, pady=8
        )
        ttk.Button(form, text=self._t("select_file"), command=self._select_config).grid(
            row=4, column=2, sticky="ew", pady=8
        )
        form.columnconfigure(1, weight=1)

        actions = ttk.Frame(root)
        actions.pack(anchor="w", pady=(18, 10))
        self.analyze_button = ttk.Button(actions, text=self._t("analyze"), command=self._start_analysis)
        self.analyze_button.pack(side="left")
        self.merge_button = ttk.Button(actions, text=self._t("merge"), command=self._start_merge)
        self.merge_button.pack(side="left", padx=(10, 0))
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
            text=self._t("select_folder"),
            command=lambda: self._select_folder(variable),
        ).grid(row=row, column=2, sticky="ew", pady=8)

    def _select_folder(self, variable: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=variable.get() or None)
        if selected:
            variable.set(selected)

    def _select_config(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._t("select_config"),
            filetypes=((self._t("json_files"), "*.json"), (self._t("all_files"), "*.*")),
        )
        if selected:
            self.config_var.set(selected)

    def _start_analysis(self) -> None:
        if not self.base_var.get() or not self.comparison_var.get() or not self.output_var.get():
            messagebox.showwarning(self._t("missing_title"), self._t("missing_message"))
            return
        self._start_worker(False)

    def _start_merge(self) -> None:
        if not all((self.base_var.get(), self.comparison_var.get(), self.output_var.get(), self.merged_var.get())):
            messagebox.showwarning(self._t("missing_title"), self._t("missing_merge_message"))
            return
        if not messagebox.askyesno(self._t("merge_confirm_title"), self._t("merge_confirm_message")):
            return
        self._start_worker(True)

    def _start_worker(self, merge: bool) -> None:
        self.analyze_button.configure(state="disabled")
        self.merge_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set(self._t("merging") if merge else self._t("analyzing"))
        self._set_result("")
        threading.Thread(target=self._analyze_worker, args=(merge,), daemon=True).start()
        self.after(100, self._poll_events)

    def _analyze_worker(self, merge: bool = False) -> None:
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
            merge_result = create_merged_folder(report, self.merged_var.get()) if merge else None
            self.events.put(("success", (report, paths, merge_result)))
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
        self.merge_button.configure(state="normal")
        if event == "error":
            self.status_var.set(self._t("failed"))
            messagebox.showerror("Golden Pot", str(payload))
            return

        report, paths, merge_result = payload
        summary = report.summary
        keys = ("ADDED", "UNCHANGED", "MODIFIED", "PRESERVED", "PROTECTED", "ERROR", "TOTAL")
        lines = [
            self._t("completed"),
            "",
            *(f"{self._t(key)}: {summary[key]}" for key in keys),
            "",
            f"{self._t('json_report')}: {paths[0]}",
            f"{self._t('text_report')}: {paths[1]}",
        ]
        if merge_result is not None:
            lines.extend([
                "", self._t("merge_completed"),
                f"{self._t('merged_folder')}: {merge_result.output_folder}",
                f"{self._t('added_to_output')}: {merge_result.added_from_comparison}",
                f"{self._t('updated_in_output')}: {merge_result.updated_from_comparison}",
                f"{self._t('preserved_in_output')}: {merge_result.copied_from_base}",
            ])
        self._set_result("\n".join(lines))
        self.status_var.set(self._t("merge_finished") if merge_result else self._t("finished"))

    def _change_language(self, _event: object = None) -> None:
        selected = self.language_var.get()
        self.language = next(code for code, label in LANGUAGES.items() if label == selected)
        self.status_var.set(self._t("ready"))
        self._build_ui()

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
