"use client";

import {
  Activity,
  AudioLines,
  Bot,
  BrainCircuit,
  Database,
  FileCheck2,
  Gauge,
  MessageSquareText,
  PlugZap,
  Settings,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import {usePathname} from "next/navigation";

const navigation = [
  ["Overview", "/", Gauge],
  ["Findings", "/findings", FileCheck2],
  ["Conversations", "/conversations", MessageSquareText],
  ["Knowledge & Retrieval", "/knowledge-retrieval", Database],
  ["Tools", "/tools", Wrench],
  ["Recommendations", "/recommendations", Sparkles],
  ["Eval Runs", "/eval-runs", Activity],
  ["Regression", "/regression", ShieldCheck],
  ["Eval Setup", "/eval-setup", BrainCircuit],
  ["Integrations", "/integrations", PlugZap],
  ["Settings", "/settings", Settings],
] as const;

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col border-r border-slate-200/80 bg-white px-4 py-5 text-slate-600 lg:flex">
      <div className="mb-5 flex items-center gap-3 px-2">
        <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-teal-600 to-cyan-600 text-white shadow-lg shadow-teal-700/15"><AudioLines size={22} /></div>
        <div><p className="font-bold tracking-tight text-slate-950">Voice AI Evals</p><p className="text-[11px] text-slate-400">Evidence before action</p></div>
      </div>
      <button className="mb-5 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2.5 text-left"><span><span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">Workspace</span><span className="mt-0.5 block text-xs font-semibold text-slate-800">Acme Voice Operations</span></span><span className="text-slate-400">⌄</span></button>
      <nav aria-label="Primary" className="space-y-1">
        {navigation.map(([label, href, Icon]) => (
          <a
            key={label}
            href={href}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition hover:bg-slate-50 hover:text-slate-950 ${pathname === href ? "bg-teal-50 font-semibold text-teal-800 ring-1 ring-inset ring-teal-100" : ""}`}
          >
            <Icon size={18} />{label}
          </a>
        ))}
      </nav>
      <div className="mt-auto rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50 to-cyan-50 p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-teal-900"><Bot size={16} className="text-teal-700" />Human controlled</div>
        <p className="mt-1.5 text-[11px] leading-5 text-teal-800/70">Recommendations stay draft-only until your team reviews them.</p>
      </div>
      <div className="mt-3 flex items-center gap-3 border-t border-slate-100 px-2 pt-4"><div className="grid size-8 place-items-center rounded-lg bg-slate-100 text-[10px] font-bold text-slate-600">RK</div><div><p className="text-xs font-semibold text-slate-800">Workspace admin</p><p className="text-[10px] text-slate-400">Local deployment</p></div><span className="ml-auto size-2 rounded-full bg-emerald-500" /></div>
    </aside>
  );
}
