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

## Estado y límites

- **Sin probar en Rhino ni Xcode**: se escribió en un entorno Linux. Solo se verificó la sintaxis de Python y la lógica de acumulación de mensajes con módulos simulados. Los signos de rotación, la escala del pan y la API de cámara (`SetCameraLocations`, `GetFrustum`, `Magnify`) deben validarse en Rhino 8.
- UDP no cifra ni autentica: usar solo en una red de confianza.
- Descubrimiento automático (Bonjour), sensibilidad configurable, órbita 6DOF y soporte para Grasshopper quedan para una segunda etapa.
