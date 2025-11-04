import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, firestore
import flask
import threading
import os

# Render এর Environment Variable থেকে টোকেন লোড করা হবে
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_WEB_APP_URL = "https://your-webapp-link.com"  # এখানে আপনার ওয়েব অ্যাপের URL বসান

# Firebase Admin SDK ইনিশিয়ালাইজ করুন
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    print(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")
    db = None

# বট টোকেন না পেলে বট চালু হবে না
if not BOT_TOKEN:
    print("ত্রুটি: টেলিগ্রাম বটের টোকেন পাওয়া যায়নি। অনুগ্রহ করে Environment Variable সেট করুন।")
else:
    # বট এবং ফ্লাস্ক অ্যাপ অবজেক্ট তৈরি করুন
    bot = telebot.TeleBot(BOT_TOKEN)
    app = flask.Flask(__name__)

    # --- Flask Web Server অংশ (UptimeRobot এর জন্য) ---
    @app.route('/')
    def index():
        return "Bot is alive and polling!"

    # --- Telegram Bot অংশ ---
    def create_webapp_keyboard():
        keyboard = InlineKeyboardMarkup()
        web_app_button = InlineKeyboardButton(
            text="▶️ Open App",
            web_app=WebAppInfo(url=YOUR_WEB_APP_URL)
        )
        keyboard.add(web_app_button)
        return keyboard

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        user_name = message.from_user.first_name
        print(f"'/start' কমান্ড পাওয়া গেছে: {chat_id} ({user_name}) থেকে")
        
        welcome_message = f"👋 Hello, {user_name}!\n\nWelcome to our bot. Click the button below to start."
        
        try:
            if db:
                print("Firebase ডাটাবেস চেক করা হচ্ছে...")
                settings_ref = db.collection('settings').document('app')
                settings_doc = settings_ref.get()
                if settings_doc.exists:
                    print("সেটিংস ডকুমেন্ট পাওয়া গেছে।")
                    settings_data = settings_doc.to_dict()
                    if 'welcomeMessage' in settings_data and settings_data['welcomeMessage']:
                        welcome_message = settings_data['welcomeMessage'].replace('{name}', user_name)
                        print("কাস্টম ওয়েলকাম মেসেজ লোড করা হয়েছে।")
                else:
                    print("সেটিংস ডকুমেন্ট পাওয়া যায়নি। ডিফল্ট মেসেজ ব্যবহার করা হবে।")
        except Exception as e:
            print(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

        try:
            print(f"{chat_id}-কে মেসেজ পাঠানোর চেষ্টা করা হচ্ছে...")
            bot.send_message(
                chat_id, welcome_message, parse_mode="Markdown", reply_markup=create_webapp_keyboard()
            )
            print(f"{chat_id}-কে মেসেজ সফলভাবে পাঠানো হয়েছে।")
        except Exception as e:
            print(f"মেসেজ পাঠাতে একটি ত্রুটি হয়েছে: {e}")
            bot.send_message(
                chat_id, welcome_message, reply_markup=create_webapp_keyboard()
            )

    def run_bot_polling():
        print("বট পোলিং শুরু হচ্ছে...")
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"বট পোলিং এ একটি বড় ধরনের ত্রুটি হয়েছে: {e}")
            # আপনি চাইলে এখানে error টি লগ করতে পারেন বা রিস্টার্ট করার ব্যবস্থা করতে পারেন

    # --- মূল অংশ ---
    if __name__ == "__main__":
        print("অ্যাপ্লিকেশন চালু হচ্ছে...")
        bot_thread = threading.Thread(target=run_bot_polling)
        bot_thread.daemon = True
        bot_thread.start()

        port = int(os.environ.get("PORT", 5000))
        print(f"Flask সার্ভার {port} পোর্টে চালু হচ্ছে...")
        app.run(host='0.0.0.0', port=port)
