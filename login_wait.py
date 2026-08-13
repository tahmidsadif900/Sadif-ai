"""
সাদিফ AI — লগইন সহায়ক (ওয়ার্কস্পেসে চলার জন্য)
=================================================
কীভাবে কাজ করে:
  ১. .env থেকে API_ID, API_HASH, PHONE_NUMBER নেয়
  ২. টেলিগ্রামে OTP পাঠায়
  ৩. এই ফোল্ডারে otp.txt ফাইলের অপেক্ষা করে (সর্বোচ্চ ১০ মিনিট)
  ৪. OTP মিললেই লগইন করে SESSION_STRING বানিয়ে session_string.txt-এ সেভ করে
"""

import asyncio
import os
import re

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0") or 0)
API_HASH = os.environ.get("API_HASH", "")
PHONE = os.environ.get("PHONE_NUMBER", "")

BASE = os.path.dirname(os.path.abspath(__file__))
OTP_FILE = os.path.join(BASE, "otp.txt")
OUT_FILE = os.path.join(BASE, "session_string.txt")


async def main():
    if not (API_ID and API_HASH and PHONE):
        print("❌ .env-এ API_ID / API_HASH / PHONE_NUMBER পূরণ করা নেই", flush=True)
        return

    if os.path.exists(OTP_FILE):
        os.remove(OTP_FILE)
    if os.path.exists(OUT_FILE):
        os.remove(OUT_FILE)

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    print(f"📩 {PHONE} নম্বরে OTP পাঠানো হচ্ছে...", flush=True)
    sent = await client.send_code_request(PHONE)
    print("✅ OTP পাঠানো হয়েছে! আপনার টেলিগ্রাম অ্যাপে 'Telegram' নামের চ্যাটে "
          "৫ ডিজিটের একটা কোড এসেছে।", flush=True)
    print("⏳ otp.txt ফাইলের অপেক্ষায়... (সর্বোচ্চ ১০ মিনিট)", flush=True)

    code = None
    for _ in range(120):
        await asyncio.sleep(5)
        if os.path.exists(OTP_FILE):
            raw = open(OTP_FILE, encoding="utf-8").read()
            code = re.sub(r"\D", "", raw)  # শুধু সংখ্যাটা রাখবে
            if code:
                break

    if not code:
        print("❌ ১০ মিনিটে OTP পাওয়া যায়নি। আবার চেষ্টা করতে হবে।", flush=True)
        await client.disconnect()
        return

    print("🔐 OTP পেয়েছি, লগইন করা হচ্ছে...", flush=True)
    try:
        await client.sign_in(PHONE, code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        print("⚠️ আপনার অ্যাকাউন্টে 2FA পাসওয়ার্ড আছে — সেটা লাগবে।", flush=True)
        await client.disconnect()
        return

    me = await client.get_me()
    session_string = client.session.save()
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(session_string)

    if os.path.exists(OTP_FILE):
        os.remove(OTP_FILE)

    print(f"🎉 লগইন সফল! অ্যাকাউন্ট: {me.first_name} (@{me.username or 'no-username'})", flush=True)
    print("✅ SESSION_STRING তৈরি হয়ে গেছে — সাদিফ AI চালুর জন্য প্রস্তুত!", flush=True)
    await client.disconnect()


asyncio.run(main())
