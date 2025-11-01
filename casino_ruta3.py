#!/usr/bin/env python3
# casino_ruta3.py — 🎰 Казино Рута 3.0 (telebot)
# Требует: pyTelegramBotAPI
# Запуск:
# export BOT_TOKEN="123456789:ABC-..."
# python3 casino_ruta3.py

import os
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any

import telebot
from telebot import types

# ---------------- Config ----------------
ADMIN_ID = 718853742  # <-- твой Telegram ID (админ)
DATA_FILE = "casino_data.json"
BACKUP_FILE = "casino_data_backup.json"

MIN_BET = 100
MAX_BET = 5000
DAILY_BONUS = 1000
BONUS_SECONDS = 86400  # 24 часа

SLOT_SYMBOLS = ["🍒", "🍋", "💎", "⭐", "🍀", "7️⃣"]
SLOT_ANIM_SECONDS = 5  # эмодзи будут меняться 5 секунд
SLOT_ANIM_PERIOD = 1   # обновлять каждые 1 сек

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------- Token ----------------
TOKEN = os.getenv("8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A")
if not TOKEN or ":" not in TOKEN:
    print("❌ Ошибка: переменная окружения BOT_TOKEN не задана или неверного формата.")
    print('Установи токен: export BOT_TOKEN="123456789:ABC-..."')
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ---------------- Data model ----------------
# structure:
# {
#   "users": {
#        "<user_id>": {
#            "balance": int,
#            "last_bonus": float,
#            "banned": bool,
#            "frozen": bool
#        }, ...
#   }
# }
data: Dict[str, Any] = {"users": {}}


def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.exception("Failed to load data, trying backup: %s", e)
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                except Exception:
                    data = {"users": {}}
            else:
                data = {"users": {}}
    else:
        data = {"users": {}}


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to save data")


def ensure_user(uid: int):
    k = str(uid)
    if k not in data["users"]:
        data["users"][k] = {
            "balance": 1000,
            "last_bonus": 0.0,
            "banned": False,
            "frozen": False
        }
        save_data()


def get_user(uid: int):
    ensure_user(uid)
    return data["users"][str(uid)]


def get_balance(uid: int) -> int:
    return int(get_user(uid)["balance"])


def change_balance(uid: int, delta: int):
    u = get_user(uid)
    u["balance"] = int(u.get("balance", 0) + int(delta))
    save_data()


def set_balance(uid: int, amount: int):
    u = get_user(uid)
    u["balance"] = int(amount)
    save_data()


def set_status(uid: int, banned=None, frozen=None):
    u = get_user(uid)
    if banned is not None:
        u["banned"] = bool(banned)
    if frozen is not None:
        u["frozen"] = bool(frozen)
    save_data()


def can_play(uid: int) -> (bool, str):
    u = get_user(uid)
    if u.get("banned"):
        return False, "🚫 Вы забанены."
    if u.get("frozen"):
        return False, "❄️ Ваш аккаунт заморожен — операции ограничены."
    return True, ""


# ---------------- UI helpers ----------------
def main_reply_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 Казино", "🎁 Бонус", "💰 Баланс")
    kb.row("🎲 Кости", "🎯 Угадай число", "🎰 Слоты (кнопки)")
    kb.row("💸 Перевод", "📊 Топ", "ℹ️ Помощь")
    return kb


def inline_bets_keyboard(prefix="slot"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💵 100", callback_data=f"{prefix}_bet_100"),
           types.InlineKeyboardButton("💰 500", callback_data=f"{prefix}_bet_500"),
           types.InlineKeyboardButton("💎 1000", callback_data=f"{prefix}_bet_1000"))
    kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="menu_back"))
    return kb


def admin_inline_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Начислить", callback_data="adm_add"),
           types.InlineKeyboardButton("➖ Снять", callback_data="adm_remove"))
    kb.add(types.InlineKeyboardButton("🚫 Забанить", callback_data="adm_ban"),
           types.InlineKeyboardButton("✅ Разбанить", callback_data="adm_unban"))
    kb.add(types.InlineKeyboardButton("❄️ Заморозить", callback_data="adm_freeze"),
           types.InlineKeyboardButton("🔥 Разморозить", callback_data="adm_unfreeze"))
    kb.add(types.InlineKeyboardButton("♻️ Обнулить", callback_data="adm_reset"),
           types.InlineKeyboardButton("📁 Экспорт", callback_data="adm_export"))
    kb.add(types.InlineKeyboardButton("🔙 Главное меню", callback_data="menu_back"))
    return kb


