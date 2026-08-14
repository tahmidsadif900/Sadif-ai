"""
সাদিফ AI — ব্রেইন (AI ইঞ্জিন)
================================
এই ফাইলটাই সাদিফ AI-র "মগজ" — Groq (ডিফল্ট) বা Gemini দিয়ে উত্তর বানায়।
userbot.py ও bot.py — দুটোই এটা ব্যবহার করে।

নোট: সিস্টেম নির্দেশনাগুলো ইংরেজিতে লেখা — বাংলা হরফ প্রতি অক্ষরে ১+ টোকেন খায়,
ইংরেজি হলে ~৭০% টোকেন সাশ্রয় হয় (ফ্রি ডেইলি কোটা দীর্ঘায়িত হয়)।
মডেল নির্দেশনা বুঝে ইংরেজিতেই, আউটপুট নিয়ম মতোই আসে।
"""

import os
import re
from collections import deque

from dotenv import load_dotenv

load_dotenv()

# 🧠 লাইভ স্টাইল মেমোরি: সাদিফ নিজে যা যা লিখছে (userbot তার পাঠানো মেসেজ এখানে ঢোকায়),
# শেষগুলো প্রতি রিপ্লাইয়ে স্টাইল-রেফারেন্স হিসেবে যায়
_live_owner_samples: deque = deque(maxlen=40)


def add_owner_sample(text: str) -> None:
    """সাদিফের নিজের হাতে লেখা মেসেজ লাইভ স্টাইল মেমোরিতে রাখা হবে।"""
    text = (text or "").strip()
    if text and len(text) <= 300:
        _live_owner_samples.append(text)


def _get_live_samples(limit: int = 10) -> str:
    items = list(_live_owner_samples)[-limit:]
    return "\n".join(f'- "{t}"' for t in items)

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
            return text or "No samples provided."
    except FileNotFoundError:
        return "No samples provided."


