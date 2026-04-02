import json
import os
import random
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

GIVEAWAY_TITLE = os.getenv("GIVEAWAY_TITLE", "🎉 سحب جديد")
GIVEAWAY_PRIZE = os.getenv("GIVEAWAY_PRIZE", "50 نجمة ⭐")
WINNERS_COUNT = int(os.getenv("WINNERS_COUNT", "1"))
FOOTER_TEXT = os.getenv("FOOTER_TEXT", "© جميع الحقوق محفوظة - Ivan Bot System")

DATA_FILE = "participants.json"
SETTINGS_FILE = "settings.json"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing.")
if not CHANNEL_USERNAME:
    raise ValueError("CHANNEL_USERNAME is missing.")
if OWNER_ID == 0:
    raise ValueError("OWNER_ID is missing or invalid.")

def load_participants():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_participants(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "is_open": True,
            "giveaway_message_id": None,
            "giveaway_chat_id": None
        }
        save_settings(default_settings)
        return default_settings
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def build_keyboard(participants_count: int):
    keyboard = [
        [
            InlineKeyboardButton(f"🎟 المشاركة في السحب [{participants_count}]", callback_data="join_giveaway")
        ],
        [
            InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        ],
        [
            InlineKeyboardButton("🔄 تحديث", callback_data="refresh_giveaway")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_giveaway_text(participants_count: int, is_open: bool):
    status = "🟢 مفتوح" if is_open else "🔴 مغلق"
    return (
        f"{GIVEAWAY_TITLE}\n\n"
        f"🎁 **الجائزة:** {GIVEAWAY_PRIZE}\n"
        f"🏆 **عدد الفائزين:** {WINNERS_COUNT}\n"
        f"📊 **عدد المشاركين:** {participants_count}\n"
        f"📌 **الحالة:** {status}\n\n"
        f"**الشروط:**\n"
        f"• الاشتراك بالقناة\n"
        f"• الضغط على زر المشاركة\n\n"
        f"{FOOTER_TEXT}"
    )

async def update_giveaway_message(context: ContextTypes.DEFAULT_TYPE):
    settings = load_settings()
    participants = load_participants()
    participants_count = len(participants)

    if settings["giveaway_message_id"] and settings["giveaway_chat_id"]:
        try:
            await context.bot.edit_message_text(
                chat_id=settings["giveaway_chat_id"],
                message_id=settings["giveaway_message_id"],
                text=build_giveaway_text(participants_count, settings["is_open"]),
                reply_markup=build_keyboard(participants_count),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print("Edit giveaway message error:", e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    participants = load_participants()
    settings = load_settings()
    participants_count = len(participants)

    await update.message.reply_text(
        build_giveaway_text(participants_count, settings["is_open"]),
        reply_markup=build_keyboard(participants_count),
        parse_mode=ParseMode.MARKDOWN
    )

async def post_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    participants = load_participants()
    settings = load_settings()
    participants_count = len(participants)

    sent = await update.message.reply_text(
        build_giveaway_text(participants_count, settings["is_open"]),
        reply_markup=build_keyboard(participants_count),
        parse_mode=ParseMode.MARKDOWN
    )

    settings["giveaway_message_id"] = sent.message_id
    settings["giveaway_chat_id"] = sent.chat_id
    save_settings(settings)

    await update.message.reply_text("✅ تم نشر رسالة السحب بنجاح.")

async def draw_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    participants = load_participants()
    if len(participants) == 0:
        return await update.message.reply_text("⚠️ لا يوجد مشاركين بعد.")

    winners_count = min(WINNERS_COUNT, len(participants))
    winner_ids = random.sample(list(participants.keys()), winners_count)

    result_text = "🎉 **نتيجة السحب**\n\n"
    for i, uid in enumerate(winner_ids, start=1):
        user = participants[uid]
        username = user.get("username")
        full_name = user.get("full_name")
        mention = f"@{username}" if username else full_name
        result_text += f"{i}. {mention}\n"

    result_text += f"\n{FOOTER_TEXT}"

    await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)

async def list_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    participants = load_participants()
    count = len(participants)

    text = f"📋 عدد المشاركين الحالي: **{count}**\n\n"
    preview = list(participants.values())[:20]

    for i, user in enumerate(preview, start=1):
        username = user.get("username")
        full_name = user.get("full_name")
        text += f"{i}. @{username}\n" if username else f"{i}. {full_name}\n"

    if count > 20:
        text += "\n... والباقي أكثر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def close_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    settings = load_settings()
    settings["is_open"] = False
    save_settings(settings)
    await update.message.reply_text("🔴 تم إغلاق المشاركة.")
    await update_giveaway_message(context)

async def open_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    settings = load_settings()
    settings["is_open"] = True
    save_settings(settings)
    await update.message.reply_text("🟢 تم فتح المشاركة.")
    await update_giveaway_message(context)

async def reset_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ هذا الأمر فقط للمالك.")

    save_participants({})
    await update.message.reply_text("🗑 تم تصفير المشاركين.")
    await update_giveaway_message(context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    participants = load_participants()
    settings = load_settings()

    if query.data == "refresh_giveaway":
        await update_giveaway_message(context)
        return await query.answer("✅ تم التحديث", show_alert=False)

    if query.data == "join_giveaway":
        if not settings["is_open"]:
            return await query.answer("❌ المشاركة مغلقة حالياً", show_alert=True)

        subscribed = await is_subscribed(user.id, context)
        if not subscribed:
            return await query.answer("⚠️ لازم تشترك بالقناة أولاً", show_alert=True)

        user_id = str(user.id)

        if user_id in participants:
            return await query.answer("✅ أنت مشارك مسبقاً", show_alert=True)

        participants[user_id] = {
            "username": user.username if user.username else "",
            "full_name": user.full_name,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_participants(participants)

        await update_giveaway_message(context)
        return await query.answer("🎉 تم تسجيلك بالسحب بنجاح!", show_alert=True)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_giveaway))
    app.add_handler(CommandHandler("draw", draw_winner))
    app.add_handler(CommandHandler("list", list_participants))
    app.add_handler(CommandHandler("close", close_giveaway))
    app.add_handler(CommandHandler("open", open_giveaway))
    app.add_handler(CommandHandler("reset", reset_giveaway))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
