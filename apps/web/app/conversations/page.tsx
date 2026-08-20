"use client";

import {useEffect, useState} from "react";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Card} from "@/components/ui";
import {api} from "@/lib/api";

type Conversation = {id: string; conversation_id: string; started_at: string; language_summary: {primary_language?: string}; metadata: Record<string, unknown>};

export default function ConversationsPage() {
  const [items, setItems] = useState<Conversation[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<Conversation[]>("/conversations").then(setItems).catch((value: Error) => setError(value.message)); }, []);
  return <AppShell><PageHeader title="Conversations" description="Immutable canonical traces with original utterances, retrieval evidence, and tool trajectories." actions={<a className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white" href="/integrations">Import traces</a>} />
    <Card className="mt-8 overflow-hidden">{error ? <p className="p-6 text-red-700">{error}</p> : items.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Conversation</th><th className="px-5 py-3">Started</th><th className="px-5 py-3">Language</th><th className="px-5 py-3">Source</th></tr></thead><tbody className="divide-y divide-slate-100">{items.map((item) => <tr key={item.id}><td className="px-5 py-4 font-semibold text-slate-900">{item.conversation_id}</td><td className="px-5 py-4 text-slate-600">{new Date(item.started_at).toLocaleString()}</td><td className="px-5 py-4"><Badge>{item.language_summary.primary_language ?? "unknown"}</Badge></td><td className="px-5 py-4 text-slate-600">{String(item.metadata.source ?? "canonical API")}</td></tr>)}</tbody></table></div> : <div className="p-6"><EmptyState title="No conversations" detail="Load the demo dataset, upload a canonical file, or send traces through the ingestion API." /></div>}</Card>
  </AppShell>;
}
