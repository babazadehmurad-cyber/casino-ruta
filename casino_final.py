#!/usr/bin/env python3
import json
import telebot
import random
import os
import time
from telebot import types

MIN_BET = 50  # минимальная ставка

# ========== НАСТРОЙКИ ==========
TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"  # <- проверь токен
bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ========== ФАЙЛ ДАННЫХ ==========
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    global data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# глобальные данные
data = load_data()

# ========== УТИЛИТЫ РАБОТЫ С ПОЛЬЗОВАТЕЛЕМ ==========
def ensure_user(uid: str, username: str = None):
    """Гарантирует, что пользователь есть в data (uid - str)."""
    global data
    if "users" not in data:
        data["users"] = {}
    if uid not in data["users"]:
        data["users"][uid] = {
            "balance": 1000,
            "frozen": False,
            "banned": False,
            "warns": 0,
            "logs": [],
            "bonus_time": 0,
            "username": username or ""
        }
        save_data()
    else:
        # обновим username если передали
        if username:
            data["users"][uid]["username"] = username
            save_data()

def get_balance(uid):
    uid = str(uid)
    ensure_user(uid)
    return int(data["users"][uid].get("balance", 0))

def change_balance(uid, delta):
    uid = str(uid)
    ensure_user(uid)
    data["users"][uid]["balance"] = int(data["users"][uid].get("balance", 0) + int(delta))
    save_data()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 Слоты", "🎯 Рулетка", "🎲 Кости")
    kb.row("🎁 Бонус", "💰 Баланс", "💸 Перевести")
    kb.row("📊 Топ", "ℹ️ Помощь")
    return kb

# inline меню для групп
def group_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🎰 Слоты", callback_data="g_slots"),
        types.InlineKeyboardButton("🎡 Рулетка", callback_data="g_roulette"),
        types.InlineKeyboardButton("🎲 Кости", callback_data="g_dice")
    )
    return kb

# ========== SAFE EDIT (устраняет message not modified) ==========
def safe_edit_message(chat_id, message_id, text):
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise

# ========== /start ==========
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = str(m.from_user.id)
    username = m.from_user.username or m.from_user.first_name or ""
    ensure_user(uid, username)
    bal = get_balance(uid)
    text = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　🎰 CASINO RUTA 🎲\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        f"👋 Привет, @{username}!\n"
        "Добро пожаловать в легендарное казино удачи 💫\n\n"
        f"💰 Твой баланс: {bal} фишек\n"
        "🎁 Забери ежедневный бонус и начни игру!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "　　　Выбери игру ниже ⬇️\n\n"
        "🆘 Нужна помощь? Обратись к 👉 @ownerrut"
    )
    bot.send_message(m.chat.id, text, reply_markup=main_menu())

# ========== /casino для группы ==========
@bot.message_handler(commands=["casino"])
def group_casino(m: types.Message):
    if m.chat.type not in ["group", "supergroup"]:
        bot.send_message(m.chat.id, "⚠️ Эта команда только для групп.")
        return
    text = (
        "🎰 <b>Казино Рута — групповая версия</b>\n\n"
        "💵 Сделай ставку и выбери игру ниже 👇\n"
        "Минимум: <b>50 фишек</b>"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=group_menu())

# ========== ИГРЫ: Слоты / Кости / Рулетка ==========
# Мы используем однотипную схему: пользователь нажал кнопку -> бот просит ставку -> запускает игру и редактирует сообщение

