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

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random, asyncio

# Главное меню для группы
def group_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🎰 Слоты", callback_data="slots"),
        InlineKeyboardButton("🎡 Рулетка", callback_data="roulette"),
        InlineKeyboardButton("🎲 Кости", callback_data="dice")
    )
    return kb

# Обработка команды /casino в группе
@bot.message_handler(commands=["casino"])
def group_casino(m):
    if m.chat.type not in ["group", "supergroup"]:
        bot.send_message(m.chat.id, "⚠️ Эта команда только для групп.")
        return

    text = (
        "🎰 <b>Казино Рута — групповая версия</b>\n\n"
        "💵 Сделай ставку и выбери игру ниже 👇\n"
        "Минимум: <b>50 фишек</b>"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=group_menu())


# ========================= 🎰 СЛОТЫ ========================= #
emojis = ["🍒", "🍋", "🍉", "🍇", "⭐", "7️⃣", "💎", "🍀"]

@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots(message):
    msg = bot.send_message(message.chat.id, "Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(msg, slots_bet)

def slots_bet(message):
    uid = message.from_user.id
    try:
        bet = int(message.text)
        if bet < 50:
            bot.send_message(message.chat.id, "⚠️ Минимальная ставка — 50 фишек.")
            return
        if get_balance(uid) < bet:
            bot.send_message(message.chat.id, "❌ Недостаточно фишек.")
            return
        msg = bot.send_message(message.chat.id, "🎰 Крутим барабаны...")
        spin_slots(message.chat.id, msg.message_id, uid, bet)
    except ValueError:
        bot.send_message(message.chat.id, "Введите число!")

def spin_slots(chat_id, msg_id, uid, bet):
    for i in range(6):
        board = [random.choice(emojis) for _ in range(3)]
        text = f"🎰 <b>Крутим барабаны...</b>\n\n{board[0]} | {board[1]} | {board[2]}"
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML")
        time.sleep(0.4)

    final = [random.choice(emojis) for _ in range(3)]
    result = f"🎰 <b>Результат:</b>\n\n➡️ {final[0]} | {final[1]} | {final[2]}\n"

# Проверяем комбинацию
if final[0] == final[1] == final[2]:
    win = amount * 10  # все три совпали
    change_balance(uid, win)
    result_text = f"🎉 Джекпот! Все три совпали! +{win} фишек"
elif final[0] == final[1] or final[1] == final[2] or final[0] == final[2]:
    win = amount * 2   # две совпали
    change_balance(uid, win)
    result_text = f"✨ Две совпали! +{win} фишек"
else:
    win = -amount
    change_balance(uid, win)
    result_text = f"😢 Не повезло. -{amount} фишек"

# ========================= 🎡 РУЛЕТКА =========================
@bot.message_handler(func=lambda m: m.text == "🎡 Рулетка")
def roulette_start(m: types.Message):
    """Запрос ставки у игрока"""
    uid = m.from_user.id
    # проверка баланса/статуса (предполагается, что есть can_play, ensure_user)
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason)
        return

    bot.send_message(m.chat.id, f"🎡 Введите сумму ставки (минимум {MIN_BET}):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("🔙 Назад"))
    bot.register_next_step_handler(m, roulette_bet)

def roulette_bet(m: types.Message):
    """Обработка введённой ставки и запуск вращения"""
    uid = m.from_user.id
    text = (m.text or "").strip()
    if text == "🔙 Назад":
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        return

    # проверяем число
    try:
        bet = int(text)
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректное число.")
        return

    if bet < MIN_BET or bet > MAX_BET:
        bot.send_message(m.chat.id, f"Ставка от {MIN_BET} до {MAX_BET}")
        return

    if get_balance(uid) < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек.")
        return

    # снимем ставку сразу
    change_balance(uid, -bet)
    get_user(uid)["games_played"] = get_user(uid).get("games_played",0)+1
    save_data()

    # отправляем сообщение и начинаем анимацию
    msg = bot.send_message(m.chat.id, "🎡 <b>Крутим рулетку...</b>", parse_mode="HTML")
    spin_roulette(m.chat.id, msg.message_id, uid, bet)

def spin_roulette(chat_id: int, msg_id: int, uid: int, bet: int):
    """Анимация и результат рулетки"""
    # варианты (эмодзи/числа) — можно настраивать
    wheel = ["🔴","⚫","🟢"]  # красное / чёрное / зеро
    # анимация (несколько кадров)
    for _ in range(7):
        frame = " ".join(random.choice(wheel) for _ in range(6))
        try:
            bot.edit_message_text(f"🎡 <b>Крутится...</b>\n\n{frame}", chat_id, msg_id, parse_mode="HTML")
        except:
            pass
        time.sleep(0.35)

    # итог (весы — можно настроить веса)
    result = random.choices(wheel, weights=[45,45,10], k=1)[0]

    # определяем выигрыш
    if result == "🟢":
        win = bet * 5   # зеро — крупный множитель
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        change_balance(uid, win)
        res_text = f"💚 Выпало {result} — Джекпот! +{win} фишек!"
    elif result == "🔴" or result == "⚫":
        # дадим 50% шанс выигрыша, для простоты: 50% выигрывает x2, 50% проигрывает (уже сняли ставку)
        # но здесь мы считаем совпадение автоматическим выигрышем — если хочешь выбор цвета, нужно дополнительный шаг.
        win = bet * 2
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        change_balance(uid, win)
        res_text = f"{result} — Победа! +{win} фишек!"
    else:
        # на всякий случай
        res_text = f"{result} — Ничего. -{bet} фишек."

    # показываем итог
    try:
        bot.edit_message_text(f"🎯 <b>Результат:</b>\n\n{result}\n\n{res_text}\n\n💰 Баланс: {get_balance(uid)}", chat_id, msg_id, parse_mode="HTML")
    except:
        bot.send_message(chat_id, f"🎯 Результат: {result}\n\n{res_text}\n\n💰 Баланс: {get_balance(uid)}")

# ========================= 🎲 КОСТИ =========================
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def dice_start(m: types.Message):
    """Запрос ставки у игрока"""
    uid = m.from_user.id
    ensure_user(uid)

    bot.send_message(m.chat.id, f"🎲 Введите сумму ставки (минимум {MIN_BET}):")
    bot.register_next_step_handler(m, dice_bet)


def dice_bet(m: types.Message):
    """Проверка ставки и начало анимации"""
    uid = m.from_user.id
    text = (m.text or "").strip()

    try:
        bet = int(text)
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректное число.")
        return

    if bet < MIN_BET:
        bot.send_message(m.chat.id, f"❗ Минимальная ставка — {MIN_BET} фишек.")
        return

    if get_balance(uid) < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек.")
        return

    # снимаем ставку
    change_balance(uid, -bet)
    save_data()

    msg = bot.send_message(m.chat.id, "🎲 Бросаем кости...")
    spin_dice(m.chat.id, msg.message_id, uid, bet)


def spin_dice(chat_id: int, msg_id: int, uid: int, bet: int):
    """Анимация броска костей и результат"""
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

    # анимация 6 кадров
    for _ in range(6):
        left = random.choice(dice_faces)
        right = random.choice(dice_faces)
        text = f"🎲 Бросаем...\n\n{left}  {right}"
        try:
            bot.edit_message_text(text, chat_id, msg_id)
        except:
            pass
        time.sleep(0.4)

    # итоговый результат
    left = random.choice(dice_faces)
    right = random.choice(dice_faces)
    total = dice_faces.index(left) + dice_faces.index(right) + 2  # от 2 до 12

    text = f"🎲 Выпало: {left}  {right}  = {total}"

    # считаем выигрыш
    if total >= 10:
        win = bet * 3
        change_balance(uid, win)
        outcome = f"💰 Вы выиграли {win} фишек!"
    elif total >= 7:
        win = bet * 2
        change_balance(uid, win)
        outcome = f"✨ Победа! +{win} фишек!"
    else:
        outcome = f"😢 Не повезло. -{bet} фишек."

    # вывод результата
    try:
        bot.edit_message_text(
            f"{text}\n\n{outcome}\n💰 Баланс: {get_balance(uid)}",
            chat_id, msg_id
        )
    except:
        bot.send_message(chat_id, f"{text}\n\n{outcome}\n💰 Баланс: {get_balance(uid)}")

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

# ========================= 👑 АДМИН ПАНЕЛЬ =========================
ADMINS = [718853742, 8509920661]  # ← ТУТ твои Telegram ID (можно добавить ещё через запятую)

LOG_FILE = "logs.json"

def log_action(action):
    data = load_data()
    logs = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except:
                logs = {}
    logs[str(len(logs) + 1)] = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action}
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


