"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { UserRole } from "../../types/api";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, role } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  if (isLoading) {
    return (
      <div
        className="flex flex-col items-center justify-center"
        style={{ minHeight: "80vh", gap: "var(--space-4)" }}
        aria-live="polite"
        aria-busy="true"
      >
        <div className="spinner spinner-large" />
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Authenticating secure session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return (
      <div className="container" style={{ padding: "var(--space-12) var(--space-6)" }}>
        <div className="card" style={{ borderColor: "var(--status-emergency-border)", maxWidth: "560px", margin: "0 auto" }}>
          <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-4)" }}>
            <span style={{ fontSize: "1.5rem" }}>🚫</span>
            <h3 style={{ color: "var(--status-emergency)" }}>Access Restricted</h3>
          </div>
          <p style={{ marginBottom: "var(--space-6)" }}>
            This section is restricted to authorized roles (<strong>{allowedRoles.join(", ")}</strong>). Your active session role is <strong>{role}</strong>.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => router.push("/dashboard")}
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
