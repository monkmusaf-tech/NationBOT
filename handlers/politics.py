import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


POLICIES = {
    "pol_healthcare": {
        "name": "🏥 Program Kesehatan Gratis",
        "cost": 3000,
        "effects": {"health": 10, "happiness": 5, "money_drain": 500},
        "desc": "Rakyat mendapat layanan kesehatan gratis"
    },
    "pol_education": {
        "name": "📚 Wajib Belajar 12 Tahun",
        "cost": 4000,
        "effects": {"education": 10, "happiness": 3, "money_drain": 400},
        "desc": "Tingkatkan kualitas pendidikan"
    },
    "pol_military_service": {
        "name": "🪖 Wajib Militer",
        "cost": 2000,
        "effects": {"soldiers": 2000, "happiness": -10, "stability": 5},
        "desc": "Semua warga wajib ikut pelatihan militer"
    },
    "pol_anti_corruption": {
        "name": "⚖️ Pemberantasan Korupsi",
        "cost": 5000,
        "effects": {"corruption": -15, "stability": 5, "approval_rating": 10},
        "desc": "Bentuk lembaga anti-korupsi"
    },
    "pol_censorship": {
        "name": "📵 Sensor Media",
        "cost": 1000,
        "effects": {"freedom_index": -20, "stability": 10, "happiness": -5},
        "desc": "Kontrol informasi yang beredar"
    },
    "pol_welfare": {
        "name": "🤲 Program Bantuan Sosial",
        "cost": 3500,
        "effects": {"happiness": 15, "unemployment": -5, "money_drain": 600},
        "desc": "Bantuan untuk rakyat miskin"
    },
    "pol_open_border": {
        "name": "🌍 Buka Perbatasan",
        "cost": 1000,
        "effects": {"population": 5000, "freedom_index": 10, "reputation": 5},
        "desc": "Terima imigran dari luar"
    },
    "pol_propaganda": {
        "name": "📢 Propaganda Nasional",
        "cost": 2000,
        "effects": {"approval_rating": 15, "freedom_index": -10, "military_morale": 10},
        "desc": "Kampanye nasionalisme"
    },
}


