# Fase 3 — Shorts, calidad y entrega local

La entrada activa produce un largo y hasta tres Shorts independientes en en-US,
con cuatro posiciones visibles y un ZIP verificable. Una posición sin guion queda
`NEEDS_SCRIPT`: no se recorta el largo ni se inventa una pieza para completar el panel.
No hay integración de subida ni publicación automática.

## Uso desde la interfaz

1. Ejecutar desde la raíz:
   `.venv/bin/python -m streamlit run app/main.py --server.address 127.0.0.1`.
2. Elegir un canal en el selector de contexto; importar su ZIP y revisar el informe.
   Activar su timeline en el motor audiovisual. Un ZIP de recursos sin asociaciones
   de escenas necesita preparación editorial antes de producir.
3. Elegir voz estadounidense, velocidad y pronunciaciones; guardar si se modifican.
   Ajustar FPS y máximo del Short. La duración sigue la narración medida: no se
   corta la voz ni se añade relleno para alcanzar el objetivo de 30–60 segundos.
4. Pulsar **Iniciar producción**. Cada pieza disponible recibe su propio job;
   los workers locales continúan fuera de los reruns de Streamlit. La cola permite
   un job activo del motor; otros workers esperan. Pausa, cancelación y reanudación
   están en **Ver trabajos y controles por etapa**. La Mac debe permanecer encendida.
5. En **Completar guiones pendientes**, aportar un timeline JSON aprobado o solicitar
   borradores al LLM local si está configurado. Leer y aprobar cada borrador antes de
   guardarlo. Guardar crea una revisión; volver a iniciar para producir esa revisión.
6. Completar descripción y keywords en inglés en **Metadatos del paquete de entrega**.
   Los campos vacíos se reportan; el motor no inventa metadatos ni fuentes.
7. Revisar los cuatro espacios del panel, reproducir los resultados y descargar MP4,
   SRT, reporte QA y ZIP completo o parcial. **Volver a generar** crea un job para esa
   pieza y conserva los jobs de las otras piezas para la misma revisión/configuración.
8. Registrar aprobación local únicamente después de revisar las cuatro piezas y
   resolver todos los bloqueos. Esa acción no sube ni programa publicaciones.

En contexto global, **Iniciar ciclo para todos los canales** activa importaciones
estructuradas y prepara sus piezas con diagnósticos aislados por episodio. Los paneles
por canal conservan los controles de cada job. No existe un segundo selector de canal.
La casilla **Producir automáticamente después de validar el ZIP** se guarda por canal;
la automatización exige derechos permitidos. La producción manual para revisión
puede conservar derechos `review_required`, pero nunca `prohibited`.

## Guiones adicionales y proveedores

Prioridad: timelines del ZIP, timelines aprobados guardados en la revisión del
proyecto, borradores de un LLM local explícitamente configurado. El campo JSON espera
un objeto de `deliverables` del contrato
`schemas/editorial-package-1.0.0.schema.json`: `kind: short`, IDs únicos, título en
US-English, resolución, FPS, duración objetivo, captions y escenas completas.
Como referencia estructural existe `schemas/examples/minimal/manifest.json`;
su contenido es una prueba, no un guion apto para publicación. Copiar la estructura
de un timeline existente exige cambiar narración, enfoque e IDs, y conservar las
referencias reales, recursos y rótulos obligatorios. Un guion Markdown aislado no
resuelve por sí mismo las asociaciones audiovisuales.

La validación rechaza narraciones completas repetidas o extraídas literalmente del
largo. Esto no demuestra independencia semántica, calidad editorial o exactitud:
se requiere revisión humana. Aprobar un Short nunca modifica el ZIP original.

Producción completamente local: Python, SQLite, Streamlit, Pillow, Kokoro ONNX,
whisper.cpp y FFmpeg/ffprobe existentes. No se instalaron dependencias ni modelos.
La narración falla de forma explícita si no hay voz/modelo disponibles. La generación
opcional de borradores usa el adaptador llama.cpp existente y una selección explícita
del proveedor `script`; no descarga modelos ni llama APIs pagadas. **No hay LLM
configurado en el proyecto real, por lo que esa generación no se verificó en vivo.**
No se requiere una API externa para importar, narrar, renderizar, comprobar y empaquetar
materiales suministrados. Generación externa de imágenes, música, nuevos hechos o
publicación en plataformas no se añadió en esta fase.

