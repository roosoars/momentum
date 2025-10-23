"use client";

import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

type TabKey = "home" | "strategies" | "telegram" | "signals";

type Banner = {
  type: "success" | "error";
  message: string;
};

type StrategySignal = {
  id: number;
  strategy_id: number;
  channel_id: string;
  telegram_message_id: number;
  raw_message: string | null;
  parsed_payload: Record<string, unknown>;
  status: string;
  error: string | null;
  received_at: string;
  processed_at: string;
};

type StrategyItem = {
  id: number;
  name: string;
  channel_identifier: string;
  channel_id: string | null;
  channel_title: string | null;
  channel_linked_at: string | null;
  is_active: boolean;
  is_paused: boolean;
  status: "active" | "paused" | "inactive";
  created_at: string;
  updated_at: string;
  last_signal?: StrategySignal;
};

type TelegramCaptureState = {
  active: boolean;
  paused: boolean;
};

type TelegramAccount = {
  display_name: string | null;
  username: string | null;
  phone: string | null;
};

type TelegramStatus = {
  connected: boolean;
  authorized: boolean;
  pending_phone: string | null;
  phone_number: string | null;
  password_required: boolean;
  channel_ids?: (string | null)[] | null;
  channel_titles?: (string | null)[] | null;
  channels?: { id: string; title: string | null }[] | null;
  capture?: TelegramCaptureState;
  account?: TelegramAccount | null;
};

type ChannelConfig = {
  channels?: { id: string; title: string | null }[];
  status: TelegramStatus;
  capture_state?: TelegramCaptureState;
};

type AdminProfile = {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type ChannelOption = {
  id: string;
  title: string;
  username?: string | null;
  type?: string | null;
};

type NavItem = {
  id: TabKey;
  label: string;
  description?: string;
  icon: JSX.Element;
  mobileOnly?: boolean;
};

const STORAGE_KEY = "momentum:admin-token";

const resolveApiBaseOnServer = () => {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return base.replace(/\/$/, "");
};

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium"
  }).format(new Date(value));

