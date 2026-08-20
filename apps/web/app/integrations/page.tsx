"use client";

import {FormEvent, useEffect, useState} from "react";
import {KeyRound, PlugZap} from "lucide-react";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Button, Card} from "@/components/ui";
import {api} from "@/lib/api";

type Provider = {id: string; name: string; provider: string; status: string; credential_configured: boolean; default_model: string | null};

export default function IntegrationsPage() {
  const [items, setItems] = useState<Provider[]>([]);
  const [provider, setProvider] = useState("openai");
  const [name, setName] = useState("My provider");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [message, setMessage] = useState("");
  function refresh() { void api<Provider[]>("/providers").then(setItems); }
  useEffect(refresh, []);
  async function submit(event: FormEvent) { event.preventDefault(); setMessage(""); try { await api("/providers", {method: "POST", body: JSON.stringify({name, provider, api_key: provider === "ollama" ? undefined : apiKey, base_url: baseUrl || undefined, default_model: model || undefined, secret_source: provider === "ollama" ? "NONE" : "ENCRYPTED_DB"})}); setApiKey(""); setMessage("Provider saved. The credential will not be shown again."); refresh(); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Could not save provider"); } }
  async function test(id: string) { try { await api(`/providers/${id}/test`, {method: "POST"}); setMessage("Connection succeeded."); refresh(); } catch (caught) { setMessage(caught instanceof Error ? caught.message : "Connection failed"); } }
  return <AppShell><PageHeader title="Integrations" description="Bring your own model credentials and canonical traces. Credentials remain backend-only, encrypted at rest, and masked after save." />
    <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_1.2fr]"><Card className="p-6"><div className="flex items-center gap-3"><KeyRound className="text-teal-700" /><h2 className="font-bold">Connect an LLM provider</h2></div><form className="mt-6 space-y-4" onSubmit={submit}><label className="block text-sm font-semibold">Provider<select className="mt-2 w-full rounded-lg border border-slate-300 p-2 font-normal" value={provider} onChange={(event) => setProvider(event.target.value)}><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="gemini">Google Gemini</option><option value="openai-compatible">OpenAI-compatible</option><option value="ollama">Ollama / local</option></select></label><label className="block text-sm font-semibold">Connection name<input className="mt-2 w-full rounded-lg border border-slate-300 p-2 font-normal" value={name} onChange={(event) => setName(event.target.value)} required /></label>{(provider === "openai-compatible" || provider === "ollama") && <label className="block text-sm font-semibold">Base URL<input className="mt-2 w-full rounded-lg border border-slate-300 p-2 font-normal" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="http://host.docker.internal:11434" /></label>}{provider !== "ollama" && <label className="block text-sm font-semibold">API key<input className="mt-2 w-full rounded-lg border border-slate-300 p-2 font-normal" type="password" autoComplete="new-password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} required /></label>}<label className="block text-sm font-semibold">Default model<input className="mt-2 w-full rounded-lg border border-slate-300 p-2 font-normal" value={model} onChange={(event) => setModel(event.target.value)} placeholder="Configurable; never hard-coded" /></label><Button type="submit"><PlugZap size={16} className="mr-2" />Save connection</Button></form>{message && <p className="mt-4 text-sm text-slate-600">{message}</p>}</Card><Card className="p-6"><h2 className="font-bold">Configured providers</h2><div className="mt-5 space-y-3">{items.length ? items.map((item) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-4" key={item.id}><div><div className="flex items-center gap-2"><p className="font-semibold">{item.name}</p><Badge>{item.provider}</Badge></div><p className="mt-1 text-xs text-slate-500">{item.default_model ?? "Choose model per run"} · credential {item.credential_configured ? "configured" : "missing"}</p></div><Button className="bg-white text-teal-800 ring-1 ring-teal-200 hover:bg-teal-50" onClick={() => test(item.id)}>Test</Button></div>) : <EmptyState title="No providers" detail="Connect OpenAI, Anthropic, Gemini, a compatible endpoint, or Ollama." />}</div></Card></div>
    <Card className="mt-6 p-6"><h2 className="font-bold">Trace ingestion</h2><p className="mt-2 text-sm text-slate-600">Use the workspace-scoped REST API, batch endpoint, SDK/CLI, or canonical JSON import. Voice-platform adapters normalize traces before eval-core sees them; all V1 external integrations are read-only.</p><code className="mt-4 block overflow-x-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-200">POST /api/v1/ingestion/conversations</code></Card>
  </AppShell>;
}
