"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../../context/AuthContext";

interface NavLinkItem {
  name: string;
  href: string;
  icon: string;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavLinkItem[];
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const pathname = usePathname();
  const { role } = useAuth();

  const patientSections: NavSection[] = [
    {
      title: "Navigation",
      items: [
        { name: "Overview", href: "/dashboard", icon: "📊" },
        { name: "AI Care Coordinator", href: "/chat", icon: "💬" },
        { name: "Appointments", href: "/appointments", icon: "📅" },
      ],
    },
    {
      title: "Health Records",
      items: [
        { name: "Vitals Tracker", href: "/vitals", icon: "❤️" },
        { name: "Medications", href: "/medications", icon: "💊" },
        { name: "Reminders", href: "/reminders", icon: "⏰" },
        { name: "Consent Center", href: "/consents", icon: "🛡️" },
      ],
    },
    {
      title: "Voice & Vision",
      items: [
        { name: "Voice Assistant", href: "/voice", icon: "🎙️" },
        { name: "Vision Analyzer", href: "/vision", icon: "👁️" },
      ],
    },
  ];

  const adminSections: NavSection[] = [
    {
      title: "Administration",
      items: [
        { name: "Admin Console", href: "/dashboard", icon: "🛡️" },
      ],
    },
    {
      title: "Analytics & Intelligence",
      items: [
        { name: "Power BI Analytics", href: "/admin/analytics", icon: "📈" },
        { name: "Evaluation Benchmarks", href: "/admin/benchmarks", icon: "🎯" },
        { name: "Messaging Gateway", href: "/admin/messaging", icon: "📱" },
      ],
    },
  ];

  const sections = role === "admin" ? adminSections : patientSections;

  return (
    <>
      {isOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            zIndex: "calc(var(--z-sticky) - 1)",
          }}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`app-sidebar ${isOpen ? "open" : ""}`} aria-label="Main Navigation">
        <div
          style={{
            height: "64px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 var(--space-4)",
            borderBottom: "1px solid var(--border-default)",
          }}
        >
          <div className="flex items-center gap-2">
            <span style={{ fontSize: "1.4rem" }}>🧬</span>
            <div className="flex flex-col">
              <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--brand-primary)" }}>
                CareGraph AI
              </span>
              <span style={{ fontSize: "0.65rem", color: "var(--text-dim)", textTransform: "uppercase" }}>
                {role === "admin" ? "Admin Portal" : "Patient Portal"}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="mobile-menu-btn"
            onClick={onClose}
            aria-label="Close sidebar"
            style={{ border: "none" }}
          >
            ✕
          </button>
        </div>

        <nav style={{ flex: 1, overflowY: "auto", padding: "var(--space-3) 0" }}>
          {sections.map((section, sIdx) => (
            <div key={sIdx} style={{ marginBottom: "var(--space-2)" }}>
              <div className="nav-section-title">{section.title}</div>
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={`nav-item ${isActive ? "active" : ""}`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <span style={{ fontSize: "1.1rem" }}>{item.icon}</span>
                    <span style={{ flex: 1 }}>{item.name}</span>
                    {item.badge && (
                      <span className="badge badge-info" style={{ fontSize: "0.65rem" }}>
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div
          style={{
            padding: "var(--space-4)",
            borderTop: "1px solid var(--border-default)",
            background: "rgba(10, 13, 20, 0.5)",
          }}
        >
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
            CareGraph AI Engine v1.0
          </div>
          <div style={{ fontSize: "0.68rem", color: "var(--text-dim)", marginTop: "2px" }}>
            Synthetic Data Sandbox
          </div>
        </div>
      </aside>
    </>
  );
};
