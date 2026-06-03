import { useSessions } from "@/context/SessionsContext";
import { Button } from "@/components/ui/button";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function SessionList() {
  const { sessions, activeId, selectSession, deleteSession, newSession } = useSessions();

  return (
    <div className="flex h-full flex-col gap-3">
      <Button
        onClick={newSession}
        className="w-full justify-start gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
      >
        <Plus className="size-4" />
        Nueva sesión
      </Button>

      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Memoria histórica
      </div>

      <div className="scrollbar-thin -mx-1 flex-1 space-y-1 overflow-y-auto pr-1">
        {sessions.map((s) => {
          const isActive = s.id === activeId;
          return (
            <div
              key={s.id}
              className={cn(
                "group flex cursor-pointer items-center gap-2 rounded-lg border border-transparent px-2.5 py-2 text-sm transition",
                isActive
                  ? "border-border bg-accent text-accent-foreground"
                  : "hover:bg-accent/40",
              )}
              onClick={() => selectSession(s.id)}
            >
              <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{s.title}</div>
                <div className="truncate text-[11px] text-muted-foreground">
                  {s.messages.length} mensajes
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteSession(s.id);
                }}
                className="rounded p-1 text-muted-foreground opacity-0 transition hover:bg-destructive/20 hover:text-destructive group-hover:opacity-100"
                aria-label="Eliminar sesión"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
