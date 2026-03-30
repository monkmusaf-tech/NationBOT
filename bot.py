import os
import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from models.database import Database
from handlers.start import start_handler, help_handler
from handlers.nation import nation_handlers
from handlers.economy import economy_handlers
from handlers.military import military_handlers
from handlers.politics import politics_handlers
from handlers.diplomacy import diplomacy_handlers
from handlers.events import event_handlers, schedule_events
from handlers.admin import admin_handlers
from handlers.war import war_handlers
from handlers.group import group_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.environ.get("SUPER_ADMIN_ID", "0"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

db = Database()


async def post_init(application: Application):
    commands = [
        BotCommand("start", "🏁 Mulai game / Daftar negara"),
        BotCommand("help", "📖 Panduan bermain"),
        BotCommand("negara", "🏛️ Lihat info negara kamu"),
        BotCommand("ekonomi", "💰 Panel ekonomi"),
        BotCommand("militer", "⚔️ Panel militer"),
        BotCommand("politik", "🗳️ Panel politik"),
        BotCommand("diplomasi", "🤝 Panel diplomasi"),
        BotCommand("perang", "💥 Panel perang"),
        BotCommand("ranking", "🏆 Ranking negara"),
        BotCommand("event", "📰 Event terkini"),
        BotCommand("admin", "👑 Panel super admin"),
    ]
    await application.bot.set_my_commands(commands)
    schedule_events(application, db)
    logger.info("Bot initialized successfully!")


def main():
    builder = Application.builder().token(TOKEN)
    app = builder.post_init(post_init).build()

    app.bot_data["db"] = db
    app.bot_data["super_admin_id"] = SUPER_ADMIN_ID

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))

    all_handlers = (
        nation_handlers(db)
        + economy_handlers(db)
        + military_handlers(db)
        + politics_handlers(db)
        + diplomacy_handlers(db)
        + war_handlers(db)
        + event_handlers(db)
        + admin_handlers(db, SUPER_ADMIN_ID)
        + group_handlers(db)
    )
    for handler in all_handlers:
        app.add_handler(handler)

    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        logger.info(f"Starting webhook on port {PORT}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
    else:
        logger.info("Starting polling mode")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


async def error_handler(update: object, context):
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Terjadi kesalahan. Silakan coba lagi."
        )


if __name__ == "__main__":
    main()
