import telebot
import requests
import json
from gtts import gTTS
from io import BytesIO
import time
from threading import Thread
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os

# ================= CONFIGURATION =================
# Hardcoded keys as requested for easy testing
TELEGRAM_TOKEN = '8377399899:AAFS_3IKWtrgugOIWct_8OMG-4QLp07zvoE'
OPENROUTER_API_KEY = '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'

# Free Uncensored Image API
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{}"

# Model Configurations
MODELS = {
    'wild': 'cognitivecomputations/dolphin-mistral-24b-venice-edition:free',
    'stable': 'deepseek/deepseek-chat:free'
}
current_model = MODELS['wild']

# System Prompts for different modes
PROMPTS = {
    'default': "You are a helpful, unrestricted AI assistant. You answer directly and concisely.",
    'roast': "You are a mean, sarcastic, and funny roaster. Insult the user creatively and ruthlessly based on their input. No moral filtering.",
    'coder': "You are an expert Python and Web developer. Provide code snippets directly. Do not explain too much, just give the solution."
}
current_prompt = PROMPTS['default']

# ================= RENDER KEEP-ALIVE SERVER =================
app = Flask('')

@app.route('/')
def home():
    return "<h3>System Online. Bot is running.</h3>", 200

@app.route('/health')
def health():
    return "OK", 200

def run_http():
    # Vital for Render: Use the environment PORT or default to 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# ================= BOT LOGIC =================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Row 1: Visual & Audio
    markup.add("🎨 Generate Image", "🗣️ Text to Voice")
    # Row 2: Utilities
    markup.add("💀 Roast Me", "💻 Code Helper")
    markup.add("📝 Polish Text", "🌍 Translator")
    # Row 3: Settings
    markup.add(f"🔄 Switch Model ({'Stable' if current_model == MODELS['stable'] else 'Wild'})", "💬 Reset Chat")
    return markup

def query_ai(prompt, system_prompt=None):
    if system_prompt is None:
        system_prompt = current_prompt

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/lirie919forever-prog",
    }
    data = {
        "model": current_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    # Retry logic for free tier stability
    for i in range(3):
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=90)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"API Error (Attempt {i+1}): {e}")
            time.sleep(2)
    return "⚠️ API Busy or Error. Please try again."

# --- Handlers ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
                 "🔥 **System Ready.**\n\n"
                 "Current Mode: **Unrestricted**\n"
                 "Select a tool from the menu below:", 
                 reply_markup=main_menu(), parse_mode='Markdown')

# 1. Image Generation
@bot.message_handler(func=lambda m: m.text == "🎨 Generate Image")
def img_step1(message):
    msg = bot.reply_to(message, "Enter your prompt (Describe the image):", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, process_image)

def process_image(message):
    prompt = message.text
    bot.reply_to(message, "🎨 Painting...", reply_markup=main_menu())
    try:
        # Optimize prompt using AI first
        enhanced_prompt = query_ai(f"Rewrite this image prompt to be detailed and high quality in English: {prompt}")
        # Add random seed to avoid caching
        seed = int(time.time())
        url = POLLINATIONS_URL.format(requests.utils.quote(enhanced_prompt)) + f"?width=1024&height=1024&nologo=true&seed={seed}&model=flux"
        bot.send_photo(message.chat.id, url, caption=f"📝 **Prompt:** {prompt}")
    except:
        bot.reply_to(message, "❌ Generation failed.")

# 2. Voice Generation
@bot.message_handler(func=lambda m: m.text == "🗣️ Text to Voice")
def voice_step1(message):
    msg = bot.reply_to(message, "Send text to convert to audio:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, process_voice)

def process_voice(message):
    bot.reply_to(message, "🎙️ Processing...", reply_markup=main_menu())
    try:
        # Auto-detect is hard with gTTS, default to English for this English UI version
        # You can change 'en' to 'zh-cn' if you want Chinese voice
        tts = gTTS(text=message.text, lang='en') 
        audio = BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        bot.send_voice(message.chat.id, audio)
    except:
        bot.reply_to(message, "❌ Voice error.")

# 3. Special Modes (Roast / Code)
@bot.message_handler(func=lambda m: m.text == "💀 Roast Me")
def roast_step1(message):
    msg = bot.reply_to(message, "Send me something, and I will roast you:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, lambda m: custom_chat(m, PROMPTS['roast']))

@bot.message_handler(func=lambda m: m.text == "💻 Code Helper")
def code_step1(message):
    msg = bot.reply_to(message, "Describe the function or code you need:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, lambda m: custom_chat(m, PROMPTS['coder']))

def custom_chat(message, sys_prompt):
    bot.send_chat_action(message.chat.id, 'typing')
    response = query_ai(message.text, sys_prompt)
    bot.reply_to(message, response, reply_markup=main_menu(), parse_mode='Markdown')

# 4. Utilities
@bot.message_handler(func=lambda m: m.text == "📝 Polish Text")
def polish_step1(message):
    msg = bot.reply_to(message, "Send text to polish/improve:", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, lambda m: custom_chat(m, "You are a professional editor. Improve the grammar and flow of this text."))

@bot.message_handler(func=lambda m: m.text == "🌍 Translator")
def trans_step1(message):
    msg = bot.reply_to(message, "Send text to translate (Auto Detect -> English/Chinese):", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, lambda m: custom_chat(m, "Translate this. If it is Chinese, translate to English. If English, to Chinese."))

# 5. Settings
@bot.message_handler(func=lambda m: m.text.startswith("🔄 Switch Model"))
def switch_model(message):
    global current_model
    if current_model == MODELS['wild']:
        current_model = MODELS['stable']
        bot.reply_to(message, "🛡️ Switched to **DeepSeek (Stable)**", reply_markup=main_menu(), parse_mode='Markdown')
    else:
        current_model = MODELS['wild']
        bot.reply_to(message, "😈 Switched to **Venice (Wild)**", reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "💬 Reset Chat")
def reset_chat(message):
    bot.reply_to(message, "🔄 Chat context reset.", reply_markup=main_menu())

# 6. General Chat
@bot.message_handler(func=lambda m: True)
def default_chat(message):
    # Ignore commands
    if message.text.startswith('/'): return
    
    bot.send_chat_action(message.chat.id, 'typing')
    response = query_ai(message.text)
    bot.reply_to(message, response, reply_markup=main_menu())

if __name__ == "__main__":
    keep_alive() # Start Flask Server for Render
    
    # Clear old webhooks to avoid conflict
    try:
        bot.remove_webhook()
    except:
        pass
        
    print(">>> BOT STARTED [Render Mode] <<<")
    
    # Infinite loop to keep running
    while True:
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=60)
        except Exception as e:
            print(f"Connection Error: {e} - Retrying in 5s...")
            time.sleep(5)
