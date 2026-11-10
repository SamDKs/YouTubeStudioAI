# AGENTS.md — YouTube Studio AI

> **Documento maestro de instrucciones para Codex en VS Code**  
> **Versión:** 2.1 — 2026-10-26 (estrategia ENGLISH-FIRST para los tres canales)  
> **Estado:** definición de arquitectura y desarrollo inicial; NO equivale a una aplicación ya implementada.  
> **Idioma de comunicación técnica con el propietario:** español latinoamericano neutral.  
> **Idioma principal OBLIGATORIO de los contenidos audiovisuales:** **inglés estadounidense (`en-US`) desde el primer episodio de los tres canales**.  
> **Mercado prioritario:** espectadores de Estados Unidos; expansión orgánica a Canadá, Reino Unido, Australia y otras audiencias angloparlantes.  
> **Español (`es-419`):** adaptación secundaria y opcional, no predeterminada.  
> **Ubicación esperada:** `~/Documents/YouTubeStudioAI/AGENTS.md`  
> **Principio rector:** construir por etapas, probar cada avance y conservar el control editorial y de publicación en manos del propietario.

---

## 1. Contexto general

### 1.1. Qué es YouTube Studio AI

YouTube Studio AI es una **aplicación visual de escritorio de uso local** que comenzará como una interfaz Streamlit ejecutada en el navegador de la Mac y un backend escrito en Python. Su objetivo es centralizar la producción de tres canales de contenido distintos: desde la importación de investigaciones y guiones hasta la narración, la planificación visual, la composición audiovisual, los subtítulos, los Shorts, la revisión y la preparación para publicación.

El producto final aspira a automatizar tareas repetitivas **sin eliminar el criterio humano**. No debe suponerse que una primera versión ya genera imágenes, video, voces o publicaciones. Cada capacidad se habilitará mediante implementaciones comprobadas y proveedores configurados.

### 1.2. Contexto del propietario y forma de colaboración

- El propietario utiliza **macOS en una MacBook Pro de 2019 con procesador Intel**, VS Code y la extensión oficial de Codex.
- Tiene experiencia como desarrollador de software. Prefiere explicaciones claras y código mantenible, pero solicita avanzar **un paso a la vez**.
- ChatGPT se utiliza para estrategia editorial, investigación y generación de guiones. Codex en VS Code se utiliza para inspeccionar y modificar los **archivos locales** de la aplicación, con los permisos correspondientes.
- Los **proyectos de ChatGPT no son accesibles automáticamente desde Codex**. El vínculo entre ambos será el intercambio explícito de archivos exportados, salvo que posteriormente se apruebe y desarrolle una integración auténtica.
- No declarar que se ejecutaron comandos, se generaron archivos, se hicieron búsquedas o se publicaron videos sin pruebas.

### 1.3. Objetivos del producto

1. Administrar tres identidades editoriales separadas desde un panel unificado.
2. Convertir guiones y planes de escenas en proyectos audiovisuales **editables**, reproducibles y guardados localmente.
3. Generar video horizontal para YouTube y piezas verticales independientes para Shorts, TikTok, Instagram Reels y Facebook Reels.
4. Producir **primero en inglés estadounidense (`en-US`)** los guiones finales, narraciones, subtítulos, títulos, miniaturas, descripciones, Shorts y paquetes de publicación de los **tres canales**. Permitir versiones adicionales en español latinoamericano (`es-419`) después de aprobación, sin alterar ni retrasar el paquete inglés.
5. Reducir el trabajo manual con procesos reutilizables, cachés y automatizaciones seguras.
6. Disponer de una vista previa y una **etapa de aprobación humana obligatoria** antes de subir o publicar.
7. Registrar costos, fuentes, licencias, versiones y resultados para poder mejorar el sistema con evidencia.

### 1.4. Lo que NO debe asumir Codex

- Que están creadas las cuentas o canales públicos de YouTube.
- Que ya existen credenciales para OpenAI, TTS, generadores de imágenes/video o APIs de redes sociales.
- Que el plan ChatGPT Plus incluye uso gratuito o ilimitado de APIs externas.
- Que se dispone de una conexión directa a los proyectos o memorias de ChatGPT.
- Que el propietario vive o tributa en Estados Unidos, ni que quiere falsificar ubicación con VPN.
- Que un render, una subida, una monetización o una prueba de retención ya tuvieron lugar.
- Que se instalaron todas las dependencias de Python necesarias para la aplicación.

---

## 2. Canales y fuentes editoriales

### 2.1. Los tres canales

| ID | Carpeta | Canal | Personalidad predominante | Duración orientativa del largo |
|---|---|---|---|---|
| `MIS` | `canales/01_misterios/` | Misterios e Historias Reales | Investigador documental: serio, intrigante, pausado, respetuoso | 8–15 min |
| `TEC` | `canales/02_tecnologia_ia/` | Tecnología e Inteligencia Artificial | Explorador tecnológico: ágil, claro, crítico, demostrativo | 8–12 min |
| `CIE` | `canales/03_ciencia_curiosidades/` | Ciencia y Curiosidades | Divulgador curioso: cálido, sorprendido, preciso, didáctico | 8–12 min |

Cada canal plantea **tres Shorts independientes por video largo** como meta editorial. La cadencia eventual es de hasta un largo diario por canal, pero la fase piloto debe validar calidad, tiempo de trabajo, costos y retención antes de escalar.

### 2.2. Documentos obligatorios

Leer antes de implementar comportamientos específicos de cada canal:

- `canales/01_misterios/REGISTRO_MAESTRO.md`
- `canales/02_tecnologia_ia/REGISTRO_MAESTRO.md`
- `canales/03_ciencia_curiosidades/REGISTRO_MAESTRO.md`

Esos registros ya contienen la identidad, los pilares, reglas narrativas, ideas iniciales y criterios editoriales. **No sustituirlos por aproximaciones resumidas ni inventar nuevos lineamientos contradictorios.** 

**Decisión editorial más reciente (2026-10-26): los tres canales se producirán en inglés estadounidense como idioma principal.** Los `REGISTRO_MAESTRO.md` existentes se redactaron antes de esta decisión y pueden especificar español latinoamericano como idioma del canal. **En ese punto concreto, esta decisión posterior prevalece**: el idioma de producción predeterminado será `en-US` en los tres canales, mientras permanecen intactos sus temas, personalidad, rigor y estructura narrativa. Codex debe **informar de esta discrepancia y proponer actualizar los registros en un paso separado**, nunca reescribirlos sin permiso. El idioma español de las instrucciones técnicas o de la interfaz **no define el idioma de los videos**.