# --- СЛОТЫ ---
@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots_request(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    msg = bot.send_message(m.chat.id, "🎰 Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(msg, slots_play)

def slots_play(m: types.Message):
    uid = str(m.from_user.id)
    username = m.from_user.username or m.from_user.first_name or ""
    try:
        amount = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "❌ Введите сумму числом.")
        return
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"❗ Минимальная ставка — {MIN_BET}.")
        return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "💸 У вас недостаточно фишек.")
        return

    # Снимаем ставку сразу (чтобы нельзя было «пережать»)
    change_balance(uid, -amount)

    symbols = ["🍒", "🍋", "🍉", "⭐", "🔔", "💎", "7️⃣"]
    header = f"🎰 Казино Рута\nИгрок: {username}\n💰 Ставка: {amount} фишек\n━━━━━━━━━━━━━━━"
    msg = bot.send_message(m.chat.id, header + "\nЗапускаем барабаны...")

    # Анимация вращения
    for i in range(5):
        line = " | ".join(random.choices(symbols, k=3))
        safe_edit_message(msg.chat.id, msg.message_id, header + f"\n{line}\n━━━━━━━━━━━━━━━\nБарабаны крутятся... 🔄")
        time.sleep(0.45)

    final = random.choices(symbols, k=3)
    result_line = " | ".join(final)

    if final[0] == final[1] == final[2]:
        win = amount * 5
        change_balance(uid, win)
        outcome = f"🔥 Джекпот! Вы выиграли {win} фишек!"
    elif final[0] == final[1] or final[1] == final[2] or final[0] == final[2]:
        win = amount * 2
        change_balance(uid, win)
        outcome = f"✨ Совпадение! Вы выиграли {win} фишек!"
    else:
        outcome = f"😔 Увы, вы проиграли {amount} фишек."

    bal = get_balance(uid)
    safe_edit_message(msg.chat.id, msg.message_id, header + f"\n{result_line}\n━━━━━━━━━━━━━━━\n{outcome}\n\n💰 Баланс: {bal} фишек")

# Callback из группы — просим ставку в чате группы (работает также)
@bot.callback_query_handler(func=lambda c: c.data == "g_slots")
def g_slots_cb(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🎰 В группе: напишите ставку числом в ответ на это сообщение, бот примет ставку (в группе).")
    msg = bot.send_message(call.message.chat.id, "Введите ставку:")
    bot.register_next_step_handler(msg, slots_play)

# --- КОСТИ (2 кубика у игрока и 2 у казино) ---
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def dice_request(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    msg = bot.send_message(m.chat.id, "🎲 Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(msg, dice_play)

def dice_play(m: types.Message):
    uid = str(m.from_user.id)
    username = m.from_user.username or m.from_user.first_name or ""
    try:
        amount = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "❌ Введите сумму числом.")
        return
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"❗ Минимальная ставка — {MIN_BET}.")
        return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "💸 У вас недостаточно фишек.")
        return

    change_balance(uid, -amount)

    header = f"🎲 Казино Рута\nИгрок: {username}\n💰 Ставка: {amount} фишек\n━━━━━━━━━━━━━━━"
    msg = bot.send_message(m.chat.id, header + "\n🎯 Вы бросаете кости...")

    dice_faces = ["⚀","⚁","⚂","⚃","⚄","⚅"]

    # анимация игрока
    for _ in range(3):
        a = random.choice(dice_faces)
        b = random.choice(dice_faces)
        safe_edit_message(msg.chat.id, msg.message_id, header + f"\n{a} | {b}\n━━━━━━━━━━━━━━━\nВы бросаете...")
        time.sleep(0.4)

    player_rolls = [random.randint(1,6), random.randint(1,6)]
    player_sum = sum(player_rolls)
    player_dice_final = f"{dice_faces[player_rolls[0]-1]} | {dice_faces[player_rolls[1]-1]}"

    safe_edit_message(msg.chat.id, msg.message_id, header + f"\nВаш бросок:\n{player_dice_final} = {player_sum}\n━━━━━━━━━━━━━━━\nКазино бросает кости...")
    time.sleep(0.8)

    # анимация казино
    for _ in range(3):
        a = random.choice(dice_faces)
        b = random.choice(dice_faces)
        safe_edit_message(msg.chat.id, msg.message_id, header + f"\n{a} | {b}\n━━━━━━━━━━━━━━━\nКазино бросает...")
        time.sleep(0.4)

    casino_rolls = [random.randint(1,6), random.randint(1,6)]
    casino_sum = sum(casino_rolls)
    casino_dice_final = f"{dice_faces[casino_rolls[0]-1]} | {dice_faces[casino_rolls[1]-1]}"

    if player_sum > casino_sum:
        win = amount * 2
        change_balance(uid, win)
        outcome = f"🔥 Вы победили! +{win} фишек"
    elif player_sum == casino_sum:
        change_balance(uid, amount)
        outcome = f"🤝 Ничья! Ставка возвращена."
    else:
        outcome = f"😔 Вы проиграли -{amount} фишек"

    bal = get_balance(uid)
    safe_edit_message(msg.chat.id, msg.message_id, header + f"\nВаш результат: {player_dice_final} = {player_sum}\nКазино: {casino_dice_final} = {casino_sum}\n━━━━━━━━━━━━━━━\n{outcome}\n\n💰 Баланс: {bal} фишек")

