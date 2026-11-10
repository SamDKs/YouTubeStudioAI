# Limpieza autorizada — 2026-11-05

Se retiraron funcionalidades abandonadas y derivados de videos anteriores. El
flujo conservado es ZIP → producción local → QA → entrega para revisión.

## Qué se eliminó

- 154 archivos de código y pruebas obsoletos: pilotos, pantallas anteriores,
  adaptadores de pago/publicación y servicios sin consumidores en el flujo actual.
- 2.788 archivos derivados y auxiliares: videos viejos, audio de pilotos,
  temporales de render, cachés Python y respaldos acumulados. Volumen registrado:
  **1.672.901.054 bytes**, aproximadamente **1,67 GB**.
- Documentación de versiones abandonadas, capturas antiguas, CSS sin uso y un alias
  de errores redundante. Se retiró el modelo Whisper multilingüe que no utiliza
  la producción actual en inglés.

No se ocultaron pruebas fallidas: se retiraron las pruebas de funcionalidades
eliminadas y se reescribió la cobertura de migraciones para el almacenamiento
vigente. La suite completa actual tiene **38 pruebas aprobadas, sin fallos**.

## Organización resultante

El motor se movió a `app/engine/`, agrupando `audio`, `domain`, `ingestion`,
`pipeline`, `rendering` y `timing`. La entrada visual está en `app/workbench.py`;
`app/main.py` sigue siendo el comando de arranque. Ya no existen esas siete
carpetas de código dispersas en la raíz ni la pantalla «Historial previo».

Se actualizaron imports, rutas del contrato, dependencias declaradas, tests y
README. Las migraciones existentes se conservaron intactas: son necesarias para
abrir bases anteriores y comprobar sus checksums. La inicialización del catálogo
ahora es atómica y comprueba rutas bajo `canales/`.

Los registros de trabajos retirados se conservaron como evidencia en SQLite,
marcados como retirados y excluidos de los paneles activos. No se ofrecen enlaces
a MP4 eliminados ni se reinician trabajos pendientes de pilotos anteriores.

## Qué se conserva

- La entrega más reciente: largo, Short, previews, subtítulos, miniatura y ZIP.
- ZIP originales importados, registros maestros y recursos compartidos.
- Modelos Kokoro y Whisper inglés, binario Whisper, `.venv` y `.env` intacto.
- Caché reutilizable de producción y logs de los dos jobs vigentes.
- Guiones e investigaciones anteriores en un único archivo de 5.992 bytes:
  `data/sources/previous-editorial-sources.zip`.
- Un único respaldo de metadatos previo a la limpieza:
  `data/backups/before-cleanup-20261105.sqlite3`.

Ese respaldo no contiene los videos eliminados: la limpieza de derivados es real,
no un traslado de todos los videos a otra carpeta del proyecto.

## Verificación

- `unittest discover`: 38 pruebas aprobadas, incluida navegación de los tres canales,
  importación, SQLite, cola, render FFmpeg de prueba y empaquetado.
- Contrato 1.0.0 y ejemplo: válidos después del traslado del motor.
- Base real: `integrity_check=ok` y sin errores de claves foráneas.
- Interfaz real: global, MIS, TEC y CIE sin excepciones; MIS conserva sus descargas.
- Videos y ZIP vigentes: SHA-256 sin cambios; ffprobe y CRC del ZIP comprobados.
- Tres registros maestros presentes, voces locales disponibles y executor construible.

La entrega audiovisual sigue siendo parcial: faltan dos guiones Short y la revisión
editorial indicada en [la guía](phase3-delivery.md). La limpieza no modifica ese estado.

Inventario detallado: [cleanup-report.json](cleanup-report.json).
