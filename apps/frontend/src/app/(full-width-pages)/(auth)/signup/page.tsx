import SignUpForm from "@/components/auth/SignUpForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Next.js SignUp Page | Football tours and travel",
  description: "This is Next.js SignUp Page | Bienvenido a vive caribe, football tours and travel around Colombia",
  // other metadata
};

export default function SignUp() {
  return <SignUpForm />;
}