### 2.3. Jerarquía de instrucciones y datos

1. Solicitud explícita más reciente y autorizada del propietario.
2. Restricciones de seguridad, políticas aplicables y permisos reales de ejecución.
3. Este `AGENTS.md` para el trabajo de ingeniería y la arquitectura general.
4. `REGISTRO_MAESTRO.md` de cada canal para identidad editorial y requisitos de contenido.
5. Datos reales de episodio, recursos, fuentes, historial y métricas.
6. Valores por defecto de la aplicación.

Si dos documentos se contradicen, señalar el conflicto y proponer una decisión antes de modificar la fuente. No reinterpretar el registro de un canal para aplicarlo automáticamente a otro.

### 2.4. Diferencias que deben preservarse

**Misterios (`MIS`)**
- Inicio con un hecho extraño comprobable, pregunta relevante o contradicción real.
- Investigación con cronología, pistas, fuentes y resolución honesta sobre lo que se conoce.
- Nunca inventar testigos, diálogos o pensamientos de personas reales; distinguir recreaciones y teorías.
- Shorts: pista intrigante, giro o documento decisivo, creencia popular frente a evidencia.
- Recursos visuales prioritarios: documentos, mapas, fotografías autorizadas, líneas temporales y reconstrucciones rotuladas.

**Tecnología e IA (`TEC`)**
- Inicio con problema concreto, resultado o demostración real.
- Explicar procedimiento, limitaciones, costos y casos de uso con lenguaje claro.
- Nunca inventar pruebas, benchmarks, capturas de pantalla, rendimiento ni accesibilidad de herramientas.
- Shorts: demostración real, explicación breve, consejo o comparación.
- Recursos prioritarios: capturas reales, diagramas, antes/después verificables y comparaciones legibles.

**Ciencia y Curiosidades (`CIE`)**
- Inicio con pregunta contraintuitiva o fenómeno fascinante.
- Conectar intuición, evidencia, explicación y consecuencia; marcar experimentos mentales como hipotéticos.
- Distinguir conocimiento establecido, hipótesis, simulaciones y especulación.
- Shorts: pregunta y respuesta, dato comprobado contextualizado, experimento mental con supuestos.
- Recursos prioritarios: animaciones explicativas, diagramas, escala, modelos y experimentos bien contextualizados.

### 2.5. Idioma principal y público objetivo: decisión de producto obligatoria

**Los tres canales serán ENGLISH-FIRST desde el lanzamiento. El contenido público primario será en inglés estadounidense (`en-US`).** La aplicación, sus botones y las conversaciones de desarrollo pueden estar en español para comodidad del propietario, pero **eso nunca debe provocar que el sistema genere en español el guion o la voz de un video por defecto**.

**Configuración por defecto que debe respetar el software cuando se implemente:**

| Propiedad | Valor inicial | Significado |
|---|---|---|
| `primary_content_language` | `en-US` | Guion y narración originales, no doblaje posterior |
| `primary_target_market` | `US` | Mercado editorial y comercial prioritario; no residencia simulada |
| `secondary_content_language` | `es-419` | Localización posterior, opcional y aprobada |
| `admin_interface_language` | `es-419` | Interfaz y comunicación de desarrollo en español |
| `narration_accent` | `en-US` | Pronunciación estadounidense natural, salvo casos justificados |
| `default_video_metadata_language` | `en-US` | Título, descripción, subtítulos, texto gráfico, portada y Shorts |
| `publication_country_claim` | `actual_verified_information` | Nunca falsificar país de residencia o de pagos |

**Audiencia prioritaria:** espectadores estadounidenses angloparlantes. Como públicos secundarios compatibles con el mismo contenido, considerar Canadá, Reino Unido, Australia y otras audiencias que comprendan inglés. Priorizar comprensión, interés real y retención; no afirmar que una IP estadounidense garantiza alcance ni monetización.

**Reglas de producción obligatorias:**

1. Investigar qué temas son interesantes para el público objetivo, contrastando evidencia y fuentes, sin asumir que todo contenido de Estados Unidos tiene éxito global.
2. Generar el **título de trabajo, la premisa, el gancho, el guion maestro y los tres Shorts originalmente en inglés**, con naturalidad de un creador estadounidense, no como traducción literal del español.
3. Preparar narración TTS o grabada con voz inglesa natural, buena entonación y pronunciación de nombres, términos técnicos y lugares; comprobar la calidad escuchando muestras antes de aprobar el episodio.
4. Generar subtítulos/captions en inglés, corregidos y sincronizados; cualquier texto dentro del video y la miniatura debe estar en inglés en el paquete principal.
5. Preparar títulos, descripciones, llamadas a la acción y copies de distribución en inglés para YouTube, TikTok, Instagram Reels y Facebook Reels.
6. Adaptar las referencias culturales, metáforas, medidas y ejemplos al público cuando tenga sentido. Conservar cifras, fechas y hechos exactos; no convertir unidades sin comprobación ni deformar fuentes.
7. Entregar **un video largo + tres Shorts independientes EN INGLÉS** como paquete principal por episodio. Una versión española o doblada es un paquete adicional, **no un sustituto** de ese entregable.
8. Permitir doblaje/localización al español más adelante, si el propietario lo decide; que sea una adaptación bien revisada, con voz, subtítulos y metadatos propios.
9. Etiquetar cada artefacto con idioma, región, estado y versión para evitar exportar o publicar la narración equivocada.
10. No instalar ni contratar servicios de doblaje, TTS o publicación sin autorización explícita.

**Dónde se administran los canales:** usar el país, domicilio y datos fiscales **reales y verificables** del propietario o entidad legítima. Colombia puede ser la sede administrativa mientras el contenido apunta a audiencias estadounidenses. **No implementar VPN para aparentar residencia estadounidense, datos ficticios de AdSense ni declaraciones fiscales falsas**. Los ingresos publicitarios dependen de la audiencia efectiva, el tema, los anunciantes y otros factores; el idioma y el país seleccionado no garantizan un RPM.

### 2.6. Identidad narrativa en inglés: cada canal conserva una voz distinta