const HomeIcon = () => (
  <svg aria-hidden className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path d="M3 11.25 12 4l9 7.25V21a.75.75 0 0 1-.75.75H6.75A.75.75 0 0 1 6 21v-6.75h12" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LayersIcon = () => (
  <svg aria-hidden className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path d="m12 3 8.5 4.5L12 12 3.5 7.5 12 3Z" strokeLinecap="round" strokeLinejoin="round" />
    <path d="m4 12.5 8 4.5 8-4.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="m4 17.5 8 4.5 8-4.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const TelegramIcon = () => (
  <svg aria-hidden className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path d="M21 3 3 11l6 2 2 6 3-4 4.5 3 2.5-15Z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SignalIcon = () => (
  <svg aria-hidden className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path d="M3 17.25 9.25 11 14 15.75 21 9" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M21 9h-4.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M21 13.5v-4.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const NAV_ITEMS: NavItem[] = [
  {
    id: "home",
    label: "Painel",
    description: "Resumo operacional",
    icon: <HomeIcon />
  },
  {
    id: "strategies",
    label: "Estratégias",
    description: "Gerencie sinais",
    icon: <LayersIcon />
  },
  {
    id: "telegram",
    label: "Telegram",
    description: "Sessão e captura",
    icon: <TelegramIcon />
  },
  {
    id: "signals",
    label: "Sinais",
    description: "Últimos alertas",
    icon: <SignalIcon />,
    mobileOnly: true
  }
];

const NAV_SECTIONS: Array<{ title: string; items: TabKey[] }> = [
  { title: "Resumo", items: ["home"] },
  { title: "Operações", items: ["strategies"] },
  { title: "Conexões", items: ["telegram"] }
];

export default function DashboardPage() {
  const [apiBase] = useState(() => {
    if (typeof window !== "undefined") {
      return window.location.origin.replace(/\/$/, "");
    }
    return resolveApiBaseOnServer();
  });

  const [token, setToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [banner, setBanner] = useState<Banner | null>(null);
  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<number | null>(null);
  const [signalsMap, setSignalsMap] = useState<Record<number, StrategySignal[]>>({});
  const [telegramStatus, setTelegramStatus] = useState<TelegramStatus | null>(null);
  const [channelConfig, setChannelConfig] = useState<ChannelConfig | null>(null);
  const [, setAdminProfile] = useState<AdminProfile | null>(null);
  const [availableChannels, setAvailableChannels] = useState<ChannelOption[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [initialised, setInitialised] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setToken(stored);
    }
    setInitialised(true);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    if (token) {
      window.localStorage.setItem(STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [token]);

  useEffect(() => {
    if (!banner) {
      return;
    }
    const handler = window.setTimeout(() => setBanner(null), 5000);
    return () => window.clearTimeout(handler);
  }, [banner]);

  const apiFetch = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      if (!token) {
        throw new Error("Sessão expirada. Faça login novamente.");
      }
      const response = await fetch(`${apiBase}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
          Authorization: `Bearer ${token}`
        }
      });
      if (response.status === 401) {
        setToken(null);
        setBanner({ type: "error", message: "Sessão expirada. Faça login novamente." });
        throw new Error("Sessão expirada");
      }
      if (!response.ok) {
        let detail = "Falha na requisição.";
        try {
          const payload = await response.json();
          if (typeof payload?.detail === "string") {
            detail = payload.detail;
          }
        } catch (error) {
          // ignore body parsing errors
        }
        throw new Error(detail);
      }
      if (response.status === 204) {
        return undefined as T;
      }
      return (await response.json()) as T;
    },
    [apiBase, token]
  );

  const fetchStrategies = useCallback(async () => {
    const data = await apiFetch<{ items: StrategyItem[]; count: number }>("/api/strategies");
    setStrategies(data.items);
    setSelectedStrategyId(prev => {
      if (prev && data.items.some(item => item.id === prev)) {
        return prev;
      }
      return data.items[0]?.id ?? null;
    });
  }, [apiFetch]);

  const fetchSignals = useCallback(
    async (strategyId: number) => {
      const data = await apiFetch<{ items: StrategySignal[]; count: number }>(
        `/api/strategies/${strategyId}/signals?limit=100`
      );
      const todayIso = new Date().toISOString().slice(0, 10);
      const filtered = data.items.filter(item => item.processed_at?.slice(0, 10) === todayIso);
      setSignalsMap(prev => ({ ...prev, [strategyId]: filtered }));
    },
    [apiFetch]
  );

  const fetchTelegramSuite = useCallback(async () => {
    const [status, config] = await Promise.all([
      apiFetch<TelegramStatus>("/api/auth/status"),
      apiFetch<ChannelConfig>("/api/config")
    ]);
    setTelegramStatus(status);
    setChannelConfig(config);
  }, [apiFetch]);

  const fetchAvailableChannels = useCallback(async () => {
    setChannelsLoading(true);
    try {
      const response = await apiFetch<{ items: ChannelOption[]; count: number }>("/api/config/channels/available");
      const items = response.items ?? [];
      const normalised = items.map(item => ({
        id: item.id,
        title: item.title ?? item.username ?? item.id,
        username: item.username,
        type: item.type
      }));
      setAvailableChannels(normalised);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro ao listar canais disponíveis.";
      if (!message.toLowerCase().includes("autentique")) {
        setBanner({ type: "error", message });
      }
    } finally {
      setChannelsLoading(false);
    }
  }, [apiFetch]);

  const fetchProfile = useCallback(async () => {
    const profile = await apiFetch<AdminProfile>("/api/admin/me");
    setAdminProfile(profile);
  }, [apiFetch]);

  useEffect(() => {
    if (!token) {
      setStrategies([]);
      setSignalsMap({});
      setTelegramStatus(null);
      setChannelConfig(null);
      setAdminProfile(null);
      setSelectedStrategyId(null);
      setAvailableChannels([]);
      setChannelsLoading(false);
      return;
    }
    (async () => {
      try {
        await Promise.all([fetchProfile(), fetchStrategies(), fetchTelegramSuite(), fetchAvailableChannels()]);
      } catch (error) {
        if (error instanceof Error && error.message.includes("Sessão expirada")) {
          return;
        }
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao carregar dados." });
      }
    })();
  }, [token, fetchProfile, fetchStrategies, fetchTelegramSuite, fetchAvailableChannels]);

  useEffect(() => {
    if (!selectedStrategyId) {
      return;
    }
    if (!signalsMap[selectedStrategyId]) {
      fetchSignals(selectedStrategyId).catch(error => {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao buscar sinais." });
      });
    }
  }, [selectedStrategyId, signalsMap, fetchSignals]);

  useEffect(() => {
    if (!token || !selectedStrategyId) {
      return;
    }
    const interval = window.setInterval(() => {
      fetchSignals(selectedStrategyId).catch(() => {
        /* suppress transient refresh errors */
      });
    }, 5000);
    return () => window.clearInterval(interval);
  }, [token, selectedStrategyId, fetchSignals]);

  const handleLogin = useCallback(
    async (email: string, password: string) => {
      setActionLoading("login");
      try {
        const response = await fetch(`${apiBase}/api/admin/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ email, password })
        });
        if (!response.ok) {
          let message = "Não foi possível autenticar.";
          try {
            const payload = await response.json();
            if (typeof payload?.detail === "string") {
              message = payload.detail;
            }
          } catch (error) {
            // ignore
          }
          throw new Error(message);
        }
        const data = (await response.json()) as { access_token: string };
        setToken(data.access_token);
        setBanner({ type: "success", message: "Autenticado com sucesso." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Falha na autenticação." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiBase]
  );

  const handleLogout = useCallback(() => {
    if (!token) {
      return;
    }
    setToken(null);
    setStrategies([]);
    setSignalsMap({});
    setTelegramStatus(null);
    setChannelConfig(null);
    setAdminProfile(null);
    setBanner({ type: "success", message: "Sessão encerrada." });
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [token]);

const handleCreateStrategy = useCallback(
  async (name: string, channelIdentifier: string) => {
    setActionLoading("create-strategy");
    try {
      await apiFetch<StrategyItem>("/api/strategies", {
        method: "POST",
        body: JSON.stringify({ name, channel_identifier: channelIdentifier, activate: false })
      });
      await fetchStrategies();
      setBanner({ type: "success", message: "Estratégia criada." });
    } catch (error) {
      setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao criar estratégia." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchStrategies]
  );

  const runStrategyCommand = useCallback(
    async (strategyId: number, path: string, successMessage: string) => {
      setActionLoading(`${strategyId}-${path}`);
      try {
        await apiFetch(`/api/strategies/${strategyId}/${path}`, { method: "POST" });
        await fetchStrategies();
        setBanner({ type: "success", message: successMessage });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Falha ao atualizar estratégia." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchStrategies]
  );

  const deleteStrategy = useCallback(
    async (strategyId: number) => {
      setActionLoading(`${strategyId}-delete`);
      try {
        await apiFetch(`/api/strategies/${strategyId}`, { method: "DELETE" });
        setSignalsMap(prev => {
          const clone = { ...prev };
          delete clone[strategyId];
          return clone;
        });
        await fetchStrategies();
        setBanner({ type: "success", message: "Estratégia removida." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao remover estratégia." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchStrategies]
  );

  const sendTelegramCode = useCallback(
    async (phone: string) => {
      setActionLoading("telegram-code");
      try {
        await apiFetch("/api/auth/send-code", {
          method: "POST",
          body: JSON.stringify({ phone })
        });
        await fetchTelegramSuite();
        setBanner({ type: "success", message: "Código enviado." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao enviar código." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchTelegramSuite]
  );

  const verifyTelegramCode = useCallback(
    async (code: string) => {
      setActionLoading("telegram-verify");
      try {
        await apiFetch("/api/auth/verify-code", {
          method: "POST",
          body: JSON.stringify({ code })
        });
        await fetchTelegramSuite();
        setBanner({ type: "success", message: "Sessão autorizada." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro na validação." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchTelegramSuite]
  );

  const logoutTelegramSession = useCallback(async () => {
    setActionLoading("telegram-logout");
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
      await fetchTelegramSuite();
      setBanner({ type: "success", message: "Sessão do Telegram encerrada." });
    } catch (error) {
      setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao encerrar sessão." });
    } finally {
      setActionLoading(null);
    }
  }, [apiFetch, fetchTelegramSuite]);

  const controlCapture = useCallback(
    async (action: "pause" | "resume" | "start" | "stop" | "clear-history") => {
      setActionLoading(`capture-${action}`);
      try {
        await apiFetch(`/api/config/capture/${action}`, { method: "POST" });
        await fetchTelegramSuite();
        if (action === "clear-history") {
          setSignalsMap({});
        }
        setBanner({ type: "success", message: "Estado de captura atualizado." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao atualizar captura." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchTelegramSuite, setSignalsMap]
  );

  const activeStrategy = useMemo(() => strategies.find(item => item.id === selectedStrategyId), [strategies, selectedStrategyId]);
  const activeSignals = selectedStrategyId ? signalsMap[selectedStrategyId] ?? [] : [];
  const captureLoading = actionLoading?.startsWith("capture-") ?? false;

  if (!initialised) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <span className="text-sm uppercase tracking-widest text-slate-400">Carregando...</span>
      </div>
    );
  }

  if (!token) {
    return <LoginView loading={actionLoading === "login"} onLogin={handleLogin} />;
  }

  return (
    <DashboardLayout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      onLogout={handleLogout}
      banner={banner}
    >
      {activeTab === "home" && (
        <HomeTab
          strategies={strategies}
          selectedStrategyId={selectedStrategyId}
          onSelectStrategy={setSelectedStrategyId}
          signals={activeSignals}
          onRefreshSignals={() => (selectedStrategyId ? fetchSignals(selectedStrategyId) : Promise.resolve())}
          loading={actionLoading === "refresh-signals"}
          telegramStatus={telegramStatus}
          captureState={channelConfig?.capture_state ?? telegramStatus?.capture}
        />
      )}
      {activeTab === "strategies" && (
        <StrategiesTab
          strategies={strategies}
          actionLoading={actionLoading}
          onCreate={handleCreateStrategy}
          onDelete={deleteStrategy}
          onCommand={runStrategyCommand}
          onRefresh={fetchStrategies}
          channelOptions={availableChannels}
          onRefreshChannels={fetchAvailableChannels}
          channelsLoading={channelsLoading}
        />
      )}
      {activeTab === "telegram" && (
        <TelegramTab
          status={telegramStatus}
          actionLoading={actionLoading}
          onRefresh={fetchTelegramSuite}
          onSendCode={sendTelegramCode}
          onVerifyCode={verifyTelegramCode}
          onLogoutTelegram={logoutTelegramSession}
          onControlCapture={controlCapture}
          captureState={telegramStatus?.capture ?? null}
          captureLoading={captureLoading}
        />
      )}
      {activeTab === "signals" && (
        <SignalsTab
          strategies={strategies}
          selectedStrategyId={selectedStrategyId}
          onSelectStrategy={setSelectedStrategyId}
          signals={activeSignals}
          onRefreshSignals={() => (selectedStrategyId ? fetchSignals(selectedStrategyId) : Promise.resolve())}
          loading={actionLoading === "refresh-signals"}
        />
      )}
    </DashboardLayout>
  );
}

type LoginViewProps = {
  loading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
};

function LoginView({ loading, onLogin }: LoginViewProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onLogin(email, password);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <div className="w-full max-w-md space-y-6 rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl shadow-black/40">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Momentum Admin</h1>
          <p className="text-sm text-slate-400">Acesse com seu e-mail administrativo para gerenciar o painel.</p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">E-mail</label>
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              type="email"
              value={email}
              onChange={event => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Senha</label>
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              type="password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          >
            {loading ? "Autenticando..." : "Entrar"}
          </button>
        </form>
        <p className="text-center text-xs text-slate-500">
          Certifique-se de configurar as variáveis ADMIN_EMAIL, ADMIN_PASSWORD e ADMIN_TOKEN_SECRET no servidor antes de publicar.
        </p>
      </div>
    </div>
  );
}

type DashboardLayoutProps = {
  activeTab: TabKey;
  setActiveTab: (tab: TabKey) => void;
  onLogout: () => void;
  banner: Banner | null;
  children: ReactNode;
};

function DashboardLayout({ activeTab, setActiveTab, onLogout, banner, children }: DashboardLayoutProps) {
  const navMap = NAV_ITEMS.reduce<Partial<Record<TabKey, NavItem>>>((acc, item) => {
    acc[item.id] = item;
    return acc;
  }, {});
  const desktopSections = NAV_SECTIONS.map(section => ({
    title: section.title,
    items: section.items
      .map(id => navMap[id])
      .filter((item): item is NavItem => {
        if (!item) {
          return false;
        }
        return !item.mobileOnly;
      })
  })).filter(section => section.items.length > 0);
  const mobileNavItems = NAV_ITEMS;

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-72 border-r border-slate-900 bg-slate-950/85 px-5 py-8 md:flex">
        <div className="flex h-full w-full flex-col">
          <div className="mb-8">
            <h2 className="text-xl font-semibold uppercase tracking-[0.5em] text-blue-300">Momentum</h2>
            <p className="mt-2 text-xs text-slate-500">Plataforma de monitoramento</p>
          </div>
          <nav className="flex-1 space-y-6">
            {desktopSections.map(section => (
              <div key={section.title}>
                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">{section.title}</p>
                <div className="mt-3 space-y-2">
                  {section.items.map(item => (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition ${
                        activeTab === item.id
                          ? "bg-blue-600/20 text-blue-200 ring-1 ring-inset ring-blue-500/40"
                          : "text-slate-300 hover:bg-slate-900/60"
                      }`}
                    >
                      <span
                        className={`rounded-lg border p-2 text-sm ${
                          activeTab === item.id ? "border-blue-500/40 bg-blue-500/10" : "border-slate-800 bg-slate-900/60"
                        }`}
                      >
                        {item.icon}
                      </span>
                      <span>
                        <span className="block text-sm font-semibold">{item.label}</span>
                        {item.description && <span className="block text-xs text-slate-500">{item.description}</span>}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </nav>
          <button
            onClick={onLogout}
            className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-red-500/60 hover:text-red-300"
          >
            Sair
          </button>
        </div>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-900 bg-slate-950/80 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between">
            <span className="text-base font-semibold uppercase tracking-[0.6em] text-blue-300">Momentum</span>
            <button
              onClick={onLogout}
              className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-red-500/60 hover:text-red-300"
            >
              Sair
            </button>
          </div>
        </header>
        {banner && (
          <div className={`border-b px-4 py-3 text-sm font-medium ${banner.type === "success" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : "border-red-500/40 bg-red-500/10 text-red-200"}`}>
            {banner.message}
          </div>
        )}
        <main className="flex-1 overflow-y-auto px-4 pb-28 pt-6 md:px-8 md:pb-10 md:pt-8">
          {children}
        </main>
        <nav className="pointer-events-none fixed bottom-4 left-0 right-0 z-30 md:hidden">
          <div className="pointer-events-auto mx-auto w-full max-w-md px-4">
            <ul className="flex items-center justify-between rounded-full border border-slate-800 bg-slate-950/80 px-4 py-3 shadow-[0_20px_40px_rgba(0,0,0,0.45)] backdrop-blur">
              {mobileNavItems.map(item => {
                const isActive = activeTab === item.id;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => setActiveTab(item.id)}
                      className={`flex flex-col items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold transition ${
                        isActive ? "text-blue-300" : "text-slate-400"
                      }`}
                    >
                      <span
                        className={`flex h-10 w-10 items-center justify-center rounded-full border text-base ${
                          isActive ? "border-blue-500/40 bg-blue-500/15 text-blue-200" : "border-slate-800 bg-slate-900/70"
                        }`}
                      >
                        {item.icon}
                      </span>
                      {item.label}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </nav>
      </div>
    </div>
  );
}

type HomeTabProps = {
  strategies: StrategyItem[];
  selectedStrategyId: number | null;
  onSelectStrategy: (id: number | null) => void;
  signals: StrategySignal[];
  onRefreshSignals: () => Promise<void>;
  loading: boolean;
  telegramStatus: TelegramStatus | null;
  captureState?: TelegramCaptureState | null;
};

function HomeTab({ strategies, selectedStrategyId, onSelectStrategy, signals, onRefreshSignals, loading, telegramStatus, captureState }: HomeTabProps) {
  const totalStrategies = strategies.length;
  const activeCount = strategies.filter(item => item.status === "active").length;
  const pausedCount = strategies.filter(item => item.status === "paused").length;
  const selectedStrategy = strategies.find(item => item.id === selectedStrategyId) ?? null;
  const sanitisedSignals = useMemo(() => sanitizeSignals(signals), [signals]);
  const HOME_SIGNAL_LIMIT = 3;
  const limitedSignals = sanitisedSignals.slice(0, HOME_SIGNAL_LIMIT);

  const handleSelect = (value: string) => {
    if (!value) {
      onSelectStrategy(null);
      return;
    }
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
      onSelectStrategy(parsed);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-4 md:grid-cols-4">
        <SummaryCard title="Estratégias" subtitle="Total configuradas" value={totalStrategies.toString()} accent="blue" />
        <SummaryCard title="Ativas" subtitle="Capturando sinais" value={activeCount.toString()} accent="emerald" />
        <SummaryCard title="Pausadas" subtitle="Aguardando retomada" value={pausedCount.toString()} accent="amber" />
        <SummaryCard
          title="Captura"
          subtitle="Status do Telegram"
          value={captureState?.active ? (captureState.paused ? "Pausada" : "Ativa") : "Desligada"}
          accent={captureState?.active ? (captureState.paused ? "amber" : "emerald") : "slate"}
        />
      </section>

      <section className="hidden flex-1 flex-col rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30 md:flex">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Sinais interpretados</h3>
            <p className="text-sm text-slate-500">Filtre por estratégia para acompanhar as últimas entradas estruturadas pela IA.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedStrategyId ?? ""}
              onChange={event => handleSelect(event.target.value)}
              className="appearance-none rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            >
              <option value="" disabled>
                Selecione uma estratégia
              </option>
              {strategies.map(item => (
                <option key={item.id} value={item.id}>
                  {item.name} {item.status !== "active" ? `(${item.status})` : ""}
                </option>
              ))}
            </select>
            <button
              onClick={onRefreshSignals}
              disabled={!selectedStrategyId || loading}
              className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
            >
              Atualizar
            </button>
          </div>
        </div>
        <div className="mt-4 flex-1 overflow-hidden rounded-xl border border-slate-900 bg-slate-900/40">
          {!selectedStrategy ? (
            <div className="flex h-full items-center justify-center px-6 py-10 text-center text-slate-400">
              Escolha uma estratégia para visualizar os sinais mais recentes.
            </div>
          ) : sanitisedSignals.length === 0 ? (
            <div className="flex h-full items-center justify-center px-6 py-10 text-center text-slate-400">
              Nenhum sinal processado nas últimas 24h para {selectedStrategy.name}.
            </div>
          ) : (
            <div className="flex h-full max-h-[380px] flex-col gap-3 overflow-y-auto px-4 py-4 pr-2">
              {limitedSignals.map((signal, index) => (
                <SignalCard key={signal.id} signal={signal} sequence={sanitisedSignals.length - index} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 text-sm text-slate-400 md:hidden">
        <h3 className="text-base font-semibold text-slate-100">Sinais interpretados</h3>
        <p className="mt-2">Acesse a aba “Sinais” na barra inferior para acompanhar os sinais processados em detalhes.</p>
      </section>

    </div>
  );
}

type SignalsTabProps = {
  strategies: StrategyItem[];
  selectedStrategyId: number | null;
  onSelectStrategy: (id: number | null) => void;
  signals: StrategySignal[];
  onRefreshSignals: () => Promise<void>;
  loading: boolean;
};

function SignalsTab({ strategies, selectedStrategyId, onSelectStrategy, signals, onRefreshSignals, loading }: SignalsTabProps) {
  const selectedStrategy = strategies.find(item => item.id === selectedStrategyId) ?? null;
  const sanitisedSignals = useMemo(() => sanitizeSignals(signals), [signals]);

  const handleSelect = (value: string) => {
    if (!value) {
      onSelectStrategy(null);
      return;
    }
    const parsed = Number(value);
    if (!Number.isNaN(parsed)) {
      onSelectStrategy(parsed);
    }
  };

  return (
    <div className="flex min-h-full flex-col gap-4 md:hidden">
      <header className="space-y-2 rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <h2 className="text-lg font-semibold text-slate-50">Sinais interpretados</h2>
        <p className="text-sm text-slate-500">Selecione uma estratégia para acompanhar as entradas geradas pela IA.</p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedStrategyId ?? ""}
            onChange={event => handleSelect(event.target.value)}
            className="flex-1 appearance-none rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
          >
            <option value="" disabled>
              Selecione uma estratégia
            </option>
            {strategies.map(item => (
              <option key={item.id} value={item.id}>
                {item.name} {item.status !== "active" ? `(${item.status})` : ""}
              </option>
            ))}
          </select>
          <button
            onClick={onRefreshSignals}
            disabled={!selectedStrategyId || loading}
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
          >
            Atualizar
          </button>
        </div>
      </header>

      {!selectedStrategy ? (
        <div className="flex flex-1 items-center justify-center rounded-2xl border border-slate-900 bg-slate-950/70 px-6 py-10 text-center text-slate-400">
          Escolha uma estratégia acima para visualizar os sinais mais recentes.
        </div>
      ) : sanitisedSignals.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-2xl border border-slate-900 bg-slate-950/70 px-6 py-10 text-center text-slate-400">
          Nenhum sinal processado nas últimas 24h para {selectedStrategy.name}.
        </div>
      ) : (
        <div className="flex flex-1 max-h-[70vh] flex-col gap-3 overflow-y-auto rounded-2xl border border-slate-900 bg-slate-950/70 px-3 py-4 shadow-lg shadow-black/30">
          {sanitisedSignals.map((signal, index) => (
            <SignalCard key={signal.id} signal={signal} sequence={sanitisedSignals.length - index} />
          ))}
        </div>
      )}
    </div>
  );
}

type SummaryCardProps = {
  title: string;
  subtitle: string;
  value: string;
  accent: "blue" | "emerald" | "amber" | "slate";
};

function SummaryCard({ title, subtitle, value, accent }: SummaryCardProps) {
  const accentClass = {
    blue: "border-blue-500/40 bg-blue-500/10 text-blue-100",
    emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-100",
    slate: "border-slate-700 bg-slate-900/40 text-slate-200"
  }[accent];

  return (
    <div className={`rounded-2xl border p-5 shadow-lg shadow-black/40 ${accentClass}`}>
      <p className="text-xs uppercase tracking-widest text-slate-300/80">{subtitle}</p>
      <h4 className="mt-2 text-3xl font-semibold">{value}</h4>
      <p className="text-sm text-slate-200/80">{title}</p>
    </div>
  );
}

type SignalCardProps = {
  signal: StrategySignal;
  sequence: number;
};

const sanitizeSignals = (signals: StrategySignal[]): StrategySignal[] => {
  return [...signals]
    .filter(signal => {
      if (!signal || signal.status !== "parsed" || signal.error) {
        return false;
      }
      const payload = signal.parsed_payload ?? {};
      const symbol = String(payload?.symbol ?? payload?.pair ?? "").trim().toUpperCase();
      const action = String(payload?.action ?? "").trim().toUpperCase();
      const entry = normaliseEntry(payload?.entry ?? payload?.price ?? "NA");
      const hasValidAction = action === "BUY" || action === "SELL";
      const hasValidSymbol = Boolean(symbol) && symbol !== "NA";
      const hasValidEntry = entry !== "NA";
      return hasValidAction && hasValidSymbol && hasValidEntry;
    })
    .sort((a, b) => {
      const aTime = new Date(a.processed_at).getTime();
      const bTime = new Date(b.processed_at).getTime();
      return Number.isNaN(bTime) || Number.isNaN(aTime) ? 0 : bTime - aTime;
    });
};

function SignalCard({ signal, sequence }: SignalCardProps) {
  const payload = signal.parsed_payload ?? {};
  const symbol = String(payload.symbol ?? payload.pair ?? "NA").toUpperCase();
  const action = String(payload.action ?? "NA").toUpperCase();
  const entry = normaliseEntry(payload.entry ?? payload.price ?? "NA");
  const maxEntry = normaliseEntry(payload.max_entry ?? "NA");
  const takeProfit = normaliseArray(payload.take_profit ?? payload.tp ?? []);
  const stopLoss = normaliseEntry(payload.stop_loss ?? payload.sl ?? "NA");
  const tpDisplay = takeProfit.length ? takeProfit.join(" · ") : "NA";
  const showMaxEntry = maxEntry !== "NA" && maxEntry !== entry;

  const actionStyles =
    action === "BUY"
      ? "bg-blue-500/15 text-blue-200 border-blue-500/40"
      : "bg-red-500/15 text-red-200 border-red-500/40";

  const stopLossIcon = "🛑";

  return (
    <div className="rounded-2xl border border-slate-900 bg-slate-900/70 p-5 shadow-lg shadow-black/35">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Sinal #{sequence.toString().padStart(2, "0")}</p>
          <div className="flex flex-wrap items-center gap-3">
            <h4 className="text-2xl font-semibold uppercase tracking-tight text-slate-50">{symbol}</h4>
            <span className={`rounded-full border px-4 py-1 text-2xl font-semibold uppercase tracking-wide ${actionStyles}`}>{action}</span>
          </div>
          <p className="text-xs text-slate-500">Processado em {formatDateTime(signal.processed_at)}</p>
        </div>
      </header>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-3 text-sm text-slate-100">
          <p className="text-[11px] uppercase tracking-widest text-slate-500">Entrada</p>
          <p className="mt-1 font-semibold text-slate-100">{entry}</p>
        </div>
        {showMaxEntry && (
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-3 text-sm text-slate-100">
            <p className="text-[11px] uppercase tracking-widest text-slate-500">Entrada máx.</p>
            <p className="mt-1 font-semibold text-slate-100">{maxEntry}</p>
          </div>
        )}
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-3 text-sm text-slate-100">
          <p className="text-[11px] uppercase tracking-widest text-slate-500">Take Profit</p>
          <p className="mt-1 font-semibold text-slate-100">{tpDisplay}</p>
        </div>
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-3 text-sm text-slate-100">
          <div className="flex items-center gap-2">
            <span className="text-lg">{stopLossIcon}</span>
            <div>
              <p className="text-[11px] uppercase tracking-widest text-slate-500">Stop Loss</p>
              <p className="mt-1 font-semibold text-slate-100">{stopLoss}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

type StrategiesTabProps = {
  strategies: StrategyItem[];
  actionLoading: string | null;
  onCreate: (name: string, channelIdentifier: string) => Promise<void>;
  onDelete: (strategyId: number) => Promise<void>;
  onCommand: (strategyId: number, path: string, successMessage: string) => Promise<void>;
  onRefresh: () => Promise<void>;
  channelOptions: ChannelOption[];
  onRefreshChannels: () => Promise<void>;
  channelsLoading: boolean;
};

function StrategiesTab({
  strategies,
  actionLoading,
  onCreate,
  onDelete,
  onCommand,
  onRefresh,
  channelOptions,
  onRefreshChannels,
  channelsLoading
}: StrategiesTabProps) {
  const [name, setName] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("");

  const STRATEGY_LIMIT = 4;
  const reachedLimit = strategies.length >= STRATEGY_LIMIT;

  const statusAppearance: Record<StrategyItem["status"], { label: string; badge: string }> = {
    active: {
      label: "Ativa",
      badge: "border border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
    },
    paused: {
      label: "Pausada",
      badge: "border border-amber-500/40 bg-amber-500/10 text-amber-200"
    },
    inactive: {
      label: "Inativa",
      badge: "border border-slate-700 bg-slate-900/70 text-slate-300"
    }
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedChannel || reachedLimit) {
      return;
    }
    await onCreate(name.trim(), selectedChannel);
    setName("");
    setSelectedChannel("");
  };

  const canSubmit = Boolean(name.trim()) && Boolean(selectedChannel) && channelOptions.length > 0;
  const creationDisabled = reachedLimit || actionLoading === "create-strategy" || !canSubmit;
  const limitedStrategies = strategies.slice(0, STRATEGY_LIMIT);

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="grid gap-6 lg:grid-cols-[1.1fr_minmax(0,1fr)]">
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-50">Nova estratégia</h3>
              <p className="text-sm text-slate-500">Organize seus sinais nomeando a estratégia e vinculando um canal monitorado.</p>
            </div>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>1. Defina um nome curto e fácil de identificar no painel.</li>
              <li>2. Selecione um canal disponível na sua conta do Telegram.</li>
              <li>3. Ative a estratégia quando estiver pronto para receber sinais.</li>
            </ul>
            <div className={`rounded-xl border px-4 py-3 text-xs font-semibold uppercase tracking-widest ${reachedLimit ? "border-amber-500/40 bg-amber-500/10 text-amber-200" : "border-slate-800 bg-slate-900/60 text-slate-300"}`}>
              Limite de {STRATEGY_LIMIT} estratégias simultâneas
            </div>
          </div>

          <form className="space-y-4 rounded-2xl border border-slate-900 bg-slate-950/60 p-5" onSubmit={handleCreate}>
            <div>
              <label className="text-xs uppercase tracking-widest text-slate-400">Nome da estratégia</label>
              <input
                value={name}
                onChange={event => setName(event.target.value)}
                disabled={reachedLimit}
                className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
                placeholder="Ex.: GBP Scalper"
                required
              />
            </div>

            <div>
              <label className="text-xs uppercase tracking-widest text-slate-400">Canal monitorado</label>
              <div className="mt-1 flex gap-2">
                <select
                  value={selectedChannel}
                  onChange={event => setSelectedChannel(event.target.value)}
                  className="flex-1 appearance-none rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
                  required
                  disabled={channelOptions.length === 0 || reachedLimit}
                >
                  <option value="" disabled>
                    Selecione um canal
                  </option>
                  {channelOptions.map(option => (
                    <option key={option.id} value={option.id}>
                      {option.title}
                      {option.username ? ` (@${option.username})` : ""}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={onRefreshChannels}
                  disabled={channelsLoading}
                  className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
                >
                  {channelsLoading ? "..." : "Atualizar"}
                </button>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {channelOptions.length
                  ? "Selecione um canal listado abaixo. Caso não apareça, sincronize novamente com o Telegram."
                  : "Nenhum canal disponível. Conecte-se ao Telegram e atualize a lista."}
              </p>
            </div>

            <button
              type="submit"
              disabled={creationDisabled}
              className="w-full rounded-lg border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-xs font-semibold text-blue-200 transition hover:border-blue-400 hover:text-blue-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
            >
              {reachedLimit ? "Limite atingido" : actionLoading === "create-strategy" ? "Criando..." : "Adicionar estratégia"}
            </button>
            {reachedLimit && <p className="text-center text-xs text-slate-500">Remova uma estratégia existente para liberar espaço.</p>}
          </form>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Estratégias configuradas</h3>
            <p className="text-sm text-slate-500">Revise rapidamente status e histórico antes de acionar os comandos.</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300">
            Atualizar lista
          </button>
        </div>
        {limitedStrategies.length === 0 ? (
          <div className="rounded-xl border border-slate-900 bg-slate-900/40 p-6 text-slate-400">
            Nenhuma estratégia cadastrada. Utilize o formulário acima para criar a primeira.
          </div>
        ) : (
          <div className="max-h-[420px] space-y-4 overflow-y-auto pr-1">
            {limitedStrategies.map(strategy => {
              const appearance = statusAppearance[strategy.status];
              const lastSignalText = strategy.last_signal ? formatDateTime(strategy.last_signal.processed_at) : null;
              const lastSignalDisplay = lastSignalText ? lastSignalText.replace(" ", ", ") : null;
              const pauseAction = strategy.status === "paused" ? "resume" : "pause";
              const pauseLabel = strategy.status === "paused" ? "Retomar" : "Pausar";
              const pauseMessage = strategy.status === "paused" ? "Estratégia retomada." : "Estratégia pausada.";
              const pauseLoading = actionLoading === `${strategy.id}-pause` || actionLoading === `${strategy.id}-resume`;
              const deleteLoading = actionLoading === `${strategy.id}-delete`;
              const canActivate = strategy.status === "inactive";
              const activateDisabled = !canActivate || actionLoading === `${strategy.id}-activate`;

              return (
                <div key={strategy.id} className="rounded-2xl border border-slate-900 bg-slate-900/50 p-5 shadow-lg shadow-black/30">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <h4 className="text-xl font-semibold text-slate-50">{strategy.name}</h4>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${appearance.badge}`}>{appearance.label}</span>
                      </div>
                      <p className="text-sm text-slate-400">{strategy.channel_title ?? strategy.channel_identifier}</p>
                      <p className="text-sm text-slate-500">{lastSignalDisplay ? `Último sinal em ${lastSignalDisplay}` : "Sem sinais recentes"}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      onClick={() => onCommand(strategy.id, "activate", "Estratégia ativada.")}
                      disabled={activateDisabled}
                      className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:border-emerald-400 hover:text-emerald-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
                    >
                      Ativar
                    </button>
                    <button
                      onClick={() => onCommand(strategy.id, pauseAction, pauseMessage)}
                      disabled={strategy.status === "inactive" || pauseLoading}
                      className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-200 transition hover:border-amber-400 hover:text-amber-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
                    >
                      {pauseLoading ? "..." : pauseLabel}
                    </button>
                    <button
                      onClick={() => onDelete(strategy.id)}
                      disabled={deleteLoading}
                      className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-200 transition hover:border-red-400 hover:text-red-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
                    >
                      {deleteLoading ? "Removendo..." : "Remover"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

type TelegramTabProps = {
  status: TelegramStatus | null;
  actionLoading: string | null;
  onRefresh: () => Promise<void>;
  onSendCode: (phone: string) => Promise<void>;
  onVerifyCode: (code: string) => Promise<void>;
  onLogoutTelegram: () => Promise<void>;
  onControlCapture: (action: "start" | "stop" | "pause" | "resume" | "clear-history") => Promise<void>;
  captureState: TelegramCaptureState | null;
  captureLoading: boolean;
};

function TelegramTab({ status, actionLoading, onRefresh, onSendCode, onVerifyCode, onLogoutTelegram, onControlCapture, captureState, captureLoading }: TelegramTabProps) {
  const [phoneInput, setPhoneInput] = useState("");
  const [codeInput, setCodeInput] = useState("");
  const [codeReady, setCodeReady] = useState(false);

  const isAuthorized = Boolean(status?.authorized);
  const isSendingCode = actionLoading === "telegram-code";
  const isVerifying = actionLoading === "telegram-verify";
  const isLoggingOut = actionLoading === "telegram-logout";

  useEffect(() => {
    const inferredPhone = status?.pending_phone || status?.phone_number || "";
    setPhoneInput(inferredPhone);
    setCodeReady(Boolean(status?.pending_phone) && !status?.authorized);
    if (status?.authorized) {
      setCodeInput("");
    }
  }, [status?.pending_phone, status?.phone_number, status?.authorized]);

  const handleSendCode = async () => {
    const trimmed = phoneInput.trim();
    if (!trimmed || isSendingCode) {
      return;
    }
    try {
      await onSendCode(trimmed);
      setCodeReady(true);
    } catch {
      /* handled upstream */
    }
  };

  const handleVerifyCode = async () => {
    const trimmed = codeInput.trim();
    if (!trimmed || isVerifying || !codeReady) {
      return;
    }
    try {
      await onVerifyCode(trimmed);
      setCodeReady(false);
      setCodeInput("");
    } catch {
      /* handled upstream */
    }
  };

  const captureStatusLabel = captureState?.active
    ? captureState.paused
      ? "Captura pausada"
      : "Captura ativa"
    : "Captura desligada";
  const startDisabled = captureLoading || Boolean(captureState?.active && !captureState.paused);
  const stopDisabled = captureLoading || !captureState?.active;
  const clearDisabled = captureLoading;

  const summaryCards = [
    {
      title: status?.connected ? "Sessão sincronizada" : "Aguardando conexão",
      subtitle: "Conexão",
      value: status?.connected ? "Online" : "Offline",
      accent: status?.connected ? ("emerald" as const) : ("slate" as const)
    },
    {
      title: status?.authorized ? status?.account?.display_name ?? "Conta validada" : "Informe o código recebido",
      subtitle: "Autorização",
      value: status?.authorized ? "Autorizada" : "Pendente",
      accent: status?.authorized ? ("emerald" as const) : ("amber" as const)
    },
    {
      title: captureState?.active
        ? captureState.paused
          ? "Listener pausado"
          : "Recebendo mensagens"
        : "Listener inativo",
      subtitle: "Captura",
      value: captureStatusLabel,
      accent: captureState?.active ? (captureState.paused ? ("amber" as const) : ("emerald" as const)) : ("slate" as const)
    }
  ];

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-3">
        {summaryCards.map(card => (
          <SummaryCard key={card.subtitle} title={card.title} subtitle={card.subtitle} value={card.value} accent={card.accent} />
        ))}
      </section>

      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Sessão do Telegram</h3>
            <p className="text-sm text-slate-500">Informe o telefone da conta e valide o código recebido pelo Telegram.</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300">
            Atualizar status
          </button>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <label className="text-xs uppercase tracking-widest text-slate-400">Número de telefone</label>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                type="tel"
                value={phoneInput}
                onChange={event => setPhoneInput(event.target.value)}
                disabled={isAuthorized || isSendingCode}
                className="w-full flex-1 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
              />
              <button
                type="button"
                onClick={handleSendCode}
                disabled={isAuthorized || isSendingCode || !phoneInput.trim()}
                className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
              >
                {isSendingCode ? "Enviando..." : "Enviar"}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">Utilize o formato internacional (ex.: +55 11 99999-0000).</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <label className="text-xs uppercase tracking-widest text-slate-400">Código recebido</label>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                value={codeInput}
                onChange={event => setCodeInput(event.target.value)}
                disabled={!codeReady || isAuthorized || isVerifying}
                className="w-full flex-1 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
              />
              <button
                type="button"
                onClick={handleVerifyCode}
                disabled={!codeReady || !codeInput.trim() || isAuthorized || isVerifying}
                className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
              >
                {isVerifying ? "Validando..." : "Confirmar"}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">Somente após “Enviar” o campo será liberado para preenchimento.</p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <button
            type="button"
            onClick={onLogoutTelegram}
            disabled={!isAuthorized || isLoggingOut}
            className="h-14 w-full rounded-lg border border-red-500/40 bg-red-500/10 text-sm font-semibold text-red-100 transition hover:border-red-400 hover:text-red-50 disabled:border-slate-900 disabled:bg-slate-900/50 disabled:text-slate-500"
          >
            {isLoggingOut ? "Encerrando sessão..." : "Encerrar sessão"}
          </button>
        </div>

      </section>

      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="space-y-2">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Monitoramento global</h3>
            <p className="text-xs text-slate-500">Inicie, finalize ou limpe o listener responsável por receber as mensagens dos canais selecionados.</p>
          </div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Status atual: {captureStatusLabel}</p>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onControlCapture("start")}
            disabled={startDisabled}
            className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:border-emerald-400 hover:text-emerald-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
          >
            Iniciar
          </button>
          <button
            type="button"
            onClick={() => onControlCapture("stop")}
            disabled={stopDisabled}
            className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-200 transition hover:border-red-400 hover:text-red-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
          >
            Parar
          </button>
          <button
            type="button"
            onClick={() => onControlCapture("clear-history")}
            disabled={clearDisabled}
            className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-200 transition hover:border-blue-400 hover:text-blue-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
          >
            Limpar histórico
          </button>
        </div>
      </section>
    </div>
  );
}

function normaliseArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map(item => String(item).trim())
      .filter(item => item.length > 0);
  }
  if (typeof value === "string" && value.trim().length > 0) {
    return [value.trim()];
  }
  return [];
}

function normaliseEntry(value: unknown): string {
  if (typeof value === "number") {
    return value.toFixed(5).replace(/0+$/, "").replace(/\.$/, "");
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return "NA";
    }
    if (trimmed.toLowerCase() === "market") {
      return "MARKET";
    }
    return trimmed;
  }
  return "NA";
}
