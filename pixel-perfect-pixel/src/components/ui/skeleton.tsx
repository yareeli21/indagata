import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-brillo rounded-xl bg-[linear-gradient(90deg,var(--primary-soft)_25%,oklch(0.97_0.015_266)_50%,var(--primary-soft)_75%)] bg-[length:200%_100%]",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
