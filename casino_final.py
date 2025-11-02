import json
import telebot
import random
import time
from telebot import types

MIN_BET = 50  # минимальная ставка

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

# 🎰 — СЛОТЫ
@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots_start(m):
    bot.send_message(m.chat.id, "🎰 Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(m, slots_play)

def slots_play(m):
    uid = str(m.from_user.id)
    amount = m.text.strip()
    data = load_data()
    ensure_user(uid)

    if not amount.isdigit():
        bot.reply_to(m, "❌ Введите число.")
        return

    amount = int(amount)
    if amount < MIN_BET:
        bot.reply_to(m, f"Минимальная ставка — {MIN_BET} фишек.")
        return

    if data["users"][uid]["balance"] < amount:
        bot.reply_to(m, "💸 Недостаточно фишек.")
        return

    reels = ["🍒", "🍋", "🔔", "🍀", "⭐", "💎"]
    msg = bot.send_message(m.chat.id, "🎰 Вращение...")
    for _ in range(3):
        spin = f"{random.choice(reels)} | {random.choice(reels)} | {random.choice(reels)}"
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"🎰 {spin}")
        time.sleep(0.5)

    final = [random.choice(reels) for _ in range(3)]
    result = " | ".join(final)
    win = final[0] == final[1] == final[2]

    if win:
        prize = amount * 5
        data["users"][uid]["balance"] += prize
        text = f"🎉 {result}\nВы выиграли {prize} фишек!"
    else:
        data["users"][uid]["balance"] -= amount
        text = f"{result}\n😢 Вы проиграли {amount} фишек."

    save_data(data)
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"🎰 {text}\n💰 Баланс: {data['users'][uid]['balance']}")


# 🎡 — РУЛЕТКА
@bot.message_handler(func=lambda m: m.text == "🎡 Рулетка")
def roulette_start(m):
    bot.send_message(m.chat.id, "🎡 Введите сумму ставки (минимум 50):")
    bot.register_next_step_handler(m, roulette_play)

def roulette_play(m):
    uid = str(m.from_user.id)
    amount = m.text.strip()
    data = load_data()
    ensure_user(uid)

    if not amount.isdigit():
        bot.reply_to(m, "❌ Введите число.")
        return

    amount = int(amount)
    if amount < MIN_BET:
        bot.reply_to(m, f"Минимальная ставка — {MIN_BET} фишек.")
        return

    if data["users"][uid]["balance"] < amount:
        bot.reply_to(m, "💸 Недостаточно фишек.")
        return

    bot.send_message(m.chat.id, "🎡 Вращаем колесо...")
    slots = ["🔴 Красное", "⚫ Чёрное", "🟢 Зелёное"]
    msg = bot.send_message(m.chat.id, "⚪ Крутится...")

    for _ in range(5):
        spin = random.choice(slots)
        bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"🎯 {spin}")
        time.sleep(0.5)

    result = random.choices(slots, weights=[45, 45, 10])[0]

    if result == "🟢 Зелёное":
        prize = amount * 10
        data["users"][uid]["balance"] += prize
        text = f"🟢 Зелёное! Вы выиграли {prize} фишек!"
    else:
        data["users"][uid]["balance"] -= amount
        text = f"{result} — вы проиграли {amount} фишек."

    save_data(data)
    bot.edit_message_text(chat_id=m.chat.id, message_id=msg.message_id, text=f"{text}\n💰 Баланс: {data['users'][uid]['balance']}")

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

# ------------------ Админ-панель (исправленная) ------------------
ADMINS = [718853742]  # <-- добавь сюда ID админов

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
        # не ломаем бота из-за логов
        print("Log error:", e)

# Команда /admin — показать панель
@bot.message_handler(commands=["admin"])
def admin_panel_cmd(m):
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

