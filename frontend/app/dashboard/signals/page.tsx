"use client";

import { useEffect, useState } from "react";
import { API_URL, STORAGE_KEYS } from "@/lib/config";

type Signal = {
  id: number;
  strategy_name: string;
  parsed_payload: any;
  processed_at: string;
};

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedKey = localStorage.getItem(STORAGE_KEYS.API_KEY);
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, []);

  const fetchSignals = async () => {
    if (!apiKey) {
      alert("Configure uma API key primeiro na página de API Keys");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/signals?limit=50`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        alert("Erro ao buscar sinais. Verifique se tem assinatura ativa.");
        return;
      }

      const data = await response.json();
      setSignals(data.items);

      // Save API key for next time
      localStorage.setItem(STORAGE_KEYS.API_KEY, apiKey);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-slate-50">Sinais</h2>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
        <label className="text-sm font-semibold text-slate-300">API Key</label>
        <div className="mt-2 flex gap-3">
          <input
            type="text"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Cole sua API key aqui"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm text-slate-100"
          />
          <button
            onClick={fetchSignals}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
          >
            {loading ? "Carregando..." : "Buscar Sinais"}
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Sua API key será salva automaticamente neste navegador
        </p>
      </div>

      <div className="space-y-3">
        {signals.map((signal) => (
          <div key={signal.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-slate-100">{signal.strategy_name}</p>
              <p className="text-xs text-slate-500">{new Date(signal.processed_at).toLocaleString()}</p>
            </div>
            <pre className="mt-2 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-300">
              {JSON.stringify(signal.parsed_payload, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
