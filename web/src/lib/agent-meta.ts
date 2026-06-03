import type { AgentKind } from "@/lib/types";
import { Brain, Database, Globe, Lock, Sparkles } from "lucide-react";

export const AGENT_META: Record<
  AgentKind,
  { label: string; color: string; bg: string; ring: string; icon: typeof Brain }
> = {
  orchestrator: {
    label: "Orquestador",
    color: "text-[color:var(--agent-orchestrator)]",
    bg: "bg-[color:var(--agent-orchestrator)]/15",
    ring: "ring-[color:var(--agent-orchestrator)]/40",
    icon: Sparkles,
  },
  rag: {
    label: "Agente RAG",
    color: "text-[color:var(--agent-rag)]",
    bg: "bg-[color:var(--agent-rag)]/15",
    ring: "ring-[color:var(--agent-rag)]/40",
    icon: Database,
  },
  web: {
    label: "Agente Web Search",
    color: "text-[color:var(--agent-web)]",
    bg: "bg-[color:var(--agent-web)]/15",
    ring: "ring-[color:var(--agent-web)]/40",
    icon: Globe,
  },
  mcp: {
    label: "Agente MCP Transaccional",
    color: "text-[color:var(--agent-mcp)]",
    bg: "bg-[color:var(--agent-mcp)]/15",
    ring: "ring-[color:var(--agent-mcp)]/40",
    icon: Lock,
  },
  summary: {
    label: "Agente Resumidor",
    color: "text-[color:var(--agent-summary)]",
    bg: "bg-[color:var(--agent-summary)]/15",
    ring: "ring-[color:var(--agent-summary)]/40",
    icon: Brain,
  },
};
