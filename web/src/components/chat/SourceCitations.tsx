import type { Citation } from "@/lib/types";
import { FileText, User, Calendar } from "lucide-react";

export function SourceCitations({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-3 space-y-2">
      <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        Fuentes recuperadas ({citations.length})
      </div>
      <div className="grid gap-2">
        {citations.map((c) => (
          <div
            key={c.id}
            className="rounded-lg border border-border bg-card/40 p-2.5 text-xs transition hover:border-[color:var(--agent-rag)]/40"
          >
            <div className="mb-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <User className="size-3" /> {c.author}
              </span>
              <span className="inline-flex items-center gap-1">
                <FileText className="size-3" />
                <span className="font-mono">{c.file}</span>
              </span>
              <span className="inline-flex items-center gap-1">
                <Calendar className="size-3" /> {c.date}
              </span>
              <span className="ml-auto rounded bg-[color:var(--agent-rag)]/15 px-1.5 py-0.5 font-mono text-[10px] text-[color:var(--agent-rag)]">
                score {c.score.toFixed(2)}
              </span>
            </div>
            <p className="leading-snug text-foreground/90">"{c.excerpt}"</p>
          </div>
        ))}
      </div>
    </div>
  );
}
