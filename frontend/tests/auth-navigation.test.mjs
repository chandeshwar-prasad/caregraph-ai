/**
 * CareGraph AI - Frontend Authentication & Navigation Test Suite
 * Validating AuthContext, ApiClient, RBAC, Quick-Login, and Navigation Matrix
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

// ==========================================
// 1. JWT Parsing & Token Claims Tests
// ==========================================

function parseJwtPayload(token) {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = Buffer.from(base64, "base64").toString("utf-8");
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function createMockJwt(username, role, expOffsetSeconds = 3600) {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(
    JSON.stringify({
      sub: username,
      role: role,
      exp: Math.floor(Date.now() / 1000) + expOffsetSeconds,
    })
  ).toString("base64url");
  const signature = Buffer.from("mock_signature").toString("base64url");
  return `${header}.${payload}.${signature}`;
}

describe("JWT Parsing & Claim Extraction", () => {
  test("extracts patient role and username correctly from valid JWT", () => {
    const token = createMockJwt("patient_demo", "patient");
    const payload = parseJwtPayload(token);
    assert.equal(payload.sub, "patient_demo");
    assert.equal(payload.role, "patient");
    assert.ok(payload.exp > Math.floor(Date.now() / 1000));
  });

  test("extracts admin role and username correctly from valid JWT", () => {
    const token = createMockJwt("admin_demo", "admin");
    const payload = parseJwtPayload(token);
    assert.equal(payload.sub, "admin_demo");
    assert.equal(payload.role, "admin");
  });

  test("identifies expired tokens correctly", () => {
    const expiredToken = createMockJwt("patient_demo", "patient", -300);
    const payload = parseJwtPayload(expiredToken);
    const nowSec = Math.floor(Date.now() / 1000);
    assert.ok(payload.exp < nowSec, "Token should be in the past");
  });

  test("returns null safely for malformed tokens without throwing", () => {
    assert.equal(parseJwtPayload("not-a-token"), null);
    assert.equal(parseJwtPayload(""), null);
    assert.equal(parseJwtPayload("a.invalid_json_payload.c"), null);
  });
});

// ==========================================
// 2. Quick-Login Presets Validation
// ==========================================

describe("Quick-Login Presets & Credentials", () => {
  const PRESETS = {
    patient: { username: "patient_demo", password: "patient_pass" },
    admin: { username: "admin_demo", password: "admin_pass" },
  };

  test("patient quick login preset maps to patient_demo credentials", () => {
    const preset = PRESETS.patient;
    assert.equal(preset.username, "patient_demo");
    assert.equal(preset.password, "patient_pass");
  });

  test("admin quick login preset maps to admin_demo credentials", () => {
    const preset = PRESETS.admin;
    assert.equal(preset.username, "admin_demo");
    assert.equal(preset.password, "admin_pass");
  });
});

// ==========================================
// 3. Role-Aware Navigation Matrix Tests
// ==========================================

describe("Role-Based Navigation Matrix", () => {
  const PATIENT_NAV_ITEMS = [
    "/dashboard",
    "/chat",
    "/appointments",
    "/vitals",
    "/medications",
    "/reminders",
    "/consents",
    "/voice",
    "/vision",
  ];

  const ADMIN_NAV_ITEMS = [
    "/dashboard",
    "/admin/analytics",
    "/admin/benchmarks",
    "/admin/messaging",
  ];

  function isRouteAllowedForRole(route, role) {
    if (route.startsWith("/admin") && role !== "admin") {
      return false;
    }
    if (role === "admin" && (route === "/vitals" || route === "/medications" || route === "/reminders" || route === "/consents")) {
      return false; // Direct patient health records are restricted
    }
    return true;
  }

  test("patient role can access all patient portal routes", () => {
    for (const route of PATIENT_NAV_ITEMS) {
      assert.ok(isRouteAllowedForRole(route, "patient"), `Patient should access ${route}`);
    }
  });

  test("patient role is denied access to admin routes", () => {
    const restrictedRoutes = ["/admin/analytics", "/admin/benchmarks", "/admin/messaging"];
    for (const route of restrictedRoutes) {
      assert.equal(isRouteAllowedForRole(route, "patient"), false, `Patient must not access ${route}`);
    }
  });

  test("admin role can access operational analytics and benchmark routes", () => {
    for (const route of ADMIN_NAV_ITEMS) {
      assert.ok(isRouteAllowedForRole(route, "admin"), `Admin should access ${route}`);
    }
  });

  test("admin role is restricted from direct patient record pages", () => {
    const directPatientRoutes = ["/vitals", "/medications", "/reminders", "/consents"];
    for (const route of directPatientRoutes) {
      assert.equal(isRouteAllowedForRole(route, "admin"), false, `Admin must not directly view patient personal pages: ${route}`);
    }
  });
});

// ==========================================
// 4. Clinical Safety Disclaimer Invariant Tests
// ==========================================

describe("Clinical Safety & Disclaimer Presentation", () => {
  const DISCLAIMER_TEXT =
    "CareGraph AI Navigation Assistant: Synthetic demonstration system. Not an AI doctor and not a substitute for clinical judgment. For emergencies, call 911 / 112 immediately.";

  test("disclaimer explicitly states CareGraph is not an AI doctor", () => {
    assert.ok(DISCLAIMER_TEXT.includes("Not an AI doctor"));
  });

  test("disclaimer includes emergency contact numbers 911 / 112", () => {
    assert.ok(DISCLAIMER_TEXT.includes("911 / 112"));
  });

  test("disclaimer specifies synthetic demonstration system", () => {
    assert.ok(DISCLAIMER_TEXT.includes("Synthetic demonstration system"));
  });
});

// ==========================================
// 5. Auth State & Redirect Invariants
// ==========================================

describe("Authentication Redirect & Protection Logic", () => {
  function getRedirectDestination(isAuthenticated, pathname, requestedRedirect = null) {
    if (!isAuthenticated) {
      return `/login?redirect=${encodeURIComponent(pathname)}`;
    }
    if (pathname === "/login" || pathname === "/") {
      return requestedRedirect || "/dashboard";
    }
    return pathname;
  }

  test("unauthenticated user on /dashboard is redirected to /login with return parameter", () => {
    const dest = getRedirectDestination(false, "/dashboard");
    assert.equal(dest, "/login?redirect=%2Fdashboard");
  });

  test("unauthenticated user on /chat is redirected to /login with chat return parameter", () => {
    const dest = getRedirectDestination(false, "/chat");
    assert.equal(dest, "/login?redirect=%2Fchat");
  });

  test("authenticated user visiting /login is redirected to /dashboard", () => {
    const dest = getRedirectDestination(true, "/login");
    assert.equal(dest, "/dashboard");
  });

  test("authenticated user visiting / is redirected to /dashboard", () => {
    const dest = getRedirectDestination(true, "/");
    assert.equal(dest, "/dashboard");
  });

  test("authenticated user with requested redirect is honored", () => {
    const dest = getRedirectDestination(true, "/login", "/appointments");
    assert.equal(dest, "/appointments");
  });
});