# ---------------- Utilities ----------------
def format_top(n=10):
    items = [(int(k), v["balance"]) for k, v in data["users"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    if not items:
        return "Пока нет игроков."
    lines = []
    for i, (uid, bal) in enumerate(items[:n], start=1):
        lines.append(f"{i}. `{uid}` — {bal} фишек")
    return "\n".join(lines)


# ---------------- Handlers ----------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    ensure_user(uid)
    kb = main_reply_keyboard()
    bot.send_message(message.chat.id,
                     f"🎰 <b>Казино Рута 3.0</b>\nПривет, {message.from_user.first_name}!\n💰 Баланс: {get_balance(uid)} фишек",
                     reply_markup=kb, parse_mode="HTML")


@bot.message_handler(commands=["balance"])
def cmd_balance(message):
    uid = message.from_user.id
    ensure_user(uid)
    bot.send_message(message.chat.id, f"💳 Твой баланс: {get_balance(uid)} фишек", reply_markup=main_reply_keyboard())


@bot.message_handler(commands=["top"])
def cmd_top(message):
    bot.send_message(message.chat.id, "📊 Топ игроков:\n\n" + format_top(10), parse_mode="Markdown", reply_markup=main_reply_keyboard())


@bot.message_handler(commands=["bonus"])
def cmd_bonus(message):
    uid = message.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(message.chat.id, reason, reply_markup=main_reply_keyboard())
        return
    now = time.time()
    last = get_user(uid).get("last_bonus", 0.0)
    if now - last < BONUS_SECONDS:
        remain = int((BONUS_SECONDS - (now - last)) // 3600)
        bot.send_message(message.chat.id, f"⏳ Бонус уже взят. Приходи через ~{remain} ч.", reply_markup=main_reply_keyboard())
    else:
        change_balance(uid, DAILY_BONUS)
        get_user(uid)["last_bonus"] = now
        save_data()
        bot.send_message(message.chat.id, f"🎁 Ты получил {DAILY_BONUS} фишек! 💰 Баланс: {get_balance(uid)}", reply_markup=main_reply_keyboard())


# Interactive transfer via /transfer <id> <amount> or menu
@bot.message_handler(commands=["transfer"])
def cmd_transfer(message):
    uid = message.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(message.chat.id, reason, reply_markup=main_reply_keyboard())
        return
    parts = message.text.split()
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        target = int(parts[1]); amount = int(parts[2])
        if amount < MIN_BET:
            bot.send_message(message.chat.id, f"Минимум для перевода {MIN_BET} фишек.", reply_markup=main_reply_keyboard()); return
        if get_balance(uid) < amount:
            bot.send_message(message.chat.id, "❌ Недостаточно фишек.", reply_markup=main_reply_keyboard()); return
        ensure_user(target)
        change_balance(uid, -amount)
        change_balance(target, amount)
        bot.send_message(message.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`.\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        try:
            bot.send_message(target, f"💸 Тебе перевели {amount} фишек от @{message.from_user.username or message.from_user.id}!")
        except:
            pass
        return
    # otherwise enter interactive flow
    msg = bot.send_message(message.chat.id, "🔁 Введи ID пользователя, которому хочешь перевести фишки (или /cancel):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, transfer_step1)


def transfer_step1(message):
    if message.text is None:
        return
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ ID должен быть числом. Операция отменена.", reply_markup=main_reply_keyboard()); return
    target = int(message.text)
    msg = bot.send_message(message.chat.id, "💰 Введи сумму перевода (минимум 100):")
    bot.register_next_step_handler(msg, transfer_step2, target)


def transfer_step2(message, target):
    if message.text is None or not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Неверная сумма. Операция отменена.", reply_markup=main_reply_keyboard()); return
    amount = int(message.text)
    uid = message.from_user.id
    if amount < MIN_BET:
        bot.send_message(message.chat.id, f"Минимум для перевода {MIN_BET} фишек.", reply_markup=main_reply_keyboard()); return
    if get_balance(uid) < amount:
        bot.send_message(message.chat.id, "❌ Недостаточно фишек.", reply_markup=main_reply_keyboard()); return
    ensure_user(target)
    change_balance(uid, -amount)
    change_balance(target, amount)
    bot.send_message(message.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`.\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    try:
        bot.send_message(target, f"💸 Тебе перевели {amount} фишек от @{message.from_user.username or message.from_user.id}!")
    except:
        pass


# ---------------- Mini-games ----------------
# Slots with animation (5 seconds) — key feature user requested
def spin_slots_and_show(chat_id, user_id, amount, message_id_to_edit=None):
    """
    Spins slots with animation: change emojis every SLOT_ANIM_PERIOD for SLOT_ANIM_SECONDS,
    then decide result and update message.
    message_id_to_edit: if not None, edit that message; otherwise send new message
    """
    # prepare animation frames
    total_frames = SLOT_ANIM_SECONDS // SLOT_ANIM_PERIOD
    # send initial message or edit existing
    text = "🎲 Крутим барабаны..."
    if message_id_to_edit:
        bot.edit_message_text(chat_id=chat_id, text=text, message_id=message_id_to_edit)
        msg_id = message_id_to_edit
    else:
        m = bot.send_message(chat_id, text)
        msg_id = m.message_id

    # deduct bet upfront
    change_balance(user_id, -amount)

    # animate
    last_symbols = None
    for _ in range(total_frames):
        s1, s2, s3 = random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS)
        last_symbols = (s1, s2, s3)
        frame = f"🎰 | {s1} | {s2} | {s3} |"
        try:
            bot.edit_message_text(chat_id=chat_id, text=frame, message_id=msg_id)
,        except Exception:
            # ignore editing errors (group contexts)
            try:
                bot.send_message(chat_id, frame)
            except:
                pass
        time.sleep(SLOT_ANIM_PERIOD)

    # final result calculation
    s1, s2, s3 = last_symbols
    if s1 == s2 == s3:
        win = amount * 5
        change_balance(user_id, win)
        result_text = f"💎 Джекпот! Все совпали! +{win} фишек!"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = amount * 2
        change_balance(user_id, win)
        result_text = f"⭐ 2 символа совпали! +{win} фишек!"
    else:
        result_text = f"💀 Увы, ничего не совпало. -{amount} фишек."

    final = f"🎰 | {s1} | {s2} | {s3} |\n\n{result_text}\n\n💰 Баланс: {get_balance(user_id)}"
    try:
        bot.edit_message_text(chat_id=chat_id, text=final, message_id=msg_id)
    except Exception:
        bot.send_message(chat_id, final)
    save_data()


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("slot_bet_"))
def cb_slot_bet(call):
    # callback_data: slot_bet_<amount>
    uid = call.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.answer_callback_query(call.id, reason, show_alert=True)
        bot.edit_message_text(reason, call.message.chat.id, call.message.message_id, reply_markup=main_reply_keyboard())
        return
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка должна быть от {MIN_BET} до {MAX_BET}.", show_alert=True)
        return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек.", show_alert=True)
        bot.edit_message_text("❌ Недостаточно фишек.", call.message.chat.id, call.message.message_id, reply_markup=main_reply_keyboard())
        return

    bot.answer_callback_query(call.id)
    # start spin in same message for nicer effect
    try:
        spin_slots_and_show(call.message.chat.id, uid, amount, message_id_to_edit=call.message.message_id)
    except Exception as e:
        logger.exception("Slot spin error: %s", e)
        bot.send_message(call.message.chat.id, "Ошибка игры.")


# Command /bet_slots <amount> for text command
@bot.message_handler(commands=["bet_slots"])
def cmd_bet_slots(message):
    uid = message.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(message.chat.id, reason, reply_markup=main_reply_keyboard()); return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Используй: /bet_slots <сумма>", reply_markup=main_reply_keyboard()); return
    amount = int(parts[1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.send_message(message.chat.id, f"Ставка должна быть от {MIN_BET} до {MAX_BET}.", reply_markup=main_reply_keyboard()); return
    if get_balance(uid) < amount:
        bot.send_message(message.chat.id, "Недостаточно фишек.", reply_markup=main_reply_keyboard()); return
    # send a message and animate editing it
    m = bot.send_message(message.chat.id, "🎲 Крутим барабаны...")
    spin_slots_and_show(message.chat.id, uid, amount, message_id_to_edit=m.message_id)


# Roulette — simple: chance with multiplier
@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("roul_bet_"))
def cb_roul_bet(call):
    uid = call.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.answer_callback_query(call.id, reason, show_alert=True); return
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка должна быть от {MIN_BET} до {MAX_BET}.", show_alert=True); return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек.", show_alert=True); return
    bot.answer_callback_query(call.id)
    # play roulette
    change_balance(uid, -amount)
    roll = random.random()
    if roll < 0.30:  # win
        win = amount * 3
        change_balance(uid, win)
        text = f"🎉 Победа в рулетке! +{win} фишек!"
    else:
        text = f"💀 Проигрыш. -{amount} фишек."
    bot.edit_message_text(f"{text}\n💰 Баланс: {get_balance(uid)}", call.message.chat.id, call.message.message_id, reply_markup=main_reply_keyboard())


# text-based games: dice and guess handled in message handler below
def play_dice(chat_id, uid):
    ensure_user(uid)
    if not can_play(uid)[0]:
        bot.send_message(chat_id, "Недоступно.")
        return
    roll = random.randint(1, 6)
    bot.send_message(chat_id, f"🎲 Выпало число: {roll}")


def guess_number_round(message):
    uid = message.from_user.id
    ensure_user(uid)
    if not can_play(uid)[0]:
        bot.send_message(message.chat.id, "Недоступно."); return
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введите число 1–5"); return
    choice = int(message.text)
    if choice < 1 or choice > 5:
        bot.send_message(message.chat.id, "Введите число от 1 до 5"); return
    num = random.randint(1, 5)
    if choice == num:
        win = 500
        change_balance(uid, win)
        bot.send_message(message.chat.id, f"🎯 Угадал! +{win} фишек!\n💰 Баланс: {get_balance(uid)}")
    else:
        bot.send_message(message.chat.id, f"😢 Неверно — было {num}.\n💰 Баланс: {get_balance(uid)}")


# ---------------- Admin commands ----------------
@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = admin_inline_kb()
    bot.send_message(message.chat.id, "👑 Админ-панель:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("adm_"))
def cb_admin(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    action = call.data.split("_", 1)[1]
    # prompt admin for input using next-step handlers
    if action in ("add", "remove"):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введи: <user_id> <amount>")
        bot.register_next_step_handler(msg, admin_add_remove, action)
    elif action in ("ban", "unban", "freeze", "unfreeze", "reset"):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "Введи: <user_id>")
        bot.register_next_step_handler(msg, admin_status_action, action)
    elif action == "export":
        bot.answer_callback_query(call.id)
        save_data()
        try:
            with open(DATA_FILE, "rb") as f:
                bot.send_document(call.message.chat.id, f)
        except Exception as e:
            logger.exception("Export failed: %s", e)
            bot.send_message(call.message.chat.id, "Ошибка при экспорте.")
    else:
        bot.answer_callback_query(call.id)


def admin_add_remove(message, action):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip('-').isdigit():
        bot.send_message(message.chat.id, "Неверный формат. Используй: <user_id> <amount>"); return
    target = int(parts[0]); amount = int(parts[1])
    ensure_user(target)
    if action == "add":
        change_balance(target, amount)
        bot.send_message(message.chat.id, f"✅ Добавлено {amount} фишек пользователю {target}. Баланс: {get_balance(target)}")
        try:
            bot.send_message(target, f"👑 Админ начислил тебе {amount} фишек!")
        except:
            pass
    else:
        if get_balance(target) < amount:
            bot.send_message(message.chat.id, "⚠️ У пользователя недостаточно фишек."); return
        change_balance(target, -amount)
        bot.send_message(message.chat.id, f"✅ Снято {amount} фишек у пользователя {target}. Баланс: {get_balance(target)}")
        try:
            bot.send_message(target, f"👑 Админ снял {amount} фишек с вашего баланса.")
        except:
            pass


def admin_status_action(message, action):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text.strip().isdigit():
        bot.send_message(message.chat.id, "Неверный формат. Введи: <user_id>"); return
    target = int(message.text.strip())
    ensure_user(target)
    if action == "ban":
        set_status(target, banned=True); bot.send_message(message.chat.id, f"🚫 {target} забане
