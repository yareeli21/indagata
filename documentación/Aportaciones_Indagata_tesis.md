# Aportaciones al sistema Indagata

Durante el periodo trabajé en tres ejes del sistema Indagata (plataforma de microservicios para gestión y consulta de instrumentos de investigación): la indexación vectorial de instrumentos y su visualización, las reglas de privacidad por rol, y la integración entre la interfaz y el backend. Todo quedó integrado y publicado en la rama `pruebas` del repositorio.

## 1. Indexación de instrumentos y mapa vectorial

Me correspondió la indexación de los instrumentos y su representación en la interfaz como un mapa vectorial.

- Cada instrumento se fragmenta (*chunking*) y cada fragmento se convierte en un vector de 768 dimensiones con un modelo de *embeddings* multilingüe (*sentence-transformers*), almacenado e indexado en **ChromaDB** por similitud de coseno. La indexación se organiza por investigación.
- La vista **Espacio vectorial** proyecta esos vectores a 2D mediante **PCA** y los dibuja como un diagrama de dispersión coloreado por colección (KPIs e instrumentos).
- Sobre la indexación se montó el proceso **RAG**: el investigador agrupa instrumentos, pregunta en el chat, y el sistema vectoriza la pregunta, recupera por similitud los fragmentos más cercanos y los muestra como **fuentes citadas**. La generación con el modelo de lenguaje local (Ollama) se integró con **degradación controlada**: si el modelo no está disponible, el sistema igual recupera y muestra las fuentes, lo que permite demostrar la recuperación semántica —la parte sustantiva del RAG— de forma independiente.

## 2. Privacidad y control de acceso por rol

Dos reglas de autorización, reforzadas en el backend (no solo en la interfaz) para que no puedan eludirse por API:

- **Alta de usuarios solo para administradores:** un investigador que intente crear usuarios recibe 403; únicamente el administrador da de alta cuentas.
- **Borrado de instrumentos solo del propietario:** un investigador solo elimina los instrumentos que él subió (si no, 403: *"Solo puedes eliminar instrumentos que tú subiste"*); el administrador puede eliminar cualquiera.

Ambas se apoyan en autenticación por **JWT** emitido por el *api-gateway*, validado por cada microservicio antes de operar.

## 3. Integración frontend–backend

Conecté la interfaz (React + TanStack Router) con los microservicios (FastAPI), que antes usaban datos simulados en varias pantallas:

- **Autenticación** real por JWT contra el *api-gateway*.
- **Puerta de enlace única** (*api-gateway*) con enrutamiento transparente a los servicios de instrumentos, almacenamiento, metadatos y visualización.
- **Pipeline de carga completo:** carga del archivo → análisis estructural → registro de **metadatos Dublin Core** (inmutables) → **asociación de KPIs** por similitud semántica confirmada por el usuario, que enriquece el instrumento (cerrando el paso que faltaba, pues tenían metadatos pero no indicadores).
- **Servicio de almacenamiento** que recibe archivos y artefactos JSON, decide dónde guardarlos y devuelve su ubicación.

La integración se validó ejercitando el flujo completo sobre Docker (login, carga, metadatos, asociación de KPIs y recuperación RAG).

---

El trabajo quedó en la rama `pruebas`; la rama principal de refactorización se mantiene intacta a la espera del microservicio pendiente, para continuar sobre ella cuando esté disponible.
