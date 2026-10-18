#!/usr/bin/env python3
"""Touchpad3D - simulador: convierte gestos del navegador en los mismos mensajes UDP que enviara el iPad.

Abre una pagina con un lienzo tactil. Sirve para afinar sensibilidad y signos con el touchpad de la laptop
(o con una pantalla tactil, o desde Safari del iPad usando --lan). Sin dependencias externas.

Uso:  python touchpad_sim.py [--lan] [--http-port 8000] [--udp-host 127.0.0.1] [--udp-port 9876]
"""
import argparse
import json
import os
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = {"orbit", "pan", "zoom", "view", "extents"}
HERE = os.path.dirname(os.path.abspath(__file__))


def lan_ips():
    try:
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
    except OSError:
        return []


def make_handler(udp, target):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, code, body=b"", ctype="text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "touchpad_sim.html"), "rb") as f:
                    self._reply(200, f.read(), "text/html; charset=utf-8")
            elif self.path == "/info":
                self._reply(200, json.dumps({"target": "{}:{}".format(*target)}).encode(), "application/json")
            else:
                self._reply(404)

        def do_POST(self):
            if self.path != "/send":
                return self._reply(404)
            length = int(self.headers.get("Content-Length", 0))
            if length > 65536:
                return self._reply(413)
            try:
                msgs = json.loads(self.rfile.read(length).decode("utf-8"))
            except ValueError:
                return self._reply(400)
            if not isinstance(msgs, list):
                return self._reply(400)
            for m in msgs[:200]:
                if isinstance(m, dict) and m.get("type") in ALLOWED:
                    udp.sendto(json.dumps(m).encode("utf-8"), target)
            self._reply(204)

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lan", action="store_true", help="aceptar conexiones de la red local (p. ej. el iPad)")
    ap.add_argument("--http-port", type=int, default=8000)
    ap.add_argument("--udp-host", default="127.0.0.1")
    ap.add_argument("--udp-port", type=int, default=9876)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.udp_host, args.udp_port)
    host = "0.0.0.0" if args.lan else "127.0.0.1"
    server = ThreadingHTTPServer((host, args.http_port), make_handler(udp, target))
    print("Simulador -> UDP {}:{}".format(*target))
    print("Abrir: http://127.0.0.1:{}".format(args.http_port))
    if args.lan:
        for ip in lan_ips():
            print("Desde el iPad: http://{}:{}".format(ip, args.http_port))
    if not args.no_browser and not args.lan:
        webbrowser.open("http://127.0.0.1:{}".format(args.http_port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
