import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { ChatMessage, Session } from "@/lib/types";

interface SessionsCtx {
  sessions: Session[];
  activeId: string;
  active: Session;
  newSession: () => void;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;
  appendMessage: (msg: ChatMessage) => void;
  renameIfFirst: (firstUserMessage: string) => void;
}

const Ctx = createContext<SessionsCtx | null>(null);
const STORAGE_KEY = "mas.sessions.v1";
const INITIAL_SESSION_ID = "initial-session";

function createSession(id = crypto.randomUUID(), createdAt = Date.now()): Session {
  return {
    id,
    title: "Nueva sesión",
    createdAt,
    messages: [],
  };
}

export function SessionsProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(() => [createSession(INITIAL_SESSION_ID, 0)]);
  const [activeId, setActiveId] = useState<string>(INITIAL_SESSION_ID);
  const [isStorageLoaded, setIsStorageLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Session[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          setActiveId(parsed[0]!.id);
        }
      }
    } catch {
      /* ignore */
    } finally {
      setIsStorageLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!isStorageLoaded) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch {
      /* ignore */
    }
  }, [isStorageLoaded, sessions]);

  const active = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? sessions[0]!,
    [sessions, activeId],
  );

  const value: SessionsCtx = {
    sessions,
    activeId,
    active,
    newSession: () => {
      const s = createSession();
      setSessions((prev) => [s, ...prev]);
      setActiveId(s.id);
    },
    selectSession: (id) => setActiveId(id),
    deleteSession: (id) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (next.length === 0) {
          const fresh = createSession();
          setActiveId(fresh.id);
          return [fresh];
        }
        if (id === activeId) setActiveId(next[0]!.id);
        return next;
      });
    },
    appendMessage: (msg) =>
      setSessions((prev) => {
        const targetId = prev.some((s) => s.id === activeId) ? activeId : prev[0]?.id;
        if (!targetId) return prev;
        return prev.map((s) => (s.id === targetId ? { ...s, messages: [...s.messages, msg] } : s));
      }),
    renameIfFirst: (firstUserMessage) =>
      setSessions((prev) => {
        const targetId = prev.some((s) => s.id === activeId) ? activeId : prev[0]?.id;
        if (!targetId) return prev;
        return prev.map((s) => {
          if (s.id !== targetId) return s;
          if (s.title !== "Nueva sesión") return s;
          const title = firstUserMessage.trim().slice(0, 48) || "Nueva sesión";
          return { ...s, title };
        });
      }),
  };

  if (!isStorageLoaded) return null;

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSessions() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSessions debe usarse dentro de SessionsProvider");
  return ctx;
}
