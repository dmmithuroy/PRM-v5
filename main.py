import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, firestore
import flask
import os

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
    print("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    db = None
    print(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")

# বট এবং ফ্লাস্ক অ্যাপ অবজেক্ট তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = flask.Flask(__name__)


# --- Webhook রুট (টেলিগ্রাম এখানে POST রিকোয়েস্ট পাঠাবে) ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        flask.abort(403)

# --- সাধারণ রুট (সার্ভার চালু আছে কিনা তা দেখার জন্য) ---
@app.route('/')
def index():
    return "Bot is alive using Webhook!"


# --- Telegram Bot এর মূল কোড ---
def create_webapp_keyboard():
    keyboard = InlineKeyboardMarkup()
    web_app_button = InlineKeyboardButton(text="▶️ Open App", web_app=WebAppInfo(url=YOUR_WEB_APP_URL))
    keyboard.add(web_app_button)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    print(f"'/start' কমান্ড পাওয়া গেছে: {chat_id} ({user_name}) থেকে")
    
    welcome_message = f"👋 Hello, {user_name}!\nWelcome! Click below to start."
    
    try:
        if db:
            settings_ref = db.collection('settings').document('app')
            settings_doc = settings_ref.get()
            if settings_doc.exists and 'welcomeMessage' in settings_doc.to_dict() and settings_doc.to_dict()['welcomeMessage']:
                welcome_message = settings_doc.to_dict()['welcomeMessage'].replace('{name}', user_name)
    except Exception as e:
        print(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

    bot.send_message(chat_id, welcome_message, reply_markup=create_webapp_keyboard())


# --- Webhook সেট করার অংশ (সার্ভার চালু হওয়ার পর শুধু একবার চলবে) ---
# এই অংশটি gunicorn দিয়ে চালালে সঠিকভাবে কাজ করে
if __name__ != '__main__':
    # Render সার্ভিসের URL টি স্বয়ংক্রিয়ভাবে পেতে
    RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
    if RENDER_EXTERNAL_URL:
        WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        print(f"Webhook সেট করা হচ্ছে: {WEBHOOK_URL}")
        bot.remove_webhook()
        # Webhook সেট করার জন্য ছোট একটি দেরি দেওয়া ভালো
        import time
        time.sleep(1) 
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook সফলভাবে সেট হয়েছে।")
