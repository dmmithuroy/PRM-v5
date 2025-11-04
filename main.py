import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, firestore
import flask
import threading
import os

# --- আপনার তথ্য এখানে পরিবর্তন করুন ---
BOT_TOKEN = "8575729910:AAF3ny-2felQNP1wivoPsSWySsAfsXLH_P4"  # এখানে আপনার টেলিগ্রাম বটের টোকেন বসান
YOUR_WEB_APP_URL = "https://prm-v5.blogspot.com/"  # এখানে আপনার ওয়েব অ্যাপের URL বসান
# ------------------------------------

# Firebase Admin SDK ইনিশিয়ালাইজ করুন
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    print(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")
    db = None

# বট এবং ফ্লাস্ক অ্যাপ অবজেক্ট তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN)
app = flask.Flask(__name__)

# --- Flask Web Server অংশ (UptimeRobot এর জন্য) ---
# এই রুটটি UptimeRobot পিং করবে
@app.route('/')
def index():
    return "Bot is alive!"

# --- Telegram Bot অংশ ---

# Mini App খোলার জন্য বাটন তৈরি করার ফাংশন
def create_webapp_keyboard():
    keyboard = InlineKeyboardMarkup()
    web_app_button = InlineKeyboardButton(
        text="▶️ Open App",
        web_app=WebAppInfo(url=YOUR_WEB_APP_URL)
    )
    keyboard.add(web_app_button)
    return keyboard

# '/start' কমান্ডের জন্য হ্যান্ডলার
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    welcome_message = f"👋 Hello, {user_name}!\n\nWelcome to our bot. Click the button below to start."
    
    try:
        if db:
            settings_ref = db.collection('settings').document('app')
            settings_doc = settings_ref.get()
            if settings_doc.exists:
                settings_data = settings_doc.to_dict()
                if 'welcomeMessage' in settings_data and settings_data['welcomeMessage']:
                    welcome_message = settings_data['welcomeMessage'].replace('{name}', user_name)
    except Exception as e:
        print(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

    try:
        bot.send_message(
            chat_id, welcome_message, parse_mode="Markdown", reply_markup=create_webapp_keyboard()
        )
    except Exception:
        bot.send_message(
            chat_id, welcome_message, reply_markup=create_webapp_keyboard()
        )

# '/app' কমান্ডের জন্য হ্যান্ডলার
@bot.message_handler(commands=['app'])
def open_app(message):
    bot.send_message(
        message.chat.id, "Click the button below to open the app.", reply_markup=create_webapp_keyboard()
    )

# বটকে একটি আলাদা থ্রেডে (Thread) চালানোর জন্য ফাংশন
def run_bot_polling():
    print("বট পোলিং শুরু হচ্ছে...")
    bot.polling(none_stop=True)

# --- মূল অংশ ---
if __name__ == "__main__":
    # বটকে ব্যাকগ্রাউন্ডে চালানোর জন্য থ্রেড শুরু করুন
    bot_thread = threading.Thread(target=run_bot_polling)
    bot_thread.daemon = True
    bot_thread.start()

    # Flask ওয়েব সার্ভারটি চালু করুন (এটি UptimeRobot এর জন্য)
    # Render.com থেকে PORT নম্বরটি পেতে os.environ.get ব্যবহার করা হয়
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)