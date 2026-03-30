import json
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


def admin_handlers(db, super_admin_id):

    def is_admin(user_id):
        return user_id == super_admin_id

    async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            send = query.edit_message_text
        else:
            user_id = update.effective_user.id
            send = update.message.reply_text

        if not is_admin(user_id):
            await send("⛔ Akses ditolak. Hanya Super Admin.")
            return

        nations = db.get_all_nations()
        wars = db.get_active_wars()
        groups = db.get_all_groups()
        game_active = db.get_setting("game_active", True)
        event_freq = db.get_setting("event_frequency", 3600)

        text = (
            f"👑 **SUPER ADMIN PANEL** 👑\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **Statistik Game:**\n"
            f"🏛️ Total Negara: {len(nations)}\n"
            f"⚔️ Perang Aktif: {len(wars)}\n"
            f"👥 Grup Terdaftar: {len(groups)}\n"
            f"🎮 Game Aktif: {'✅ Ya' if game_active else '❌ Tidak'}\n"
            f"⏱️ Frekuensi Event: {event_freq}s\n"
        )

        keyboard = make_keyboard([
            ("🏛️ Kelola Negara", "adm_nations"),
            ("⚔️ Kelola Perang", "adm_wars"),
            ("📰 Trigger Event Manual", "adm_event"),
            ("💰 Beri Resource", "adm_give"),
            ("🔧 Setting Game", "adm_settings"),
            ("📢 Broadcast Pesan", "adm_broadcast"),
            ("🗑️ Hapus Negara", "adm_delete"),
            ("📊 Export Data", "adm_export"),
            ("🔄 Reset Game", "adm_reset_confirm"),
        ], columns=2)

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    async def manage_nations(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        nations = db.get_all_nations()
        if not nations:
            await query.edit_message_text(
                "📭 Belum ada negara.",
                reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
            )
            return

        text = "🏛️ **SEMUA NEGARA**\n━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for n in nations:
            power = db.calc_power(n)
            war = "⚔️" if n.get("is_at_war") else ""
            text += (
                f"🏛️ **{n['name']}** {war}\n"
                f"  👤 ID: `{n['user_id']}`\n"
                f"  ⚡ Power: {format_number(power)} | 💰 ${format_number(n['money'])}\n"
                f"  👥 Pop: {format_number(n['population'])} | 😊 {n['happiness']}%\n\n"
            )
            buttons.append((f"✏️ {n['name']}", f"adm_edit_{n['user_id']}"))

        buttons.append(("🔙 Admin", "menu_admin"))

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=2)
        )

    async def edit_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        target_id = int(query.data.replace("adm_edit_", ""))
        nation = db.get_nation(target_id)
        if not nation:
            return

        text = (
            f"✏️ **EDIT: {nation['name']}**\n"
            f"ID: `{nation['user_id']}`\n\n"
            f"Pilih aksi untuk negara ini:"
        )

        buttons = [
            ("💰 +$10,000", f"adm_add_money_{target_id}"),
            ("💰 -$10,000", f"adm_rem_money_{target_id}"),
            ("🪖 +5,000 Tentara", f"adm_add_soldiers_{target_id}"),
            ("👥 +50,000 Populasi", f"adm_add_pop_{target_id}"),
            ("😊 +20 Happiness", f"adm_add_happy_{target_id}"),
            ("😡 -20 Happiness", f"adm_rem_happy_{target_id}"),
            ("☢️ +1 Nuklir", f"adm_add_nuke_{target_id}"),
            ("⚖️ +20 Stabilitas", f"adm_add_stab_{target_id}"),
            ("🗑️ Hapus Negara", f"adm_del_{target_id}"),
            ("🔙 Daftar Negara", "adm_nations"),
        ]

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=2)
        )

    async def admin_modify(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        data = query.data

        modifications = {
            "adm_add_money_": ("money", 10000, "💰 +$10,000"),
            "adm_rem_money_": ("money", -10000, "💰 -$10,000"),
            "adm_add_soldiers_": ("soldiers", 5000, "🪖 +5,000 Tentara"),
            "adm_add_pop_": ("population", 50000, "👥 +50,000 Populasi"),
            "adm_add_happy_": ("happiness", 20, "😊 +20 Happiness"),
            "adm_rem_happy_": ("happiness", -20, "😡 -20 Happiness"),
            "adm_add_nuke_": ("nukes", 1, "☢️ +1 Nuklir"),
            "adm_add_stab_": ("stability", 20, "⚖️ +20 Stabilitas"),
        }

        for prefix, (field, amount, desc) in modifications.items():
            if data.startswith(prefix):
                target_id = int(data.replace(prefix, ""))
                nation = db.get_nation(target_id)
                if not nation:
                    return

                new_val = nation[field] + amount
                if field in ("happiness", "stability", "approval_rating", "corruption"):
                    new_val = clamp(new_val)
                else:
                    new_val = max(0, new_val)

                db.update_nation(target_id, {field: new_val})

                await query.edit_message_text(
                    f"✅ **Modifikasi Berhasil!**\n\n"
                    f"🏛️ {nation['name']}\n"
                    f"📝 {desc}\n"
                    f"📊 {field}: {nation[field]} → {new_val}",
                    parse_mode="Markdown",
                    reply_markup=make_keyboard([
                        (f"✏️ Edit Lagi", f"adm_edit_{target_id}"),
                        ("🔙 Admin", "menu_admin"),
                    ])
                )
                return

    async def delete_nation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        target_id = int(query.data.replace("adm_del_", ""))
        nation = db.get_nation(target_id)
        if not nation:
            return

        await query.edit_message_text(
            f"⚠️ **Hapus {nation['name']}?**\n\n"
            f"Tindakan ini tidak bisa dibatalkan!",
            parse_mode="Markdown",
            reply_markup=make_keyboard([
                ("✅ Ya, Hapus!", f"adm_delconfirm_{target_id}"),
                ("❌ Batal", f"adm_edit_{target_id}"),
            ])
        )

    async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        target_id = int(query.data.replace("adm_delconfirm_", ""))
        nation = db.get_nation(target_id)
        name = nation["name"] if nation else "Unknown"
        db.delete_nation(target_id)

        await query.edit_message_text(
            f"🗑️ **Negara {name} telah dihapus!**",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
        )

    async def manage_wars(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        wars = db.get_active_wars()
        if not wars:
            await query.edit_message_text(
                "☮️ Tidak ada perang aktif.",
                reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
            )
            return

        text = "⚔️ **PERANG AKTIF**\n━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for w in wars:
            atk = db.get_nation(w["attacker_id"])
            defe = db.get_nation(w["defender_id"])
            atk_name = atk["name"] if atk else "?"
            def_name = defe["name"] if defe else "?"
            text += (
                f"⚔️ {atk_name} vs {def_name}\n"
                f"  Skor: {w['attacker_wins']}-{w['defender_wins']} (R{w['total_rounds']})\n\n"
            )
            buttons.append((f"🛑 Stop: {atk_name} vs {def_name}",
                            f"adm_stopwar_{w['attacker_id']}_{w['defender_id']}"))

        buttons.append(("🔙 Admin", "menu_admin"))
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def stop_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        parts = query.data.replace("adm_stopwar_", "").split("_")
        atk_id, def_id = int(parts[0]), int(parts[1])
        db.end_war(atk_id, def_id, 0)

        await query.edit_message_text(
            "🛑 **Perang dihentikan oleh Admin!**",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
        )

    async def trigger_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        from handlers.events import RANDOM_EVENTS, apply_event_effects
        import random

        nations = db.get_all_nations()
        if not nations:
            await query.answer("Tidak ada negara!", show_alert=True)
            return

        buttons = []
        for i, event in enumerate(RANDOM_EVENTS):
            type_emoji = {"disaster": "🔴", "crisis": "🟡", "bonus": "🟢"}.get(event["type"], "⚪")
            buttons.append((f"{type_emoji} {event['name']}", f"adm_evt_{i}"))
        buttons.append(("🎲 Random ke Semua", "adm_evt_random_all"))
        buttons.append(("🔙 Admin", "menu_admin"))

        await query.edit_message_text(
            "📰 **TRIGGER EVENT MANUAL**\n\nPilih event untuk ditrigger:",
            parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=2)
        )

    async def execute_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        from handlers.events import RANDOM_EVENTS, apply_event_effects
        import random

        nations = db.get_all_nations()

        if query.data == "adm_evt_random_all":
            results = []
            for nation in nations:
                event = random.choice(RANDOM_EVENTS)
                apply_event_effects(db, nation, event["effects"])
                db.log_event(event["type"], nation["user_id"], event["description"], event["effects"])
                results.append(f"🏛️ {nation['name']}: {event['name']}")

            await query.edit_message_text(
                "🎲 **EVENT RANDOM KE SEMUA!**\n\n" + "\n".join(results),
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
            )
            return

        event_idx = int(query.data.replace("adm_evt_", ""))
        event = RANDOM_EVENTS[event_idx]

        # Apply to random nation
        nation = random.choice(nations)
        apply_event_effects(db, nation, event["effects"])
        db.log_event(event["type"], nation["user_id"], event["description"], event["effects"])

        effect_text = ""
        for k, v in event["effects"].items():
            sign = "+" if v > 0 else ""
            effect_text += f"  {k}: {sign}{v}\n"

        await query.edit_message_text(
            f"📰 **EVENT TRIGGERED!**\n\n"
            f"🏛️ Target: {nation['name']}\n"
            f"📌 {event['name']}\n"
            f"📝 {event['description']}\n\n"
            f"📊 Efek:\n{effect_text}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([
                ("📰 Trigger Lagi", "adm_event"),
                ("🔙 Admin", "menu_admin"),
            ])
        )

    async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        game_active = db.get_setting("game_active", True)
        event_freq = db.get_setting("event_frequency", 3600)

        text = (
            f"🔧 **GAME SETTINGS**\n\n"
            f"🎮 Game Aktif: {'✅' if game_active else '❌'}\n"
            f"⏱️ Event Frequency: {event_freq}s ({event_freq//60} menit)\n"
        )

        keyboard = make_keyboard([
            (f"{'❌ Matikan' if game_active else '✅ Aktifkan'} Game", "adm_toggle_game"),
            ("⏱️ Event: 30 menit", "adm_freq_1800"),
            ("⏱️ Event: 1 jam", "adm_freq_3600"),
            ("⏱️ Event: 3 jam", "adm_freq_10800"),
            ("⏱️ Event: 6 jam", "adm_freq_21600"),
            ("🔙 Admin", "menu_admin"),
        ], columns=2)

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    async def toggle_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        current = db.get_setting("game_active", True)
        db.set_setting("game_active", not current)

        status = "AKTIF ✅" if not current else "NONAKTIF ❌"
        await query.edit_message_text(
            f"🎮 **Game sekarang {status}**",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Settings", "adm_settings")])
        )

    async def set_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        freq = int(query.data.replace("adm_freq_", ""))
        db.set_setting("event_frequency", freq)

        await query.edit_message_text(
            f"⏱️ **Event frequency: {freq}s ({freq//60} menit)**\n\n"
            f"⚠️ Restart bot untuk menerapkan perubahan.",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Settings", "adm_settings")])
        )

    async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text(
            "📢 **BROADCAST**\n\n"
            "Ketik pesan yang ingin dikirim ke semua pemain dan grup.\n"
            "Ketik /cancel untuk batal.",
            parse_mode="Markdown"
        )

    async def give_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        nations = db.get_all_nations()
        buttons = []
        for n in nations:
            buttons.append((f"🏛️ {n['name']}", f"adm_giveto_{n['user_id']}"))
        buttons.append(("💰 Semua Negara +$5000", "adm_giveall"))
        buttons.append(("🔙 Admin", "menu_admin"))

        await query.edit_message_text(
            "💰 **BERI RESOURCE**\n\nPilih negara target:",
            parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=2)
        )

    async def give_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        nations = db.get_all_nations()
        for n in nations:
            db.update_nation(n["user_id"], {"money": n["money"] + 5000})

        await query.edit_message_text(
            f"✅ **${format_number(5000)} diberikan ke {len(nations)} negara!**",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
        )

    async def reset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        await query.edit_message_text(
            "⚠️ **RESET SELURUH GAME?**\n\n"
            "Semua negara, perang, aliansi akan DIHAPUS!\n"
            "Tindakan ini TIDAK BISA dibatalkan!",
            parse_mode="Markdown",
            reply_markup=make_keyboard([
                ("🔴 YA, RESET!", "adm_reset_do"),
                ("❌ Batal", "menu_admin"),
            ])
        )

    async def do_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        db.nations.clear_cache()
        db.nations.truncate()
        db.wars.truncate()
        db.alliances.truncate()
        db.elections.truncate()
        db.events.truncate()
        db.trade_offers.truncate()

        await query.edit_message_text(
            "🔄 **GAME TELAH DI-RESET!**\n\n"
            "Semua data terhapus. Game dimulai dari awal.",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
        )

    async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not is_admin(query.from_user.id):
            return

        data = {
            "nations": db.get_all_nations(),
            "wars": db.wars.all(),
            "alliances": db.alliances.all(),
            "events": db.events.all()[-50:],
        }

        text = f"📊 **DATA EXPORT**\n\n```json\n{json.dumps(data, indent=2, default=str)[:3500]}\n```"
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Admin", "menu_admin")])
        )

    return [
        CommandHandler("admin", admin_menu),
        CallbackQueryHandler(admin_menu, pattern=r"^menu_admin$"),
        CallbackQueryHandler(manage_nations, pattern=r"^adm_nations$"),
        CallbackQueryHandler(edit_nation, pattern=r"^adm_edit_"),
        CallbackQueryHandler(admin_modify, pattern=r"^adm_(add|rem)_"),
        CallbackQueryHandler(delete_nation, pattern=r"^adm_del_\d+$"),
        CallbackQueryHandler(confirm_delete, pattern=r"^adm_delconfirm_"),
        CallbackQueryHandler(manage_wars, pattern=r"^adm_wars$"),
        CallbackQueryHandler(stop_war, pattern=r"^adm_stopwar_"),
        CallbackQueryHandler(trigger_event, pattern=r"^adm_event$"),
        CallbackQueryHandler(execute_event, pattern=r"^adm_evt_"),
        CallbackQueryHandler(admin_settings, pattern=r"^adm_settings$"),
        CallbackQueryHandler(toggle_game, pattern=r"^adm_toggle_game$"),
        CallbackQueryHandler(set_frequency, pattern=r"^adm_freq_"),
        CallbackQueryHandler(broadcast, pattern=r"^adm_broadcast$"),
        CallbackQueryHandler(give_resources, pattern=r"^adm_give$"),
        CallbackQueryHandler(give_all, pattern=r"^adm_giveall$"),
        CallbackQueryHandler(reset_confirm, pattern=r"^adm_reset_confirm$"),
        CallbackQueryHandler(do_reset, pattern=r"^adm_reset_do$"),
        CallbackQueryHandler(export_data, pattern=r"^adm_export$"),
    ]
