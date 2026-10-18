#!/usr/bin/env python3
"""Touchpad3D - puente universal: traduce los gestos del iPad a eventos de raton/teclado de Windows.

Sirve para cualquier programa que navegue con raton (Archicad, Rhino, Maya...).
Sin dependencias externas. El cursor debe estar sobre la ventana 3D con foco.

Uso:  python mouse_bridge.py [--config config.json] [--dry-run]
"""
import argparse
import json
import math
import os
import socket
import sys
import time

BUTTONS = ("left", "right", "middle")
MODIFIER_VK = {"shift": 0x10, "ctrl": 0x11, "alt": 0x12}


def key_to_vk(name):
    name = name.lower()
    if name in MODIFIER_VK:
        return MODIFIER_VK[name]
    if len(name) == 1:
        return ord(name.upper())
    if name.startswith("f") and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
        return 0x70 + int(name[1:]) - 1
    raise ValueError("tecla no soportada: " + name)


class DryInjector(object):
    """Imprime las acciones; sirve para probar en cualquier sistema."""
    def __init__(self):
        self.log = []

    def _emit(self, *a):
        self.log.append(a)
        print(*a)

    def button(self, name, down): self._emit("button", name, "down" if down else "up")
    def key(self, vk, down): self._emit("key", hex(vk), "down" if down else "up")
    def move(self, dx, dy): self._emit("move", dx, dy)
    def wheel(self, ticks): self._emit("wheel", ticks)
    def wheel_raw(self, delta): self._emit("wheel_raw", delta)
    def save_cursor(self): self._emit("save_cursor")
    def restore_cursor(self): self._emit("restore_cursor")


class WindowsInjector(object):
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.user32 = ctypes.windll.user32
        ulong_ptr = ctypes.c_size_t

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]

        class _Union(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", _Union)]

        self.MOUSEINPUT, self.KEYBDINPUT, self.INPUT = MOUSEINPUT, KEYBDINPUT, INPUT
        self.POINT = wintypes.POINT
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self.user32.SendInput.restype = wintypes.UINT
        self.saved = None

    def _send(self, inp):
        self.user32.SendInput(1, self.ctypes.byref(inp), self.ctypes.sizeof(self.INPUT))

    def _mouse(self, flags, dx=0, dy=0, data=0):
        inp = self.INPUT(type=0)
        inp.mi = self.MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
        self._send(inp)

    def button(self, name, down):
        flags = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}[name]
        self._mouse(flags[0] if down else flags[1])

    def key(self, vk, down):
        inp = self.INPUT(type=1)
        inp.ki = self.KEYBDINPUT(vk, 0, 0 if down else 0x0002, 0, 0)
        self._send(inp)

    def move(self, dx, dy): self._mouse(0x0001, dx, dy)
    def wheel(self, ticks): self._mouse(0x0800, data=ticks * 120)
    def wheel_raw(self, delta): self._mouse(0x0800, data=delta)

    def save_cursor(self):
        pt = self.POINT()
        self.user32.GetCursorPos(self.ctypes.byref(pt))
        self.saved = (pt.x, pt.y)

    def restore_cursor(self):
        if self.saved:
            self.user32.SetCursorPos(*self.saved)


