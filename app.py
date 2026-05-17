import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from markitdown import MarkItDown
import os
import threading

# ── palette ──────────────────────────────────────────────────────────────────
BG        = "#1e1e2e"
SURFACE   = "#2a2a3e"
ACCENT    = "#7c6af7"
ACCENT_H  = "#9d8fff"
DROP_IDLE = "#2e2e45"
DROP_HOV  = "#3a3a58"
TEXT      = "#e0e0f0"
SUBTEXT   = "#8888aa"
SUCCESS   = "#4caf82"
ERROR     = "#e05c5c"
BORDER    = "#44445a"

FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("MarkItDown")
        self.geometry("560x620")
        self.minsize(480, 540)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.output_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.queued: list[str] = []
        self.converting = False

        self._build_ui()
        self._center()

    # ── layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self

        # title bar
        header = tk.Frame(root, bg=BG, pady=18)
        header.pack(fill="x", padx=28)
        tk.Label(header, text="MarkItDown", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text="by Microsoft", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(8, 0), pady=(5, 0))

        # drop zone
        self.drop_frame = tk.Frame(root, bg=DROP_IDLE, bd=0,
                                   highlightthickness=2,
                                   highlightbackground=BORDER,
                                   highlightcolor=ACCENT)
        self.drop_frame.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        self.drop_label = tk.Label(
            self.drop_frame,
            text="Arrastra archivos aquí",
            font=("Segoe UI", 14),
            bg=DROP_IDLE, fg=SUBTEXT,
            cursor="hand2",
        )
        self.drop_label.place(relx=0.5, rely=0.38, anchor="center")

        self.drop_sub = tk.Label(
            self.drop_frame,
            text="PDF · DOCX · XLSX · PPTX · HTML · imágenes…",
            font=FONT_SMALL,
            bg=DROP_IDLE, fg=SUBTEXT,
        )
        self.drop_sub.place(relx=0.5, rely=0.50, anchor="center")

        btn_browse = tk.Button(
            self.drop_frame,
            text="  o selecciona archivos  ",
            font=FONT_SMALL,
            bg=SURFACE, fg=TEXT,
            activebackground=ACCENT, activeforeground="white",
            bd=0, padx=14, pady=6, cursor="hand2",
            command=self._browse_files,
        )
        btn_browse.place(relx=0.5, rely=0.65, anchor="center")

        # drag-and-drop bindings
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_frame.dnd_bind("<<DragEnter>>", self._on_drag_enter)
        self.drop_frame.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        for w in (self.drop_label, self.drop_sub):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", self._on_drop)
            w.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            w.dnd_bind("<<DragLeave>>", self._on_drag_leave)

        # output folder row
        folder_row = tk.Frame(root, bg=BG)
        folder_row.pack(fill="x", padx=28, pady=(0, 10))

        tk.Label(folder_row, text="Guardar en:", font=FONT_BODY,
                 bg=BG, fg=SUBTEXT).pack(side="left")

        self.folder_entry = tk.Entry(
            folder_row, textvariable=self.output_dir,
            font=FONT_MONO, bg=SURFACE, fg=TEXT,
            insertbackground=TEXT, bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=5)

        tk.Button(
            folder_row, text="…", font=FONT_BODY,
            bg=SURFACE, fg=TEXT,
            activebackground=ACCENT, activeforeground="white",
            bd=0, padx=10, pady=4, cursor="hand2",
            command=self._browse_folder,
        ).pack(side="left")

        # log area
        log_frame = tk.Frame(root, bg=BG)
        log_frame.pack(fill="x", padx=28, pady=(0, 14))

        tk.Label(log_frame, text="Registro", font=FONT_SMALL,
                 bg=BG, fg=SUBTEXT).pack(anchor="w")

        self.log_text = tk.Text(
            log_frame, height=7, font=FONT_MONO,
            bg=SURFACE, fg=TEXT, bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled", wrap="word",
            padx=8, pady=6,
        )
        self.log_text.pack(fill="x")
        self.log_text.tag_config("ok",  foreground=SUCCESS)
        self.log_text.tag_config("err", foreground=ERROR)
        self.log_text.tag_config("dim", foreground=SUBTEXT)

        # convert button
        self.btn_convert = tk.Button(
            root, text="Convertir",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            bd=0, pady=10, cursor="hand2",
            command=self._start_conversion,
        )
        self.btn_convert.pack(fill="x", padx=28, pady=(0, 22))

    # ── drag-and-drop ─────────────────────────────────────────────────────────

    def _parse_paths(self, data: str) -> list[str]:
        """Handle {path with spaces} or plain paths from DnD event."""
        import re
        paths = re.findall(r'\{([^}]+)\}|(\S+)', data)
        return [a or b for a, b in paths]

    def _on_drag_enter(self, event):
        self.drop_frame.configure(bg=DROP_HOV, highlightbackground=ACCENT)
        for w in (self.drop_label, self.drop_sub):
            w.configure(bg=DROP_HOV)

    def _on_drag_leave(self, event):
        self.drop_frame.configure(bg=DROP_IDLE, highlightbackground=BORDER)
        for w in (self.drop_label, self.drop_sub):
            w.configure(bg=DROP_IDLE)

    def _on_drop(self, event):
        self._on_drag_leave(event)
        paths = self._parse_paths(event.data)
        self._add_files(paths)

    # ── file selection ────────────────────────────────────────────────────────

    def _browse_files(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar archivos",
            filetypes=[
                ("Todos los soportados",
                 "*.pdf *.docx *.xlsx *.xls *.pptx *.ppt "
                 "*.html *.htm *.txt *.csv *.json *.xml "
                 "*.jpg *.jpeg *.png *.gif *.bmp *.webp "
                 "*.mp3 *.wav *.zip"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if files:
            self._add_files(list(files))

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            title="Seleccionar carpeta de destino",
            initialdir=self.output_dir.get(),
        )
        if folder:
            self.output_dir.set(folder)

    def _add_files(self, paths: list[str]):
        added = 0
        for p in paths:
            p = p.strip()
            if p and os.path.isfile(p) and p not in self.queued:
                self.queued.append(p)
                added += 1
        if added:
            self._log(f"{added} archivo(s) en cola — total: {len(self.queued)}", "dim")
            self._update_drop_label()

    def _update_drop_label(self):
        n = len(self.queued)
        if n == 0:
            self.drop_label.configure(text="Arrastra archivos aquí")
        else:
            self.drop_label.configure(text=f"{n} archivo(s) en cola")

    # ── conversion ───────────────────────────────────────────────────────────

    def _start_conversion(self):
        if self.converting:
            return
        if not self.queued:
            messagebox.showinfo("Sin archivos",
                                "Arrastra o selecciona archivos primero.")
            return
        out = self.output_dir.get().strip()
        if not os.path.isdir(out):
            messagebox.showerror("Carpeta inválida",
                                 f"La carpeta no existe:\n{out}")
            return
        self.converting = True
        self.btn_convert.configure(text="Convirtiendo…", state="disabled",
                                   bg=SUBTEXT)
        files = list(self.queued)
        self.queued.clear()
        self._update_drop_label()
        threading.Thread(target=self._convert_batch,
                         args=(files, out), daemon=True).start()

    def _convert_batch(self, files: list[str], out_dir: str):
        md = MarkItDown()
        ok = err = 0
        for path in files:
            name = os.path.splitext(os.path.basename(path))[0] + ".md"
            dest = os.path.join(out_dir, name)
            try:
                result = md.convert(path)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                self._log(f"✓  {os.path.basename(path)}  →  {name}", "ok")
                ok += 1
            except Exception as e:
                self._log(f"✗  {os.path.basename(path)}: {e}", "err")
                err += 1

        summary = f"Listo: {ok} convertido(s)"
        if err:
            summary += f", {err} con error"
        self._log(summary, "dim")
        self.after(0, self._reset_button)

    def _reset_button(self):
        self.converting = False
        self.btn_convert.configure(text="Convertir", state="normal", bg=ACCENT)

    # ── log ──────────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = ""):
        def _insert():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _insert)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


if __name__ == "__main__":
    App().mainloop()
