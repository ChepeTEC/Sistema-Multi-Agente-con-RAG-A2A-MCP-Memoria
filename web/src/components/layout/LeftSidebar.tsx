import { SessionList } from "@/components/sessions/SessionList";
import { UserProfileCard } from "@/components/sessions/UserProfileCard";
import { Sparkles } from "lucide-react";

export function LeftSidebar() {
  return (
    <aside className="flex h-full w-72 flex-col gap-4 border-r border-border bg-sidebar/60 p-4 backdrop-blur">
      <div className="flex items-center gap-2">
        <div className="grid size-9 place-items-center rounded-lg bg-primary/20 ring-1 ring-primary/40">
          <Sparkles className="size-4 text-primary" />
        </div>
        <div className="min-w-0">
          <div className="font-display text-sm font-semibold">Multi-Agent System</div>
          <div className="truncate text-[11px] text-muted-foreground">RAG · MCP · Memoria</div>
        </div>
      </div>


      <div className="min-h-0 flex-1">
        <SessionList />
      </div>

      <div className="rounded-lg border border-border bg-card/40 p-2.5 text-[11px] leading-snug text-muted-foreground">
        Orquestación trazada con <span className="text-foreground">Langfuse</span>. Toda
        consulta sensible queda registrada en el log de auditoría.
      </div>
    </aside>
  );
}
