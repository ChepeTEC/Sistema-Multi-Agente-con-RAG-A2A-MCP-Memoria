import { useMcp } from "@/context/McpContext";
import { useUserRole } from "@/context/UserRoleContext";
import { Eye, EyeOff, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

function maskAccount(id: string) {
  const tail = id.slice(-4);
  return `****-****-****-${tail}`;
}

function maskAmount(n: number, masked: boolean) {
  if (masked) return "***";
  return new Intl.NumberFormat("es", { style: "currency", currency: "USD" }).format(n);
}

export function McpDataTable() {
  const { account, transactions, masked } = useMcp();
  const { role } = useUserRole();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between rounded-lg border border-border bg-card/60 p-3">
        <div className="flex items-center gap-2">
          {masked ? (
            <EyeOff className="size-4 text-[color:var(--agent-mcp)]" />
          ) : (
            <Eye className="size-4 text-[color:var(--agent-mcp)]" />
          )}
          <div>
            <div className="text-sm font-medium">
              {masked ? "Datos enmascarados" : "Datos visibles"}
            </div>
            <div className="text-[11px] text-muted-foreground">
              Aplicado automáticamente por rol: <span className="text-foreground">{role}</span>
              {masked && " · solo el rol Auditor puede ver los datos en claro"}
            </div>
          </div>
        </div>
        <span
          className={cn(
            "rounded-md px-2 py-1 text-[10px] font-medium uppercase tracking-wider ring-1",
            masked
              ? "bg-[color:var(--agent-mcp)]/15 text-[color:var(--agent-mcp)] ring-[color:var(--agent-mcp)]/40"
              : "bg-[color:var(--agent-summary)]/15 text-[color:var(--agent-summary)] ring-[color:var(--agent-summary)]/40",
          )}
        >
          {masked ? "Protegido" : "Auditor"}
        </span>
      </div>

      <div className="rounded-lg border border-border bg-card/60 p-3">
        <div className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
          Cuenta protegida (MCP)
        </div>
        <div className="font-mono text-sm">{masked ? maskAccount(account.id) : account.id}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          Saldo:{" "}
          <span className="font-mono text-foreground">{maskAmount(account.balance, masked)}</span>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-card/60">
        <div className="border-b border-border px-3 py-2 text-[11px] uppercase tracking-wider text-muted-foreground">
          Últimas transacciones
        </div>
        <ul className="divide-y divide-border text-xs">
          {transactions.map((t) => (
            <li
              key={t.id}
              className={cn(
                "flex items-center gap-2 px-3 py-2",
                t.flagged && "bg-[color:var(--agent-mcp)]/10",
              )}
            >
              {t.flagged && (
                <ShieldAlert className="size-3.5 shrink-0 text-[color:var(--agent-mcp)]" />
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate">{t.description}</div>
                <div className="text-[10px] text-muted-foreground">{t.date}</div>
              </div>
              <div
                className={cn(
                  "font-mono",
                  t.amount < 0 ? "text-[color:var(--agent-mcp)]" : "text-[color:var(--agent-summary)]",
                )}
              >
                {maskAmount(t.amount, masked)}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
