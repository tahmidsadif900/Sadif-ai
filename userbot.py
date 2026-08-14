"""
সাদিফ AI (Sadif AI) — ইউজারবট মোড
====================================
আপনার নিজের টেলিগ্রাম অ্যাকাউন্ট থেকে চলে — বন্ধুরা আপনার ইনবক্সে
মেসেজ দেবে, আর সাদিফ AI আপনার অ্যাকাউন্ট থেকেই, আপনার স্টাইলে উত্তর দেবে।

- ব্রেইন: Groq / Gemini (ai_engine.py)
- style_profile.txt থেকে আপনার কথার স্টাইল শেখে
- ক্লাউডে (Render) ২৪/৭ চলে — ল্যাপটপ বন্ধ থাকলেও

নিয়ন্ত্রণ: টেলিগ্রামে নিজের "Saved Messages"-এ লিখুন —
  !pause   → সাদিফ AI থামবে
  !resume  → আবার চালু হবে
  !status  → অবস্থা দেখাবে
  !reset   → সব চ্যাটের স্মৃতি মুছে যাবে
"""

import asyncio
import json
import logging
import os
import random
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

import ai_engine

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SadifAI-Userbot")

# ---------------- সেটিংস (এনভায়রনমেন্ট ভ্যারিয়েবল) ----------------
API_ID = int(os.environ.get("API_ID", "0") or 0)
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
PORT = int(os.environ.get("PORT", "8080"))

client = TelegramClient(StringSession(SESSION_STRING or None), API_ID, API_HASH)

# প্রতিটা চ্যাটের সাম্প্রতিক কথোপকথন মনে রাখবে (OpenAI ফরম্যাটে)
histories = defaultdict(lambda: deque(maxlen=24))
chat_names = {}                    # chat_id → বন্ধুর নাম (রিপোর্টের জন্য)
total_replies = defaultdict(int)   # চ্যাটভেদে মোট রিপ্লাই সংখ্যা

# 🎯 কাস্টম ফ্রেন্ড মোড (Saved Messages থেকে !mode দিয়ে সেট করা যায়)
MODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friend_modes.json")
try:
    with open(MODES_FILE, encoding="utf-8") as f:
        friend_modes = json.load(f)
except Exception:
    friend_modes = {}


