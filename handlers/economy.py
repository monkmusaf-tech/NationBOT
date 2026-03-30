import time
import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.helpers import make_keyboard, format_number, clamp, RESOURCE_EMOJI


def economy_handlers(db):

    async def economy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"💰 **PANEL EKONOMI — {nation['name']}** 💰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 Uang: ${format_number(nation['money'])}\n"
            f"📈 GDP: ${format_number(nation['gdp'])}\n"
            f"📊 Inflasi: {nation['inflation']:.1f}%\n"
            f"👷 Pengangguran: {nation['unemployment']:.1f}%\n"
            f"💸 Pajak: {nation['tax_rate']}%\n\n"
            f"🏭 Pabrik: {nation['factories']} | "
            f"🌾 Pertanian: {nation['farms']} | "
            f"⛏️ Tambang: {nation['mines']} | "
            f"🛢️ Sumur Minyak: {nation['oil_wells']}\n\n"
            f"🍚 Makanan: {format_number(nation['food'])}\n"
            f"🪨 Material: {format_number(nation['materials'])}\n"
            f"🛢️ Minyak: {format_number(nation['oil'])}\n"
        )

        keyboard = make_keyboard([
            ("💵 Kumpulkan Pendapatan", "eco_collect"),
            ("🏭 Bangun Pabrik ($2000)", "eco_build_factory"),
            ("🌾 Bangun Pertanian ($1500)", "eco_build_farm"),
            ("⛏️ Bangun Tambang ($1800)", "eco_build_mine"),
            ("🛢️ Bangun Sumur Minyak ($3000)", "eco_build_oil"),
            ("📊 Atur Pajak", "eco_tax_menu"),
            ("🔬 Riset Teknologi ($5000)", "eco_research"),
            ("🔙 Kembali", "menu_back"),
        ], columns=2)

        await send(text, parse_mode="Markdown", reply_markup=keyboard)

    async def collect_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        now = time.time()
        elapsed = now - nation.get("last_collect", now)
        hours = elapsed / 3600

        if hours < 0.5:
            mins = int((0.5 - hours) * 60)
            await query.answer(f"⏰ Tunggu {mins} menit lagi!", show_alert=True)
            return

        # Calculate income
        tax_income = int(nation["population"] * nation["tax_rate"] / 100 * 0.1 * hours)
        factory_income = int(nation["factories"] * 200 * hours)
        farm_production = int(nation["farms"] * 150 * hours)
        mine_production = int(nation["mines"] * 100 * hours)
        oil_production = int(nation["oil_wells"] * 50 * hours)

        total_money = tax_income + factory_income
        # GDP growth
        new_gdp = int(nation["gdp"] * (1 + random.uniform(0.001, 0.01)))

        # Population growth
        growth_rate = 0.001 * (nation["happiness"] / 100) * (nation["health"] / 100)
        pop_growth = int(nation["population"] * growth_rate * hours)

        db.update_nation(user_id, {
            "money": nation["money"] + total_money,
            "food": nation["food"] + farm_production,
            "materials": nation["materials"] + mine_production,
            "oil": nation["oil"] + oil_production,
            "gdp": new_gdp,
            "population": nation["population"] + pop_growth,
            "last_collect": now,
            "turn": nation["turn"] + 1,
        })

        await query.edit_message_text(
            f"💵 **PENDAPATAN DIKUMPULKAN!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ Waktu: {hours:.1f} jam\n\n"
            f"💰 Pajak: +${format_number(tax_income)}\n"
            f"🏭 Pabrik: +${format_number(factory_income)}\n"
            f"🌾 Makanan: +{format_number(farm_production)}\n"
            f"⛏️ Material: +{format_number(mine_production)}\n"
            f"🛢️ Minyak: +{format_number(oil_production)}\n"
            f"👥 Populasi: +{format_number(pop_growth)}\n"
            f"📈 GDP: ${format_number(new_gdp)}\n\n"
            f"💰 Total uang: ${format_number(nation['money'] + total_money)}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Ekonomi", "menu_ekonomi")])
        )

    async def build_facility(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        builds = {
            "eco_build_factory": ("factories", "Pabrik", 2000, "🏭"),
            "eco_build_farm": ("farms", "Pertanian", 1500, "🌾"),
            "eco_build_mine": ("mines", "Tambang", 1800, "⛏️"),
            "eco_build_oil": ("oil_wells", "Sumur Minyak", 3000, "🛢️"),
        }

        key, name, cost, emoji = builds[query.data]

        if nation["money"] < cost:
            await query.answer(f"💸 Uang tidak cukup! Butuh ${format_number(cost)}", show_alert=True)
            return

        db.update_nation(user_id, {
            "money": nation["money"] - cost,
            key: nation[key] + 1,
            "unemployment": clamp(nation["unemployment"] - 0.5, 0, 50),
        })

        await query.edit_message_text(
            f"{emoji} **{name} Dibangun!**\n\n"
            f"💰 Biaya: -${format_number(cost)}\n"
            f"📦 Total {name}: {nation[key] + 1}\n"
            f"💰 Sisa uang: ${format_number(nation['money'] - cost)}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Ekonomi", "menu_ekonomi")])
        )

    async def tax_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        await query.edit_message_text(
            f"📊 **PENGATURAN PAJAK**\n\n"
            f"Pajak saat ini: **{nation['tax_rate']}%**\n"
            f"😊 Kebahagiaan: {nation['happiness']}%\n\n"
            f"⚠️ Pajak tinggi = lebih banyak uang tapi rakyat tidak senang\n"
            f"⚠️ Pajak rendah = rakyat senang tapi pendapatan sedikit",
            parse_mode="Markdown",
            reply_markup=make_keyboard([
                ("📉 5% (Sangat Rendah)", "eco_tax_5"),
                ("📉 10% (Rendah)", "eco_tax_10"),
                ("📊 15% (Normal)", "eco_tax_15"),
                ("📈 25% (Tinggi)", "eco_tax_25"),
                ("📈 35% (Sangat Tinggi)", "eco_tax_35"),
                ("📈 50% (Ekstrem)", "eco_tax_50"),
                ("🔙 Kembali", "menu_ekonomi"),
            ], columns=2)
        )

    async def set_tax(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        rate = int(query.data.replace("eco_tax_", ""))
        old_rate = nation["tax_rate"]
        happiness_change = (old_rate - rate) // 2

        new_happiness = clamp(nation["happiness"] + happiness_change)
        db.update_nation(user_id, {
            "tax_rate": rate,
            "happiness": new_happiness,
        })

        emoji = "📈" if rate > old_rate else "📉"
        mood = "😊" if happiness_change > 0 else "😠" if happiness_change < 0 else "😐"

        await query.edit_message_text(
            f"{emoji} **Pajak diubah ke {rate}%**\n\n"
            f"Sebelumnya: {old_rate}%\n"
            f"{mood} Kebahagiaan: {nation['happiness']}% → {new_happiness}%",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Ekonomi", "menu_ekonomi")])
        )

    async def research_tech(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        nation = db.get_nation(user_id)
        if not nation:
            return

        cost = 5000
        if nation["money"] < cost:
            await query.answer(f"💸 Butuh ${format_number(cost)}!", show_alert=True)
            return

        tech_gain = random.randint(5, 20)
        db.update_nation(user_id, {
            "money": nation["money"] - cost,
            "tech_points": nation["tech_points"] + tech_gain,
            "education": clamp(nation["education"] + 2),
        })

        await query.edit_message_text(
            f"🔬 **RISET BERHASIL!**\n\n"
            f"🔬 Tech Points: +{tech_gain}\n"
            f"📚 Pendidikan: +2%\n"
            f"💰 Biaya: -${format_number(cost)}",
            parse_mode="Markdown",
            reply_markup=make_keyboard([("🔙 Panel Ekonomi", "menu_ekonomi")])
        )

    return [
        CommandHandler("ekonomi", economy_menu),
        CallbackQueryHandler(economy_menu, pattern=r"^menu_ekonomi$"),
        CallbackQueryHandler(collect_income, pattern=r"^eco_collect$"),
        CallbackQueryHandler(build_facility, pattern=r"^eco_build_"),
        CallbackQueryHandler(tax_menu, pattern=r"^eco_tax_menu$"),
        CallbackQueryHandler(set_tax, pattern=r"^eco_tax_\d+$"),
        CallbackQueryHandler(research_tech, pattern=r"^eco_research$"),
    ]
