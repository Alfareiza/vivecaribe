import SignInForm from "@/components/auth/SignInForm";
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
      fallback={
        <div className="flex flex-1 items-center justify-center text-sm text-gray-500">
          Cargando…
        </div>
      }
    >
      <SignInGate>
        <SignInForm />
      </SignInGate>
    </Suspense>
  );
}
