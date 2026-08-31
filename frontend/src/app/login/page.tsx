"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { apiClient, ApiClientError } from "../../lib/api-client";
import { UserRole } from "../../types/api";

function LoginFormContent() {
  const { login, quickLogin, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/dashboard";

  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("patient");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(redirectUrl);
    }
  }, [isAuthenticated, isLoading, router, redirectUrl]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage("Please enter both username and password.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await login(username.trim(), password);
      router.replace(redirectUrl);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Authentication failed. Please verify your credentials.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage("Please fill in all registration fields.");
      return;
    }
    if (password.length < 6) {
      setErrorMessage("Password must be at least 6 characters long.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.register({
        username: username.trim(),
        password,
        role,
      });
      setSuccessMessage("Account registered successfully. Signing you in...");
      // Immediately log in after successful registration
      await login(username.trim(), password);
      router.replace(redirectUrl);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Registration failed. Username may already exist.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (targetRole: UserRole) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await quickLogin(targetRole);
      router.replace(redirectUrl);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || err.message);
      } else {
        setErrorMessage("Quick login failed. Ensure the CareGraph API backend is running.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="spinner spinner-large" />
      </div>
    );
  }

  return (
    <div className="auth-container">
      <main className="auth-card" role="main">
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
          <div style={{ fontSize: "2.4rem", marginBottom: "var(--space-2)" }}>🧬</div>
          <h1 style={{ fontSize: "var(--font-size-2xl)", color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
            CareGraph AI
          </h1>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
            Multi-Agent Healthcare Navigation & Care Coordination
          </p>
        </div>

        {/* Quick Login Presets */}
        <div className="quick-login-card" aria-label="Development Quick Login Presets">
          <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
            <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--brand-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              ⚡ Demo Quick Login Presets
            </span>
            <span className="badge badge-info" style={{ fontSize: "0.6rem" }}>
              Sandbox
            </span>
          </div>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", marginBottom: "var(--space-3)" }}>
            Instant evaluation authentication using pre-seeded synthetic credentials:
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-2)" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleQuickLogin("patient")}
              disabled={isSubmitting}
              style={{ fontSize: "var(--font-size-xs)", padding: "0.5rem" }}
            >
              🔑 Patient Demo
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleQuickLogin("admin")}
              disabled={isSubmitting}
              style={{ fontSize: "var(--font-size-xs)", padding: "0.5rem" }}
            >
              🛡️ Admin Demo
            </button>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="tab-group" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={`tab-btn ${mode === "login" ? "active" : ""}`}
            onClick={() => {
              setMode("login");
              setErrorMessage(null);
              setSuccessMessage(null);
            }}
          >
            🔒 Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={`tab-btn ${mode === "register" ? "active" : ""}`}
            onClick={() => {
              setMode("register");
              setErrorMessage(null);
              setSuccessMessage(null);
            }}
          >
            📝 Register Account
          </button>
        </div>

        {/* Error / Success Alerts */}
        {errorMessage && (
          <div
            className="card"
            style={{
              borderColor: "var(--status-emergency-border)",
              backgroundColor: "var(--status-emergency-bg)",
              padding: "var(--space-3)",
              marginBottom: "var(--space-4)",
            }}
            role="alert"
            aria-live="polite"
          >
            <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600 }}>
              ⚠️ {errorMessage}
            </p>
          </div>
        )}

        {successMessage && (
          <div
            className="card"
            style={{
              borderColor: "var(--status-success-border)",
              backgroundColor: "var(--status-success-bg)",
              padding: "var(--space-3)",
              marginBottom: "var(--space-4)",
            }}
            role="status"
            aria-live="polite"
          >
            <p style={{ color: "var(--status-success)", fontSize: "var(--font-size-xs)", fontWeight: 600 }}>
              ✅ {successMessage}
            </p>
          </div>
        )}

        {/* Login Form */}
        {mode === "login" ? (
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: "var(--space-4)" }}>
              <label
                htmlFor="login-username"
                style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}
              >
                Username
              </label>
              <input
                id="login-username"
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. patient_demo"
                autoComplete="username"
                required
                disabled={isSubmitting}
              />
            </div>

            <div style={{ marginBottom: "var(--space-6)" }}>
              <label
                htmlFor="login-password"
                style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                disabled={isSubmitting}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%" }}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="spinner" />
                  <span>Signing In...</span>
                </div>
              ) : (
                "Sign In to Console"
              )}
            </button>
          </form>
        ) : (
          /* Register Form */
          <form onSubmit={handleRegister}>
            <div style={{ marginBottom: "var(--space-3)" }}>
              <label
                htmlFor="reg-username"
                style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}
              >
                Desired Username
              </label>
              <input
                id="reg-username"
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. jane_doe"
                autoComplete="username"
                required
                disabled={isSubmitting}
              />
            </div>

            <div style={{ marginBottom: "var(--space-3)" }}>
              <label
                htmlFor="reg-password"
                style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}
              >
                Password (min. 6 characters)
              </label>
              <input
                id="reg-password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                required
                disabled={isSubmitting}
              />
            </div>

            <div style={{ marginBottom: "var(--space-6)" }}>
              <label
                htmlFor="reg-role"
                style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}
              >
                Account Role
              </label>
              <select
                id="reg-role"
                className="select"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                disabled={isSubmitting}
              >
                <option value="patient">Patient (Care Navigation & Health Records)</option>
                <option value="admin">Administrator (Analytics & Evaluation Scorecards)</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%" }}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="spinner" />
                  <span>Creating Account...</span>
                </div>
              ) : (
                "Create Account & Sign In"
              )}
            </button>
          </form>
        )}

        {/* Footer Disclaimer */}
        <div style={{ marginTop: "var(--space-6)", textAlign: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-4)" }}>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>
            Prototype for healthcare navigation. Strictly non-diagnostic.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="auth-container">
          <div className="spinner spinner-large" />
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
