import { useMcp } from "@/context/McpContext";
import { ScrollText } from "lucide-react";

export function AuditLog() {
  const { audit } = useMcp();
  return (
    <div className="rounded-lg border border-border bg-card/60">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <ScrollText className="size-3.5 text-muted-foreground" />
        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
          Log de auditoría
        </span>
      </div>
      {audit.length === 0 ? (
        <div className="p-3 text-xs text-muted-foreground">
          Aún no hay llamadas registradas al servidor MCP.
        </div>
      ) : (
        <ul className="scrollbar-thin max-h-64 divide-y divide-border overflow-y-auto text-xs">
          {audit.map((e) => (
            <li key={e.id} className="px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[color:var(--agent-mcp)]">{e.tool}</span>
                <span className="text-[10px] text-muted-foreground">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                rol: <span className="text-foreground">{e.role}</span> ·{" "}
                <span className="font-mono">{JSON.stringify(e.args)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
