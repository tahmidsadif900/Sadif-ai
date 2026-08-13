"""
সাদিফ AI — একবারের লগইন স্ক্রিপ্ট
===================================
এটা আপনার টেলিগ্রাম অ্যাকাউন্টকে সাদিফ AI-র সাথে যুক্ত করে।
শুধু একবার চালাতে হবে।

চালানোর নিয়ম (ল্যাপটপে):
    pip install telethon python-dotenv
    python login.py

চাইলে জিজ্ঞেস করবে:
    ১. API_ID ও API_HASH (my.telegram.org থেকে ফ্রিতে নেওয়া)
    ২. আপনার ফোন নম্বর (যেমন +8801XXXXXXXXX)
    ৩. টেলিগ্রাম অ্যাপে যে OTP কোডটা আসবে

শেষে একটা SESSION_STRING দেবে — এটা কোথাও গোপনে রাখুন,
কারো সাথে শেয়ার করবেন না! (এটা দিয়ে অ্যাকাউন্টে ঢোকা যায় 🔒)
"""

from telethon import TelegramClient
from telethon.sessions import StringSession

print("=" * 50)
print("🤖 সাদিফ AI — টেলিগ্রাম লগইন")
print("=" * 50)

api_id = int(input("\n১) API_ID লিখুন: ").strip())
api_hash = input("২) API_HASH লিখুন: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    session_string = client.session.save()

print("\n" + "=" * 50)
print("✅ লগইন সফল! নিচের SESSION_STRING টা কপি করুন:")
print("=" * 50)
print()
print(session_string)
print()
print("🔒 এটা কারো সাথে শেয়ার করবেন না!")
print("এখন GUIDE.md-এর ধাপ ৬ অনুযায়ী Render-এ SESSION_STRING হিসেবে বসাবেন।")
