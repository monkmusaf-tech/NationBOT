from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils.helpers import make_keyboard, format_number


def group_handlers(db):

    async def group_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show ranking in group chat."""
        if update.effective_chat.type == "private":
            await update.message.reply_text("Perintah ini untuk grup! Gunakan /ranking di private chat.")
            return

        db.register_group(update.effective_chat.id, update.effective_chat.title)

        nations = db.get_all_nations()
        if not nations:
            await update.message.reply_text("📊 Belum ada negara. Daftarkan negara di private chat bot!")
            return

        ranked = sorted(nations, key=lambda n: db.calc_power(n), reverse=True)

        text = "🏆 **WORLD RANKING** 🏆\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, n in enumerate(ranked[:10]):
            medal = medals[i] if i < 3 else f"#{i+1}"
            power = db.calc_power(n)
            war = " ⚔️" if n.get("is_at_war") else ""
            text += f"{medal} **{n['name']}** — ⚡{format_number(power)}{war}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def group_wars(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active wars in group."""
        if update.effective_chat.type == "private":
            return

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
            return

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

    async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast message from admin."""
        if not context.user_data.get("awaiting_broadcast"):
            return
        if update.effective_chat.type != "private":
            return

        admin_id = context.application.bot_data.get("super_admin_id", 0)
        if update.effective_user.id != admin_id:
            return

        if update.message.text == "/cancel":
            context.user_data["awaiting_broadcast"] = False
            await update.message.reply_text("❌ Broadcast dibatalkan.")
            return

        context.user_data["awaiting_broadcast"] = False
        message = update.message.text
        sent = 0
        failed = 0

        # Send to all players
        nations = db.get_all_nations()
        for n in nations:
            try:
                await context.bot.send_message(
                    n["user_id"],
                    f"📢 **PENGUMUMAN ADMIN** 📢\n━━━━━━━━━━━━━━━━━━\n\n{message}",
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1

        # Send to all groups
        groups = db.get_all_groups()
        for g in groups:
            try:
                await context.bot.send_message(
                    g["chat_id"],
                    f"📢 **PENGUMUMAN ADMIN** 📢\n━━━━━━━━━━━━━━━━━━\n\n{message}",
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1

        await update.message.reply_text(
            f"📢 **Broadcast Selesai!**\n\n"
            f"✅ Terkirim: {sent}\n"
            f"❌ Gagal: {failed}",
            parse_mode="Markdown"
        )

    return [
        CommandHandler("ranking", group_ranking),
        CommandHandler("wars", group_wars),
        CommandHandler("news", group_news),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_broadcast,
        ),
    ]
