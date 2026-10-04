from __future__ import annotations
import queue, math, sys, threading, tkinter as tk
from contextlib import ExitStack
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from .comparator import compare_directories
from .config import GoldenPotConfig, load_config
from .i18n import LANGUAGES, detect_language, translate
from .merger import create_layered_package
from .reporter import write_reports
from .source_adapter import normalized_source

class GoldenPotApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.geometry("900x760"); self.minsize(720,600)
        self.language=detect_language(); self.language_var=tk.StringVar(value=LANGUAGES[self.language])
        self.base_var=tk.StringVar(); self.base_mappings_var=tk.StringVar(); self.comparison_var=tk.StringVar(); self.comparison_mappings_var=tk.StringVar()
        self.output_var=tk.StringVar(value=str(Path.cwd()/"reports")); self.merged_var=tk.StringVar(value=str(Path.cwd()/"GoldenPot-Output")); self.config_var=tk.StringVar(); self.status_var=tk.StringVar(value=self._t("ready"))
        self.events=queue.Queue(); self.app_icon=self.header_logo=self.cloud_image=None; self._animation_generation=0; self._progress_running=False; self._progress_offset=0
        self._load_images(); self._build_ui()
    def _t(self,key): return translate(self.language,key)
    def _load_images(self):
        try:
            self.app_icon=tk.PhotoImage(file=self._asset_path("icon1.png")); self.header_logo=tk.PhotoImage(file=self._asset_path("icon2.png")); self.cloud_image=tk.PhotoImage(file=self._asset_path("cloud.png")); self.iconphoto(True,self.app_icon)
        except (tk.TclError,OSError): self.app_icon=self.header_logo=self.cloud_image=None
    @staticmethod
    def _asset_path(name):
        if getattr(sys,"frozen",False): return str(Path(sys._MEIPASS)/"golden_pot"/"assets"/name)
        return str(Path(__file__).resolve().parent/"assets"/name)
    def _build_ui(self):
        self.title(self._t("title")); self._animation_generation+=1
        if hasattr(self,"root_frame"): self.root_frame.destroy()
        root=self.root_frame=ttk.Frame(self,padding=20); root.pack(fill="both",expand=True)
        header=ttk.Frame(root); header.pack(fill="x",pady=(0,18)); art=tk.Canvas(header,height=112,highlightthickness=0,background="#f0f0f0"); art.pack(side="left",fill="x",expand=True)
        if self.header_logo is not None: art.create_image(55,56,image=self.header_logo)
        art.create_text(112,42,text="Golden Pot",anchor="w",font=("Segoe UI",22,"bold"),fill="#172117"); art.create_text(112,72,text=self._t("subtitle"),anchor="w",font=("Segoe UI",9),fill="#424942")
        self._clouds=[]
        if self.cloud_image is not None:
            for x,y,phase in ((255,24,0),(350,57,11),(455,28,22)): self._clouds.append((art.create_image(x,y,image=self.cloud_image),y,phase))
        self._animate_clouds(art,self._animation_generation)
        language_box=ttk.Frame(header); language_box.pack(side="right",anchor="ne"); ttk.Label(language_box,text=self._t("language")).pack(anchor="e")
        selector=ttk.Combobox(language_box,textvariable=self.language_var,values=tuple(LANGUAGES.values()),state="readonly",width=13); selector.pack(anchor="e",pady=(4,0)); selector.bind("<<ComboboxSelected>>",self._change_language)
        form=ttk.Frame(root); form.pack(fill="x")
        rows=(("base_texture_folder",self.base_var),("base_mappings_folder",self.base_mappings_var),("comparison_texture_folder",self.comparison_var),("comparison_mappings_folder",self.comparison_mappings_var),("report_destination",self.output_var),("merged_destination",self.merged_var))
        for index,(label,var) in enumerate(rows): self._folder_row(form,index,self._t(label),var)
        ttk.Label(form,text=self._t("configuration")).grid(row=6,column=0,sticky="w",pady=8); ttk.Entry(form,textvariable=self.config_var).grid(row=6,column=1,sticky="ew",padx=10,pady=8); ttk.Button(form,text=self._t("select_file"),command=self._select_config).grid(row=6,column=2,sticky="ew",pady=8); form.columnconfigure(1,weight=1)
        actions=ttk.Frame(root); actions.pack(anchor="w",pady=(18,10)); self.analyze_button=ttk.Button(actions,text=self._t("analyze"),command=self._start_analysis); self.analyze_button.pack(side="left"); self.merge_button=ttk.Button(actions,text=self._t("merge"),command=self._start_merge); self.merge_button.pack(side="left",padx=(10,0))
        self.progress=tk.Canvas(root,height=18,highlightthickness=1,highlightbackground="#aeb8ae",background="#f4f4f4"); self.progress.pack(fill="x",pady=(0,10)); ttk.Label(root,textvariable=self.status_var).pack(anchor="w",pady=(0,10)); self.result=tk.Text(root,height=10,wrap="word",state="disabled"); self.result.pack(fill="both",expand=True)
    def _folder_row(self,parent,row,label,variable):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=7); ttk.Entry(parent,textvariable=variable).grid(row=row,column=1,sticky="ew",padx=10,pady=7); ttk.Button(parent,text=self._t("select_folder"),command=lambda:self._select_folder(variable)).grid(row=row,column=2,sticky="ew",pady=7)
    def _select_folder(self,variable):
        selected=filedialog.askdirectory(initialdir=variable.get() or None)
        if selected: variable.set(selected)
    def _select_config(self):
        selected=filedialog.askopenfilename(title=self._t("select_config"),filetypes=((self._t("json_files"),"*.json"),(self._t("all_files"),"*.*")))
        if selected: self.config_var.set(selected)
    def _start_analysis(self):
        if not self.base_var.get() or not self.comparison_var.get() or not self.output_var.get(): messagebox.showwarning(self._t("missing_title"),self._t("missing_message")); return
        self._start_worker(False)
    def _start_merge(self):
        if not all((self.base_var.get(),self.base_mappings_var.get(),self.comparison_var.get(),self.comparison_mappings_var.get(),self.output_var.get(),self.merged_var.get())): messagebox.showwarning(self._t("missing_title"),self._t("missing_merge_message")); return
        if not messagebox.askyesno(self._t("merge_confirm_title"),self._t("merge_confirm_message")): return
        self._start_worker(True)
    def _start_worker(self,merge):
        self.analyze_button.configure(state="disabled"); self.merge_button.configure(state="disabled"); self._start_progress(); self.status_var.set(self._t("merging") if merge else self._t("analyzing")); self._set_result(""); threading.Thread(target=self._analyze_worker,args=(merge,),daemon=True).start(); self.after(100,self._poll_events)
    def _analyze_worker(self,merge=False):
        try:
            config=load_config(self.config_var.get()) if self.config_var.get() else GoldenPotConfig()
            with ExitStack() as stack:
                base=stack.enter_context(normalized_source(self.base_var.get())); comparison=stack.enter_context(normalized_source(self.comparison_var.get())); report=compare_directories(base,comparison,config)
                merge_result=create_layered_package(report,self.base_mappings_var.get(),self.comparison_mappings_var.get(),self.merged_var.get()) if merge else None
            report.base_folder=self.base_var.get(); report.comparison_folder=self.comparison_var.get(); paths=write_reports(report,self.output_var.get()); self.events.put(("success",(report,paths,merge_result)))
        except Exception as error: self.events.put(("error",error))
    def _poll_events(self):
        try: event,payload=self.events.get_nowait()
        except queue.Empty: self.after(100,self._poll_events); return
        self._stop_progress(); self.analyze_button.configure(state="normal"); self.merge_button.configure(state="normal")
        if event=="error": self.status_var.set(self._t("failed")); messagebox.showerror("Golden Pot",str(payload)); return
        report,paths,merge_result=payload; summary=report.summary; keys=("ADDED","UNCHANGED","MODIFIED","PRESERVED","PROTECTED","ERROR","TOTAL"); lines=[self._t("completed"),"",*(f"{self._t(k)}: {summary[k]}" for k in keys),"",f"{self._t('json_report')}: {paths[0]}",f"{self._t('text_report')}: {paths[1]}"]
        if merge_result is not None: lines.extend(["",self._t("merge_completed"),f"{self._t('merged_folder')}: {merge_result.output_folder}",f"{self._t('added_to_output')}: {merge_result.texture.added_from_comparison}",f"{self._t('updated_in_output')}: {merge_result.texture.updated_from_comparison}",f"{self._t('preserved_in_output')}: {merge_result.texture.copied_from_base}",f"{self._t('preserved_mappings')}: {merge_result.preserved_mappings}",f"{self._t('added_mappings')}: {merge_result.added_mappings}",f"{self._t('merged_mappings')}: {merge_result.merged_mapping_files}",f"{self._t('rebuilt_pack')}: {merge_result.rebuilt_pack}",f"{self._t('mapping_warnings')}: {len(merge_result.warnings)}"])
        self._set_result("
".join(lines)); self.status_var.set(self._t("merge_finished") if merge_result else self._t("finished"))
    def _change_language(self,_event=None):
        selected=self.language_var.get(); self.language=next(code for code,label in LANGUAGES.items() if label==selected); self.status_var.set(self._t("ready")); self._build_ui()
    def _set_result(self,text): self.result.configure(state="normal"); self.result.delete("1.0","end"); self.result.insert("1.0",text); self.result.configure(state="disabled")
    def _animate_clouds(self,canvas,generation,tick=0):
        if generation!=self._animation_generation or not canvas.winfo_exists(): return
        for cloud_id,base_y,phase in self._clouds:
            x,_=canvas.coords(cloud_id); canvas.coords(cloud_id,x,base_y+math.sin((tick+phase)/10)*5)
        self.after(70,self._animate_clouds,canvas,generation,tick+1)
    def _start_progress(self): self._progress_running=True; self._progress_offset=0; self._animate_progress()
    def _stop_progress(self): self._progress_running=False; self.progress.delete("all")
    def _animate_progress(self):
        if not self._progress_running: return
        self.progress.delete("all"); width=max(self.progress.winfo_width(),1); height=max(self.progress.winfo_height(),18); colors=("#ef3340","#ff8c1a","#ffd43b","#38b000","#2693ff","#6f42c1"); stripe_width=52; start=self._progress_offset-stripe_width; stripe=0
        while start<width: self.progress.create_rectangle(start,0,start+stripe_width+1,height,fill=colors[stripe%len(colors)],outline=""); start+=stripe_width; stripe+=1
        self._progress_offset=(self._progress_offset+7)%stripe_width; self.after(55,self._animate_progress)

def main():
    app=GoldenPotApp(); app.mainloop(); return 0
if __name__=="__main__": raise SystemExit(main())
from __future__ import annotations

import queue
import math
import sys
import threading
import tkinter as tk
from contextlib import ExitStack
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .comparator import compare_directories
from .config import GoldenPotConfig, load_config
from .i18n import LANGUAGES, detect_language, translate
from .merger import create_merged_folder
from .reporter import write_reports
from .source_adapter import normalized_source


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
        self.app_icon: tk.PhotoImage | None = None
        self.header_logo: tk.PhotoImage | None = None
        self.cloud_image: tk.PhotoImage | None = None
        self._animation_generation = 0
        self._progress_running = False
        self._progress_offset = 0
        self._load_images()
        self._build_ui()

    def _t(self, key: str) -> str:
        return translate(self.language, key)

    def _load_images(self) -> None:
        try:
            self.app_icon = tk.PhotoImage(file=self._asset_path("icon1.png"))
            self.header_logo = tk.PhotoImage(file=self._asset_path("icon2.png"))
            self.cloud_image = tk.PhotoImage(file=self._asset_path("cloud.png"))
            self.iconphoto(True, self.app_icon)
        except (tk.TclError, OSError):
            self.app_icon = None
            self.header_logo = None
            self.cloud_image = None

    @staticmethod
    def _asset_path(name: str) -> str:
        if getattr(sys, "frozen", False):
            return str(Path(sys._MEIPASS) / "golden_pot" / "assets" / name)
        return str(Path(__file__).resolve().parent / "assets" / name)

    def _build_ui(self) -> None:
        self.title(self._t("title"))
        self._animation_generation += 1
        if hasattr(self, "root_frame"):
            self.root_frame.destroy()
        root = self.root_frame = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 18))
        art = tk.Canvas(header, height=112, highlightthickness=0, background="#f0f0f0")
        art.pack(side="left", fill="x", expand=True)
        if self.header_logo is not None:
            art.create_image(55, 56, image=self.header_logo)
        art.create_text(112, 42, text="Golden Pot", anchor="w", font=("Segoe UI", 22, "bold"), fill="#172117")
        art.create_text(112, 72, text=self._t("subtitle"), anchor="w", font=("Segoe UI", 9), fill="#424942")
        cloud_specs = ((255, 24, 0), (350, 57, 11), (455, 28, 22))
        self._clouds: list[tuple[int, float, int]] = []
        if self.cloud_image is not None:
            for x, y, phase in cloud_specs:
                cloud_id = art.create_image(x, y, image=self.cloud_image)
                self._clouds.append((cloud_id, y, phase))
        self._animate_clouds(art, self._animation_generation)
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
        self.progress = tk.Canvas(root, height=18, highlightthickness=1, highlightbackground="#aeb8ae", background="#f4f4f4")
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
        self._start_progress()
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
            with ExitStack() as stack:
                base = stack.enter_context(normalized_source(self.base_var.get()))
                comparison = stack.enter_context(normalized_source(self.comparison_var.get()))
                report = compare_directories(base, comparison, config)
                merge_result = create_merged_folder(report, self.merged_var.get()) if merge else None
            report.base_folder = self.base_var.get()
            report.comparison_folder = self.comparison_var.get()
            paths = write_reports(report, self.output_var.get())
            self.events.put(("success", (report, paths, merge_result)))
        except Exception as error:
            self.events.put(("error", error))

    def _poll_events(self) -> None:
        try:
            event, payload = self.events.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_events)
            return
        self._stop_progress()
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
                f"{self._t('merged_mappings')}: {merge_result.merged_json_files}",
                f"{self._t('rebuilt_pack')}: {merge_result.rebuilt_pack}",
                f"{self._t('mapping_warnings')}: {len(merge_result.warnings)}",
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

    def _animate_clouds(self, canvas: tk.Canvas, generation: int, tick: int = 0) -> None:
        if generation != self._animation_generation or not canvas.winfo_exists():
            return
        for cloud_id, base_y, phase in self._clouds:
            x, _ = canvas.coords(cloud_id)
            canvas.coords(cloud_id, x, base_y + math.sin((tick + phase) / 10) * 5)
        self.after(70, self._animate_clouds, canvas, generation, tick + 1)

    def _start_progress(self) -> None:
        self._progress_running = True
        self._progress_offset = 0
        self._animate_progress()

    def _stop_progress(self) -> None:
        self._progress_running = False
        self.progress.delete("all")

    def _animate_progress(self) -> None:
        if not self._progress_running:
            return
        self.progress.delete("all")
        width = max(self.progress.winfo_width(), 1)
        height = max(self.progress.winfo_height(), 18)
        colors = ("#ef3340", "#ff8c1a", "#ffd43b", "#38b000", "#2693ff", "#6f42c1")
        stripe_width = 52
        start = self._progress_offset - stripe_width
        stripe = 0
        while start < width:
            self.progress.create_rectangle(start, 0, start + stripe_width + 1, height, fill=colors[stripe % len(colors)], outline="")
            start += stripe_width
            stripe += 1
        self._progress_offset = (self._progress_offset + 7) % stripe_width
        self.after(55, self._animate_progress)


def main() -> int:
    app = GoldenPotApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
