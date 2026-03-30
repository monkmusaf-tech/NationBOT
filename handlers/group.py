from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number


def group_handlers(db):

    async def group_wars(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active wars in group."""
        if update.effective_chat.type == "private":
            await update.message.reply_text("Perintah ini untuk grup!")
            return

        db.register_group(update.effective_chat.id, update.effective_chat.title)

        wars = db.get_active_wars()
        if not wars:
            await update.message.reply_text("☮️ Tidak ada perang aktif saat ini.")
            return

        text = "⚔️ **PERANG DUNIA** ⚔️\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for w in wars:
            atk = db.get_nation(w["attacker_id"])
            defe = db.get_nation(w["defender_id"])
            atk_name = atk["name"] if atk else "?"
            def_name = defe["name"] if defe else "?"
            text += (
                f"⚔️ **{atk_name}** vs **{def_name}**\n"
                f"  Skor: {w['attacker_wins']}-{w['defender_wins']} (Ronde {w['total_rounds']})\n\n"
            )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def group_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent events in group."""
        if update.effective_chat.type == "private":
            await update.message.reply_text("Perintah ini untuk grup!")
            return

        db.register_group(update.effective_chat.id, update.effective_chat.title)

        events = db.get_recent_events(limit=10)
        if not events:
            await update.message.reply_text("📰 Belum ada berita.")
            return

        text = "📰 **BERITA DUNIA** 📰\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for e in events:
            type_emoji = {
                "disaster": "🔴", "crisis": "🟡", "bonus": "🟢",
                "war_declared": "⚔️", "nuke_launched": "☢️",
                "alliance": "🤝", "nation_created": "🏛️",
                "gov_change": "🔄", "sanction": "🚫",
                "aid": "📦", "nuke_developed": "☢️",
            }.get(e["type"], "📌")
            text += f"{type_emoji} {e['description']}\n"
            text += f"  ⏰ {e['timestamp'][:16]}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    return [
        CommandHandler("wars", group_wars),
        CommandHandler("news", group_news),
    ]
