"""
সাদিফ AI — ব্রেইন (AI ইঞ্জিন)
================================
Aই ফাইলটাই সাদিফ AI-র "মগজ" — Groq (ডিফল্ট) বা Gemini দিয়ে উত্তর বানায়।
userbot.py ও bot.py — দুটোই এটা ব্যবহার করে।
"""

import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_style_profile() -> str:
    """style_profile.txt থেকে সাদিফের কথার স্টাইল পড়ে আনবে।"""
    try:
        with open(os.path.join(BASE_DIR, "style_profile.txt"), encoding="utf-8") as f:
            text = f.read().strip()
            return text or "কোনো নমুনা দেওয়া হয়নি।"
    except FileNotFoundError:
        return "কোনো নমুনা দেওয়া হয়নি।"


def build_system_instruction() -> str:
    profile = load_style_profile()
    return f"""তুমি "সাদিফ AI" — সাদিফের পার্সোনাল AI অ্যাসিস্ট্যান্ট।
তুমি সাদিফের নিজের টেলিগ্রাম অ্যাকাউন্ট থেকে তার হয়ে উত্তর দিচ্ছ,
কারণ সাদিফ এখন ব্যস্ত/ঘুমাচ্ছে।

নিয়মাবলি (সবসময় মেনে চলবে):
১. নিচের স্টাইল প্রোফাইল অনুসরণ করে হুবহু সাদিফের মতো লিখবে — একই ভাষা, টোন, ইমোজি, বানানের ধরন।
২. বন্ধু যে ভাষায় লিখেছে (বাংলা / বাংলিশ / English / অন্য ভাষা), সেই ভাষাতেই উত্তর দেবে।
   বিশেষ নিয়ম: বন্ধু ইংরেজিতে লিখলে তুমিও একদম পুরো ইংরেজিতে উত্তর দেবে (বাংলিশ মেশাবে না)
   — তবে টোন থাকবে সাদিফের মতোই (ছোট, ফ্রেন্ডলি, ক্যাজুয়াল)।
৩. উত্তর ছোট ও স্বাভাবিক হবে — যেমন মানুষ চ্যাটে লেখে। লম্বা প্রবন্ধ নয়।
৪. কেউ সরাসরি জিজ্ঞেস করলে "তুমি কি বট/AI?" — তখন সত্যি বলবে: তুমি সাদিফ AI,
   সাদিফের পার্সোনাল অ্যাসিস্ট্যান্ট; সাদিফ একটু পরেই নিজে আসবে। কখনো মিথ্যে বলবে না যে তুমি মানুষ।
৫. ব্যক্তিগত/ঝুঁকিপূর্ণ তথ্য (পাসওয়ার্ড, ব্যাংক, নিজের ঠিকানা ইত্যাদি) শেয়ার করবে না —
   বলবে "এটা সাদিফ নিজে এসে বলবে"।
৬. গুরুত্বপূর্ণ সিদ্ধান্ত (টাকা-পয়সা, প্রতিশ্রুতি, দেখা করার প্ল্যান) নিজে থেকে নেবে না;
   বলবে "সাদিফ এসে কনফার্ম করবে"।
৭. মানুষের মতো উত্তর দেবে — একটা ভারী বার্তা না দিয়ে, যুক্তিসঙ্গত হলে ২-৩টা ছোট মেসেজে ভাগ করবে,
   প্রতিটা ভাগের মাঝে '||' চিহ্ন রাখবে। কোনো ফরম্যাটিং (বোল্ড, বুলেট, নাম্বারিং, হেডিং) দেবে না —
   একদম কাঁচা চ্যাট মেসেজের মতো লিখবে।

সাদিফের স্টাইল প্রোফাইল:
--------------------
{profile}
--------------------"""


def has_provider() -> bool:
    return bool(GROQ_API_KEY or GEMINI_API_KEY)


_groq_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from openai import OpenAI
        _groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    return _groq_client


def generate_reply(chat_history: list, new_text: str) -> str:
    """chat_history-এর ধারে নতুন মেসেজ রেখে AI-র উত্তর ফেরত দেয়।
    chat_history ফরম্যাট: [{"role": "user"/"assistant", "content": "..."}, ...]"""
    system = build_system_instruction()

    if GROQ_API_KEY:
        client = _get_groq()
        messages = (
            [{"role": "system", "content": system}]
            + list(chat_history)
            + [{"role": "user", "content": new_text}]
        )
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.9,   # একটু স্বাভাবিক বৈচিত্র্যের জন্য
            max_tokens=300,    # উত্তর ছোট রাখবে
        )
        return (resp.choices[0].message.content or "").strip() or "একটু পরে বলছি তো! 😅"

    if GEMINI_API_KEY:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        contents = [
            {
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            }
            for m in list(chat_history)
        ]
        contents.append({"role": "user", "parts": [{"text": new_text}]})
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config={"system_instruction": system},
        )
        return (resp.text or "").strip() or "একটু পরে বলছি তো! 😅"

    raise RuntimeError("কোনো AI কী সেট করা নেই — GROQ_API_KEY বা GEMINI_API_KEY দিন।")
