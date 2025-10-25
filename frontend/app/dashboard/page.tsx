"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL, STORAGE_KEYS } from "@/lib/config";

type UserProfile = {
  id: number;
  email: string;
  is_verified: boolean;
  has_active_subscription: boolean;
  created_at: string;
};

type Subscription = {
  id: number;
  stripe_subscription_id: string;
  stripe_price_id: string;
  status: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  is_active: boolean;
};

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      if (!token) return;

      try {
        const [profileRes, subRes] = await Promise.all([
          fetch(`${API_URL}/api/users/me`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/users/subscription/current`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (!profileRes.ok) throw new Error();

        const profileData = await profileRes.json();
        setProfile(profileData);

        if (subRes.ok) {
          const subData = await subRes.json();
          setSubscription(subData);
        }

        if (!profileData.is_verified) {
          alert("Por favor, verifique seu email antes de continuar.");
        }
      } catch {
        localStorage.removeItem(STORAGE_KEYS.USER_TOKEN);
        router.push("/auth/login");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const handleCancelSubscription = async () => {
    if (!confirm("Tem certeza que deseja cancelar sua assinatura?")) return;

    setCancelling(true);
    try {
      const token = localStorage.getItem(STORAGE_KEYS.USER_TOKEN);
      const response = await fetch(`${API_URL}/api/users/subscription/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error();

      alert("Assinatura cancelada. Você terá acesso até o fim do período.");
      window.location.reload();
    } catch {
      alert("Erro ao cancelar assinatura.");
    } finally {
      setCancelling(false);
    }
  };

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

      {subscription && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
          <h3 className="text-lg font-semibold text-slate-50">Detalhes da Assinatura</h3>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
              <p className="mt-2 text-base font-semibold text-slate-100">{subscription.status}</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Próxima cobrança</p>
              <p className="mt-2 text-base font-semibold text-slate-100">
                {new Date(subscription.current_period_end).toLocaleDateString("pt-BR")}
              </p>
            </div>
          </div>

          {subscription.cancel_at_period_end && (
            <div className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              Assinatura será cancelada ao fim do período
            </div>
          )}

          {!subscription.cancel_at_period_end && subscription.is_active && (
            <button
              onClick={handleCancelSubscription}
              disabled={cancelling}
              className="mt-4 w-full rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-200 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {cancelling ? "Cancelando..." : "Cancelar assinatura"}
            </button>
          )}
        </div>
      )}

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
