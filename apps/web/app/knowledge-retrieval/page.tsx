"use client";

import {useEffect, useState} from "react";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Card} from "@/components/ui";
import {api, percent} from "@/lib/api";

type Run = {id: string};
type LanguageData = {minimum_sample_size: number; language_performance_gap: number | null; performance: {language: string; total_results: number; evaluated_results: number; pass_rate: number | null; meets_minimum_sample: boolean}[]};

export default function KnowledgePage() {
  const [data, setData] = useState<LanguageData | null>(null);
  useEffect(() => { void api<Run[]>("/eval-runs").then((runs) => runs[0] ? api<LanguageData>(`/analytics/languages?run_id=${runs[0].id}`) : null).then(setData); }, []);
  return <AppShell><PageHeader title="Knowledge, retrieval & language" description="Grounding, RAG applicability, and language parity share one pipeline; translations never overwrite source utterances." /><section className="mt-8 grid gap-4 sm:grid-cols-3"><Card className="p-5"><p className="text-xs font-semibold uppercase text-slate-500">Language gap</p><p className="mt-2 text-3xl font-bold">{percent(data?.language_performance_gap)}</p></Card><Card className="p-5"><p className="text-xs font-semibold uppercase text-slate-500">Minimum sample</p><p className="mt-2 text-3xl font-bold">{data?.minimum_sample_size ?? 5}</p></Card><Card className="p-5"><p className="text-xs font-semibold uppercase text-slate-500">Languages observed</p><p className="mt-2 text-3xl font-bold">{data?.performance.length ?? 0}</p></Card></section><Card className="mt-6 overflow-hidden">{data?.performance.length ? <table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr><th className="p-4">Language</th><th>Pass rate</th><th>Evaluated</th><th>Confidence</th></tr></thead><tbody>{data.performance.map((item) => <tr className="border-t border-slate-100" key={item.language}><td className="p-4 font-semibold">{item.language}</td><td>{percent(item.pass_rate)}</td><td>{item.evaluated_results} / {item.total_results}</td><td><Badge>{item.meets_minimum_sample ? "Reportable" : "Low sample"}</Badge></td></tr>)}</tbody></table> : <div className="p-6"><EmptyState title="No language metrics" detail="Run the multilingual demo or evaluate ingested traces." /></div>}</Card></AppShell>;
}
