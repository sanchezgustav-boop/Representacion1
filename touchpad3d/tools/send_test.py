#!/usr/bin/env python3
"""Cliente de prueba: envia gestos simulados al servidor de Rhino sin necesitar el iPad.

Uso: python3 send_test.py <ip-de-la-pc-con-rhino> [puerto]
"""
import json
import math
import socket
import sys
import time

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 9876
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(**msg):
    sock.sendto(json.dumps(msg).encode("utf-8"), (host, port))


send(type="view", name="perspective")
send(type="extents")
time.sleep(0.5)
for i in range(120):                      # orbita horizontal
    send(type="orbit", dx=0.004, dy=0.0)
    time.sleep(1 / 60)
for i in range(60):                       # orbita vertical
    send(type="orbit", dx=0.0, dy=0.003 * math.cos(i / 10))
    time.sleep(1 / 60)
for i in range(60):                       # pan
    send(type="pan", dx=0.005, dy=0.0)
    time.sleep(1 / 60)
for i in range(30):                       # zoom in
    send(type="zoom", factor=1.03)
    time.sleep(1 / 60)
send(type="view", name="top")
print("Enviado a {}:{}".format(host, port))
