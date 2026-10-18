# Touchpad3D

Reemplazo moderno de *Maide Control* (2011): el iPad es una superficie multitáctil que controla la cámara del viewport de Rhino por Wi-Fi.

```
iPad (SwiftUI/UIKit)  --UDP/JSON, puerto 9876-->  Rhino 8 (Python 3, hilo + UI thread)
 gestos normalizados                               orbit / pan / zoom / vistas / extents
```

## Gestos

| Gesto | Acción |
|---|---|
| 1 dedo | Orbitar (turntable, eje Z, elevación limitada a ±89°) |
| 2 dedos | Desplazar (pan) |
| Pellizco | Zoom |
| Doble toque | Zoom extents |
| Botones | Top, Front, Right, Perspective, Extents |

## Instalación

**Rhino 8 (Windows)**
1. Abrir `rhino/touchpad3d_server.py` en el ScriptEditor y ejecutarlo. Imprime la IP de la PC. Ejecutarlo de nuevo lo detiene.
2. Permitir en el Firewall de Windows tráfico entrante **UDP 9876** (red privada).

**iPad**
1. En Xcode (Mac): *App* nueva, SwiftUI, iOS 16+. Reemplazar los archivos por los de `ios/Touchpad3D/` y agregar las claves de `Info-additions.plist.txt`.
2. Instalar en el iPad, escribir la IP de la PC y pulsar *Conectar*.

**Prueba sin iPad:** `python3 tools/send_test.py <ip-de-la-pc>` envía orbit, pan, zoom y cambios de vista simulados.

## Protocolo (v1)

Un objeto JSON por datagrama. `dx`/`dy` son fracciones del ancho/alto del lienzo (independientes de la resolución).

```json
{"type":"orbit","dx":0.01,"dy":-0.02}
{"type":"pan","dx":0.01,"dy":0.00}
{"type":"zoom","factor":1.05}
{"type":"view","name":"top"}      // top|bottom|left|right|front|back|perspective
{"type":"extents"}
```

El servidor acumula los deltas recibidos entre cuadros y los aplica una sola vez en el hilo de UI, para no saturar Rhino.

## Puente universal (Archicad y otros programas)

`bridge/mouse_bridge.py` recibe el mismo UDP y **inyecta eventos de ratón y teclado de Windows** (`SendInput`), sin drivers ni dependencias. Sirve para cualquier programa que navegue con ratón.

1. Ejecutar `python bridge/mouse_bridge.py` en la PC (no usar a la vez que el script de Rhino: ambos escuchan el puerto 9876; para Rhino con este puente basta apagar el script).
2. Dejar el cursor sobre la ventana 3D con foco y operar desde el iPad.

| Gesto | Evento inyectado (configurable en `bridge/config.json`) |
|---|---|
| 1 dedo | Shift + botón derecho mantenido + movimiento |
| 2 dedos | Botón derecho mantenido + movimiento |
| Pellizco | Rueda del ratón (`ticks_per_doubling`, `invert`) |
| Extents / vistas | Combinaciones de teclas; vienen en `null` y hay que asignarlas, ej. `["ctrl","shift","f"]` |

Opciones de ajuste: `press_delay_ms` (espera tras pulsar antes de mover), `zoom.smooth` (rueda en fracciones de muesca), `button: null` (gesto solo con teclas) y `--verbose` (muestra botones, teclas y rueda inyectados).

El gesto se suelta solo tras `release_ms` sin datos, y el cursor vuelve a su posición (`restore_cursor`). Probar sin inyectar: `python bridge/mouse_bridge.py --dry-run`.

**Pendiente de validar en Archicad:** las combinaciones de navegación por defecto son una suposición (Shift + botón derecho para orbitar, botón derecho para desplazar: confirmado por el usuario); ajustarlas a la configuración real de la versión instalada. La inyección real solo se verificó por lectura de código: en Linux se probó únicamente el modo `--dry-run`. El zoom durante un arrastre envía la rueda sin soltar el botón; si Archicad lo rechaza, habrá que cambiar esa política.

## Probar con el touchpad de la laptop (simulador)

`tools/touchpad_sim.py` abre en el navegador un lienzo táctil que emite los mismos mensajes UDP que enviará el iPad. Sin dependencias.

```
python tools/touchpad_sim.py                 # solo esta PC (127.0.0.1)
python tools/touchpad_sim.py --lan           # también accesible desde la red local
```

| Gesto del touchpad | Mensaje |
|---|---|
| Arrastrar (clic sostenido o toque + arrastre) | `orbit` |
| Scroll con 2 dedos | `pan` |
| Pellizco (llega como Ctrl + rueda) | `zoom` |
| Doble clic | `extents` |
| Botón derecho o central + arrastre (ratón) | `pan` |
| Pantalla táctil: 1 dedo / 2 dedos / pellizco / doble toque | `orbit` / `pan` / `zoom` / `extents` |

El panel lateral ajusta sensibilidad e inversión de cada eje y los guarda en el navegador. Cuando estén afinados, esos valores se trasladan como constantes a la app del iPad.

**Con Rhino** (script `rhino/touchpad3d_server.py`): funciona en la misma laptop, con el navegador y Rhino lado a lado, porque el script usa la API de Rhino y no depende del foco.

**Con Archicad** (`bridge/mouse_bridge.py`): el puente mueve el cursor real, que durante la prueba está sobre la ventana del simulador, no sobre Archicad. Desde la laptop solo sirve para ver las acciones con `--dry-run`. Para probar de verdad hay que mandar los gestos desde otro dispositivo: `--lan` y abrir la URL que imprime el simulador en Safari del iPad (sin compilar nada en Xcode).

## Estado y límites

- **Sin probar en Rhino ni Xcode**: se escribió en un entorno Linux. Solo se verificó la sintaxis de Python y la lógica de acumulación de mensajes con módulos simulados. Los signos de rotación, la escala del pan y la API de cámara (`SetCameraLocations`, `GetFrustum`, `Magnify`) deben validarse en Rhino 8.
- UDP no cifra ni autentica: usar solo en una red de confianza.
- Descubrimiento automático (Bonjour), sensibilidad configurable, órbita 6DOF y soporte para Grasshopper quedan para una segunda etapa.
