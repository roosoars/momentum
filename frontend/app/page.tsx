"use client";

import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";

type TabKey = "home" | "strategies" | "telegram" | "admin";

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
  description: string;
  icon: JSX.Element;
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

const UserIcon = () => (
  <svg aria-hidden className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 20.75a8 8 0 0 1 16 0" strokeLinecap="round" strokeLinejoin="round" />
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
    id: "admin",
    label: "Admin",
    description: "Conta e segurança",
    icon: <UserIcon />
  }
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
  const [adminProfile, setAdminProfile] = useState<AdminProfile | null>(null);
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
  }, [apiFetch]);

  const fetchSignals = useCallback(
    async (strategyId: number) => {
      const data = await apiFetch<{ items: StrategySignal[]; count: number }>(
        `/api/strategies/${strategyId}/signals?limit=100`
      );
      setSignalsMap(prev => ({ ...prev, [strategyId]: data.items }));
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
      setBanner({
        type: "error",
        message: error instanceof Error ? error.message : "Erro ao listar canais disponíveis."
      });
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

  const handleLogout = useCallback(async () => {
    if (!token) {
      return;
    }
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      // ignore logout errors, still clear local state
    } finally {
      setToken(null);
      setStrategies([]);
      setSignalsMap({});
      setTelegramStatus(null);
      setChannelConfig(null);
      setAdminProfile(null);
      setBanner({ type: "success", message: "Sessão encerrada." });
    }
  }, [apiFetch, token]);

  const handleCreateStrategy = useCallback(
    async (name: string, channelIdentifier: string, activate: boolean) => {
      setActionLoading("create-strategy");
      try {
        await apiFetch<StrategyItem>("/api/strategies", {
          method: "POST",
          body: JSON.stringify({ name, channel_identifier: channelIdentifier, activate })
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

  const updateStrategyName = useCallback(
    async (strategyId: number, name: string) => {
      setActionLoading(`${strategyId}-rename`);
      try {
        await apiFetch(`/api/strategies/${strategyId}`, {
          method: "PATCH",
          body: JSON.stringify({ name })
        });
        await fetchStrategies();
        setBanner({ type: "success", message: "Estratégia atualizada." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao renomear." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchStrategies]
  );

  const assignStrategyChannel = useCallback(
    async (strategyId: number, channelIdentifier: string) => {
      setActionLoading(`${strategyId}-channel`);
      try {
        await apiFetch(`/api/strategies/${strategyId}/channel`, {
          method: "POST",
          body: JSON.stringify({ channel_identifier: channelIdentifier })
        });
        await fetchStrategies();
        setBanner({ type: "success", message: "Canal atualizado." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao vincular canal." });
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

  const provideTelegramPassword = useCallback(
    async (password: string) => {
      setActionLoading("telegram-password");
      try {
        await apiFetch("/api/auth/password", {
          method: "POST",
          body: JSON.stringify({ password })
        });
        await fetchTelegramSuite();
        setBanner({ type: "success", message: "Senha confirmada." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao validar senha." });
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
        setBanner({ type: "success", message: "Estado de captura atualizado." });
      } catch (error) {
        setBanner({ type: "error", message: error instanceof Error ? error.message : "Erro ao atualizar captura." });
      } finally {
        setActionLoading(null);
      }
    },
    [apiFetch, fetchTelegramSuite]
  );

  const activeStrategy = useMemo(() => strategies.find(item => item.id === selectedStrategyId), [strategies, selectedStrategyId]);
  const activeSignals = selectedStrategyId ? signalsMap[selectedStrategyId] ?? [] : [];

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
      adminProfile={adminProfile}
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
          onRename={updateStrategyName}
          onAssignChannel={assignStrategyChannel}
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
          config={channelConfig}
          actionLoading={actionLoading}
          onRefresh={fetchTelegramSuite}
          onSendCode={sendTelegramCode}
          onVerifyCode={verifyTelegramCode}
          onProvidePassword={provideTelegramPassword}
          onLogoutTelegram={logoutTelegramSession}
          onControlCapture={controlCapture}
        />
      )}
      {activeTab === "admin" && <AdminTab profile={adminProfile} />}
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
  adminProfile: AdminProfile | null;
  children: ReactNode;
};

function DashboardLayout({ activeTab, setActiveTab, onLogout, banner, adminProfile, children }: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-72 flex-col border-r border-slate-900 bg-slate-950/80 px-4 py-6 md:flex">
        <div className="mb-8 space-y-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-blue-400">Momentum</span>
          <h2 className="text-xl font-semibold text-slate-50">Painel Administrativo</h2>
          <p className="text-xs text-slate-500">Controle estratégias de sinal, integrações e captura do Telegram.</p>
        </div>
        <nav className="flex flex-1 flex-col gap-2">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center justify-start gap-3 rounded-xl px-3 py-3 text-left transition ${
                activeTab === item.id
                  ? "bg-blue-600/20 text-blue-200 ring-1 ring-inset ring-blue-500/40"
                  : "hover:bg-slate-900/60 text-slate-300"
              }`}
            >
              <span className={`rounded-lg border ${activeTab === item.id ? "border-blue-500/40 bg-blue-500/10" : "border-slate-800 bg-slate-900/60"} p-2 text-sm`}>{item.icon}</span>
              <span>
                <span className="block text-sm font-semibold">{item.label}</span>
                <span className="block text-xs text-slate-500">{item.description}</span>
              </span>
            </button>
          ))}
        </nav>
        <div className="mt-6 rounded-xl border border-slate-900 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{adminProfile?.email ?? "Administrador"}</span>
            <button onClick={onLogout} className="rounded-lg border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-300 transition hover:border-red-500/60 hover:text-red-300">
              Sair
            </button>
          </div>
        </div>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-900 bg-slate-950/80 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs uppercase tracking-widest text-blue-400">Momentum</span>
              <h1 className="text-lg font-semibold text-slate-50">{NAV_ITEMS.find(item => item.id === activeTab)?.label}</h1>
            </div>
            <button onClick={onLogout} className="rounded-lg border border-slate-800 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-red-500/60 hover:text-red-300">
              Sair
            </button>
          </div>
        </header>
        {banner && (
          <div className={`border-b px-4 py-3 text-sm font-medium ${banner.type === "success" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : "border-red-500/40 bg-red-500/10 text-red-200"}`}>
            {banner.message}
          </div>
        )}
        <main className="flex-1 overflow-y-auto px-4 pb-20 pt-6 md:px-8 md:pb-10 md:pt-8">
          {children}
        </main>
        <nav className="fixed bottom-0 left-0 right-0 border-t border-slate-900 bg-slate-950/90 backdrop-blur md:hidden">
          <ul className="flex items-stretch justify-around">
            {NAV_ITEMS.map(item => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`flex h-14 flex-col items-center justify-center gap-1 px-4 text-xs transition ${
                    activeTab === item.id ? "text-blue-300" : "text-slate-400"
                  }`}
                >
                  <span className={`rounded-md border p-1 ${activeTab === item.id ? "border-blue-500/40 bg-blue-500/10" : "border-slate-800 bg-slate-900/60"}`}>{item.icon}</span>
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
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

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section className="flex flex-col rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
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
            ) : signals.length === 0 ? (
              <div className="flex h-full items-center justify-center px-6 py-10 text-center text-slate-400">
                Nenhum sinal processado nas últimas 24h para {selectedStrategy.name}.
              </div>
            ) : (
              <div className="max-h-[460px] space-y-3 overflow-y-auto px-4 py-4 pr-2">
                {signals.map(signal => (
                  <SignalCard key={signal.id} signal={signal} strategyName={selectedStrategy.name} />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
          <h3 className="text-lg font-semibold text-slate-50">Sessão do Telegram</h3>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <StatusBadge label="Conexão" value={telegramStatus?.connected ? "Online" : "Offline"} variant={telegramStatus?.connected ? "emerald" : "slate"} />
            <StatusBadge label="Autorização" value={telegramStatus?.authorized ? "Autorizado" : "Pendente"} variant={telegramStatus?.authorized ? "emerald" : "amber"} />
            <StatusBadge label="Telefone" value={telegramStatus?.phone_number ?? telegramStatus?.pending_phone ?? "Não informado"} variant="slate" />
            <StatusBadge
              label="Canais ativos"
              value={(telegramStatus?.channels ?? []).map(item => item.title ?? item.id).join(", ") || "Nenhum"}
              variant="slate"
            />
          </div>
        </section>
      </div>
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

type StatusBadgeProps = {
  label: string;
  value: string;
  variant: "emerald" | "amber" | "slate";
};

function StatusBadge({ label, value, variant }: StatusBadgeProps) {
  const styles = {
    emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-100",
    slate: "border-slate-800 bg-slate-900/50 text-slate-200"
  }[variant];
  return (
    <div className={`rounded-xl border p-4 ${styles}`}>
      <p className="text-xs uppercase tracking-widest text-slate-300/80">{label}</p>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  );
}

type SignalCardProps = {
  signal: StrategySignal;
  strategyName: string;
};

function SignalCard({ signal, strategyName }: SignalCardProps) {
  const payload = signal.parsed_payload ?? {};
  const symbol = String(payload.symbol ?? payload.pair ?? "NA").toUpperCase();
  const action = String(payload.action ?? "NA").toUpperCase();
  const entry = normaliseEntry(payload.entry ?? payload.price ?? "NA");
  const takeProfit = normaliseArray(payload.take_profit ?? payload.tp ?? []);
  const stopLoss = normaliseEntry(payload.stop_loss ?? payload.sl ?? "NA");
  const tpDisplay = takeProfit.length ? takeProfit.join(" / ") : "NA";
  const headline = `PAIR: ${symbol} | ACTION: ${action} | ENTRY: ${entry} | TP: ${tpDisplay} | SL: ${stopLoss} — PROVIDER: ${strategyName || "N/A"}`;

  return (
    <div className="rounded-xl border border-slate-900 bg-slate-900/60 p-4 shadow-md shadow-black/25">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <p className="text-sm font-semibold leading-relaxed text-slate-50">{headline}</p>
        <span className="text-xs font-medium text-slate-500 sm:text-right">Processed {formatDateTime(signal.processed_at)}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
        <span className={`rounded-md border px-2 py-1 font-semibold ${signal.status === "parsed" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : signal.status === "failed" ? "border-red-500/40 bg-red-500/10 text-red-200" : "border-slate-700 bg-slate-900/70 text-slate-200"}`}>
          STATUS: {signal.status.toUpperCase()}
        </span>
        <span className="rounded-md border border-slate-700 bg-slate-900/70 px-2 py-1">
          Message #{signal.telegram_message_id}
        </span>
      </div>
      {signal.error && (
        <p className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {signal.error}
        </p>
      )}
      {signal.raw_message && (
        <details className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2 text-xs text-slate-400">
          <summary className="cursor-pointer text-slate-300">Mensagem original</summary>
          <p className="mt-2 whitespace-pre-line text-slate-400">{signal.raw_message}</p>
        </details>
      )}
    </div>
  );
}

type StrategiesTabProps = {
  strategies: StrategyItem[];
  actionLoading: string | null;
  onCreate: (name: string, channelIdentifier: string, activate: boolean) => Promise<void>;
  onRename: (strategyId: number, name: string) => Promise<void>;
  onAssignChannel: (strategyId: number, channelIdentifier: string) => Promise<void>;
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
  onRename,
  onAssignChannel,
  onDelete,
  onCommand,
  onRefresh,
  channelOptions,
  onRefreshChannels,
  channelsLoading
}: StrategiesTabProps) {
  const [name, setName] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("");
  const [activate, setActivate] = useState(true);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedChannel) {
      return;
    }
    await onCreate(name, selectedChannel, activate);
    setName("");
    setSelectedChannel("");
  };

  const variantForStatus = (status: StrategyItem["status"]) => {
    if (status === "active") return "text-emerald-300";
    if (status === "paused") return "text-amber-300";
    return "text-slate-400";
  };

  const canSubmit = Boolean(name.trim()) && Boolean(selectedChannel) && channelOptions.length > 0;

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <h3 className="text-lg font-semibold text-slate-50">Nova estratégia</h3>
        <p className="text-sm text-slate-500">Defina um nome amigável e selecione um canal do Telegram para monitorar.</p>
        <form className="mt-4 grid gap-4 md:grid-cols-4" onSubmit={handleCreate}>
          <div className="md:col-span-2">
            <label className="text-xs uppercase tracking-widest text-slate-400">Nome da estratégia</label>
            <input
              value={name}
              onChange={event => setName(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              required
            />
          </div>
          <div className="md:col-span-2">
            <label className="text-xs uppercase tracking-widest text-slate-400">Canal monitorado</label>
            <div className="mt-1 flex gap-2">
              <select
                value={selectedChannel}
                onChange={event => setSelectedChannel(event.target.value)}
                className="flex-1 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm font-semibold text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
                required
                disabled={channelOptions.length === 0}
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
                ? "Lista com os canais públicos e privados acessíveis pela sua conta do Telegram."
                : "Nenhum canal listado ainda. Atualize após autenticar a sessão no Telegram."}
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <input type="checkbox" checked={activate} onChange={event => setActivate(event.target.checked)} className="rounded border-slate-700 bg-slate-900 text-blue-500 focus:ring-blue-500" />
            Iniciar captura imediatamente (máx. 5 estratégias ativas)
          </label>
          <div className="md:col-span-4 flex justify-end">
            <button
              type="submit"
              disabled={actionLoading === "create-strategy" || !canSubmit}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              {actionLoading === "create-strategy" ? "Criando..." : "Adicionar estratégia"}
            </button>
          </div>
        </form>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Estratégias configuradas</h3>
            <p className="text-sm text-slate-500">Gerencie status, canais e ações de cada estratégia.</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300">
            Atualizar lista
          </button>
        </div>
        {strategies.length === 0 ? (
          <div className="rounded-xl border border-slate-900 bg-slate-900/40 p-6 text-slate-400">
            Nenhuma estratégia cadastrada. Utilize o formulário acima para criar a primeira.
          </div>
        ) : (
          <div className="space-y-4">
            {strategies.map(strategy => (
              <div key={strategy.id} className="rounded-xl border border-slate-900 bg-slate-900/40 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <h4 className="text-lg font-semibold text-slate-50">{strategy.name}</h4>
                      <span className={`text-xs font-semibold uppercase tracking-wide ${variantForStatus(strategy.status)}`}>{strategy.status}</span>
                    </div>
                    <p className="text-xs text-slate-500">{strategy.channel_title ?? strategy.channel_identifier}</p>
                    <p className="text-[11px] text-slate-600">Criada em {formatDateTime(strategy.created_at)}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => onCommand(strategy.id, "activate", "Estratégia ativada.")}
                      disabled={actionLoading === `${strategy.id}-activate`}
                      className="rounded-lg border border-emerald-500/40 px-3 py-1 text-xs font-semibold text-emerald-200 transition hover:border-emerald-400 hover:text-emerald-100"
                    >
                      Ativar
                    </button>
                    <button
                      onClick={() => onCommand(strategy.id, "pause", "Estratégia pausada.")}
                      disabled={actionLoading === `${strategy.id}-pause`}
                      className="rounded-lg border border-amber-500/40 px-3 py-1 text-xs font-semibold text-amber-200 transition hover:border-amber-400 hover:text-amber-100"
                    >
                      Pausar
                    </button>
                    <button
                      onClick={() => onCommand(strategy.id, "resume", "Estratégia retomada.")}
                      disabled={actionLoading === `${strategy.id}-resume`}
                      className="rounded-lg border border-blue-500/40 px-3 py-1 text-xs font-semibold text-blue-200 transition hover:border-blue-400 hover:text-blue-100"
                    >
                      Retomar
                    </button>
                    <button
                      onClick={() => onCommand(strategy.id, "deactivate", "Estratégia desativada.")}
                      disabled={actionLoading === `${strategy.id}-deactivate`}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
                    >
                      Desativar
                    </button>
                    <button
                      onClick={() => onDelete(strategy.id)}
                      disabled={actionLoading === `${strategy.id}-delete`}
                      className="rounded-lg border border-red-500/40 px-3 py-1 text-xs font-semibold text-red-200 transition hover:border-red-400 hover:text-red-100"
                    >
                      Remover
                    </button>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <InlineForm
                    label="Alterar nome"
                    placeholder="Novo nome"
                    submitLabel="Renomear"
                    loading={actionLoading === `${strategy.id}-rename`}
                    onSubmit={value => onRename(strategy.id, value)}
                  />
                  <InlineForm
                    label="Alterar canal"
                    placeholder="@novo_canal"
                    submitLabel="Atualizar"
                    loading={actionLoading === `${strategy.id}-channel`}
                    onSubmit={value => onAssignChannel(strategy.id, value)}
                  />
                  {strategy.last_signal && (
                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                      Último sinal às <span className="text-slate-200">{formatDateTime(strategy.last_signal.processed_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

type InlineFormProps = {
  label: string;
  placeholder: string;
  submitLabel: string;
  loading: boolean;
  onSubmit: (value: string) => Promise<void>;
};

function InlineForm({ label, placeholder, submitLabel, loading, onSubmit }: InlineFormProps) {
  const [value, setValue] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!value.trim()) {
      return;
    }
    await onSubmit(value.trim());
    setValue("");
  };

  return (
    <form className="flex flex-col gap-2" onSubmit={handleSubmit}>
      <label className="text-xs uppercase tracking-widest text-slate-400">{label}</label>
      <div className="flex gap-2">
        <input
          value={value}
          onChange={event => setValue(event.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
        >
          {loading ? "..." : submitLabel}
        </button>
      </div>
    </form>
  );
}

type TelegramTabProps = {
  status: TelegramStatus | null;
  config: ChannelConfig | null;
  actionLoading: string | null;
  onRefresh: () => Promise<void>;
  onSendCode: (phone: string) => Promise<void>;
  onVerifyCode: (code: string) => Promise<void>;
  onProvidePassword: (password: string) => Promise<void>;
  onLogoutTelegram: () => Promise<void>;
  onControlCapture: (action: "pause" | "resume" | "start" | "stop" | "clear-history") => Promise<void>;
};

function TelegramTab({ status, config, actionLoading, onRefresh, onSendCode, onVerifyCode, onProvidePassword, onLogoutTelegram, onControlCapture }: TelegramTabProps) {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-50">Sessão do Telegram</h3>
            <p className="text-sm text-slate-500">Autentique-se para permitir que o serviço monitore os canais configurados.</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300">
            Atualizar status
          </button>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <InlineForm
            label="Enviar código de login"
            placeholder="+55 11 99999-0000"
            submitLabel="Enviar"
            loading={actionLoading === "telegram-code"}
            onSubmit={value => onSendCode(value)}
          />
          <InlineForm
            label="Validar código"
            placeholder="12345"
            submitLabel="Confirmar"
            loading={actionLoading === "telegram-verify"}
            onSubmit={value => onVerifyCode(value)}
          />
          <InlineForm
            label="Senha em duas etapas"
            placeholder="Senha"
            submitLabel="Validar"
            loading={actionLoading === "telegram-password"}
            onSubmit={value => onProvidePassword(value)}
          />
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-widest text-slate-400">Encerrar sessão</label>
            <button
              onClick={onLogoutTelegram}
              className="rounded-lg border border-red-500/40 px-3 py-2 text-xs font-semibold text-red-200 transition hover:border-red-400 hover:text-red-100"
              disabled={actionLoading === "telegram-logout"}
            >
              {actionLoading === "telegram-logout" ? "Encerrando..." : "Sair do Telegram"}
            </button>
          </div>
        </div>
        {status && (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatusBadge label="Conectado" value={status.connected ? "Sim" : "Não"} variant={status.connected ? "emerald" : "slate"} />
            <StatusBadge label="Autorizado" value={status.authorized ? "Sim" : "Não"} variant={status.authorized ? "emerald" : "amber"} />
            <StatusBadge label="Telefone" value={status.phone_number ?? status.pending_phone ?? "Não informado"} variant="slate" />
            <StatusBadge label="Captura" value={status.capture?.active ? (status.capture.paused ? "Pausada" : "Ativa") : "Inativa"} variant={status.capture?.active ? (status.capture.paused ? "amber" : "emerald") : "slate"} />
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
        <h3 className="text-lg font-semibold text-slate-50">Controles de captura</h3>
        <p className="text-sm text-slate-500">Gerencie a ingestão de mensagens em tempo real. As estratégias configuradas continuarão vinculadas aos canais definidos.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <CaptureButton label="Iniciar" action="start" loading={actionLoading} onAction={onControlCapture} />
          <CaptureButton label="Pausar" action="pause" loading={actionLoading} onAction={onControlCapture} />
          <CaptureButton label="Retomar" action="resume" loading={actionLoading} onAction={onControlCapture} />
          <CaptureButton label="Parar" action="stop" loading={actionLoading} onAction={onControlCapture} />
          <CaptureButton label="Limpar histórico" action="clear-history" loading={actionLoading} onAction={onControlCapture} />
        </div>
        <div className="mt-6 rounded-xl border border-slate-900 bg-slate-900/40 p-4 text-sm text-slate-400">
          <p>
            Canais ativos: {(config?.channels ?? []).map(item => item.title ?? item.id).join(", ") || "Nenhum"}. A gestão principal dos canais deve ser realizada nas estratégias.
          </p>
        </div>
      </section>
    </div>
  );
}

type CaptureButtonProps = {
  label: string;
  action: "pause" | "resume" | "start" | "stop" | "clear-history";
  loading: string | null;
  onAction: (action: "pause" | "resume" | "start" | "stop" | "clear-history") => Promise<void>;
};

function CaptureButton({ label, action, loading, onAction }: CaptureButtonProps) {
  const busy = loading === `capture-${action}`;
  return (
    <button
      onClick={() => onAction(action)}
      disabled={busy}
      className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-blue-500/50 hover:text-blue-300 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
    >
      {busy ? "Aguarde..." : label}
    </button>
  );
}

type AdminTabProps = {
  profile: AdminProfile | null;
};

function AdminTab({ profile }: AdminTabProps) {
  return (
    <section className="rounded-2xl border border-slate-900 bg-slate-950/70 p-6 shadow-lg shadow-black/30">
      <h3 className="text-lg font-semibold text-slate-50">Perfil administrativo</h3>
      {profile ? (
        <div className="mt-4 space-y-2 text-sm text-slate-400">
          <p>
            <span className="text-slate-500">E-mail:</span> {profile.email}
          </p>
          <p>
            <span className="text-slate-500">Criado em:</span> {formatDateTime(profile.created_at)}
          </p>
          <p>
            <span className="text-slate-500">Última atualização:</span> {formatDateTime(profile.updated_at)}
          </p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-400">Não foi possível carregar os dados do administrador.</p>
      )}
      <p className="mt-6 text-xs text-slate-500">
        Para prover acesso a novos administradores, cadastre-os diretamente no banco ou exponha um fluxo controlado fora deste painel.
      </p>
    </section>
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
