from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from utils.helpers import (
    nation_summary, make_keyboard, IDEOLOGY_MAP, format_number
)

NAMING = 1


def nation_handlers(db):
    async def ideology_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if db.get_nation(user_id):
            await query.edit_message_text("⚠️ Kamu sudah punya negara!")
            return

        ideology = query.data.replace("ideology_", "")
        context.user_data["pending_ideology"] = ideology

        ideology_names = {
            "demokrasi": "🗳️ Demokrasi",
            "monarki": "👑 Monarki",
            "komunis": "☭ Komunis",
            "militer": "⚔️ Junta Militer",
            "teokrasi": "🕌 Teokrasi",
        }

        await query.edit_message_text(
            f"✅ Ideologi: **{ideology_names.get(ideology, ideology)}**\n\n"
            f"📝 Sekarang ketik **nama negara** kamu:\n"
            f"(Contoh: Republik Nusantara, Kerajaan Sakura, dll)",
            parse_mode="Markdown"
        )

    async def name_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if db.get_nation(user_id):
            return
        if "pending_ideology" not in context.user_data:
            return

        name = update.message.text.strip()
        if len(name) < 3 or len(name) > 30:
            await update.message.reply_text("⚠️ Nama harus 3-30 karakter. Coba lagi:")
            return

        if db.get_nation_by_name(name):
            await update.message.reply_text("⚠️ Nama sudah dipakai. Pilih nama lain:")
            return

        ideology = context.user_data.pop("pending_ideology")
        nation = db.create_nation(user_id, name, ideology)

        if ideology in IDEOLOGY_MAP:
            db.update_nation(user_id, IDEOLOGY_MAP[ideology])

        db.log_event("nation_created", user_id, f"Negara {name} telah didirikan!")

        await update.message.reply_text(
            f"🎉 **NEGARA DIDIRIKAN!** 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ **{name}** resmi berdiri!\n"
            f"🏛️ Pemerintahan: {ideology.title()}\n"
            f"💰 Dana awal: $10,000\n"
            f"👥 Populasi: 100,000\n"
            f"🪖 Tentara: 1,000\n\n"
            f"Gunakan /negara untuk melihat detail.\n"
            f"Gunakan /help untuk panduan lengkap.",
            parse_mode="Markdown"
        )

    async def view_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        nation = db.get_nation(user_id)
        if not nation:
            await update.message.reply_text(
                "⚠️ Kamu belum punya negara. Gunakan /start untuk mendirikan!"
            )
            return

        text = nation_summary(nation, db)

        keyboard = make_keyboard([
            ("💰 Ekonomi", "menu_ekonomi"),
            ("⚔️ Militer", "menu_militer"),
            ("🗳️ Politik", "menu_politik"),
            ("🤝 Diplomasi", "menu_diplomasi"),
            ("💥 Perang", "menu_perang"),
            ("📰 Event", "menu_event"),
        ])

        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        nations = db.get_all_nations()
        if not nations:
            await update.message.reply_text("📊 Belum ada negara yang terdaftar.")
            return

        ranked = sorted(nations, key=lambda n: db.calc_power(n), reverse=True)

        text = "🏆 **RANKING NEGARA** 🏆\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, n in enumerate(ranked[:15]):
            medal = medals[i] if i < 3 else f"#{i+1}"
            power = db.calc_power(n)
            war_status = " ⚔️" if n.get("is_at_war") else ""
            text += f"{medal} **{n['name']}** — ⚡{format_number(power)}{war_status}\n"
            text += f"    👥 {format_number(n['population'])} | 💰 ${format_number(n['money'])}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    return [
        CallbackQueryHandler(ideology_callback, pattern=r"^ideology_"),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            name_nation
        ),
        CommandHandler("negara", view_nation),
        CommandHandler("ranking", ranking_cmd),
    ]
