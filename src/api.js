const API_URL = "http://100.121.68.48:8011";
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
  const response = await fetch(`${API_URL}/api/auth/dev-login/${DEV_PLAYER}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`dev-login failed: ${response.status}`);
  }

  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export async function fetchMe() {
  let response = await apiFetch("/api/me", { method: "GET" });
  let data = await response.json();

  if (!data.authenticated) {
    await devLogin();
    response = await apiFetch("/api/me", { method: "GET" });
    data = await response.json();
  }

  return data;
}

export async function serverSpin() {
  const response = await apiFetch("/api/spin", {
    method: "POST",
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Spin API ${response.status}: ${text}`);
  }

  return await response.json();
}

export async function fetchLeaderboard() {
  const response = await apiFetch("/api/leaderboard", {
    method: "GET",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Leaderboard API ${response.status}: ${text}`);
  }

  return await response.json();
}
