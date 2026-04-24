import feedparser
import asyncio
import sys
import re
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8297166958:AAHYImxX6oSoEA8QnQcaT1eSq84LPeIe9Ys"
CHAT_ID = 6797169

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

async def send_news():
    bot = Bot(token=TOKEN)
    all_news = fetch_news()
    total = sum(len(v) for v in all_news.values())

    if total == 0:
        await bot.send_message(chat_id=CHAT_ID, text="Новостей о финансировании за сегодня не найдено.")
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
                await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=True)
                message = item
            else:
                message += item
        message += "\n"

    if message.strip():
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_news, "cron", hour=9, minute=0)
    scheduler.start()
    print("Бот запущен. Дайджест будет приходить каждый день в 9:00.")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(send_news())
    else:
        asyncio.run(main())
