import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


def military_handlers(db):

    async def military_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        text = (
            f"⚔️ **PANEL MILITER — {nation['name']}** ⚔️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🪖 Tentara: {format_number(nation['soldiers'])}\n"
            f"🚜 Tank: {format_number(nation['tanks'])}\n"
            f"✈️ Jet Tempur: {format_number(nation['jets'])}\n"
            f"🚢 Kapal Perang: {format_number(nation['ships'])}\n"
            f"🚀 Rudal: {format_number(nation['missiles'])}\n"
            f"☢️ Nuklir: {format_number(nation['nukes'])}\n\n"
            f"🛡️ Pertahanan: Lv.{nation['defense_level']}\n"
            f"🔬 Teknologi Militer: Lv.{nation['military_tech']}\n"
            f"💪 Moral Tentara: {nation['military_morale']}%\n"
        )

        keyboard = make_keyboard([
            ("🪖 Rekrut 500 Tentara ($500)", "mil_recruit"),
            ("🚜 Beli 5 Tank ($3000)", "mil_tank"),
            ("✈️ Beli 2 Jet ($5000)", "mil_jet"),
            ("🚢 Beli 1 Kapal ($8000)", "mil_ship"),
            ("🚀 Beli 3 Rudal ($10000)", "mil_missile"),
            ("🛡️ Upgrade Pertahanan ($7000)", "mil_defense"),
            ("🔬 Upgrade Tech Militer ($6000)", "mil_tech"),
            ("☢️ Riset Nuklir ($50000)", "mil_nuke"),
            ("💪 Tingkatkan Moral ($2000)", "mil_morale"),
            ("🔙 Kembali", "menu_back"),
        ], columns=2)

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    async def military_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        actions = {
            "mil_recruit": {
                "cost": 500, "field": "soldiers", "amount": 500,
                "name": "Tentara", "emoji": "🪖"
            },
            "mil_tank": {
                "cost": 3000, "field": "tanks", "amount": 5,
                "name": "Tank", "emoji": "🚜"
            },
            "mil_jet": {
                "cost": 5000, "field": "jets", "amount": 2,
                "name": "Jet Tempur", "emoji": "✈️"
            },
            "mil_ship": {
                "cost": 8000, "field": "ships", "amount": 1,
                "name": "Kapal Perang", "emoji": "🚢"
            },
            "mil_missile": {
                "cost": 10000, "field": "missiles", "amount": 3,
                "name": "Rudal", "emoji": "🚀"
            },
            "mil_defense": {
                "cost": 7000, "field": "defense_level", "amount": 1,
                "name": "Pertahanan", "emoji": "🛡️"
            },
            "mil_tech": {
                "cost": 6000, "field": "military_tech", "amount": 1,
                "name": "Tech Militer", "emoji": "🔬"
            },
            "mil_morale": {
                "cost": 2000, "field": "military_morale", "amount": 10,
                "name": "Moral Tentara", "emoji": "💪", "max": 100
            },
        }

        action = actions.get(query.data)
        if not action:
            return

        if nation["money"] < action["cost"]:
            await query.answer(
                f"💸 Butuh ${format_number(action['cost'])}!", show_alert=True
            )
            return

        new_val = nation[action["field"]] + action["amount"]
        if "max" in action:
            new_val = min(new_val, action["max"])

        db.update_nation(user_id, {
            "money": nation["money"] - action["cost"],
            action["field"]: new_val,
        })

        await query.edit_message_text(
            f"{action['emoji']} **{action['name']} ditambah!**\n\n"
            f"📦 {action['name']}: {format_number(nation[action['field']])} → {format_number(new_val)}\n"
            f"💰 Biaya: -${format_number(action['cost'])}\n"
            f"💰 Sisa: ${format_number(nation['money'] - action['cost'])}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Militer", "menu_militer")])
        )

    async def nuke_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        cost = 50000
        if nation["money"] < cost:
            await query.answer(f"💸 Butuh ${format_number(cost)}!", show_alert=True)
            return

        if nation["military_tech"] < 5:
            await query.answer(
                "⚠️ Butuh Tech Militer minimal Lv.5!", show_alert=True
            )
            return

        success = random.random() < 0.6  # 60% chance
        db.update_nation(user_id, {"money": nation["money"] - cost})

        if success:
            db.update_nation(user_id, {"nukes": nation["nukes"] + 1})
            db.log_event(
                "nuke_developed", user_id,
                f"☢️ {nation['name']} berhasil mengembangkan senjata nuklir!",
                {"reputation_change": -10}
            )
            # Decrease reputation globally
            db.update_nation(user_id, {
                "reputation": clamp(nation["reputation"] - 10, 0, 100)
            })

            await query.edit_message_text(
                f"☢️ **RISET NUKLIR BERHASIL!**\n\n"
                f"Negara {nation['name']} kini memiliki {nation['nukes'] + 1} senjata nuklir.\n"
                f"⚠️ Reputasi internasional menurun -10\n"
                f"💰 Biaya: ${format_number(cost)}",
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Panel Militer", "menu_militer")])
            )
        else:
            await query.edit_message_text(
                f"💥 **RISET NUKLIR GAGAL!**\n\n"
                f"Riset tidak membuahkan hasil kali ini.\n"
                f"💰 Biaya tetap: -${format_number(cost)}\n"
                f"Coba lagi nanti!",
                parse_mode="Markdown",
                reply_markup=make_keyboard([("🔙 Panel Militer", "menu_militer")])
            )

    return [
        CommandHandler("militer", military_menu),
        CallbackQueryHandler(military_menu, pattern=r"^menu_militer$"),
        CallbackQueryHandler(nuke_research, pattern=r"^mil_nuke$"),
        CallbackQueryHandler(military_action, pattern=r"^mil_(recruit|tank|jet|ship|missile|defense|tech|morale)$"),
    ]
