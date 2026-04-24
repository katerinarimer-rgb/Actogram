import feedparser
import asyncio
import sys
import re
import json
import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8297166958:AAHYImxX6oSoEA8QnQcaT1eSq84LPeIe9Ys"
SUBSCRIBERS_FILE = "subscribers.json"

CATEGORIES = {
    "🔬 Конкуренты": [
        "https://news.google.com/rss/search?q=circadian+rhythm+startup+funding&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=sleep+tracking+startup+raised&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=chronobiology+wearable+investment&hl=en&gl=US&ceid=US:en",
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

SKIP_COMPANIES = ["apple", "samsung", "fitbit", "google", "microsoft", "anthropic", "amazon", "meta"]
SKIP_SOURCES = ["pr newswire", "kickstarter", "indiegogo", "globenewswire", "businesswire"]
FUNDING_WORDS = ["fund", "raise", "raised", "million", "invest", "series", "seed", "round", "capital", "backed"]
SKIP_TOPICS = ["fsa", "hsa", "gift", "recall", "lawsuit", "ipo canceled"]

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE) as f:
            return set(json.load(f))
    return {6797169}

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)

def extract_amount(title):
    match = re.search(r'\$(\d+(?:\.\d+)?)\s*(M|B|million|billion)', title, re.IGNORECASE)
    if match:
        amount = float(match.group(1))
        unit = match.group(2).upper()
        if unit in ['B', 'BILLION']:
            amount *= 1000
        return amount
    return None

def is_relevant(title, source=""):
    title_lower = title.lower()
    source_lower = source.lower()
    if any(c in title_lower for c in SKIP_COMPANIES):
        return False
    if any(s in source_lower for s in SKIP_SOURCES):
        return False
    if any(t in title_lower for t in SKIP_TOPICS):
        return False
    if not any(w in title_lower for w in FUNDING_WORDS):
        return False
    amount = extract_amount(title)
    if amount is not None and amount < 1:
        return False
    return True

seen_urls = set()

def fetch_news():
    results = {cat: [] for cat in CATEGORIES}
    for category, feeds in CATEGORIES.items():
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "")
                if link in seen_urls:
                    continue
                if not is_relevant(title, source):
                    continue
                seen_urls.add(link)
                results[category].append((title, link))
    return results

async def send_news_to(bot, chat_id):
    all_news = fetch_news()
    total = sum(len(v) for v in all_news.values())
    if total == 0:
        await bot.send_message(chat_id=chat_id, text="Новостей о финансировании за сегодня не найдено.")
        return
    header = f"📡 *Дайджест финансирования* — {total} новостей\n\n"
    message = header
    for category, items in all_news.items():
        if not items:
            continue
        message += f"*{category}* ({len(items)})\n"
        for title, link in items:
            item = f"• [{title}]({link})\n"
            if len(message) + len(item) > 4000:
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)
                message = item
            else:
                message += item
        message += "\n"
    if message.strip():
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown", disable_web_page_preview=True)

async def send_to_all(context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    for chat_id in subscribers:
        await send_news_to(context.bot, chat_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    subscribers.add(chat_id)
    save_subscribers(subscribers)
    await update.message.reply_text("✅ Ты подписан на дайджест финансирования в wearable/healthtech. Новости приходят каждый день в 9:00. Команда /news — получить сейчас.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    subscribers.discard(chat_id)
    save_subscribers(subscribers)
    await update.message.reply_text("❌ Ты отписан от дайджеста.")

async def news_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("Собираю новости, подожди...")
    await send_news_to(context.bot, chat_id)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("news", news_now))

    app.job_queue.run_daily(send_to_all, time=__import__('datetime').time(9, 0))

    print("Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(send_news_to(Bot(TOKEN), 6797169))
    else:
        main()
