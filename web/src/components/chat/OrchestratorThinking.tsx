import { AGENT_META } from "@/lib/agent-meta";
import { Sparkles } from "lucide-react";

export function OrchestratorThinking() {
  const meta = AGENT_META.orchestrator;
  return (
    <div className="flex items-start gap-3">
      <div className={`grid size-8 shrink-0 place-items-center rounded-lg ${meta.bg} ring-1 ${meta.ring}`}>
        <Sparkles className={`size-4 ${meta.color}`} />
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-border bg-card/50 px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>El Orquestador está delegando la tarea</span>
          <span className="inline-flex gap-1">
            <span className="thinking-dot size-1.5 rounded-full bg-primary" style={{ animationDelay: "0ms" }} />
            <span className="thinking-dot size-1.5 rounded-full bg-primary" style={{ animationDelay: "150ms" }} />
            <span className="thinking-dot size-1.5 rounded-full bg-primary" style={{ animationDelay: "300ms" }} />
          </span>
        </div>
      </div>
    </div>
  );
}
