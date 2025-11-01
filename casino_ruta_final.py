#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Casino Ruta Final — полный рабочий бот
Требует: pyTelegramBotAPI
Перед запуском: pip install pyTelegramBotAPI
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, Optional

import telebot
from telebot import types

# ========== CONFIG ==========
TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"   # <-- твой токен
ADMINS = [718853742]  # админ(ы)
OWNER_USERNAME = "ownerrut"

DATA_FILE = "data.json"
BACKUP_FILE = "data_backup.json"

MIN_BET = 50
MAX_BET = 50000
DAILY_BONUS = 1000
BONUS_SECONDS = 86400  # 24 hours

SLOT_EMOJIS = ["🍒","🍋","🍇","🍉","💎","7️⃣","🍀","⭐"]

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("casino_ruta")

# ========== BOT ==========
if not TOKEN or TOKEN.strip() == "":
    print("ERROR: Вставь токен в переменную TOKEN")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========== DATA HELPERS ==========
data: Dict[str, Any] = {}

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # backup attempt
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                        logger.info("Loaded data from backup")
                except Exception:
                    data = {}
            else:
                data = {}
    else:
        data = {}
    # ensure minimal structure
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    if "meta" not in data:
        data["meta"] = {"created": time.time()}
    return data

def save_data():
    global data
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # write backup
        with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to save data")

def ensure_user(uid: int, username: Optional[str]=None):
    global data
    k = str(uid)
    if k not in data["users"]:
        data["users"][k] = {
            "balance": 1000,
            "last_bonus": 0.0,
            "banned": False,
            "frozen": False,
            "wins": 0,
            "losses": 0,
            "games_played": 0,
            "username": username or "",
            "warns": 0
        }
        save_data()
    else:
        # update username if provided
        if username:
            if data["users"][k].get("username") != username:
                data["users"][k]["username"] = username
                save_data()

def get_user(uid: int) -> Dict[str, Any]:
    ensure_user(uid)
    return data["users"][str(uid)]

def get_balance(uid: int) -> int:
    return int(get_user(uid).get("balance", 0))

def change_balance(uid: int, delta: int):
    u = get_user(uid)
    u["balance"] = int(u.get("balance", 0) + int(delta))
    save_data()

def set_balance(uid: int, amount: int):
    u = get_user(uid)
    u["balance"] = int(amount)
    save_data()

def set_status(uid: int, banned: Optional[bool]=None, frozen: Optional[bool]=None):
    u = get_user(uid)
    if banned is not None:
        u["banned"] = bool(banned)
    if frozen is not None:
        u["frozen"] = bool(frozen)
    save_data()

def add_warn(uid:int, reason:Optional[str]=None):
    u = get_user(uid)
    u["warns"] = int(u.get("warns",0)) + 1
    save_data()
    return u["warns"]

def can_play(uid:int) -> (bool, Optional[str]):
    u = get_user(uid)
    if u.get("banned"):
        return False, "🚫 Вы забанены и не можете играть."
    if u.get("frozen"):
        return False, "❄️ Ваш аккаунт заморожен."
    return True, None

# ========== UI / KEYBOARDS ==========
def private_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 Слоты", "🎯 Рулетка", "🎲 Кости")
    kb.row("🎁 Бонус", "💰 Баланс", "📊 Топ")
    kb.row("💸 Перевести", "ℹ️ Помощь")
    return kb

def group_main_inline():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎰 Слоты", callback_data="g_slots"),
           types.InlineKeyboardButton("🎯 Рулетка", callback_data="g_roul"),
           types.InlineKeyboardButton("🎲 Кости", callback_data="g_dice"))
    kb.row(types.InlineKeyboardButton("🎁 Бонус", callback_data="g_bonus"),
           types.InlineKeyboardButton("💰 Баланс", callback_data="g_balance"),
           types.InlineKeyboardButton("📊 Топ", callback_data="g_top"))
    kb.row(types.InlineKeyboardButton("💸 Перевести", callback_data="g_transfer"),
           types.InlineKeyboardButton("ℹ️ Помощь", callback_data="g_help"))
    return kb

def back_to_menu_markup(private:bool):
    return private_main_keyboard() if private else group_main_inline()

