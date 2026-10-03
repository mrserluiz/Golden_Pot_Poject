from __future__ import annotations
import queue, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from .branding import LOGO_PNG_BASE64
from .comparator import compare_directories
from .config import GoldenPotConfig, load_config
from .i18n import LANGUAGES, detect_language, translate
from .reporter import write_reports

class GoldenPotApp(tk.Tk):
 def __init__(self):
  super().__init__(); self.geometry("900x650"); self.minsize(720,500)
  self.language=detect_language(); self.language_var=tk.StringVar(value=LANGUAGES[self.language])
  self.base_var=tk.StringVar(); self.comparison_var=tk.StringVar(); self.output_var=tk.StringVar(value=str(Path.cwd()/"reports")); self.config_var=tk.StringVar(); self.status_var=tk.StringVar(value=self._t("ready")); self.events=queue.Queue(); self.logo_image=None
  try: self.logo_image=tk.PhotoImage(data=LOGO_PNG_BASE64); self.iconphoto(True,self.logo_image)
  except tk.TclError: pass
  self._build_ui()
 def _t(self,key): return translate(self.language,key)
 def _build_ui(self):
  self.title(self._t("title"))
  if hasattr(self,"root_frame"): self.root_frame.destroy()
  root=self.root_frame=ttk.Frame(self,padding=20); root.pack(fill="both",expand=True)
  header=ttk.Frame(root); header.pack(fill="x",pady=(0,18))
  if self.logo_image: ttk.Label(header,image=self.logo_image).pack(side="left",padx=(0,14))
  heading=ttk.Frame(header); heading.pack(side="left",fill="x",expand=True); ttk.Label(heading,text="Golden Pot",font=("Segoe UI",22,"bold")).pack(anchor="w"); ttk.Label(heading,text=self._t("subtitle")).pack(anchor="w")
  box=ttk.Frame(header); box.pack(side="right",anchor="ne"); ttk.Label(box,text=self._t("language")).pack(anchor="e")
  selector=ttk.Combobox(box,textvariable=self.language_var,values=tuple(LANGUAGES.values()),state="readonly",width=13); selector.pack(anchor="e",pady=(4,0)); selector.bind("<<ComboboxSelected>>",self._change_language)
  form=ttk.Frame(root); form.pack(fill="x"); self._folder_row(form,0,self._t("base_folder"),self.base_var); self._folder_row(form,1,self._t("comparison_folder"),self.comparison_var); self._folder_row(form,2,self._t("report_destination"),self.output_var)
  ttk.Label(form,text=self._t("configuration")).grid(row=3,column=0,sticky="w",pady=8); ttk.Entry(form,textvariable=self.config_var).grid(row=3,column=1,sticky="ew",padx=10,pady=8); ttk.Button(form,text=self._t("select_file"),command=self._select_config).grid(row=3,column=2,sticky="ew",pady=8); form.columnconfigure(1,weight=1)
  self.analyze_button=ttk.Button(root,text=self._t("analyze"),command=self._start_analysis); self.analyze_button.pack(anchor="w",pady=(18,10)); self.progress=ttk.Progressbar(root,mode="indeterminate"); self.progress.pack(fill="x",pady=(0,10)); ttk.Label(root,textvariable=self.status_var).pack(anchor="w",pady=(0,10)); self.result=tk.Text(root,height=14,wrap="word",state="disabled"); self.result.pack(fill="both",expand=True)
 def _folder_row(self,parent,row,label,variable):
  ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=8); ttk.Entry(parent,textvariable=variable).grid(row=row,column=1,sticky="ew",padx=10,pady=8); ttk.Button(parent,text=self._t("select_folder"),command=lambda:self._select_folder(variable)).grid(row=row,column=2,sticky="ew",pady=8)
 def _select_folder(self,variable):
  selected=filedialog.askdirectory(initialdir=variable.get() or None)
  if selected: variable.set(selected)
 def _select_config(self):
  selected=filedialog.askopenfilename(title=self._t("select_config"),filetypes=((self._t("json_files"),"*.json"),(self._t("all_files"),"*.*")))
  if selected: self.config_var.set(selected)
 def _start_analysis(self):
  if not self.base_var.get() or not self.comparison_var.get() or not self.output_var.get(): messagebox.showwarning(self._t("missing_title"),self._t("missing_message")); return
  self.analyze_button.configure(state="disabled"); self.progress.start(10); self.status_var.set(self._t("analyzing")); self._set_result(""); threading.Thread(target=self._analyze_worker,daemon=True).start(); self.after(100,self._poll_events)
 def _analyze_worker(self):
  try:
   config=load_config(self.config_var.get()) if self.config_var.get() else GoldenPotConfig(); report=compare_directories(self.base_var.get(),self.comparison_var.get(),config); self.events.put(("success",(report,write_reports(report,self.output_var.get()))))
  except Exception as error: self.events.put(("error",error))
 def _poll_events(self):
  try: event,payload=self.events.get_nowait()
  except queue.Empty: self.after(100,self._poll_events); return
  self.progress.stop(); self.analyze_button.configure(state="normal")
  if event=="error": self.status_var.set(self._t("failed")); messagebox.showerror("Golden Pot",str(payload)); return
  report,paths=payload; keys=("ADDED","UNCHANGED","MODIFIED","PRESERVED","PROTECTED","ERROR","TOTAL"); lines=[self._t("completed"),"",*(f"{self._t(k)}: {report.summary[k]}" for k in keys),"",f"{self._t('json_report')}: {paths[0]}",f"{self._t('text_report')}: {paths[1]}"]; self._set_result("\n".join(lines)); self.status_var.set(self._t("finished"))
 def _change_language(self,_event=None):
  self.language=next(c for c,l in LANGUAGES.items() if l==self.language_var.get()); self.status_var.set(self._t("ready")); self._build_ui()
 def _set_result(self,text):
  self.result.configure(state="normal"); self.result.delete("1.0","end"); self.result.insert("1.0",text); self.result.configure(state="disabled")

def main():
 app=GoldenPotApp(); app.mainloop(); return 0
if __name__=="__main__": raise SystemExit(main())
