import telebot
from telebot import types
import json, time, random

TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"
ADMIN_ID = 718853742
bot = telebot.TeleBot(TOKEN)

data_file = "casino_data.json"
try:
    with open(data_file, "r") as f:
        users = json.load(f)
except:
    users = {}

def save():
    with open(data_file, "w") as f:
        json.dump(users, f)

def get_user(uid):
    if str(uid) not in users:
        users[str(uid)] = {"balance": 1000, "bonus_time": 0, "banned": False, "frozen": False}
        save()
    return users[str(uid)]

def reply_markup():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 Казино", "🎁 Бонус", "💰 Баланс")
    kb.row("🎲 Кости", "🎯 Угадай число")
    kb.row("💸 Перевод", "ℹ️ Помощь")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    u = get_user(msg.from_user.id)
    bot.send_message(msg.chat.id, f"🎰 Добро пожаловать в Казино Рута 2.0!\n💰 Ваш баланс: {u['balance']} фишек",
                     reply_markup=reply_markup())

@bot.message_handler(func=lambda m: True)
def handler(msg):
    u = get_user(msg.from_user.id)
    if u["banned"]:
        return bot.send_message(msg.chat.id, "🚫 Вы забанены.")
    if u["frozen"]:
        return bot.send_message(msg.chat.id, "❄️ Аккаунт заморожен.")

    text = msg.text

    if text == "💰 Баланс":
        bot.send_message(msg.chat.id, f"💰 Ваш баланс: {u['balance']} фишек")

    elif text == "🎁 Бонус":
        now = time.time()
        if now - u["bonus_time"] >= 86400:
            u["balance"] += 1000
            u["bonus_time"] = now
            save()
            bot.send_message(msg.chat.id, "🎁 Вы получили ежедневный бонус 1000 фишек!")
        else:
            h = int((86400 - (now - u["bonus_time"])) / 3600)
            bot.send_message(msg.chat.id, f"⌛ Следующий бонус через {h} часов")

    elif text == "🎰 Казино":
        bot.send_message(msg.chat.id, "Введите сумму ставки (пример: 500):")
        bot.register_next_step_handler(msg, casino_game)

    elif text == "💸 Перевод":
        bot.send_message(msg.chat.id, "📤 Введите ID и сумму через пробел (пример: 123456789 100):")
        bot.register_next_step_handler(msg, transfer)

    elif text == "🎲 Кости":
        game_dice(msg)

    elif text == "🎯 Угадай число":
        bot.send_message(msg.chat.id, "Введите число от 1 до 5:")
        bot.register_next_step_handler(msg, guess_number)

    elif text == "ℹ️ Помощь":
        bot.send_message(msg.chat.id,
                         "📜 Команды:\n/start — начать\n"
                         "🎰 Казино — ставка\n"
                         "🎁 Бонус — ежедневные фишки\n"
                         "💸 Перевод — отправить фишки\n"
                         "🎲 Кости — случайное число\n"
                         "🎯 Угадай число — шанс х5")

# 🎰 Казино
def casino_game(msg):
    u = get_user(msg.from_user.id)
    if not msg.text.isdigit():
        return bot.send_message(msg.chat.id, "❌ Введите число!")
    bet = int(msg.text)
    if bet <= 0 or bet > u["balance"]:
        return bot.send_message(msg.chat.id, "⚠️ Недостаточно фишек!")
    roll = random.randint(1, 100)
    if roll <= 45:
        u["balance"] -= bet
        res = f"😢 Проигрыш {bet}"
    elif roll <= 90:
        win = int(bet * 1.5)
        u["balance"] += win
        res = f"🎉 Победа! Выигрыш {win}"
    else:
        win = bet * 3
        u["balance"] += win
        res = f"🔥 Джекпот! Вы выиграли {win}"
    save()
    bot.send_message(msg.chat.id, f"{res}\n💰 Баланс: {u['balance']}")

# 💸 Перевод
def transfer(msg):
    parts = msg.text.split()
    if len(parts) != 2:
        return bot.send_message(msg.chat.id, "❌ Неверный формат!")
    tid, amount = parts
    if not amount.isdigit():
        return bot.send_message(msg.chat.id, "❌ Введите сумму числом!")
    amount = int(amount)
    sender = get_user(msg.from_user.id)
    if amount <= 0 or amount > sender["balance"]:
        return bot.send_message(msg.chat.id, "⚠️ Недостаточно фишек!")
    receiver = get_user(tid)
    sender["balance"] -= amount
    receiver["balance"] += amount
    save()
    bot.send_message(msg.chat.id, f"✅ Отправлено {amount} фишек пользователю {tid}")
    try:
        bot.send_message(tid, f"💸 Вам перевели {amount} фишек от {msg.from_user.id}")
    except:
        pass

# 🎲 Кости
def game_dice(msg):
    roll = random.randint(1, 6)
    bot.send_message(msg.chat.id, f"🎲 Выпало число: {roll}")

# 🎯 Угадай число
def guess_number(msg):
    if not msg.text.isdigit():
        return bot.send_message(msg.chat.id, "❌ Введите число!")
    choice = int(msg.text)
    if not 1 <= choice <= 5:
        return bot.send_message(msg.chat.id, "Введите от 1 до 5")
    num = random.randint(1, 5)
    u = get_user(msg.from_user.id)
    if choice == num:
        win = 500
        u["balance"] += win
        bot.send_message(msg.chat.id, f"🎯 Угадал! +{win} фишек!")
    else:
        bot.send_message(msg.chat.id, f"😢 Неверно! Было число {num}")
    save()

# 👑 Админ-команды
@bot.message_handler(commands=["admin"])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    bot.send_message(msg.chat.id,
                     "👑 Админ-панель:\n"
                     "/give id сумма — выдать\n"
                     "/ban id — бан\n"
                     "/unban id — разбан\n"
                     "/freeze id — заморозить\n"
                     "/unfreeze id — разморозить")

@bot.message_handler(commands=["give", "ban", "unban", "freeze", "unfreeze"])
def admin_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    args = msg.text.split()
    if len(args) < 2:
        return
    cmd = args[0][1:]
    uid = args[1]
    u = get_user(uid)
    if cmd == "give" and len(args) == 3:
        u["balance"] += int(args[2])
        bot.send_message(msg.chat.id, f"💸 Выдано {args[2]} фишек пользователю {uid}")
    elif cmd == "ban":
        u["banned"] = True
        bot.send_message(msg.chat.id, f"🚫 {uid} забанен")
    elif cmd == "unban":
        u["banned"] = False
        bot.send_message(msg.chat.id, f"✅ {uid} разбанен")
    elif cmd == "freeze":
        u["frozen"] = True
        bot.send_message(msg.chat.id, f"❄️ {uid} заморожен")
    elif cmd == "unfreeze":
        u["frozen"] = False
        bot.send_message(msg.chat.id, f"🔥 {uid} разморожен")
    save()

bot.polling(none_stop=True)
