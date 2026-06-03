import { createContext, useContext, useState, type ReactNode } from "react";
import type { UserRole } from "@/lib/types";

interface UserRoleCtx {
  role: UserRole;
  setRole: (r: UserRole) => void;
}

const Ctx = createContext<UserRoleCtx | null>(null);

export function UserRoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>("Estudiante");
  return <Ctx.Provider value={{ role, setRole }}>{children}</Ctx.Provider>;
}

export function useUserRole() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useUserRole debe usarse dentro de UserRoleProvider");
  return ctx;
}
