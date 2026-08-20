"use client";

import {FormEvent, useEffect, useState} from "react";
import {Play} from "lucide-react";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Button, Card} from "@/components/ui";
import {api} from "@/lib/api";

type Run = {id: string; status: string; counts: Record<string, number>; usage: Record<string, number>; snapshot: {model: string}};
type Provider = {id: string; name: string; default_model: string | null};
type Conversation = {id: string; conversation_id: string};

export default function EvalRunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [providerId, setProviderId] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [model, setModel] = useState("");
  const [message, setMessage] = useState("");

  function refresh() { void api<Run[]>("/eval-runs").then(setRuns); }
  useEffect(() => {
    refresh();
    void api<Provider[]>("/providers").then((items) => { setProviders(items); if (items[0]) { setProviderId(items[0].id); setModel(items[0].default_model ?? ""); } });
    void api<Conversation[]>("/conversations").then((items) => { setConversations(items); if (items[0]) setConversationId(items[0].id); });
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage("Queuing evaluation…");
    try {
      await api("/eval-runs", {method: "POST", body: JSON.stringify({conversation_ids: [conversationId], provider_connection_id: providerId, model})});
      setMessage("Evaluation submitted."); refresh();
    } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Run failed"); }
  }

  return <AppShell><PageHeader title="Evaluation runs" description="Immutable snapshots of conversations, evaluator versions, routing, provider/model provenance, retries, usage, and errors." />
    <Card className="mt-8 p-6"><form onSubmit={submit} className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto]"><label className="text-xs font-semibold text-slate-600">Conversation<select className="mt-2 w-full rounded-lg border border-slate-300 p-2 text-sm" value={conversationId} onChange={(event) => setConversationId(event.target.value)}>{conversations.map((item) => <option value={item.id} key={item.id}>{item.conversation_id}</option>)}</select></label><label className="text-xs font-semibold text-slate-600">Provider<select className="mt-2 w-full rounded-lg border border-slate-300 p-2 text-sm" value={providerId} onChange={(event) => {setProviderId(event.target.value); const found = providers.find((item) => item.id === event.target.value); if (found?.default_model) setModel(found.default_model);}}>{providers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label className="text-xs font-semibold text-slate-600">Judge model<input className="mt-2 w-full rounded-lg border border-slate-300 p-2 text-sm" value={model} onChange={(event) => setModel(event.target.value)} required /></label><Button className="self-end" disabled={!providerId || !conversationId}><Play size={16} className="mr-2" />Run suite</Button></form>{message && <p className="mt-3 text-sm text-slate-600">{message}</p>}</Card>
    <div className="mt-6 space-y-3">{runs.length ? runs.map((run) => <Card className="flex flex-wrap items-center justify-between gap-4 p-5" key={run.id}><div><div className="flex items-center gap-2"><Badge>{run.status}</Badge><span className="font-mono text-xs text-slate-500">{run.id}</span></div><p className="mt-2 text-sm font-semibold">{run.snapshot.model}</p></div><div className="flex gap-6 text-center text-sm"><div><p className="font-bold text-emerald-700">{run.counts.pass ?? 0}</p><p className="text-xs text-slate-500">Pass</p></div><div><p className="font-bold text-red-700">{run.counts.fail ?? 0}</p><p className="text-xs text-slate-500">Fail</p></div><div><p className="font-bold">{run.usage.input_tokens ?? 0}</p><p className="text-xs text-slate-500">Input tokens</p></div></div></Card>) : <EmptyState title="No eval runs" detail="Connect a provider and ingest a conversation to run the default suite." />}</div>
  </AppShell>;
}
