import { useUserRole } from "@/context/UserRoleContext";
import type { UserRole } from "@/lib/types";
import { GraduationCap, Shield, UserCog } from "lucide-react";
import { cn } from "@/lib/utils";

const ROLES: { value: UserRole; icon: typeof Shield; hint: string }[] = [
  { value: "Estudiante", icon: GraduationCap, hint: "Acceso a RAG y Web" },
  { value: "Profesor",   icon: UserCog,       hint: "Acceso ampliado" },
  { value: "Auditor",    icon: Shield,        hint: "Datos MCP sin máscara" },
];

export function UserProfileCard() {
  const { role, setRole } = useUserRole();
  return (
    <div className="rounded-xl border border-border bg-card/60 p-3">
      <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Perfil activo
      </div>
      <div className="grid grid-cols-3 gap-1">
        {ROLES.map(({ value, icon: Icon }) => {
          const active = role === value;
          return (
            <button
              key={value}
              onClick={() => setRole(value)}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-[11px] transition",
                active
                  ? "border-primary/60 bg-primary/15 text-foreground glow-ring"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {value}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
        {ROLES.find((r) => r.value === role)?.hint}
      </p>
    </div>
  );
}
