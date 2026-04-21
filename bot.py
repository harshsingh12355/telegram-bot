import logging
import os
import json
import datetime
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, JobQueue
)
import httpx
 
# ── Tokens (set as Railway environment variables) ──────────────────
TELEGRAM_TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")   # openweathermap.org (free)
NEWS_API_KEY    = os.environ.get("NEWS_API_KEY")       # newsapi.org (free)
YOUR_CHAT_ID    = os.environ.get("YOUR_CHAT_ID")       # your Telegram user ID
 
# ── Simple file-based storage ──────────────────────────────────────
DATA_FILE = "data.json"
 
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"todos": [], "notes": [], "expenses": [], "habits": {}, "reminders": []}
 
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
 
# ── Gemini AI helper ───────────────────────────────────────────────
async def ask_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not set. Add GEMINI_API_KEY in Railway Variables."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload)
        result = r.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "⚠️ Gemini error. Please try again."
 
# ── Main Menu keyboard ─────────────────────────────────────────────
def main_menu():
    keyboard = [
        ["🧠 Ask AI",        "📋 To-Do List"],
        ["📝 Notes",         "💰 Expenses"],
        ["✅ Habits",        "⏰ Reminders"],
        ["🌤 Morning Brief", "🏏 Cricket Score"],
        ["💼 Interview Prep","🌍 Translate"],
        ["✍️ Fix Grammar",   "😂 Joke / Quote"],
        ["📊 My Summary",    "❓ Help"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
 
# ══════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hey {name}! I'm your Personal AI Assistant!\n\n"
        "I can help you with:\n"
        "🧠 AI answers  📋 Tasks  📝 Notes\n"
        "💰 Expenses  ✅ Habits  ⏰ Reminders\n"
        "🌤 Daily Brief  🏏 Cricket  💼 Jobs\n"
        "🌍 Translate  ✍️ Grammar  😂 Jokes\n\n"
        "Use the menu below or just type anything!",
        reply_markup=main_menu()
    )
 
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *ALL COMMANDS*\n\n"
        "*AI Features:*\n"
        "🧠 Ask AI — Smart AI replies\n"
        "💼 Interview Prep — Practice interviews\n"
        "🌍 Translate — Translate any text\n"
        "✍️ Fix Grammar — Fix your English\n\n"
        "*Personal Tools:*\n"
        "📋 To-Do List — Manage your tasks\n"
        "📝 Notes — Save important notes\n"
        "💰 Expenses — Track spending in ₹\n"
        "✅ Habits — Build daily habits\n"
        "⏰ Reminders — Set reminders\n\n"
        "*Info & Fun:*\n"
        "🌤 Morning Brief — Weather + News\n"
        "🏏 Cricket Score — Live IPL scores\n"
        "😂 Joke / Quote — Fun content\n"
        "📊 My Summary — Your daily stats\n",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
 
# ══════════════════════════════════════════════════════════════════
#  AI FEATURES
# ══════════════════════════════════════════════════════════════════
 
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "ai"
    await update.message.reply_text("🧠 Ask me anything! Type your question:")
 
async def interview_prep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "interview"
    await update.message.reply_text(
        "💼 *Interview Prep Mode*\n\n"
        "Tell me the company or role and I'll give you questions + answers!\n\n"
        "Example: _TCS frontend developer interview_",
        parse_mode="Markdown"
    )
 
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "translate"
    await update.message.reply_text(
        "🌍 *Translator*\n\nFormat: `[language] [text]`\n\n"
        "Example: _Hindi Hello, how are you?_",
        parse_mode="Markdown"
    )
 
async def fix_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "grammar"
    await update.message.reply_text("✍️ Send me any text and I'll fix the grammar!")
 
# ══════════════════════════════════════════════════════════════════
#  TO-DO LIST
# ══════════════════════════════════════════════════════════════════
 
async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    todos = data["todos"]
    if not todos:
        msg = "📋 *Your To-Do List is empty!*\n\nTo add a task type:\n`/add Buy groceries`"
    else:
        msg = "📋 *Your To-Do List:*\n\n"
        for i, t in enumerate(todos, 1):
            status = "✅" if t.get("done") else "⬜"
            msg += f"{status} {i}. {t['task']}\n"
        msg += "\n`/add [task]` — Add task\n`/done [number]` — Mark done\n`/remove [number]` — Remove"
    await update.message.reply_text(msg, parse_mode="Markdown")
 
async def add_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = " ".join(context.args)
    if not task:
        await update.message.reply_text("Usage: `/add Buy groceries`", parse_mode="Markdown")
        return
    data = load_data()
    data["todos"].append({"task": task, "done": False, "date": str(datetime.date.today())})
    save_data(data)
    await update.message.reply_text(f"✅ Added: *{task}*", parse_mode="Markdown")
 
async def done_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(context.args[0]) - 1
        data = load_data()
        data["todos"][idx]["done"] = True
        save_data(data)
        await update.message.reply_text(f"🎉 Task {idx+1} marked as done!")
    except Exception:
        await update.message.reply_text("Usage: `/done 1`", parse_mode="Markdown")
 
async def remove_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(context.args[0]) - 1
        data = load_data()
        removed = data["todos"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"🗑 Removed: *{removed['task']}*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/remove 1`", parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  NOTES
# ══════════════════════════════════════════════════════════════════
 
async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["notes"]:
        msg = "📝 *No notes saved yet!*\n\nType: `/note Your note here`"
    else:
        msg = "📝 *Your Notes:*\n\n"
        for i, n in enumerate(data["notes"], 1):
            msg += f"{i}. {n['text']} _(_{n['date']}_)_\n"
        msg += "\n`/note [text]` — Add note\n`/delnote [number]` — Delete note"
    await update.message.reply_text(msg, parse_mode="Markdown")
 
async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: `/note Meeting at 3pm tomorrow`", parse_mode="Markdown")
        return
    data = load_data()
    data["notes"].append({"text": text, "date": str(datetime.date.today())})
    save_data(data)
    await update.message.reply_text(f"📝 Note saved: *{text}*", parse_mode="Markdown")
 
async def del_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(context.args[0]) - 1
        data = load_data()
        removed = data["notes"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"🗑 Deleted note: *{removed['text']}*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/delnote 1`", parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  EXPENSE TRACKER
# ══════════════════════════════════════════════════════════════════
 
async def expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    exps = data["expenses"]
    if not exps:
        msg = "💰 *No expenses recorded yet!*\n\nType: `/spend 150 Food`"
    else:
        total = sum(e["amount"] for e in exps)
        msg = "💰 *Your Expenses:*\n\n"
        for e in exps[-10:]:
            msg += f"• ₹{e['amount']} — {e['category']} ({e['date']})\n"
        msg += f"\n💸 *Total: ₹{total}*\n\n`/spend [amount] [category]` — Add expense\n`/clearexp` — Clear all"
    await update.message.reply_text(msg, parse_mode="Markdown")
 
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        category = " ".join(context.args[1:]) or "General"
        data = load_data()
        data["expenses"].append({
            "amount": amount, "category": category,
            "date": str(datetime.date.today())
        })
        save_data(data)
        await update.message.reply_text(f"💸 Recorded: ₹{amount} for *{category}*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/spend 150 Food`", parse_mode="Markdown")
 
async def clear_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["expenses"] = []
    save_data(data)
    await update.message.reply_text("🗑 All expenses cleared!")
 
# ══════════════════════════════════════════════════════════════════
#  HABIT TRACKER
# ══════════════════════════════════════════════════════════════════
 
async def habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    h = data["habits"]
    today = str(datetime.date.today())
    if not h:
        msg = "✅ *No habits added yet!*\n\nType: `/addhabit Exercise`"
    else:
        msg = f"✅ *Habit Tracker — {today}*\n\n"
        for habit, info in h.items():
            done_today = today in info.get("done_dates", [])
            streak = info.get("streak", 0)
            status = "✅" if done_today else "⬜"
            msg += f"{status} {habit} — 🔥 {streak} day streak\n"
        msg += "\n`/addhabit [name]` — Add habit\n`/did [habit]` — Mark done today"
    await update.message.reply_text(msg, parse_mode="Markdown")
 
async def add_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    habit = " ".join(context.args)
    if not habit:
        await update.message.reply_text("Usage: `/addhabit Exercise`", parse_mode="Markdown")
        return
    data = load_data()
    data["habits"][habit] = {"streak": 0, "done_dates": []}
    save_data(data)
    await update.message.reply_text(f"✅ Habit added: *{habit}*", parse_mode="Markdown")
 
async def did_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    habit = " ".join(context.args)
    today = str(datetime.date.today())
    data = load_data()
    if habit not in data["habits"]:
        await update.message.reply_text(f"❌ Habit '{habit}' not found. Use `/addhabit {habit}` first.", parse_mode="Markdown")
        return
    h = data["habits"][habit]
    if today not in h["done_dates"]:
        h["done_dates"].append(today)
        h["streak"] = h.get("streak", 0) + 1
        save_data(data)
        await update.message.reply_text(f"🔥 Great job! *{habit}* done today!\nStreak: {h['streak']} days!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"✅ You already completed *{habit}* today!", parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  REMINDERS
# ══════════════════════════════════════════════════════════════════
 
async def reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "reminder"
    await update.message.reply_text(
        "⏰ *Set a Reminder*\n\n"
        "Format: `[minutes] [message]`\n\n"
        "Example: _30 Call mom_\n"
        "_(This will remind you after 30 minutes)_",
        parse_mode="Markdown"
    )
 
# ══════════════════════════════════════════════════════════════════
#  MORNING BRIEFING
# ══════════════════════════════════════════════════════════════════
 
async def morning_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌤 Fetching your morning brief...")
    brief = f"🌅 *Good Morning! — {datetime.date.today().strftime('%d %B %Y')}*\n\n"
 
    # Weather
    if WEATHER_API_KEY:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.get(
                    f"https://api.openweathermap.org/data/2.5/weather",
                    params={"q": "Begusarai,IN", "appid": WEATHER_API_KEY, "units": "metric"}
                )
                w = r.json()
                temp = w["main"]["temp"]
                desc = w["weather"][0]["description"].title()
                brief += f"🌡 *Weather in Begusarai:*\n{desc}, {temp}°C\n\n"
            except:
                brief += "🌡 Weather unavailable\n\n"
    else:
        brief += "🌡 Add WEATHER_API_KEY in Railway Variables for weather\n\n"
 
    # News
    if NEWS_API_KEY:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"country": "in", "pageSize": 5, "apiKey": NEWS_API_KEY}
                )
                news = r.json()
                brief += "📰 *Top News Today:*\n"
                for i, a in enumerate(news.get("articles", [])[:5], 1):
                    brief += f"{i}. {a['title']}\n"
            except:
                brief += "📰 News unavailable\n"
    else:
        brief += "📰 Add NEWS_API_KEY in Railway Variables for news\n"
 
    # Todo summary
    data = load_data()
    pending = [t for t in data["todos"] if not t.get("done")]
    if pending:
        brief += f"\n📋 *Pending Tasks: {len(pending)}*\n"
        for t in pending[:3]:
            brief += f"• {t['task']}\n"
 
    await update.message.reply_text(brief, parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  CRICKET SCORES
# ══════════════════════════════════════════════════════════════════
 
async def cricket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏏 Fetching live cricket scores...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
                headers={
                    "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY", ""),
                    "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
                })
            matches = r.json()
            msg = "🏏 *Live Cricket Scores:*\n\n"
            found = False
            for match in matches.get("typeMatches", []):
                for series in match.get("seriesMatches", []):
                    for m in series.get("seriesAdWrapper", {}).get("matches", [])[:3]:
                        info = m.get("matchInfo", {})
                        score = m.get("matchScore", {})
                        t1 = info.get("team1", {}).get("teamSName", "")
                        t2 = info.get("team2", {}).get("teamSName", "")
                        status = info.get("status", "")
                        msg += f"*{t1} vs {t2}*\n_{status}_\n\n"
                        found = True
            if not found:
                msg = "🏏 No live matches right now!\nCheck back during match time 🕐"
    except Exception:
        msg = ("🏏 Add RAPIDAPI_KEY in Railway Variables for live scores!\n\n"
               "Get free key at: rapidapi.com\nSearch: Cricbuzz API")
    await update.message.reply_text(msg, parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  JOKE / QUOTE
# ══════════════════════════════════════════════════════════════════
 
async def joke_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😂 Fetching something fun...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,racist")
            j = r.json()
            if j["type"] == "single":
                msg = f"😂 *Joke:*\n\n{j['joke']}"
            else:
                msg = f"😂 *Joke:*\n\n{j['setup']}\n\n_{j['delivery']}_"
    except Exception:
        msg = "😄 Why do programmers prefer dark mode?\nBecause light attracts bugs! 🐛"
    await update.message.reply_text(msg, parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  MY SUMMARY
# ══════════════════════════════════════════════════════════════════
 
async def my_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    today = str(datetime.date.today())
    pending_todos = len([t for t in data["todos"] if not t.get("done")])
    done_todos    = len([t for t in data["todos"] if t.get("done")])
    total_notes   = len(data["notes"])
    total_exp     = sum(e["amount"] for e in data["expenses"])
    today_exp     = sum(e["amount"] for e in data["expenses"] if e["date"] == today)
    habits_done   = sum(1 for h in data["habits"].values() if today in h.get("done_dates", []))
    total_habits  = len(data["habits"])
 
    msg = (
        f"📊 *Your Daily Summary — {today}*\n\n"
        f"📋 Tasks: {done_todos} done, {pending_todos} pending\n"
        f"📝 Notes saved: {total_notes}\n"
        f"💰 Today's spending: ₹{today_exp} | Total: ₹{total_exp}\n"
        f"✅ Habits: {habits_done}/{total_habits} done today\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
 
# ══════════════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════
 
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode", "")
 
    # Menu button routing
    routes = {
        "🧠 Ask AI":          ask_ai,
        "📋 To-Do List":      todo,
        "📝 Notes":           notes,
        "💰 Expenses":        expenses,
        "✅ Habits":          habits,
        "⏰ Reminders":       reminder,
        "🌤 Morning Brief":   morning_brief,
        "🏏 Cricket Score":   cricket,
        "💼 Interview Prep":  interview_prep,
        "🌍 Translate":       translate,
        "✍️ Fix Grammar":     fix_grammar,
        "😂 Joke / Quote":    joke_quote,
        "📊 My Summary":      my_summary,
        "❓ Help":            help_command,
    }
    if text in routes:
        context.user_data["mode"] = ""
        await routes[text](update, context)
        return
 
    # Mode-based AI handling
    if mode == "ai":
        context.user_data["mode"] = ""
        await update.message.reply_text("🧠 Thinking...")
        reply = await ask_gemini(f"You are a helpful personal assistant. Answer concisely:\n{text}")
        await update.message.reply_text(reply)
 
    elif mode == "interview":
        context.user_data["mode"] = ""
        await update.message.reply_text("💼 Preparing interview questions...")
        prompt = (f"Give me 10 important interview questions with brief answers for: {text}. "
                  f"Format nicely with Q: and A: labels.")
        reply = await ask_gemini(prompt)
        await update.message.reply_text(reply)
 
    elif mode == "translate":
        context.user_data["mode"] = ""
        await update.message.reply_text("🌍 Translating...")
        reply = await ask_gemini(f"Translate the following text as requested. Only give the translation, nothing else: {text}")
        await update.message.reply_text(reply)
 
    elif mode == "grammar":
        context.user_data["mode"] = ""
        await update.message.reply_text("✍️ Fixing grammar...")
        reply = await ask_gemini(
            f"Fix the grammar of this text. Show the corrected version and briefly explain the changes:\n{text}"
        )
        await update.message.reply_text(reply)
 
    elif mode == "reminder":
        context.user_data["mode"] = ""
        try:
            parts = text.split(" ", 1)
            minutes = int(parts[0])
            msg = parts[1] if len(parts) > 1 else "Reminder!"
            async def send_reminder():
                await asyncio.sleep(minutes * 60)
                await update.message.reply_text(f"⏰ *REMINDER:* {msg}", parse_mode="Markdown")
            asyncio.create_task(send_reminder())
            await update.message.reply_text(f"⏰ Reminder set! I'll remind you in *{minutes} minutes*: _{msg}_", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("Format: `30 Call mom`\n_(minutes followed by message)_", parse_mode="Markdown")
 
    else:
        # Default — smart AI reply
        await update.message.reply_text("🧠 Thinking...")
        reply = await ask_gemini(f"You are a helpful personal assistant. Answer concisely:\n{text}")
        await update.message.reply_text(reply)
 
# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
 
logging.basicConfig(level=logging.INFO)
 
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
 
app.add_handler(CommandHandler("start",      start))
app.add_handler(CommandHandler("help",       help_command))
app.add_handler(CommandHandler("add",        add_todo))
app.add_handler(CommandHandler("done",       done_todo))
app.add_handler(CommandHandler("remove",     remove_todo))
app.add_handler(CommandHandler("note",       add_note))
app.add_handler(CommandHandler("delnote",    del_note))
app.add_handler(CommandHandler("spend",      add_expense))
app.add_handler(CommandHandler("clearexp",   clear_expenses))
app.add_handler(CommandHandler("addhabit",   add_habit))
app.add_handler(CommandHandler("did",        did_habit))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
 
print("🤖 Personal Assistant Bot is running...")
app.run_polling()
