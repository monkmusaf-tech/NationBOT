from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random


def format_number(n):
    """Format number with comma separator."""
    if isinstance(n, float):
        return f"{n:,.1f}"
    return f"{n:,}"


def progress_bar(value, max_val=100, length=10):
    """Create emoji progress bar."""
    filled = int(value / max_val * length)
    filled = max(0, min(filled, length))
    return "█" * filled + "░" * (length - filled)


def nation_summary(nation, db):
    """Create a formatted nation summary."""
    power = db.calc_power(nation)
    return (
        f"🏛️ **{nation['name']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Pemimpin: User `{nation['user_id']}`\n"
        f"🏛️ Pemerintahan: {nation['government_type']}\n"
        f"⚡ Power: {format_number(power)}\n\n"
        f"📊 **Sumber Daya**\n"
        f"💰 Uang: ${format_number(nation['money'])}\n"
        f"🍚 Makanan: {format_number(nation['food'])}\n"
        f"🪨 Material: {format_number(nation['materials'])}\n"
        f"🛢️ Minyak: {format_number(nation['oil'])}\n"
        f"🔬 Tech: {format_number(nation['tech_points'])}\n\n"
        f"👥 **Populasi & Sosial**\n"
        f"👥 Penduduk: {format_number(nation['population'])}\n"
        f"😊 Kebahagiaan: {progress_bar(nation['happiness'])} {nation['happiness']}%\n"
        f"🏥 Kesehatan: {progress_bar(nation['health'])} {nation['health']}%\n"
        f"📚 Pendidikan: {progress_bar(nation['education'])} {nation['education']}%\n\n"
        f"⚔️ **Militer**\n"
        f"🪖 Tentara: {format_number(nation['soldiers'])}\n"
        f"🚜 Tank: {format_number(nation['tanks'])}\n"
        f"✈️ Jet: {format_number(nation['jets'])}\n"
        f"🚢 Kapal: {format_number(nation['ships'])}\n"
        f"🚀 Rudal: {format_number(nation['missiles'])}\n"
        f"☢️ Nuklir: {format_number(nation['nukes'])}\n\n"
        f"🏛️ **Politik**\n"
        f"👍 Approval: {progress_bar(nation['approval_rating'])} {nation['approval_rating']}%\n"
        f"🕳️ Korupsi: {progress_bar(nation['corruption'])} {nation['corruption']}%\n"
        f"🗽 Kebebasan: {progress_bar(nation['freedom_index'])} {nation['freedom_index']}%\n"
        f"⚖️ Stabilitas: {progress_bar(nation['stability'])} {nation['stability']}%\n"
    )


def make_keyboard(buttons, columns=2):
    """Create inline keyboard from list of (text, callback_data) tuples."""
    keyboard = []
    row = []
    for text, data in buttons:
        row.append(InlineKeyboardButton(text, callback_data=data))
        if len(row) >= columns:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def clamp(value, min_val=0, max_val=100):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


IDEOLOGY_MAP = {
    "demokrasi": {"freedom_index": 70, "corruption": 15, "stability": 65, "leader_title": "Presiden"},
    "monarki": {"freedom_index": 30, "corruption": 30, "stability": 80, "leader_title": "Raja/Ratu"},
    "komunis": {"freedom_index": 20, "corruption": 25, "stability": 75, "leader_title": "Sekretaris Jenderal"},
    "militer": {"freedom_index": 15, "corruption": 35, "stability": 85, "leader_title": "Jenderal Besar"},
    "teokrasi": {"freedom_index": 25, "corruption": 20, "stability": 70, "leader_title": "Pemimpin Agung"},
}

RESOURCE_EMOJI = {
    "money": "💰",
    "food": "🍚",
    "materials": "🪨",
    "oil": "🛢️",
    "tech_points": "🔬",
}