# группа callback для костей
@bot.callback_query_handler(func=lambda c: c.data == "g_dice")
def g_dice_cb(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎲 Введите ставку (числом):")
    bot.register_next_step_handler(msg, dice_play)

# --- РУЛЕТКА ---
@bot.message_handler(func=lambda m: m.text == "🎯 Рулетка" or m.text == "🎡 Рулетка")
def roulette_request(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    msg = bot.send_message(m.chat.id, "🎯 Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(msg, roulette_play)

def roulette_play(m: types.Message):
    uid = str(m.from_user.id)
    username = m.from_user.username or m.from_user.first_name or ""
    try:
        amount = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "❌ Введите сумму числом.")
        return
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"❗ Минимальная ставка — {MIN_BET}.")
        return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "💸 У вас недостаточно фишек.")
        return

    change_balance(uid, -amount)
    header = f"🎡 Казино Рута\nИгрок: {username}\n💰 Ставка: {amount} фишек\n━━━━━━━━━━━━━━━"
    msg = bot.send_message(m.chat.id, header + "\nЗапускаем рулетку...")

    # анимация
    numbers = list(range(0,37))
    for _ in range(8):
        n = random.choice(numbers)
        safe_edit_message(msg.chat.id, msg.message_id, header + f"\nШарик крутится... 🎯 {n}\n━━━━━━━━━━━━━━━")
        time.sleep(0.25)

    result = random.randint(0,36)
    if result == 0:
        outcome = f"🟢 Зеро! Казино забирает ставку.\nБаланс: {data[str(uid)]['balance']}"
    elif result % 2 == 0:
        win = amount * 2
        change_balance(uid, win)
        outcome = f"🟥 Красное! Вы выиграли {win} фишек 💰\nБаланс: {get_balance(uid)}"
    else:
        outcome = f"⬛ Чёрное! Вы проиграли {amount} фишек 😔\nБаланс: {get_balance(uid)}"

    save_data()
    safe_edit_message(msg.chat.id, msg.message_id, header + f"\nВыпало число {result}\n━━━━━━━━━━━━━━━\n{outcome}")