| Canal | Voz original en inglés | Sensación principal | Gancho preferido | Evitar |
|---|---|---|---|---|
| `MIS` Misterios e Historias Reales | **Calm investigative documentary narrator**: medium-low pitch, measured pace, deliberate silence, empathy | Suspense supported by evidence | An unusual, sourced detail or credible contradiction | Sensationalism, fictitious dialogue, unsupported accusations |
| `TEC` Tecnología e Inteligencia Artificial | **Confident tech explorer**: energetic, concise, conversational, skeptical | Discovery + practical value | A verifiable demonstration, problem or result | Hype without testing, invented benchmarks, empty buzzwords |
| `CIE` Ciencia y Curiosidades | **Wonder-driven science storyteller**: warm, lively, clear and intellectually honest | Awe + understanding | A counterintuitive question or experiment | Pseudoscience, misleading simulations, invented certainty |

**Cómo debe sonar cada uno (ejemplos ilustrativos que no afirman hechos de una historia concreta):**

- `MIS`: “The records tell one story. But a single detail raises a much harder question.” No utilizar este gancho si no existen registros y contradicción documentados.
- `TEC`: “Can this tool actually do what it promises? We’ll test it, measure the results, and show you where it falls short.” Solo afirmar pruebas cuando se hayan realizado.
- `CIE`: “What would happen if you could see the world the way a different animal does? The answer starts with how vision really works.” Desarrollar únicamente con fuentes científicas.

**Dirección de locución:** inglés estadounidense claro, sin acentos caricaturescos; cambios de velocidad y pausas según el tipo de historia. Escribir oraciones pronunciables, contracciones naturales cuando correspondan y vocabulario accesible. Evitar frases con aspecto de traducción automática. Separar notas de voz del texto leído.

### 2.7. Enganches, retención y distribución para la audiencia angloparlante

- **3–8 segundos iniciales:** presentar una pregunta, contradicción, demostración o consecuencia intrigante directamente en inglés. No iniciar con “Hey guys, welcome back” ni largas presentaciones.
- **Antes de 30 segundos:** confirmar que la pregunta o promesa del título y de la miniatura está respaldada por el contenido real del episodio.
- **Durante el desarrollo:** introducir evidencia, decisiones, pruebas, ejemplos, descubrimientos o matices nuevos; no utilizar preguntas vacías o cortes arbitrarios como sustituto de sustancia.
- **Desenlace:** entregar la respuesta prometida y distinguir hechos, límites y dudas restantes.
- **Cada Short:** crear un gancho, desarrollo y recompensa autosuficientes para consumo vertical, con locución y subtítulos en inglés.
- **SEO y descubrimiento:** escribir títulos/keywords de manera natural para hablantes de inglés. Los temas deben seleccionarse por relevancia, interés y calidad, no por repetir palabras clave.
- **Experimentos editoriales:** evaluar varios formatos de hooks, títulos y miniaturas con datos reales, sin prometer que un umbral de retención garantice viralidad.
- **Métricas posteriores:** segmentar alcance, CTR, retención, espectadores e ingresos por país e idioma cuando existan datos verificables; comprobar si efectivamente estamos llegando a EE. UU.

---

## 3. Objetivo funcional y experiencia de usuario

### 3.1. Vista general de producto

Diseñar un panel que permita pasar de la idea al video final sin perder trazabilidad de guiones, recursos, ediciones ni versiones. El usuario debe poder intervenir en cada escena cuando no esté conforme con el resultado automático.

### 3.2. Módulos previstos, por etapas

**A. Dashboard y selección de canal — primera fase**
- Tarjetas independientes para `MIS`, `TEC` y `CIE`.
- Nombre, identificador y resumen de identidad editorial obtenido de fuentes locales verificadas; mostrar **idioma principal `English (US)`** y **mercado objetivo `United States`** para los tres canales.
- Seleccionar canal, navegar a su vista y consultar el estado editorial básico.
- Mensajes claros cuando falten registros o haya datos incompletos.

**B. Administración de episodios**
- Crear, importar, editar, duplicar y archivar episodios sin destruir archivos.
- Estados controlados: `idea`, `investigacion`, `guion`, `aprobado_guion`, `produccion`, `revision`, `exportado`, `listo_para_publicar`, `publicado` y `bloqueado` si hay errores de derechos o seguridad.
- Identificadores estables e independientes de los títulos y nombres de archivo.
- Historial básico de versiones y fecha de modificación.

**C. Importación estructurada de guiones**
- Inicialmente admitir texto o Markdown; luego un contrato JSON validado.
- Separar el texto que se narra de las instrucciones de edición y de las citas.
- Permitir dividir el guion en escenas y reorganizarlas manualmente.
- Señalar si un contenido importado no tiene fuentes suficientes o si el idioma es desconocido.

**D. Guion visual y edición de escenas**
- Lista o línea de tiempo con escenas, duración, voz, recursos, subtítulos y transiciones.
- Cambiar imágenes, recortar tiempos, ajustar zoom/paneo, volumen y orden de escenas.
- Mostrar vista previa rápida sin obligar a renderizar toda la película.
- Mantener cambios editables: evitar que solo exista un MP4 final sin proyecto fuente.

**E. Narración y audio**
- Importar audio grabado manualmente o conectar proveedores TTS después de aprobación.
- Voces y parámetros propios por canal e idioma; diccionarios de pronunciación cuando haga falta.
- Preescucha por escena y regeneración selectiva sin rehacer todo.
- Música y efectos con procedencia/licencia registrada; control de volúmenes y pausas.
- No clonar voces de terceros sin autorización.

**F. Imágenes, clips y generación por IA**
- Subir imágenes y clips del usuario, verificar formato y licencia cuando corresponda.
- Generar instrucciones visuales basadas en una escena; generación real solo con proveedor integrado.
- Cachear recursos con identificadores y versionado; permitir sustituciones manuales.
- Identificar material real, ilustración, simulación, recreación o contenido sintético.

**G. Motor de composición de video**
- Combinar recursos visuales, audio, música, subtítulos, transiciones y efectos.
- Exportar a MP4 con perfiles reproducibles; guardar logs de FFmpeg y reportar errores.
- Soportar distintos tamaños y duraciones sin deformar rostros ni recortar texto esencial.
- Priorizar renderizado local eficiente y evitar trabajo repetido mediante caché.

