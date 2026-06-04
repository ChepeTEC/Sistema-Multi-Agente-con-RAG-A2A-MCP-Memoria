import { useCallback, useMemo, useState } from "react";
import { useSessions } from "@/context/SessionsContext";
import { useUserRole } from "@/context/UserRoleContext";
import { useMockOrchestrator } from "@/hooks/useMockOrchestrator";
import type { AgentKind, ChatMessage, Citation, ExecutionTrace, ToolCall } from "@/lib/types";

interface BackendSource {
  title?: string;
  url?: string;
  score?: number;
  published_date?: string | null;
  file?: string;
  author?: string;
  date?: string;
  page?: string | number;
  section?: string;
  topic?: string;
  distance?: number | null;
}

interface BackendTrace {
  question?: string;
  agent_selected?: string;
  decision_model?: string;
  decision_provider?: string;
  raw_decision?: string;
  decision_duration_ms?: number;
  total_duration_ms?: number;
  delegated_agent?: string;
  delegated_trace?: Record<string, unknown>;
}

interface BackendChatResponse {
  agent_selected: "rag" | "web";
  decision_reason: string;
  answer: string;
  sources: BackendSource[];
  trace: BackendTrace;
}

function getBackendUrl() {
  return import.meta.env.VITE_API_BACKEND_URL?.replace(/\/$/, "");
}

function sourceToCitation(source: BackendSource, index: number): Citation {
  const isWeb = Boolean(source.url);
  const score = typeof source.score === "number"
    ? source.score
    : typeof source.distance === "number"
      ? Math.max(0, 1 - source.distance)
      : 0;

  return {
    id: `${isWeb ? source.url : source.file ?? "source"}-${index}`,
    author: source.author ?? (isWeb ? "Web Search" : "Apuntes del curso"),
    file: source.file ?? source.title ?? source.url ?? "fuente",
    date: source.date ?? source.published_date ?? "sin fecha",
    excerpt: isWeb
      ? source.url ?? ""
      : [
          source.topic ? `Tema: ${source.topic}` : "",
          source.section ? `Seccion: ${source.section}` : "",
          source.page ? `Pagina: ${source.page}` : "",
        ].filter(Boolean).join(" | ") || "Fuente recuperada por RAG.",
    score,
  };
}

function buildToolCalls(response: BackendChatResponse): ToolCall[] {
  const tools: ToolCall[] = [
    {
      name: "gemini_decision",
      args: {
        model: response.trace.decision_model ?? "unknown",
        selected: response.agent_selected,
      },
    },
  ];

  if (response.agent_selected === "rag") {
    tools.push({
      name: "rag_agent.answer",
      args: { sources: response.sources.length },
    });
  } else {
    tools.push({
      name: "web_search_agent.answer",
      args: { sources: response.sources.length },
    });
  }

  return tools;
}

function toExecutionTrace(response: BackendChatResponse, role: ExecutionTrace["role"]): ExecutionTrace {
  return {
    agent: response.agent_selected as AgentKind,
    latencyMs: response.trace.total_duration_ms ?? response.trace.decision_duration_ms ?? 0,
    tokens: {
      input: 0,
      output: 0,
    },
    tools: buildToolCalls(response),
    role,
    decisionReason: response.decision_reason,
    backendTrace: response.trace,
  };
}

export function useOrchestrator() {
  const mock = useMockOrchestrator();
  const { active, appendMessage, renameIfFirst } = useSessions();
  const { role } = useUserRole();
  const [isThinking, setIsThinking] = useState(false);
  const backendUrl = useMemo(() => getBackendUrl(), []);

  const send = useCallback(
    async (text: string) => {
      if (!backendUrl) {
        await mock.send(text);
        return;
      }

      const content = text.trim();
      if (!content || isThinking) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        createdAt: Date.now(),
      };
      appendMessage(userMsg);
      if (active.messages.length === 0) renameIfFirst(content);

      setIsThinking(true);

      try {
        const response = await fetch(`${backendUrl}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ question: content }),
        });

        if (!response.ok) {
          throw new Error(`Backend respondio con estado ${response.status}`);
        }

        const data = (await response.json()) as BackendChatResponse;
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.answer,
          createdAt: Date.now(),
          trace: toExecutionTrace(data, role),
          citations: data.sources.map(sourceToCitation),
        };

        appendMessage(assistantMsg);
      } catch (error) {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "No pude conectar con el backend real. Revisa que FastAPI este corriendo y que VITE_API_BACKEND_URL apunte al servidor correcto.",
          createdAt: Date.now(),
          trace: {
            agent: "orchestrator",
            latencyMs: 0,
            tokens: { input: 0, output: 0 },
            tools: [
              {
                name: "backend_fetch",
                args: {
                  error: error instanceof Error ? error.message : "unknown",
                },
              },
            ],
            role,
          },
        };
        appendMessage(assistantMsg);
      } finally {
        setIsThinking(false);
      }
    },
    [active.messages.length, appendMessage, backendUrl, isThinking, mock, renameIfFirst, role],
  );

  return {
    send,
    isThinking: backendUrl ? isThinking : mock.isThinking,
  };
}
