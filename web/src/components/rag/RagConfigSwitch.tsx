import { useRagConfig } from "@/context/RagConfigContext";
import { cn } from "@/lib/utils";
import { Layers, Sparkles } from "lucide-react";

export function RagConfigSwitch() {
  const { config, setConfig } = useRagConfig();

  const options = [
    {
      id: "fija" as const,
      title: "RAG 1 · Fragmentación Fija",
      desc: "Chunks de 512 tokens · overlap 50",
      icon: Layers,
    },
    {
      id: "semantica" as const,
      title: "RAG 2 · Fragmentación Semántica",
      desc: "Segmentación por embeddings",
      icon: Sparkles,
    },
  ];

  return (
    <div className="space-y-2">
      {options.map((o) => {
        const active = config === o.id;
        const Icon = o.icon;
        return (
          <button
            key={o.id}
            onClick={() => setConfig(o.id)}
            className={cn(
              "w-full rounded-lg border p-3 text-left transition",
              active
                ? "border-primary/60 bg-primary/10 glow-ring"
                : "border-border bg-card/40 hover:border-border/80 hover:bg-card",
            )}
          >
            <div className="mb-1 flex items-center gap-2">
              <Icon className={cn("size-4", active ? "text-primary" : "text-muted-foreground")} />
              <span className="text-sm font-medium">{o.title}</span>
            </div>
            <p className="text-[11px] text-muted-foreground">{o.desc}</p>
          </button>
        );
      })}
      <p className="px-1 text-[11px] leading-snug text-muted-foreground">
        Cambia la configuración y vuelve a hacer una pregunta académica para comparar las
        citas y los scores recuperados.
      </p>
    </div>
  );
}
