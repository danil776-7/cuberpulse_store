# CyberPulse.it Store

Готовый storefront + FastAPI backend + server-side admin.

## Локальный запуск
1. `python -m venv .venv`
2. Активируйте окружение.
3. `pip install -r requirements.txt`
4. Скопируйте `.env.example` в `.env`, задайте `ADMIN_PASSWORD` и `SESSION_SECRET`.
5. `uvicorn app:app --reload`
6. Откройте http://127.0.0.1:8000

## Production / Railway
Добавьте PostgreSQL и переменные `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SESSION_SECRET`. Для Telegram-уведомлений добавьте новый (перевыпущенный) `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` и при необходимости `TELEGRAM_TOPIC_ID`.

**Важно:** старый Telegram token из исходного проекта был раскрыт в клиентском HTML. Не используйте его повторно.
