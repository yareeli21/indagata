import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

// Configuración estándar de Vite + TanStack Start.
// Orden de plugins recomendado por TanStack Start:
//   1. tsConfigPaths  → resuelve el alias "@" desde tsconfig.json.
//   2. tailwindcss    → Tailwind v4 vía su plugin oficial de Vite.
//   3. tanstackStart  → routing + SSR; su entry de servidor es src/server.ts.
//   4. viteReact      → transformación de React (debe ir después de tanstackStart).
//   5. nitro          → empaquetado del servidor para desplegar.
export default defineConfig({
  server: {
    port: 8080,
    // En Docker sobre Windows el contenedor no recibe los avisos de cambio de la carpeta montada y
    // Vite seguía sirviendo la versión anterior de los archivos editados (9 nov). Con
    // VITE_USAR_POLLING=true (docker-compose.yml) revisa los archivos cada 300 ms.
    watch:
      process.env.VITE_USAR_POLLING === "true" ? { usePolling: true, interval: 300 } : undefined,
  },
  optimizeDeps: {
    include: ["sonner"],
  },
  plugins: [
    tsConfigPaths(),
    tailwindcss(),
    tanstackStart({
      server: { entry: "src/server.ts" },
    }),
    viteReact(),
    nitro(),
  ],
});
