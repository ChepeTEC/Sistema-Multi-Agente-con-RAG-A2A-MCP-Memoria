export type AgentKind = "orchestrator" | "rag" | "web" | "mcp" | "summary";

export type UserRole = "Estudiante" | "Profesor" | "Auditor";

export type RagConfig = "fija" | "semantica";

export interface Citation {
  id: string;
  author: string;
  file: string;
  date: string;
  excerpt: string;
  score: number;
}

export interface ToolCall {
  name: string;
  args: Record<string, string | number>;
}

export interface ExecutionTrace {
  agent: AgentKind;
  latencyMs: number;
  tokens: { input: number; output: number };
  tools: ToolCall[];
  ragConfig?: RagConfig;
  role: UserRole;
  searchMode: "web" | "docs";
  decisionReason?: string;
  backendTrace?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  trace?: ExecutionTrace;
  citations?: Citation[];
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
}

export interface BankTransaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  flagged?: boolean;
}

export interface AuditEntry {
  id: string;
  timestamp: number;
  tool: string;
  args: Record<string, string | number>;
  role: UserRole;
}
