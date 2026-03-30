import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


def diplomacy_handlers(db):

    async def diplomacy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        alliance = db.get_user_alliance(user_id)
        alliance_name = alliance["name"] if alliance else "Tidak ada"
        allies = ", ".join([str(a) for a in nation.get("allies", [])]) or "Tidak ada"
        enemies = ", ".join([str(e) for e in nation.get("enemies", [])]) or "Tidak ada"

        text = (
            f"🤝 **PANEL DIPLOMASI — {nation['name']}** 🤝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌍 Reputasi: {nation['reputation']}%\n"
            f"🏛️ Aliansi: {alliance_name}\n"
            f"🤝 Sekutu: {allies}\n"
            f"💢 Musuh: {enemies}\n"
            f"🚫 Sanksi dari: {len(nation.get('sanctions_from', []))} negara\n"
            f"🚫 Sanksi ke: {len(nation.get('sanctions_to', []))} negara\n"
        )

        # Show other nations for interaction
        all_nations = db.get_all_nations()
        others = [n for n in all_nations if n["user_id"] != user_id]

        keyboard = make_keyboard([
            ("📋 Daftar Negara", "dip_list"),
            ("🏛️ Buat Aliansi", "dip_create_alliance"),
            ("🤝 Gabung Aliansi", "dip_join_alliance"),
            ("📦 Kirim Bantuan", "dip_send_aid"),
            ("🚫 Jatuhkan Sanksi", "dip_sanction"),
            ("📜 Tawaran Dagang", "dip_trade"),
            ("🔙 Kembali", "menu_back"),
        ], columns=2)

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    async def list_nations(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        all_nations = db.get_all_nations()
        others = [n for n in all_nations if n["user_id"] != user_id]

        if not others:
            await query.edit_message_text(
                "🌍 Belum ada negara lain yang terdaftar.",
                reply_markup=make_keyboard([("🔙 Kembali", "menu_diplomasi")])
            )
            return

        text = "🌍 **DAFTAR NEGARA**\n━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for n in others:
            power = db.calc_power(n)
            status = ""
            if n.get("is_at_war"):
                status = "⚔️"
            text += (
                f"🏛️ **{n['name']}** {status}\n"
                f"  ⚡ Power: {format_number(power)}\n"
                f"  👥 {format_number(n['population'])} | "
                f"🌍 Rep: {n['reputation']}%\n\n"
            )
            buttons.append((f"🔍 {n['name']}", f"dip_view_{n['user_id']}"))

        buttons.append(("🔙 Kembali", "menu_diplomasi"))

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def view_other_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_view_", ""))

        nation = db.get_nation(target_id)
        if not nation:
            await query.answer("Negara tidak ditemukan!", show_alert=True)
            return

        power = db.calc_power(nation)
        text = (
            f"🏛️ **{nation['name']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ {nation['government_type'].title()}\n"
            f"⚡ Power: {format_number(power)}\n"
            f"👥 Populasi: {format_number(nation['population'])}\n"
            f"🌍 Reputasi: {nation['reputation']}%\n"
            f"🪖 Tentara: {format_number(nation['soldiers'])}\n"
            f"☢️ Nuklir: {nation['nukes']}\n"
        )

        my_nation = db.get_nation(user_id)
        buttons = []
        if target_id not in my_nation.get("allies", []):
            buttons.append(("🤝 Tawarkan Aliansi", f"dip_ally_{target_id}"))
        if target_id not in my_nation.get("enemies", []):
            buttons.append(("💢 Jadikan Musuh", f"dip_enemy_{target_id}"))
        buttons.append(("📦 Kirim Bantuan $1000", f"dip_aid_{target_id}"))
        buttons.append(("🚫 Sanksi", f"dip_sanc_{target_id}"))
        buttons.append(("🔙 Daftar Negara", "dip_list"))

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=2)
        )

    async def ally_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_ally_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        allies = nation.get("allies", [])
        if target_id in allies:
            await query.answer("Sudah menjadi sekutu!", show_alert=True)
            return

        allies.append(target_id)
        db.update_nation(user_id, {"allies": allies})

        t_allies = target.get("allies", [])
        t_allies.append(user_id)
        db.update_nation(target_id, {"allies": t_allies})

        # Remove from enemies if applicable
        enemies = nation.get("enemies", [])
        if target_id in enemies:
            enemies.remove(target_id)
            db.update_nation(user_id, {"enemies": enemies})

        db.log_event("alliance", user_id, f"{nation['name']} dan {target['name']} menjadi sekutu!")

        await query.edit_message_text(
            f"🤝 **ALIANSI TERBENTUK!**\n\n"
            f"🏛️ {nation['name']} 🤝 {target['name']}\n"
            f"Kedua negara kini menjadi sekutu!",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
        )

    async def enemy_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_enemy_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        enemies = nation.get("enemies", [])
        enemies.append(target_id)
        db.update_nation(user_id, {"enemies": enemies})

        # Remove from allies
        allies = nation.get("allies", [])
        if target_id in allies:
            allies.remove(target_id)
            db.update_nation(user_id, {"allies": allies})

        db.update_nation(user_id, {"reputation": clamp(nation["reputation"] - 5, 0, 100)})

        await query.edit_message_text(
            f"💢 **HUBUNGAN MEMBURUK!**\n\n"
            f"🏛️ {nation['name']} menyatakan {target['name']} sebagai musuh!\n"
            f"🌍 Reputasi: -5",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
        )

    async def send_aid(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_aid_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        aid_amount = 1000
        if nation["money"] < aid_amount:
            await query.answer("💸 Uang tidak cukup!", show_alert=True)
            return

        db.update_nation(user_id, {
            "money": nation["money"] - aid_amount,
            "reputation": clamp(nation["reputation"] + 5, 0, 100),
        })
        db.update_nation(target_id, {"money": target["money"] + aid_amount})

        db.log_event("aid", user_id, f"{nation['name']} mengirim bantuan ${aid_amount} ke {target['name']}")

        await query.edit_message_text(
            f"📦 **BANTUAN TERKIRIM!**\n\n"
            f"🏛️ {nation['name']} → {target['name']}\n"
            f"💰 Jumlah: ${format_number(aid_amount)}\n"
            f"🌍 Reputasi: +5",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
        )

    async def sanction_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_sanc_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        sanctions_to = nation.get("sanctions_to", [])
        if target_id in sanctions_to:
            await query.answer("Sudah memberikan sanksi!", show_alert=True)
            return

        sanctions_to.append(target_id)
        db.update_nation(user_id, {"sanctions_to": sanctions_to})

        sanctions_from = target.get("sanctions_from", [])
        sanctions_from.append(user_id)
        db.update_nation(target_id, {
            "sanctions_from": sanctions_from,
            "trade_income": max(0, target.get("trade_income", 0) - 200),
        })

        db.log_event("sanction", user_id, f"{nation['name']} menjatuhkan sanksi ke {target['name']}")

        await query.edit_message_text(
            f"🚫 **SANKSI DIJATUHKAN!**\n\n"
            f"🏛️ {nation['name']} → {target['name']}\n"
            f"📉 Pendapatan dagang target: -200/siklus",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
        )

    async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        if db.get_user_alliance(user_id):
            await query.answer("⚠️ Kamu sudah dalam aliansi!", show_alert=True)
            return

        alliance_name = f"Aliansi {nation['name']}"
        result = db.create_alliance(alliance_name, user_id)
        if result:
            await query.edit_message_text(
                f"🏛️ **ALIANSI DIBENTUK!**\n\n"
                f"📛 Nama: {alliance_name}\n"
                f"👑 Pendiri: {nation['name']}\n\n"
                f"Negara lain bisa bergabung melalui menu diplomasi.",
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
            )
        else:
            await query.answer("Gagal membuat aliansi!", show_alert=True)

    async def join_alliance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if db.get_user_alliance(user_id):
            await query.answer("⚠️ Kamu sudah dalam aliansi!", show_alert=True)
            return

        alliances = db.alliances.all()
        if not alliances:
            await query.edit_message_text(
                "📭 Belum ada aliansi yang dibuat.",
                reply_markup=make_keyboard([("🔙 Kembali", "menu_diplomasi")])
            )
            return

        buttons = []
        text = "🏛️ **ALIANSI TERSEDIA**\n━━━━━━━━━━━━━━━━\n\n"
        for a in alliances:
            text += f"📛 **{a['name']}** — {len(a['members'])} anggota\n"
            buttons.append((f"Gabung {a['name']}", f"dip_jaliance_{a['name']}"))

        buttons.append(("🔙 Kembali", "menu_diplomasi"))

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        from utils.helpers import nation_summary
        text = nation_summary(nation, db)
        keyboard = make_keyboard([
            ("💰 Ekonomi", "menu_ekonomi"),
            ("⚔️ Militer", "menu_militer"),
            ("🗳️ Politik", "menu_politik"),
            ("🤝 Diplomasi", "menu_diplomasi"),
            ("💥 Perang", "menu_perang"),
            ("📰 Event", "menu_event"),
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    return [
        CommandHandler("diplomasi", diplomacy_menu),
        CallbackQueryHandler(diplomacy_menu, pattern=r"^menu_diplomasi$"),
        CallbackQueryHandler(list_nations, pattern=r"^dip_list$"),
        CallbackQueryHandler(view_other_nation, pattern=r"^dip_view_"),
        CallbackQueryHandler(ally_nation, pattern=r"^dip_ally_"),
        CallbackQueryHandler(enemy_nation, pattern=r"^dip_enemy_"),
        CallbackQueryHandler(send_aid, pattern=r"^dip_aid_"),
        CallbackQueryHandler(sanction_nation, pattern=r"^dip_sanc_"),
        CallbackQueryHandler(create_alliance, pattern=r"^dip_create_alliance$"),
        CallbackQueryHandler(join_alliance_menu, pattern=r"^dip_join_alliance$"),
        CallbackQueryHandler(menu_back, pattern=r"^menu_back$"),
    ]
