"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "momentum:user-token";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) {
      router.push("/auth/login");
      return;
    }
    setLoading(false);
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    router.push("/auth/login");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="text-slate-400">Carregando...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800 bg-slate-900/80">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-slate-50">Momentum</h1>
            <div className="flex gap-6">
              <Link href="/dashboard" className="text-sm text-slate-300 hover:text-slate-100">
                Dashboard
              </Link>
              <Link href="/dashboard/plans" className="text-sm text-slate-300 hover:text-slate-100">
                Planos
              </Link>
              <Link href="/dashboard/api-keys" className="text-sm text-slate-300 hover:text-slate-100">
                API Keys
              </Link>
              <Link href="/dashboard/signals" className="text-sm text-slate-300 hover:text-slate-100">
                Sinais
              </Link>
              <button onClick={handleLogout} className="text-sm text-red-400 hover:text-red-300">
                Sair
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  );
}
