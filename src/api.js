import { getTelegramInitData, getTelegramWebApp } from "./telegram.js";

const API_URL = (import.meta.env?.VITE_API_URL || "").replace(/\/$/, "");
const SESSION_KEY = "skua_slots_session";

let authSession = null;

export class ApiClientError extends Error {
  constructor(code, message, status = null) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
  }
}

function getSessionStorage() {
  try {
    return globalThis.sessionStorage || globalThis.window?.sessionStorage || null;
  } catch {
    return null;
  }
}

function isExpired(expiresAt) {
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(expiresAt);
  const timestamp = Date.parse(hasTimezone ? expiresAt : expiresAt + "Z");
  return !Number.isFinite(timestamp) || timestamp <= Date.now();
}

function readAuthSession() {
  if (authSession && !isExpired(authSession.expiresAt)) {
    return authSession;
  }

  authSession = null;
  const storage = getSessionStorage();
  const stored = storage?.getItem(SESSION_KEY);
  if (!stored) return null;

  try {
    const parsed = JSON.parse(stored);
    if (
      typeof parsed.accessToken !== "string"
      || !parsed.accessToken
      || typeof parsed.expiresAt !== "string"
      || isExpired(parsed.expiresAt)
    ) {
      storage.removeItem(SESSION_KEY);
      return null;
    }
    authSession = parsed;
    return authSession;
  } catch {
    storage.removeItem(SESSION_KEY);
    return null;
  }
}

function writeAuthSession(payload) {
  const expiresAt = payload?.expires_at;
  if (
    typeof payload?.access_token !== "string"
    || !payload.access_token
    || typeof expiresAt !== "string"
    || isExpired(expiresAt)
  ) {
    throw new ApiClientError(
      "AUTHENTICATION_REFUSED",
      "Telegram authentication returned an invalid session.",
    );
  }

  authSession = {
    accessToken: payload.access_token,
    expiresAt,
  };
  getSessionStorage()?.setItem(SESSION_KEY, JSON.stringify(authSession));
}

export function clearAuthSession() {
  authSession = null;
  getSessionStorage()?.removeItem(SESSION_KEY);
}

async function fetchResponse(path, options = {}, requiresAuth = false) {
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  if (requiresAuth) {
    const session = readAuthSession();
    if (!session) {
      throw new ApiClientError(
        "SESSION_EXPIRED",
        "Telegram session is missing or expired.",
        401,
      );
    }
    headers.Authorization = "Bearer " + session.accessToken;
  }

  let response;
  try {
    response = await fetch(API_URL + path, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiClientError(
      "NETWORK_ERROR",
      "The SkuaSlots API is unreachable.",
    );
  }

  if (requiresAuth && response.status === 401) {
    clearAuthSession();
    throw new ApiClientError(
      "SESSION_EXPIRED",
      "Telegram session is missing or expired.",
      401,
    );
  }

  if (!response.ok) {
    throw new ApiClientError(
      "API_ERROR",
      "The SkuaSlots API refused the request.",
      response.status,
    );
  }

  return response;
}

async function responseJson(response, errorCode = "API_ERROR") {
  try {
    return await response.json();
  } catch {
    throw new ApiClientError(errorCode, "The SkuaSlots API returned an invalid response.");
  }
}

export async function authenticateWithTelegram() {
  if (!getTelegramWebApp()) {
    clearAuthSession();
    throw new ApiClientError(
      "TELEGRAM_UNAVAILABLE",
      "Telegram WebApp is unavailable.",
    );
  }

  const initData = getTelegramInitData().trim();
  if (!initData) {
    clearAuthSession();
    throw new ApiClientError(
      "TELEGRAM_INIT_DATA_MISSING",
      "Telegram initData is missing.",
    );
  }

  clearAuthSession();

  let response;
  try {
    response = await fetch(API_URL + "/api/auth/telegram", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ init_data: initData }),
    });
  } catch {
    clearAuthSession();
    throw new ApiClientError(
      "NETWORK_ERROR",
      "The SkuaSlots API is unreachable.",
    );
  }

  if (!response.ok) {
    clearAuthSession();
    throw new ApiClientError(
      "AUTHENTICATION_REFUSED",
      "Telegram authentication was refused.",
      response.status,
    );
  }

  const payload = await responseJson(response, "AUTHENTICATION_REFUSED");
  writeAuthSession(payload);
  return payload;
}

async function ensureAuthSession() {
  if (!readAuthSession()) {
    await authenticateWithTelegram();
  }
}

async function protectedJson(path, options = {}) {
  await ensureAuthSession();
  const response = await fetchResponse(path, options, true);
  return responseJson(response);
}

export async function fetchMe() {
  const data = await protectedJson("/api/me", { method: "GET" });
  if (!data.authenticated) {
    clearAuthSession();
    throw new ApiClientError(
      data.reason === "expired_token" ? "SESSION_EXPIRED" : "AUTHENTICATION_REFUSED",
      "Telegram authentication was refused.",
      401,
    );
  }
  return data;
}

export async function serverSpin() {
  return protectedJson("/api/spin", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function fetchLeaderboard() {
  const response = await fetchResponse("/api/leaderboard", { method: "GET" });
  return responseJson(response);
}

export async function fetchWallet() {
  return protectedJson("/api/wallet", { method: "GET" });
}

export async function fetchWalletHistory(limit = 10, offset = 0) {
  return protectedJson(
    "/api/wallet/history?limit=" + encodeURIComponent(limit)
      + "&offset=" + encodeURIComponent(offset),
    { method: "GET" },
  );
}

export async function fetchStreak() {
  return protectedJson("/api/streak", { method: "GET" });
}

export async function claimStreak() {
  return protectedJson("/api/streak/claim", { method: "POST" });
}
