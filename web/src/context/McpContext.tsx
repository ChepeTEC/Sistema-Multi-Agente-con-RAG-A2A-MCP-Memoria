import { createContext, useContext, useState, type ReactNode } from "react";
import type { AuditEntry, BankTransaction } from "@/lib/types";
import { MOCK_ACCOUNT, MOCK_TRANSACTIONS } from "@/mocks/transactions";
import { useUserRole } from "@/context/UserRoleContext";

interface McpCtx {
  account: typeof MOCK_ACCOUNT;
  transactions: BankTransaction[];
  masked: boolean;
  audit: AuditEntry[];
  logCall: (entry: Omit<AuditEntry, "id" | "timestamp">) => void;
}

const Ctx = createContext<McpCtx | null>(null);

export function McpProvider({ children }: { children: ReactNode }) {
  const { role } = useUserRole();
  const masked = role !== "Auditor";
  const [audit, setAudit] = useState<AuditEntry[]>([]);

  const logCall: McpCtx["logCall"] = (entry) =>
    setAudit((prev) => [
      { ...entry, id: crypto.randomUUID(), timestamp: Date.now() },
      ...prev,
    ].slice(0, 50));

  return (
    <Ctx.Provider
      value={{
        account: MOCK_ACCOUNT,
        transactions: MOCK_TRANSACTIONS,
        masked,
        audit,
        logCall,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useMcp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useMcp debe usarse dentro de McpProvider");
  return ctx;
}
