/** Burbujas de conversación decorativas (gateway Chat). */
export function VisualChat() {
  return (
    // Solo cuando la tarjeta es ancha (2 columnas): en lg–2xl ocupa 1 columna.
    <div className="absolute right-6 top-7 hidden w-48 flex-col gap-2 sm:flex md:right-8 lg:hidden 2xl:flex 2xl:w-64">
      <span className="ml-10 h-8 rounded-2xl rounded-br-md bg-primary/85" />
      <span className="mr-6 h-8 rounded-2xl rounded-bl-md bg-primary-soft" />
      <span className="mr-16 h-8 rounded-2xl rounded-bl-md bg-primary-soft" />
    </div>
  );
}
