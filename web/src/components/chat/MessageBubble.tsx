import type { ChatMessage } from "@/lib/types";
import { AGENT_META } from "@/lib/agent-meta";
import { User } from "lucide-react";
import { ExecutionTraceView } from "./ExecutionTrace";
import { SourceCitations } from "./SourceCitations";

// Minimal inline-markdown renderer (bold, links, line breaks)
function renderInline(text: string) {
  const parts: (string | React.ReactNode)[] = [];
  const regex = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const token = m[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else {
      const label = token.slice(1, token.indexOf("]"));
      const url = token.slice(token.indexOf("(") + 1, -1);
      parts.push(
        <a
          key={key++}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-primary underline-offset-2 hover:underline"
        >
          {label}
        </a>,
      );
    }
    last = regex.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function Markdown({ text }: { text: string }) {
  return (
    <div className="space-y-2 whitespace-pre-wrap text-sm leading-relaxed">
      {text.split("\n").map((line, i) => (
        <p key={i}>{renderInline(line)}</p>
      ))}
    </div>
  );
}

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div className="flex items-start gap-3">
        <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-secondary text-secondary-foreground">
          <User className="size-4" />
        </div>
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-border bg-secondary/40 px-4 py-3">
          <Markdown text={msg.content} />
        </div>
      </div>
    );
  }

  const agent = msg.trace?.agent ?? "orchestrator";
  const meta = AGENT_META[agent];
  const Icon = meta.icon;

  return (
    <div className="flex items-start gap-3">
      <div className={`grid size-8 shrink-0 place-items-center rounded-lg ${meta.bg} ring-1 ${meta.ring}`}>
        <Icon className={`size-4 ${meta.color}`} />
      </div>
      <div className="min-w-0 max-w-[85%] flex-1">
        <div className="mb-1 flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className={`font-medium ${meta.color}`}>{meta.label}</span>
          <span>· vía Orquestador</span>
        </div>
        <div className="rounded-2xl rounded-tl-sm border border-border bg-card/60 px-4 py-3">
          <Markdown text={msg.content} />
          {msg.citations && msg.citations.length > 0 && <SourceCitations citations={msg.citations} />}
          {msg.trace && <ExecutionTraceView trace={msg.trace} />}
        </div>
      </div>
    </div>
  );
}
