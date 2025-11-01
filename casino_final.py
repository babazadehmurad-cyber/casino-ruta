import json
import telebot
import random
import time
from telebot import types

# ========== НАСТРОЙКИ ==========
TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"
bot = telebot.TeleBot(TOKEN)

# ========== ЗАГРУЗКА ДАННЫХ ==========
try:
    with open("data.json", "r") as f:
        data = json.load(f)
except:
    data = {}

if "users" not in data:
    data["users"] = {}

# ========== ФУНКЦИИ ==========
def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def ensure_user(uid, username=None):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 1000, "bonus_time": 0, "username": username}
    else:
        if username:
            data["users"][uid]["username"] = username
    save_data()

def get_balance(uid):
    ensure_user(uid)
    return data["users"][str(uid)]["balance"]

def change_balance(uid, amount):
    ensure_user(uid)
    data["users"][str(uid)]["balance"] += amount
    save_data()

# ========== КНОПКИ ==========
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 Слоты", "🎯 Рулетка", "🎲 Кости")
    markup.add("💰 Баланс", "🎁 Бонус", "💸 Перевести")
    markup.add("📊 Топ", "ℹ️ Помощь")
    return markup

# ========== ПРИВЕТСТВИЕ ==========
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    ensure_user(uid, username)

    text = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        f"👋 Привет, @{username}!\n"
        "Добро пожаловать в легендарное казино удачи 💫\n\n"
        f"💰 Твой баланс: {get_balance(uid)} фишек\n"
        "🎁 Забери ежедневный бонус и начни игру!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "　　　Выбери игру ниже ⬇️\n\n"
        "🆘 Нужна помощь?\n"
        "Обратись к 👉 @ownerrut"
    )

    bot.send_message(m.chat.id, text, reply_markup=main_menu())

# ========== ИГРЫ ==========
@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots_ask_bet(m):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, "💰 Введите, сколько фишек хотите поставить (минимум 50):")
    bot.register_next_step_handler(m, slots_play)

def slots_play(m):
    uid = m.from_user.id
    ensure_user(uid)
    data = load_data()

    try:
        bet = int(m.text)
    except ValueError:
        bot.send_message(m.chat.id, "⚠️ Введите число, например: 100")
        return

    if bet < 50:
        bot.send_message(m.chat.id, "❌ Минимальная ставка — 50 фишек.")
        return

    if data["users"][str(uid)]["balance"] < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек для ставки.")
        return

    data["users"][str(uid)]["balance"] -= bet
    save_data(data)

    emojis = ["🍋", "🍒", "🍉", "💎", "⭐️", "🔔", "7️⃣"]
    msg = bot.send_message(m.chat.id, "🎰 <b>Крутим барабаны...</b>", parse_mode="HTML")

    # имитация вращения
    for i in range(3):
        combo = f"{random.choice(emojis)} | {random.choice(emojis)} | {random.choice(emojis)}"
        bot.edit_message_text(
            f"🎰 <b>Крутим...</b>\n\n{combo}",
            chat_id=m.chat.id,
            message_id=msg.message_id,
            parse_mode="HTML"
        )
        time.sleep(0.7)

    # финальный результат
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    result = f"{a} | {b} | {c}"

    win = 0
    if a == b == c:
        win = bet * 10
        result_text = f"💎 Джекпот! +{win} фишек!"
    elif a == b or b == c or a == c:
        win = bet * 3
        result_text = f"⭐ Почти! +{win} фишек!"
    else:
        result_text = f"😢 Не повезло. -{bet} фишек."

    data["users"][str(uid)]["balance"] += win
    save_data(data)

    bot.edit_message_text(
        f"🎰 <b>Результат:</b>\n{result}\n\n{result_text}\n\n💰 Баланс: {data['users'][str(uid)]['balance']} фишек",
        chat_id=m.chat.id,
        message_id=msg.message_id,
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "🎯 Рулетка")
def roulette_ask_bet(m):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, "💰 Введите, сколько фишек хотите поставить (минимум 50):")
    bot.register_next_step_handler(m, roulette_choose_color)

