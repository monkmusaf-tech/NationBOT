import random
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


RANDOM_EVENTS = [
    {
        "name": "🌋 Gunung Meletus",
        "type": "disaster",
        "description": "Gunung berapi meletus! Infrastruktur rusak parah.",
        "effects": {"population": -5000, "farms": -2, "happiness": -15, "money": -3000},
        "weight": 5,
    },
    {
        "name": "🌊 Tsunami",
        "type": "disaster",
        "description": "Tsunami besar menerjang pesisir!",
        "effects": {"population": -8000, "ships": -1, "money": -5000, "happiness": -20},
        "weight": 3,
    },
    {
        "name": "🦠 Pandemi",
        "type": "crisis",
        "description": "Wabah penyakit menyebar di seluruh negeri!",
        "effects": {"population": -3000, "health": -25, "happiness": -15, "gdp": -5000},
        "weight": 5,
    },
    {
        "name": "📉 Krisis Ekonomi",
        "type": "crisis",
        "description": "Resesi global menghantam ekonomi negara!",
        "effects": {"money": -8000, "gdp": -10000, "unemployment": 10, "happiness": -10},
        "weight": 7,
    },
    {
        "name": "🪖 Kudeta Militer",
        "type": "crisis",
        "description": "Perwira tinggi mencoba menggulingkan pemerintah!",
        "effects": {"stability": -30, "soldiers": -500, "approval_rating": -20},
        "weight": 3,
    },
    {
        "name": "😡 Protes Massal",
        "type": "crisis",
        "description": "Rakyat turun ke jalan menuntut perubahan!",
        "effects": {"stability": -15, "happiness": -10, "approval_rating": -15},
        "weight": 8,
    },
    {
        "name": "💰 Boom Ekonomi",
        "type": "bonus",
        "description": "Perekonomian tumbuh pesat!",
        "effects": {"money": 10000, "gdp": 15000, "happiness": 10},
        "weight": 6,
    },
    {
        "name": "🔬 Terobosan Teknologi",
        "type": "bonus",
        "description": "Ilmuwan menemukan teknologi baru!",
        "effects": {"tech_points": 20, "education": 10, "military_tech": 1},
        "weight": 5,
    },
    {
        "name": "🌾 Panen Raya",
        "type": "bonus",
        "description": "Hasil panen melimpah tahun ini!",
        "effects": {"food": 5000, "happiness": 10, "health": 5},
        "weight": 8,
    },
    {
        "name": "🛢️ Sumber Minyak Baru",
        "type": "bonus",
        "description": "Ditemukan ladang minyak baru!",
        "effects": {"oil": 3000, "money": 5000, "oil_wells": 2},
        "weight": 4,
    },
    {
        "name": "👶 Baby Boom",
        "type": "bonus",
        "description": "Lonjakan kelahiran meningkatkan populasi!",
        "effects": {"population": 15000, "happiness": 5},
        "weight": 6,
    },
    {
        "name": "🌪️ Badai Besar",
        "type": "disaster",
        "description": "Badai dahsyat menghancurkan infrastruktur!",
        "effects": {"factories": -1, "farms": -2, "money": -2000, "happiness": -5},
        "weight": 7,
    },
    {
        "name": "🕵️ Skandal Korupsi",
        "type": "crisis",
        "description": "Skandal korupsi besar terungkap!",
        "effects": {"corruption": 15, "approval_rating": -20, "stability": -10},
        "weight": 6,
    },
    {
        "name": "🏆 Kemenangan Olahraga",
        "type": "bonus",
        "description": "Tim nasional memenangkan kejuaraan dunia!",
        "effects": {"happiness": 15, "reputation": 5, "approval_rating": 10},
        "weight": 5,
    },
    {
        "name": "⛏️ Penemuan Tambang Emas",
        "type": "bonus",
        "description": "Tambang emas besar ditemukan!",
        "effects": {"money": 15000, "materials": 3000, "mines": 2},
        "weight": 3,
    },
    {
        "name": "🔥 Kebakaran Hutan",
        "type": "disaster",
        "description": "Kebakaran hutan meluas tak terkendali!",
        "effects": {"farms": -3, "food": -2000, "health": -10, "happiness": -5},
        "weight": 6,
    },
    {
        "name": "💊 Obat Baru Ditemukan",
        "type": "bonus",
        "description": "Ilmuwan menemukan obat revolusioner!",
        "effects": {"health": 15, "happiness": 5, "reputation": 5, "tech_points": 10},
        "weight": 4,
    },
    {
        "name": "🏴‍☠️ Serangan Bajak Laut",
        "type": "crisis",
        "description": "Bajak laut menyerang jalur perdagangan!",
        "effects": {"ships": -1, "money": -3000, "trade_income": -500},
        "weight": 5,
    },
]


