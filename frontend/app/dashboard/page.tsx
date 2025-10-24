"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const STORAGE_KEY = "momentum:user-token";

type UserProfile = {
  id: number;
  email: string;
  is_verified: boolean;
  has_active_subscription: boolean;
  created_at: string;
};

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem(STORAGE_KEY);
      if (!token) return;

      try {
        const response = await fetch("http://localhost:8000/api/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) throw new Error();

        const data = await response.json();
        setProfile(data);

        if (!data.is_verified) {
          alert("Por favor, verifique seu email antes de continuar.");
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        router.push("/auth/login");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  if (loading) {
    return <p className="text-slate-400">Carregando...</p>;
  }

  if (!profile) return null;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
        <h2 className="text-xl font-semibold text-slate-50">Bem-vindo!</h2>
        <p className="mt-2 text-sm text-slate-400">{profile.email}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Status da conta</p>
          <p className="mt-2 text-lg font-semibold text-slate-100">
            {profile.is_verified ? "✓ Verificada" : "⚠️ Não verificada"}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Assinatura</p>
          <p className="mt-2 text-lg font-semibold text-slate-100">
            {profile.has_active_subscription ? "✓ Ativa" : "❌ Sem assinatura"}
          </p>
        </div>
      </div>

      {!profile.has_active_subscription && profile.is_verified && (
        <div className="rounded-xl border border-blue-500/40 bg-blue-500/10 p-6 text-center">
          <p className="text-sm text-blue-200">
            Assine um plano para começar a receber sinais!
          </p>
          <button
            onClick={() => router.push("/dashboard/plans")}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
          >
            Ver planos
          </button>
        </div>
      )}
    </div>
  );
}
