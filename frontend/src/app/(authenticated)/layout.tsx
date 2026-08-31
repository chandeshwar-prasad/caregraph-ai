"use client";

import React, { useState } from "react";
import { ProtectedRoute } from "../../components/auth/ProtectedRoute";
import { ClinicalBanner } from "../../components/layout/ClinicalBanner";
import { Header } from "../../components/layout/Header";
import { Sidebar } from "../../components/layout/Sidebar";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <ProtectedRoute>
      <div className="flex-col" style={{ minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
        {/* Persistent Clinical Disclaimer Banner */}
        <ClinicalBanner />

        <div className="app-shell">
          {/* Responsive Sidebar Navigation */}
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
          />

          {/* Main Application Area */}
          <div className="app-main">
            <Header onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)} />
            <main className="app-content">{children}</main>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
