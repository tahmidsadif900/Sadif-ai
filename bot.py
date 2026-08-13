"""
সাদিফ AI (Sadif AI) — বট মোড (আলাদা বট অ্যাকাউন্ট)
=====================================================
@BotFather দিয়ে বানানো আলাদা বট অ্যাকাউন্ট থেকে চলে।
- ব্রেইন: Groq / Gemini (ai_engine.py)
- style_profile.txt থেকে আপনার কথার স্টাইল শেখে
- Render-এর মতো ফ্রি ক্লাউড হোস্টিংয়ে ২৪/৭ চলে
"""

import asyncio
import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import ai_engine

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SadifAI")

# ---------------- সেটিংস ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")  # যেমন: https://sadif-ai.onrender.com

# প্রতিটা চ্যাটের সাম্প্রতিক কথোপকথন মনে রাখবে
histories = defaultdict(lambda: deque(maxlen=24))


# ------------------------------ কমান্ডগুলো ------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "বন্ধু"
    await update.message.reply_text(
        f"হাই {name}! 👋 আমি সাদিফ AI — সাদিফের পার্সোনাল AI অ্যাসিস্ট্যান্ট।\n"
        "সাদিফ এখন ব্যস্ত, তাই আমি তার হয়ে কথা বলছি। কী খবর বলো? 😄\n\n"
        "/reset — আগের কথোপকথন ভুলে যাব\n"
        "/help — সাহায্য"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 সাদিফ AI\n\n"
        "• যেকোনো মেসেজ লিখলেই আমি সাদিফের স্টাইলে উত্তর দেব\n"
        "• /reset — আমার সঙ্গে আগের কথা মুছে নতুন করে শুরু\n"
        "• গ্রুপে আমাকে মেনশন (@) করলে বা আমার মেসেজে রিপ্লাই দিলে উত্তর দেব"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories.pop(update.message.chat.id, None)
    await update.message.reply_text("আচ্ছা, আগের সব ভুলে গেলাম! নতুন করে শুরু করি 😄")


# ------------------------------ মূল উত্তর ------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    # গ্রুপ চ্যাটে শোরগোল কমাতে: শুধু মেনশন/রিপ্লাই পেলেই উত্তর দেবে
    if msg.chat.type in ("group", "supergroup"):
        bot_username = (context.bot.username or "").lower()
        mentioned = f"@{bot_username}" in msg.text.lower() or "sadif" in msg.text.lower()
        replied_to_bot = bool(
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == context.bot.id
        )
        if not (mentioned or replied_to_bot):
            return

    chat_id = msg.chat.id
    history = histories[chat_id]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        reply_text = await asyncio.to_thread(
            ai_engine.generate_reply, list(history), msg.text
        )
    except Exception as e:  # কোটা শেষ/নেট সমস্যা হলে বন্ধুত্বপূর্ণ মেসেজ
        logger.error("AI error: %s", e)
        await msg.reply_text("উফ, একটু টেকনিক্যাল ঝামেলা হচ্ছে 😅 সাদিফ নিজে এসে উত্তর দেবে একটু পরেই!")
        return

    history.append({"role": "user", "content": msg.text})
    history.append({"role": "assistant", "content": reply_text})
    await msg.reply_text(reply_text)


# ------------------------------ চালু ------------------------------
def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN সেট করা নেই। GUIDE.md দেখুন।")
    if not ai_engine.has_provider():
        raise SystemExit("❌ GROQ_API_KEY বা GEMINI_API_KEY সেট করা নেই। GUIDE.md দেখুন।")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        # ক্লাউড (Render) মোড — ২৪/৭ চলবে, ল্যাপটপ লাগবে না
        logger.info("Webhook mode চালু হচ্ছে...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        # লোকাল টেস্ট মোড
        logger.info("Polling mode চালু হচ্ছে (লোকাল টেস্ট)...")
        app.run_polling()


if __name__ == "__main__":
    main()
