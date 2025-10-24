"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "momentum:user-token";

type ApiKey = {
  id: number;
  name: string;
  key_preview: string;
  is_active: boolean;
  created_at: string;
};

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchKeys = async () => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) return;

    const response = await fetch("http://localhost:8000/api/users/api-keys", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    setKeys(data.items);
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    setLoading(true);

    try {
      const token = localStorage.getItem(STORAGE_KEY);
      const response = await fetch("http://localhost:8000/api/users/api-keys", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newKeyName }),
      });

      const data = await response.json();
      setNewKeyValue(data.key);
      setNewKeyName("");
      await fetchKeys();
    } finally {
      setLoading(false);
    }
  };

  const deleteKey = async (id: number) => {
    const token = localStorage.getItem(STORAGE_KEY);
    await fetch(`http://localhost:8000/api/users/api-keys/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    await fetchKeys();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-slate-50">API Keys</h2>

      {newKeyValue && (
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-6">
          <p className="text-sm font-semibold text-emerald-200">Chave criada! Copie agora:</p>
          <p className="mt-2 break-all font-mono text-sm text-emerald-100">{newKeyValue}</p>
          <button
            onClick={() => setNewKeyValue("")}
            className="mt-4 text-sm text-emerald-300 hover:text-emerald-200"
          >
            Fechar
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
        <h3 className="text-lg font-semibold text-slate-50">Criar Nova Chave</h3>
        <div className="mt-4 flex gap-3">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Nome da chave"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm text-slate-100"
          />
          <button
            onClick={createKey}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:bg-slate-700"
          >
            Criar
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {keys.map((key) => (
          <div key={key.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div>
              <p className="font-semibold text-slate-100">{key.name}</p>
              <p className="text-sm text-slate-500">{key.key_preview}</p>
            </div>
            <button
              onClick={() => deleteKey(key.id)}
              className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-200 hover:bg-red-500/20"
            >
              Deletar
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