**H. Shorts y distribución vertical**
- Tres guiones verticales **independientes** por episodio largo, no tres recortes al azar.
- Adaptación de ritmo, encuadre, subtítulos, cierre y recursos para móvil.
- Exportes sin marcas de agua ajenas para YouTube Shorts, TikTok, Reels y Facebook Reels.
- Permitir revisión individual de cada vertical.

**I. Idiomas y localización**
- Variante **EN-US obligatoria y predeterminada** de guion, narración, subtítulos, miniatura y metadatos; variante **ES-419 opcional** y posterior, con temporización propia cuando sea necesario.
- Revisar términos científicos, nombres propios, pronunciación y localismos.
- Distinguir pistas de audio alternativas de renders independientes; no asumir que YouTube ofrece automáticamente la misma función a todos los canales.

**J. Títulos, miniaturas y paquete de publicación**
- Variantes de título y conceptos de miniatura no engañosos.
- Descripción, etiquetas relevantes, referencias y texto adaptado a cada plataforma.
- Lista de control de derechos, exactitud, material sintético y aprobación previa.
- Exportar los metadatos en archivos locales incluso sin API conectada.

**K. Publicaciones e integraciones — fase posterior**
- Integración opcional con APIs oficiales, autenticación OAuth y permisos mínimos.
- Subida inicial **privada o no listada**, tras aprobación explícita y verificación de estado.
- Publicación pública/programación solo como acción adicional autorizada; nunca como efecto secundario de generar un video.
- Registro auditable de intención, solicitud, respuesta de la plataforma y enlace real.
- Nunca guardar contraseñas de Google ni tokens sin protección apropiada.

**L. Analítica y mejora**
- Registro de métricas reales aportadas por el usuario o integraciones autorizadas.
- Comparación por canal, formato, idioma y período.
- CTR, retención, tiempo de visualización y RPM solo cuando exista fuente real y contexto pertinente.
- No inventar resultados, tendencias, métricas privadas de competidores ni causas de rendimiento.

### 3.3. Experiencia de usuario

- **Interfaz administrativa en español**, con textos concisos y errores explicativos; los contenidos exportados se generan **en inglés estadounidense** de forma predeterminada.
- Barra lateral o navegación simple: **Inicio / Canal / Episodios / Editor / Exportaciones / Ajustes** según implementación disponible.
- Las funciones futuras se muestran como pendientes o se omiten; **no colocar botones que simulen funcionar**.
- Antes de acciones costosas o irreversibles, mostrar alcance, costo estimado si existe y confirmación.
- Guardar cambios explícitamente y mostrar estado de guardado; si existe autoguardado, verificarlo con pruebas.
- Recuperar sesiones sin perder escenas ni medios.

---

## 4. Tecnologías y entorno confirmado

### 4.1. Estado de herramientas en la Mac

**Confirmado por salida de Terminal compartida por el propietario:**

| Componente | Estado | Evidencia/observación |
|---|---|---|
| Equipo | MacBook Pro 2019 Intel | Información confirmada por el propietario; no es Mac M4 |
| Homebrew | Presente | Instalación Intel en `/usr/local` |
| Python | `3.12.16` | `python3.12 --version` |
| FFmpeg | `9.0.2` | `ffmpeg -version`, salida correcta, código de salida 0 |
| Entorno virtual | `.venv` creado y activado | Ruta Python confirmada |
| VS Code | Instalado y carpeta confiable | Confirmado por el propietario |
| Codex | Extensión instalada y sesión iniciada | Confirmado por el propietario |
| Streamlit | **Pendiente de comprobar** | Se propuso instalarlo; no hay confirmación de instalación exitosa |
| Node.js/npm | **No requeridos actualmente** | Hubo intento anterior de instalación, interrumpido; no asumir estado |

**Ruta confirmada del intérprete virtual:**

`/Users/samacostar/Documents/YouTubeStudioAI/.venv/bin/python`

**Raíz esperada:**

`~/Documents/YouTubeStudioAI/`

No ejecutar una reinstalación automática de Python o FFmpeg. No actualizar versiones ni cambiar de plataforma sin consentimiento.

### 4.2. Stack inicial

- **Python 3.12** como lenguaje principal.
- **Streamlit** como interfaz local inicial, sujeto a verificación de instalación.
- **FFmpeg 9.0.2** para procesamiento multimedia.
- **SQLite y archivos del sistema** para persistencia local en etapas posteriores.
- Biblioteca estándar de Python cuando resulte suficiente.
- `venv` para aislar dependencias.
- `pytest` como opción futura de pruebas, solo después de aprobación de instalación.

**No introducir Node.js, npm, React, Electron, Docker ni infraestructura cloud** por comodidad o moda. Si un requerimiento futuro hace necesario cambiar el stack, explicar ventajas, costos, alternativas y migración; pedir autorización.

### 4.3. Compatibilidad con equipo Intel

- No asumir aceleración Apple Silicon, Neural Engine, Metal específico de M-series ni modelos locales que requieran GPUs no disponibles.
- FFmpeg declara `videotoolbox` habilitado en la compilación instalada, pero **comprobar disponibilidad real del codificador y del formato solicitado antes de usar aceleración por hardware**.
- Para renders exigentes, diseñar colas, barra de progreso, controles de calidad y trabajos cancelables cuando lleguen esas fases.
- Evitar renderizar cuatro versiones completas durante cada cambio de una sola escena.

### 4.4. Versionado y dependencias

- Mantener un registro de dependencias explícitas y sus versiones en el proyecto.
- Comprobar cada instalación dentro de `.venv` usando su Python, no el Python global.
- No ejecutar `pip install`, `brew install` u otros instaladores sin autorización cuando agreguen dependencias nuevas.
- Los comandos de terminal deben venir listos para copiar y pegar, con su propósito y salida esperada.

---

## 5. Arquitectura de carpetas y persistencia

### 5.1. Estructura inicial existente

```text
YouTubeStudioAI/
├── AGENTS.md
├── .venv/                             # entorno virtual: no editar ni subir al repositorio
├── app/                               # código de la interfaz y lógica modular
├── config/                            # configuración local (sin credenciales en Git)
├── shared/                            # recursos comunes con licencia trazable
└── canales/
    ├── 01_misterios/
    │   └── REGISTRO_MAESTRO.md
    ├── 02_tecnologia_ia/
    │   └── REGISTRO_MAESTRO.md
    └── 03_ciencia_curiosidades/
        └── REGISTRO_MAESTRO.md
```

