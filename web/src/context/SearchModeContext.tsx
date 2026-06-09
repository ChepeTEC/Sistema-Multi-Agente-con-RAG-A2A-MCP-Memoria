import { createContext, useContext, useState, type ReactNode } from "react";

export type SearchMode = "web" | "docs";

interface Ctx {
  mode: SearchMode;
  setMode: (m: SearchMode) => void;
}

const SearchModeCtx = createContext<Ctx | null>(null);

export function SearchModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<SearchMode>("web");
  return <SearchModeCtx.Provider value={{ mode, setMode }}>{children}</SearchModeCtx.Provider>;
}

export function useSearchMode() {
  const ctx = useContext(SearchModeCtx);
  if (!ctx) throw new Error("useSearchMode debe usarse dentro de SearchModeProvider");
  return ctx;
}