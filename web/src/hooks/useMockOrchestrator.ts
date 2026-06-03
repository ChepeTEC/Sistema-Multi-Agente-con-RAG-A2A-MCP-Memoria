import { useCallback, useState } from "react";
import { useSessions } from "@/context/SessionsContext";
import { useRagConfig } from "@/context/RagConfigContext";
import { useUserRole } from "@/context/UserRoleContext";
import { useMcp } from "@/context/McpContext";
import { buildMockAnswer, classifyIntent } from "@/mocks/fixtures";
import { getRagCitations } from "@/mocks/sources";
import type { ChatMessage } from "@/lib/types";

export function useMockOrchestrator() {
  const { active, appendMessage, renameIfFirst } = useSessions();
  const { config } = useRagConfig();
  const { role } = useUserRole();
  const { transactions, masked, logCall } = useMcp();
  const [isThinking, setIsThinking] = useState(false);

  const send = useCallback(
    async (text: string) => {
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

      const agent = classifyIntent(content);
      const latency = 900 + Math.floor(Math.random() * 800);
      await new Promise((r) => setTimeout(r, latency));

      const result = buildMockAnswer(agent, content, transactions, masked);

      // Side-effect: audit MCP tool calls
      if (agent === "mcp") {
        result.tools.forEach((t) =>
          logCall({ tool: t.name, args: t.args, role }),
        );
      }

      // Build assistant message
      let answer = result.answer;
      if (agent === "web" && result.webResults) {
        answer +=
          "\n\n" +
          result.webResults
            .map((r, i) => `${i + 1}. [${r.title}](${r.url}) — ${r.snippet}`)
            .join("\n");
      }

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: answer,
        createdAt: Date.now(),
        trace: {
          agent,
          latencyMs: latency,
          tokens: {
            input: 80 + Math.floor(Math.random() * 220),
            output: 140 + Math.floor(Math.random() * 380),
          },
          tools: result.tools,
          ragConfig: agent === "rag" ? config : undefined,
          role,
        },
        citations: agent === "rag" ? getRagCitations(config) : undefined,
      };

      appendMessage(assistantMsg);
      setIsThinking(false);
    },
    [active.messages.length, appendMessage, config, isThinking, logCall, masked, renameIfFirst, role, transactions],
  );

  return { send, isThinking };
}
