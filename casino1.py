#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Casino Ruta Final — полный рабочий бот (виртуальные фишки)
Требует: pyTelegramBotAPI
Перед запуском: pip install pyTelegramBotAPI
Вставь токен от BotFather в TOKEN.
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, Optional, Tuple

import telebot
from telebot import types

# Проверяем, есть ли ключ "users" в данных, если нет — создаем
	if "users" not in data:
    data["users"] = {}

# ---------- CONFIG ----------
TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"   # <-- вставь сюда токен
ADMIN_ID = 718853742        # <-- твой ID администратора (указан тобой)

DATA_FILE = "casino_data.json"
BACKUP_FILE = "casino_data_backup.json"

MIN_BET = 100
MAX_BET = 50000
DAILY_BONUS = 1000
BONUS_SECONDS = 86400  # 24 часа

SLOT_SYMBOLS = ["🍒","🍋","🍇","🍉","💎","7️⃣","🍀","⭐"]
SLOT_JACK_MULT = 5
SLOT_PAIR_MULT = 2

ROULETTE_CHANCE = 0.30
ROULETTE_MULT = 3

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("casino_ruta_final")

# ---------- BOT ----------
if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
    print("ERROR: вставь токен в переменную TOKEN в файле casino_ruta_final.py")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ---------- DATA ----------
data: Dict[str, Any] = {"users": {}, "meta": {"created": time.time()}}

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded data from %s", DATA_FILE)
        except Exception as e:
            logger.exception("Failed to load data: %s", e)
            # try backup
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                        logger.info("Loaded data from backup")
                except Exception:
                    data = {"users": {}, "meta": {"created": time.time()}}
            else:
                data = {"users": {}, "meta": {"created": time.time()}}
    else:
        data = {"users": {}, "meta": {"created": time.time()}}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=2)
        logger.info("Data saved")
    except Exception:
        logger.exception("Failed to save data")

# ---------- HELPERS ----------
def ensure_user(uid: int):
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
            "name": ""
        }
        save_data()

def get_user(uid: int) -> Dict[str, Any]:
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

def set_status(uid: int, banned: Optional[bool]=None, frozen: Optional[bool]=None):
    u = get_user(uid)
    if banned is not None:
        u["banned"] = bool(banned)
    if frozen is not None:
        u["frozen"] = bool(frozen)
    save_data()

def can_play(uid: int) -> Tuple[bool, Optional[str]]:
    u = get_user(uid)
    if u.get("banned"):
        return False, "🚫 Вы забанены."
    if u.get("frozen"):
        return False, "❄️ Ваш аккаунт заморожен."
    return True, None

def nice_name(user: types.User) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)

# ---------- KEYBOARDS ----------
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

def inline_bet_buttons(prefix: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("💵 100", callback_data=f"{prefix}_bet_100"),
           types.InlineKeyboardButton("💰 500", callback_data=f"{prefix}_bet_500"),
           types.InlineKeyboardButton("💎 1000", callback_data=f"{prefix}_bet_1000"))
    kb.row(types.InlineKeyboardButton("🔙 Меню", callback_data="menu_back"))
    return kb

def admin_keyboard_inline():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("➕ Начислить", callback_data="adm_add"),
           types.InlineKeyboardButton("➖ Снять", callback_data="adm_remove"))
    kb.row(types.InlineKeyboardButton("🚫 Бан", callback_data="adm_ban"),
           types.InlineKeyboardButton("✅ Разбан", callback_data="adm_unban"))
    kb.row(types.InlineKeyboardButton("❄️ Заморозить", callback_data="adm_freeze"),
           types.InlineKeyboardButton("🔥 Разморозить", callback_data="adm_unfreeze"))
    kb.row(types.InlineKeyboardButton("♻ Обнулить", callback_data="adm_reset"),
           types.InlineKeyboardButton("📁 Экспорт", callback_data="adm_export"))
    kb.row(types.InlineKeyboardButton("🔙 Меню", callback_data="menu_back"))
    return kb

