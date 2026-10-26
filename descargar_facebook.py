#!/usr/bin/env python3
"""Descargador de videos de Facebook (uso personal) basado en yt-dlp.

Uso:
    python descargar_facebook.py                     # abre la interfaz gráfica
    python descargar_facebook.py URL [carpeta]       # modo consola

Requisitos:
    pip install yt-dlp
    ffmpeg en el PATH (para unir video y audio en HD)
"""
import sys
import threading
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Falta yt-dlp. Instálalo con: pip install yt-dlp")

CARPETA_POR_DEFECTO = Path.home() / "Videos"


def descargar(url, carpeta, progreso=None):
    """Descarga el video en la mejor calidad disponible y devuelve la ruta."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    opciones = {
        "outtmpl": str(carpeta / "%(title).80s [%(id)s].%(ext)s"),
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if progreso:
        opciones["progress_hooks"] = [progreso]
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info)).with_suffix(".mp4")


def modo_consola(argv):
    url = argv[1]
    carpeta = argv[2] if len(argv) > 2 else CARPETA_POR_DEFECTO

    def progreso(d):
        if d["status"] == "downloading":
            print(f"\r{d.get('_percent_str', '').strip()}", end="", flush=True)

    try:
        ruta = descargar(url, carpeta, progreso)
    except yt_dlp.utils.DownloadError as e:
        sys.exit(f"\nError: {e}")
    print(f"\nGuardado en: {ruta}")


def modo_grafico():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    raiz = tk.Tk()
    raiz.title("Descargar video de Facebook")
    raiz.geometry("560x190")
    raiz.resizable(False, False)

    url_var = tk.StringVar()
    carpeta_var = tk.StringVar(value=str(CARPETA_POR_DEFECTO))
    estado_var = tk.StringVar(value="Pega el enlace del video y presiona Descargar.")

    ttk.Label(raiz, text="URL del video:").grid(row=0, column=0, padx=10, pady=(14, 4), sticky="w")
    ttk.Entry(raiz, textvariable=url_var, width=62).grid(row=1, column=0, columnspan=2, padx=10, sticky="we")

    ttk.Label(raiz, text="Carpeta de destino:").grid(row=2, column=0, padx=10, pady=(10, 4), sticky="w")
    ttk.Entry(raiz, textvariable=carpeta_var, width=50).grid(row=3, column=0, padx=10, sticky="we")

    def elegir():
        elegida = filedialog.askdirectory(initialdir=carpeta_var.get())
        if elegida:
            carpeta_var.set(elegida)

    ttk.Button(raiz, text="Examinar…", command=elegir).grid(row=3, column=1, padx=(0, 10))

    barra = ttk.Progressbar(raiz, length=540, maximum=100)
    barra.grid(row=4, column=0, columnspan=2, padx=10, pady=(12, 2))
    ttk.Label(raiz, textvariable=estado_var).grid(row=5, column=0, columnspan=2, padx=10, sticky="w")

    boton = ttk.Button(raiz, text="Descargar")
    boton.grid(row=6, column=1, padx=10, pady=6, sticky="e")

    def progreso(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                raiz.after(0, barra.config, {"value": d["downloaded_bytes"] * 100 / total})
            raiz.after(0, estado_var.set, f"Descargando… {d.get('_percent_str', '').strip()}")

    def trabajo():
        try:
            ruta = descargar(url_var.get().strip(), carpeta_var.get(), progreso)
            raiz.after(0, estado_var.set, f"Listo: {ruta.name}")
            raiz.after(0, barra.config, {"value": 100})
        except Exception as e:  # noqa: BLE001 - se muestra al usuario
            raiz.after(0, estado_var.set, "Error al descargar.")
            raiz.after(0, messagebox.showerror, "Error", str(e))
        finally:
            raiz.after(0, boton.config, {"state": "normal"})

    def iniciar():
        if not url_var.get().strip():
            messagebox.showwarning("Falta la URL", "Pega el enlace del video.")
            return
        boton.config(state="disabled")
        barra.config(value=0)
        estado_var.set("Conectando…")
        threading.Thread(target=trabajo, daemon=True).start()

    boton.config(command=iniciar)
    raiz.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        modo_consola(sys.argv)
    else:
        modo_grafico()
