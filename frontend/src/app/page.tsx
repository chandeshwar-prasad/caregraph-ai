"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace("/dashboard");
      } else {
        router.replace("/login");
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{ minHeight: "100vh", gap: "var(--space-4)" }}
    >
      <div className="spinner spinner-large" />
      <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
        Loading CareGraph AI...
      </p>
    </div>
  );
}