def apply_event_effects(db, nation, effects):
    """Apply event effects to a nation."""
    updates = {}
    for key, val in effects.items():
        if key in nation:
            new_val = nation[key] + val
            if key in ("happiness", "health", "education", "corruption",
                       "freedom_index", "stability", "approval_rating",
                       "military_morale", "unemployment"):
                new_val = clamp(new_val)
            elif key in ("population", "soldiers", "tanks", "jets", "ships",
                         "factories", "farms", "mines", "oil_wells", "food",
                         "materials", "oil", "money", "gdp"):
                new_val = max(0, new_val)
            updates[key] = new_val
    if updates:
        db.update_nation(nation["user_id"], updates)
    return updates


def schedule_events(application, db):
    """Schedule random events using job queue."""
    freq = db.get_setting("event_frequency", 3600)

    async def trigger_random_event(context):
        if not db.get_setting("game_active", True):
            return

        nations = db.get_all_nations()
        if not nations:
            return

        # Pick random nation
        nation = random.choice(nations)

        # Weighted random event
        weights = [e["weight"] for e in RANDOM_EVENTS]
        event = random.choices(RANDOM_EVENTS, weights=weights, k=1)[0]

        applied = apply_event_effects(db, nation, event["effects"])
        db.log_event(event["type"], nation["user_id"], event["description"], event["effects"])

        # Try to notify the user
        try:
            effect_text = ""
            for key, val in event["effects"].items():
                sign = "+" if val > 0 else ""
                effect_text += f"  {key}: {sign}{val}\n"

            await context.bot.send_message(
                nation["user_id"],
                f"📰 **EVENT: {event['name']}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🏛️ Negara: {nation['name']}\n"
                f"📝 {event['description']}\n\n"
                f"📊 **Dampak:**\n{effect_text}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # Announce to groups
        groups = db.get_all_groups()
        for g in groups:
            try:
                await context.bot.send_message(
                    g["chat_id"],
                    f"📰 **EVENT!** {event['name']}\n"
                    f"🏛️ {nation['name']}: {event['description']}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    application.job_queue.run_repeating(trigger_random_event, interval=freq, first=60)


def event_handlers(db):

    async def event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            send = query.edit_message_text
        else:
            user_id = update.effective_user.id
            send = update.message.reply_text

        nation = db.get_nation(user_id)

        # Get recent events
        if nation:
            events = db.get_recent_events(user_id, 5)
        else:
            events = db.get_recent_events(limit=10)

        text = "📰 **EVENT TERKINI** 📰\n━━━━━━━━━━━━━━━━━━━━━\n\n"

        if not events:
            text += "Belum ada event."
        else:
            for e in events:
                type_emoji = {"disaster": "🔴", "crisis": "🟡", "bonus": "🟢"}.get(e["type"], "⚪")
                text += f"{type_emoji} {e['description']}\n"
                text += f"  ⏰ {e['timestamp'][:16]}\n\n"

        # Global events
        global_events = db.get_recent_events(limit=5)
        if global_events:
            text += "\n🌍 **Event Global:**\n"
            for e in global_events[:5]:
                type_emoji = {"disaster": "🔴", "crisis": "🟡", "bonus": "🟢",
                              "war_declared": "⚔️", "nuke_launched": "☢️",
                              "alliance": "🤝", "nation_created": "🏛️"}.get(e["type"], "📌")
                text += f"{type_emoji} {e['description']}\n"

        await send(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Kembali", "menu_back")])
        )

    return [
        CommandHandler("event", event_menu),
        CallbackQueryHandler(event_menu, pattern=r"^menu_event$"),
    ]
