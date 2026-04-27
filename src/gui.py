from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

from converter import convert_pdf_by_patient


BACKGROUND = "#f4f7f7"
PANEL = "#ffffff"
ACCENT = "#006b68"
ACCENT_DARK = "#004f4d"
TEXT = "#1f2933"
MUTED = "#5d6b78"


class GalConverterApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("GAL - Gerador de mapas editáveis")
        self.root.geometry("900x640")
        self.root.minsize(780, 560)
        self.root.configure(bg=BACKGROUND)

        self.input_path = StringVar()
        self.output_dir = StringVar(value=str(Path.cwd() / "output"))
        self.generate_docx = BooleanVar(value=True)
        self.generate_html = BooleanVar(value=True)
        self.is_running = False

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=11)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family="Segoe UI", size=11)
        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(family="Consolas", size=10)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", font=default_font, background=BACKGROUND, foreground=TEXT)
        style.configure("App.TFrame", background=BACKGROUND)
        style.configure("Panel.TFrame", background=PANEL, relief="flat")
        style.configure("Header.TLabel", background=BACKGROUND, foreground=ACCENT_DARK, font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=BACKGROUND, foreground=MUTED, font=("Segoe UI", 11))
        style.configure("Section.TLabelframe", background=PANEL, bordercolor="#d9e2e2", relief="solid")
        style.configure(
            "Section.TLabelframe.Label",
            background=PANEL,
            foreground=ACCENT_DARK,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure("TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=PANEL, foreground=ACCENT_DARK, font=("Segoe UI", 11, "bold"))
        style.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT, padding=8)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11), padding=(14, 8))
        style.configure("Primary.TButton", background=ACCENT, foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.map(
            "Primary.TButton",
            background=[("active", ACCENT_DARK), ("disabled", "#90a4a3")],
            foreground=[("disabled", "#f3f4f6")],
        )

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame = ttk.Frame(self.root, padding=22, style="App.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        header = ttk.Frame(frame, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="GAL - Mapas editáveis", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Laboratório de Micobactérias | LACEN-DF",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        accent_line = ttk.Frame(frame, height=4, style="Panel.TFrame")
        accent_line.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        accent_line.configure(style="Accent.TFrame")
        ttk.Style(self.root).configure("Accent.TFrame", background=ACCENT)

        input_panel = ttk.LabelFrame(frame, text="Arquivos", padding=16, style="Section.TLabelframe")
        input_panel.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        input_panel.columnconfigure(1, weight=1)

        ttk.Label(input_panel, text="PDF de entrada").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        ttk.Entry(input_panel, textvariable=self.input_path).grid(row=0, column=1, sticky="ew", pady=8)
        ttk.Button(input_panel, text="Selecionar...", command=self.choose_input).grid(row=0, column=2, padx=(10, 0), pady=8)

        ttk.Label(input_panel, text="Pasta de saída").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)
        ttk.Entry(input_panel, textvariable=self.output_dir).grid(row=1, column=1, sticky="ew", pady=8)
        ttk.Button(input_panel, text="Selecionar...", command=self.choose_output_dir).grid(row=1, column=2, padx=(10, 0), pady=8)

        options_panel = ttk.LabelFrame(frame, text="Conversão", padding=16, style="Section.TLabelframe")
        options_panel.grid(row=3, column=0, sticky="nsew")
        options_panel.columnconfigure(0, weight=1)
        options_panel.rowconfigure(3, weight=1)

        format_frame = ttk.Frame(options_panel, style="Panel.TFrame")
        format_frame.grid(row=0, column=0, sticky="w", pady=(0, 12))
        ttk.Checkbutton(format_frame, text="Gerar DOCX", variable=self.generate_docx).grid(row=0, column=0, padx=(0, 18))
        ttk.Checkbutton(format_frame, text="Gerar HTML", variable=self.generate_html).grid(row=0, column=1)

        actions = ttk.Frame(options_panel, style="Panel.TFrame")
        actions.grid(row=1, column=0, sticky="w", pady=(0, 14))
        self.convert_button = ttk.Button(actions, text="Converter", command=self.start_conversion, style="Primary.TButton")
        self.convert_button.grid(row=0, column=0, padx=(0, 10))
        ttk.Button(actions, text="Abrir pasta", command=self.open_output_dir).grid(row=0, column=1)

        self.status = ttk.Label(options_panel, text="Pronto", style="Status.TLabel")
        self.status.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.log = ScrolledText(options_panel, height=12, wrap="word", font=("Consolas", 10))
        self.log.grid(row=3, column=0, sticky="nsew")
        self.log.configure(
            state="disabled",
            bg="#fbfdfd",
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
        )

    def choose_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar PDF do GAL",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.input_path.set(path)

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Selecionar pasta de saída")
        if path:
            self.output_dir.set(path)

    def append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_running(self, running: bool) -> None:
        self.is_running = running
        self.convert_button.configure(state=("disabled" if running else "normal"))
        self.status.configure(text=("Convertendo..." if running else "Pronto"))

    def validate_inputs(self) -> bool:
        input_path = Path(self.input_path.get())
        if not input_path.is_file():
            messagebox.showerror("Entrada inválida", "Selecione um PDF de entrada válido.")
            return False
        if not self.generate_docx.get() and not self.generate_html.get():
            messagebox.showerror("Formato inválido", "Selecione DOCX, HTML ou ambos.")
            return False
        return True

    def start_conversion(self) -> None:
        if self.is_running or not self.validate_inputs():
            return

        self.set_running(True)
        self.append_log("Iniciando conversão.")
        worker = threading.Thread(target=self.run_conversion, daemon=True)
        worker.start()

    def run_conversion(self) -> None:
        try:
            outputs = convert_pdf_by_patient(
                self.input_path.get(),
                self.output_dir.get(),
                generate_docx=self.generate_docx.get(),
                generate_html=self.generate_html.get(),
            )
        except Exception as exc:
            details = traceback.format_exc()
            self.root.after(0, self.finish_with_error, exc, details)
            return

        self.root.after(0, self.finish_success, outputs)

    def finish_success(self, outputs) -> None:
        for output in outputs:
            paths = [str(path) for path in (output.docx_path, output.html_path) if path]
            self.append_log(f"{output.patient_name}: {', '.join(paths)}")
        self.append_log(f"Concluído. {len(outputs)} paciente(s)/página(s) processado(s).")
        self.set_running(False)
        messagebox.showinfo("Conversão concluída", f"{len(outputs)} paciente(s)/página(s) processado(s).")

    def finish_with_error(self, exc: Exception, details: str) -> None:
        self.append_log(f"Erro: {exc}")
        self.append_log(details)
        self.set_running(False)
        messagebox.showerror("Erro na conversão", str(exc))

    def open_output_dir(self) -> None:
        path = Path(self.output_dir.get())
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])


def main() -> int:
    root = Tk()
    GalConverterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
