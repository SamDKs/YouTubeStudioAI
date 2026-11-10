# YouTube Studio AI

Aplicación local para importar ZIP editoriales, producir un largo y hasta tres
Shorts independientes, verificar los archivos y descargar la entrega.
Interfaz en español; contenido principal en inglés estadounidense (`en-US`).
No sube ni publica videos.

## Ejecutar

Desde la raíz del proyecto:

```bash
.venv/bin/python -B -m streamlit run app/main.py --server.address 127.0.0.1
```

Abre `http://127.0.0.1:8501`. Selecciona un canal, importa y valida el ZIP,
activa su timeline y pulsa **Iniciar producción**. La interfaz inicia los workers
necesarios. Los guiones o recursos ausentes se muestran como pendientes.

[Guía de producción y descarga](docs/phase3-delivery.md) ·
[Contrato de importación](docs/phase1-package-import.md) ·
[Herramientas locales](docs/LOCAL_TOOLS.md) ·
[Limpieza del proyecto](docs/cleanup.md)

## Organización

```text
app/
  main.py, workbench.py      Entrada y ensamblado de la interfaz
  application/              Casos de uso de importación, producción y entrega
  domain/                   Reglas, errores y estados de la aplicación
  presentation/             Componentes Streamlit
  infrastructure/           SQLite, migraciones, workers y proveedor local
  engine/                   Importación, audio, tiempos, render y pipeline
canales/                    Tres registros maestros
config/                     Catálogo inicial de canales
schemas/                    Contrato JSON, adaptador y ejemplo mínimo
shared/                     Recursos originales compartidos
data/                      Base, modelos, herramientas, fuentes y trabajo local
docs/                      Guías vigentes y evidencia
tests/                     Pruebas del flujo actual
tools/                     Constructor del ejemplo del contrato
```

Los datos operativos están en `data/work/`: `imports`, `cache`, `temporary`,
`exports` y `logs`. Los modelos instalados se conservan en `data/models/`.
`.venv` y `.env` permanecen privados y no se versionan.

## Comprobar

```bash
.venv/bin/python -B -m unittest discover -s tests -q
.venv/bin/python -B -m app.cli contract-check
```

La CLI permite validar/importar ZIP y consultar proyectos. Para procesar un job
concreto fuera de la interfaz:

```bash
.venv/bin/python -B -m app.worker --job ID_DEL_TRABAJO
```

No ejecutar workers genéricos si solo se pretende procesar un job concreto.

## Estado actual

Se conserva la última entrega local de MIS-E001: largo de 133,73 s y Short de
40,77 s. Faltan los otros dos guiones; derechos, subtítulos aproximados y descripción
requieren revisión. No se presenta el ZIP parcial como una entrega completa.
Rutas y hashes: [verificación audiovisual](docs/phase3-verification.json).

No hay LLM local configurado. Los borradores adicionales requieren un proveedor
configurado o timelines aportados y aprobados por el propietario. La producción
usa FFmpeg, Kokoro y whisper.cpp locales; no consume APIs pagadas.
