export function getTelegramWebApp() {
  return globalThis.window?.Telegram?.WebApp || null;
}

export function initTelegramWebApp() {
  const tg = getTelegramWebApp();
  tg?.ready?.();
  return tg;
}

export function getTelegramUser() {
  return getTelegramWebApp()?.initDataUnsafe?.user || null;
}

export function getTelegramInitData() {
  return getTelegramWebApp()?.initData || "";
}