# Когда админ нажал кнопку — спросим нужные данные
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_"))
def on_admin_cb(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    action = call.data.split("_",1)[1]  # e.g. "add", "ban", ...
    bot.answer_callback_query(call.id)
    # Спрашиваем у админа данные в зависимости от действия
    if action in ("add","remove"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id> <amount> (пример: 12345678 500)")
        bot.register_next_step_handler(msg, admin_handle_add_remove, action)
    elif action in ("ban","unban","freeze","unfreeze","warn","reset","balance"):
        msg = bot.send_message(call.message.chat.id, "Введите ID пользователя (например: 12345678):")
        bot.register_next_step_handler(msg, admin_handle_id_action, action)
    elif action == "export":
        # просто отправляем файл данных
        try:
            save_data()  # если такая функция есть — обновим файл
        except:
            pass
        try:
            bot.send_document(call.message.chat.id, open(DATA_FILE, "rb"))
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Ошибка экспорта: {e}")
    elif action == "logs":
        # выведем последние 30 строк логов, если есть
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                items = list(logs.items())[-30:]
                text = "\n".join([f"{k}: {v['time']} — {v['action']}" for k,v in items])
                bot.send_message(call.message.chat.id, f"📜 Логи (последние):\n\n{text}")
            else:
                bot.send_message(call.message.chat.id, "📁 Логи пусты.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Ошибка чтения логов: {e}")

# Обработчик для действий, где требуется "<id> <amount>"
def admin_handle_add_remove(m: types.Message, action: str):
    # защита: проверяем, что тот кто ввёл — админ
    if m.from_user.id not in ADMINS:
        return bot.send_message(m.chat.id, "🚫 Нет доступа.")
    parts = (m.text or "").strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        return bot.send_message(m.chat.id, "Неверный формат. Введите: <user_id> <amount> (пример: 12345678 500)")
    target = int(parts[0])
    amount = int(parts[1])
    data = load_data()
    uid = str(target)
    if uid not in data["users"]:
        ensure_user(target)  # создадим
        data = load_data()
    if action == "add":
        change_balance(uid, amount) if isinstance(uid,str) else change_balance(target, amount)
        bot.send_message(m.chat.id, f"✅ Добавлено {amount} фишек пользователю {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ начислил вам {amount} фишек.")
        except: pass
        log_action(f"Admin {m.from_user.id} added {amount} to {target}")
    else:  # remove
        if get_balance(target) < amount:
            return bot.send_message(m.chat.id, "У пользователя недостаточно фишек.")
        change_balance(uid, -amount) if isinstance(uid,str) else change_balance(target, -amount)
        bot.send_message(m.chat.id, f"✅ Снято {amount} фишек у пользователя {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ снял {amount} фишек с вашего баланса.")
        except: pass
        log_action(f"Admin {m.from_user.id} removed {amount} from {target}")

# Обработчик для действий, где требуется только "<id>"
def admin_handle_id_action(m: types.Message, action: str):
    if m.from_user.id not in ADMINS:
        return bot.send_message(m.chat.id, "🚫 Нет доступа.")
    txt = (m.text or "").strip()
    if not txt.isdigit():
        return bot.send_message(m.chat.id, "Неверный ID. Введите только цифры.")
    target = int(txt)
    data = load_data()
    uid = str(target)
    # ensure user exists
    if uid not in data["users"]:
        ensure_user(target)

    if action == "ban":
        data["users"][uid]["banned"] = True
        save_data(data)
        bot.send_message(m.chat.id, f"🚫 Пользователь {target} забанен.")
        try: bot.send_message(target, "🚫 Вы были забанены администратором.")
        except: pass
        log_action(f"Admin {m.from_user.id} banned {target}")

    elif action == "unban":
        data["users"][uid]["banned"] = False
        save_data(data)
        bot.send_message(m.chat.id, f"✅ Пользователь {target} разбанен.")
        log_action(f"Admin {m.from_user.id} unbanned {target}")

    elif action == "freeze":
        data["users"][uid]["frozen"] = True
        save_data(data)
        bot.send_message(m.chat.id, f"❄️ Пользователь {target} заморожен.")
        log_action(f"Admin {m.from_user.id} frozen {target}")

    elif action == "unfreeze":
        data["users"][uid]["frozen"] = False
        save_data(data)
        bot.send_message(m.chat.id, f"✅ Пользователь {target} разморожен.")
        log_action(f"Admin {m.from_user.id} unfroze {target}")

    elif action == "warn":
        data["users"][uid].setdefault("warns", 0)
        data["users"][uid]["warns"] += 1
        save_data(data)
        bot.send_message(m.chat.id, f"⚠️ Предупреждение пользователю {target}. Всего предупреждений: {data['users'][uid]['warns']}")
        log_action(f"Admin {m.from_user.id} warned {target}")

    elif action == "reset":
        data["users"][uid]["balance"] = 0
        save_data(data)
        bot.send_message(m.chat.id, f"♻️ Баланс пользователя {target} обнулён.")
        log_action(f"Admin {m.from_user.id} reset balance {target}")

    elif action == "balance":
        bal = get_balance(target)
        bot.send_message(m.chat.id, f"💰 Баланс {target}: {bal} фишек.")
        log_action(f"Admin {m.from_user.id} checked balance {target}")

    else:
        bot.send_message(m.chat.id, "Неизвестное действие.")

# --------------------------------------------------------------------

# ====== ЗАПУСК ======
if __name__ == "__main__":
    print("✅ Бот запущен и слушает сообщения...")
    bot.infinity_polling(skip_pending=True)
