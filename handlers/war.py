import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp


def calculate_battle(attacker, defender):
    """Simulate a battle and return results."""
    # Attack power
    atk_power = (
        attacker["soldiers"] * 1 * (attacker["military_morale"] / 100)
        + attacker["tanks"] * 50
        + attacker["jets"] * 100
        + attacker["ships"] * 80
        + attacker["missiles"] * 200
    ) * (attacker["military_tech"] * 0.3 + 0.7)

    # Defense power
    def_power = (
        defender["soldiers"] * 1 * (defender["military_morale"] / 100)
        + defender["tanks"] * 50
        + defender["jets"] * 100
        + defender["ships"] * 80
        + defender["missiles"] * 200
    ) * (defender["military_tech"] * 0.3 + 0.7) * (1 + defender["defense_level"] * 0.15)

    # Random factor
    atk_power *= random.uniform(0.8, 1.2)
    def_power *= random.uniform(0.8, 1.2)

    attacker_wins = atk_power > def_power
    ratio = atk_power / max(def_power, 1)

    # Casualties
    if attacker_wins:
        atk_losses = random.uniform(0.05, 0.15)
        def_losses = random.uniform(0.15, 0.30)
    else:
        atk_losses = random.uniform(0.15, 0.30)
        def_losses = random.uniform(0.05, 0.15)

    return {
        "winner": "attacker" if attacker_wins else "defender",
        "atk_power": int(atk_power),
        "def_power": int(def_power),
        "atk_soldier_loss": int(attacker["soldiers"] * atk_losses),
        "atk_tank_loss": int(attacker["tanks"] * atk_losses * 0.5),
        "atk_jet_loss": int(attacker["jets"] * atk_losses * 0.3),
        "def_soldier_loss": int(defender["soldiers"] * def_losses),
        "def_tank_loss": int(defender["tanks"] * def_losses * 0.5),
        "def_jet_loss": int(defender["jets"] * def_losses * 0.3),
        "money_stolen": int(defender["money"] * 0.1) if attacker_wins else 0,
    }


