# SkuaSlots Telegram authentication boundary

This branch prepares the existing SkuaSlots API for a Telegram Mini App without
activating or bypassing Telegram authentication.

## Runtime requirements

- `TELEGRAM_BOT_TOKEN`: real BotFather token, supplied only through the runtime
  secret store. If absent, `POST /api/auth/telegram` fails closed with HTTP 401.
- `SKUA_SLOTS_CORS_ORIGINS`: comma-separated exact HTTPS Mini App origins.
- `SKUA_SLOTS_ALLOW_DEV_AUTH`: leave unset or `false` outside an isolated local
  development runtime. It gates both `dev-login` and `dev-mint`.

The client must send Telegram's unchanged `initData` string as `init_data` to
`POST /api/auth/telegram`. The server verifies its HMAC, age and signed user ID,
then returns the existing bearer session format. Mutable player, wallet, streak,
daily and spin routes require that bearer session and never fall back to a
client-supplied player identity.

## Activation proof required

1. Merge only after reconciling the frontend worktree changes with this endpoint.
2. Inject the real token without printing or committing it.
3. Configure the exact public HTTPS origin.
4. Prove invalid, expired and tampered `initData` are rejected.
5. Prove one real Telegram session can authenticate and mutate only its own state.

## Rollback

Revert the deployment to the previous image or commit and restart only the
SkuaSlots API unit. No database migration is introduced by this change; existing
sessions and player data remain compatible.