# группа callback рулетка
@bot.callback_query_handler(func=lambda c: c.data == "g_roulette")
def g_roulette_cb(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎯 Введите ставку (числом):")
    bot.register_next_step_handler(msg, roulette_play)

# ========== БОНУС ==========
@bot.message_handler(func=lambda m: m.text == "🎁 Бонус")
def bonus_cmd(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    now = time.time()
    if "bonus_time" not in data["users"][uid]:
        data["users"][uid]["bonus_time"] = 0
    last = data["users"][uid].get("bonus_time", 0)
    if now - last < 86400:
        remaining = int((86400 - (now - last)) // 3600)
        bot.send_message(m.chat.id, f"🕒 Бонус уже получен. Через ~{remaining} ч.")
        return
    reward = random.randint(200, 500)
    change_balance(uid, reward)
    data["users"][uid]["bonus_time"] = now
    save_data()
    bot.send_message(m.chat.id, f"🎁 Ты получил {reward} фишек! Баланс: {get_balance(uid)}")

# ========== ПЕРЕВОД ==========
@bot.message_handler(func=lambda m: m.text == "💸 Перевести")
def start_transfer(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    bot.send_message(m.chat.id, "💳 Введи @username и сумму через пробел.\n\nПример: @rut 200")
    bot.register_next_step_handler(m, make_transfer)

def make_transfer(m: types.Message):
    sender = str(m.from_user.id)
    parts = (m.text or "").split()
    if len(parts) != 2:
        return bot.send_message(m.chat.id, "⚠️ Неверный формат. Пример: @rut 200")
    target_name = parts[0].lstrip("@")
    try:
        amount = int(parts[1])
    except:
        return bot.send_message(m.chat.id, "⚠️ Сумма должна быть числом.")
    if amount <= 0:
        return bot.send_message(m.chat.id, "⚠️ Сумма должна быть больше нуля.")
    if get_balance(sender) < amount:
        return bot.send_message(m.chat.id, "😢 Недостаточно фишек.")
    # найдем пользователя по username
    target_uid = None
    for tid, info in data["users"].items():
        if info.get("username", "") == target_name:
            target_uid = tid
            break
    if not target_uid:
        return bot.send_message(m.chat.id, "❌ Пользователь не найден или не зарегистрирован (ему нужно было нажать /start).")
    change_balance(sender, -amount)
    change_balance(target_uid, amount)
    bot.send_message(m.chat.id, f"✅ Переведено {amount} фишек пользователю @{target_name}")
    try:
        bot.send_message(int(target_uid), f"💰 Тебе перевели {amount} фишек от @{m.from_user.username or m.from_user.first_name}")
    except:
        pass

# ========== БАЛАНС ==========
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(m: types.Message):
    uid = str(m.from_user.id)
    ensure_user(uid, m.from_user.username or m.from_user.first_name)
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек")

# ========== ТОП ==========
@bot.message_handler(func=lambda m: m.text == "📊 Топ")
def top_cmd(m: types.Message):
    items = []
    for k, v in data.get("users", {}).items():
        items.append((k, v.get("balance", 0)))
    items.sort(key=lambda x: x[1], reverse=True)
    lines = []
    for i, (uid, bal) in enumerate(items[:10], start=1):
        lines.append(f"{i}. @{data['users'][uid].get('username','?')} ({uid}) — {bal} фишек")
    bot.send_message(m.chat.id, "📊 Топ игроков:\n\n" + ("\n".join(lines) if lines else "Пока нет игроков."))

# ========== ПОМОЩЬ ==========
@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_cmd(m: types.Message):
    bot.send_message(m.chat.id, "📘 Команды:\n🎰 Слоты\n🎯 Рулетка\n🎲 Кости\n🎁 Бонус\n💸 Перевести\n📊 Топ\n🆘 Помощь — @ownerrut")

# ========== ПРИВЕТСТВИЕ В ГРУППЕ ==========
@bot.message_handler(content_types=['new_chat_members'])
def greet_new_member(m: types.Message):
    for user in m.new_chat_members:
        name = user.first_name or user.username or "Игрок"
        text = (
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
            "　　　🎰 CASINO RUTA 🎲\n"
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
            f"👋 Добро пожаловать, {name}!\n"
            "Ты попал в легендарное казино удачи 💫\n\n"
            "🎁 Используй /start в личке со мной, чтобы получить стартовые фишки!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "　　　Желаем удачи в игре! 🍀"
        )
        bot.send_message(m.chat.id, text)

# ------------------ Админ-панель ------------------
ADMINS = [718853742]  # замените на ваши ID

LOG_FILE = "admin_logs.json"

def log_action(action: str):
    try:
        logs = {}
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        idx = str(len(logs) + 1)
        logs[idx] = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action}
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Log error:", e)

@bot.message_handler(commands=["admin"])
def admin_panel_cmd(m: types.Message):
    if m.from_user.id not in ADMINS:
        return bot.send_message(m.chat.id, "🚫 У вас нет доступа в админ-панель.")
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Начислить", callback_data="adm_add"),
        types.InlineKeyboardButton("➖ Снять", callback_data="adm_remove"),
        types.InlineKeyboardButton("🚫 Бан", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ Разбан", callback_data="adm_unban"),
        types.InlineKeyboardButton("❄️ Заморозить", callback_data="adm_freeze"),
        types.InlineKeyboardButton("🔥 Разморозить", callback_data="adm_unfreeze"),
        types.InlineKeyboardButton("⚠️ Предупредить", callback_data="adm_warn"),
        types.InlineKeyboardButton("♻️ Обнулить", callback_data="adm_reset"),
        types.InlineKeyboardButton("📁 Экспорт (json)", callback_data="adm_export"),
        types.InlineKeyboardButton("📜 Логи", callback_data="adm_logs"),
        types.InlineKeyboardButton("💰 Баланс по ID", callback_data="adm_balance"),
    )
    bot.send_message(m.chat.id, "👑 Админ-панель:", reply_markup=kb)

# Обработчик админских callback'ов
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_"))
def admin_cb(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    action = call.data.split("_",1)[1]
    if action in ("add","remove"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id> <amount>")
        bot.register_next_step_handler(msg, admin_add_remove, action)
    else:
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя:")
        bot.register_next_step_handler(msg, admin_status_action, action)

def admin_add_remove(m: types.Message, action: str):
    if m.from_user.id not in ADMINS:
        return
    parts = (m.text or "").strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        return bot.send_message(m.chat.id, "Неверный формат. Введите: <user_id> <amount>")
    target = int(parts[0]); amount = int(parts[1])
    ensure_user(str(target))
    if action == "add":
        change_balance(str(target), amount)
        bot.send_message(m.chat.id, f"✅ Добавлено {amount} фишек пользователю {target}. Баланс: {get_balance(target)}")
        log_action(f"{m.from_user.id} added {amount} to {target}")
    else:
        if get_balance(target) < amount:
            return bot.send_message(m.chat.id, "У пользователя недостаточно фишек.")
        change_balance(str(target), -amount)
        bot.send_message(m.chat.id, f"✅ Снято {amount} фишек у пользователя {target}. Баланс: {get_balance(target)}")
        log_action(f"{m.from_user.id} removed {amount} from {target}")

def admin_status_action(m: types.Message, action: str):
    if m.from_user.id not in ADMINS:
        return
    if not (m.text or "").strip().isdigit():
    if not (m.text or "").strip().isdigit():
        return bot.send_message(m.chat.id, "Неверный ID.")
    target = int(m.text.strip())
    ensure_user(str(target))
    if action == "ban":
        data["users"][str(target)]["banned"] = True
        save_data()
        bot.send_message(m.chat.id, f"🚫 Пользователь {target} забанен.")
        log_action(f"{m.from_user.id} banned {target}")
    elif action == "unban":
        data["users"][str(target)]["banned"] = False
        save_data()
        bot.send_message(m.chat.id, f"✅ Пользователь {target} разбанен.")
        log_action(f"{m.from_user.id} unbanned {target}")
    elif action == "freeze":
        data["users"][str(target)]["frozen"] = True
        save_data()
        bot.send_message(m.chat.id, f"❄️ Пользователь {target} заморожен.")
        log_action(f"{m.from_user.id} frozen {target}")
    elif action == "unfreeze":
        data["users"][str(target)]["frozen"] = False
        save_data()
        bot.send_message(m.chat.id, f"✅ Пользователь {target} разморожен.")
        log_action(f"{m.from_user.id} unfroze {target}")
    elif action == "warn":
        data["users"][str(target)].setdefault("warns",0)
        data["users"][str(target)]["warns"] += 1
        save_data()
        bot.send_message(m.chat.id, f"⚠️ Предупреждение пользователю {target}.")
        log_action(f"{m.from_user.id} warned {target}")
    elif action == "reset":
        data["users"][str(target)]["balance"] = 0
        save_data()
        bot.send_message(m.chat.id, f"♻️ Баланс пользователя {target} обнулён.")
        log_action(f"{m.from_user.id} reset {target}")
    elif action == "export":
        save_data()
        try:
            bot.send_document(m.chat.id, open(DATA_FILE, "rb"))
        except Exception as e:
            bot.send_message(m.chat.id, f"Ошибка экспорта: {e}")
    elif action == "logs":
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                items = list(logs.items())[-50:]
                text = "\n".join([f"{k}: {v['time']} — {v['action']}" for k,v in items])
                bot.send_message(m.chat.id, f"📜 Логи:\n\n{text}")
            else:
                bot.send_message(m.chat.id, "Логов нет.")
        except Exception as e:
            bot.send_message(m.chat.id, f"Ошибка чтения логов: {e}")
    elif action == "balance":
        bot.send_message(m.chat.id, f"Баланс {target}: {get_balance(target)}")
    else:
        bot.send_message(m.chat.id, "Неизвестное действие.")

# ====== ЗАПУСК ======
if __name__ == "__main__":
    print("✅ Бот запущен и слушает сообщения...")
    bot.infinity_polling(skip_pending=True)