# ---------- UTIL ----------
def format_top(n=10) -> str:
    items = [(int(k), v["balance"], v.get("name") or "") for k, v in data["users"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    lines = []
    for i, (uid, bal, name) in enumerate(items[:n], start=1):
        if name:
            lines.append(f"{i}. {name} (`{uid}`) — {bal} фишек")
        else:
            lines.append(f"{i}. `{uid}` — {bal} фишек")
    return "\n".join(lines) if lines else "Пока нет игроков."

def render_header(name: str, balance: int) -> str:
    # ровное оформление приветствия
    bal_str = f"{balance:,}".replace(",", " ")
    header = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        f"👋 Привет, {name}!\n"
        "Добро пожаловать в роскошное казино удачи 💫\n\n"
        f"💰 Твой баланс: {bal_str} фишек\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "　　　Выбери игру ниже ⬇️\n\n"
        "🆘 Нужна помощь? Обратись к 👉 @ownerrut"
    )
    return header

# ---------- HANDLERS: START / HELP / BALANCE / TOP / BONUS ----------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    data["users"][str(uid)]["name"] = nice_name(m.from_user)
    save_data()
    name = nice_name(m.from_user)
    text = render_header(name, get_balance(uid))
    if m.chat.type == "private":
        bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=private_main_keyboard())
    else:
        bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=group_main_inline())

@bot.message_handler(commands=["help"])
def cmd_help(m: types.Message):
    send_help(m)

