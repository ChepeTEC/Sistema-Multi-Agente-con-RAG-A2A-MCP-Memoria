import type { AgentKind, BankTransaction } from "@/lib/types";

export interface IntentResult {
  agent: AgentKind;
  answer: string;
  tools: { name: string; args: Record<string, string | number> }[];
  webResults?: { title: string; url: string; snippet: string }[];
  mcpQuery?: { accountId: string; transactions: BankTransaction[] };
}

const ACADEMIC = ["gradiente", "apunte", "paper", "definici", "carlos", "neuronal", "entren", "overfit", "regulariz"];
const WEB = ["últimas", "ultimas", "noticia", "hoy", "esta semana", "openai", "anthropic", "google", "reciente"];
const MCP = ["cuenta", "transacci", "saldo", "sospechos", "bancari", "movimiento", "auditor"];

export function classifyIntent(query: string): AgentKind {
  const q = query.toLowerCase();
  if (MCP.some((k) => q.includes(k))) return "mcp";
  if (WEB.some((k) => q.includes(k))) return "web";
  if (ACADEMIC.some((k) => q.includes(k))) return "rag";
  return "summary";
}

export function buildMockAnswer(
  agent: AgentKind,
  query: string,
  transactions: BankTransaction[],
  masked: boolean,
): IntentResult {
  switch (agent) {
    case "rag":
      return {
        agent,
        tools: [
          { name: "vector_search", args: { query, top_k: 3 } },
          { name: "rerank", args: { model: "bge-reranker-v2" } },
        ],
        answer:
          "Según los apuntes recuperados, el **descenso del gradiente** es un método iterativo que actualiza los parámetros θ en la dirección opuesta al gradiente de la función de pérdida, escalado por la tasa de aprendizaje α. Los apuntes de Carlos enfatizan que las variantes mini-batch introducen ruido beneficioso para la generalización, y que Adam es el optimizador por defecto en la práctica moderna. Las fuentes consultadas se listan abajo.",
      };

    case "web":
      return {
        agent,
        tools: [
          { name: "web_search", args: { query, recency: "7d" } },
          { name: "summarize_results", args: { max_items: 3 } },
        ],
        webResults: [
          {
            title: "OpenAI anuncia nuevas capacidades de razonamiento en su última actualización",
            url: "https://openai.com/blog/latest-update",
            snippet: "La compañía presenta mejoras en cadena de pensamiento y reducción de alucinaciones en tareas complejas.",
          },
          {
            title: "Acuerdo de OpenAI con empresas de medios",
            url: "https://techcrunch.com/openai-media-deal",
            snippet: "Nuevos acuerdos de licenciamiento de contenido para entrenamiento de modelos.",
          },
          {
            title: "OpenAI lanza modo de voz avanzado en más regiones",
            url: "https://theverge.com/openai-voice-mode",
            snippet: "El despliegue alcanza América Latina y Europa esta semana.",
          },
        ],
        answer:
          "Resumen de las últimas noticias relevantes de OpenAI esta semana: nuevas capacidades de razonamiento, acuerdos de licenciamiento con medios y expansión global del modo de voz avanzado. A continuación se citan las fuentes obtenidas en tiempo real.",
      };

    case "mcp": {
      const accountId = "AC-9087-4421-1234";
      const flagged = transactions.filter((t) => t.flagged);
      const fmt = (n: number) =>
        masked ? "***" : new Intl.NumberFormat("es", { style: "currency", currency: "USD" }).format(n);
      const acc = masked ? "****-****-****-1234" : accountId;
      return {
        agent,
        tools: [
          { name: "get_account", args: { account_id: accountId } },
          { name: "get_transaction_by_id", args: { account_id: accountId, window: "7d" } },
          { name: "flag_suspicious_activity", args: { criteria: "night_hours" } },
        ],
        mcpQuery: { accountId, transactions: flagged },
        answer:
          `Se consultó la cuenta **${acc}** vía el servidor MCP. Se detectaron **${flagged.length} transacciones sospechosas** ` +
          flagged.map((t) => `\n- ${t.date} · ${t.description} · ${fmt(t.amount)}`).join("") +
          `\n\nLa política de auditoría enmascara los datos sensibles cuando el rol no es Auditor. Se ha registrado la consulta en el log de auditoría.`,
      };
    }

    default:
      return {
        agent: "summary",
        tools: [{ name: "summarize_context", args: { history_turns: 5 } }],
        answer:
          "He revisado el contexto de esta sesión. Puedo ayudarte con tres flujos: (1) consultas académicas que activan el RAG sobre apuntes y papers, (2) noticias recientes vía Web Search, y (3) consultas transaccionales vía MCP con auditoría. ¿Qué te gustaría explorar?",
      };
  }
}
