import { Lock } from "lucide-react";

export function OtherResearcherBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
      <Lock className="h-3 w-3" />
      De otro investigador
    </span>
  );
}
