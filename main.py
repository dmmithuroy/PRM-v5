import os
import asyncio
import logging
from flask import Flask, request

from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

import firebase_admin
from firebase_admin import credentials, firestore

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- আপনার তথ্য ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# নিচের URL টি আপনার USER.txt এবং ADMIN.txt যে লিঙ্কে হোস্ট করা আছে, সেই লিঙ্ক হবে
YOUR_WEB_APP_URL = "https://your-user-facing-webapp-url.com" 
# ------------------------------------

# Firebase ইনিশিয়ালাইজ করুন
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    db = None
    logger.error(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")

# Telegram Application অবজেক্ট তৈরি করুন
application = Application.builder().token(BOT_TOKEN).build()

# --- Telegram Bot এর ফাংশন ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"'/start' কমান্ড পাওয়া গেছে: {user.id} ({user.first_name}) থেকে")

    welcome_message = f"👋 Hello, {user.first_name}!\n\nWelcome! Click the button below to start."
    
    try:
        if db:
            settings_ref = db.collection('settings').document('app')
            settings_doc = settings_ref.get()
            if settings_doc.exists:
                settings_data = settings_doc.to_dict()
                if 'welcomeMessage' in settings_data and settings_data['welcomeMessage']:
                    welcome_message = settings_data['welcomeMessage'].replace('{name}', user.first_name)
    except Exception as e:
        logger.error(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

    keyboard = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(
            text="▶️ Open App",
            web_app=WebAppInfo(url=YOUR_WEB_APP_URL)
        )
    )
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

# হ্যান্ডলার যোগ করুন
application.add_handler(CommandHandler("start", start))

# --- Flask Web Server এবং Webhook সেটআপ ---
app = Flask(__name__)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    update_json = request.get_json(force=True)
    update = Update.de_json(update_json, application.bot)
    await application.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return "Bot is alive and using Webhook!"

async def setup():
    # Render সার্ভিসের URL টি স্বয়ংক্রিয়ভাবে পেতে
    RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
    if not RENDER_EXTERNAL_URL:
        logger.error("RENDER_EXTERNAL_URL পাওয়া যায়নি, Webhook সেট করা সম্ভব নয়।")
        return

    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    logger.info(f"Webhook সেট করা হচ্ছে: {webhook_url}")

    # Webhook সেট করুন
    await application.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info("Webhook সফলভাবে সেট হয়েছে।")
    
    # Flask সার্ভারটি চালু করুন
    port = int(os.environ.get("PORT", 8080))
    # Werkzeug সার্ভার সরাসরি async ফাংশন সাপোর্ট করে না, তাই এই workaround
    # এটি Render-এর পরিবেশে সঠিকভাবে কাজ করবে
    from werkzeug.serving import run_simple
    run_simple(hostname="0.0.0.0", port=port, application=app, use_reloader=False)

# --- মূল অংশ যা `python main.py` দিয়ে চালানো হবে ---
if __name__ == '__main__':
    # Webhook সেট করুন এবং সার্ভার চালু করুন
    asyncio.run(setup())
