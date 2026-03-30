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

        ally_names = []
        for a_id in nation.get("allies", []):
            a = db.get_nation(a_id)
            if a:
                ally_names.append(a["name"])
        allies_text = ", ".join(ally_names) if ally_names else "Tidak ada"

        enemy_names = []
        for e_id in nation.get("enemies", []):
            e = db.get_nation(e_id)
            if e:
                enemy_names.append(e["name"])
        enemies_text = ", ".join(enemy_names) if enemy_names else "Tidak ada"

        text = (
            f"🤝 **PANEL DIPLOMASI — {nation['name']}** 🤝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌍 Reputasi: {nation['reputation']}%\n"
            f"🏛️ Aliansi: {alliance_name}\n"
            f"🤝 Sekutu: {allies_text}\n"
            f"💢 Musuh: {enemies_text}\n"
            f"🚫 Sanksi dari: {len(nation.get('sanctions_from', []))} negara\n"
            f"🚫 Sanksi ke: {len(nation.get('sanctions_to', []))} negara\n"
        )

        keyboard = make_keyboard([
            ("📋 Daftar Negara", "dip_list"),
            ("🏛️ Buat Aliansi", "dip_create_alliance"),
            ("🤝 Gabung Aliansi", "dip_join_alliance"),
            ("📦 Kirim Bantuan", "dip_send_aid_menu"),
            ("🚫 Jatuhkan Sanksi", "dip_sanction_menu"),
            ("📜 Perdagangan", "dip_trade_menu"),
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
            status = " ⚔️" if n.get("is_at_war") else ""
            text += (
                f"🏛️ **{n['name']}** {status}\n"
                f"  ⚡ Power: {format_number(power)} | 🌍 Rep: {n['reputation']}%\n\n"
            )
            buttons.append((f"🔍 {n['name']}", f"dip_view_{n['user_id']}"))

        buttons.append(("🔙 Kembali", "menu_diplomasi"))
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=1))

    async def view_other_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_view_", ""))

        nation = db.get_nation(target_id)
        if not nation:
            await query.answer("Negara tidak ditemukan!", show_alert=True)
            return

        my_nation = db.get_nation(user_id)
        power = db.calc_power(nation)
        text = (
            f"🏛️ **{nation['name']}**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ {nation['government_type'].title()}\n"
            f"⚡ Power: {format_number(power)}\n"
            f"👥 Populasi: {format_number(nation['population'])}\n"
            f"🌍 Reputasi: {nation['reputation']}%\n"
            f"🪖 Tentara: {format_number(nation['soldiers'])}\n"
            f"☢️ Nuklir: {nation['nukes']}\n"
        )

        buttons = []
        if my_nation:
            if target_id not in my_nation.get("allies", []):
                buttons.append(("🤝 Jadikan Sekutu", f"dip_ally_{target_id}"))
            if target_id not in my_nation.get("enemies", []):
                buttons.append(("💢 Jadikan Musuh", f"dip_enemy_{target_id}"))
            buttons.append(("📦 Kirim Bantuan $1000", f"dip_aid_{target_id}"))
            buttons.append(("🚫 Sanksi", f"dip_sanc_{target_id}"))
            buttons.append(("📜 Tawarkan Dagang", f"dip_trade_{target_id}"))
        buttons.append(("🔙 Daftar Negara", "dip_list"))

        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=2))

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
        if target_id in enemies:
            await query.answer("Sudah menjadi musuh!", show_alert=True)
            return
        enemies.append(target_id)
        db.update_nation(user_id, {"enemies": enemies})

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

    async def send_aid_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        others = [n for n in db.get_all_nations() if n["user_id"] != user_id]
        if not others:
            await query.edit_message_text("🌍 Tidak ada negara lain.",
                                           reply_markup=make_keyboard([("🔙 Kembali", "menu_diplomasi")]))
            return

        buttons = [(f"📦 {n['name']}", f"dip_aid_{n['user_id']}") for n in others]
        buttons.append(("🔙 Kembali", "menu_diplomasi"))
        await query.edit_message_text("📦 **Pilih negara untuk bantuan ($1000):**",
                                       parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=1))

    async def sanction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        others = [n for n in db.get_all_nations() if n["user_id"] != user_id]
        if not others:
            await query.edit_message_text("🌍 Tidak ada negara lain.",
                                           reply_markup=make_keyboard([("🔙 Kembali", "menu_diplomasi")]))
            return

        buttons = [(f"🚫 {n['name']}", f"dip_sanc_{n['user_id']}") for n in others]
        buttons.append(("🔙 Kembali", "menu_diplomasi"))
        await query.edit_message_text("🚫 **Pilih negara untuk sanksi:**",
                                       parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=1))

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

    async def trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        others = [n for n in db.get_all_nations() if n["user_id"] != user_id]
        if not others:
            await query.edit_message_text("🌍 Tidak ada negara lain.",
                                           reply_markup=make_keyboard([("🔙 Kembali", "menu_diplomasi")]))
            return

        # Show pending trades
        pending = db.get_pending_trades(user_id)
        text = "📜 **PERDAGANGAN**\n━━━━━━━━━━━━━━━━━━\n\n"

        if pending:
            text += "📥 **Tawaran masuk:**\n"
            for t in pending:
                sender = db.get_nation(t["from_id"])
                sender_name = sender["name"] if sender else "?"
                text += f"  🏛️ {sender_name}: {t['offer']} ↔ {t['request']}\n"
            text += "\n"

        text += "Pilih negara untuk berdagang:"

        buttons = [(f"📜 {n['name']}", f"dip_trade_{n['user_id']}") for n in others]
        buttons.append(("🔙 Kembali", "menu_diplomasi"))
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=1))

    async def trade_with(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("dip_trade_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        buttons = [
            ("💰 $2000 → 🍚 1000 Food", f"dip_dotrade_money2food_{target_id}"),
            ("🍚 2000 Food → 💰 $1500", f"dip_dotrade_food2money_{target_id}"),
            ("💰 $3000 → 🛢️ 500 Oil", f"dip_dotrade_money2oil_{target_id}"),
            ("🪨 2000 Mat → 💰 $2000", f"dip_dotrade_mat2money_{target_id}"),
            ("🔙 Kembali", "dip_trade_menu"),
        ]

        await query.edit_message_text(
            f"📜 **Dagang dengan {target['name']}**\n\n"
            f"Pilih jenis pertukaran:",
            parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        # Parse: dip_dotrade_{type}_{target_id}
        parts = query.data.replace("dip_dotrade_", "").rsplit("_", 1)
        trade_type = parts[0]
        target_id = int(parts[1])

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        trades = {
            "money2food": {"give": ("money", 2000), "get": ("food", 1000), "target_give": ("food", 1000), "target_get": ("money", 2000)},
            "food2money": {"give": ("food", 2000), "get": ("money", 1500), "target_give": ("money", 1500), "target_get": ("food", 2000)},
            "money2oil": {"give": ("money", 3000), "get": ("oil", 500), "target_give": ("oil", 500), "target_get": ("money", 3000)},
            "mat2money": {"give": ("materials", 2000), "get": ("money", 2000), "target_give": ("money", 2000), "target_get": ("materials", 2000)},
        }

        trade = trades.get(trade_type)
        if not trade:
            return

        give_res, give_amt = trade["give"]
        get_res, get_amt = trade["get"]
        tg_res, tg_amt = trade["target_give"]
        tgt_res, tgt_amt = trade["target_get"]

        if nation.get(give_res, 0) < give_amt:
            await query.answer(f"💸 {give_res} tidak cukup! Butuh {give_amt}", show_alert=True)
            return
        if target.get(tg_res, 0) < tg_amt:
            await query.answer(f"⚠️ {target['name']} tidak punya cukup {tg_res}!", show_alert=True)
            return

        db.update_nation(user_id, {
            give_res: nation[give_res] - give_amt,
            get_res: nation.get(get_res, 0) + get_amt,
        })
        db.update_nation(target_id, {
            tg_res: target[tg_res] - tg_amt,
            tgt_res: target.get(tgt_res, 0) + tgt_amt,
        })

        db.log_event("trade", user_id, f"{nation['name']} berdagang dengan {target['name']}")

        await query.edit_message_text(
            f"📜 **PERDAGANGAN BERHASIL!**\n\n"
            f"🏛️ {nation['name']} ↔ {target['name']}\n\n"
            f"📤 Kamu kirim: {give_amt} {give_res}\n"
            f"📥 Kamu dapat: {get_amt} {get_res}",
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
            safe_name = str(hash(a['name']) % 100000)
            buttons.append((f"Gabung {a['name'][:20]}", f"dip_joinal_{safe_name}"))
            # Store mapping
            context.user_data[f"alliance_{safe_name}"] = a['name']

        buttons.append(("🔙 Kembali", "menu_diplomasi"))
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=make_keyboard(buttons, columns=1))

    async def join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        safe_name = query.data.replace("dip_joinal_", "")
        alliance_name = context.user_data.get(f"alliance_{safe_name}")
        if not alliance_name:
            await query.answer("Aliansi tidak ditemukan!", show_alert=True)
            return

        success = db.join_alliance(alliance_name, user_id)
        nation = db.get_nation(user_id)
        name = nation["name"] if nation else "?"

        if success:
            await query.edit_message_text(
                f"🤝 **Bergabung ke {alliance_name}!**\n\n"
                f"🏛️ {name} kini anggota aliansi.",
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Diplomasi", "menu_diplomasi")])
            )
        else:
            await query.answer("Gagal bergabung!", show_alert=True)

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
        CallbackQueryHandler(view_other_nation, pattern=r"^dip_view_\d+$"),
        CallbackQueryHandler(ally_nation, pattern=r"^dip_ally_\d+$"),
        CallbackQueryHandler(enemy_nation, pattern=r"^dip_enemy_\d+$"),
        CallbackQueryHandler(send_aid, pattern=r"^dip_aid_\d+$"),
        CallbackQueryHandler(send_aid_menu, pattern=r"^dip_send_aid_menu$"),
        CallbackQueryHandler(sanction_menu, pattern=r"^dip_sanction_menu$"),
        CallbackQueryHandler(sanction_nation, pattern=r"^dip_sanc_\d+$"),
        CallbackQueryHandler(trade_menu, pattern=r"^dip_trade_menu$"),
        CallbackQueryHandler(trade_with, pattern=r"^dip_trade_\d+$"),
        CallbackQueryHandler(execute_trade, pattern=r"^dip_dotrade_"),
        CallbackQueryHandler(create_alliance, pattern=r"^dip_create_alliance$"),
        CallbackQueryHandler(join_alliance_menu, pattern=r"^dip_join_alliance$"),
        CallbackQueryHandler(join_alliance, pattern=r"^dip_joinal_"),
        CallbackQueryHandler(menu_back, pattern=r"^menu_back$"),
    ]