El máximo configurable es 30–180 segundos, con 60 por defecto. YouTube documenta
Shorts de hasta tres minutos para videos cuadrados/verticales elegibles en su
[ayuda oficial](https://support.google.com/youtube/answer/15424877?hl=en).
Esto no certifica límites ni elegibilidad de TikTok, Instagram o Facebook.

## Organización y archivos modificados

El código activo está concentrado en `app/`; el motor está en `app/engine/`.
Se retiraron módulos, pantallas, pilotos y pruebas de funcionalidades abandonadas.
La biblioteca de recursos, originales importados y registros maestros se conservan.
Consulta [la limpieza realizada](cleanup.md) y su inventario para el detalle.

| Ubicación | Responsabilidad |
|---|---|
| `app/domain/delivery.py` | Cuatro posiciones y comprobación estructural de independencia |
| `app/application/episode_delivery.py` | Producción por pieza, guiones aprobados, ciclo multicanal y descarga verificada |
| `app/infrastructure/sqlite/deliveries.py` | Entregas, candidatos, aprobación y preferencia automática |
| `app/infrastructure/migrations/014_episode_deliveries.sql` | Persistencia aditiva sin modificar migraciones anteriores |
| `app/presentation/episode_delivery.py` | Panel de cuatro piezas, metadatos y revisión |
| `app/presentation/production_monitor.py` | Monitor reutilizado y controles de jobs |
| `app/presentation/package_production.py`, `package_preparation.py`, `app/workbench.py` | Integración con la entrada activa y automatización |
| `app/engine/pipeline/service.py`, `sqlite_store.py`, `executor.py` | Plan, selección del proveedor y ejecución por pieza |
| `app/engine/pipeline/quality.py` | Decodificación, codecs, tamaño, FPS, tiempos, SRT, negro y silencio |
| `app/engine/pipeline/delivery.py` | Ensamblado inmutable, hashes y estados de entrega |
| `app/engine/pipeline/short_scripts.py` | Borradores locales sujetos a contrato y aprobación |
| `app/engine/rendering/composer.py`, `overlays.py` | Composición y textos dentro del encuadre móvil |
| `app/engine/domain/package.py`, `schemas/editorial-package-1.0.0.schema.json` | Tarea de borradores y metadatos opcionales compatibles |
| `app/worker.py` | Actualiza la entrega al terminar una pieza |
| `tests/integration/test_episode_delivery.py`, `test_package_preparation.py` | Regresión de entrega y migración actual |

## Control de calidad y persistencia

El largo usa 1920×1080; los Shorts 1080×1920. Salidas H.264/AAC, FPS constantes,
subtítulos y rótulos en inglés. El perfil inicial es 30 FPS. No se estiran visuales;
se respetan encuadres, movimiento y rótulos declarados. El texto vertical reserva
márgenes, aunque la superposición de interfaces de cada red requiere revisión móvil.

`RENDER_COMPLETED` solo afirma que existe el render. `QA_PASSED` exige decodificación
completa, codecs/tamaño/FPS correctos, escenas y duración coherentes, SRT temporal
válido y audio presente. Negro prolongado o silencios fuera de las pausas esperadas
producen `QA_REVIEW_REQUIRED`. No es reconocimiento semántico de imágenes ni una
escucha humana. Los captions aproximados siguen identificados y bloquean aprobación.
`EDITORIAL_REVIEW_PENDING` separa esas comprobaciones de la decisión del propietario.
`APPROVED_FOR_PUBLICATION` registra una decisión local sobre el contenido exacto.

Entregas en `data/work/exports/deliveries/<delivery_id>/<fingerprint>/` y ZIP paralelo:

- `long_en-US.mp4` y `short_01_en-US.mp4` a `short_03_en-US.mp4`, solo si existen.
- `subtitles/<pieza>_en-US.srt` y `thumbnail.png` desde un recurso real suministrado.
- `metadata.json`: títulos, descripción, keywords, fuentes, atribuciones y advertencias.
- `qa_report.json`: resultados y faltantes; `project_manifest.json`: contrato, voz,
  revisión, configuración y hash del ZIP original.

No se mezclan entradas y derivados. Los MP4 se verifican contra checkpoints; el ZIP
se comprueba por SHA-256 al descargar. Un ZIP alterado bloquea su entrega; regenerar
crea otra entrega. Los reportes completos se guardan también en SQLite. La generación
no cambia derechos, no aprueba por defecto y no oculta piezas ausentes.

## Evidencia real y límites

Ver [phase3-verification.json](phase3-verification.json) para rutas, hashes y mediciones.
Paquete real MIS-E001, importado por el flujo de fase 1 y vinculado al motor existente:

| Pieza | Resultado real |
|---|---|
| Largo | 133,733 s, 1920×1080, 30 FPS, H.264/AAC, 9 escenas, 48 cues SRT |
| Short 1 | 40,767 s, 1080×1920, 30 FPS, H.264/AAC, 4 escenas, 17 cues SRT |
| Shorts 2 y 3 | `NEEDS_SCRIPT`: el ZIP no aporta esos timelines y no hay LLM configurado |

Se verificaron ffprobe, decodificación completa de ambos videos, CRC del ZIP, hashes
internos de los videos y orden/límites de SRT. QA no detectó negro ni silencio
prolongado; máximos de audio −1 dB. Se inspeccionó un frame vertical a los 12 s:
texto legible, encuadre preservado y avisos visibles. No equivale a revisión humana
completa de voz, pronunciación, contenido o licencias.

El ZIP es **PARTIAL_DELIVERY**. Derechos de recursos pendientes, captions aproximados
y descripción estructurada vacía también impiden aprobación. No se inventaron los
dos Shorts ni se etiquetó este piloto de 2:14 como un episodio editorial de 8–15 min.

Pruebas focalizadas: **28 aprobadas** (arquitectura, importación, producción y entrega).
Incluyen SQLite real, aislamiento, idempotencia, regeneración selectiva, ausencia de
LLM, rechazo de duplicados, aprobación y corrupción de ZIP. La prueba de cuatro
archivos usa resultados simulados y no representa cuatro renders reales. Una prueba
FFmpeg sintética verifica la detección de negro. AppTest real: global, MIS, TEC y CIE,
sin excepciones, cuatro posiciones visibles y seis descargas en MIS.

La suite se actualizó durante la limpieza: las pruebas de componentes eliminados
se retiraron junto con esos componentes; las de persistencia se migraron al arranque
vigente. El resultado completo actual está en [cleanup.md](cleanup.md).
