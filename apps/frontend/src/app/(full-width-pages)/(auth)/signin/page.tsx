import SignInForm from "@/components/auth/SignInForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Next.js SignIn Page | Football tours and travel",
  description: "This is Next.js Signin Page | Bienvenido a vive caribe, football tours and travel around Colombia",
};

export default function SignIn() {
  return <SignInForm />;
}
