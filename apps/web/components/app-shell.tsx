"use client";

import type {ReactNode} from "react";
import {Bell, HelpCircle, Menu, Search} from "lucide-react";
import {Sidebar} from "@/components/sidebar";

export function AppShell({children}: {children: ReactNode}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="min-w-0 flex-1">
        <div className="sticky top-0 z-20 flex h-16 items-center border-b border-slate-200/80 bg-white/90 px-5 backdrop-blur-xl md:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <Menu size={20} />
            <span className="font-bold">Voice AI Evals</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <label className="hidden h-9 w-64 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 text-slate-400 md:flex">
              <Search size={15} /><span className="text-xs">Search conversations, findings…</span>
            </label>
            <a aria-label="Documentation" href="http://localhost:8000/docs" className="grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 hover:bg-slate-50"><HelpCircle size={17} /></a>
            <button aria-label="Notifications" className="relative grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 hover:bg-slate-50"><Bell size={17} /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-amber-500" /></button>
            <div className="ml-1 grid size-9 place-items-center rounded-xl bg-gradient-to-br from-teal-600 to-cyan-600 text-xs font-bold text-white">RK</div>
          </div>
        </div>
        <div className="px-5 py-6 md:px-8 md:py-8">
          <div className="mx-auto max-w-[1440px]">{children}</div>
        </div>
      </main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-teal-700">Voice intelligence</p>
        <h1 className="text-3xl font-bold tracking-[-0.025em] text-slate-950">{title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{description}</p>
      </div>
      {actions}
    </header>
  );
}

export function EmptyState({title, detail}: {title: string; detail: string}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <p className="font-semibold text-slate-800">{title}</p>
      <p className="mt-2 text-sm text-slate-500">{detail}</p>
    </div>
  );
}
