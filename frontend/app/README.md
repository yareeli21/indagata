# INDAGATA - Frontend App

Sistema de gestión de instrumentos de investigación educativa.  
Incluye landing animado + sistema completo en una sola aplicación.

## 🚀 Ejecutar

```bash
npm install
npm run dev
# → http://localhost:5173
```

Backend requerido en `http://localhost:8000`

## 🗺️ Rutas

| Ruta | Descripción | Acceso |
|------|-------------|--------|
| `/` | Landing animado (logo → libro → frase) | Público |
| `/login` | Autenticación | Público |
| `/app/instrumentos` | Catálogo y detalle de instrumentos | Protegido |
| `/app/cargar` | Wizard de carga (5 pasos) | Protegido |
| `/app/chatbot` | Chatbot con IA | Protegido (placeholder) |
| `/app/kpis` | Dashboard de KPIs | Protegido (placeholder) |

## 🎬 Flujo completo

1. **`/`** — Landing: primera visita muestra animación completa, visitas siguientes van directo al estado final
2. Botón "Ingresar a Indagata" → **`/login`**
3. Login (dev: cualquier credencial) → **`/app/instrumentos`**
4. "Salir" en el header → **`/login`** (limpia sesión)
5. "← Volver al inicio" en login → **`/`**

## 📁 Estructura

```
src/
├── pages/
│   ├── LandingPage/          # Landing animado con framer-motion
│   │   └── components/       # CustomCursor, DustParticles, BookTransition
│   ├── LoginPage/            # Autenticación (placeholder)
│   ├── CargaInstrumentosPage/      # Wizard 5 pasos ✅
│   ├── VisualizacionInstrumentosPage/  # Catálogo + detalle ✅
│   ├── ChatbotPage/          # Placeholder
│   └── KpiPage/              # Placeholder
├── components/
│   ├── layout/MainLayout.tsx # Header + nav + footer
│   ├── instrumentos/         # Componentes de carga y visualización
│   └── common/               # Stepper, LoadingSpinner, Alerts
├── services/
│   ├── apiClient.ts          # Axios + interceptores
│   └── instrumentosService.ts # 12 métodos de API
├── types/
│   ├── index.ts              # Interfaces TypeScript
│   └── constants.ts          # Estados, labels, colores
└── routes/index.tsx          # React Router + guards
```

## 🔌 Conexión con Backend

El servicio `instrumentosService.ts` consume los endpoints de FastAPI en `http://localhost:8000`.

Todos los estados del wizard están controlados por el campo `estado` del backend:

```
pendiente → metadata_registrado → etl_pendiente → etl_aprobado → en_ingesta → vectorizado
```

## 🛠️ Scripts

```bash
npm run dev      # Desarrollo
npm run build    # Build producción
npm run preview  # Preview del build
```

## 🐛 Troubleshooting

**Pantalla en blanco**: Verificar que `src/index.css` use `@import "tailwindcss"` (no `@tailwind base/components/utilities`).

**Puerto ocupado**: Vite asigna el siguiente disponible (5174, etc.). Detener con Ctrl+C y reiniciar.

**Animación no se ve**: Verificar que `sessionStorage.indagata_intro` no esté seteado. Borrar con DevTools → Application → Session Storage.
