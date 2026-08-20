import type {HTMLAttributes, ButtonHTMLAttributes} from "react";
import {cn} from "@/lib/utils";

export function Card({className, ...props}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.03),0_8px_24px_rgba(15,23,42,0.035)]", className)} {...props} />;
}

export function Button({className, ...props}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-px hover:bg-teal-800 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:translate-y-0 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({className, ...props}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full border border-slate-200/80 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-slate-600", className)}
      {...props}
    />
  );
}