@bot.message_handler(commands=["admin"])
def admin_panel(m: types.Message):
    if m.from_user.id not in ADMINS:
        return bot.send_message(m.chat.id, "🚫 У вас нет доступа.")

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔒 Забанить", callback_data="admin_ban"),
        types.InlineKeyboardButton("🔓 Разбанить", callback_data="admin_unban"),
    )
    markup.add(
        types.InlineKeyboardButton("❄️ Заморозить", callback_data="admin_freeze"),
        types.InlineKeyboardButton("⚠️ Предупредить", callback_data="admin_warn"),
    )
    markup.add(types.InlineKeyboardButton("📜 Логи", callback_data="admin_logs"))
    markup.add(types.InlineKeyboardButton("💰 Баланс по ID", callback_data="admin_balance"))

    bot.send_message(m.chat.id, "👑 Панель администратора", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def admin_action(call):
    action = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введите ID пользователя для '{action}'")
    bot.register_next_step_handler(msg, lambda m: process_admin_action(m, action))


def process_admin_action(m, action):
    try:
        uid = int(m.text)
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректный числовой ID.")
        return

    data = load_data()

    if action == "ban":
        data["users"].setdefault(str(uid), {})["banned"] = True
        save_data()
        bot.send_message(m.chat.id, f"🚫 Пользователь {uid} забанен.")
        log_action(f"Админ {m.from_user.id} забанил {uid}")

    elif action == "unban":
        if str(uid) in data["users"]:
            data["users"][str(uid)]["banned"] = False
            save_data()
            bot.send_message(m.chat.id, f"✅ Пользователь {uid} разбанен.")
            log_action(f"Админ {m.from_user.id} разбанил {uid}")

    elif action == "freeze":
        data["users"].setdefault(str(uid), {})["frozen"] = True
        save_data()
        bot.send_message(m.chat.id, f"❄️ Пользователь {uid} заморожен.")
        log_action(f"Админ {m.from_user.id} заморозил {uid}")

    elif action == "warn":
        data["users"].setdefault(str(uid), {}).setdefault("warns", 0)
        data["users"][str(uid)]["warns"] += 1
        save_data()
        warns = data["users"][str(uid)]["warns"]
        bot.send_message(m.chat.id, f"⚠️ Предупреждение выдано пользователю {uid}. Всего: {warns}")
        log_action(f"Админ {m.from_user.id} выдал предупреждение {uid}")

    elif action == "logs":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            text = "\n".join([f"{v['time']}: {v['action']}" for v in logs.values()[-10:]])
            bot.send_message(m.chat.id, f"📜 Последние логи:\n{text}")
        else:
            bot.send_message(m.chat.id, "📁 Логи пока пусты.")

    elif action == "balance":
        bal = get_balance(uid)
        bot.send_message(m.chat.id, f"💰 Баланс пользователя {uid}: {bal} фишек.")


# Проверка перед любой игрой
def can_play(uid):
    data = load_data()
    user = data["users"].get(str(uid), {})
    if user.get("banned"):
        return False, "🚫 Вы заблокированы."
    if user.get("frozen"):
        return False, "❄️ Ваш аккаунт заморожен."
    return True, ""

# ====== ЗАПУСК ======
if __name__ == "__main__":
    print("✅ Бот запущен и слушает сообщения...")
    bot.infinity_polling(skip_pending=True)
