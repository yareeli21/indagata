# Plan de implementación — Alta de usuarios (frontend-only)

Objetivo: pantalla de "Gestión de usuarios" en el frontend `pixel-perfect-pixel`, visible SOLO para administradores, que crea usuarios llamando al endpoint EXISTENTE `POST http://localhost:8000/auth/register` con el JWT de admin ya guardado. FRONTEND ONLY: no se toca `services/*`, `infrastructure/*` ni Dockerfiles.

## Decisiones de diseño (grounded en el código leído)

- **Reutilizar `pedir` con `auth: true`.** `src/api/client.ts` ya adjunta `Authorization: Bearer <token>` (clave localStorage `indagata.token`) cuando `auth: true`. El JWT del admin se guarda tras el login (`src/api/auth.ts` → `guardarToken`). No se necesita token nuevo.
- **Mapeo de errores por `detail` + extensión mínima de `pedir` para exponer el status.** Hoy `pedir` lanza un `Error` genérico y para no-401 usa `datos.detail` (string del backend) o un fallback con el código HTTP. El backend ya devuelve `detail` en español para 409 ("Ya existe un usuario con ese email."). Para 403/422 el `detail` puede venir en inglés o como objeto de validación, así que se añade el `status` numérico al `Error` lanzado por `pedir` (propiedad opcional) y `usuarios.ts` decide el mensaje en español según el código. Esta extensión es aditiva: no cambia el mensaje de 401 ni el flujo de login. Rechazada la alternativa de parsear solo el texto de `detail` porque 422 de FastAPI trae `detail` como arreglo de objetos, no un string legible.
- **Rol: mapear capitalizado ↔ minúsculas.** El dominio del front usa `Rol = "Investigador" | "Administrador"` (`src/types/index.ts`); el backend exige `rol` en minúsculas. `usuarios.ts` convierte a minúsculas al enviar. El `select` del formulario ofrece las etiquetas capitalizadas del dominio.
- **Gateo de solo-admin en dos capas:** (1) la entrada del Sidebar se renderiza condicionalmente con `useAuth()` cuando `usuario?.rol === "Administrador"`; (2) la ruta `_panel.usuarios.tsx` muestra un aviso "no autorizado" si `usuario?.rol !== "Administrador"`. Doble capa porque el Sidebar oculta pero no protege la URL directa.
- **Formulario:** se espeja el vocabulario de estilos de `login.tsx` (inputs con tokens, bloque de error `role="alert"`, submit deshabilitado mientras envía) y se usa el componente `Select` de `@/components/ui/select` para el rol, igual que `StepDublinCore.tsx`/`FiltrosPanel.tsx`. Encabezado con `PageHeader` como en `EspacioVectorialPage.tsx`.
- **Sin framework de pruebas** (no hay `*.test.*` ni script `test` en `package.json`). La verificación es `bun run build` (tipos TS), `bun run lint` y prueba manual en navegador contra el backend vivo.

## Archivos

Crear:
- `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\api\usuarios.ts`
- `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\features\usuarios\GestionUsuariosPage.tsx`
- `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\routes\_panel.usuarios.tsx`

Editar:
- `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\api\client.ts` (extensión mínima aditiva de `pedir`)
- `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\components\layout\Sidebar.tsx` (entrada de nav solo-admin)

## Firma de `registrarUsuario` y mapeo de errores

```ts
// src/api/usuarios.ts
import type { Rol } from "@/types";

export interface DatosNuevoUsuario {
  nombre: string;
  email: string;
  password: string;
  rol: Rol; // "Investigador" | "Administrador" (dominio del front)
}

export interface UsuarioCreado {
  usuario_id: number;
  nombre: string;
  email: string;
  rol: string; // minúsculas desde el backend
}

export async function registrarUsuario(datos: DatosNuevoUsuario): Promise<UsuarioCreado>;
```

Comportamiento:
- `rol` del dominio → minúsculas al enviar: `"Administrador" → "administrador"`, `"Investigador" → "investigador"`.
- Llama `pedir<UsuarioCreado>(\`${API_URL}/auth/register\`, { method: "POST", auth: true, body: { nombre, email, password, rol: rolMin } })`.
- Mapeo de errores (según `status` adjunto al `Error`):
  - `409` → "Ya existe un usuario con ese correo electrónico."
  - `403` → "No tienes permisos para crear usuarios (se requiere rol administrador)."
  - `422` → "Datos inválidos: revisa el correo (formato válido, sin dominios reservados) y que la contraseña tenga al menos 6 caracteres."
  - `401` → se deja el mensaje de sesión que ya produce `pedir` ("Usuario o contraseña incorrectos") o se reescribe a "Tu sesión expiró, vuelve a iniciar sesión." (preferir este último en `usuarios.ts`).
  - sin `status` reconocido / red → "No fue posible crear el usuario. Intenta de nuevo."

## Plan por pasos

- [ ] 1. Extender `pedir` en `client.ts` para adjuntar el status HTTP al `Error` lanzado, de forma aditiva.
      Añadir `interface ErrorHttp extends Error { status?: number }` (o asignar `(err as { status?: number }).status`) y, en la rama `!respuesta.ok`, setear `error.status = respuesta.status` antes de `throw`, incluyendo el caso 401. No cambiar los textos actuales ni la firma pública de `pedir`.
      Files: `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\api\client.ts`
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build` compila sin errores TS; el login manual sigue funcionando (se valida en el paso 7).

- [ ] 2. Crear `src/api/usuarios.ts` con `DatosNuevoUsuario`, `UsuarioCreado` y `registrarUsuario` (firma y mapeo de arriba). Usa `API_URL` y `pedir` de `./client`; convierte `rol` a minúsculas; traduce los status a los mensajes en español definidos.
      Files: `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\api\usuarios.ts`
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build` sin errores TS; `bun run lint` sin nuevos avisos en el archivo.

