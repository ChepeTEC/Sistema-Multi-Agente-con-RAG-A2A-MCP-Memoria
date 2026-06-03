import { createContext, useContext, useState, type ReactNode } from "react";
import type { RagConfig } from "@/lib/types";

interface RagCtx {
  config: RagConfig;
  setConfig: (c: RagConfig) => void;
}

const Ctx = createContext<RagCtx | null>(null);

export function RagConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<RagConfig>("semantica");
  return <Ctx.Provider value={{ config, setConfig }}>{children}</Ctx.Provider>;
}

export function useRagConfig() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRagConfig debe usarse dentro de RagConfigProvider");
  return ctx;
}
