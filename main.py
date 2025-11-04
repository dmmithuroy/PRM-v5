import os
import logging
from dotenv import load_dotenv
from flask import Flask
import threading

from telegram import Update, WebAppInfo
from telegram.ext import Updater, CommandHandler, CallbackContext

import firebase_admin
from firebase_admin import credentials, firestore

# .env ফাইল থেকে Environment Variable গুলো লোড করুন (লোকাল পরীক্ষার জন্য)
load_dotenv()

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- আপনার তথ্য .env ফাইল বা Render Environment থেকে লোড হবে ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_WEB_APP_URL = os.environ.get("YOUR_WEB_APP_URL", "https://google.com")
# ------------------------------------

# Firebase ইনিশিয়ালাইজ করুন
db = None
try:
    # Render এ Secret File হিসেবে "serviceAccountKey.json" সেট করতে হবে
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    logger.error(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")

# --- Flask Web Server (UptimeRobot এর জন্য) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive and polling!"

def run_flask_app():
    # Render.com থেকে PORT নম্বরটি পেতে os.environ.get ব্যবহার করা হয়
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- Telegram Bot এর ফাংশন ---
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    logger.info(f"'/start' কমান্ড পাওয়া গেছে: {user.id} ({user.first_name}) থেকে")
    
    welcome_message = f"👋 Hello, {user.first_name}!\n\nWelcome! Click the button below to start."
    
    try:
        if db:
            settings_doc = db.collection('settings').document('app').get()
            if settings_doc.exists:
                settings_data = settings_doc.to_dict()
                if 'welcomeMessage' in settings_data and settings_data['welcomeMessage']:
                    welcome_message = settings_data['welcomeMessage'].replace('{name}', user.first_name)
    except Exception as e:
        logger.error(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

    keyboard = [[
        {"text": "▶️ Open App", "web_app": {"url": YOUR_WEB_APP_URL}}
    ]]
    update.message.reply_text(welcome_message, reply_markup={"inline_keyboard": keyboard})

# --- মূল অংশ ---
def main() -> None:
    if not BOT_TOKEN:
        logger.error("ত্রুটি: টেলিগ্রাম বটের টোকেন পাওয়া যায়নি। .env ফাইল বা Environment Variable চেক করুন।")
        return

    # Flask অ্যাপটিকে একটি আলাদা থ্রেডে (Thread) চালু করুন
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    logger.info("Flask সার্ভার একটি ব্যাকগ্রাউন্ড থ্রেডে চালু হয়েছে।")

    # Telegram Bot এর Updater তৈরি করুন
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # '/start' কমান্ডের জন্য হ্যান্ডলার যোগ করুন
    dispatcher.add_handler(CommandHandler("start", start))
    
    logger.info("বট Polling মোডে চালু হচ্ছে...")
    # Polling শুরু করুন
    updater.start_polling()
    # বটটি Ctrl+C চাপার আগ পর্যন্ত চলতে থাকবে
    updater.idle()

if __name__ == '__main__':
    main()
