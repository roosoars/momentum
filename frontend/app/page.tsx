"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

type AuthStatus = {
  connected: boolean;
  authorized: boolean;
  channel_id: string | null;
  channel_title: string | null;
  pending_phone: string | null;
  phone_number: string | null;
  password_required: boolean;
};

type ConfigResponse = {
  channel_id: string | null;
  channel_title: string | null;
  last_input: string | null;
  status: AuthStatus;
  capture_state?: CaptureState;
};

type MessageItem = {
  telegram_id: number;
  channel_id: string;
  sender: string | null;
  message: string | null;
  created_at: string;
};

type Banner = {
  type: "success" | "error";
  message: string;
};

type ChannelOption = {
  id: string;
  title: string;
  username?: string | null;
  type?: string | null;
};

type CaptureState = {
  active: boolean;
  paused: boolean;
};

const resolveApiBaseOnServer = () => {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return base.replace(/\/$/, "");
};

const resolveWsBaseOnServer = () => {
  const base =
    process.env.NEXT_PUBLIC_API_WS_URL ??
    (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
      /^http(s?)/i,
      "ws$1"
    );
  return base.replace(/\/$/, "");
};

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium"
  }).format(new Date(value));

const statusColor = (state: boolean) =>
  state ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-slate-800 text-slate-400 border border-slate-700";

const SubmitButton = ({
  children,
  loading,
  disabled
}: {
  children: ReactNode;
  loading: boolean;
  disabled?: boolean;
}) => (
  <button
    type="submit"
    disabled={disabled || loading}
    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand/30 transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
  >
    {loading && (
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
    )}
    {children}
  </button>
);