def save_modes():
    try:
        with open(MODES_FILE, "w", encoding="utf-8") as f:
            json.dump(friend_modes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("মোড সেভ করা যায়নি: %s", e)

# নিয়ন্ত্রণ ও নিরাপত্তা গার্ড
PAUSED = False
ME_ID = None
last_reply_at = defaultdict(float)   # একই চ্যাটে খুব দ্রুত রিপ্লাই আটকাতে
hour_count = defaultdict(int)        # প্রতি চ্যাটে ঘণ্টায় সর্বোচ্চ ১৫টা রিপ্লাই
hour_start = defaultdict(float)


@client.on(events.NewMessage())
async def remember_my_messages(event):
    """আপনি নিজে যা লিখেন — বট সেটাও স্মৃতিতে রাখবে,
    যাতে ফুল কথোপকথনের প্রসঙ্গ জানা থাকে। (কখনো থামায় না, শুধু মনে রাখে)"""
    try:
        if not event.out:
            return
        if ME_ID is not None and event.chat_id == ME_ID:
            return  # Saved Messages বাদ
        text = (event.raw_text or "").strip()
        if not text or text.startswith("!"):
            return  # কমান্ড বাদ
        histories[event.chat_id].append({"role": "assistant", "content": text})
        ai_engine.add_owner_sample(text)  # 🧠 লাইভ স্টাইল লার্নিং — নিজের লেখা বট শিখছে
        logger.info("📝 আপনার নিজের মেসেজ স্মৃতি+স্টাইলে রাখা হলো (চ্যাট %s)", event.chat_id)
    except Exception:
        pass


@client.on(events.NewMessage(incoming=True))
async def on_message(event):
    global ME_ID
    if PAUSED:
        return

    # নিজের আইডি একবারই শিখে রাখবে
    if ME_ID is None:
        me = await client.get_me()
        ME_ID = me.id

    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False):  # অন্য বটদের উত্তর দেবে না (লুপ ঠেকাতে)
        return
    if sender.id == ME_ID:  # নিজের মেসেজে না
        return
    chat_names[event.chat_id] = (
        getattr(sender, "first_name", None)
        or getattr(sender, "username", None)
        or str(sender.id)
    )

    text = (event.raw_text or "").strip()
    photo_bytes = None
    if not text:
        # 👁️ ছবি-অনলি মেসেজ: ভিশন চালু থাকলে ছবি দেখে উত্তর দেবে
        if event.photo and ai_engine.GEMINI_API_KEY:
            try:
                photo_bytes = await event.download_media(file=bytes)
            except Exception as e:
                logger.error("ছবি ডাউনলোড ব্যর্থ: %s", e)
                return
        else:
            return

    # গ্রুপে উত্তর দেবে শুধু যদি আপনাকে মেনশন করে বা আপনার মেসেজে রিপ্লাই দেয়
    if not event.is_private:
        should_reply = bool(getattr(event.message, "mentioned", False))
        if not should_reply and event.message.is_reply:
            try:
                replied_msg = await event.message.get_reply_message()
                if replied_msg and replied_msg.sender_id == ME_ID:
                    should_reply = True
            except Exception:
                pass
        if not should_reply:
            return

    # নিরাপত্তা গার্ড: একই চ্যাটে ৪ সেকেন্ডের আগে আবার রিপ্লাই না
    now = time.time()
    if now - last_reply_at[event.chat_id] < 4:
        return
    # প্রতি চ্যাটে ঘণ্টায় সর্বোচ্চ ১৫টা
    if now - hour_start[event.chat_id] > 3600:
        hour_start[event.chat_id] = now
        hour_count[event.chat_id] = 0
    if hour_count[event.chat_id] >= 15:
        logger.info("ঘণ্টার সীমা পূর্ণ — এই চ্যাটে ১ ঘণ্টা বিরতি।")
        return

    # 🎯 কাস্টম ফ্রেন্ড মোড (@username বা id দিয়ে ম্যাচ)
    uname = (getattr(sender, "username", None) or "").lower()
    mode = friend_modes.get("@" + uname) or friend_modes.get(uname) or friend_modes.get(str(sender.id))
    brain_text = text if not mode else f"{text}\n\n[Style note for THIS friend: {mode}]"

    try:
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(random.uniform(1.5, 4.0))  # মানুষের মতো টাইপ করার বিরতি
            history = histories[event.chat_id]
            if photo_bytes is not None:
                reply = await asyncio.to_thread(
                    ai_engine.generate_image_reply, list(history), photo_bytes, text
                )
            else:
                reply = await asyncio.to_thread(
                    ai_engine.generate_reply, list(history), brain_text
                )
    except Exception as e:
        # ব্রেইন ব্যস্ত/লিমিট শেষ → চুপচাপ থাকবে, বন্ধুকে রোবোটিক এরর মেসেজ পাঠাবে না
        logger.error("AI error: %s", e)
        return

    # 🧑 মানুষের মতো: একটা লম্বা মেসেজ না — ২-৩টা ছোট মেসেজ পরপর
    # কোট/রিপ্লাই-ট্যাগ ছাড়া সরাসরি মেসেজ পাঠাবে (মানুষ ফাস্ট চ্যাটে কোট করে না)
    parts = [p.strip() for p in reply.split("||") if p.strip()][:4] or [reply]
    history.append({"role": "user", "content": text if text else "[ছবি পাঠিয়েছে]"})
    history.append({"role": "assistant", "content": " ".join(parts)})

    for i, part in enumerate(parts):
        if i > 0:
            async with client.action(event.chat_id, "typing"):
                await asyncio.sleep(random.uniform(0.8, 2.0))
        await client.send_message(event.chat_id, part)
    last_reply_at[event.chat_id] = time.time()
    hour_count[event.chat_id] += 1
    total_replies[event.chat_id] += 1
    logger.info("✉️ %s কে রিপ্লাই দেওয়া হলো", getattr(sender, "first_name", None) or sender.id)


