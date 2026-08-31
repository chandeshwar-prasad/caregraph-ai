"use client";

import React from "react";
import { useAuth } from "../../context/AuthContext";

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { user, role, logout } = useAuth();

  return (
    <header className="app-header">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation menu"
        >
          <span style={{ fontSize: "1.2rem", lineHeight: 1 }}>☰</span>
        </button>
        <div className="flex items-center gap-2">
          <span style={{ fontSize: "1.3rem" }}>🧬</span>
          <span style={{ fontWeight: 700, fontSize: "var(--font-size-base)", color: "var(--text-primary)" }}>
            CareGraph AI
          </span>
          <span
            className="badge badge-info"
            style={{ fontSize: "0.7rem", padding: "0.15rem 0.5rem" }}
          >
            Care Coordination
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user ? (
          <div className="flex items-center gap-3">
            <div className="flex flex-col" style={{ alignItems: "flex-end" }}>
              <span style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--text-primary)" }}>
                {user.username}
              </span>
              <span
                className={role === "admin" ? "badge badge-urgent" : "badge badge-success"}
                style={{ fontSize: "0.65rem", padding: "0.1rem 0.4rem" }}
              >
                {role ? role.toUpperCase() : "USER"}
              </span>
            </div>

            <button
              type="button"
              onClick={logout}
              className="btn btn-secondary"
              style={{ padding: "0.4rem 0.8rem", fontSize: "var(--font-size-xs)" }}
              aria-label="Log out of session"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>
            Not authenticated
          </span>
        )}
      </div>
    </header>
  );
};
