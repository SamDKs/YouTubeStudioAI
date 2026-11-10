# Importación y preparación de ZIP

El importador vigente está en `app/engine/ingestion/`; sus casos de uso en
`app/application/package_preparation.py` y su panel en `app/presentation/`.
Reutiliza la misma base SQLite del motor. La [guía de entrega](phase3-delivery.md)
describe la producción posterior.

## Contrato

`schemas/editorial-package-1.0.0.schema.json` define el contrato canónico:

- `contract_version`, `package_version`, `channel_id`, `episode_id`, `title`,
  `language: en-US` y `target_market: US`.
- `assets`: identificador, tipo, rol, ruta, hash SHA-256, disponibilidad, dimensiones,
  procedencia, licencia, estado de derechos y restricciones de recorte.
- `deliverables`: un largo y hasta tres Shorts, cada uno con título, escenas,
  narración, recursos, captions, FPS y duración objetivo propios.
- `editorial_references` y `checksums`: referencias y archivos fuente verificables.
- `publication_metadata`: descripción y keywords opcionales, revisadas en el panel.

El ZIP lleva `manifest.json` en raíz o dentro de una única carpeta contenedora.
El adaptador `schemas/adapters/editorial-production-1.json` permite interpretar el
paquete original compatible de Wow!; no convierte cualquier formato arbitrario.
El ejemplo mínimo se encuentra en `schemas/examples/minimal/` y es una prueba
geométrica, no un episodio editorial.

Un ZIP sin manifiesto puede importarse como recursos. Los nombres de archivos no
se interpretan como hechos ni como asociaciones automáticas de escenas. Un guion
Markdown sin timeline y recursos explícitos requiere preparación adicional.

## Validación y seguridad

Se validan el tipo real de los medios, hashes, documentos UTF-8, nombres y rutas.
Se rechazan enlaces, traversal, rutas absolutas, ejecutables, ZIP cifrados, CRC
inválido y extensiones incompatibles con su contenido. No se ejecutan archivos.
Límites iniciales: 500 entradas, 128 MiB comprimidos, 512 MiB expandidos,
128 MiB por archivo y ratio de compresión 200.

Los ZIP originales y los archivos extraídos quedan en `data/work/imports/`.
Los archivos derivados se guardan aparte. La identidad canal/hash impide importaciones
duplicadas accidentales; el informe conserva inventario, faltantes, errores y eventos.

## Estados y uso

Seleccionar canal → cargar ZIP → **Validar e importar** → revisar el informe →
**Preparar producción** → **Activar timeline en el motor audiovisual**.

Los estados son `IMPORTED`, `VALIDATING`, `NEEDS_SCRIPT`, `NEEDS_ASSETS`,
`READY_FOR_PRODUCTION` y `FAILED`. READY exige el paquete completo y derechos
resueltos; no significa render terminado ni aprobación editorial. El motor puede
producir por separado las piezas disponibles de un paquete incompleto para revisión.
La automatización opcional exige derechos permitidos.

Los guiones aprobados del canal pueden asociarse desde SQLite si existen; esa
asociación no inventa recursos ni un timeline. En la entrega se pueden añadir
Shorts estructurados y aprobados mediante una nueva revisión del proyecto.

## Comprobar

```bash
.venv/bin/python -B -m app.cli contract-check
.venv/bin/python -B -m app.cli validate /ruta/al/paquete.zip
.venv/bin/python -B -m unittest tests.integration.test_package_preparation -q
```