No borrar ni reubicar estos directorios sin permiso. **Las carpetas de episodios descritas a continuación son una propuesta futura**, no deben darse por creadas.

### 5.2. Organización futura sugerida por episodio

```text
canales/01_misterios/
├── REGISTRO_MAESTRO.md
└── episodios/
    └── MIS-0001/
        ├── episode.json                # estado, idioma, metadatos, referencias
        ├── fuentes.md                  # trazabilidad de hechos y derechos
        ├── guion/
        │   ├── en.md                   # ORIGINAL EN-US: obligatorio
        │   └── es.md                   # localización opcional, posterior
        ├── escenas/
        │   └── scenes.json             # guion técnico editable
        ├── recursos/
        │   ├── imagenes/
        │   ├── clips/
        │   ├── audio/
        │   └── licencias.json
        ├── shorts/
        │   ├── S1/
        │   ├── S2/
        │   └── S3/
        ├── previews/
        ├── exports/
        └── logs/
```

Replicar el modelo por canal sin mezclar fuentes, medios, idiomas ni configuraciones.

### 5.3. Política de archivos

- Utilizar identificadores permanentes (`MIS-0001`, `TEC-0001`, `CIE-0001`) y rutas relativas a la raíz del proyecto siempre que sea posible.
- Evitar colisiones de nombre al exportar por idioma, formato y versión.
- Guardar archivos derivados separados de los materiales fuente y **nunca sobrescribir originales sin aviso**.
- Validar nombres de archivo y rutas; impedir path traversal al importar proyectos o ZIP.
- Registrar fecha, versión, hashes o tamaños cuando sea útil para detectar cambios.
- No copiar secretos dentro de manifiestos ni registros editoriales.
- Si Documentos se sincroniza con iCloud, evitar archivos temporales gigantes en rutas sincronizadas sin una decisión expresa; proponer carpeta de caché local configurable.

### 5.4. Persistencia y estados

- Para el primer dashboard, **no añadir base de datos si no es necesaria**: leer los registros como datos locales.
- Para ediciones y proyectos duraderos, preferir SQLite con esquema/migraciones claras y almacenamiento de multimedia como archivos.
- Escrituras atómicas cuando corresponda, copias de seguridad y recuperación ante fallo.
- Distinguir `guardado`, `pendiente_de_guardar`, `renderizando`, `error` y `publicado` solo con evidencia real.
- Mantener trazabilidad del resultado de cada render y de cada eventual intento de subida.

---

## 6. Reglas de desarrollo de software

### 6.1. Calidad y mantenibilidad

- Código legible, modular, documentado sin comentarios redundantes.
- Tipado en servicios, modelos y funciones de negocio cuando aporte claridad.
- Separar presentación Streamlit, validación, servicios, repositorios y llamadas a FFmpeg.
- No concentrar la aplicación completa en `app/main.py`; ese archivo debe actuar como entrada o enrutador básico.
- Priorizar funciones pequeñas, parámetros explícitos y dependencias inyectables.
- No acoplar la lógica a un proveedor específico de IA.
- Evitar sobreingeniería durante el primer dashboard.

### 6.2. Seguridad y privacidad

- Nunca imprimir, transmitir ni versionar credenciales, tokens OAuth, cookies, contraseñas o información privada del propietario.
- Variables de entorno o almacenes seguros para configuración sensible; `.env` fuera de Git y con ejemplo sin secretos si se requiere.
- No ejecutar código arbitrario de guiones importados, plantillas no confiables o respuestas de modelos.
- Validar tipo MIME/extensión, peso y tamaño de imágenes, audio y video.
- Validar argumentos de FFmpeg mediante listas de argumentos, evitando composición de comandos de shell con entradas no confiables.
- No habilitar acceso público al servidor Streamlit por defecto: uso local exclusivamente hasta que se defina autenticación y despliegue.
- No borrar contenido, mover carpetas importantes o ejecutar `rm -rf` sin aprobación explícita y explicación del efecto.
- No modificar el entorno virtual manualmente ni registrar `.venv/` en control de versiones.

### 6.3. Robustez del procesamiento

- Usar `ffprobe` para obtener información real de multimedia en vez de asumir duración/resolución.
- Manejar archivos no válidos, medios ausentes, audios vacíos y procesos interrumpidos.
- Mostrar stderr relevante de FFmpeg sin exponer datos sensibles.
- Usar archivos temporales y reemplazo seguro al completar exportes.
- Evitar bloquear indefinidamente la interfaz; en etapas futuras, gestionar jobs y progreso.
- Registrar duración y tamaño del render para estimar costos de cómputo.

### 6.4. Pruebas

- Probar rutas y existencia de los tres registros.
- Probar cambio de canal sin mezcla de datos.
- Probar manejo de archivos o registros faltantes.
- Probar modelos y serialización antes de activar proyectos persistentes.
- Probar más adelante renderes de 5–10 segundos con medios de prueba autorizados antes de un episodio completo.
- Probar horizontal/vertical, subtítulos, acentos y caracteres especiales.
- Diferenciar prueba simulada y prueba de integración verdadera.

### 6.5. Git y documentación

- Si aún no hay repositorio Git, proponer inicializarlo, pero pedir permiso.
- Crear `.gitignore` cuando se apruebe, incluyendo `.venv/`, cachés, renders pesados y secretos.
- Mantener `README.md` actualizado sobre requisitos y comandos reales de ejecución.
- No inventar instrucciones de ejecución o resultados de tests.
- Mostrar un resumen de archivos modificados, riesgos conocidos y cómo verificar cada cambio.

---

## 7. Flujo editorial, guiones y contrato de datos

### 7.1. Flujo completo objetivo

```text
Investigación y selección de idea
    → validación de fuentes y licencias
    → guion narrativo
    → aprobación del guion
    → storyboard y escenas estructuradas
    → narración por idioma
    → imágenes, videos y música
    → montaje + subtítulos
    → vista previa y correcciones
    → control de calidad
    → exportación
    → aprobación de subida
    → subida privada/no listada (solo fase futura)
    → autorización de publicación
    → analítica y aprendizaje
```

Cada flecha es un **estado verificable**, no una automatización garantizada desde el inicio.

### 7.2. Reglas narrativas comunes de los tres canales