@client.on(events.NewMessage(pattern=r"^!(pause|resume|status|reset|summary|modes|mode|modeclear)\b\s*(.*)$"))
async def owner_commands(event):
    """Saved Messages-এ আপনার নিজের কমান্ড ধরবে।"""
    global PAUSED
    if ME_ID is None or event.chat_id != ME_ID or not event.out:
        return

    cmd = event.pattern_match.group(1).lower()
    arg = (event.pattern_match.group(2) or "").strip()

    if cmd == "pause":
        PAUSED = True
        await client.send_message("me", "⏸️ সাদিফ AI এখন থামা। আপনি নিজে হাতে চ্যাট করতে পারেন।")
    elif cmd == "resume":
        PAUSED = False
        await client.send_message("me", "▶️ সাদিফ AI আবার চালু!")
    elif cmd == "status":
        state = "⏸️ থামা" if PAUSED else "▶️ চালু"
        provider = "Groq" if ai_engine.GROQ_API_KEY else "Gemini"
        vision = "👁️ চালু" if ai_engine.GEMINI_API_KEY else "👁️ বন্ধ (GEMINI_API_KEY দিন)"
        await client.send_message(
            "me",
            f"🤖 সাদিফ AI: {state}\nব্রেইন: {provider}\nভিশন: {vision}\n"
            f"রিপোর্ট: প্রতিদিন সকাল ৮টা 🗞️"
        )
    elif cmd == "reset":
        histories.clear()
        await client.send_message("me", "🧹 সব চ্যাটের স্মৃতি মুছে ফেলা হয়েছে।")
    elif cmd == "summary":
        await client.send_message("me", "📋 রিপোর্ট বানাচ্ছি, একটু অপেক্ষা করুন... ⏳")
        asyncio.create_task(send_daily_summary())
    elif cmd == "mode":
        parts = arg.split(" ", 1)
        if len(parts) < 2:
            await client.send_message(
                "me",
                "🎯 ব্যবহার: !mode @username স্টাইল-নির্দেশনা\n"
                "যেমন: !mode @kelly_blaq extra funny roast mode\n"
                "দেখতে: !modes · মুছতে: !modeclear @kelly_blaq"
            )
        else:
            name, instr = parts[0].lower(), parts[1]
            friend_modes[name] = instr
            save_modes()
            await client.send_message("me", f"🎯 {name} এর জন্য কাস্টম মোড সেট হলো:\n\"{instr}\"")
    elif cmd == "modeclear":
        name = arg.lower()
        if name in friend_modes:
            friend_modes.pop(name)
            save_modes()
            await client.send_message("me", f"🧹 {name} এর কাস্টম মোড মুছে গেছে।")
        else:
            await client.send_message("me", "এই নামে কোনো মোড নেই — !modes দিয়ে তালিকা দেখুন।")
    elif cmd == "modes":
        if friend_modes:
            listing = "\n".join(f"• {k}: {v}" for k, v in friend_modes.items())
            await client.send_message("me", f"🎯 কাস্টম ফ্রেন্ড মোডস:\n{listing}")
        else:
            await client.send_message(
                "me", "🎯 কোনো কাস্টম মোড সেট করা নেই।\nসেট করুন: !mode @username নির্দেশনা"
            )