def politics_handlers(db):

    async def politics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            send = query.edit_message_text
        else:
            user_id = update.effective_user.id
            send = update.message.reply_text

        nation = db.get_nation(user_id)
        if not nation:
            await send("⚠️ Kamu belum punya negara. /start")
            return

        active = nation.get("active_policies", [])
        policy_list = ", ".join(active) if active else "Tidak ada"

        text = (
            f"🗳️ **PANEL POLITIK — {nation['name']}** 🗳️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ Pemerintahan: {nation['government_type'].title()}\n"
            f"👑 Gelar: {nation.get('leader_title', 'Presiden')}\n"
            f"👍 Approval Rating: {nation['approval_rating']}%\n"
            f"🕳️ Korupsi: {nation['corruption']}%\n"
            f"🗽 Kebebasan: {nation['freedom_index']}%\n"
            f"⚖️ Stabilitas: {nation['stability']}%\n\n"
            f"📋 Kebijakan aktif: {policy_list}\n"
        )

        keyboard = make_keyboard([
            ("📋 Buat Kebijakan", "pol_policies"),
            ("🗳️ Adakan Pemilu", "pol_election"),
            ("⚖️ Berantas Korupsi ($5000)", "pol_anti_corruption"),
            ("📢 Kampanye Propaganda ($2000)", "pol_propaganda"),
            ("🔄 Ganti Pemerintahan", "pol_change_gov"),
            ("🔙 Kembali", "menu_back"),
        ], columns=2)

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    async def show_policies(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        active = nation.get("active_policies", [])
        buttons = []
        for key, pol in POLICIES.items():
            status = "✅" if pol["name"] in active else ""
            buttons.append((
                f"{status}{pol['name']} (${format_number(pol['cost'])})",
                key
            ))
        buttons.append(("🔙 Kembali", "menu_politik"))

        await query.edit_message_text(
            "📋 **KEBIJAKAN TERSEDIA**\n\n"
            "Pilih kebijakan untuk diterapkan:\n"
            "(✅ = sudah aktif)",
            parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def apply_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        policy = POLICIES.get(query.data)
        if not policy:
            return

        active = nation.get("active_policies", [])
        if policy["name"] in active:
            await query.answer("⚠️ Kebijakan sudah aktif!", show_alert=True)
            return

        if nation["money"] < policy["cost"]:
            await query.answer(f"💸 Butuh ${format_number(policy['cost'])}!", show_alert=True)
            return

        # Apply effects
        updates = {"money": nation["money"] - policy["cost"]}
        effect_text = ""
        for key, val in policy["effects"].items():
            if key == "money_drain":
                continue
            if key in nation:
                if isinstance(nation[key], int):
                    new_val = nation[key] + val
                    if key in ("happiness", "health", "education", "corruption",
                               "freedom_index", "stability", "approval_rating",
                               "military_morale", "unemployment"):
                        new_val = clamp(new_val)
                    updates[key] = new_val
                    sign = "+" if val > 0 else ""
                    effect_text += f"  {key}: {sign}{val}\n"

        active.append(policy["name"])
        updates["active_policies"] = active
        db.update_nation(user_id, updates)

        await query.edit_message_text(
            f"✅ **Kebijakan Diterapkan!**\n\n"
            f"📋 {policy['name']}\n"
            f"📝 {policy['desc']}\n"
            f"💰 Biaya: -${format_number(policy['cost'])}\n\n"
            f"📊 **Efek:**\n{effect_text}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Politik", "menu_politik")])
        )

    async def hold_election(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        if nation["government_type"] not in ("demokrasi",):
            await query.answer("⚠️ Hanya negara demokrasi yang bisa mengadakan pemilu!", show_alert=True)
            return

        # Simulate election
        candidates = ["Partai Rakyat", "Partai Kemajuan", "Partai Persatuan", "Partai Reformasi"]
        results = {}
        for c in candidates:
            results[c] = random.randint(10, 40)

        total = sum(results.values())
        winner = max(results, key=results.get)

        text = f"🗳️ **HASIL PEMILU**\n━━━━━━━━━━━━━━━━━━\n\n"
        for c, votes in sorted(results.items(), key=lambda x: -x[1]):
            pct = votes / total * 100
            bar = "█" * int(pct / 5)
            win_mark = " 🏆" if c == winner else ""
            text += f"{c}: {pct:.1f}% {bar}{win_mark}\n"

        # Election effects
        approval_change = random.randint(-10, 15)
        stability_change = random.randint(-5, 10)
        db.update_nation(user_id, {
            "approval_rating": clamp(nation["approval_rating"] + approval_change),
            "stability": clamp(nation["stability"] + stability_change),
        })

        text += (
            f"\n🏆 **Pemenang: {winner}**\n"
            f"👍 Approval: {'+' if approval_change > 0 else ''}{approval_change}%\n"
            f"⚖️ Stabilitas: {'+' if stability_change > 0 else ''}{stability_change}%"
        )

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Politik", "menu_politik")])
        )

    async def change_government(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        keyboard = make_keyboard([
            ("🗳️ Demokrasi", "gov_demokrasi"),
            ("👑 Monarki", "gov_monarki"),
            ("☭ Komunis", "gov_komunis"),
            ("⚔️ Junta Militer", "gov_militer"),
            ("🕌 Teokrasi", "gov_teokrasi"),
            ("🔙 Kembali", "menu_politik"),
        ], columns=2)

        await query.edit_message_text(
            "🔄 **GANTI PEMERINTAHAN**\n\n"
            "⚠️ Mengganti pemerintahan akan:\n"
            "• Menurunkan stabilitas -20\n"
            "• Mengubah statistik dasar\n"
            "• Risiko pemberontakan!\n\n"
            "Pilih bentuk pemerintahan baru:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    async def set_government(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        from utils.helpers import IDEOLOGY_MAP
        gov = query.data.replace("gov_", "")

        if gov == nation["government_type"]:
            await query.answer("⚠️ Sudah menggunakan pemerintahan ini!", show_alert=True)
            return

        # Revolution chance
        revolt_chance = 0.3
        if random.random() < revolt_chance:
            damage = random.randint(1000, 5000)
            pop_loss = random.randint(1000, 10000)
            db.update_nation(user_id, {
                "money": max(0, nation["money"] - damage),
                "population": max(10000, nation["population"] - pop_loss),
                "stability": clamp(nation["stability"] - 30),
            })
            await query.edit_message_text(
                f"💥 **PEMBERONTAKAN!**\n\n"
                f"Rakyat tidak setuju dengan perubahan!\n"
                f"💰 Kerugian: -${format_number(damage)}\n"
                f"👥 Korban: -{format_number(pop_loss)} jiwa\n"
                f"⚖️ Stabilitas: -30%\n\n"
                f"Pemerintahan tetap {nation['government_type'].title()}.",
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Panel Politik", "menu_politik")])
            )
            return

        updates = {
            "government_type": gov,
            "stability": clamp(nation["stability"] - 20),
        }
        if gov in IDEOLOGY_MAP:
            updates.update(IDEOLOGY_MAP[gov])

        db.update_nation(user_id, updates)
        db.log_event("gov_change", user_id, f"{nation['name']} berubah menjadi {gov.title()}")

        await query.edit_message_text(
            f"🔄 **PEMERINTAHAN BERUBAH!**\n\n"
            f"🏛️ Sekarang: {gov.title()}\n"
            f"⚖️ Stabilitas: -20%\n"
            f"Statistik disesuaikan dengan ideologi baru.",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Politik", "menu_politik")])
        )

    return [
        CommandHandler("politik", politics_menu),
        CallbackQueryHandler(politics_menu, pattern=r"^menu_politik$"),
        CallbackQueryHandler(show_policies, pattern=r"^pol_policies$"),
        CallbackQueryHandler(apply_policy, pattern=r"^pol_(healthcare|education|military_service|anti_corruption|censorship|welfare|open_border|propaganda)$"),
        CallbackQueryHandler(hold_election, pattern=r"^pol_election$"),
        CallbackQueryHandler(change_government, pattern=r"^pol_change_gov$"),
        CallbackQueryHandler(set_government, pattern=r"^gov_"),
    ]
