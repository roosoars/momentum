"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "momentum:user-token";

type Plan = {
  product_id: string;
  product_name: string;
  product_description: string | null;
  prices: Array<{
    price_id: string;
    amount: number;
    currency: string;
    interval: string | null;
    interval_count: number | null;
  }>;
};

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const response = await fetch("http://localhost:8000/api/users/subscription/plans");
        const data = await response.json();
        setPlans(data);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSubscribe = async (priceId: string) => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) return;

    try {
      const response = await fetch("http://localhost:8000/api/users/subscription/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ price_id: priceId }),
      });

      const data = await response.json();
      window.location.href = data.checkout_url;
    } catch (err) {
      alert("Erro ao criar sessão de checkout");
    }
  };

  if (loading) return <p className="text-slate-400">Carregando planos...</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-slate-50">Planos Disponíveis</h2>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => (
          <div key={plan.product_id} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
            <h3 className="text-lg font-semibold text-slate-50">{plan.product_name}</h3>
            {plan.product_description && (
              <p className="mt-2 text-sm text-slate-400">{plan.product_description}</p>
            )}

            <div className="mt-4 space-y-2">
              {plan.prices.map((price) => (
                <div key={price.price_id} className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
                  <p className="text-xl font-bold text-slate-100">
                    {(price.amount / 100).toLocaleString("pt-BR", {
                      style: "currency",
                      currency: price.currency,
                    })}
                  </p>
                  {price.interval && (
                    <p className="text-xs text-slate-500">
                      por {price.interval_count! > 1 ? price.interval_count : ""} {price.interval}
                    </p>
                  )}
                  <button
                    onClick={() => handleSubscribe(price.price_id)}
                    className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
                  >
                    Assinar
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
