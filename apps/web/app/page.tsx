"use client";

import {useEffect, useState} from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDollarSign,
  FileSearch,
  Gauge,
  Languages,
  Play,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {AppShell, EmptyState, PageHeader} from "@/components/app-shell";
import {Badge, Card} from "@/components/ui";
import {ApiError, api, percent} from "@/lib/api";

type Run = {id: string; status: string; snapshot: {model?: string}; counts: Record<string, number>};
type Overview = {
  metrics: Record<string, number | null>;
  counts: Record<string, number>;
  failure_ownership: {owner: string; count: number}[];
  usage: Record<string, number>;
};
type LanguageData = {
  language_performance_gap: number | null;
  performance: {language: string; evaluated_results: number; pass_rate: number | null; meets_minimum_sample: boolean}[];
};
type Finding = {id: string; title: string; severity: string; root_cause_owner: string; confidence: number; affected_conversation_ids: string[]};

const labelMap: Record<string, string> = {
  PROMPT: "Prompt & policy",
  KNOWLEDGE_CONTENT: "Knowledge content",
  RETRIEVAL: "Retrieval",
  TOOL_SELECTION: "Tool selection",
  TOOL_RESULT_USAGE: "Tool result usage",
  CONVERSATION_POLICY: "Conversation policy",
  UNKNOWN: "Needs investigation",
};