- [ ] 3. Crear `src/features/usuarios/GestionUsuariosPage.tsx` (un componente, props tipadas si las hubiera). Formulario en español: Nombre (text, requerido), Correo electrónico (`type="email"`, requerido), Contraseña (`type="password"`, `minLength={6}`, requerido), Rol (`Select` de `@/components/ui/select` con opciones "Investigador"/"Administrador", default "Investigador"). Encabezado con `PageHeader` (título "Gestión de usuarios"). Estado local `enviando`, `error`, `exito`. Al enviar: `setEnviando(true)`, llamar `registrarUsuario`, en éxito mostrar "Usuario creado: <email>" y resetear el formulario; en error mostrar el mensaje en un bloque `role="alert"` con las clases de token de `login.tsx` (`border-destructive/30 bg-destructive/10 text-destructive`). Submit deshabilitado mientras `enviando`. Clases de estilo espejando `login.tsx` (inputs con borde inferior y tokens; nunca colores literales).
      Files: `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\features\usuarios\GestionUsuariosPage.tsx`
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build` sin errores TS.

- [ ] 4. Crear la ruta `src/routes/_panel.usuarios.tsx` bajo el layout `_panel`, espejando `_panel.espacio.tsx` (`createFileRoute("/_panel/usuarios")`, bloque `head` con meta en español). El componente de ruta usa `useAuth()`: si `usuario?.rol !== "Administrador"`, renderiza un aviso corto "no autorizado" (p.ej. tarjeta con `PageHeader` "Acceso restringido" y texto "No tienes permisos para ver esta sección."); si es administrador, renderiza `<GestionUsuariosPage />`.
      Files: `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\routes\_panel.usuarios.tsx`
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build` sin errores TS; la ruta `/usuarios` queda registrada por el router (sin errores de generación de rutas en el build).

- [ ] 5. Editar `Sidebar.tsx` para añadir la entrada de nav solo-admin. Importar `useAuth` de `@/features/auth/AuthContext` y el icono `UserPlus` (o `Users`) de `lucide-react`. Dentro de `Sidebar()` obtener `const { usuario } = useAuth();` y construir la lista de opciones a renderizar añadiendo `{ to: "/usuarios", etiqueta: "Gestión de usuarios", icono: UserPlus }` SOLO cuando `usuario?.rol === "Administrador"` (p.ej. `const opciones = [...OPCIONES, ...(usuario?.rol === "Administrador" ? [{...}] : [])]`). Mantener el resto del render igual.
      Files: `c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel\src\components\layout\Sidebar.tsx`
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build` sin errores TS; `bun run lint` sin nuevos avisos.

- [ ] 6. Verificación estática completa: build + lint del frontend.
      Files: (ninguno)
      Verify: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run build; bun run lint` — build termina sin errores TS y lint sin errores nuevos.

- [ ] 7. Verificación manual en navegador contra el backend vivo (docker ya levantado: api-gateway en http://localhost:8000). Arrancar el dev server en segundo plano: `cd c:\Users\yarel\Documents\indagata\indagata\pixel-perfect-pixel; bun run dev` (background). Pasos:
      1. Entrar como admin (`admin@indagata.com` / `admin123`). Confirmar que el Sidebar muestra "Gestión de usuarios".
      2. Ir a `/usuarios`, crear un usuario de prueba (p.ej. nombre "Prueba QA", email `prueba.qa@indagata.com`, password `prueba123`, rol Investigador). Confirmar mensaje "Usuario creado: prueba.qa@indagata.com" y reset del formulario.
      3. Probar errores: reenviar el mismo email → "Ya existe un usuario con ese correo electrónico." (409); email inválido o password < 6 → mensaje de datos inválidos (422).
      4. Cerrar sesión e iniciar sesión con el usuario de prueba → confirmar que entra (JWT válido) y que el Sidebar NO muestra "Gestión de usuarios"; navegar a `/usuarios` manualmente → se ve el aviso "no autorizado".
      Files: (ninguno)
      Verify: todos los pasos anteriores se comportan como se describe en el navegador.

- [ ] 8. Limpieza: BORRAR el usuario de prueba de la base de datos (schema `tt_rag`, db `indagata_db`) para no dejar datos de prueba. Comando sugerido desde la raíz del repo:
      `docker compose -f docker-compose.yml exec -T postgres psql -U <usuario_db> -d indagata_db -c "DELETE FROM tt_rag.usuario WHERE email = 'prueba.qa@indagata.com';"`
      (ajustar el nombre de la tabla/usuario de DB según `infrastructure/postgres/init/01_schema.sql` si difiere). NO modificar ningún archivo bajo `infrastructure/*`; esto es solo una operación de datos, no un cambio de código.
      Files: (ninguno)
      Verify: una consulta `SELECT email FROM tt_rag.usuario WHERE email = 'prueba.qa@indagata.com';` no devuelve filas.

## Notas / supuestos

- El nombre real de la tabla de usuarios y el usuario de la DB para `psql` deben confirmarse en `infrastructure/postgres/init/01_schema.sql` antes del paso 8 (está abierto en el editor). Si el borrado por SQL no es viable, borrar vía cualquier herramienta de DB disponible; el objetivo es dejar la DB sin el usuario de prueba.
- Si el 401 de `pedir` ya cubre el caso de sesión expirada, basta con dejar que `usuarios.ts` reescriba ese mensaje; no se requiere lógica de refresh de token (fuera de alcance).
- No se añaden endpoints de listado/edición/borrado de usuarios: el alcance es solo el alta (`POST /auth/register`).
```