1. **Primeros 3–8 segundos:** presentar una pregunta, contradicción, resultado sorprendente o conflicto; evitar saludos largos.
2. **Primeros 30 segundos:** demostrar que el contenido responde a la promesa del título y la miniatura.
3. **Desarrollo:** nueva información, pruebas, giros o demostraciones genuinas; nunca relleno para alcanzar una duración artificial.
4. **Desenlace:** contestar la pregunta principal y reconocer incertidumbres importantes.
5. **Tres Shorts por largo:** cada uno con gancho, desarrollo y recompensa; no limitarse a cortar tres fragmentos sin contexto.

Los tiempos propuestos son heurísticas editoriales sujetas a experimentación, no reglas oficiales de rendimiento garantizado.

**Aplicación del idioma:** estos cinco principios se implementan en cada canal **con guiones originales en inglés estadounidense** y Shorts originales en inglés. No generar la narración principal en español por el hecho de que el prompt o el `REGISTRO_MAESTRO.md` estén escritos en español.

### 7.3. Contrato de entrada para importar un episodio — propuesta, NO implementado

Cuando se desarrolle el importador, diseñar un modelo versionado y documentado con campos como:

```json
{
  "schema_version": "1.0",
  "episode_id": "MIS-0001",
  "channel_id": "MIS",
  "title_working": "Unpublished example topic",
  "language": "en-US",
  "target_market": "US",
  "status": "guion",
  "central_question": "What question does this episode answer?",
  "sources": [],
  "narration": "Approved English voice-over text",
  "scenes": [
    {
      "scene_id": "S001",
      "narration": "Narration for this scene in natural American English",
      "visual_direction": "Visual direction for the editor",
      "asset_ids": [],
      "estimated_seconds": 8,
      "music_notes": "",
      "source_refs": []
    }
  ],
  "shorts": [
    {"short_id": "S1", "narration": "Original English short-form script"},
    {"short_id": "S2", "narration": "Another standalone English short-form script"},
    {"short_id": "S3", "narration": "A third complete English short-form script"}
  ]
}
```

Este JSON es un **ejemplo de futuro contrato**, no un archivo que exista ni una especificación cerrada. La validación real debe rechazar campos erróneos y garantizar que el `channel_id` coincida con la ubicación del episodio. Un contrato definitivo se aprobará cuando toque construir el importador.

### 7.4. Guion y narración

- Distinguir `narration` (palabras pronunciadas) de `production_notes` (edición), `sources` (evidencia), `captions` (subtítulos) y `metadata` (publicación).
- Nunca enviar instrucciones como `[PAUSA]` al proveedor de voz sin traducirlas a parámetros o pausas compatibles.
- Guardar duración real del audio después de sintetizarlo; no confiar solo en estimaciones por cantidad de palabras.
- Si se modifica un guion, invalidar solo escenas o audios dependientes de ese cambio.
- **Inglés estadounidense es el idioma ORIGINAL, no la traducción**. Escribir con naturalidad, pronunciación adecuada y revisión específica de nombres propios; preparar fonética o diccionarios de pronunciación cuando TTS falle.
- Texto hablado, captions, rótulos, títulos, textos de miniatura y copies publicitarios deben mantenerse consistentes en `en-US` en el paquete principal.
- La futura versión `es-419` requerirá adaptación cultural y revisión editorial independientes; no sustituir automáticamente un archivo inglés por uno español.

### 7.5. Recursos y derechos

- Cada recurso debe tener procedencia, dueño/licencia conocida cuando corresponda, uso permitido, fecha de incorporación e identificación de IA sintética.
- Si los derechos de un clip son desconocidos, **no marcarlo como publicable**.
- No depender de descargas no autorizadas de videos de competidores.
- Respetar restricciones de licencias de música, bancos visuales y APIs generativas.

---

## 8. Especificaciones audiovisuales, idiomas y publicación

### 8.1. Perfil de exportación propuesto — sujeto a pruebas

| Uso | Aspecto | Resolución inicial orientativa | Formato |
|---|---|---|---|
| YouTube largo | 16:9 | 1920×1080 | MP4 / H.264 / AAC |
| Shorts, TikTok, Reels | 9:16 | 1080×1920 | MP4 / H.264 / AAC |
| Vista previa rápida | 16:9 o 9:16 | Reducida y configurable | Archivo local ligero |

Estos valores son **objetivos iniciales**, no resultados validados. El perfil real debe respetar medios de entrada, compatibilidad, calidad y limitaciones de cada plataforma. No asumir que una duración fija de Shorts aplica siempre ni que una exportación garantiza aceptación de publicación.

### 8.2. Subtítulos

- Soportar archivos `.srt` o formatos equivalentes cuando se implemente.
- Sincronizar con audio real y revisar cortes por frase y lectura en móvil.
- Generar y verificar **primero subtítulos en inglés (`en-US`)**; mantener otras versiones por idioma solo cuando se aprueben y corregir errores de transcripción.
- Evitar texto fuera de zonas seguras y subtítulos ilegibles.
- Permitir subtítulos incrustados o externos según el destino.

### 8.3. Ajustes visuales

- Mantener proporciones y recorte inteligente; nunca estirar imágenes.
- Para pasar de horizontal a vertical, prever reencuadre manual y pruebas con sujetos principales.
- Usar movimiento de imagen (pan/zoom) cuando aporte, evitando efectos repetitivos.
- Identificar recreaciones documentales y animaciones científicas como tales cuando sea relevante.

### 8.4. Exportación y revisión

Antes de marcar un episodio `listo_para_publicar`, verificar:

- Narración legible y sin silencios accidentales.
- Fuentes importantes correctas y accesibles.
- Recursos con derechos y atribuciones apropiadas.
- Formato/aspecto/tamaño correctos.
- Duraciones y sincronización correctas.
- Subtítulos revisados en los idiomas exportados.
- Título, miniatura y descripción coherentes.
- Divulgación de contenido sintético cuando corresponda.
- Aprobación explícita del propietario.

### 8.5. Publicación responsable

- Primero exportar localmente; las APIs se desarrollan solo en una fase posterior autorizada.
- Se debe poder generar un paquete de publicación **sin subir nada**.
- Si se habilita una API, el estado `exportado` no puede activar por sí solo una subida.
- Una subida privada y una publicación pública son **acciones distintas** y requieren controles claros.
- No afirmar que TikTok, Instagram o Facebook permiten exactamente la misma automatización; revisar las APIs disponibles y las condiciones de cada cuenta.

