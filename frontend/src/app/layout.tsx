import React from "react";
import type { Metadata } from "next";
import "../styles/globals.css";
import { AuthProvider } from "../context/AuthContext";

export const metadata: Metadata = {
  title: "CareGraph AI - Care Coordination Assistant",
  description: "Clinical Care Navigation & Scheduling Workflow",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
