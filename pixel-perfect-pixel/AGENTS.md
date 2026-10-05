# INDAGATA — reglas del proyecto

- Interfaz completamente en español (textos, rutas y nombres de dominio en el código).
- Los datos de ejemplo viven en `src/mocks/`; las pantallas NUNCA los importan directamente. Todo acceso pasa por funciones asíncronas en `src/api/`, que pueden resolver con mocks (`simularRed`) o con llamadas HTTP reales a la API FastAPI, sin tocar la UI.
- Conexión con el backend en curso: el login YA es real (JWT contra el api-gateway, `src/api/auth.ts` + helper `pedir` en `src/api/client.ts`) y la pantalla "Espacio vectorial" consume el analysis-service. El resto de endpoints (carga, instrumentos, chat, investigaciones, kpis) siguen con mocks (`simularRed`) por ahora.
- Base URLs del backend configurables vía `src/api/client.ts` (`API_URL` → api-gateway :8000, `ANALYSIS_URL` → analysis-service :8002). El JWT se guarda en localStorage (`indagata.token`) y se envía como `Authorization: Bearer` en las llamadas autenticadas.
- Organización por features en `src/features/{auth,upload,instruments,research,chat,kpis}/`; componentes compartidos en `src/components/`. Un componente por archivo con props tipadas.
- Tipos de dominio compartidos en `src/types/index.ts`, incluida la lista cerrada de niveles educativos.
- Enrutamiento con TanStack Router (archivos en `src/routes/`); el layout global es la ruta `_panel.tsx`. No se usa React Router ni Next.js.
- Colores, tipografía y sombras solo como tokens semánticos en `src/styles.css`; nunca clases de color literales en los componentes.
