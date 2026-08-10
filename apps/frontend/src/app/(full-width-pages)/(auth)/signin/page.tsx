import SignInForm from "@/components/auth/SignInForm";
import PageLoading from "@/components/ui/loading/PageLoading";
import { SignInGate } from "@/context/AuthContext";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Iniciar sesión | ViveCaribe",
  description: "Acceso al panel de operaciones ViveCaribe",
};

export default function SignIn() {
  return (
    <Suspense
      fallback={<PageLoading label="Cargando…" className="flex-1" />}
    >
      <SignInGate>
        <SignInForm />
      </SignInGate>
    </Suspense>
  );
}