export default function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [languages, setLanguages] = useState<LanguageData | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [latestRun, setLatestRun] = useState<Run | null>(null);
  const [authenticated, setAuthenticated] = useState(true);

  useEffect(() => {
    api<Run[]>("/eval-runs")
      .then(async (runs) => {
        const latest = runs[0] ?? null;
        setLatestRun(latest);
        const [overviewResult, languageResult, findingResult] = await Promise.all([
          latest ? api<Overview>(`/analytics/overview?run_id=${latest.id}`) : null,
          latest ? api<LanguageData>(`/analytics/languages?run_id=${latest.id}&minimum_sample_size=3`) : null,
          api<Finding[]>("/findings"),
        ]);
        setOverview(overviewResult);
        setLanguages(languageResult);
        setFindings(findingResult.slice(0, 4));
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) setAuthenticated(false);
      });
  }, []);

  const verdictData = [{
    name: "Results",
    pass: overview?.counts.pass ?? 0,
    fail: overview?.counts.fail ?? 0,
    uncertain: overview?.counts.uncertain ?? 0,
    notApplicable: overview?.counts.not_applicable ?? 0,
  }];
  const ownership = overview?.failure_ownership.map((item) => ({
    ...item,
    label: labelMap[item.owner] ?? item.owner.replaceAll("_", " "),
  })) ?? [];

  return (
    <AppShell>
      <PageHeader
        title="Evaluation overview"
        description="Understand quality, risk, evidence coverage, and the root causes that deserve your team’s attention."
        actions={<div className="flex flex-wrap items-center gap-3"><Badge className="border-emerald-200 bg-emerald-50 text-emerald-700">No production writeback</Badge><div className="hidden text-right sm:block"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Latest run</p><p className="mt-1 text-xs font-semibold text-slate-700">{latestRun?.snapshot.model ?? "No model yet"} · {latestRun?.status ?? "Ready"}</p></div><a href="/eval-runs" className="inline-flex h-10 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-teal-800"><Play className="mr-2" size={15} />New evaluation</a></div>}
      />
      {!authenticated && <a className="mt-6 flex items-center justify-between rounded-2xl bg-slate-950 p-4 text-sm font-semibold text-white" href="/login">Sign in to your workspace <ArrowRight size={18} /></a>}

      <section aria-label="Key metrics" className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={CheckCircle2} label="Eval pass rate" value={percent(overview?.metrics.eval_pass_rate)} detail={`${overview?.counts.pass ?? 0} of ${(overview?.counts.pass ?? 0) + (overview?.counts.fail ?? 0) + (overview?.counts.uncertain ?? 0)} evaluated checks`} tone="emerald" progress={overview?.metrics.eval_pass_rate ?? 0} />
        <MetricCard icon={ShieldAlert} label="Critical failure rate" value={percent(overview?.metrics.critical_failure_rate)} detail={`${overview?.counts.critical_failures ?? 0} critical failures`} tone="rose" progress={overview?.metrics.critical_failure_rate ?? 0} inverse />
        <MetricCard icon={FileSearch} label="Grounded responses" value={percent(overview?.metrics.grounded_response_rate)} detail="Claims supported by evidence" tone="blue" progress={overview?.metrics.grounded_response_rate ?? 0} />
        <MetricCard icon={Gauge} label="Evaluation coverage" value={percent(overview?.metrics.eval_coverage ?? 0)} detail="Applicable checks completed" tone="violet" progress={overview?.metrics.eval_coverage ?? 0} />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-bold tracking-tight text-slate-950">Evaluation health</h2><p className="mt-1 text-xs text-slate-500">Structured verdict distribution from the latest run</p></div><Badge className="border-emerald-200 bg-emerald-50 text-emerald-700"><span className="mr-1.5 size-1.5 rounded-full bg-emerald-500" />Live analytics</Badge></div>
          <div className="mt-7 h-24">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={verdictData} layout="vertical" margin={{left: -36, right: 4}} barSize={28}>
                <XAxis type="number" hide /><YAxis type="category" dataKey="name" hide />
                <Tooltip cursor={false} contentStyle={{borderRadius: 12, borderColor: "#e2e8f0", fontSize: 12}} />
                <Bar dataKey="pass" stackId="a" fill="#10b981" radius={[7, 0, 0, 7]} />
                <Bar dataKey="fail" stackId="a" fill="#f43f5e" />
                <Bar dataKey="uncertain" stackId="a" fill="#f59e0b" />
                <Bar dataKey="notApplicable" stackId="a" fill="#cbd5e1" radius={[0, 7, 7, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <LegendItem color="bg-emerald-500" label="Passed" value={overview?.counts.pass ?? 0} />
            <LegendItem color="bg-rose-500" label="Failed" value={overview?.counts.fail ?? 0} />
            <LegendItem color="bg-amber-500" label="Uncertain" value={overview?.counts.uncertain ?? 0} />
            <LegendItem color="bg-slate-300" label="Not applicable" value={overview?.counts.not_applicable ?? 0} />
          </div>
        </Card>
        <Card className="overflow-hidden p-6">
          <div className="flex items-center justify-between"><div><h2 className="font-bold tracking-tight text-slate-950">Judge usage</h2><p className="mt-1 text-xs text-slate-500">Transparent model consumption</p></div><CircleDollarSign className="text-teal-600" size={21} /></div>
          <div className="mt-6 grid grid-cols-2 gap-3"><UsageStat label="Input tokens" value={formatNumber(overview?.usage.input_tokens)} /><UsageStat label="Output tokens" value={formatNumber(overview?.usage.output_tokens)} /><UsageStat label="Latency" value={`${Math.round((overview?.usage.latency_ms ?? 0) / 1000)}s`} /><UsageStat label="Model" value={latestRun?.snapshot.model?.split("/").at(-1) ?? "—"} /></div>
          <p className="mt-5 rounded-xl bg-teal-50 p-3 text-[11px] leading-5 text-teal-800">Retries, fallbacks, provider, model, latency, and token usage remain visible in every run.</p>
        </Card>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[0.82fr_1.18fr]">
        <Card className="p-6">
          <div className="flex items-start justify-between"><div><h2 className="font-bold tracking-tight text-slate-950">Failure ownership</h2><p className="mt-1 text-xs text-slate-500">Earliest likely causal layer</p></div><Sparkles className="text-violet-500" size={19} /></div>
          <div className="mt-5 h-60">{ownership.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={ownership} layout="vertical" margin={{left: 8, right: 10}}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eef2f7" /><XAxis type="number" hide /><YAxis dataKey="label" type="category" width={128} tick={{fontSize: 11, fill: "#64748b"}} axisLine={false} tickLine={false} /><Tooltip cursor={{fill: "#f8fafc"}} contentStyle={{borderRadius: 12, borderColor: "#e2e8f0", fontSize: 12}} /><Bar dataKey="count" fill="#0f766e" radius={[0, 7, 7, 0]} barSize={18} /></BarChart></ResponsiveContainer> : <EmptyState title="No findings yet" detail="Run an evaluation to populate evidence-linked ownership data." />}</div>
        </Card>
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="font-bold tracking-tight text-slate-950">Needs attention</h2><p className="mt-1 text-xs text-slate-500">Prioritized by severity, volume, recency, and confidence</p></div><a href="/findings" className="text-xs font-semibold text-teal-700">View all <ArrowRight className="ml-1 inline" size={13} /></a></div>
          {findings.length ? <div className="divide-y divide-slate-100">{findings.map((item) => <a href="/findings" key={item.id} className="group flex items-center gap-4 px-6 py-4 hover:bg-slate-50/70"><div className={`grid size-9 shrink-0 place-items-center rounded-xl ${item.severity === "CRITICAL" ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600"}`}><AlertTriangle size={17} /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-900 group-hover:text-teal-800">{item.title}</p><p className="mt-1 text-[11px] text-slate-500">{labelMap[item.root_cause_owner] ?? item.root_cause_owner} · {item.affected_conversation_ids.length} calls affected</p></div><div className="text-right"><Badge className={item.severity === "CRITICAL" ? "border-rose-200 bg-rose-50 text-rose-700" : "border-amber-200 bg-amber-50 text-amber-700"}>{item.severity}</Badge><p className="mt-1.5 text-[10px] text-slate-400">{percent(item.confidence)} confidence</p></div></a>)}</div> : <div className="p-6"><EmptyState title="No findings" detail="Completed runs with failures appear here." /></div>}
        </Card>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="overflow-hidden"><div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><div className="flex items-center gap-2"><Languages className="text-teal-600" size={18} /><h2 className="font-bold tracking-tight text-slate-950">Language performance</h2></div><p className="mt-1 text-xs text-slate-500">Same evaluator semantics across every language</p></div><div className="text-right"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Parity gap</p><p className="mt-1 text-lg font-bold text-slate-900">{percent(languages?.language_performance_gap)}</p></div></div><div className="grid divide-y divide-slate-100 sm:grid-cols-2 sm:divide-x sm:divide-y-0 xl:grid-cols-5">{languages?.performance.slice(0, 5).map((item) => <div className="p-5" key={item.language}><div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-600">{displayLanguage(item.language)}</span><span className={`size-2 rounded-full ${item.meets_minimum_sample ? "bg-emerald-500" : "bg-amber-400"}`} /></div><p className="mt-3 text-2xl font-bold tracking-tight text-slate-950">{percent(item.pass_rate)}</p><p className="mt-1 text-[10px] text-slate-400">{item.evaluated_results} evaluated checks</p><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-600" style={{width: `${(item.pass_rate ?? 0) * 100}%`}} /></div></div>)}</div></Card>
        <Card className="bg-gradient-to-br from-slate-950 to-slate-800 p-6 text-white"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-teal-300">Recommended next step</p><h2 className="mt-3 text-xl font-bold tracking-tight">Review evidence before changing behavior.</h2><p className="mt-2 text-xs leading-5 text-slate-300">The top findings are ready for human review. Approved changes remain exportable drafts only.</p><a href="/recommendations" className="mt-5 inline-flex h-9 items-center rounded-xl bg-white px-4 text-xs font-bold text-slate-900">Review recommendations <ArrowRight className="ml-2" size={14} /></a></Card>
      </section>
    </AppShell>
  );
}

const tones = {emerald: "bg-emerald-50 text-emerald-600", rose: "bg-rose-50 text-rose-600", blue: "bg-blue-50 text-blue-600", violet: "bg-violet-50 text-violet-600"};

function MetricCard({icon: Icon, label, value, detail, tone, progress, inverse = false}: {icon: typeof Gauge; label: string; value: string; detail: string; tone: keyof typeof tones; progress: number; inverse?: boolean}) {
  return <Card className="relative overflow-hidden p-5"><div className="flex items-start justify-between"><div className={`grid size-10 place-items-center rounded-xl ${tones[tone]}`}><Icon size={19} /></div><Badge className="border-slate-100 bg-white text-slate-400">Latest run</Badge></div><p className="mt-5 text-xs font-semibold text-slate-500">{label}</p><p className="mt-1 text-3xl font-bold tracking-[-0.04em] text-slate-950">{value}</p><p className="mt-2 text-[11px] text-slate-400">{detail}</p><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${inverse ? "bg-rose-500" : "bg-teal-600"}`} style={{width: `${Math.max(2, Math.min(progress * 100, 100))}%`}} /></div></Card>;
}

function LegendItem({color, label, value}: {color: string; label: string; value: number}) { return <div className="rounded-xl bg-slate-50 p-3"><div className="flex items-center gap-2"><span className={`size-2 rounded-full ${color}`} /><span className="text-[10px] font-semibold text-slate-500">{label}</span></div><p className="mt-1.5 text-lg font-bold text-slate-900">{value}</p></div>; }
function UsageStat({label, value}: {label: string; value: string}) { return <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3"><p className="text-[10px] font-semibold text-slate-400">{label}</p><p className="mt-1 truncate text-sm font-bold text-slate-800">{value}</p></div>; }
function formatNumber(value?: number) { return value == null ? "—" : new Intl.NumberFormat("en", {notation: "compact", maximumFractionDigits: 1}).format(value); }
function displayLanguage(code: string) { return ({en: "English", hi: "Hindi", "hi-Latn": "Hinglish", ta: "Tamil", ml: "Malayalam"} as Record<string, string>)[code] ?? code; }
