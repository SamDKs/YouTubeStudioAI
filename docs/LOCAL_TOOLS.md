# Herramientas del flujo vigente

Verificadas localmente, sin reinstalar ni modificar `.venv` durante la limpieza:

| Componente | Uso |
|---|---|
| Python 3.12.16 y Streamlit 1.51.0 | Aplicación local |
| SQLite de Python | Persistencia y cola |
| FFmpeg/ffprobe 9.0.2 | Composición y comprobación audiovisual |
| Pillow 12.3.0 | Imágenes y rótulos |
| jsonschema 4.26.0 | Contrato de importación |
| NumPy 2.5.4 | Lectura de voces y audio |
| Kokoro ONNX 0.6.1 / ONNX Runtime 1.23.2 | Narración por CPU |
| whisper.cpp local / modelo inglés | Temporización de narración |
| requests 2.34.2 | Conector opcional llama.cpp en loopback |

Dependencias directas: `requirements.txt` y `requirements-local.txt`.
Los modelos Kokoro y Whisper inglés permanecen en `data/models/`; el binario
Whisper y sus bibliotecas en `data/tools/whisper/`. No se descargan automáticamente.
El modelo Whisper multilingüe y los pilotos españoles se retiraron por no pertenecer
al flujo actual en-US. No se desinstalaron paquetes del entorno virtual.

La integración llama.cpp solo opera con servidor y modelo elegidos explícitamente;
no está configurada en este proyecto. Los adaptadores antiguos de OpenAI,
ElevenLabs y publicación se retiraron del código activo. `.env` se conservó intacto.

No se equipara una comprobación automática con la revisión humana de pronunciación,
licencias o exactitud editorial. Antes de aprobar, escuchar narración y revisar
fuentes, rótulos, encuadres y subtítulos.
