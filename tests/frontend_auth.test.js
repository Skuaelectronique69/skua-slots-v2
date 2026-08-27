import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test, { afterEach, beforeEach } from "node:test";

import {
  authenticateWithTelegram,
  clearAuthSession,
  fetchMe,
  serverSpin,
} from "../src/api.js";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalSessionStorage = globalThis.sessionStorage;
const originalLocalStorage = globalThis.localStorage;

function createSessionStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    },
  };
}

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return body;
    },
  };
}

function installTelegram(initData) {
  globalThis.window = {
    Telegram: {
      WebApp: {
        initData,
        ready() {},
      },
    },
  };
}

function restoreGlobal(name, value) {
  if (value === undefined) {
    delete globalThis[name];
  } else {
    globalThis[name] = value;
  }
}

beforeEach(() => {
  globalThis.sessionStorage = createSessionStorage();
  globalThis.localStorage = {
    getItem() {
      throw new Error("localStorage must not be used");
    },
    setItem() {
      throw new Error("localStorage must not be used");
    },
    removeItem() {
      throw new Error("localStorage must not be used");
    },
  };
  installTelegram("query_id=test-fixture&hash=not-a-real-signature");
  clearAuthSession();
});

afterEach(() => {
  clearAuthSession();
  restoreGlobal("fetch", originalFetch);
  restoreGlobal("window", originalWindow);
  restoreGlobal("sessionStorage", originalSessionStorage);
  restoreGlobal("localStorage", originalLocalStorage);
});

test("initData authentication stores a session bearer and attaches it to mutations", async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/auth/telegram") {
      return jsonResponse({
        access_token: "test-session-bearer",
        expires_at: "2099-01-01T00:00:00",
      });
    }
    if (url === "/api/me") {
      return jsonResponse({
        authenticated: true,
        player_id: "test-player",
        energy: 100,
        xp: 0,
        credits: 500,
      });
    }
    if (url === "/api/spin") {
      return jsonResponse({ accepted: true });
    }
    throw new Error("unexpected request");
  };

  const me = await fetchMe();
  const spin = await serverSpin();

  assert.equal(me.authenticated, true);
  assert.equal(spin.accepted, true);
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    init_data: "query_id=test-fixture&hash=not-a-real-signature",
  });
  assert.equal(calls[1].options.headers.Authorization, "Bearer test-session-bearer");
  assert.equal(calls[2].options.headers.Authorization, "Bearer test-session-bearer");
  assert.deepEqual(JSON.parse(calls[2].options.body), {});
  assert.ok(globalThis.sessionStorage.getItem("skua_slots_session"));
});

test("normal frontend source contains no dev auth call or production URL fallback", async () => {
  const source = await readFile(new URL("../src/api.js", import.meta.url), "utf8");

  assert.equal(source.includes("/api/auth/dev-login"), false);
  assert.equal(source.includes("/api/wallet/dev-mint"), false);
  assert.equal(source.includes("localStorage"), false);
  assert.equal(/https?:\/\/[A-Za-z0-9]/.test(source), false);
});

test("Telegram WebApp absence fails before any network request", async () => {
  globalThis.window = {};
  globalThis.fetch = async () => {
    assert.fail("network must not be called");
  };

  await assert.rejects(
    authenticateWithTelegram(),
    (error) => error.code === "TELEGRAM_UNAVAILABLE",
  );
});

test("missing initData fails before any network request", async () => {
  installTelegram("");
  globalThis.fetch = async () => {
    assert.fail("network must not be called");
  };

  await assert.rejects(
    authenticateWithTelegram(),
    (error) => error.code === "TELEGRAM_INIT_DATA_MISSING",
  );
});

test("backend refusal of invalid initData is reported without creating a session", async () => {
  installTelegram("malformed-test-init-data");
  globalThis.fetch = async () => jsonResponse({ detail: "invalid" }, 401);

  await assert.rejects(
    authenticateWithTelegram(),
    (error) => error.code === "AUTHENTICATION_REFUSED" && error.status === 401,
  );
  assert.equal(globalThis.sessionStorage.getItem("skua_slots_session"), null);
});

test("expired server session is cleared and reported", async () => {
  let requestCount = 0;
  globalThis.fetch = async (url) => {
    requestCount += 1;
    if (url === "/api/auth/telegram") {
      return jsonResponse({
        access_token: "test-expiring-bearer",
        expires_at: "2099-01-01T00:00:00",
      });
    }
    return jsonResponse({ detail: "expired" }, 401);
  };

  await assert.rejects(
    fetchMe(),
    (error) => error.code === "SESSION_EXPIRED" && error.status === 401,
  );
  assert.equal(requestCount, 2);
  assert.equal(globalThis.sessionStorage.getItem("skua_slots_session"), null);
});

test("network failure is reported without persisting a session", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("test network failure");
  };

  await assert.rejects(
    authenticateWithTelegram(),
    (error) => error.code === "NETWORK_ERROR",
  );
  assert.equal(globalThis.sessionStorage.getItem("skua_slots_session"), null);
});
