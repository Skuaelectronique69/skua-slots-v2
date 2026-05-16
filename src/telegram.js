export function getTelegramWebApp() {
  return window.Telegram?.WebApp || null;
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

export function getPlayerId() {
  return getTelegramUser()?.id || 12345;
}

export function getPlayerName() {
  const user = getTelegramUser();
  return user?.username || user?.first_name || "DEV_OP";
}
