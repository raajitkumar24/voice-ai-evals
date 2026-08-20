"use client";

import {useEffect, useState} from "react";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Card} from "@/components/ui";
import {api} from "@/lib/api";

type Definition = {id: string; version: string; name: string; family: string; description: string; applicability: string; severity: string};
type Suite = {id: string; name: string; version: string; definition_versions: string[]; thresholds: Record<string, number>};

export default function EvalSetupPage() {
  const [definitions, setDefinitions] = useState<Definition[]>([]); const [suites, setSuites] = useState<Suite[]>([]);
  useEffect(() => { void api<Definition[]>("/eval-setup/definitions").then(setDefinitions); void api<Suite[]>("/eval-setup/suites").then(setSuites); }, []);
  return <AppShell><PageHeader title="Evaluation setup" description="Versioned, declarative specialist evaluators and suites. Analytics always use structured verdicts—not parsed judge prose." /><section className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_1fr]"><Card className="overflow-hidden"><div className="border-b border-slate-200 p-5"><h2 className="font-bold">Evaluator definitions</h2></div>{definitions.length ? <div className="divide-y divide-slate-100">{definitions.map((item) => <div className="p-5" key={`${item.id}:${item.version}`}><div className="flex flex-wrap items-center gap-2"><p className="font-semibold">{item.name}</p><Badge>{item.family}</Badge><Badge>{item.severity}</Badge><span className="ml-auto font-mono text-xs text-slate-500">v{item.version}</span></div><p className="mt-2 text-sm text-slate-600">{item.description}</p><p className="mt-2 text-xs text-slate-500">Applies when: {item.applicability}</p></div>)}</div> : <div className="p-5"><EmptyState title="No evaluators" detail="Seed or create a versioned evaluator definition." /></div>}</Card><Card className="p-5"><h2 className="font-bold">Eval suites</h2><div className="mt-4 space-y-4">{suites.map((suite) => <div className="rounded-lg border border-slate-200 p-4" key={suite.id}><div className="flex justify-between"><p className="font-semibold">{suite.name}</p><Badge>v{suite.version}</Badge></div><p className="mt-2 text-xs text-slate-500">{suite.definition_versions.length} evaluator versions</p><pre className="mt-3 overflow-x-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(suite.thresholds, null, 2)}</pre></div>)}</div></Card></section></AppShell>;
}
