import feedparser
import asyncio
import sys
import json
import os
import time as time_module
from datetime import time
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8297166958:AAHYImxX6oSoEA8QnQcaT1eSq84LPeIe9Ys"
SUBSCRIBERS_FILE = "subscribers.json"

CATEGORIES = {
    "🔬 Конкуренты": [
        "https://news.google.com/rss/search?q=circadian+rhythm+startup+funding&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=sleep+tracking+startup+raised&hl=en&gl=US&ceid=US:en",
    ],
    "⌚ Потенциальные клиенты": [
        "https://news.google.com/rss/search?q=smartwatch+company+funding&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=wearable+health+platform+raised&hl=en&gl=US&ceid=US:en",
    ],
    "📈 Рынок": [
        "https://news.google.com/rss/search?q=digital+wellness+wearable+Series+A&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=wearable+health+SDK+investment&hl=en&gl=US&ceid=US:en",
    ],
}

SKIP = ["apple", "samsung", "fitbit", "google", "microsoft", "anthropic", "amazon", "meta"]
FUNDING = ["fund", "raise", "raised", "million", "invest", "series", "seed", "round", "capital"]

def load_subs():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE) as f:
            return set(json.load(f))
    return {6797169}

def save_subs(s):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(s), f)

def fetch():
    results = {cat: [] for cat in CATEGORIES}
    seen_links = set()
    for cat, feeds in CATEGORIES.items():
        for url in feeds:
            feed = feedparser.parse(url)
            for e in feed.entries:
                t = e.get("title", "")
                l = e.get("link", "")
                if l in seen_links:
                    continue
                if any(c in t.lower() for c in SKIP):
                    continue
                if not any(w in t.lower() for w in FUNDING):
                    continue
                published = e.get("published_parsed")
                if published:
                    age_days = (time_module.time() - time_module.mktime(published)) / 86400
                    if age_days > 30:
                        continue
                seen_links.add(l)
                results[cat].append((t, l))
    return results

async def send_to(bot, chat_id):
    news = fetch()
    total = sum(len(v) for v in news.values())
    if total == 0:
        await bot.send_message(chat_id=chat_id, text="Новостей не найдено.")
        return
    msg = "📡 *Дайджест финансирования* — " + str(total) + " новостей\n\n"
    for cat, items in news.items():
        if not items:
            continue
        msg += "*" + cat + "* (" + str(len(items)) + ")\n"
        for t, l in items:
            item = "• [" + t + "](" + l + ")\n"
            if len(msg) + len(item) > 4000:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
                msg = item
            else:
                msg += item
        msg += "\n"
    if msg.strip():
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", disable_web_page_preview=True)

async def daily(context):
    for cid in load_subs():
        await send_to(context.bot, cid)

async def start(update, context):
    cid = update.effective_chat.id
    s = load_subs()
    s.add(cid)
    save_subs(s)
    await update.message.reply_text("✅ Подписан! Дайджест приходит каждый день в 9:00. /news — получить сейчас.")

async def stop(update, context):
    cid = update.effective_chat.id
    s = load_subs()
    s.discard(cid)
    save_subs(s)
    await update.message.reply_text("❌ Отписан.")

async def news_now(update, context):
    await update.message.reply_text("Собираю новости...")
    await send_to(context.bot, update.effective_chat.id)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("news", news_now))
    app.job_queue.run_daily(daily, time=time(9, 0))
    print("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(send_to(Bot(TOKEN), 6797169))
    else:
        main()
