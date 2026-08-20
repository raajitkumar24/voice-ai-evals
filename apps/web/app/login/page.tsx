"use client";

import {FormEvent, useState} from "react";
import {AudioLines} from "lucide-react";
import {Button, Card} from "@/components/ui";
import {api} from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("change-me-before-production");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/auth/login", {method: "POST", body: JSON.stringify({email, password})});
      window.location.assign("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign in failed");
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <Card className="w-full max-w-md p-8">
        <div className="mb-8 flex items-center gap-3"><div className="grid size-11 place-items-center rounded-xl bg-teal-600 text-white"><AudioLines /></div><div><h1 className="font-bold text-slate-950">Voice AI Evals</h1><p className="text-xs text-slate-500">Local workspace sign in</p></div></div>
        <form onSubmit={submit} className="space-y-5">
          <label className="block text-sm font-semibold">Email<input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label className="block text-sm font-semibold">Password<input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <Button className="w-full" type="submit">Sign in</Button>
        </form>
        <p className="mt-6 text-xs leading-5 text-slate-500">The default credentials are for local development only. Change them before any shared deployment.</p>
      </Card>
    </main>
  );
}
