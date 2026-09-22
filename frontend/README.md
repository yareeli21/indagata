# INDAGATA - Frontend

El frontend de INDAGATA es **una sola aplicación** que incluye tanto el landing animado como el sistema de gestión.

## Ejecutar

```bash
cd app
npm install
npm run dev
```

Abrir en `http://localhost:5173`

## Flujo de Navegación

```
http://localhost:5173/           → Landing animado
http://localhost:5173/login      → Autenticación
http://localhost:5173/app/*      → Sistema principal (protegido)
```

## Requisitos

- Node.js 18+
- Backend FastAPI corriendo en `http://localhost:8000`

## Notas

- La carpeta `landing/` es el proyecto original de animación. **Ya no es necesario ejecutarla por separado** — todo está integrado en `app/`.
- Para desarrollo, solo se necesita correr `app/`.