export default function DashboardPage() {
  const [apiBase] = useState(() => {
    if (typeof window !== "undefined") {
      return window.location.origin.replace(/\/$/, "");
    }
    return resolveApiBaseOnServer();
  });

  const [wsBase] = useState(() => {
    if (typeof window !== "undefined") {
      const protocol = window.location.protocol.startsWith("https") ? "wss:" : "ws:";
      return `${protocol}//${window.location.host}`.replace(/\/$/, "");
    }
    return resolveWsBaseOnServer();
  });

  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [channelInput, setChannelInput] = useState("");
  const [resetHistory, setResetHistory] = useState(true);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [banner, setBanner] = useState<Banner | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [channelOptions, setChannelOptions] = useState<ChannelOption[]>([]);
  const [captureState, setCaptureState] = useState<CaptureState | null>(null);

  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const channelTitle = useMemo(
    () => config?.channel_title ?? authStatus?.channel_title ?? null,
    [config?.channel_title, authStatus?.channel_title]
  );

  const currentChannelId = useMemo(
    () => config?.channel_id ?? authStatus?.channel_id ?? null,
    [config?.channel_id, authStatus?.channel_id]
  );

  const isCaptureActive = captureState?.active ?? false;
  const isCapturePaused = captureState?.paused ?? false;
  const captureStatusLabel = !isCaptureActive
    ? "Captura parada"
    : isCapturePaused
      ? "Captura pausada"
      : "Captura em andamento";

  const postJSON = async (path: string, body?: unknown) => {
    const response = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    });

    if (response.status === 204) {
      return null;
    }

    const raw = await response.text();
    let data: any = null;
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = null;
      }
    }

    if (!response.ok) {
      const detail =
        (data && (data.detail ?? data.message)) ||
        `Erro ${response.status}`;
      throw new Error(detail);
    }

    return data;
  };

  const refreshStatus = async (silent = false) => {
    try {
      const response = await fetch(`${apiBase}/api/auth/status`);
      if (!response.ok) {
        throw new Error();
      }
      const data: AuthStatus = await response.json();
      setAuthStatus(data);
      if (!phone) {
        setPhone(data.pending_phone ?? data.phone_number ?? "");
      }
    } catch (error) {
      console.error("auth status", error);
      if (!silent) {
        setBanner({
          type: "error",
          message: "Não foi possível atualizar o status de autenticação."
        });
      }
    }
  };

  const refreshConfig = async (silent = false) => {
    try {
      const response = await fetch(`${apiBase}/api/config`);
      if (!response.ok) {
        throw new Error();
      }
      const data: ConfigResponse = await response.json();
      setConfig(data);
      if (!channelInput) {
        setChannelInput(data.last_input ?? "");
      }
      if (data.capture_state) {
        setCaptureState(data.capture_state);
      }
    } catch (error) {
      console.error("config", error);
      if (!silent) {
        setBanner({
          type: "error",
          message: "Falha ao carregar configurações atuais."
        });
      }
    }
  };

  useEffect(() => {
    void refreshStatus(true);
    void refreshConfig(true);
  }, [apiBase]);

  useEffect(() => {
    const socket = new WebSocket(`${wsBase}/ws/messages`);
    wsRef.current = socket;

    const handleMessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "history" && Array.isArray(payload.data)) {
          const ordered = [...payload.data].sort(
            (a: MessageItem, b: MessageItem) =>
              new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );
          setMessages(ordered);
        }
        if (payload.type === "message" && payload.data) {
          const incoming: MessageItem = payload.data;
          setMessages(prev => {
            if (prev.some(item => item.telegram_id === incoming.telegram_id)) {
              return prev;
            }
            const updated = [...prev, incoming].sort(
              (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
            );
            return updated;
          });
        }
      } catch (error) {
        console.error("WebSocket parse", error);
      }
    };

    const handleOpen = () => {
      socket.send(JSON.stringify({ type: "ping" }));
    };

    const handleError = () => {
      setBanner({
        type: "error",
        message: "Conexão em tempo real interrompida. Tentando novamente..."
      });
    };

    socket.addEventListener("open", handleOpen);
    socket.addEventListener("message", handleMessage);
    socket.addEventListener("error", handleError);

    const pingInterval = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);

    return () => {
      window.clearInterval(pingInterval);
      socket.removeEventListener("open", handleOpen);
      socket.removeEventListener("message", handleMessage);
      socket.removeEventListener("error", handleError);
      socket.close(1000, "page navigation");
    };
  }, [wsBase]);

  useEffect(() => {
    if (!scrollerRef.current) {
      return;
    }
    scrollerRef.current.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [messages]);

  const handleSendCode = async (event: FormEvent) => {
    event.preventDefault();
    setLoadingKey("send-code");
    setBanner(null);
    try {
      await postJSON("/api/auth/send-code", { phone });
      setBanner({ type: "success", message: "Código enviado para o Telegram." });
      await refreshStatus(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro ao enviar código.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const handleVerifyCode = async (event: FormEvent) => {
    event.preventDefault();
    setLoadingKey("verify-code");
    setBanner(null);
    try {
      const result = await postJSON("/api/auth/verify-code", { code });
      if (result?.password_required) {
        setBanner({
          type: "error",
          message: "Senha 2FA necessária. Informe abaixo."
        });
      } else {
        setCode("");
        setBanner({
          type: "success",
          message: "Autenticação concluída com sucesso."
        });
      }
      await refreshStatus(true);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erro ao validar código.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const handlePassword = async (event: FormEvent) => {
    event.preventDefault();
    setLoadingKey("password");
    setBanner(null);
    try {
      await postJSON("/api/auth/password", { password });
      setPassword("");
      setBanner({
        type: "success",
        message: "Senha confirmada. Sessão autorizada."
      });
      await refreshStatus(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro ao validar senha.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const handleLogout = async () => {
    setLoadingKey("logout");
    setBanner(null);
    try {
      await postJSON("/api/auth/logout");
      setBanner({ type: "success", message: "Sessão encerrada." });
      setCode("");
      setPassword("");
      await refreshStatus(true);
      await refreshConfig(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro ao sair.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const handleChannel = async (event: FormEvent) => {
    event.preventDefault();
    setLoadingKey("channel");
    setBanner(null);
    try {
      const result = await postJSON("/api/config/channel", {
        channel_id: channelInput.trim(),
        reset_history: resetHistory
      });
      updateCaptureState(result?.capture_state ?? null);
      setBanner({
        type: "success",
        message: "Canal atualizado com sucesso."
      });
      await refreshConfig(true);
      await refreshStatus(true);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erro ao atualizar canal.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const loadChannelOptions = async () => {
    setLoadingKey("load-channels");
    setBanner(null);
    try {
      const response = await fetch(`${apiBase}/api/config/channels/available`);
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Falha ao listar canais disponíveis.");
      }
      const data = await response.json();
      setChannelOptions(data.items ?? []);
      if (!channelInput && Array.isArray(data.items) && data.items.length > 0) {
        setChannelInput(data.items[0].id);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erro ao buscar canais disponíveis.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const updateCaptureState = (state?: CaptureState | null) => {
    if (state) {
      setCaptureState(state);
    }
  };

  const handleCaptureAction = async (
    path: string,
    successMessage: string,
    key: string,
    onSuccess?: () => void
  ) => {
    setLoadingKey(key);
    setBanner(null);
    try {
      const data = await postJSON(path);
      updateCaptureState(data?.capture_state ?? data?.state ?? null);
      setBanner({ type: "success", message: successMessage });
      if (onSuccess) {
        onSuccess();
      }
      await refreshConfig(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ação não concluída.";
      setBanner({ type: "error", message });
    } finally {
      setLoadingKey(null);
    }
  };

  const handlePauseCapture = () => handleCaptureAction("/api/config/capture/pause", "Captura pausada.", "pause");
  const handleResumeCapture = () => handleCaptureAction("/api/config/capture/resume", "Captura retomada.", "resume");
  const handleStopCapture = () => handleCaptureAction("/api/config/capture/stop", "Captura interrompida.", "stop");
  const handleStartCapture = () => handleCaptureAction("/api/config/capture/start", "Captura iniciada.", "start");
  const handleClearHistory = () =>
    handleCaptureAction("/api/config/capture/clear-history", "Histórico limpo.", "clear", () => {
      setMessages([]);
    });

  return (
    <div className="min-h-screen pb-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 pt-12 lg:px-6">
        <header className="flex flex-col gap-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-600/40 bg-blue-600/20 px-4 py-1 text-sm text-blue-200 shadow-lg shadow-blue-900/40 w-max">
            Telegram Channel Collector
          </div>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            Painel administrativo completo
          </h1>
          <p className="max-w-3xl text-slate-300">
            Configure a autenticação da sua conta do Telegram, selecione qual canal monitorar
            e acompanhe as mensagens em tempo real em um layout responsivo e moderno.
          </p>
        </header>

        {banner && (
          <div
            className={`rounded-2xl border px-4 py-3 text-sm font-medium ${
              banner.type === "success"
                ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-200"
                : "border-rose-500/40 bg-rose-500/15 text-rose-200"
            }`}
          >
            {banner.message}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[380px,1fr]">
          <div className="flex flex-col gap-6">
            <section className="card">
              <header className="flex flex-col gap-2">
                <h2 className="card-title">Autenticação Telegram</h2>
                <p className="text-sm text-slate-400">
                  Informe o número do Telegram, valide o código recebido e finalize com a senha de dois fatores se necessário.
                </p>
              </header>

              <div className="mt-4 grid gap-2 text-sm">
                <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${statusColor(authStatus?.connected ?? false)}`}>
                  <span className="h-2 w-2 rounded-full bg-current" />
                  Conexão {authStatus?.connected ? "estabelecida" : "offline"}
                </div>
                <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${statusColor(authStatus?.authorized ?? false)}`}>
                  <span className="h-2 w-2 rounded-full bg-current" />
                  {authStatus?.authorized ? "Sessão autorizada" : "Autenticação pendente"}
                </div>
                {authStatus?.phone_number && (
                  <p className="text-xs text-slate-400">
                    Conta ativa:{" "}
                    <span className="font-semibold text-slate-200">
                      {authStatus.phone_number}
                    </span>
                  </p>
                )}
              </div>

              <form onSubmit={handleSendCode} className="mt-6 grid gap-3">
                <label className="text-sm font-medium text-slate-200" htmlFor="phone">
                  Número do Telegram (com DDI)
                </label>
                <input
                  id="phone"
                  type="tel"
                  value={phone}
                  onChange={event => setPhone(event.target.value)}
                  placeholder="+5511999999999"
                  className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-black/60 focus:border-blue-500 focus:outline-none"
                />
                <SubmitButton loading={loadingKey === "send-code"}>
                  Enviar código via Telegram
                </SubmitButton>
              </form>

              <form onSubmit={handleVerifyCode} className="mt-6 grid gap-3">
                <label className="text-sm font-medium text-slate-200" htmlFor="code">
                  Código recebido (SMS / Telegram)
                </label>
                <input
                  id="code"
                  type="text"
                  value={code}
                  onChange={event => setCode(event.target.value)}
                  placeholder="12345"
                  className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-black/60 focus:border-blue-500 focus:outline-none"
                />
                <SubmitButton loading={loadingKey === "verify-code"}>
                  Validar código
                </SubmitButton>
              </form>

              <form onSubmit={handlePassword} className="mt-6 grid gap-3">
                <label className="text-sm font-medium text-slate-200" htmlFor="password">
                  Senha 2FA (se habilitada)
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  placeholder="Senha do Telegram"
                  className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-black/60 focus:border-blue-500 focus:outline-none"
                />
                <SubmitButton loading={loadingKey === "password"}>
                  Confirmar senha
                </SubmitButton>
              </form>

              <button
                type="button"
                onClick={handleLogout}
                className="mt-6 inline-flex w-full items-center justify-center rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-rose-500 hover:text-rose-200"
                disabled={loadingKey === "logout"}
              >
                Encerrar sessão
              </button>
            </section>

            <section className="card">
              <header className="flex flex-col gap-2">
                <h2 className="card-title">Canal monitorado</h2>
                <p className="text-sm text-slate-400">
                  Configure o `@username` ou ID numérico (ex: -1001234567890) do canal desejado. As mensagens entram automaticamente.
                </p>
              </header>
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm text-slate-300">
                <p className="font-medium text-slate-200">Canal atual</p>
                <p className="text-slate-300">
                  {channelTitle ? (
                    <span className="font-semibold text-blue-200">{channelTitle}</span>
                  ) : (
                    "Nenhum canal configurado."
                  )}
                </p>
                {currentChannelId && (
                  <p className="text-xs text-slate-500">ID: {currentChannelId}</p>
                )}
              </div>

              <form onSubmit={handleChannel} className="mt-6 grid gap-3">
                <label className="text-sm font-medium text-slate-200" htmlFor="channel">
                  Canal (ID ou @username)
                </label>
                <input
                  id="channel"
                  type="text"
                  value={channelInput}
                  onChange={event => setChannelInput(event.target.value)}
                  placeholder="@canal ou -1001234567890"
                  className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 shadow-inner shadow-black/60 focus:border-blue-500 focus:outline-none"
                  required
                />

                <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-sm">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-slate-200">Canais disponíveis</p>
                    <button
                      type="button"
                      onClick={loadChannelOptions}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-medium text-slate-200 transition hover:border-blue-500 hover:text-blue-300"
                      disabled={loadingKey === "load-channels"}
                    >
                      {loadingKey === "load-channels" ? "Carregando..." : "Atualizar lista"}
                    </button>
                  </div>
                  {channelOptions.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      Clique em "Atualizar lista" para carregar os canais pertencentes à conta autenticada.
                    </p>
                  ) : (
                    <>
                      <select
                        value={channelInput}
                        onChange={event => setChannelInput(event.target.value)}
                        className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
                      >
                        {channelOptions.map(option => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                            {option.username ? ` (@${option.username})` : ""}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-slate-500">
                        A seleção acima preenche o campo automaticamente. Você pode ajustar manualmente se necessário.
                      </p>
                    </>
                  )}
                </div>

                <div className="grid gap-2 rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-sm">
                  <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-xs font-semibold text-slate-200">
                    <span
                      className={`h-2 w-2 rounded-full ${!isCaptureActive ? "bg-rose-400" : isCapturePaused ? "bg-amber-300" : "bg-emerald-400"}`}
                    />
                    {captureStatusLabel}
                  </div>
                  <p className="text-xs text-slate-500">
                    Controle a ingestão de mensagens sem perder a configuração atual do canal.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleStartCapture}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-emerald-500 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loadingKey === "start" || isCaptureActive}
                    >
                      Iniciar
                    </button>
                    <button
                      type="button"
                      onClick={handlePauseCapture}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-amber-500 hover:text-amber-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loadingKey === "pause" || !isCaptureActive || isCapturePaused}
                    >
                      Pausar
                    </button>
                    <button
                      type="button"
                      onClick={handleResumeCapture}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-emerald-500 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loadingKey === "resume" || !isCapturePaused || !isCaptureActive}
                    >
                      Continuar
                    </button>
                    <button
                      type="button"
                      onClick={handleStopCapture}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-rose-500 hover:text-rose-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loadingKey === "stop" || !isCaptureActive}
                    >
                      Parar
                    </button>
                    <button
                      type="button"
                      onClick={handleClearHistory}
                      className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-sky-500 hover:text-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={loadingKey === "clear"}
                    >
                      Apagar histórico
                    </button>
                  </div>
                </div>

                <label className="inline-flex items-center gap-3 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={resetHistory}
                    onChange={event => setResetHistory(event.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-blue-500 focus:ring-blue-500"
                  />
                  Limpar histórico salvo antes de sincronizar novamente
                </label>

                <SubmitButton
                  loading={loadingKey === "channel"}
                  disabled={!authStatus?.authorized}
                >
                  Salvar canal e sincronizar
                </SubmitButton>
              </form>
            </section>
          </div>

          <section className="card h-full">
            <header className="flex flex-col gap-1">
              <h2 className="card-title">Mensagens em tempo real</h2>
              <p className="text-sm text-slate-400">
                Novas mensagens aparecem instantaneamente após a captura.
              </p>
            </header>

            <div
              ref={scrollerRef}
              className="mt-4 flex h-[520px] flex-col gap-3 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/50 p-4"
            >
              {messages.length === 0 && (
                <div className="mt-12 flex flex-col items-center gap-2 text-center text-sm text-slate-500">
                  <span className="text-xl">💬</span>
                  Nenhuma mensagem capturada ainda.
                </div>
              )}

              {messages.map(item => (
                <article
                  key={item.telegram_id}
                  className="flex flex-col gap-1 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm shadow-inner shadow-black/40"
                >
                  <header className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-medium text-slate-200">
                      {item.sender ?? "Desconhecido"}
                    </span>
                    <time dateTime={item.created_at}>{formatDateTime(item.created_at)}</time>
                  </header>
                  <p className="text-slate-100">
                    {item.message?.trim() || <i className="text-slate-500">[conteúdo sem texto]</i>}
                  </p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
