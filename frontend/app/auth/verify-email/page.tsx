"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { API_URL } from "@/lib/config";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      return;
    }

    (async () => {
      try {
        const response = await fetch(`${API_URL}/api/users/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (!response.ok) throw new Error("Verification failed");

        setStatus("success");
        setTimeout(() => router.push("/auth/login"), 3000);
      } catch {
        setStatus("error");
      }
    })();
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
      <div className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-center">
        {status === "loading" && (
          <>
            <h2 className="text-xl font-semibold text-slate-50">Verificando email...</h2>
            <p className="text-sm text-slate-400">Aguarde um momento</p>
          </>
        )}

        {status === "success" && (
          <>
            <h2 className="text-xl font-semibold text-emerald-200">Email verificado!</h2>
            <p className="text-sm text-emerald-300">
              Sua conta foi ativada. Redirecionando para login...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <h2 className="text-xl font-semibold text-red-200">Erro na verificação</h2>
            <p className="text-sm text-red-300">
              Token inválido ou expirado.
            </p>
            <Link
              href="/auth/login"
              className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              Ir para login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="text-slate-400">Carregando...</p>
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
