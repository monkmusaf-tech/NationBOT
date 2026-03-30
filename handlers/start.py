from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    user_id = update.effective_user.id
    nation = db.get_nation(user_id)

    if update.effective_chat.type != "private":
        # Group chat - register group
        db.register_group(update.effective_chat.id, update.effective_chat.title)
        if nation:
            await update.message.reply_text(
                f"🏛️ Selamat datang kembali, pemimpin **{nation['name']}**!\n\n"
                f"Grup ini sudah terdaftar. Gunakan /help untuk melihat perintah.\n"
                f"Untuk mengelola negara, chat bot secara pribadi.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "🌍 **NATION BUILDER GAME** 🌍\n\n"
                "Selamat datang! Chat saya secara pribadi untuk mendirikan negara.\n"
                "Klik tombol di bawah untuk memulai!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏁 Mulai di Private Chat", url=f"https://t.me/{context.bot.username}?start=new")]
                ])
            )
        return

    # Private chat
    if nation:
        await update.message.reply_text(
            f"🏛️ Selamat datang kembali, pemimpin **{nation['name']}**!\n\n"
            f"Gunakan /negara untuk melihat status negara.\n"
            f"Gunakan /help untuk melihat semua perintah.",
            parse_mode="Markdown"
        )
        return

    # New player registration
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗳️ Demokrasi", callback_data="ideology_demokrasi")],
        [InlineKeyboardButton("👑 Monarki", callback_data="ideology_monarki")],
        [InlineKeyboardButton("☭ Komunis", callback_data="ideology_komunis")],
        [InlineKeyboardButton("⚔️ Junta Militer", callback_data="ideology_militer")],
        [InlineKeyboardButton("🕌 Teokrasi", callback_data="ideology_teokrasi")],
    ])

    await update.message.reply_text(
        "🌍 **NATION BUILDER GAME** 🌍\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Bangun negaramu dari nol!\n"
        "Kelola ekonomi, militer, politik, dan diplomasi.\n"
        "Bersaing atau beraliansi dengan pemain lain!\n\n"
        "📌 **Langkah 1:** Pilih ideologi pemerintahan:\n",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 **PANDUAN NATION BUILDER** 📖\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏛️ **Negara**\n"
        "/negara - Lihat info lengkap negaramu\n"
        "/ranking - Peringkat semua negara\n\n"
        "💰 **Ekonomi**\n"
        "/ekonomi - Panel ekonomi\n"
        "  • Bangun pabrik, tambang, pertanian\n"
        "  • Atur pajak & perdagangan\n"
        "  • Kumpulkan pendapatan\n\n"
        "⚔️ **Militer**\n"
        "/militer - Panel militer\n"
        "  • Rekrut tentara & beli senjata\n"
        "  • Upgrade teknologi & pertahanan\n"
        "  • Riset nuklir\n\n"
        "🗳️ **Politik**\n"
        "/politik - Panel politik dalam negeri\n"
        "  • Buat kebijakan & undang-undang\n"
        "  • Adakan pemilu\n"
        "  • Kelola korupsi & stabilitas\n\n"
        "🤝 **Diplomasi**\n"
        "/diplomasi - Panel diplomasi\n"
        "  • Buat aliansi\n"
        "  • Kirim/terima tawaran dagang\n"
        "  • Sanksi negara lain\n\n"
        "💥 **Perang**\n"
        "/perang - Mulai atau kelola perang\n"
        "  • Serang negara musuh\n"
        "  • Pertahankan dari serangan\n\n"
        "📰 **Event**\n"
        "/event - Lihat event yang sedang terjadi\n\n"
        "👑 **Admin** (khusus Super Admin)\n"
        "/admin - Panel kontrol game\n\n"
        "💡 **Tips:**\n"
        "• Kumpulkan pendapatan secara rutin\n"
        "• Seimbangkan militer dan ekonomi\n"
        "• Cari sekutu sebelum berperang\n"
        "• Jaga kebahagiaan rakyat!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