@bot.message_handler(commands=["balance"])
def cmd_balance(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    text = f"💰 Твой баланс: {get_balance(uid)} фишек"
    if m.chat.type == "private":
        bot.send_message(m.chat.id, text, reply_markup=private_main_keyboard())
    else:
        bot.send_message(m.chat.id, text, reply_markup=group_main_inline())

@bot.message_handler(commands=["top"])
def cmd_top(m: types.Message):
    txt = "📊 Топ игроков:\n\n" + format_top(10)
    if m.chat.type == "private":
        bot.send_message(m.chat.id, txt, parse_mode="Markdown", reply_markup=private_main_keyboard())
    else:
        bot.send_message(m.chat.id, txt, parse_mode="Markdown", reply_markup=group_main_inline())

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

# ---------- TRANSFER ----------
@bot.message_handler(commands=["transfer"])
def cmd_transfer(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    parts = m.text.split()
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        target = int(parts[1]); amount = int(parts[2])
        if amount < MIN_BET:
            bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек"); return
        if get_balance(uid) < amount:
            bot.send_message(m.chat.id, "❌ Недостаточно фишек"); return
        ensure_user(target)
        change_balance(uid, -amount)
        change_balance(target, amount)
        bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        try:
            bot.send_message(target, f"💸 Тебе перевели {amount} фишек от {nice_name(m.from_user)}")
        except: pass
        return
    # interactive path
    bot.send_message(m.chat.id, "🔁 Введи ID получателя:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(m, transfer_step1)

def transfer_step1(m: types.Message):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Неверный ID. Операция отменена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    target = int(m.text)
    msg = bot.send_message(m.chat.id, "💰 Введи сумму:")
    bot.register_next_step_handler(msg, transfer_step2, target)

def transfer_step2(m: types.Message, target:int):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Неверная сумма. Операция отменена.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    amount = int(m.text)
    uid = m.from_user.id
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    ensure_user(target)
    change_balance(uid, -amount)
    change_balance(target, amount)
    bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
    try:
        bot.send_message(target, f"💸 Тебе перевели {amount} фишек от {nice_name(m.from_user)}")
    except: pass

# ---------- SLOTS ----------
def spin_slots(chat_id:int, uid:int, amount:int, edit_message_id:Optional[int]=None):
    change_balance(uid, -amount)
    total_frames = 4
    last = None
    if edit_message_id:
        try:
            bot.edit_message_text("🎰 Крутим барабаны...", chat_id, edit_message_id)
            msg_id = edit_message_id
        except:
            m = bot.send_message(chat_id, "🎰 Крутим барабаны...")
            msg_id = m.message_id
    else:
        m = bot.send_message(chat_id, "🎰 Крутим барабаны...")
        msg_id = m.message_id

    for _ in range(total_frames):
        s1 = random.choice(SLOT_SYMBOLS)
        s2 = random.choice(SLOT_SYMBOLS)
        s3 = random.choice(SLOT_SYMBOLS)
        last = (s1,s2,s3)
        frame = f"🎰 | {s1} | {s2} | {s3} |"
        try:
            bot.edit_message_text(frame, chat_id, msg_id)
        except:
            try:
                bot.send_message(chat_id, frame)
            except:
                pass
        time.sleep(0.8)

    s1,s2,s3 = last
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    if s1==s2==s3:
        win = amount * SLOT_JACK_MULT
        change_balance(uid, win)
        u["wins"] += 1
        result = f"💎 Джекпот! +{win} фишек!"
    elif s1==s2 or s2==s3 or s1==s3:
        win = amount * SLOT_PAIR_MULT
        change_balance(uid, win)
        u["wins"] += 1
        result = f"⭐ 2 совпали! +{win} фишек!"
    else:
        u["losses"] = u.get("losses",0)+1
        result = f"💀 Проигрыш. -{amount} фишек."
    final = f"🎰 | {s1} | {s2} | {s3} |\n\n{result}\n\n💰 Баланс: {get_balance(uid)}"
    try:
        bot.edit_message_text(final, chat_id, msg_id, reply_markup=private_main_keyboard() if get_chat_type_by_id(chat_id)=="private" else group_main_inline())
    except:
        bot.send_message(chat_id, final, reply_markup=private_main_keyboard() if get_chat_type_by_id(chat_id)=="private" else group_main_inline())
    save_data()

# helper to detect chat type by id (best-effort)
def get_chat_type_by_id(chat_id: int) -> str:
    # fallback: assume private for simplicity
    return "private"

@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def handler_slots_btn(m: types.Message):
    if m.chat.type == "private":
        kb = inline_bet_buttons("slot")
        bot.send_message(m.chat.id, "Выберите ставку для слотов (или /bet slots <сумма>):", reply_markup=kb)
    else:
        bot.send_message(m.chat.id, "Сделай ставку (нажми кнопку):", reply_markup=inline_bet_buttons("slot"))

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("slot_bet_"))
def on_slot_bet(call: types.CallbackQuery):
    uid = call.from_user.id
    ensure_user(uid)
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка от {MIN_BET} до {MAX_BET}", show_alert=True); return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек", show_alert=True); return
    bot.answer_callback_query(call.id)
    try:
        spin_slots(call.message.chat.id, uid, amount, edit_message_id=call.message.message_id)
    except Exception:
        spin_slots(call.message.chat.id, uid, amount)

# ---------- ROULETTE with animation ----------
@bot.message_handler(func=lambda m: m.text == "🎯 Рулетка")
def handler_roul_btn(m: types.Message):
    if m.chat.type == "private":
        # show amount buttons then color choose in callback
        kb = inline_bet_buttons("roul")
        bot.send_message(m.chat.id, "Выберите ставку для рулетки (или /bet roul <сумма>):", reply_markup=kb)
    else:
        bot.send_message(m.chat.id, "Рулетка — выбери ставку:", reply_markup=inline_bet_buttons("roul"))

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("roul_bet_"))
def on_roul_bet(call: types.CallbackQuery):
    uid = call.from_user.id
    ensure_user(uid)
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка от {MIN_BET} до {MAX_BET}", show_alert=True); return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек", show_alert=True); return
    # Ask for color selection
    bot.answer_callback_query(call.id)
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🔴 Красное (x2)", callback_data=f"roul_choice_{amount}_red"),
           types.InlineKeyboardButton("⚫ Чёрное (x2)", callback_data=f"roul_choice_{amount}_black"))
    kb.row(types.InlineKeyboardButton("🟢 Зелёное (x5)", callback_data=f"roul_choice_{amount}_green"))
    kb.row(types.InlineKeyboardButton("🔙 Меню", callback_data="menu_back"))
    try:
        bot.edit_message_text(f"🎯 Выберите цвет. Ставка: {amount} фишек\n💰 Баланс: {get_balance(uid)}", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, f"🎯 Выберите цвет. Ставка: {amount} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("roul_choice_"))
def on_roul_choice(call: types.CallbackQuery):
    # format: roul_choice_<amount>_<color>
    try:
        _, rest = call.data.split("roul_choice_",1)
        amount_str, color = rest.rsplit("_",1)
        amount = int(amount_str)
    except Exception:
        bot.answer_callback_query(call.id, "Ошибка данных", show_alert=True); return
    uid = call.from_user.id
    ensure_user(uid)
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек", show_alert=True); return
    bot.answer_callback_query(call.id)
    # Deduct upfront for animation
    change_balance(uid, -amount)
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    save_data()
    # animate: series of frames then result
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    try:
        bot.edit_message_text("🎯 Крутим рулетку...", chat_id, msg_id)
    except:
        bot.send_message(chat_id, "🎯 Крутим рулетку...")
        msg_id = None
    wheel_symbols = ["🔴","⚫","⚫","🔴","🔴","⚫","🟢"]  # bias green rarer
    frames = []
    for _ in range(3):
        random.shuffle(wheel_symbols)
        frames.append(" ".join(random.choices(wheel_symbols, k=6)))
    # show frames
    for frame in frames:
        try:
            if msg_id:
                bot.edit_message_text("🎯 Крутим рулетку...\n\n" + frame, chat_id, msg_id)
            else:
                bot.send_message(chat_id, "🎯 Крутим рулетку...\n\n" + frame)
        except:
            pass
        time.sleep(0.8)
    # final pick
    result_symbol = random.choices(["red","black","green"], weights=[45,45,10])[0]
    # evaluate
    won = 0
    payout = 0
    if (color == "red" and result_symbol=="red") or (color=="black" and result_symbol=="black"):
        payout = amount * 2
        won = payout
        change_balance(uid, payout)
        u["wins"] += 1
        res_text = f"🎉 Выпало {result_symbol.upper()}! Ты выиграл {payout} фишек!"
    elif color=="green" and result_symbol=="green":
        payout = amount * 5
        won = payout
        change_balance(uid, payout)
        u["wins"] += 1
        res_text = f"🎉 Выпало ЗЕЛЁНОЕ! Ты выиграл {payout} фишек!"
    else:
        u["losses"] = u.get("losses",0)+1
        res_text = f"🔻 Выпало {result_symbol.upper()}. Ты проиграл {amount} фишек."
    save_data()
    final = f"🎯 Результат:\n\n{res_text}\n\n💰 Баланс: {get_balance(uid)}"
    try:
        if msg_id:
          bot.edit_message_text(final, chat_id, msg_id, reply_markup=private_main_keyboard() if call.message.chat.type=="private" else group_main_inline())
        else:
            bot.send_message(chat_id, final, reply_markup=private_main_keyboard() if call.message.chat.type=="private" else group_main_inline())
    except:
        bot.send_message(chat_id, final, reply_markup=private_main_keyboard() if call.message.chat.type=="private" else group_main_inline())

# ---------- DICE ----------
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def handler_dice_btn(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    roll = random.randint(1,6)
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    bot.send_message(m.chat.id, f"🎲 {nice_name(m.from_user)} бросил кости — выпало: {roll}", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
    save_data()

# ---------- /bet command ----------
@bot.message_handler(commands=["bet"])
def cmd_bet(m: types.Message):
    parts = m.text.split()
    if len(parts) < 3:
        bot.send_message(m.chat.id, "Использование: /bet <game> <amount>\nПримеры: /bet slots 500  /bet roul 1000 /bet dice 300", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        return
    game = parts[1].lower()
    if not parts[2].lstrip('-').isdigit():
        bot.send_message(m.chat.id, "Сумма должна быть числом.", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    amount = int(parts[2])
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    if amount < MIN_BET or amount > MAX_BET:
        bot.send_message(m.chat.id, f"Ставка от {MIN_BET} до {MAX_BET}", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "Недостаточно фишек", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline()); return

    if game in ("slots","slot"):
        try:
            spin_slots(m.chat.id, uid, amount)
        except Exception:
            bot.send_message(m.chat.id, "Ошибка при игре в слоты.")
    elif game in ("roul","roulette","roulett","rou"):
        # simulate roulette as if user pressed amount -> then color will be prompted via callback in private mode
        if m.chat.type == "private":
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("🔴 Красное (x2)", callback_data=f"roul_choice_{amount}_red"),
                   types.InlineKeyboardButton("⚫ Чёрное (x2)", callback_data=f"roul_choice_{amount}_black"))
            kb.row(types.InlineKeyboardButton("🟢 Зелёное (x5)", callback_data=f"roul_choice_{amount}_green"))
            bot.send_message(m.chat.id, f"🎯 Выберите цвет. Ставка: {amount} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=kb)
        else:
            # group: just behave like callback flow by sending inline color buttons
            bot.send_message(m.chat.id, f"{nice_name(m.from_user)} предлагает ставку {amount} фишек — выберите цвет:", reply_markup=types.InlineKeyboardMarkup().row(
                types.InlineKeyboardButton("🔴 Красное (x2)", callback_data=f"roul_choice_{amount}_red"),
                types.InlineKeyboardButton("⚫ Чёрное (x2)", callback_data=f"roul_choice_{amount}_black")
            ))
    elif game in ("dice","die"):
        change_balance(uid, -amount)
        roll = random.randint(1,6)
        u = get_user(uid)
        u["games_played"] = u.get("games_played",0)+1
        if roll >= 4:
            win = amount * 2
            change_balance(uid, win)
            u["wins"] += 1
            bot.send_message(m.chat.id, f"🎲 Выпало {roll}. Победа! +{win} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        else:
            u["losses"] = u.get("losses",0)+1
            bot.send_message(m.chat.id, f"🎲 Выпало {roll}. Проигрыш. -{amount} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())
        save_data()
    else:
        bot.send_message(m.chat.id, "Неизвестная игра. Доступные: slots, roul, dice", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ---------- SIMPLE REPLY-BUTTON HANDLERS (private) ----------
@bot.message_handler(func=lambda m: m.chat.type=="private" and m.text == "💰 Баланс")
def btn_balance_private(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек", reply_markup=private_main_keyboard())

@bot.message_handler(func=lambda m: m.chat.type=="private" and m.text == "🎁 Бонус")
def btn_bonus_private(m: types.Message):
    cmd_bonus(m)

@bot.message_handler(func=lambda m: m.chat.type=="private" and m.text == "📊 Топ")
def btn_top_private(m: types.Message):
    cmd_top(m)

@bot.message_handler(func=lambda m: m.chat.type=="private" and m.text == "💸 Перевести")
def btn_transfer_private(m: types.Message):
    cmd_transfer(m)

@bot.message_handler(func=lambda m: m.chat.type=="private" and m.text == "ℹ️ Помощь")
def btn_help_private(m: types.Message):
    send_help(m)

# ---------- GROUP INLINE CALLBACKS ----------
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("g_"))
def on_group_callback(c: types.CallbackQuery):
    data_cmd = c.data.split("_", 1)[1]
    uid = c.from_user.id
    ensure_user(uid)
    if data_cmd == "slots":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, f"{nice_name(c.from_user)} хочет сыграть: выберите сумму", reply_markup=inline_bet_buttons("slot"))
    elif data_cmd == "roul":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, f"{nice_name(c.from_user)} запускает рулетку — выберите ставку:", reply_markup=inline_bet_buttons("roul"))
    elif data_cmd == "dice":
        bot.answer_callback_query(c.id)
        roll = random.randint(1,6)
        u = get_user(uid); u["games_played"] = u.get("games_played",0)+1; save_data()
        bot.send_message(c.message.chat.id, f"🎲 {nice_name(c.from_user)} бросил кости — выпало {roll}", reply_markup=group_main_inline())
    elif data_cmd == "bonus":
        bot.answer_callback_query(c.id)
        cmd_bonus(c.message)
    elif data_cmd == "balance":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, f"💰 {nice_name(c.from_user)} — {get_balance(uid)} фишек", reply_markup=group_main_inline())
    elif data_cmd == "top":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, "📊 Топ игроков:\n\n" + format_top(10), parse_mode="Markdown", reply_markup=group_main_inline())
    elif data_cmd == "transfer":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, "Для перевода используй команду в личке: /transfer <id> <amount>", reply_markup=group_main_inline())
    elif data_cmd == "help":
        bot.answer_callback_query(c.id)
        send_help(c.message)
    else:
        bot.answer_callback_query(c.id, "Неизвестная команда", show_alert=True)

# ---------- HELP ----------
def send_help(m: types.Message):
    txt = (
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
        "　　　　ℹ️  П О М О Щ Ь\n"
        "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
        "🎰 Слоты — кнопками (100/500/1000) или /bet slots <сумма>\n"
        "🎯 Рулетка — шанс ~30%, выигрыш ×3. Кнопки или /bet roul <сумма>\n"
        "🎲 Кости — /bet dice <сумма> или просто нажми кнопку\n"
        "🎁 Бонус — ежедневные +1000 фишек (/bonus)\n"
        "💸 Перевести — /transfer <id> <amount>\n"
        "📊 Топ — /top\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🆘 Нужна помощь? Обратись к 👉 @ownerrut"
    )
    bot.send_message(m.chat.id, txt, parse_mode="HTML", reply_markup=private_main_keyboard() if m.chat.type=="private" else group_main_inline())

# ---------- ADMIN ----------
@bot.message_handler(commands=["admin"])
def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    kb = admin_keyboard_inline()
    bot.send_message(m.chat.id, "👑 Админ-панель", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_"))
def admin_cb(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True); return
    action = call.data.split("_",1)[1]
    bot.answer_callback_query(call.id)
    if action in ("add","remove"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id> <amount>")
        bot.register_next_step_handler(msg, admin_add_remove, action)
    elif action in ("ban","unban","freeze","unfreeze","reset"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id>")
        bot.register_next_step_handler(msg, admin_status_action, action)
    elif action == "export":
        save_data()
        try:
            bot.send_document(call.message.chat.id, open(DATA_FILE, "rb"))
        except Exception:
            bot.send_message(call.message.chat.id, "Ошибка экспорта данных.")

def admin_add_remove(m: types.Message, action: str):
    if m.from_user.id != ADMIN_ID: return
    parts = m.text.strip().split()
    if len(parts)!=2 or not parts[0].lstrip('-').isdigit() or not parts[1].lstrip('-').isdigit():
        bot.send_message(m.chat.id, "Неверный формат. Используй: <user_id> <amount>"); return
    target = int(parts[0]); amount = int(parts[1])
    ensure_user(target)
    if action=="add":
        change_balance(target, amount)
        bot.send_message(m.chat.id, f"✅ Добавлено {amount} фишек пользователю {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ начислил вам {amount} фишек.")
        except: pass
    else:
        if get_balance(target) < amount:
            bot.send_message(m.chat.id, "У пользователя недостаточно фишек."); return
        change_balance(target, -amount)
        bot.send_message(m.chat.id, f"✅ Снято {amount} фишек у пользователя {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ снял {amount} фишек с вашего баланса.")
        except: pass

def admin_status_action(m: types.Message, action: str):
    if m.from_user.id != ADMIN_ID: return
    if not m.text.strip().lstrip('-').isdigit():
        bot.send_message(m.chat.id, "Неверный формат. Введи ID"); return
    target = int(m.text.strip())
    ensure_user(target)
    if action=="ban":
        set_status(target, banned=True)
        bot.send_message(m.chat.id, f"🚫 {target} забанен")
        try: bot.send_message(target, "🚫 Вы были забанены администратором.")
        except: pass
    elif action=="unban":
        set_status(target, banned=False)
        bot.send_message(m.chat.id, f"✅ {target} разбанен")
        try: bot.send_message(target, "✅ Вас разбанил администратор.")
        except: pass
    elif action=="freeze":
        set_status(target, frozen=True)
        bot.send_message(m.chat.id, f"❄️ {target} заморожен")
        try: bot.send_message(target, "❄️ Ваш аккаунт временно заморожен администратором.")
        except: pass
    elif action=="unfreeze":
        set_status(target, frozen=False)
        bot.send_message(m.chat.id, f"🔥 {target} разморожен")
        try: bot.send_message(target, "🔥 Ваш аккаунт разморожен администратором.")
        except: pass
    elif action=="reset":
        set_balance(target, 1000)
        bot.send_message(m.chat.id, f"♻ {target} обнулён. Новый баланс: 1000 фишек")
        try: bot.send_message(target, "♻ Ваш баланс был сброшен администратором до 1000 фишек.")
        except: pass

# ---------- WELCOME NEW MEMBERS IN GROUPS ----------
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(m: types.Message):
    for u in m.new_chat_members:
        name = f"@{u.username}" if getattr(u, "username", None) else (u.first_name or str(u.id))
        text = (
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n"
            "　　　🎰 ＣＡＳＩＮＯ ＲＵＴＡ 🎲\n"
            "💎━━━━━━━━━━━━━━━━━━━━━━💎\n\n"
            f"👋 Привет, {name}!\n"
            "Добро пожаловать в наше казино удачи 💫\n\n"
            "💰 Начальный баланс: 1 000 фишек\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "　　　Выбери игру ниже ⬇️\n\n"
            "🆘 Нужна помощь? Обратись к 👉 @ownerrut"
        )
        bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=group_main_inline())

# ---------- STARTUP ----------
if __name__ == "__main__":
    load_data()
    print("🎰 Casino Ruta Final запущен!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception:
        logger.exception("Polling failed, exiting.")

