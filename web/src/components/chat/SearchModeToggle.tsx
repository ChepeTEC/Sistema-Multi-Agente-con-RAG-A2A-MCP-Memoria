import { useSearchMode, type SearchMode } from "@/context/SearchModeContext";
import { cn } from "@/lib/utils";
import { Globe, BookOpen } from "lucide-react";

const OPTIONS: { id: SearchMode; label: string; icon: typeof Globe }[] = [
  { id: "web", label: "Solo Web", icon: Globe },
  { id: "docs", label: "Solo Apuntes", icon: BookOpen },
];

export function SearchModeToggle() {
  const { mode, setMode } = useSearchMode();
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-border bg-card/50 p-1"
         role="radiogroup" aria-label="Modo de búsqueda">
      {OPTIONS.map((o) => {
        const active = mode === o.id;
        const Icon = o.icon;
        return (
          <button key={o.id} type="button" role="radio" aria-checked={active}
            onClick={() => setMode(o.id)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium transition",
              active
                ? "bg-primary/15 text-primary ring-1 ring-primary/40 glow-ring"
                : "text-muted-foreground hover:text-foreground",
            )}>
            <Icon className="size-3.5" />
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
