<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

# INDAGATA — reglas del proyecto

- Interfaz completamente en español (textos, rutas y nombres de dominio en el código).
- Los datos de ejemplo viven en `src/mocks/`; las pantallas NUNCA los importan directamente. Todo acceso pasa por funciones asíncronas en `src/api/` para poder sustituirlas por llamadas HTTP a la API FastAPI sin tocar la UI.
- Sin backend, base de datos ni autenticación externa (nada de Supabase). El login es simulado en `src/api/auth.ts`.
- Organización por features en `src/features/{auth,upload,instruments,research,chat,kpis}/`; componentes compartidos en `src/components/`. Un componente por archivo con props tipadas.
- Tipos de dominio compartidos en `src/types/index.ts`, incluida la lista cerrada de niveles educativos.
- Enrutamiento con TanStack Router (archivos en `src/routes/`); el layout global es la ruta `_panel.tsx`. No se usa React Router ni Next.js.
- Colores, tipografía y sombras solo como tokens semánticos en `src/styles.css`; nunca clases de color literales en los componentes.