# ---------------- 📋 ডেইলি রিপোর্ট (প্রতিদিন সকাল ৮টা, ঢাকা সময়) ----------------
async def send_daily_summary():
    """যে যে বন্ধুর সাথে কথা হয়েছে তার ছোট সারসংক্ষেপ Saved Messages-এ।"""
    try:
        rows = []
        for chat_id, hist in histories.items():
            if not hist:
                continue
            name = chat_names.get(chat_id, str(chat_id))
            lines = "\n".join(
                f"  {'বন্ধু' if m['role'] == 'user' else 'সাদিফAI'}: {m['content'][:70]}"
                for m in list(hist)[-10:]
            )
            rows.append(f"💬 {name} (মোট রিপ্লাই: {total_replies.get(chat_id, 0)})\n{lines}")
        if not rows:
            await client.send_message(
                "me", "📋 সাদিফ AI রিপোর্ট: এই সেশনে কোনো চ্যাট-অ্যাক্টিভিটি ছিল না 😴"
            )
            return
        instruction = (
            "তুমি সাদিফের ব্যক্তিগত সহকারী। নিচের চ্যাট লগ দেখে সাদিফের জন্য বাংলায় "
            "ছোট্ট মর্নিং ব্রিফ বানাও: প্রথম লাইনে উষ্ণ সালাম (যেমন 'সুপ্রভাত সাদিফ! ☀️'), "
            "তারপর প্রতিটা বন্ধুর নাম ও কী নিয়ে কথা হয়েছে (১ লাইন করে), "
            "শেষে কোনো দরকারি ফলো-আপ বাকি আছে কিনা (টাকা/প্ল্যান/উত্তরহীন প্রশ্ন 👀)। "
            "ইমোজিসহ, সংক্ষিপ্ত ও পড়তে মজার হবে। নিজের ভূমিকা/মেটা কথা একদম নয়।"
        )
        summary = await asyncio.to_thread(
            ai_engine.raw_complete, instruction, "\n\n".join(rows)
        )
        await client.send_message("me", f"📋 সাদিফ AI — ডেইলি চ্যাট রিপোর্ট 🗞️\n\n{summary}")
    except Exception as e:
        logger.error("রিপোর্ট ব্যর্থ: %s", e)


async def daily_summary_loop():
    """প্রতিদিন সকাল ৮টায় (ঢাকা সময়) ডেইলি রিপোর্ট পাঠাবে।"""
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    from zoneinfo import ZoneInfo
    while True:
        try:
            now = _dt.now(ZoneInfo("Asia/Dhaka"))
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now >= target:
                target += _td(days=1)
            await asyncio.sleep((target - now).total_seconds())
            await send_daily_summary()
        except Exception as e:
            logger.error("রিপোর্ট লুপ এরর: %s", e)
            await asyncio.sleep(3600)


# ---------------- Render ফ্রি সার্ভারকে জাগিয়ে রাখার ছোট ওয়েব সার্ভার ----------------
class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Sadif AI userbot is alive ✅".encode())

    def log_message(self, *args):
        pass


def start_health_server():
    server = HTTPServer(("0.0.0.0", PORT), _Health)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health server পোর্ট %s-এ চালু", PORT)


def main():
    missing = [
        name
        for name, val in [
            ("API_ID", API_ID),
            ("API_HASH", API_HASH),
            ("SESSION_STRING", SESSION_STRING),
        ]
        if not val
    ]
    if not ai_engine.has_provider():
        missing.append("GROQ_API_KEY বা GEMINI_API_KEY")
    if missing:
        raise SystemExit(f"❌ এনভায়রনমেন্টে সেট করা নেই: {', '.join(missing)} — GUIDE.md দেখুন।")

    if os.environ.get("RENDER") or os.environ.get("PORT"):
        start_health_server()

    logger.info("🤖 সাদিফ AI (ইউজারবট মোড) চালু হচ্ছে...")
    client.start()

    # নিজের আইডি শুরুতেই শিখে রাখবে (কমান্ড যেন প্রথম মেসেজ থেকেই কাজ করে)
    async def _init_me():
        global ME_ID
        me = await client.get_me()
        ME_ID = me.id
        logger.info("👤 অ্যাকাউন্ট: %s (@%s)", me.first_name, me.username)

    client.loop.run_until_complete(_init_me())
    client.loop.create_task(daily_summary_loop())  # প্রতিদিন সকাল ৮টার রিপোর্ট
    logger.info("✅ সাদিফ AI অনলাইন! ২৪/৭ আপনার হয়ে উত্তর দেবে।")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