---

## 9. Integraciones externas, costos, monetización y métricas

### 9.1. Diseño por proveedores

Crear interfaces desacopladas en etapas posteriores para:

- Síntesis de voz (TTS).
- Generación y edición de imágenes.
- Generación de clips.
- Investigación o acceso a fuentes autorizadas.
- Almacenamiento externo, si se aprueba.
- Publicación mediante APIs oficiales.
- Analítica mediante APIs oficiales.

Cada integración debe declarar: proveedor, método de autenticación, permisos, costo estimable, límites de uso, manejo de errores, reintentos, salida y mecanismo para desactivar el servicio.

### 9.2. Control de presupuesto

- Antes de llamar a una API de pago, informar si la acción consume créditos o dinero.
- Mostrar costo estimado si existen tarifas verificadas y se conoce el volumen.
- Limitar regeneraciones automáticas y guardar resultados reutilizables.
- Permitir un modo de pruebas con recursos gratuitos/locales sin gastar en proveedores.
- No confundir el plan de ChatGPT con saldo de APIs de desarrolladores.

### 9.3. Monetización responsable

- Diseñar contenido original con intervención editorial real; evitar producción masiva repetitiva y material reutilizado sin valor añadido.
- No inventar cifras de CPM, RPM, impresiones, ingresos ni retención.
- No asumir que seleccionar el país Estados Unidos o utilizar VPN aumenta el RPM de YouTube.
- Priorizar contenido original en **inglés estadounidense para captar audiencia de EE. UU.**, con potencial adicional en Canadá, Reino Unido y Australia; optimizar temas, calidad, relevancia comercial y medición real sin prometer resultados.
- Registrar patrocinios y afiliaciones y facilitar su divulgación cuando corresponda.
- Consultar políticas vigentes de cada plataforma al implementar publicación y monetización.

### 9.4. Métricas cuando haya datos reales

Medir, según disponibilidad: impresiones, CTR, visualizaciones, tiempo de reproducción, retención al inicio, duración promedio vista, espectadores recurrentes, geografía de audiencia, suscriptores generados, RPM y costo de producción. **Priorizar comprobar proporción de audiencia y desempeño en Estados Unidos**, sin excluir otros países angloparlantes. Segmentar por canal, idioma, país, formato y período. Diferenciar observación y hipótesis; documentar experimentos.

### 9.5. Recursos oficiales de consulta

- Monetización: https://support.google.com/youtube/answer/1311392
- Retención de público: https://support.google.com/youtube/answer/9314415
- Contenido alterado o sintético: https://support.google.com/youtube/answer/14328491

Los enlaces son referencias a consultar cuando se necesiten; **no afirmar que se verificaron en tiempo real sin acceso web**.

---

## 10. Cómo debe trabajar Codex con el propietario

### 10.1. Prioridad absoluta: avanzar paso a paso

El propietario ha pedido explícitamente **no recibir una cadena larga de comandos de golpe**. Codex debe respetar ese ritmo:

1. Inspeccionar el estado real de la carpeta, archivos y dependencias.
2. Explicar en español el **único siguiente objetivo** y por qué importa.
3. Proponer el cambio mínimo verificable.
4. Pedir permiso antes de instalar paquetes, contratar servicios, añadir credenciales o modificar arquitectura.
5. Ejecutar únicamente el trabajo autorizado.
6. Verificar con una prueba real, si es posible.
7. Entregar los archivos modificados, resultado y **un siguiente paso**; esperar confirmación.

### 10.2. Cómo responder

- Ser claro, profesional y directo.
- Explicar la diferencia entre *lo que existe*, *lo que se recomienda* y *lo que falta*.
- Ofrecer comandos en bloques de código listos para copiar y pegar cuando el usuario los necesite.
- No convertir cada respuesta en una lista de diez instalaciones.
- Si el usuario reporta un error, leer la salida real y diagnosticarlo antes de recomendar reinstalar todo.
- Si se requieren varias decisiones independientes, explicar primero la decisión inmediata.
- Ante una limitación real de Codex, Streamlit, FFmpeg o ChatGPT, señalarla sin prometer capacidades inexistentes.

### 10.3. Comportamiento frente a cambios de alcance

- Si se solicita una mejora visual, modificar solo lo necesario y conservar la lógica.
- Si se solicita una nueva automatización, describir qué depende de servicios externos y cuánto puede costar.
- Si se solicita publicar, comprobar primero integración real, permisos, aprobación y cumplimiento.
- Si se solicita migración de tecnología, no borrar trabajo existente; preparar una propuesta justificada.

### 10.4. Formato de reporte tras cada tarea

```text
Objetivo realizado: ...
Archivos creados/modificados: ...
Comprobaciones ejecutadas: ...
Resultado observado: ...
Limitaciones o decisiones pendientes: ...
Siguiente paso propuesto (solo uno): ...
```

No utilizar “funciona correctamente” sin haberlo comprobado o sin indicar que la verificación debe realizarla el usuario.

---

## 11. Primera fase de desarrollo y criterio de aceptación

### 11.1. Estado actual que Codex debe respetar

- Los tres directorios de canal y sus `REGISTRO_MAESTRO.md` ya se copiaron a la Mac, según lo confirmado por el usuario; **verificar que existan en disco antes de usarlos**.
- `AGENTS.md` estará en la raíz del proyecto tras ser copiado.
- Python 3.12.16, FFmpeg 9.0.2 y `.venv` se confirmaron mediante comandos previos.
- La instalación de **Streamlit no ha sido confirmada**.
- **Nueva decisión confirmada:** todos los videos largos, narraciones, tres Shorts, textos de publicación y subtítulos **deben prepararse primero en inglés estadounidense (`en-US`)** para una audiencia prioritariamente de EE. UU. Los registros antiguos todavía pueden hablar de español: no cambiarlos sin permiso, pero **no usar español como idioma predeterminado del contenido**.
- No se ha autorizado todavía implementar la generación de voz, imágenes, montaje, Shorts o subida a plataformas.

### 11.2. Primera tarea de Codex — SOLO INSPECCIÓN

Cuando el usuario indique que está listo:

