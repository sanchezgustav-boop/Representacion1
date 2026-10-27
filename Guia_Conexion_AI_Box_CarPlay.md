# Guía técnica: conexión y modificación del Wireless CarPlay AI Box (Android 11, QCM2290, 4G LTE)

**Autor:** Gustavo (Urbanista y Dibujo Técnico)
**Equipo:** Guideforyou, Wireless CarPlay / Android Auto AI Box, Android 11, Qualcomm QCM2290, 4G LTE, GPS integrado
**Objetivo:** Conectar el box a un PC para modificar su presentación, quitar programas preinstalados y añadir otros.

---

## 1. ¿Puede Claude conectarse al box?

No directamente. La sesión de Claude Code corre en un contenedor en la nube, aislado, sin acceso a la red local, USB ni Bluetooth del usuario. La conexión la realiza el usuario desde su PC; Claude guía y prepara comandos y scripts.

Alternativa: si el usuario habilita *computer use* en la app de escritorio de Claude, este podría operar el PC y ejecutar ADB.

## 2. Medios de conexión

| Medio | Funcionamiento | Observaciones |
|---|---|---|
| ADB por USB | Cable de datos al PC con "Depuración USB" activa | Más estable; depende de que el puerto transmita datos |
| ADB por Wi-Fi | `adb connect IP:5555` en la misma red | No requiere cable |
| scrcpy | Control de pantalla del box desde el PC (sobre ADB) | Útil para configurar la interfaz |
| Sideload de APK | Instalar APK desde USB, navegador o gestor de archivos | No requiere ADB |

**Activar modo desarrollador:** Ajustes → Acerca de → tocar 7 veces "Número de compilación" → Opciones de desarrollador → Depuración USB.

## 3. Especificaciones del artículo (según ficha del vendedor)

| Especificación | Valor | Implicación |
|---|---|---|
| Marca | Guideforyou (origen CN) | Firmware genérico |
| Function1 | Plug and play | El servicio CarPlay/AA no debe eliminarse |
| Function2 | Versión WiFi | Permite ADB inalámbrico |
| Function3 | Versión 4G | Apps con datos propios (SIM) |
| Function4 | Soporta Google Play Store | Instalación directa de apps |
| Function5 | Aplicaciones integradas | Apps preinstaladas a depurar |
| Function6 | Conexión estable | — |

## 4. Ruta recomendada (de menor a mayor riesgo)

1. **Desde la interfaz del box:** instalar apps desde Play Store; en Ajustes → Apps desinstalar las de usuario y deshabilitar las de sistema.
2. **Cambiar la presentación con un launcher** (Lawnchair, Nova, etc.): Ajustes → Apps → Apps predeterminadas → Launcher. Verificar que persista tras reiniciar.
3. **ADB** solo para lo que la interfaz no permita quitar.

## 5. Comandos ADB útiles

```bash
adb devices                                   # verificar conexión
adb shell getprop ro.product.model            # modelo exacto
adb shell getprop ro.build.fingerprint        # versión de firmware
adb shell pm list packages -f                 # listar todas las apps con ruta
adb shell pm list packages -3                 # apps de usuario/fabricante
adb shell pm list packages -s                 # apps de sistema
adb install app.apk                           # instalar app
adb shell pm uninstall -k --user 0 <paquete>  # quitar app (reversible)
adb shell pm disable-user --user 0 <paquete>  # deshabilitar sin borrar
adb shell cmd package install-existing <paquete>  # restaurar app quitada
```

## 6. Conexión directa por USB-C al PC

El box se conecta al auto por USB-C (el auto actúa como host y el box como dispositivo), por lo que es probable que el PC pueda reconocerlo por el mismo puerto, aunque no está garantizado.

**Pasos**

1. Encender el box alimentado por el auto o un cargador y activar Depuración USB.
2. Conectarlo al PC con un cable USB-C **de datos**.
3. Ejecutar `adb devices`:
   - `device`: listo.
   - `unauthorized`: aceptar el aviso en la pantalla del box.
   - Lista vacía: probar otro cable o puerto (preferible USB-A directo de la placa, sin hub).

**Posibles problemas**

- **Potencia insuficiente:** un puerto de PC entrega 0,5 a 0,9 A; el box puede reiniciarse (sobre todo con el módem 4G). Solución: hub USB con alimentación propia.
- **Modo del puerto:** si el puerto no cambia a modo dispositivo con el PC, usar ADB por Wi-Fi.
- No conectar al PC mientras el box está en uso en el auto; hacerlo con el box sobre una mesa.

## 7. Plan B: ADB por Wi-Fi

1. Conectar el box a la red Wi-Fi (no solo a datos 4G).
2. Ver su IP en Ajustes → Wi-Fi.
3. Desde el PC, en la misma red:

```bash
adb connect 192.168.x.x:5555
```

Si el puerto 5555 no responde, activarlo una vez por USB con `adb tcpip 5555`, o usar "Depuración inalámbrica" si el Android 11 del box la ofrece.

## 8. Precauciones

1. Respaldar el listado de paquetes (`pm list packages -f`) antes de modificar.
2. **No eliminar los servicios de CarPlay/Android Auto inalámbrico** (nombres típicos: `carlink`, `zlink`, `autokit`, `ottocast`); sin ellos el box pierde su función principal.
3. Usar `--user 0` en lugar de borrado definitivo, para poder restaurar.
4. No hacer root ni flashear firmware sin tener la imagen original (riesgo de dejar el equipo inutilizable).
5. Las actualizaciones OTA pueden revertir cambios o reinstalar apps.
6. Firmware genérico: suele traer apps de publicidad o tiendas propias; identificarlas antes de deshabilitar.

## 9. Próximos pasos

- [ ] Instalar ADB (Android Platform Tools) en el PC; indicar si es Windows o Mac.
- [ ] Ejecutar `adb devices` y comprobar si el puerto USB-C transmite datos.
- [ ] Obtener `pm list packages -3` y `-s` para identificar qué quitar.
- [ ] Elegir un launcher alternativo.
- [ ] Preparar un script `.sh` o `.bat` con la secuencia final de cambios.

---

*Documento generado a partir de la conversación del 26 y 27 de octubre de 2026.*
