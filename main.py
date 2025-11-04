import os
import flask
from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# --- আপনার তথ্য ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# নিচের URL টি আপনার USER.txt এবং ADMIN.txt যে লিঙ্কে হোস্ট করা আছে, সেই লিঙ্ক হবে
YOUR_WEB_APP_URL = "https://prm-v5.blogspot.com/" 
# ------------------------------------

# Firebase সেটআপ (আপনার আগের কোড থেকে)
import firebase_admin
from firebase_admin import credentials, firestore

try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    db = None
    print(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")

# বট এবং ডিসপ্যাচার ইনিশিয়ালাইজ করুন
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)
app = flask.Flask(__name__)

# --- Webhook রুট ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook_handler():
    update = Update.de_json(flask.request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive with python-telegram-bot!'

# --- Telegram Bot এর ফাংশন ---
def create_webapp_keyboard():
    keyboard = InlineKeyboardMarkup.from_button(
        InlineKeyboardButton(text="▶️ Open App", web_app=WebAppInfo(url=YOUR_WEB_APP_URL))
    )
    return keyboard

def start(update, context):
    user = update.effective_user
    chat_id = user.id
    user_name = user.first_name
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

    context.bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        reply_markup=create_webapp_keyboard()
    )

# --- ডিসপ্যাচারে হ্যান্ডলার যোগ করা ---
dispatcher.add_handler(CommandHandler('start', start))

# --- Webhook সেট করার অংশ (সার্ভার চালু হওয়ার পর শুধু একবার চলবে) ---
if __name__ != '__main__':
    RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
    if RENDER_EXTERNAL_URL:
        WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        print(f"Webhook সেট করা হচ্ছে: {WEBHOOK_URL}")
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook সফলভাবে সেট হয়েছে।")