# ========== RENDER HELPERS ==========
def nice_name(user: types.User) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)

def render_header(name: str, balance: int) -> str:
    bal_str = f"{balance:,}".replace(",", " ")
    header = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        f"👋 Привет, {name}!\n"
        "Добро пожаловать в легендарное казино удачи 💫\n\n"
        f"💰 Твой баланс: {bal_str} фишек\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "　　　Выбери игру ниже ⬇️\n\n"
        f"🆘 Нужна помощь? Обратись к 👉 @{OWNER_USERNAME}"
    )
    return header

# ========== HANDLERS: START / HELP / BALANCE / TOP / BONUS ==========
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid, getattr(m.from_user, "username", None) or getattr(m.from_user, "first_name", None))
    name = nice_name(m.from_user)
    text = render_header(name, get_balance(uid))
    if m.chat.type == "private":
        bot.send_message(m.chat.id, text, reply_markup=private_main_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(m.chat.id, text, reply_markup=group_main_inline(), parse_mode="HTML")

@bot.message_handler(commands=["help"])
def cmd_help(m: types.Message):
    send_help(m)

@bot.message_handler(commands=["balance"])
def cmd_balance(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

@bot.message_handler(commands=["top"])
def cmd_top(m: types.Message):
    items = [(int(k), v["balance"], v.get("username","")) for k,v in data["users"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    lines = []
    for i,(uid,bal,un) in enumerate(items[:10], start=1):
        if un:
            lines.append(f"{i}. {un} (`{uid}`) — {bal} фишек")
        else:
            lines.append(f"{i}. `{uid}` — {bal} фишек")
    text = "📊 Топ игроков:\n\n" + ("\n".join(lines) if lines else "Пока нет игроков.")
    bot.send_message(m.chat.id, text, parse_mode="Markdown", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

@bot.message_handler(commands=["bonus"])
def cmd_bonus(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    now = time.time()
    last = get_user(uid).get("last_bonus", 0.0)
    if now - last < BONUS_SECONDS:
        rem = int((BONUS_SECONDS - (now - last)) // 3600)
        bot.send_message(m.chat.id, f"⏳ Бонус уже взят. Через ~{rem} ч.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        return
    change_balance(uid, DAILY_BONUS)
    get_user(uid)["last_bonus"] = now
    save_data()
    bot.send_message(m.chat.id, f"🎁 Ты получил {DAILY_BONUS} фишек! Баланс: {get_balance(uid)}", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ========== TRANSFER (/transfer or interactive) ==========
@bot.message_handler(commands=["transfer"])
def cmd_transfer(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    parts = m.text.split()
    if len(parts) == 3:
        target_raw = parts[1]
        amount_raw = parts[2]
        try:
            amount = int(amount_raw)
        except:
            bot.send_message(m.chat.id, "Неверная сумма."); return
        # convert @username -> id if possible
        target_uid = None
        if target_raw.startswith("@"):
            uname = target_raw.strip("@")
            for tid, info in data["users"].items():
                if info.get("username") == uname:
                    target_uid = int(tid); break
        elif target_raw.isdigit():
            target_uid = int(target_raw)
        else:
            bot.send_message(m.chat.id, "Неверный ID/username."); return

        if target_uid is None:
            bot.send_message(m.chat.id, "Пользователь не найден или он не общался с ботом.")
            return

        if amount < MIN_BET:
            bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек"); return
        if get_balance(uid) < amount:
            bot.send_message(m.chat.id, "❌ Недостаточно фишек"); return

        ensure_user(target_uid)
        change_balance(uid, -amount)
        change_balance(target_uid, amount)
        bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target_uid}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, f"💸 Тебе перевели {amount} фишек от {nice_name(m.from_user)}")
        except:
            pass
        return

    bot.send_message(m.chat.id, "🔁 Введи ID или @username получателя:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(m, transfer_step1)

def transfer_step1(m: types.Message):
    if not m.text:
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard()); return
    target_raw = m.text.strip()
    bot.send_message(m.chat.id, "💰 Введи сумму:")
    bot.register_next_step_handler(m, transfer_step2, target_raw)

def transfer_step2(m: types.Message, target_raw: str):
    uid = m.from_user.id
    try:
        amount = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "Неверная сумма.", reply_markup=private_main_keyboard()); return
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек", reply_markup=private_main_keyboard()); return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек", reply_markup=private_main_keyboard()); return

    target_uid = None
    if target_raw.startswith("@"):
        uname = target_raw.strip("@")
        for tid, info in data["users"].items():
            if info.get("username") == uname:
                target_uid = int(tid); break
    elif target_raw.isdigit():
        target_uid = int(target_raw)
    else:
        bot.send_message(m.chat.id, "Неверный получатель.", reply_markup=private_main_keyboard()); return

    if target_uid is None:
        bot.send_message(m.chat.id, "Пользователь не найден или он не зарегистрирован.", reply_markup=private_main_keyboard()); return

    ensure_user(target_uid)
    change_balance(uid, -amount)
    change_balance(target_uid, amount)
    bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target_uid}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=private_main_keyboard())
    try:
        bot.send_message(target_uid, f"💸 Тебе перевели {amount} фишек от {nice_name(m.from_user)}")
    except:
        pass

# ========== SLOTS with animation and custom bet ==========
@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def slots_ask_bet(m: types.Message):
    uid = m.from_user.id
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Введите, сколько фишек хотите поставить (минимум {MIN_BET}):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("🔙 Назад"))
    bot.register_next_step_handler(m, slots_play)

def slots_play(m: types.Message):
    uid = m.from_user.id
    if not m.text or m.text.strip()=="🔙 Назад":
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    try:
        bet = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректное число.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    if bet < MIN_BET:
        bot.send_message(m.chat.id, f"❌ Минимальная ставка — {MIN_BET} фишек.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    if bet > MAX_BET:
        bot.send_message(m.chat.id, f"❌ Максимальная ставка — {MAX_BET} фишек.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    if get_balance(uid) < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек для ставки.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return

    # deduct upfront
    change_balance(uid, -bet)
    get_user(uid)["games_played"] = get_user(uid).get("games_played",0)+1
    save_data()

    # initial message
    msg = bot.send_message(m.chat.id, "🎰 <b>Крутим барабаны...</b>", parse_mode="HTML")
    # animation frames
    for _ in range(3):
        frame = " | ".join(random.choice(SLOT_EMOJIS) for _ in range(3))
        try:
            bot.edit_message_text(f"🎰 <b>Крутим...</b>\n\n{frame}", m.chat.id, msg.message_id, parse_mode="HTML")
        except:
            try:
                bot.send_message(m.chat.id, frame)
            except:
                pass
        time.sleep(0.6)

    # final
    a,b,c = (random.choice(SLOT_EMOJIS) for _ in range(3))
    result = f"{a} | {b} | {c}"
    win = 0
    if a==b==c:
        win = bet * 10
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        res_text = f"💎 Джекпот! +{win} фишек!"
    elif a==b or b==c or a==c:
        win = bet * 3
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        res_text = f"✨ Повезло! +{win} фишек!"
    else:
        get_user(uid)["losses"] = get_user(uid).get("losses",0)+1
        res_text = f"😢 Проигрыш. -{bet} фишек."

    if win:
        change_balance(uid, win)
    save_data()

    try:
        bot.edit_message_text(f"🎰 <b>Результат:</b>\n{result}\n\n{res_text}\n\n💰 Баланс: {get_balance(uid)} фишек",
                              m.chat.id, msg.message_id, parse_mode="HTML")
    except:
        bot.send_message(m.chat.id, f"🎰 Результат:\n{result}\n\n{res_text}\n\n💰 Баланс: {get_balance(uid)} фишек")

    # show menu
    bot.send_message(m.chat.id, "🔙", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ========== ROULETTE with bet and animation ==========
@bot.message_handler(func=lambda m: m.text == "🎯 Рулетка")
def roul_ask_bet(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    bot.send_message(m.chat.id, f"💰 Введите, сколько фишек хотите поставить (минимум {MIN_BET}):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("🔙 Назад"))
    bot.register_next_step_handler(m, roul_choose_color)

def roul_choose_color(m: types.Message):
    uid = m.from_user.id
    if not m.text or m.text.strip()=="🔙 Назад":
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    try:
        bet = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректное число."); return
    if bet < MIN_BET or bet > MAX_BET:
        bot.send_message(m.chat.id, f"Ставка от {MIN_BET} до {MAX_BET}"); return
    if get_balance(uid) < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек."); return

    # deduct
    change_balance(uid, -bet)
    get_user(uid)["games_played"] = get_user(uid).get("games_played",0)+1
    save_data()

    # ask color
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔴 Красное", "⚫ Чёрное", "🟢 Зелёное")
    kb.row("🔙 Назад")
    msg = bot.send_message(m.chat.id, f"🎯 На какой цвет ставите? (Ставка: {bet} фишек)", reply_markup=kb)
    bot.register_next_step_handler(msg, roul_spin, bet)

def roul_spin(m: types.Message, bet: int):
    uid = m.from_user.id
    choice = m.text.strip()
    if choice == "🔙 Назад":
        # refund bet
        change_balance(uid, bet)
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        return

    msg = bot.send_message(m.chat.id, "🎡 <b>Крутим рулетку...</b>", parse_mode="HTML")
    colors = ["🔴","⚫","🟢"]
    for _ in range(4):
        frame = " ".join(random.choice(colors) for _ in range(6))
        try:
            bot.edit_message_text(f"🎡 <b>Крутится...</b>\n\n{frame}", m.chat.id, msg.message_id, parse_mode="HTML")
        except:
            bot.send_message(m.chat.id, frame)
        time.sleep(0.6)

    result = random.choices(["🔴","⚫","🟢"], weights=[45,45,10], k=1)[0]
    try:
        bot.edit_message_text(f"🎯 <b>Результат:</b>\n\n{result}", m.chat.id, msg.message_id, parse_mode="HTML")
    except:
        bot.send_message(m.chat.id, f"Результат: {result}")

    win = 0
    if (choice == "🔴 Красное" and result == "🔴") or (choice == "⚫ Чёрное" and result == "⚫"):
        win = bet * 2
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        res_text = f"🎉 Победа! +{win} фишек!"
    elif choice == "🟢 Зелёное" and result == "🟢":
        win = bet * 5
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
        res_text = f"💎 Джекпот! +{win} фишек!"
    else:
        get_user(uid)["losses"] = get_user(uid).get("losses",0)+1
        res_text = f"😢 Проигрыш. -{bet} фишек."

    if win:
        change_balance(uid, win)
    save_data()

    bot.send_message(m.chat.id, f"{res_text}\n💰 Баланс: {get_balance(uid)} фишек", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ========== DICE with bet and animation ==========
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def dice_ask_bet(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Введите, сколько фишек хотите поставить (минимум {MIN_BET}):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("🔙 Назад"))
    bot.register_next_step_handler(m, dice_play)

def dice_play(m: types.Message):
    uid = m.from_user.id
    if not m.text or m.text.strip()=="🔙 Назад":
        bot.send_message(m.chat.id, "Отмена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    try:
        bet = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "⚠️ Введите корректное число."); return
    if bet < MIN_BET or bet > MAX_BET:
        bot.send_message(m.chat.id, f"Ставка от {MIN_BET} до {MAX_BET}"); return
    if get_balance(uid) < bet:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек."); return

    change_balance(uid, -bet)
    get_user(uid)["games_played"] = get_user(uid).get("games_played",0)+1
    save_data()

    msg = bot.send_message(m.chat.id, "🎲 <b>Бросаем кости...</b>", parse_mode="HTML")
    for _ in range(3):
        d1, d2 = random.randint(1,6), random.randint(1,6)
        try:
            bot.edit_message_text(f"🎲 <b>Кости крутятся...</b>\n\n[{d1}] + [{d2}]", m.chat.id, msg.message_id, parse_mode="HTML")
        except:
            bot.send_message(m.chat.id, f"[{d1}] + [{d2}]")
        time.sleep(0.6)

    d1, d2 = random.randint(1,6), random.randint(1,6)
    total = d1 + d2
    win = 0
    if total >= 10:
        win = bet * 2
        res = f"🎉 Выпало {d1} + {d2} = {total}. Победа! +{win} фишек!"
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
    elif d1 == 6 and d2 == 6:
        win = bet * 5
        res = f"💎 Дубль шесть! +{win} фишек!"
        get_user(uid)["wins"] = get_user(uid).get("wins",0)+1
    else:
        res = f"😢 Выпало {d1} + {d2} = {total}. Проигрыш."

    if win:
        change_balance(uid, win)
    else:
        get_user(uid)["losses"] = get_user(uid).get("losses",0)+1
    save_data()

    try:
        bot.edit_message_text(f"{res}\n\n💰 Баланс: {get_balance(uid)}", m.chat.id, msg.message_id, parse_mode="HTML")
    except:
        bot.send_message(m.chat.id, f"{res}\n\n💰 Баланс: {get_balance(uid)}", parse_mode="HTML")
    bot.send_message(m.chat.id, "🔙", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ========== HELP ==========
def send_help(m: types.Message):
    txt = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　　ℹ️  П О М О Щ Ь\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        "🎰 Слоты — поставь сумму и крути барабаны\n"
        "🎯 Рулетка — выбери ставку и цвет\n"
        "🎲 Кости — поставь сумму и бросай кости\n"
        "🎁 Бонус — раз в 24 часа (+1000)\n"
        "💸 Перевести — /transfer или кнопка\n"
        "📊 Топ — /top\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆘 Если нужна помощь — пиши @{OWNER_USERNAME}"
    )
    bot.send_message(m.chat.id, txt, parse_mode="HTML", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_button(m: types.Message):
    send_help(m)

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=["admin"])
def admin_panel_cmd(m: types.Message):
    if m.from_user.id not in ADMINS:
        bot.send_message(m.chat.id, "⛔ У тебя нет доступа.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Начислить", "➖ Снять")
    kb.row("🚫 Бан", "✅ Разбан")
    kb.row("❄️ Заморозить", "🔥 Разморозить")
    kb.row("⚠️ Предупредить", "📋 Список")
    kb.row("📢 Рассылка", "🔙 Меню")
    bot.send_message(m.chat.id, "👑 Админ-панель — выберите действие:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.from_user.id in ADMINS and m.text in ["➕ Начислить","➖ Снять","🚫 Бан","✅ Разбан","❄️ Заморозить","🔥 Разморозить","⚠️ Предупредить","📋 Список","📢 Рассылка"])
def admin_actions(m: types.Message):
    cmd = m.text
    uid = m.from_user.id
    if cmd == "➕ Начислить":
        bot.send_message(uid, "Введите: <user_id> <amount>")
        bot.register_next_step_handler(m, admin_add)
    elif cmd == "➖ Снять":
        bot.send_message(uid, "Введите: <user_id> <amount>")
        bot.register_next_step_handler(m, admin_remove)
    elif cmd == "🚫 Бан":
        bot.send_message(uid, "Введите: <user_id>")
        bot.register_next_step_handler(m, admin_ban)
    elif cmd == "✅ Разбан":
        bot.send_message(uid, "Введите: <user_id>")
        bot.register_next_step_handler(m, admin_unban)
    elif cmd == "❄️ Заморозить":
        bot.send_message(uid, "Введите: <user_id>")
        bot.register_next_step_handler(m, admin_freeze)
    elif cmd == "🔥 Разморозить":
        bot.send_message(uid, "Введите: <user_id>")
        bot.register_next_step_handler(m, admin_unfreeze)
    elif cmd == "⚠️ Предупредить":
        bot.send_message(uid, "Введите: <user_id> <причина (необязательно)>")
        bot.register_next_step_handler(m, admin_warn)
    elif cmd == "📋 Список":
        s = []
        for uid_k, info in data["users"].items():
            s.append(f"{uid_k} — {info.get('username','')} — {info.get('balance',0)}")
        bot.send_message(uid, "📋 Пользователи:\n\n" + ("\n".join(s) if s else "Пока нет пользователей"))
    elif cmd == "📢 Рассылка":
        bot.send_message(uid, "Введите текст рассылки:")
        bot.register_next_step_handler(m, admin_broadcast)

def admin_add(m: types.Message):
    try:
        uid_s, amt_s = m.text.split()
        uid_t = int(uid_s); amt = int(amt_s)
        ensure_user(uid_t)
        change_balance(uid_t, amt)
        bot.send_message(m.chat.id, f"✅ Добавлено {amt} фишек пользователю {uid_t}")
    except:
        bot.send_message(m.chat.id, "Неверный формат. Пример: 123456789 500")

def admin_remove(m: types.Message):
    try:
        uid_s, amt_s = m.text.split()
        uid_t = int(uid_s); amt = int(amt_s)
        ensure_user(uid_t)
        if get_balance(uid_t) < amt:
            bot.send_message(m.chat.id, "У пользователя недостаточно фишек.")
            return
        change_balance(uid_t, -amt)
        bot.send_message(m.chat.id, f"✅ Снято {amt} фишек у пользователя {uid_t}")
    except:
        bot.send_message(m.chat.id, "Неверный формат. Пример: 123456789 500")

def admin_ban(m: types.Message):
    try:
        uid_t = int(m.text.strip())
        ensure_user(uid_t)
        set_status(uid_t, banned=True)
        bot.send_message(m.chat.id, f"🚫 Пользователь {uid_t} забанен")
        try: bot.send_message(uid_t, "🚫 Вы были забанены администратором.")
        except: pass
    except:
        bot.send_message(m.chat.id, "Неверный ID")

def admin_unban(m: types.Message):
    try:
        uid_t = int(m.text.strip())
        ensure_user(uid_t)
        set_status(uid_t, banned=False)
        bot.send_message(m.chat.id, f"✅ {uid_t} разбанен")
    except:
        bot.send_message(m.chat.id, "Неверный ID")

def admin_freeze(m: types.Message):
    try:
        uid_t = int(m.text.strip())
        ensure_user(uid_t)
        set_status(uid_t, frozen=True)
        bot.send_message(m.chat.id, f"❄️ {uid_t} заморожен")
    except:
        bot.send_message(m.chat.id, "Неверный ID")

def admin_unfreeze(m: types.Message):
    try:
        uid_t = int(m.text.strip())
        ensure_user(uid_t)
        set_status(uid_t, frozen=False)
        bot.send_message(m.chat.id, f"🔥 {uid_t} разморожен")
    except:
        bot.send_message(m.chat.id, "Неверный ID")

def admin_warn(m: types.Message):
    parts = m.text.split(maxsplit=1)
    try:
        uid_t = int(parts[0])
    except:
        bot.send_message(m.chat.id, "Неверный ID")
        return
    reason = parts[1] if len(parts) > 1 else None
    w = add_warn(uid_t, reason)
    bot.send_message(m.chat.id, f"⚠️ Пользователь {uid_t} предупреждён (предупреждений: {w})")
    try:
        bot.send_message(uid_t, f"⚠️ Вы получили предупреждение. Причина: {reason or 'не указана'}. Всего предупреждений: {w}")
    except: pass

def admin_broadcast(m: types.Message):
    text = m.text
    count = 0
    for uid_k in list(data["users"].keys()):
        try:
            bot.send_message(int(uid_k), f"📢 Сообщение от администрации:\n\n{text}")
            count += 1
        except:
            pass
    bot.send_message(m.chat.id, f"✅ Рассылка завершена ({count} пользователей).")

# ========== WELCOME NEW MEMBERS IN GROUPS ==========
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(m: types.Message):
    for u in m.new_chat_members:
        name = f"@{u.username}" if getattr(u,"username",None) else (u.first_name or str(u.id))
        # give starter balance when they run /start in PM; here just announce
        text = (
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
            "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
            f"👋 Привет, {name}!\n"
            "Ты попал в легендарное казино удачи 💫\n\n"
            "🎁 Напомни: напишите /start боту в личку, чтобы получить стартовые фишки.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "　　　Желаем удачи в игре! 🍀"
        )
        try:
            bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=group_main_inline())
        except:
            pass

# ========== STARTUP ==========
if __name__ == "__main__":
    load_data()
    print("🎰 Casino Ruta Final запущен! Listening...")
    try:
        bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception:
        logger.exception("Polling failed, exiting.")