1. Verificar el workspace abierto y localizar `AGENTS.md`.
2. Revisar las tres rutas de `REGISTRO_MAESTRO.md` y leerlas sin modificarlas.
3. Comprobar que el intérprete seleccionado corresponde a `.venv/bin/python` y Python 3.12.
4. Comprobar si `streamlit` está instalado dentro de `.venv` **sin instalarlo**.
5. Identificar si existe código previo en `app/`; no sobrescribirlo.
6. Informar qué se encontró, qué falta y proponer un solo siguiente paso.
7. **Esperar aprobación para escribir código o instalar dependencias**.

### 11.3. Segunda tarea — SOLO CUANDO SE APRUEBE

Construir un dashboard básico con Streamlit que:

- Lea los tres registros desde sus carpetas.
- Muestre tres tarjetas con canal, ID y descripción fiel a cada registro.
- Permita seleccionar un canal y ver su identidad editorial sin modificar sus archivos.
- Maneje adecuadamente los errores si falta un registro.
- Mantenga separada la configuración de canales del diseño de la pantalla.
- Inicie localmente con un comando explícito y verificable.
- No llame a servicios externos ni genere videos.

### 11.4. Criterios de aceptación del dashboard

- Abre desde el entorno virtual correcto.
- Muestra exactamente los tres canales conocidos.
- No mezcla personalidad, datos ni carpetas.
- No crea publicaciones ni llama a APIs de pago.
- Cambiar de canal funciona sin excepciones.
- La interfaz administrativa es comprensible y usable en español, y muestra claramente que el **idioma por defecto de los contenidos es inglés estadounidense (`en-US`)** para los tres canales.
- Existe una verificación reproducible o una lista corta de comprobaciones manuales.
- No se han modificado los `REGISTRO_MAESTRO.md` sin autorización.

### 11.5. Evolución posterior — NO implementarla todavía

1. Estructura persistente de episodios y guardado.
2. Importación de guiones de ChatGPT.
3. Editor de escenas con previsualización.
4. Prueba mínima de FFmpeg con archivos locales de muestra.
5. Narración y subtítulos.
6. Integraciones opcionales de imagen/clip generativo.
7. Renderizado de largos y tres Shorts autónomos.
8. Localización opcional al español desde originales EN-US (el inglés ya es principal desde la primera fase).
9. Exportación de metadatos y publicación con aprobación explícita.
10. Métricas y optimización editorial basada en datos.

**No desarrollar varias de estas fases a la vez salvo autorización explícita del propietario.**

---

## Resumen operativo para Codex

**Tu función inmediata no es “crear toda la plataforma”.** Es leer este documento y los registros, confirmar el entorno y ayudar a construir una primera pantalla verificable. **Al crear módulos que generan o muestran guiones de producción, define el inglés estadounidense como idioma editorial por defecto de los tres canales y el mercado estadounidense como prioridad; la interfaz de administración permanece en español.** La aplicación se ampliará de manera modular hasta permitir un flujo profesional de producción audiovisual con tres canales independientes, sin exagerar capacidades, inventar evidencia ni publicar nada sin autorización.

**Primer mensaje recomendado que deberá recibir Codex al empezar:**

> «Lee `AGENTS.md` y los tres `REGISTRO_MAESTRO.md`. Ten presente la **decisión editorial posterior**: los tres canales tendrán **videos, voces, guiones y tres Shorts originales en inglés estadounidense (`en-US`)** y estarán orientados principalmente a espectadores de **Estados Unidos**, aunque la interfaz del programa permanezca en español. Por ahora NO modifiques archivos ni instales paquetes. Inspecciona el workspace, confirma el Python del `.venv`, verifica si Streamlit está disponible y dime qué falta para construir el dashboard inicial. Señala cualquier contradicción de idioma con los registros antiguos. Espero tu diagnóstico antes de autorizar cambios».


## Implementación autorizada — fase 1 de paquetes (2026-11-05)

La entrada `app/main.py` ofrece contexto por canal e importación/preparación ZIP.
La documentación operativa vigente de esta fase está en
`docs/phase1-package-import.md`. Reutiliza contrato editorial-package 1.0.0,
lector seguro y SQLite existente mediante migración aditiva 012.
No activa generación, render ni publicación desde la UI de esta fase.
Conservar datos, pilotos y dependencias históricas de CLI/worker.
Las instrucciones editoriales anteriores y en-US siguen vigentes.


## Implementación autorizada — fase 2 audiovisual (2026-11-05)

La solicitud posterior de fase 2 habilita producción local del largo desde los ZIP
validados, mediante el motor, cola y caché existentes. Prevalece sobre la restricción
de UI de fase 1. Ver `docs/phase2-audiovisual-production.md`. La migración 013
agrega pausa cooperativa y vínculos, sin eliminar datos. No habilitar fase 3 de
Shorts, publicación ni servicios de pago. Los visuales con derechos pendientes
conservan ese estado; un render local para revisión no implica autorización pública.


## Implementación autorizada — fase 3 de entregas (2026-11-05)

La solicitud posterior de fase 3 habilita Shorts independientes, QA y paquetes locales,
y prevalece sobre la exclusión de Shorts de fase 2. Ver `docs/phase3-delivery.md`.
La migración aditiva 014 conserva las entregas y candidatos; no altera originales.
Cada episodio tiene cuatro posiciones visibles y jobs independientes. Un faltante
permanece NEEDS_SCRIPT. No confundir un ZIP parcial con cuatro videos terminados.
El LLM opcional debe estar configurado explícitamente y sus borradores requieren
revisión. No habilita publicaciones, instalaciones ni servicios de pago.
La aprobación humana queda vinculada al contenido; QA técnica no aprueba derechos,
fuentes, pronunciación o subtítulos aproximados.

## Limpieza autorizada por el propietario — 2026-11-05

La solicitud posterior «elimina todo lo que no nos sirve y los videos viejos»
autoriza retirar código abandonado y derivados antiguos. Se conservó el flujo
ZIP/producción/QA/entrega y su último resultado; los pilotos y sus pantallas se
retiraron. Los originales importados y registros maestros permanecen intactos.

Arquitectura vigente: motor en `app/engine/`, entrada en `app/main.py` y
`app/workbench.py`. Ya no usar imports raíz audio/domain/ingestion/pipeline/rendering/
timing/ui ni restaurar bootstrap, proveedores o pantallas retirados solo para
satisfacer documentación histórica. README y `docs/cleanup.md` describen el estado
actual. Las migraciones SQL aplicadas permanecen inmutables. No regenerar videos
eliminados como efecto secundario de abrir la aplicación.