class Bridge(object):
    def __init__(self, cfg, inj, clock=time.monotonic):
        self.cfg, self.inj, self.clock = cfg, inj, clock
        self.mode = None          # None | "orbit" | "pan"
        self.last = 0.0
        self.armed_until = 0.0    # tras pulsar, espera antes de mover (algunos programas lo necesitan)
        self.rem = {"x": 0.0, "y": 0.0, "wheel": 0.0}

    # --- gestos de arrastre (boton + modificadores mantenidos) ---
    def _begin(self, mode):
        spec = self.cfg[mode]
        if self.cfg.get("restore_cursor", True):
            self.inj.save_cursor()
        for m in spec["modifiers"]:
            self.inj.key(key_to_vk(m), True)
        if spec.get("button"):
            self.inj.button(spec["button"], True)
        self.armed_until = self.clock() + self.cfg.get("press_delay_ms", 40) / 1000.0
        self.mode = mode
        self.rem["x"] = self.rem["y"] = 0.0

    def end(self):
        if self.mode is None:
            return
        spec = self.cfg[self.mode]
        if spec.get("button"):
            self.inj.button(spec["button"], False)
        for m in reversed(spec["modifiers"]):
            self.inj.key(key_to_vk(m), False)
        if self.cfg.get("restore_cursor", True):
            self.inj.restore_cursor()
        self.mode = None

    def _drag(self, mode, dx, dy):
        if self.mode != mode:
            self.end()
            self._begin(mode)
        ppw = float(self.cfg[mode]["pixels_per_width"])
        self.rem["x"] += dx * ppw
        self.rem["y"] += dy * ppw
        if self.clock() < self.armed_until:
            return
        ix, iy = int(self.rem["x"]), int(self.rem["y"])
        self.rem["x"] -= ix
        self.rem["y"] -= iy
        if ix or iy:
            self.inj.move(ix, iy)

    def _zoom(self, factor):
        if factor <= 0:
            return
        z = self.cfg["zoom"]
        ticks = math.log(factor, 2) * z["ticks_per_doubling"]
        self.rem["wheel"] += -ticks if z.get("invert") else ticks
        if z.get("smooth"):                      # fracciones de muesca (1/120), si el programa las acepta
            n = int(self.rem["wheel"] * 120)
            self.rem["wheel"] -= n / 120.0
            if n:
                self.inj.wheel_raw(n)
            return
        n = int(self.rem["wheel"])
        self.rem["wheel"] -= n
        if n:
            self.inj.wheel(n)

    def _combo(self, keys):
        if not keys:
            return
        vks = [key_to_vk(k) for k in keys]
        for vk in vks:
            self.inj.key(vk, True)
        for vk in reversed(vks):
            self.inj.key(vk, False)

    def handle(self, msg):
        kind = msg.get("type")
        self.last = self.clock()
        if kind in ("orbit", "pan"):
            self._drag(kind, float(msg.get("dx", 0)), float(msg.get("dy", 0)))
        elif kind == "zoom":
            self._zoom(float(msg.get("factor", 1)))
        elif kind == "extents":
            self.end()
            self._combo(self.cfg.get("extents"))
        elif kind == "view":
            self.end()
            self._combo(self.cfg.get("views", {}).get(str(msg.get("name", "")).lower()))

    def tick(self):
        """Suelta el gesto si el iPad dejo de enviar datos."""
        if self.mode and (self.clock() - self.last) * 1000 >= self.cfg.get("release_ms", 150):
            self.end()


class Verbose(object):
    """Imprime cada accion salvo los movimientos (para ver que se esta inyectando)."""
    def __init__(self, inner):
        self.inner = inner

    def __getattr__(self, name):
        fn = getattr(self.inner, name)

        def call(*a):
            if name != "move":
                print(">", name, *a)
            return fn(*a)
        return call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    ap.add_argument("--verbose", action="store_true", help="imprime botones, teclas y rueda inyectados")
    ap.add_argument("--dry-run", action="store_true", help="solo imprime las acciones")
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    if not args.dry_run and os.name != "nt":
        sys.exit("La inyeccion real solo esta soportada en Windows. Use --dry-run para probar.")
    inj = DryInjector() if args.dry_run else WindowsInjector()
    bridge = Bridge(cfg, Verbose(inj) if args.verbose else inj)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", cfg.get("port", 9876)))
    sock.settimeout(0.03)
    print("Touchpad3D bridge escuchando en UDP {} (Ctrl+C para salir)".format(cfg.get("port", 9876)))
    try:
        while True:
            try:
                data, _ = sock.recvfrom(2048)
                bridge.handle(json.loads(data.decode("utf-8")))
            except socket.timeout:
                pass
            except ValueError:
                pass
            bridge.tick()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.end()


if __name__ == "__main__":
    main()
