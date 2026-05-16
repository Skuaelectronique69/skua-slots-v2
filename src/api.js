const API_URL = import.meta.env.VITE_API_URL || "http://100.121.68.48:8016";
import { getTelegramInitData, getTelegramUser, getPlayerId, getPlayerName } from "./telegram.js";
const TOKEN_KEY = "skua_slots_token";
const DEV_PLAYER = "DEV_OP";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

async function apiFetch(path, options = {}) {
  const token = getToken();

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Accept": "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  return response;
}

export async function devLogin() {
  const response = await fetch(`${API_URL}/api/v1/player/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      getTelegramInitData()
        ? { initData: getTelegramInitData() }
        : { telegram_id: getPlayerId(), username: getPlayerName() }
    ),
  });

  if (!response.ok) {
    throw new Error(`dev-login failed: ${response.status}`);
  }

  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export async function fetchMe() {
  let response = await apiFetch(`/api/v1/player/profile/${getPlayerId()}`, { method: "GET" });
  let data = await response.json();

  if (!data.authenticated) {
    await devLogin();
    response = await apiFetch(`/api/v1/player/profile/${getPlayerId()}`, { method: "GET" });
    data = await response.json();
  }

  return data;
}

export async function serverSpin() {
  const tgUser = getTelegramUser();

  const payload = getTelegramInitData()
    ? {
        telegram_id: tgUser?.id,
        username: getPlayerName(),
        bet: 10,
        initData: getTelegramInitData(),
      }
    : {
        telegram_id: getPlayerId(),
        username: getPlayerName(),
        bet: 10,
      };

  const response = await apiFetch("/api/v1/slots/spin", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Spin API ${response.status}: ${text}`);
  }

  return await response.json();
}

export async function fetchLeaderboard() {
  const response = await apiFetch("/api/v1/economy/leaderboard", {
    method: "GET",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Leaderboard API ${response.status}: ${text}`);
  }

  return await response.json();
}

export async function fetchWallet() {
  const response = await apiFetch(`/api/v1/economy/balance/${getPlayerId()}`, { method: "GET" });
  if (!response.ok) throw new Error(`/api/wallet failed ${response.status}`);
  return await response.json();
}

export async function fetchWalletHistory(limit = 10, offset = 0) {
  const response = await apiFetch(`/api/v1/economy/history/${getPlayerId()}?limit=${limit}`, {
    method: "GET",
  });
  if (!response.ok) throw new Error(`/api/wallet/history failed ${response.status}`);
  return await response.json();
}

export async function fetchStreak() {
  const response = await apiFetch(`/api/v1/economy/balance/${getPlayerId()}`, { method: "GET" });
  if (!response.ok) throw new Error(`/api/streak failed ${response.status}`);
  return await response.json();
}

export async function claimStreak() {
  const response = await apiFetch(`/api/v1/economy/daily/${getPlayerId()}`, { method: "POST" });
  if (!response.ok) throw new Error(`/api/streak/claim failed ${response.status}`);
  return await response.json();
}
