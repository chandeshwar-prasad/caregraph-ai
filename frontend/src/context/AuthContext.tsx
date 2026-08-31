"use client";

/**
 * CareGraph AI - Authentication Context & Token Manager
 * React Context providing JWT session management, RBAC state, and login/logout handlers
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { UserRole, PatientResponse } from "../types/api";
import { apiClient, ApiClientError } from "../lib/api-client";

interface AuthUser {
  username: string;
  role: UserRole;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  patientProfile: PatientResponse | null;
  login: (username: string, password: string) => Promise<void>;
  quickLogin: (role: UserRole) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "caregraph_auth_token";
const USER_STORAGE_KEY = "caregraph_auth_user";

function parseJwtPayload(token: string): { sub?: string; role?: UserRole; exp?: number } | null {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [patientProfile, setPatientProfile] = useState<PatientResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setPatientProfile(null);
    apiClient.setToken(null);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      sessionStorage.removeItem(USER_STORAGE_KEY);
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token || user?.role !== "patient") return;
    try {
      const profile = await apiClient.getMyProfile();
      setPatientProfile(profile);
    } catch (err: unknown) {
      if (err instanceof ApiClientError && err.status === 404) {
        setPatientProfile(null);
      }
    }
  }, [token, user?.role]);

  // Hydrate session on client mount
  useEffect(() => {
    if (typeof window === "undefined") {
      setIsLoading(false);
      return;
    }

    try {
      const storedToken = sessionStorage.getItem(TOKEN_STORAGE_KEY) || localStorage.getItem(TOKEN_STORAGE_KEY);
      if (storedToken) {
        const payload = parseJwtPayload(storedToken);
        const nowSec = Math.floor(Date.now() / 1000);
        if (payload?.exp && payload.exp < nowSec) {
          // Token expired
          logout();
        } else if (payload?.sub && payload?.role) {
          setToken(storedToken);
          setUser({ username: payload.sub, role: payload.role });
          apiClient.setToken(storedToken);
        }
      }
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  // Fetch patient profile whenever token & role become available
  useEffect(() => {
    if (token && user?.role === "patient") {
      refreshProfile();
    }
  }, [token, user?.role, refreshProfile]);

  const login = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      try {
        const tokenRes = await apiClient.login(username, password);
        const jwtToken = tokenRes.access_token;
        const payload = parseJwtPayload(jwtToken);

        if (!payload?.sub || !payload?.role) {
          throw new Error("Invalid token received from authentication server.");
        }

        const authenticatedUser: AuthUser = {
          username: payload.sub,
          role: payload.role,
        };

        setToken(jwtToken);
        setUser(authenticatedUser);
        apiClient.setToken(jwtToken);

        if (typeof window !== "undefined") {
          sessionStorage.setItem(TOKEN_STORAGE_KEY, jwtToken);
          sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(authenticatedUser));
        }

        if (authenticatedUser.role === "patient") {
          try {
            const profile = await apiClient.getMyProfile();
            setPatientProfile(profile);
          } catch {
            setPatientProfile(null);
          }
        }
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const quickLogin = useCallback(
    async (targetRole: UserRole) => {
      if (targetRole === "patient") {
        await login("patient_demo", "patient_pass");
      } else {
        await login("admin_demo", "admin_pass");
      }
    },
    [login]
  );

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      token,
      role: user?.role || null,
      isAuthenticated: !!token && !!user,
      isLoading,
      patientProfile,
      login,
      quickLogin,
      logout,
      refreshProfile,
    }),
    [user, token, isLoading, patientProfile, login, quickLogin, logout, refreshProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
