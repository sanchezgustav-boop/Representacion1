#! python 3
# -*- coding: utf-8 -*-
"""Touchpad3D - servidor UDP para Rhino 8 (Windows).

Recibe gestos desde el iPad y mueve la camara del viewport activo.
Ejecutar una vez para iniciar y otra vez para detener (ScriptEditor o comando RunPythonScript).
Protocolo: ver ../README.md
"""
import json
import math
import socket
import threading

import System
import Rhino
import scriptcontext as sc
from Rhino.Geometry import Point3d, Vector3d, Transform
from Rhino.Display import DefinedViewportProjection

PORT = 9876
STICKY_KEY = "touchpad3d_server"
ORBIT_GAIN = math.pi      # radianes por pantalla completa deslizada (coordenadas normalizadas)
MAX_ELEVATION = math.radians(89.0)

VIEWS = {
    "top": DefinedViewportProjection.Top,
    "bottom": DefinedViewportProjection.Bottom,
    "left": DefinedViewportProjection.Left,
    "right": DefinedViewportProjection.Right,
    "front": DefinedViewportProjection.Front,
    "back": DefinedViewportProjection.Back,
    "perspective": DefinedViewportProjection.Perspective,
}


def empty_pending():
    return {"ox": 0.0, "oy": 0.0, "px": 0.0, "py": 0.0, "zoom": 1.0, "view": None, "extents": False}


def merge(pending, msg):
    """Acumula un mensaje en el estado pendiente (los deltas se suman)."""
    kind = msg.get("type")
    if kind == "orbit":
        pending["ox"] += float(msg.get("dx", 0.0))
        pending["oy"] += float(msg.get("dy", 0.0))
    elif kind == "pan":
        pending["px"] += float(msg.get("dx", 0.0))
        pending["py"] += float(msg.get("dy", 0.0))
    elif kind == "zoom":
        factor = float(msg.get("factor", 1.0))
        if factor > 0:
            pending["zoom"] *= factor
    elif kind == "view":
        name = str(msg.get("name", "")).lower()
        if name in VIEWS:
            pending["view"] = name
    elif kind == "extents":
        pending["extents"] = True


def orbit(vp, dx, dy):
    """Orbita alrededor del target, estilo turntable con Z hacia arriba."""
    target = vp.CameraTarget
    loc = Point3d(vp.CameraLocation)
    up = Vector3d(vp.CameraUp)
    cam_x = Vector3d(vp.CameraX)

    rot_h = Transform.Rotation(-dx * ORBIT_GAIN, Vector3d.ZAxis, target)
    loc.Transform(rot_h)
    up.Transform(rot_h)
    cam_x.Transform(rot_h)

    v = loc - target
    r = v.Length
    if r > 0:
        elev = math.asin(max(-1.0, min(1.0, v.Z / r)))
        delta = dy * ORBIT_GAIN
        delta = max(-MAX_ELEVATION - elev, min(MAX_ELEVATION - elev, delta))
        rot_v = Transform.Rotation(-delta, cam_x, target)
        loc.Transform(rot_v)
        up.Transform(rot_v)

    vp.SetCameraLocations(target, loc)
    vp.CameraUp = up


def pan(vp, dx, dy):
    """Desplaza la camara; dx, dy son fracciones del ancho/alto del lienzo."""
    target = vp.CameraTarget
    loc = vp.CameraLocation
    ok, left, right, bottom, top, near, far = vp.GetFrustum()
    if not ok:
        return
    width = right - left
    height = top - bottom
    if not vp.IsParallelProjection and near > 0:
        scale = (target - loc).Length / near
        width *= scale
        height *= scale
    move = vp.CameraX * (-dx * width) + vp.CameraY * (dy * height)
    vp.SetCameraLocations(target + move, loc + move)


class Server(object):
    def __init__(self, port):
        self.port = port
        self.lock = threading.Lock()
        self.pending = empty_pending()
        self.scheduled = False
        self.running = False
        self.sock = None
        self.thread = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(0.5)
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="touchpad3d")
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def _loop(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            with self.lock:
                merge(self.pending, msg)
                if self.scheduled:
                    continue
                self.scheduled = True
            Rhino.RhinoApp.InvokeOnUiThread(System.Action(self._apply))

    def _apply(self):
        with self.lock:
            p = self.pending
            self.pending = empty_pending()
            self.scheduled = False
        doc = Rhino.RhinoDoc.ActiveDoc
        view = doc.Views.ActiveView if doc else None
        if view is None:
            return
        vp = view.ActiveViewport
        if p["view"]:
            vp.SetProjection(VIEWS[p["view"]], None, False)
        if p["extents"]:
            vp.ZoomExtents()
        if p["ox"] or p["oy"]:
            orbit(vp, p["ox"], p["oy"])
        if p["px"] or p["py"]:
            pan(vp, p["px"], p["py"])
        if p["zoom"] != 1.0:
            vp.Magnify(p["zoom"], False)
        view.Redraw()


def local_ips():
    try:
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
    except OSError:
        return []


def main():
    running = sc.sticky.get(STICKY_KEY)
    if running:
        running.stop()
        del sc.sticky[STICKY_KEY]
        print("Touchpad3D detenido.")
        return
    server = Server(PORT)
    server.start()
    sc.sticky[STICKY_KEY] = server
    print("Touchpad3D escuchando en UDP {}. IP(s) de esta PC: {}".format(PORT, ", ".join(local_ips()) or "?"))


if __name__ == "__main__":
    main()
