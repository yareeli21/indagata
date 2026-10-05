# INDAGATA — Frontend

Interfaz web de INDAGATA: plataforma para subir, estandarizar, buscar y
consultar instrumentos de investigación educativa en México.

## Stack

- **React 19** + **TypeScript**
- **TanStack Start** (routing + SSR) y **TanStack Router**
- **TanStack Query** para estado de servidor
- **Vite 8** como bundler, con **Nitro** para el empaquetado de servidor
- **Tailwind CSS 4** + **Radix UI**
- **react-hook-form** + **zod** para formularios y validación
- **recharts** para gráficas

## Requisitos

- [Bun](https://bun.sh) (gestor de paquetes y runtime de scripts)

## Desarrollo

```sh
bun install
bun run dev
```

El servidor de desarrollo queda disponible en `http://localhost:8080`
(si el puerto está ocupado, Vite usa el siguiente libre).

### Variables de entorno

Copia `.env.example` a `.env` y ajústalo:

- `VITE_API_URL` — URL base del api-gateway (por defecto `http://localhost:8000`).
- `VITE_USAR_BACKEND` — `true` usa el backend real para autenticación; `false`
  corre todo con datos de ejemplo (mocks), sin necesidad de levantar servicios.

## Build

```sh
bun run build
```

Genera el bundle de cliente y el de servidor (SSR) bajo `.output/`.

## Arquitectura

- `src/api/` — único punto de acceso a datos. Las pantallas nunca importan los
  mocks directamente; todo pasa por funciones asíncronas aquí, para poder
  sustituirlas por llamadas HTTP sin tocar la UI.
- `src/features/{auth,upload,instruments,research,chat,kpis}/` — organización por
  dominio; un componente por archivo con props tipadas.
- `src/components/` — componentes compartidos.
- `src/routes/` — rutas de TanStack Router; el layout global es `_panel.tsx`.
- `src/types/index.ts` — tipos de dominio compartidos.
- `src/styles.css` — tokens semánticos de color, tipografía y sombras.