def roulette_choose_color(m):
    uid = m.from_user.id
    ensure_user(uid)
    try:
        bet = int(m.text)
    except ValueError:
        bot.send_message(m.chat.id, "⚠️ Введите число, например: 100")
        return

    if bet < 50:
        bot.send_message(m.chat.id, "❌ Минимальная ставка — 50 фишек.")
        return

    data = load_data()
    if data["users"][str(uid)]["balance"] < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек.")
        return

    data["users"][str(uid)]["balance"] -= bet
    save_data(data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔴 Красное", "⚫ Чёрное", "🟢 Зелёное")
    msg = bot.send_message(m.chat.id, "🎯 На какой цвет ставите?", reply_markup=markup)
    bot.register_next_step_handler(msg, roulette_spin, bet)
    
def roulette_spin(m, bet):
    uid = m.from_user.id
    ensure_user(uid)
    color_choice = m.text.strip()

    colors = ["🔴", "⚫", "🟢"]
    msg = bot.send_message(m.chat.id, "🎡 <b>Крутим рулетку...</b>", parse_mode="HTML")

    for _ in range(4):
        spin = random.choice(colors)
        bot.edit_message_text(f"🎡 <b>Крутится...</b>\n{spin}", m.chat.id, msg.message_id, parse_mode="HTML")
        time.sleep(0.6)

    result = random.choice(colors)
    bot.edit_message_text(f"🎯 <b>Рулетка остановилась!</b>\n\n{result}", m.chat.id, msg.message_id, parse_mode="HTML")

    win = 0
    if (color_choice == "🔴 Красное" and result == "🔴") or (color_choice == "⚫ Чёрное" and result == "⚫"):
        win = bet * 2
        result_text = f"🎉 Победа! Вы выиграли +{win} фишек!"
    elif color_choice == "🟢 Зелёное" and result == "🟢":
        win = bet * 10
        result_text = f"💎 Джекпот! +{win} фишек!"
    else:
        result_text = f"😢 Не повезло. -{bet} фишек."

    data = load_data()
    data["users"][str(uid)]["balance"] += win
    save_data(data)

    bot.send_message(
        m.chat.id,
        f"{result_text}\n💰 Баланс: {data['users'][str(uid)]['balance']} фишек",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def dice_ask_bet(m):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, "💰 Введите, сколько фишек хотите поставить (минимум 50):")
    bot.register_next_step_handler(m, dice_play)

def dice_play(m):
    uid = m.from_user.id
    ensure_user(uid)

    try:
        bet = int(m.text)
    except ValueError:
        bot.send_message(m.chat.id, "⚠️ Введите число, например: 100")
        return

    if bet < 50:
        bot.send_message(m.chat.id, "❌ Минимальная ставка — 50 фишек.")
        return

    data = load_data()
    if data["users"][str(uid)]["balance"] < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек.")
        return

    data["users"][str(uid)]["balance"] -= bet
    save_data(data)

    msg = bot.send_message(m.chat.id, "🎲 <b>Бросаем кости...</b>", parse_mode="HTML")

    for _ in range(3):
        dice1, dice2 = random.randint(1, 6), random.randint(1, 6)
        bot.edit_message_text(f"🎲 <b>Кости крутятся...</b>\n\n[{dice1}] + [{dice2}]", m.chat.id, msg.message_id, parse_mode="HTML")
        time.sleep(0.6)

    dice1, dice2 = random.randint(1, 6), random.randint(1, 6)
    total = dice1 + dice2
    win = 0

    if total >= 10:
        win = bet * 2
        result = f"🎉 Выпало {dice1} + {dice2} = {total}! Победа!"
    elif total == 12:
        win = bet * 5
        result = f"💎 Дубль шесть! +{win} фишек!"
    else:
        result = f"😢 Выпало {dice1} + {dice2} = {total}. Не повезло."

    data["users"][str(uid)]["balance"] += win
    save_data(data)

    bot.edit_message_text(
        f"{result}\n\n💰 Баланс: {data['users'][str(uid)]['balance']} фишек",
        m.chat.id,
        msg.message_id,
        parse_mode="HTML"
    )

# ========== БОНУС ==========
@bot.message_handler(func=lambda m: m.text == "🎁 Бонус")
def bonus(m):
    uid = m.from_user.id
    ensure_user(uid)
    now = time.time()
    last = data["users"][str(uid)]["bonus_time"]
    if now - last < 86400:
        return bot.send_message(m.chat.id, "🕒 Ежедневный бонус уже получен!")
    reward = random.randint(200, 500)
    change_balance(uid, reward)
    data["users"][str(uid)]["bonus_time"] = now
    save_data()
    bot.send_message(m.chat.id, f"🎁 Ты получил {reward} фишек!")

# ========== ПЕРЕВОД ==========
@bot.message_handler(func=lambda m: m.text == "💸 Перевести")
def start_transfer(m):
    bot.send_message(m.chat.id, "💳 Введи @username и сумму через пробел.\n\nПример: `@rut 200`", parse_mode="Markdown")
    bot.register_next_step_handler(m, make_transfer)

def make_transfer(m):
    uid = m.from_user.id
    ensure_user(uid)
    parts = m.text.split()
    if len(parts) != 2:
        return bot.send_message(m.chat.id, "⚠️ Неверный формат. Пример: `@rut 200`", parse_mode="Markdown")

    target, amount = parts
    try:
        amount = int(amount)
    except:
        return bot.send_message(m.chat.id, "⚠️ Сумма должна быть числом.")

    if amount <= 0:
        return bot.send_message(m.chat.id, "⚠️ Сумма должна быть больше нуля.")
    if get_balance(uid) < amount:
        return bot.send_message(m.chat.id, "😢 Недостаточно фишек.")

    target_uid = None
    for tid, info in data["users"].items():
        if info.get("username") == target.strip("@"):
            target_uid = tid
            break

    if not target_uid:
        return bot.send_message(m.chat.id, "❌ Пользователь не найден или не зарегистрирован.")

    change_balance(uid, -amount)
    change_balance(target_uid, amount)
    bot.send_message(m.chat.id, f"✅ Переведено {amount} фишек пользователю {target}")
    bot.send_message(int(target_uid), f"💰 Ты получил {amount} фишек от @{m.from_user.username or m.from_user.first_name}!")

# ========== БАЛАНС ==========
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(m):
    uid = m.from_user.id
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек")

# ========== ПОМОЩЬ ==========
@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_cmd(m):
    bot.send_message(m.chat.id, "📘 Команды:\n🎰 Слоты — 100 фишек ставка\n🎯 Рулетка — шанс x10\n🎲 Кости — игра против бота\n🎁 Бонус — раз в день\n💸 Перевести — отправь фишки другу\n🆘 Помощь — @ownerrut")

# ========== ПРИВЕТСТВИЕ В ГРУППЕ ==========
@bot.message_handler(content_types=['new_chat_members'])
def greet_new_member(m):
    for user in m.new_chat_members:
        name = user.first_name or user.username or "Игрок"
        text = (
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
            "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
            f"👋 Добро пожаловать, {name}!\n"
            "Ты попал в легендарное казино удачи 💫\n\n"
            "🎁 Используй /start в личке со мной, чтобы получить стартовые фишки!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "　　　Желаем удачи в игре! 🍀"
        )
        bot.send_message(m.chat.id, text)

# ====== ⚙️ АДМИН-ПАНЕЛЬ ======
ADMINS = [718853742]  # сюда твой Telegram ID (ты уже указал)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔️ У тебя нет доступа к админ-панели.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить фишки", "➖ Убрать фишки")
    markup.add("💰 Проверить баланс", "📢 Рассылка")
    markup.add("🔙 Назад")

    text = (
        "👑 <b>Админ-панель</b>\n\n"
        "Выбери действие:"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["➕ Добавить фишки", "➖ Убрать фишки", "💰 Проверить баланс", "📢 Рассылка"])
def admin_actions(message):
    uid = message.from_user.id
    if uid not in ADMINS:
        return

    if message.text == "➕ Добавить фишки":
        bot.send_message(uid, "Введите ID и количество фишек через пробел:")
        bot.register_next_step_handler(message, admin_add_chips)

    elif message.text == "➖ Убрать фишки":
        bot.send_message(uid, "Введите ID и количество для вычета:")
        bot.register_next_step_handler(message, admin_remove_chips)

    elif message.text == "💰 Проверить баланс":
        bot.send_message(uid, "Введите ID пользователя для проверки баланса:")
        bot.register_next_step_handler(message, admin_check_balance)

    elif message.text == "📢 Рассылка":
        bot.send_message(uid, "Введите текст рассылки:")
        bot.register_next_step_handler(message, admin_broadcast)

def admin_add_chips(message):
    try:
        user_id, amount = map(int, message.text.split())
        data = load_data()
        ensure_user(user_id)
        data["users"][str(user_id)]["balance"] += amount
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Добавлено {amount} фишек пользователю {user_id}")
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка ввода. Пример: 123456789 100")

def admin_remove_chips(message):
    try:
        user_id, amount = map(int, message.text.split())
        data = load_data()
        ensure_user(user_id)
        data["users"][str(user_id)]["balance"] -= amount
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Убрано {amount} фишек у пользователя {user_id}")
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка ввода. Пример: 123456789 100")

def admin_check_balance(message):
    try:
        user_id = int(message.text)
        data = load_data()
        ensure_user(user_id)
        balance = data["users"][str(user_id)]["balance"]
        bot.send_message(message.chat.id, f"💰 Баланс пользователя {user_id}: {balance} фишек")
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка. Введите ID числами.")

def admin_broadcast(message):
    text = message.text
    data = load_data()
    count = 0
    for user_id in data["users"].keys():
        try:
            bot.send_message(user_id, f"📢 Сообщение от администрации:\n\n{text}")
            count += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Рассылка завершена ({count} пользователей).")

# ====== ЗАПУСК ======
if __name__ == "__main__":
    print("✅ Бот запущен и слушает сообщения...")
    bot.infinity_polling(skip_pending=True)