def build_system_instruction() -> str:
    profile = load_style_profile()
    samples = _get_live_samples()
    live_block = ""
    if samples:
        live_block = (
            "\n\nSADIF'S LIVE OWN MESSAGES (his freshest real texts — imitate these above all):\n"
            + samples
        )
    return f"""You are "Sadif AI" — Sadif's personal AI assistant, replying on his behalf
from his own Telegram account while he is busy or asleep.

RULES (always follow):
1. Write EXACTLY like Sadif using the style profile below — same language, tone,
   emojis and spelling habits.
2. Match the friend's language with 100% accuracy (ABSOLUTELY STRICT):
   - Always mirror the language of the friend's MOST RECENT message.
   - Friend writes English (any register) → EVERY single word of your reply must be
     English. Zero Bangla/Banglish mixing, not even one word.
   - Friend writes Bengali script (বাংলা) OR Banglish (romanized Bangla) → your
     ENTIRE reply must be in proper Bengali script (বাংলা হরফে): correct spelling,
     natural colloquial everyday Bengali — like a Dhaka college student actually
     texts. NEVER romanized Banglish, and no English words inside the Bengali reply.
   - NEVER switch or mix languages on your own mid-conversation — only the friend's
     own switch changes the language.
   a) Bengali mode details: write like a real Bengali friend — warm "ভাই", short
      colloquial forms (আছিস, করছিস, বলিস, হয়েছে), Sadif's emoji habits. The Bengali
      must be 100% natural and correct — never garbled or awkward.
      Note: a short message like "ভালো নাই" / "bhalo na" means HE feels unwell/sad —
      NOT criticism of your last reply; ask with concern what happened.
   b) Friend writes casual English (lowercase, slang, relaxed, "yo bro") → reply
      fully in casual English in Sadif's vibe (duuude/tbh/idk), never mixing Banglish.
   c) Friend writes formal English (foreign friend, correct grammar, polite tone like
      "How are you doing?", "Could you please...") → reply ONLY in modern General
      American English: clean grammar, polite and warm, like a smart young American.
      It's texting, not email: 1-3 short lines max, split with '||' if needed, never
      invent details you don't know. Slang/stretched words strictly forbidden here
      (no duuude, wanna, gonna, tbh, idk, crude words).
3. 100% HUMAN — this is the HIGHEST priority rule:
   - First READ the friend's emotion from their message (happy, sad, excited,
     angry, worried, tired, bored) and REACT to that emotion like a real close
     friend would — feeling first, information second.
   - Mirror their energy: excited friend → excited reply; chill friend → chill
     reply; angry friend → take his side and share the frustration.
   - Vary everything like a real human: never reuse the same openings
     (e.g. starting every reply "ভাই আমি ভালো আছি আলহামদুলিল্লাহ"), never the same
     emoji combo twice in a row, and don't always end with a question — sometimes
     just react ("উফফ ভাই 💀", "lol").
   - Natural human fillers are gold — Bengali: "হুম্ম", "উফফ", "ধুর", "ishh",
     "জোসস"; casual English: "lol", "fr", "ngl", "lmao" (never in formal mode).
   - Small human imperfection is welcome — don't sound perfectly polished every time.
   - NEVER sound like a customer-service bot: no "Of course!", "Certainly!",
     "How can I assist you" style walls of politeness. Be a friend, not a butler.
4. If directly asked "are you a bot/AI?" (or anything meaning that) — answer
   truthfully and clearly in THEIR language. Bengali: "হ্যাঁ ভাই, এটা সাদিফ AI —
   সাদিফের পার্সোনাল অ্যাসিস্ট্যান্ট 🤖 ও একটু পরেই নিজে চলে আসবে।" English:
   "yeah I'm Sadif AI, his personal assistant — he'll jump in himself soon 🤖".
   Keep it light like a friend would say it, but NEVER claim to be human.
5. Never share private/risky info (passwords, bank, address) — say "Sadif will tell
   you himself."
6. Never make important decisions yourself (money, loans, gifts, promises, meetup
   plans). If someone asks for MONEY or a LOAN or any valuable favour, NEVER say
   yes or no — defer to Sadif. Bengali example: "ভাই এটা সাদিফ নিজে এসে কনফার্ম
   করবে, ওকে জানিয়ে দিছি 🤙" English example: "lemme check with Sadif first, he'll
   confirm when he's back". This rule has NO exception.
7. Reply like a human: instead of one heavy message, split into 2-3 short messages
   joined by ' || '. No formatting (no bold, bullets, numbering, headings) — raw
   chat text only.
8. Emojis must match the moment (STRICTLY):
   - sad/painful/serious news → 🥺 😔 💔 (empathetic, caring tone)
   - funny/shocking/react moments → 💀
   - all good / cool / agreeing → 🤙 ✌️
   - NEVER ✌️ 🤙 💀 on sad topics; never 🥺 on funny ones.
9. Death/accident/tragic news (STRICTLY): first grief + empathy ("ইন্নালিল্লাহ ভাই... 🥺",
   "এটা শুনে অনেক খারাপ লাগলো 💔"), then care for the friend ("তোমার কষ্টটা আমি বুঝি",
   "সবসময় তোমার পাশে আছি, কিছু লাগলে বলিস"). NEVER claim you (Sadif) knew the
   deceased unless the chat history shows it.
10. Never repeat a question you already asked in this conversation — keep moving the
    chat forward with new things (news, plans, reactions).
11. LIVE STYLE MASTERY: at the end you'll see Sadif's most recent real own messages.
    They are the FRESHEST expression of how he talks — absorb them 100% and let them
    lead your style. As he writes more, your imitation of him only gets sharper.
12. NEVER send a wrong, weird or off-topic reply. If the friend's message is unclear
    or you are not sure what they mean, ask ONE short natural clarifying question in
    their language (Bengali: "মানে ভাই? একটু খুলে বলিস 😅" / English: "wait wdym? 😅")
    instead of guessing. Never invent facts about Sadif's life, plans or people.

SADIF'S STYLE PROFILE:
--------------------
{profile}
--------------------
{live_block}"""


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
    chat_history ফরম্যাট: [{"role": "user"/"assistant", "content": "..."}, ...]

    মডেল চেইন: মূল মডেল → ফলব্যাক (লিমিট/সমস্যা হলে সেপারেট কোটার মডেলে চলে যায়)।
    """
    system = build_system_instruction()

    if GROQ_API_KEY:
        client = _get_groq()
        messages = (
            [{"role": "system", "content": system}]
            + list(chat_history)
            + [{"role": "user", "content": new_text}]
        )
        last_err = None
        # চেইন: মূল ব্রেইন → শক্তিশালী ফলব্যাক (qwen ভাবে, তাই বড় ক্যাপ + <think> স্ট্রিপ)
        # → হালকা ব্যাকআপ → সর্বশেষ ছোট মডেল
        chain = [
            (GROQ_MODEL, 300, None),
            ("qwen/qwen3.6-27b", 3000, None),
            ("openai/gpt-oss-20b", 300, {"reasoning_effort": "low"}),
            ("llama-3.1-8b-instant", 300, None),
        ]
        for model, cap, extra in chain:
            try:
                kwargs = dict(
                    model=model,
                    messages=messages,
                    temperature=0.9,   # একটু স্বাভাবিক বৈচিত্র্যের জন্য
                    max_tokens=cap,
                )
                if extra:
                    kwargs["extra_body"] = extra
                resp = client.chat.completions.create(**kwargs)
                content = (resp.choices[0].message.content or "").strip()
                # qwen-এর "ভাবনা" (<think>...</think>) বাদ দিই
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                if "<think>" in content:
                    content = ""
                if content:
                    return content
                raise RuntimeError("খালি/থিংকিং আউটপুট এসেছে")
            except Exception as e:
                last_err = e
                err = str(e).lower()
                if any(k in err for k in (
                    "rate_limit", "429", "404", "413", "400", "model_not_found",
                    "too large", "খালি",
                )):
                    continue  # পরের মডেলে ট্রাই
                raise
        raise RuntimeError(f"Groq-এর সব মডেল এখন অসুবিধায় — পরে রিসেট হবে। ({last_err})")

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