def war_handlers(db):

    async def war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        active_wars = db.get_active_wars(user_id)
        war_text = ""
        if active_wars:
            war_text = "\n⚔️ **Perang Aktif:**\n"
            for w in active_wars:
                opponent_id = w["defender_id"] if w["attacker_id"] == user_id else w["attacker_id"]
                opponent = db.get_nation(opponent_id)
                opp_name = opponent["name"] if opponent else "Unknown"
                role = "Penyerang" if w["attacker_id"] == user_id else "Bertahan"
                war_text += f"  ⚔️ vs {opp_name} ({role}) — R{w['total_rounds']}\n"
                war_text += f"    Skor: {w['attacker_wins']}-{w['defender_wins']}\n"

        text = (
            f"💥 **PANEL PERANG — {nation['name']}** 💥\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🪖 Tentara: {format_number(nation['soldiers'])}\n"
            f"🚜 Tank: {format_number(nation['tanks'])}\n"
            f"✈️ Jet: {format_number(nation['jets'])}\n"
            f"💪 Moral: {nation['military_morale']}%\n"
            f"😰 War Weariness: {nation.get('war_weariness', 0)}%\n"
            f"{war_text}"
        )

        buttons = [("⚔️ Serang Negara Lain", "war_target_list")]
        if active_wars:
            buttons.append(("🗡️ Lanjut Pertempuran", "war_battle"))
            buttons.append(("🏳️ Menyerah", "war_surrender"))
        if nation["nukes"] > 0:
            buttons.append(("☢️ Luncurkan Nuklir!", "war_nuke_target"))
        buttons.append(("🔙 Kembali", "menu_back"))

        await send(text, parse_mode="Markdown", reply_markup=make_keyboard(buttons, columns=2))

    async def target_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)

        if nation.get("is_at_war"):
            await query.answer("⚠️ Kamu sudah dalam perang!", show_alert=True)
            return

        all_nations = db.get_all_nations()
        others = [n for n in all_nations if n["user_id"] != user_id]

        if not others:
            await query.edit_message_text(
                "🌍 Tidak ada negara lain untuk diserang.",
                reply_markup=make_keyboard([("🔙 Kembali", "menu_perang")])
            )
            return

        buttons = []
        text = "⚔️ **PILIH TARGET SERANGAN**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for n in others:
            if n.get("is_at_war"):
                continue
            power = db.calc_power(n)
            text += f"🏛️ **{n['name']}** — ⚡{format_number(power)}\n"
            buttons.append((f"⚔️ {n['name']}", f"war_declare_{n['user_id']}"))

        buttons.append(("🔙 Kembali", "menu_perang"))

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons, columns=1)
        )

    async def declare_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("war_declare_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        if nation.get("is_at_war"):
            await query.answer("⚠️ Sudah dalam perang!", show_alert=True)
            return

        # Check if target is ally
        if target_id in nation.get("allies", []):
            await query.edit_message_text(
                f"⚠️ **{target['name']} adalah sekutu kamu!**\n\n"
                f"Apakah kamu yakin ingin mengkhianati sekutu?",
                parse_mode="Markdown",
                reply_markup=make_keyboard([
                    ("⚔️ Ya, Serang!", f"war_confirm_{target_id}"),
                    ("🔙 Batal", "menu_perang"),
                ])
            )
            return

        await _start_war(query, db, user_id, target_id, nation, target)

    async def confirm_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_id = int(query.data.replace("war_confirm_", ""))

        nation = db.get_nation(user_id)
        target = db.get_nation(target_id)
        if not nation or not target:
            return

        # Remove from allies (betrayal)
        allies = nation.get("allies", [])
        if target_id in allies:
            allies.remove(target_id)
            db.update_nation(user_id, {
                "allies": allies,
                "reputation": clamp(nation["reputation"] - 20, 0, 100)
            })
            t_allies = target.get("allies", [])
            if user_id in t_allies:
                t_allies.remove(user_id)
                db.update_nation(target_id, {"allies": t_allies})

        await _start_war(query, db, user_id, target_id, nation, target)

    async def _start_war(query, db, user_id, target_id, nation, target):
        war_name = f"Perang {nation['name']} vs {target['name']}"
        db.create_war(user_id, target_id, war_name)
        db.log_event("war_declared", user_id, f"⚔️ {war_name} telah dimulai!")

        # Add to enemies
        enemies = nation.get("enemies", [])
        if target_id not in enemies:
            enemies.append(target_id)
            db.update_nation(user_id, {"enemies": enemies})

        await query.edit_message_text(
            f"⚔️ **PERANG DIMULAI!** ⚔️\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ {nation['name']} ⚔️ {target['name']}\n\n"
            f"Gunakan /perang untuk bertempur!",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🗡️ Bertempur!", "war_battle")])
        )

    async def do_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        wars = db.get_active_wars(user_id)
        if not wars:
            await query.answer("Tidak ada perang aktif!", show_alert=True)
            return

        war = wars[0]
        is_attacker = war["attacker_id"] == user_id
        opponent_id = war["defender_id"] if is_attacker else war["attacker_id"]
        opponent = db.get_nation(opponent_id)
        if not opponent:
            return

        if is_attacker:
            result = calculate_battle(nation, opponent)
        else:
            result = calculate_battle(opponent, nation)
            # Flip perspective
            result["winner"] = "defender" if result["winner"] == "attacker" else "attacker"

        i_win = (is_attacker and result["winner"] == "attacker") or \
                (not is_attacker and result["winner"] == "defender")

        # Apply losses to attacker (me if I'm attacker)
        my_losses = {
            "soldiers": max(0, nation["soldiers"] - result["atk_soldier_loss"] if is_attacker else nation["soldiers"] - result["def_soldier_loss"]),
            "tanks": max(0, nation["tanks"] - (result["atk_tank_loss"] if is_attacker else result["def_tank_loss"])),
            "jets": max(0, nation["jets"] - (result["atk_jet_loss"] if is_attacker else result["def_jet_loss"])),
            "war_weariness": min(100, nation.get("war_weariness", 0) + 5),
            "happiness": clamp(nation["happiness"] - 3),
        }

        opp_losses = {
            "soldiers": max(0, opponent["soldiers"] - (result["def_soldier_loss"] if is_attacker else result["atk_soldier_loss"])),
            "tanks": max(0, opponent["tanks"] - (result["def_tank_loss"] if is_attacker else result["atk_tank_loss"])),
            "jets": max(0, opponent["jets"] - (result["def_jet_loss"] if is_attacker else result["atk_jet_loss"])),
            "war_weariness": min(100, opponent.get("war_weariness", 0) + 5),
            "happiness": clamp(opponent["happiness"] - 3),
        }

        if i_win and result["money_stolen"] > 0:
            my_losses["money"] = nation["money"] + result["money_stolen"]
            opp_losses["money"] = max(0, opponent["money"] - result["money_stolen"])

        db.update_nation(user_id, my_losses)
        db.update_nation(opponent_id, opp_losses)

        # Update war score
        new_atk_wins = war["attacker_wins"] + (1 if result["winner"] == "attacker" else 0)
        new_def_wins = war["defender_wins"] + (1 if result["winner"] == "defender" else 0)
        new_rounds = war["total_rounds"] + 1

        db.wars.update(
            {"attacker_wins": new_atk_wins, "defender_wins": new_def_wins, "total_rounds": new_rounds},
            (db.Q.attacker_id == war["attacker_id"])
            & (db.Q.defender_id == war["defender_id"])
            & (db.Q.status == "active")
        )

        # Check war end (best of 5)
        war_over = False
        winner_id = None
        if new_atk_wins >= 3:
            war_over = True
            winner_id = war["attacker_id"]
        elif new_def_wins >= 3:
            war_over = True
            winner_id = war["defender_id"]

        result_emoji = "🏆 MENANG!" if i_win else "💀 KALAH!"

        text = (
            f"⚔️ **PERTEMPURAN RONDE {new_rounds}** ⚔️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Kekuatan: {format_number(result['atk_power'])} vs {format_number(result['def_power'])}\n\n"
            f"**{result_emoji}**\n\n"
            f"📉 **Kerugianmu:**\n"
            f"🪖 -{format_number(result['atk_soldier_loss'] if is_attacker else result['def_soldier_loss'])} tentara\n"
            f"🚜 -{result['atk_tank_loss'] if is_attacker else result['def_tank_loss']} tank\n"
            f"✈️ -{result['atk_jet_loss'] if is_attacker else result['def_jet_loss']} jet\n"
        )

        if i_win and result["money_stolen"] > 0:
            text += f"💰 Rampasan: +${format_number(result['money_stolen'])}\n"

        text += f"\n📊 **Skor: {new_atk_wins} - {new_def_wins}** (Best of 5)\n"

        if war_over:
            db.end_war(war["attacker_id"], war["defender_id"], winner_id)
            i_won_war = winner_id == user_id
            if i_won_war:
                # War winner bonuses
                db.update_nation(user_id, {
                    "reputation": clamp(nation["reputation"] + 10, 0, 100),
                })
                text += f"\n🏆 **PERANG DIMENANGKAN!** 🎉\n🌍 Reputasi +10"
            else:
                db.update_nation(user_id, {
                    "reputation": clamp(nation["reputation"] - 5, 0, 100),
                })
                text += f"\n💀 **PERANG KALAH!**\n🌍 Reputasi -5"
            buttons = [("🔙 Panel Perang", "menu_perang")]
        else:
            buttons = [
                ("🗡️ Ronde Berikutnya!", "war_battle"),
                ("🏳️ Menyerah", "war_surrender"),
            ]

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_keyboard(buttons)
        )

    async def surrender(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)

        wars = db.get_active_wars(user_id)
        if not wars:
            return

        war = wars[0]
        winner_id = war["defender_id"] if war["attacker_id"] == user_id else war["attacker_id"]
        winner = db.get_nation(winner_id)

        db.end_war(war["attacker_id"], war["defender_id"], winner_id)

        # Surrender penalty
        penalty = int(nation["money"] * 0.2)
        db.update_nation(user_id, {
            "money": max(0, nation["money"] - penalty),
            "reputation": clamp(nation["reputation"] - 15, 0, 100),
        })
        if winner:
            db.update_nation(winner_id, {"money": winner["money"] + penalty})

        await query.edit_message_text(
            f"🏳️ **MENYERAH!**\n\n"
            f"🏛️ {nation['name']} menyerah kepada {winner['name'] if winner else 'musuh'}.\n"
            f"💰 Reparasi: -${format_number(penalty)}\n"
            f"🌍 Reputasi: -15",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Perang", "menu_perang")])
        )

    async def nuke_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)

        if not nation or nation["nukes"] < 1:
            await query.answer("☢️ Tidak punya nuklir!", show_alert=True)
            return

        wars = db.get_active_wars(user_id)
        if not wars:
            await query.answer("Harus dalam perang dulu!", show_alert=True)
            return

        war = wars[0]
        opponent_id = war["defender_id"] if war["attacker_id"] == user_id else war["attacker_id"]
        opponent = db.get_nation(opponent_id)

        # Nuke effects - devastating
        nuke_damage = {
            "population": max(10000, opponent["population"] - random.randint(20000, 50000)),
            "soldiers": max(0, opponent["soldiers"] - random.randint(2000, 5000)),
            "factories": max(0, opponent["factories"] - random.randint(3, 8)),
            "farms": max(0, opponent["farms"] - random.randint(3, 8)),
            "happiness": clamp(opponent["happiness"] - 40),
            "health": clamp(opponent["health"] - 30),
            "stability": clamp(opponent["stability"] - 30),
        }

        db.update_nation(opponent_id, nuke_damage)
        db.update_nation(user_id, {
            "nukes": nation["nukes"] - 1,
            "reputation": clamp(nation["reputation"] - 30, 0, 100),
        })

        db.log_event("nuke_launched", user_id,
                      f"☢️ {nation['name']} meluncurkan nuklir ke {opponent['name']}!")

        await query.edit_message_text(
            f"☢️ **NUKLIR DILUNCURKAN!** ☢️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ Target: {opponent['name']}\n\n"
            f"💀 **Kerusakan:**\n"
            f"👥 Korban massal\n"
            f"🏭 Infrastruktur hancur\n"
            f"😰 Kebahagiaan & kesehatan anjlok\n\n"
            f"⚠️ Reputasi internasional: -30\n"
            f"☢️ Sisa nuklir: {nation['nukes'] - 1}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Perang", "menu_perang")])
        )

    return [
        CommandHandler("perang", war_menu),
        CallbackQueryHandler(war_menu, pattern=r"^menu_perang$"),
        CallbackQueryHandler(target_list, pattern=r"^war_target_list$"),
        CallbackQueryHandler(declare_war, pattern=r"^war_declare_"),
        CallbackQueryHandler(confirm_war, pattern=r"^war_confirm_"),
        CallbackQueryHandler(do_battle, pattern=r"^war_battle$"),
        CallbackQueryHandler(surrender, pattern=r"^war_surrender$"),
        CallbackQueryHandler(nuke_target, pattern=r"^war_nuke_target$"),
    ]
