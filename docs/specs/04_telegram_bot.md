---

APEX TELEGRAM SUBSYSTEM BLUEPRINT

Part 01

Vision, Architecture Philosophy, Global Requirements and Design Principles

Version : 1.0 Production Blueprint

Project : APEX Institutional Crypto Trading Platform

Subsystem : Telegram Interface Backtest Paper Trading Live Trading Portfolio Administration Optimization Integration


---

1. Purpose

هدف این زیرسیستم، تبدیل ربات تلگرام به کنسول عملیاتی اصلی پروژه APEX است.

تلگرام نباید تنها یک پیام‌رسان یا نمایش‌دهنده سیگنال باشد.

بلکه باید نقش موارد زیر را ایفا کند:

Trading Terminal

Monitoring Dashboard

Portfolio Console

Optimization Controller

Risk Management Console

Administrative Panel

Notification Center

Research Gateway


به عبارت دیگر، پس از راه‌اندازی پروژه، تقریباً تمام عملیات روزمره باید بدون نیاز به ترمینال Termux و تنها از طریق تلگرام قابل انجام باشد؛ به‌جز عملیات توسعه نرم‌افزار.


---

2. Design Philosophy

طراحی کل سیستم باید بر اساس اصول زیر انجام شود.

Principle 1

Telegram is NOT Messenger

Telegram IS Control Center.


---

Principle 2

Every Action must be reversible.

تمام عملیات دارای گزینه Back باشند.

هیچ بن‌بستی در Navigation وجود نداشته باشد.


---

Principle 3

No Dangerous Action without Confirmation

تمام عملیات حساس نیازمند تأیید دو مرحله‌ای هستند.

مثال:

Start Live Trading

↓

Confirmation

↓

Execute


---

Principle 4

Admin First

تمام قابلیت‌ها ابتدا برای Admin طراحی شوند.

سپس مشخص شود کدام قسمت برای کاربران عادی قابل مشاهده است.


---

Principle 5

Maximum Visibility

هر اتفاق مهم باید قابل مشاهده باشد.

مثلاً:

Order Created

↓

Order Filled

↓

SL Updated

↓

TP Modified

↓

Position Closed

↓

Portfolio Updated

↓

Notification Sent


---

Principle 6

Everything should be Observable.

هیچ ماژولی نباید Hidden باشد.

حتی Optimizer نیز باید وضعیت خود را نمایش دهد.


---

Principle 7

Minimal Typing

کاربر تا حد امکان نباید چیزی تایپ کند.

تقریباً همه عملیات توسط:

Inline Keyboard

انجام می‌شوند.


---

Principle 8

State Driven

هیچ منویی مستقل نیست.

تمام منوها دارای State هستند.

به عنوان مثال:

MAIN

↓

Trading

↓

Live

↓

BTC

↓

1H

↓

Position

↓

Modify TP

↓

Confirm

↓

Done

↓

Back


---

3. Global Architecture

کل زیرسیستم تلگرام به هشت زیرسیستم اصلی تقسیم می‌شود:

Telegram

│

├── Navigation Engine

├── Session Manager

├── Permission Engine

├── Trading Controller

├── Backtest Controller

├── Optimization Controller

├── Portfolio Controller

└── Notification Engine

هیچ کدام از این ماژول‌ها نباید مستقیماً منطق معاملاتی را پیاده‌سازی کنند؛ آن‌ها تنها درخواست را به موتورهای موجود پروژه ارسال می‌کنند.


---

4. Separation of Responsibilities

Bot.py مسئول هیچ منطق معاملاتی نیست.

Bot.py فقط مسئول:

دریافت پیام

دریافت Callback

مدیریت Session

مدیریت Keyboard

فراخوانی Controller مناسب

ارسال پاسخ


است.

تمام منطق در Controllerها قرار می‌گیرد.


---

5. Telegram Folder Architecture

ساختار پیشنهادی:

telegram/

bot.py

handlers.py

navigation.py

permissions.py

sessions.py

callbacks.py

notifications.py

menus/

main.py

trading.py

backtest.py

optimization.py

portfolio.py

reports.py

settings.py

admin.py

controllers/

trading_controller.py

backtest_controller.py

optimization_controller.py

portfolio_controller.py

admin_controller.py

formatters/

signal_formatter.py

backtest_formatter.py

optimization_formatter.py

portfolio_formatter.py

chart_formatter.py

utils/

keyboard_builder.py

message_builder.py

pagination.py

state_machine.py

این ساختار باعث جداسازی کامل رابط کاربری از منطق سیستم می‌شود.


---

6. Navigation Rules

تمام صفحات باید دارای گزینه بازگشت باشند.

↩ Back

تمام صفحات اصلی باید دارای:

🏠 Main Menu

باشند.

هیچ صفحه‌ای نباید کاربر را مجبور به استفاده از دستور /start برای بازگشت کند.


---

7. Navigation Stack

هر Session دارای Stack مستقل است.

مثال:

Main

↓

Trading

↓

Live

↓

BTC

↓

1H

↓

Position

↓

Modify TP

اگر کاربر Back بزند:

Position

دوباره Back:

1H

دوباره Back:

BTC

این Stack باید برای هر کاربر به‌صورت مستقل نگهداری شود تا چند کاربر هم‌زمان بدون تداخل بتوانند از ربات استفاده کنند.


---

8. User Types

تنها دو سطح دسترسی تعریف می‌شود:

Public User

فقط قابلیت مشاهده و استفاده از امکانات غیرحساس.

Administrator

دسترسی کامل به تمامی بخش‌های پروژه.

در آینده، در صورت نیاز، می‌توان نقش‌های بیشتری مانند Operator یا Analyst اضافه کرد، اما نسخه فعلی فقط همین دو نقش را پیاده‌سازی می‌کند تا سادگی و امنیت حفظ شود.


---

9. Trading Philosophy

پروژه سه حالت عملیاتی خواهد داشت:

Paper Trading

↓

Live Trading

↓

Backtest

هر حالت کاملاً مستقل است و نباید داده یا وضعیت خود را با دیگری مخلوط کند.


---

10. Symbol Philosophy

کل پروژه فقط روی ۱۰ نماد منتخب کار می‌کند.

تمام منوها، گزارش‌ها، اعلان‌ها و فرآیندهای معاملاتی باید بر همین مجموعه استاندارد بنا شوند و انتخاب نماد از همین فهرست انجام شود.


---

11. Timeframe Philosophy

تمام بخش‌ها از مجموعه ثابت ۱۴ تایم‌فریم پشتیبانی می‌کنند:

1m
3m
5m
15m
30m
1h
2h
4h
6h
8h
12h
1d
1w
1M

هیچ بخشی نباید مجموعه متفاوتی از تایم‌فریم‌ها ارائه دهد تا تجربه کاربری یکپارچه باقی بماند.


---

End of Part 01

در Part 02 معماری داخلی Telegram Subsystem، شامل State Machine، Session Manager، Event Flow، Callback Architecture، Controller Layer، Message Lifecycle و ساختار ارتباط با موتورهای پروژه به‌صورت کاملاً مهندسی و با جزئیات طراحی خواهد شد.

APEX TELEGRAM SUBSYSTEM BLUEPRINT

Part 02

Telegram Internal Architecture, Session Manager, State Machine, Event Flow & Controller Layer

Version: 1.0 Production Blueprint


---

1. Objective

هدف این بخش، تعریف معماری داخلی زیرسیستم Telegram است به گونه‌ای که:

کاملاً Stateless از دید Telegram باشد.

کاملاً Stateful از دید APEX باشد.

چندین کاربر بتوانند همزمان بدون تداخل از ربات استفاده کنند.

هیچ Callback یا Message مستقیماً وارد موتورهای معاملاتی نشود.

تمام ارتباطات از طریق Controller Layer انجام شوند.



---

2. High-Level Architecture

Telegram Server
                       │
                       │
                Update / Callback
                       │
                       ▼
                 Telegram Bot
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
 SessionManager   PermissionEngine   CallbackRouter
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 Navigation Engine
                       │
                       ▼
               Controller Dispatcher
                       │
 ┌──────────┬──────────┼──────────┬──────────┐
 ▼          ▼          ▼          ▼          ▼
Trading  Backtest  Portfolio  Reports  Optimization
Controller Controller Controller Controller Controller
                       │
                       ▼
                 Application Layer
                       │
                       ▼
            Existing Project Engines


---

3. Design Rules

هیچ Callback نباید مستقیماً:

BacktestEngine

ExecutionEngine

PortfolioEngine

RiskEngine

Optimizer


را فراخوانی کند.

تمام درخواست‌ها ابتدا وارد Controller متناظر می‌شوند.


---

4. Telegram Bot Responsibilities

Bot.py فقط مسئول موارد زیر است:

Receive Update

↓

Parse Update

↓

Create Session

↓

Validate User

↓

Forward Request

↓

Return Response

موارد زیر ممنوع هستند:

محاسبه سیگنال

ارسال سفارش

محاسبه ریسک

بک‌تست

دسترسی مستقیم به دیتابیس

پردازش مالی



---

5. Session Manager

برای هر کاربر یک Session مستقل نگهداری می‌شود.

Session

UserID

Current Menu

Navigation Stack

Selected Symbol

Selected Timeframe

Trading Mode

Pending Action

Last Message ID

Pagination State

Temporary Data

Timeout

نمونه:

Session

user_id = 123456

current_menu = LIVE

symbol = BTC

timeframe = 1h

mode = PAPER

pending_action = MODIFY_SL

stack =

Main

Trading

Paper

BTC

1H

Position


---

6. Session Lifetime

هر Session دارای Timeout است.

پیشنهاد:

20 minutes

اگر کاربر در این مدت فعالیتی نداشته باشد:

Session Reset

ولی تنظیمات دائمی مانند:

زبان

نقش

تنظیمات نمایش


باقی می‌مانند.


---

7. Session Storage

برای نسخه فعلی:

Memory

کافی است.

برای نسخه Enterprise:

Redis

پیشنهاد می‌شود.

مزایا:

Multi Instance

High Availability

Crash Recovery

Fast Lookup



---

8. Navigation Stack

هر ورود به منوی جدید:

push(menu)

هر Back:

pop()

اگر Stack خالی باشد:

Main Menu

نمایش داده می‌شود.


---

9. Navigation Example

Main

↓

Trading

↓

Paper

↓

BTC

↓

4H

↓

Signals

↓

Signal Details

↓

Chart

Back

↓

Signal Details

↓

Signals

↓

4H

↓

BTC

↓

Paper

↓

Trading

↓

Main


---

10. Callback Routing

هیچ Callback نباید بیش از یک مسئول داشته باشد.

ساختار استاندارد:

trade.paper.start

trade.paper.stop

trade.live.start

trade.live.stop

trade.live.position

trade.live.balance

trade.live.orders

trade.live.history

backtest.symbol

backtest.tf

backtest.run

backtest.report

portfolio.summary

portfolio.positions

portfolio.closed

optimization.signal

optimization.risk

optimization.list

optimization.rollback

settings.general

settings.notifications

admin.logs

admin.health

admin.shutdown


---

11. Callback Naming Rules

فرمت:

module.action.target

مثال:

trade.live.start

trade.live.stop

trade.live.modify_tp

trade.live.modify_sl

trade.paper.chart

portfolio.export

admin.metrics

settings.language

استفاده از رشته‌های نامفهوم مانند:

btn1

abc

test

menu3

کاملاً ممنوع است.


---

12. Controller Layer

هر Controller فقط مسئول یک زیرسیستم است.

TradingController

↓

Paper

↓

Live

↓

Manual Orders

↓

Position Management

BacktestController

↓

Run

↓

History

↓

Reports

↓

Chart

↓

Suggestions

OptimizationController

↓

Signal

↓

Risk

↓

Portfolio

↓

Validation

↓

Rollback


---

13. Event Driven Design

Telegram هیچ Engine را Poll نمی‌کند.

بلکه Event دریافت می‌کند.

ExecutionEngine

↓

EventBus

↓

Telegram Notification

↓

User


---

14. Notification Pipeline

ExecutionEngine

↓

Order Filled

↓

EventBus

↓

Notification Engine

↓

Telegram Formatter

↓

Telegram Bot

↓

Send Message


---

15. Message Builder

تمام متن‌ها باید توسط Message Builder ساخته شوند.

Bot.py نباید Message تولید کند.

BacktestFormatter

TradingFormatter

PortfolioFormatter

OptimizationFormatter

AdminFormatter

ChartFormatter


---

16. Keyboard Builder

تمام Keyboardها باید از طریق Builder ساخته شوند.

نمونه:

KeyboardBuilder

↓

Back Button

↓

Home Button

↓

Pagination

↓

Action Buttons

مزایا:

یکپارچگی

قابلیت تغییر Theme

حذف کد تکراری



---

17. Pagination Engine

برای لیست‌های بزرگ:

Positions

Reports

Signals

Orders

Versions


صفحه‌بندی اجباری است.

Previous

1 / 9

Next


---

18. Message Editing Policy

قانون کلی:

عملیات ناوبری:

edit_message()

عملیات مهم:

new_message()

نمونه:

Run Backtest

↓

New Message

Backtest Running...

ولی:

Back

↓

Edit Previous Message


---

19. Error Flow

Controller

↓

Exception

↓

Logger

↓

Formatter

↓

Telegram

↓

Friendly Message

کاربر هرگز نباید Traceback یا Exception خام مشاهده کند.


---

20. Concurrency Model

تمام عملیات طولانی مانند:

Backtest

Optimization

Full History Download

Chart Rendering


باید به صورت:

asyncio.create_task()

یا Queue داخلی اجرا شوند تا رابط کاربری تلگرام پاسخگو باقی بماند.


---

21. Recovery Strategy

اگر Bot ری‌استارت شود:

Sessionهای موقت بازیابی یا بازنشانی شوند.

هیچ سفارش فعال تحت تأثیر قرار نگیرد.

Live Trading مستقل از رابط تلگرام ادامه پیدا کند.


بنابراین تلگرام فقط یک Control Layer است، نه بخشی از هسته اجرای معاملات.


---

22. Golden Rule

تمام اجزای Telegram Subsystem باید از این قانون پیروی کنند:

> Telegram فقط رابط کاربری پروژه است؛ هیچ منطق معاملاتی، تصمیم‌گیری یا مدیریت ریسک نباید در آن پیاده‌سازی شود. تمام تصمیم‌ها در موتورهای اصلی پروژه گرفته می‌شوند و تلگرام صرفاً آن‌ها را هدایت، نمایش و کنترل می‌کند.




---

End of Part 02

در Part 03 درخت کامل منوها (Menu Tree)، تمامی زیرمنوها، مسیرهای ناوبری، دکمه‌ها، ساختار Back/Home، صفحات کاربر و ادمین، و جریان کامل تعامل کاربر با ربات به‌صورت یک طراحی جامع و قابل پیاده‌سازی ارائه خواهد شد.

پارت ۳ — طراحی معماری منوی Telegram و Navigation حرفه‌ای (Enterprise UI/UX)

> Document: APEX Telegram Integration Blueprint
Section: 3 of N
Status: Final Design Specification (Implementation Target)
Version: 1.0




---

3.1 Design Philosophy

منوی تلگرام نباید صرفاً مجموعه‌ای از Command ها باشد.

این منو باید مانند یک نرم‌افزار Trading حرفه‌ای رفتار کند.

اهداف:

حداقل تایپ توسط کاربر

حداقل احتمال خطا

بیشترین سرعت دسترسی

جداسازی کامل قابلیت‌های عمومی از قابلیت‌های مدیریتی

قابلیت توسعه در آینده بدون تغییر معماری

امکان اضافه شدن ماژول‌های جدید بدون تغییر ساختار Menu Tree



---

3.2 Navigation System

تمام منوها باید دارای:

⬅ Back
🏠 Main Menu
❌ Cancel

باشند.

هر صفحه باید بداند از کجا فراخوانی شده است.

بنابراین Navigation Stack لازم است.

Main
   ↓
Backtest
   ↓
BTC
   ↓
1H
   ↓
Run
   ↓
Report

Back دقیقاً یک مرحله عقب برگردد.

نه اینکه همیشه به Main برگردد.


---

3.3 اولین صفحه

━━━━━━━━━━━━━━━━━━

APEX

Institutional Trading System

━━━━━━━━━━━━━━━━━━

📈 Trading

📊 Backtesting

🧠 Optimization

📁 Reports

⚙ Settings

━━━━━━━━━━━━━━━━━━

ℹ Status

❓ Help

در صورت Admin بودن:

🛡 ADMIN

در Header نمایش داده شود.


---

3.4 Trading Branch

Trading دو شاخه کاملاً مجزا دارد.

Trading

│

├── Paper Trading

│

└── Live Trading

دلیل:

هیچ کاربری نباید اشتباهاً وارد Live شود.


---

3.5 Paper Trading

Paper Trading

▶ Start

■ Stop

📈 Live Signals

📋 Active Signals

📊 Performance

⬅ Back

این بخش هیچ ارتباطی با Exchange ندارد.

فقط Engine اجرا می‌شود.


---

3.6 Live Trading

به دلیل حساسیت مالی باید دو مرحله تأیید داشته باشد.

Live Trading

⚠ Warning

This uses REAL MONEY.

Continue?

YES

NO

بعد از تأیید:

▶ Start

■ Stop

📈 Open Positions

📋 Orders

💰 Balance

📊 Performance

⚙ Risk

⬅ Back


---

3.7 Backtest Branch

جریان کامل:

Backtest

↓

Choose Symbol

↓

Choose Timeframe

↓

Confirm

↓

Run

↓

Result


---

انتخاب Symbol

BTC

ETH

SOL

BNB

XRP

DOGE

ADA

LINK

DOT

AVAX


---

پس از انتخاب Symbol:

Choose Timeframe

1m

3m

5m

15m

30m

1h

2h

4h

6h

8h

12h

1D

1W

1M


---

پس از انتخاب:

Run Backtest?

BTC

1H

History:
FULL

YES

BACK


---

3.8 Progress Screen

هنگام اجرا:

Running Backtest...

██████████░░░░░

62%

Candles:

514,322

Signals:

2,814

Elapsed:

02:17

Estimated:

01:12

هر چند ثانیه EditMessage انجام شود و پیام جدید ارسال نشود.


---

3.9 Result Screen

ابتدا خلاصه:

Backtest Complete

Win Rate

63.2%

Profit Factor

2.11

Sharpe

2.48

Max DD

7.3%

Trades

2844


---

سپس:

Recent Signals

فقط

آخرین ۲۵ سیگنال

نمایش داده شود.

مثلاً

BUY BTC

74213

TP Hit

+2.8%

--------

SELL BTC

73982

SL Hit

-1R


---

پس از آن:

Buttons

📈 Equity

📉 Drawdown

📊 Statistics

🧠 AI Analysis

⬅ Back


---

3.10 AI Recommendation Engine

این بخش یکی از ارزشمندترین قسمت‌های پروژه خواهد بود.

پس از پایان Backtest فقط آمار نمایش داده نشود.

بلکه موتور تحلیل نتایج نیز اجرا گردد.

نمونه خروجی:

Analysis

Current Market Regime

Bullish Trend

Confidence

82%

Recommendation

Paper Trading

★★★★★

Live Trading

★★★

Risk Profile

Balanced

Suggested Position Size

0.8%

Suggested Leverage

3x

Avoid Trading During

Low Liquidity Sessions


---

در نسخه‌های بعدی این موتور می‌تواند از خروجی Optimizer، Regime Engine، Evidence Engine و Risk Engine به صورت هم‌زمان استفاده کند تا توصیه‌ها صرفاً آماری نباشند، بلکه با وضعیت فعلی بازار نیز تطبیق داده شوند.

Part 3 — معماری ناوبری (Navigation Architecture) و طراحی منوی حرفه‌ای تلگرام

> نسخه: 1.0
وابستگی: Part 1 + Part 2
هدف: طراحی کامل ساختار ناوبری (Navigation Tree)، سطح دسترسی، دکمه‌های بازگشت، مدیریت Session و تجربه کاربری (UX) برای ربات تلگرام APEX.




---

3.1 اهداف طراحی

رابط تلگرام نباید مجموعه‌ای از Commandهای پراکنده باشد.

بلکه باید شبیه یک نرم‌افزار معاملاتی حرفه‌ای عمل کند.

کاربر نباید مجبور باشد هیچ پارامتری را تایپ کند.

تقریباً تمام عملیات باید توسط:

Inline Keyboard

Callback Query

Wizard

Session State


انجام شود.


---

3.2 ساختار کلی منو

MAIN MENU
│
├── 📊 Backtest
│
├── 📈 Trading
│      │
│      ├── 🧪 Paper Trading
│      │
│      └── 💰 Live Trading
│
├── 📚 Reports
│
├── ⚙ Settings
│
├── ❤️ System Status
│
└── ❓ Help


---

تمام شاخه‌ها دارای:

⬅ Back

🏠 Main Menu

❌ Cancel

هستند.

هیچ بن‌بستی در منو وجود ندارد.


---

3.3 Session State Machine

برای هر کاربر:

TelegramSession

user_id

current_menu

previous_menu

selected_symbol

selected_timeframe

selected_optimizer

selected_strategy

selected_report

selected_trade

language

role

last_message_id

created_at

updated_at


---

Session فقط در حافظه نباشد.

در SQLite یا Redis نیز ذخیره گردد.


---

3.4 Main Menu

═══════════════════════

APEX Trading System

═══════════════════════

📊 Backtest

📈 Trading

📚 Reports

⚙ Settings

❤️ Status

❓ Help

═══════════════════════


---

3.5 Backtest Wizard

مرحله اول

Select Symbol

BTC

ETH

SOL

BNB

XRP

DOGE

ADA

AVAX

LINK

DOT


---

بعد از انتخاب Symbol

Select Timeframe

1m

3m

5m

15m

30m

45m

1h

2h

4h

6h

12h

1D

1W

1M


---

بعد از آن

Run Full History Backtest

دکمه:

▶ Start


---

بدون نیاز به هیچ گزینه اضافی.


---

3.6 روند اجرای Backtest

User

↓

Symbol

↓

Timeframe

↓

Engine Loading

↓

Progress

↓

Finished

↓

Signals

↓

Statistics

↓

AI Suggestions

↓

Back


---

3.7 Progress Screen

Running Backtest...

███████░░░░░░░░░

38%

Downloading candles...

سپس

Preparing Features

سپس

Generating Signals

سپس

Calculating Metrics


---

تمام مراحل به صورت Live Edit Message انجام شوند.

پیام جدید ارسال نشود.


---

3.8 پایان Backtest

ابتدا

آخرین 25 سیگنال

نمایش داده شود.

نمونه:

BUY

BTC

1H

Probability 91%

RR 4.1

Win

...

۲۵ مورد.


---

سپس

Summary

Net Profit

Sharpe

Sortino

PF

Winrate

Average RR

Expectancy

Max DD

Trades

Duration


---

بعد

Interpretation

و بعد

AI Recommendation


---

3.9 AI Recommendation

این قسمت صرفاً نمایش اعداد نباشد.

باید تحلیل کند.

مثلاً:

سیستم در روندهای قوی عملکرد بسیار خوبی دارد.

در بازار رنج افت محسوسی مشاهده شده است.

پیشنهاد می‌شود:

Live Trading

Aggressive Mode

Risk 1.5%

یا

Paper Trading Recommended

یا

Optimization Required


---

3.10 پیشنهادهای بعد از بک‌تست

دکمه‌ها:

Run Optimization

Paper Trading

Live Trading

View Charts

Export Report

Main Menu


---

3.11 طراحی Navigation Stack

Main

↓

Backtest

↓

BTC

↓

1H

↓

Progress

↓

Result

↓

Charts

با زدن Back

Charts

↓

Result

↓

1H

↓

BTC

↓

Backtest

↓

Main


---

هیچ مرحله‌ای حذف نشود.

Session همیشه حفظ گردد.


---

3.12 مدیریت Callbackها

هر Callback دارای شناسه استاندارد باشد:

BT_SYMBOL_BTC

BT_SYMBOL_ETH

BT_TF_1H

BT_TF_4H

BT_START

BT_EXPORT

BT_CHART

BT_BACK

MAIN

REPORTS

STATUS


---

هیچ Callback آزاد یا بدون Prefix تعریف نشود.


---

در ادامه (Part 4)، طراحی کامل بخش Trading شامل تفکیک Paper Trading و Live Trading، کنترل‌های ایمنی، مدیریت سفارش‌های واقعی، و معماری عملیاتی متصل به Toobit را با جزئیات کامل ارائه می‌کنم.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 5 — Navigation Architecture (State Machine + Professional UX)

> Version: 1.0
Dependency:

Part 1

Part 2

Part 3

Part 4





---

5. Navigation Philosophy

از آنجا که پروژه APEX یک سیستم Institutional است، منوی تلگرام نباید صرفاً مجموعه‌ای از Commandها باشد، بلکه باید مانند یک نرم‌افزار حرفه‌ای با State Machine کامل عمل کند.

بنابراین هر صفحه دارای ویژگی‌های زیر خواهد بود:

عنوان صفحه

Breadcrumb

Back

Home

Refresh

Context

Permission Validation

Session Cache

Timeout Recovery



---

5.1 Breadcrumb

همیشه بالای هر صفحه مسیر کاربر نمایش داده می‌شود.

مثال:

🏠 Main

🏠 Main
└── 📊 Backtest

🏠 Main
└── 📊 Backtest
      └── BTCUSDT

🏠 Main
└── 📊 Backtest
      └── BTCUSDT
             └── 1H

این موضوع باعث می‌شود کاربر هرگز گم نشود.


---

5.2 Global Buttons

تمام صفحات دارای دکمه‌های ثابت هستند.

⬅ Back

🏠 Home

🔄 Refresh

❌ Cancel

هیچ صفحه‌ای بدون Back نباید وجود داشته باشد.


---

5.3 Session State

برای هر User یک Session نگهداری می‌شود.

Session

User ID

Current Menu

Current Symbol

Current TF

Current Trade Mode

Current Optimizer

Current Job

Last Report

Current Page

Selected Position

Selected Signal

Timeout

بنابراین دیگر نیازی نیست کاربر هر بار Symbol را تایپ کند.


---

5.4 Timeout

اگر کاربر:

10 دقیقه

کاری انجام ندهد

Session پاک می‌شود.

و پیام ارسال می‌شود:

Session expired.

Please start again.


---

5.5 Main Menu

🏠 APEX

├── 📊 Backtest
│
├── 📈 Trading
│
├── 🧠 Optimization
│
├── 📁 Reports
│
├── 📡 Market
│
├── ⚙ Settings
│
├── ❤️ Health
│
└── 👤 Account


---

5.6 Backtest Flow

کاربر وارد:

📊 Backtest

↓

انتخاب Symbol

BTC

ETH

SOL

BNB

DOGE

...

↓

انتخاب Timeframe

1m

3m

5m

15m

30m

1H

2H

4H

6H

12H

1D

3D

1W

1M

↓

نمایش Summary

BTC

1H

Data:

Jan 2020

↓

Now

Candles:

52,881

↓

Run

▶ Run

⬅ Back

🏠 Home

↓

Engine اجرا می‌شود.


---

5.7 پایان Backtest

پس از اتمام:

✔ Completed

نمایش:

Net Profit

Sharpe

PF

Expectancy

Max DD

Winrate

R

Trades

سپس:

Last 25 Signals

نمایش داده می‌شود.

بعد از آن:

AI Recommendations

سپس:

Next Actions


---

5.8 Trading Menu

📈 Trading

├── Paper Trading

└── Live Trading


---

5.9 Paper Trading

Paper Trading

├── Start

├── Stop

├── Current Signal

├── Recent Signals

├── Positions

├── Statistics

└── Settings


---

5.10 Live Trading

به دلیل حساسیت سرمایه واقعی، این بخش کاملاً از Paper جدا خواهد بود.

Live Trading

├── Start

├── Stop

├── Positions

├── Orders

├── Exposure

├── Risk

├── Balance

├── Withdraw

├── Deposit Info

├── Emergency Stop

└── Exchange Status

نکته مهم:

طبق ساختار فعلی پروژه و کدهای ToobitAdapter، ExecutionEngine و ToobitClient که ارائه کرده‌اید، فقط عملیات سفارش‌گذاری (Place/Cancel/Status) در هسته پروژه پیاده‌سازی شده است. قابلیت‌هایی مانند برداشت وجه (Withdraw)، واریز (Deposit)، انتقال بین حساب‌ها یا مدیریت API Key باید فقط در صورتی به منو اضافه شوند که مستندات API صرافی این Endpointها را پشتیبانی کند و پس از بررسی کامل آن مستندات، با لایه‌های امنیتی (تأیید دومرحله‌ای، محدودیت ادمین، ثبت Audit Log و تأیید مجدد) طراحی شوند. نباید صرفاً به دلیل وجود یک دکمه در منو، عملیات مالی واقعی بدون کنترل‌های لازم فعال شود.


---

در بخش بعدی (Part 6)، طراحی کامل Optimization Center، سیستم گزارش‌ها، نسخه‌بندی، Rollback، صف اجرای Optimization و داشبورد مدیریتی را به‌صورت جزئی و در سطح Production ادامه می‌دهم.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 6 — Optimization Center & Administration Console (Production Specification)

> Version: 1.0
Dependency:

Part 1

Part 2

Part 3

Part 4

Part 5





---

6. Optimization Center

Optimization نباید فقط یک دستور /optimize باشد.

بلکه باید یک زیرسیستم مدیریتی کامل برای تمام فرآیندهای بهینه‌سازی پروژه باشد.

هدف این بخش:

اجرای بهینه‌سازی

مشاهده وضعیت

مدیریت Queue

مشاهده نسخه‌ها

مقایسه نسخه‌ها

فعال‌سازی نسخه

Rollback

مشاهده Validation

مشاهده Artifactها

دریافت گزارش‌ها

دریافت نمودارها



---

6.1 Main Optimization Menu

🧠 Optimization

├── ▶ Run Optimization

├── 📋 Running Jobs

├── 📚 Version Manager

├── 📈 Reports

├── 🧪 Validation

├── 📦 Artifacts

├── 🔄 Rollback

├── ⚙ Optimizer Settings

└── ⬅ Back

این منو فقط برای Admin نمایش داده می‌شود.

کاربر عادی اصلاً این منو را مشاهده نخواهد کرد.


---

6.2 Run Optimization Wizard

اجرای Optimization به‌صورت Wizard چندمرحله‌ای انجام می‌شود.

Step 1

Select Symbol

BTC

ETH

SOL

BNB

...

↓

Step 2

Select Timeframe

↓

Step 3

Optimization Type

○ Signal

○ Risk

○ Portfolio

○ Ensemble

○ Full

↓

Step 4

Trials

100

300

500

1000

Custom

↓

Step 5

Validation

✔ Walk Forward

✔ Monte Carlo

✔ Stress Test

✔ Cross Validation

✔ Stability Test

↓

Step 6

Confirmation

Run Optimization?

Estimated Time

Expected CPU

Expected Memory

Expected Disk

↓

▶ Start


---

6.3 Running Jobs

Running Jobs

Job #31

BTC

1H

Signal

Progress

67%

Elapsed

00:14:32

ETA

00:05:10

CPU

73%

Memory

1.8 GB

Status

Running

Buttons:

Refresh

Pause

Cancel

Logs

Back


---

6.4 Optimization Queue

اگر Job دیگری در حال اجرا باشد:

Queue

#1 BTC Signal

#2 ETH Risk

#3 SOL Portfolio

#4 BTC Full

برای هر Job:

Priority

Created

Owner

Estimated Runtime

Status


---

6.5 Version Manager

BTC

↓

1H

↓

Signal

↓

Versions

v1.0

v1.1

v1.2

v2.0 ACTIVE

v2.1

هر نسخه دارای اطلاعات زیر است:

Date

Optimizer

Trials

Validation Score

Sharpe

PF

DD

Stability

Status


---

6.6 Version Actions

برای هر نسخه:

View Report

Compare

Activate

Rollback

Delete

Export

Artifacts

Delete فقط برای نسخه‌های Archive مجاز است.


---

6.7 Compare Versions

Compare

v2.0

vs

v2.1

نمایش:

Profit

Sharpe

PF

DD

Winrate

Expectancy

Trades

Recovery

Stability

Confidence

در انتها:

Winner

v2.1

+7.3%


---

6.8 Validation Center

هر Optimization دارای Validation مستقل است.

Validation

Walk Forward

PASS

Monte Carlo

PASS

Stress

PASS

Cross Validation

PASS

Out Of Sample

PASS

در صورت Fail:

FAILED

Reason:

High Variance


---

6.9 Reports

Reports

Summary

Detailed

Charts

CSV

Excel

PDF

JSON

هر Report قابل دانلود خواهد بود.


---

6.10 Charts

تمام نمودارها به‌صورت تصویر PNG و در صورت امکان SVG تولید می‌شوند.

Equity Curve

Drawdown

Monthly Returns

Parameter Importance

Optimization History

Trade Distribution

R Multiple

Exposure

Win/Loss

Heatmap


---

6.11 Artifact Browser

Artifacts

├ Report.pdf

├ trades.csv

├ parameters.json

├ optimization.json

├ validation.json

├ charts/

├ logs/

└ metadata.json

هر فایل قابل دانلود از طریق تلگرام خواهد بود.


---

6.12 Optimizer Settings

این قسمت مخصوص تنظیماتی است که خارج از چرخه یادگیری و بهینه‌سازی قرار دارند و نباید پارامترهای خروجی Optimizer را به‌صورت دستی بازنویسی کنند.

Optimizer Settings

Execution Mode

○ Automatic

○ Manual Approval

○ Manual Parameters

Risk Profile

○ Defensive

○ Balanced

○ Aggressive

Optimization Schedule

○ Disabled

○ Daily

○ Weekly

○ Monthly

Auto Activate Better Version

ON / OFF

Minimum Improvement

1%

2%

5%

Rollback Threshold

Validation Failure

Performance Drop

Manual Only

در این طراحی، Optimizer همچنان مسئول تعیین پارامترهای معاملاتی است و ادمین فقط سیاست‌های کلان (Policy) را کنترل می‌کند، نه اینکه مستقیماً پارامترهای بهینه‌شده را تغییر دهد. این رویکرد با معماری حرفه‌ای سیستم‌های الگوریتمی سازگارتر است و از تداخل تصمیمات انسانی با نتایج بهینه‌سازی جلوگیری می‌کند.


---

در Part 7 طراحی کامل Live Trading Center، مدیریت سفارش‌ها، مدیریت پوزیشن‌ها، داشبورد سرمایه، اعلان‌های هوشمند و کنترل‌های ایمنی (Emergency Controls) ارائه خواهد شد.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 7 — Live Trading Center (Institutional Trading Console)

> Version: 1.0
Dependency:

Part 1 تا Part 6





---

7. Live Trading Center

این بخش مهم‌ترین قسمت کل سیستم است.

از آنجا که پروژه به صرافی Toobit متصل است و طبق فایل‌های بررسی‌شده:

ToobitClient

ToobitAdapter

ExecutionEngine

TradeBlueprint


زیرساخت اجرای سفارش از قبل وجود دارد، بنابراین منوی تلگرام باید فقط یک رابط کاربری (UI Layer) باشد و هیچ منطق معاملاتی مستقلی در آن قرار نگیرد.

اصل طراحی:

Telegram → Application Layer → Execution Engine → Toobit Adapter → Toobit API

هیچ فراخوانی مستقیمی از Bot به Exchange مجاز نیست.


---

7.1 Main Live Trading Menu

💰 Live Trading

├── 📊 Dashboard

├── 📈 Open Positions

├── 🧾 Orders

├── 💵 Wallet

├── 📉 Risk Monitor

├── 🔔 Signals

├── ⚡ Emergency

├── ⚙ Trading Policy

└── ⬅ Back

این بخش فقط برای Administrator نمایش داده می‌شود.

کاربر عادی هرگز نباید به آن دسترسی داشته باشد.


---

7.2 Live Dashboard

Live Dashboard

Exchange

Toobit

Mode

LIVE

Connection

ONLINE

Account Equity

Balance

Available Margin

Used Margin

Floating PnL

Today's PnL

Win Rate

Risk Level

Active Symbols

Running Strategies

Optimizer Version

Server Time

پایین صفحه:

Refresh

Positions

Orders

Emergency

Back


---

7.3 Open Positions

Open Positions

BTC LONG

ETH SHORT

SOL LONG

...

انتخاب هر پوزیشن:

Entry

Current

PnL

Quantity

Leverage

Risk

Stop

TP1

TP2

TP3

Holding Time

Trade Quality Index

Blueprint ID


---

7.4 Position Actions

برای هر Position:

Modify Stop

Move SL To BE

Partial Close

Close Position

View Chart

View History

Back

تمام عملیات قبل از اجرا باید نیازمند تأیید مجدد باشند.

Confirm?

YES

NO


---

7.5 Orders

Orders

Pending

Filled

Cancelled

Rejected

Expired

برای هر Order:

Order ID

Client Order ID

Status

Exchange Status

Create Time

Execution Time

Retries

Latency


---

7.6 Wallet

نمایش اطلاعات سرمایه بدون امکان برداشت از داخل تلگرام.

Wallet

Account Balance

Available Balance

Margin Balance

Realized PnL

Floating PnL

Today's Profit

Weekly Profit

Monthly Profit

Maximum Drawdown

دلیل حذف عملیات برداشت و واریز:

این عملیات بسیار حساس هستند.

معمولاً نیازمند احراز هویت دومرحله‌ای، ایمیل، یا تأییدهای امنیتی صرافی هستند.

بهتر است مدیریت دارایی فقط از طریق پنل رسمی صرافی انجام شود و تلگرام صرفاً نقش مانیتورینگ و مدیریت معاملات را داشته باشد.



---

7.7 Risk Monitor

Risk Monitor

Portfolio Risk

Exposure

Max Position

Daily Loss

Weekly Loss

Current DD

VAR

Leverage

Margin Ratio

Liquidation Distance

در صورت عبور از آستانه‌های تعریف‌شده، هشدار فوری صادر می‌شود.


---

7.8 Live Signals

Recent Signals

BTC LONG

Probability

91%

Confidence

94%

Expected Value

Trade Quality

Execution

FILLED

برای هر سیگنال:

View Blueprint

View Chart

View Features

View Decision

View Risk


---

7.9 Emergency Center

این بخش یکی از مهم‌ترین قابلیت‌های مدیریتی سیستم است.

Emergency

Pause Trading

Resume Trading

Disable New Entries

Close All Positions

Cancel All Orders

Safe Mode

Disconnect Exchange

Reconnect Exchange

برای عملیات‌های بحرانی مانند Close All Positions و Cancel All Orders تأیید دومرحله‌ای (Double Confirmation) الزامی است تا از اجرای ناخواسته جلوگیری شود.


---

7.10 Trading Policy

این بخش برای تعیین سیاست‌های کلان اجرای معاملات است و نباید جایگزین تصمیمات Optimizer شود.

Trading Policy

Strategy State

○ Enabled

○ Disabled

Execution Mode

○ Paper

○ Live

Trading Style

○ Defensive

○ Balanced

○ Aggressive

Maximum Concurrent Trades

Maximum Daily Risk

Maximum Symbol Exposure

Maximum Portfolio Drawdown

Auto Resume After Error

ON / OFF

تمام این گزینه‌ها باید در لایه تنظیمات مرکزی پروژه ذخیره شوند و توسط موتورهای تصمیم‌گیری و اجرا خوانده شوند، نه اینکه مستقیماً در Bot اعمال شوند.


---

در Part 8 طراحی کامل Paper Trading Center، سیستم اعلان‌های هوشمند، نمایش گرافیکی معاملات و کندل‌ها، و یکپارچه‌سازی نمایش نمودارهای واقعی بازار ارائه خواهد شد.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 8 — Paper Trading Center, Smart Notifications & Professional Charting

> Version: 1.0
Dependency:

Part 1 تا Part 7





---

8. Paper Trading Center

Paper Trading باید دقیقاً همان مسیر Live Trading را طی کند، با این تفاوت که هیچ سفارشی به صرافی ارسال نمی‌شود.

اصل طراحی:

Signal Engine
      │
      ▼
Decision Engine
      │
      ▼
Risk Engine
      │
      ▼
Trade Blueprint
      │
      ▼
Execution Simulator
      │
      ▼
Virtual Portfolio

بدین ترتیب تمام آمارهای Paper Trading با Live Trading قابل مقایسه خواهند بود.


---

8.1 Main Menu

📝 Paper Trading

├── Dashboard

├── Active Signals

├── Virtual Positions

├── Trade History

├── Performance

├── Suggestions

├── Reset Portfolio

└── ⬅ Back


---

8.2 Paper Dashboard

Mode

PAPER

Virtual Balance

10000 USDT

Equity

10437 USDT

Open Positions

5

Today's Profit

+3.14%

Floating PnL

+172

Closed Trades

214

Winrate

71%

Sharpe

2.31

Profit Factor

2.81

Current Optimizer

v2.3


---

8.3 Active Signals

هر سیگنال شامل اطلاعات کامل Blueprint خواهد بود.

BTC LONG

Probability

94%

Confidence

92%

Expected Value

Trade Quality Index

Risk Score

Entry

Stop

TP1

TP2

TP3

Leverage

Execution Status


---

8.4 Virtual Positions

BTC LONG

Entry

Current Price

PnL

Holding Time

Risk

Remaining Distance To TP

Remaining Distance To SL

عملیات مجاز:

Close

Move SL

Move TP

Chart

Analysis

Back


---

8.5 Performance

Daily

Weekly

Monthly

All Time

نمایش:

Profit

Sharpe

Sortino

Calmar

Recovery

Drawdown

Winrate

Average RR

Average Holding

Expectancy


---

8.6 Intelligent Suggestions

این قسمت یکی از قابلیت‌های اختصاصی پروژه خواهد بود.

بعد از پایان Backtest یا Paper Trading، سیستم صرفاً آمار نمایش نمی‌دهد، بلکه پیشنهادهای عملی ارائه می‌کند.

نمونه:

Current Market

Trending

Recommendation

Balanced Mode

Confidence

High

Reason

Strong trend

Low volatility

Positive liquidity

Institutional bias detected

یا:

Market

Highly Volatile

Recommendation

Do NOT enable Live Trading

Reason

Poor Stability

Weak Confirmation

High Drawdown Probability

این پیشنهادها باید توسط موتور تحلیل پروژه تولید شوند و متن‌ها از قالب‌های از پیش تعریف‌شده (Template-Based) با داده‌های واقعی پر شوند.


---

8.7 Smart Notifications

سیستم اعلان‌ها باید کاملاً قابل تنظیم باشد.

Notifications

├── Trading

├── Optimization

├── Risk

├── Portfolio

├── Exchange

├── Health

├── Security

└── Reports


---

Trading Notifications

New Signal

Position Opened

Position Closed

TP Hit

SL Hit

Break Even

Partial Close

High Probability Signal

Rejected Order


---

Optimization Notifications

Optimization Started

Optimization Finished

Validation Passed

Validation Failed

New Best Version

Rollback Executed


---

Risk Notifications

Daily Loss Limit

Portfolio DD

Margin Warning

High Exposure

Risk Limit Reached

Emergency Stop Activated


---

Health Notifications

WebSocket Disconnected

Exchange Reconnected

API Error

Heartbeat Lost

High CPU

Low Memory

Queue Overflow


---

8.8 Notification Priority

هر اعلان باید دارای سطح اهمیت باشد.

INFO

SUCCESS

WARNING

ERROR

CRITICAL

اعلان‌های CRITICAL باید حتی در صورت غیرفعال بودن اعلان‌های عادی نیز برای مدیر ارسال شوند.


---

8.9 Professional Chart Viewer

این بخش یکی از قابلیت‌هایی است که سطح پروژه را به شکل محسوسی ارتقا می‌دهد و با پیشنهاد شما نیز کاملاً همسو است.

برای هر سیگنال یا معامله، گزینه:

📈 View Chart

وجود خواهد داشت.

با انتخاب آن، سیستم یک تصویر واقعی از چارت تولید می‌کند که شامل موارد زیر است:

50 تا 200 کندل قبل از Trigger (قابل تنظیم)

کندل Trigger

کندل‌های بعد از Trigger تا وضعیت فعلی یا خروج

نقطه Entry

Stop Loss

TP1 / TP2 / TP3

جهت معامله (LONG/SHORT)

نواحی مهم ساختاری (در صورت وجود)

زمان و تایم‌فریم


این تصویر می‌تواند از داده‌های واقعی دریافت‌شده از صرافی تولید شود و با کتابخانه‌هایی مانند Plotly یا mplfinance رندر گردد.


---

8.10 Interactive Web Chart

علاوه بر تصویر ثابت، سیستم می‌تواند یک نمایشگر وب نیز داشته باشد.

جریان کار:

Telegram

↓

Open Web Viewer

↓

Browser

↓

http://SERVER:PORT/chart?id=TRADE_ID

در این صفحه امکانات زیر وجود دارد:

Zoom

Pan

نمایش اندیکاتورهای پروژه

نمایش سیگنال‌ها

نمایش ساختار بازار

مشاهده تمام کندل‌ها

حرکت روی تاریخچه

نمایش توضیحات هر سیگنال با Hover


این قابلیت ادامه طبیعی همان ایده‌ای است که قبلاً برای نمایش نمودار در مرورگر استفاده کرده بودید و برای تحلیل‌های حرفه‌ای بسیار ارزشمند است.


---

در Part 9 طراحی نهایی بخش Settings، Role-Based Access Control، مدیریت کاربران، ثبت رویدادها (Audit Log)، امنیت، ساختار Callbackها، State Machine منوها و معماری داخلی Telegram Layer ارائه خواهد شد.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 9 — Security, RBAC, Settings, Audit Log & Telegram Architecture (Enterprise Specification)

> Version: 1.0
Dependency:

Part 1 تا Part 8





---

9. Enterprise Security Architecture

از آنجا که این پروژه مستقیماً به حساب واقعی صرافی متصل می‌شود، لایه تلگرام باید صرفاً یک Presentation Layer باشد و هیچ منطق امنیتی در Handlerها پیاده‌سازی نشود.

معماری صحیح:

Telegram UI
      │
      ▼
Telegram Router
      │
      ▼
Permission Manager
      │
      ▼
Application Service
      │
      ▼
Domain Layer
      │
      ▼
Execution Engine
      │
      ▼
Exchange Adapter

هیچ Handler تلگرام نباید مستقیماً:

API صرافی را فراخوانی کند.

فایل تنظیمات را تغییر دهد.

پارامترهای Optimizer را تغییر دهد.

به Vault دسترسی مستقیم داشته باشد.



---

9.1 Role Based Access Control (RBAC)

سیستم دارای چهار سطح دسترسی خواهد بود.

ROLE_PUBLIC

↓

ROLE_TRADER

↓

ROLE_ADMIN

↓

ROLE_OWNER


---

ROLE_PUBLIC

فقط مشاهده اطلاعات عمومی:

Status

Recent Signals

Backtest Reports

Optimizer Active Version

Market Status

Paper Trading Reports

هیچ عملیات اجرایی ندارد.


---

ROLE_TRADER

علاوه بر موارد بالا:

Paper Trading

Paper Portfolio

Paper Charts

Strategy Suggestions

Personal Notifications

هنوز دسترسی به Live Trading ندارد.


---

ROLE_ADMIN

تمام قابلیت‌های عملیاتی:

Optimization

Live Trading

Orders

Positions

Emergency

Risk

Reports

Policies

Settings


---

ROLE_OWNER

تمام قابلیت‌های ADMIN به علاوه:

User Management

Role Management

API Keys

Vault

System Update

Danger Zone

Factory Reset

License

Diagnostics


---

9.2 User Management

Users

Administrator

Trader

Guest

Blocked

برای هر کاربر:

Telegram ID

Username

Role

Registration Time

Last Activity

Permissions

Status


---

9.3 Permission Matrix

Module	Public	Trader	Admin	Owner

Status	✔	✔	✔	✔
Backtest	✔	✔	✔	✔
Paper Trading	✖	✔	✔	✔
Live Trading	✖	✖	✔	✔
Optimization	✖	✖	✔	✔
Risk	✖	✖	✔	✔
Settings	✖	✖	✔	✔
User Manager	✖	✖	✖	✔
Vault	✖	✖	✖	✔



---

9.4 Audit Log

تمام عملیات مهم باید ثبت شوند.

Audit Log

Date

Time

User

Action

Module

Result

IP (در صورت وجود)

Duration

Correlation ID

نمونه:

2026-07-18

21:31:14

ADMIN

Rollback Optimizer

SUCCESS

Duration

3.2 sec


---

9.5 Security Log

ثبت رویدادهای امنیتی:

Failed Login

Permission Denied

Unknown Callback

Expired Session

Invalid Command

Repeated Requests

Exchange Authentication Error


---

9.6 Settings Center

تنظیمات باید به چند بخش تقسیم شوند.

⚙ Settings

├── General

├── Telegram

├── Notifications

├── Trading

├── Optimizer

├── Charts

├── Reports

├── Security

├── Backup

└── Back


---

General

Language

Timezone

Theme

Default Symbol

Default Timeframe

Date Format

Number Format


---

Telegram

Menu Style

Inline Keyboard

Pagination

Auto Refresh

Message Lifetime

Delete Old Messages

Maximum History


---

Notifications

Trading

Optimizer

Risk

Portfolio

Exchange

Health

Security

Reports

هر مورد:

ON/OFF

Priority

Mute Period

Delivery Method


---

Charts

Candles Before Trigger

50

100

200

500

Theme

Dark

Light

Indicators

ON

OFF

Image Resolution

HD

4K


---

Reports

PDF

Excel

CSV

JSON

Automatic Archive

Compression

Retention Period


---

Backup

Export Settings

Import Settings

Create Snapshot

Restore Snapshot

Cloud Backup (Future)

Local Backup


---

9.7 Callback Architecture

تمام Callbackها باید نام‌گذاری استاندارد داشته باشند.

BT_SYMBOL_BTC

BT_TF_1H

BT_RUN

LIVE_POS_12

LIVE_CLOSE_12

OPT_RUN

OPT_VERSION_21

REPORT_PDF

REPORT_CSV

BACK

از Callbackهای طولانی یا دارای داده خام JSON استفاده نشود.


---

9.8 Menu State Machine

هر کاربر یک وضعیت (State) فعال خواهد داشت.

MAIN_MENU

↓

BACKTEST_MENU

↓

SELECT_SYMBOL

↓

SELECT_TIMEFRAME

↓

RUNNING

↓

RESULT

↓

BACK

↓

MAIN

بازگشت (⬅ Back) فقط یک دکمه ظاهری نیست؛ باید وضعیت قبلی را از Stack منو بازیابی کند تا تجربه کاربری روان و بدون بن‌بست باشد.


---

9.9 Session Manager

برای هر کاربر:

Current Menu

Current Wizard

Selected Symbol

Selected TF

Selected Version

Current Job

Last Message

Permissions

Timeout

اگر نشست منقضی شود:

Session Expired

Return To Main Menu


---

9.10 Enterprise Design Principles

این طراحی بر چند اصل استوار است:

جداسازی کامل UI از منطق کسب‌وکار

اعمال RBAC در یک نقطه مرکزی

عدم دسترسی مستقیم Bot به Exchange یا Vault

ثبت کامل عملیات در Audit Log

قابلیت توسعه برای چند صرافی و چند کاربر

State Machine برای مدیریت منوها

Callbackهای استاندارد و قابل نگهداری

امکان افزودن قابلیت‌های آینده بدون بازطراحی ساختار



---

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 10 — Exchange Integration, Live Execution Workflow & Enterprise Trading Operations

> Version: 1.0
Dependency:

Part 1 تا Part 9

Toobit API Documentation (نسخه بررسی‌شده)

ساختار فعلی پروژه (ToobitClient / ToobitAdapter / ExecutionEngine)





---

10. فلسفه طراحی اتصال به صرافی

پس از بررسی کامل مستند رسمی Toobit و همچنین فایل‌های پروژه، ساختار فعلی پروژه از نظر معماری بسیار مناسب است و باید حفظ شود.

معماری نهایی باید به صورت زیر باقی بماند:

Telegram UI

↓

Telegram Router

↓

Application Service

↓

Execution Engine

↓

Exchange Adapter

↓

Toobit Client

↓

REST API
+
User Data WebSocket
+
Market WebSocket

هیچ Handler تلگرام نباید مستقیماً هیچ Endpoint صرافی را فراخوانی کند.


---

10.1 لایه‌های ارتباط با Toobit

پس از بررسی مستند رسمی، سیستم باید از سه کانال مستقل استفاده کند:

Channel 1

Market Data

وظیفه:

قیمت

کندل

عمق بازار

مارک پرایس

Funding

Open Interest

Long/Short Ratio


این همان WebSocket فعلی پروژه است که باید توسعه یابد.


---

Channel 2

Trading REST

وظیفه:

ایجاد سفارش

حذف سفارش

تغییر سفارش

تغییر لوریج

تغییر Margin Type

دریافت موجودی

دریافت معاملات

دریافت سفارش‌ها



---

Channel 3

Private User Stream

این بخش اکنون در پروژه وجود ندارد و باید اضافه شود.

وظیفه:

Position Update

Order Update

Balance Update

Trade Update

TP/SL Update

ListenKey KeepAlive


این کانال باید منبع اصلی به‌روزرسانی وضعیت معاملات باشد و از Polling مداوم REST جلوگیری کند.


---

10.2 وضعیت اتصال (Connection Center)

منوی جدید:

Exchange

──────────────

REST

ONLINE

WS Market

ONLINE

WS User

ONLINE

Latency

18 ms

Last Ping

3 sec

Reconnect Count

2

Rate Limit

Healthy

API Version

v2

Server Time

...

دکمه‌ها:

Reconnect

Diagnostics

Ping

Back


---

10.3 عملیات مجاز در Live Trading

با توجه به مستند API، تنها عملیات زیر از داخل تلگرام مجاز باشند:

سفارش

ایجاد سفارش

لغو سفارش

مشاهده سفارش

مشاهده سفارش‌های باز

مشاهده تاریخچه سفارش‌ها



---

پوزیشن

مشاهده

بستن

تغییر Stop

تغییر TP

انتقال به BreakEven

Partial Close



---

تنظیمات

تغییر Leverage

تغییر Margin Mode

تغییر Trading Style پروژه



---

مشاهده

موجودی

سود روز

معاملات

PnL

Risk



---

10.4 عملیاتی که نباید از تلگرام انجام شوند

با وجود اینکه مستند API برخی از این قابلیت‌ها را ارائه می‌دهد، پیشنهاد می‌شود در نسخه Production از طریق تلگرام انجام نشوند:

❌ برداشت دارایی

❌ انتقال بین حساب‌ها

❌ مدیریت API Key

❌ حذف کاربران

❌ Factory Reset

❌ تغییر Vault

این موارد فقط از محیط‌های مدیریتی امن انجام شوند.


---

10.5 چرخه اجرای سفارش

هر سفارش باید مراحل زیر را طی کند:

Signal

↓

Decision Engine

↓

Risk Engine

↓

Trade Blueprint

↓

Execution Validation

↓

Telegram Confirmation
(Admin Only if required)

↓

Execution Engine

↓

Exchange Adapter

↓

Toobit REST

↓

Order Accepted

↓

User Stream

↓

Position Update

↓

Portfolio Update

↓

Telegram Notification

هیچ مرحله‌ای نباید حذف شود.


---

10.6 پیش‌اعتبارسنجی سفارش (Pre-Trade Validation)

قبل از ارسال هر سفارش، سیستم باید موارد زیر را بررسی کند:

اتصال REST برقرار باشد.

WebSocket کاربر فعال باشد.

نماد در وضعیت TRADING باشد.

موجودی کافی باشد.

حجم سفارش از حداقل و حداکثر مجاز عبور نکند.

دقت قیمت و حجم با فیلترهای صرافی منطبق باشد.

تعداد معاملات همزمان از سقف سیاست پروژه بیشتر نباشد.

محدودیت ریسک روزانه نقض نشده باشد.

Circuit Breaker فعال نباشد.

Emergency Stop فعال نباشد.


در صورت رد شدن هر مورد، سفارش هرگز به صرافی ارسال نشود.


---

10.7 چرخه مدیریت سفارش

پس از ارسال سفارش:

NEW

↓

PARTIALLY_FILLED

↓

FILLED

↓

POSITION_CREATED

↓

TP / SL ACTIVE

↓

POSITION CLOSED

↓

ARCHIVED

تمام این تغییرات باید از User Data Stream دریافت شوند، نه با Polling مداوم REST.


---

10.8 مدیریت خطاها

کدهای خطای صرافی باید به دسته‌های معنایی تبدیل شوند:

NETWORK

AUTH

RATE_LIMIT

BALANCE

INVALID_ORDER

RISK_LIMIT

SYMBOL_ERROR

TIME_SYNC

SERVER_ERROR

کاربر نباید مستقیماً کدهایی مانند -1131 یا -1021 را ببیند؛ بلکه پیام‌های قابل فهم همراه با ثبت جزئیات فنی در Log نمایش داده شوند.


---

10.9 همگام‌سازی زمان

با توجه به حساسیت امضای درخواست‌ها، سیستم باید به‌صورت دوره‌ای زمان محلی را با زمان سرور صرافی همگام کند تا از خطاهای ناشی از اختلاف زمان جلوگیری شود.


---

در Part 11 طراحی کامل سیستم گزارش‌گیری حرفه‌ای، داشبورد مدیریتی، تحلیل عملکرد، آرشیو معاملات، خروجی PDF/Excel، و داشبورد تحت وب Enterprise ارائه خواهد شد.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 11 — Enterprise Reporting, Analytics Dashboard, Live Monitoring & Decision Support

> Version: 1.0
Dependency:

Part 1 تا Part 10

بررسی مستند رسمی Toobit API (REST + WebSocket + User Data Stream)





---

11. فلسفه طراحی داشبورد مدیریتی

هدف این بخش صرفاً نمایش اطلاعات نیست.

این بخش باید تبدیل شود به:

> Command & Control Center پروژه



یعنی مدیر پروژه بتواند تنها با تلگرام وضعیت کل سیستم را مشاهده و تحلیل کند، بدون نیاز به ورود به سرور یا ترمینال.


---

11.1 Main Dashboard

📊 Dashboard

────────────────────

System

ONLINE

Exchange

CONNECTED

Optimizer

RUNNING

Paper Trading

ACTIVE

Live Trading

ACTIVE

Portfolio

+4.83%

Risk

LOW

CPU

21%

RAM

34%

Queue

0

Latency

19 ms

Health

100%

Last Update

14 sec ago

────────────────────

[Portfolio]

[Trading]

[Optimizer]

[Reports]

[Monitoring]

[Back]

این داشبورد باید به صورت Auto Refresh (قابل تنظیم) بروزرسانی شود.


---

11.2 Portfolio Dashboard

Portfolio

──────────────

Balance

12,532 USDT

Equity

12,911

Floating

+381

Closed Profit

+7,812

Today's Profit

+1.83%

Weekly

+8.12%

Monthly

+21.8%

Open Positions

6

Margin Used

14%

Available

86%

Leverage Avg

4.2x


---

11.3 Risk Dashboard

Risk

────────────

Portfolio DD

2.3%

Daily DD

0.4%

Current Exposure

31%

Value At Risk

1.6%

Expected Shortfall

0.9%

Worst Position

SOL

Largest Winner

BTC

Emergency Status

OFF

Circuit Breaker

OFF


---

11.4 Optimizer Dashboard

Optimizer

──────────────

Current Version

v2.8

Signal Optimizer

Healthy

Risk Optimizer

Healthy

Walk Forward

PASS

Monte Carlo

PASS

Stress Test

PASS

Validation Score

96.3

Next Schedule

Tomorrow 03:00 UTC


---

11.5 Execution Dashboard

با توجه به ساختار فعلی ExecutionEngine و ToobitAdapter، این بخش باید وضعیت اجرای سفارش‌ها را نمایش دهد.

Execution

────────────

Orders Today

214

Filled

207

Rejected

2

Cancelled

5

Average Latency

28 ms

Retry Count

4

Current Queue

0

Last Order

SUCCESS


---

11.6 Exchange Health Dashboard

بر اساس اطلاعات WebSocket و REST.

Exchange

────────────

REST

ONLINE

Market WS

ONLINE

User WS

ONLINE

ListenKey

VALID

Next KeepAlive

38 min

Reconnects Today

1

Rate Limit

Healthy

Clock Drift

3 ms

از آنجا که مستند رسمی Toobit استفاده از ListenKey با اعتبار ۶۰ دقیقه را الزام کرده است، وضعیت آن باید دائماً مانیتور شود.


---

11.7 Reports Center

Reports

────────────

Performance

Portfolio

Trades

Optimizer

Backtests

Paper Trading

Risk

Exchange

Logs

Audit

Export


---

11.8 Performance Report

گزارش کامل شامل:

Net Profit

Gross Profit

Gross Loss

Profit Factor

Sharpe

Sortino

Calmar

Recovery

Expectancy

Average RR

Average Win

Average Loss

Largest Win

Largest Loss

Longest Win Streak

Longest Loss Streak

Average Holding Time

Total Trades

Winrate

Drawdown

Return/DD Ratio


---

11.9 Trade Report

برای هر معامله:

Trade ID

Blueprint ID

Decision ID

Signal Quality

Probability

Confidence

Entry

Exit

PnL

R Multiple

Commission

Slippage

Holding Time

Exit Reason

Optimizer Version

این اطلاعات با ساختار TradeBlueprint و Trade موجود در پروژه کاملاً سازگار است.


---

11.10 Backtest Report

پس از پایان بک‌تست:

ابتدا:

25 آخرین سیگنال

نمایش داده شود.

سپس:

Summary Report

سپس:

Professional Analysis


---

نمونه:

Current Regime

Strong Trend

Recommendation

Enable Live Trading

Confidence

95%

Suggested Style

Balanced

Risk

Medium

Recommended Leverage

3x

Recommended Capital Usage

30%


---

11.11 AI Decision Support

این قسمت یکی از ارزشمندترین قابلیت‌های پروژه خواهد بود.

سیستم صرفاً گزارش ارائه نمی‌دهد.

بلکه تفسیر نیز ارائه می‌کند.

مثال:

Recent trades indicate:

Excellent trend detection

Low drawdown

Very stable optimizer

Market volatility acceptable

Recommendation:

Live Trading can remain enabled.

یا

Recent Backtests indicate:

Optimizer unstable

Monte Carlo weak

Recent losses increasing

Recommendation

Disable Live Trading

Run Optimization Again

Paper Trading Recommended


---

11.12 Export Center

Export

────────────

PDF

Excel

CSV

JSON

HTML

ZIP Archive

هر گزارش باید قابلیت خروجی در چند قالب را داشته باشد.


---

11.13 Automatic Scheduled Reports

قابلیت زمان‌بندی ارسال گزارش:

Daily

Weekly

Monthly

Optimization Finished

Large Drawdown

New Best Version

Emergency Event

مدیر پروژه بدون درخواست دستی گزارش را دریافت خواهد کرد.


---

11.14 Enterprise Log Viewer

Logs

────────────

Trading

Optimizer

Exchange

Security

Telegram

System

Errors

Warnings

Debug

با امکان:

جستجو

فیلتر

دانلود

پاک‌سازی (فقط Owner)



---

در Part 12 معماری نهایی فایل‌ها، ساختار پوشه‌های Telegram Layer، کلاس‌های موردنیاز، جریان کامل Callbackها، قرارداد بین Bot و Application Layer، و برنامه مرحله‌به‌مرحله پیاده‌سازی بدون شکستن ساختار فعلی پروژه ارائه خواهد شد.

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 12 — Final Architecture, Telegram Layer, Implementation Roadmap & Production Integration

> Version: 1.0
Dependency:

Part 1 تا Part 11

بررسی کامل ساختار فعلی پروژه

بررسی مستند رسمی Toobit API (REST v1/v2 + User Stream + WebSocket)





---

12. هدف نهایی

در پایان این Blueprint، لایه Telegram باید فقط یک رابط کاربری باشد و هیچ منطق تجاری در آن قرار نگیرد.

تمام تصمیم‌گیری‌ها، مدیریت معاملات، ریسک، بهینه‌سازی و ارتباط با صرافی باید در لایه‌های پایین‌تر انجام شود.

Telegram

↓

Router

↓

Command Dispatcher

↓

Permission Manager

↓

Application Services

↓

Domain

↓

Infrastructure

↓

Exchange


---

12.1 ساختار پیشنهادی پوشه Telegram

src/apex/infrastructure/telegram/

│

├── bot.py

├── router.py

├── dispatcher.py

├── callback_router.py

├── permissions.py

├── session_manager.py

├── state_machine.py

├── keyboards.py

├── paginator.py

├── message_builder.py

├── chart_sender.py

├── report_sender.py

├── notification_service.py

├── callback_constants.py

├── menu_registry.py

├── handlers/

│      main.py
│      backtest.py
│      optimize.py
│      paper.py
│      live.py
│      portfolio.py
│      reports.py
│      settings.py
│      users.py
│      diagnostics.py

└── dto/


---

12.2 مسئولیت هر فایل

bot.py

فقط:

Start

Stop

Polling

ثبت Handlerها

Bootstrap


هیچ منطق دیگری.


---

router.py

تشخیص:

Command

Callback

Message



---

dispatcher.py

تبدیل Command به:

Application Service


---

session_manager.py

نگهداری:

Current Menu

Wizard

Selections

Timeout

History Stack


---

state_machine.py

تمام حرکت بین منوها:

Main

↓

Trade

↓

Live

↓

Position

↓

Chart

↓

Back


---

message_builder.py

تمام متن‌های ارسالی.

هیچ متن HardCode در Handlerها نباشد.


---

keyboards.py

تمام InlineKeyboardها در یک محل متمرکز.


---

notification_service.py

تمام اعلان‌های:

Trading

Optimizer

Exchange

Health

Security

Risk



---

12.3 Command Dispatcher

تمام دستورات:

/menu

/status

/backtest

/paper

/live

/portfolio

/reports

/optimizer

/settings

همگی به Dispatcher ارسال شوند.


---

12.4 Callback Dispatcher

تمام Callbackها ابتدا اعتبارسنجی شوند.

Permission

↓

State

↓

Callback

↓

Application

اگر Callback ناشناخته باشد:

Audit Log

+

Security Log

+

Ignore


---

12.5 ارتباط با Application Layer

هیچ Handler نباید:

ToobitClient()

ExecutionEngine()

Optimizer()

Vault()

را مستقیماً Instantiate کند.

فقط Service Interface فراخوانی شود.


---

12.6 Dependency Injection

تمام سرویس‌ها از Bootstrap تزریق شوند.

مثال:

TelegramRouter

↓

PortfolioService

↓

OptimizerService

↓

TradingService

↓

ReportService


---

12.7 Production Checklist

قبل از انتشار نسخه Production، موارد زیر باید تکمیل باشند:

RBAC کامل

Session Timeout

Audit Log

Security Log

User Stream فعال

KeepAlive خودکار برای ListenKey (هر 60 دقیقه یا کمتر مطابق مستند Toobit)

Retry Policy

Circuit Breaker

Emergency Stop

Health Monitor

Notification Engine

PDF Reports

Chart Generator

Backup & Restore

State Machine

Pagination

Localization (FA/EN)



---

12.8 هم‌راستایی با ساختار فعلی پروژه

بر اساس فایل‌هایی که ارائه کردی:

ExecutionEngine بدون تغییر معماری حفظ شود.

ToobitAdapter فقط نقش Adapter را داشته باشد.

ToobitClient به‌تدریج به Endpointهای v2 و User Stream توسعه یابد.

TradeBlueprint به‌عنوان قرارداد مرکزی اجرای معامله حفظ شود.

IExchangeAdapter تغییر نکند و قابلیت توسعه برای صرافی‌های دیگر را نیز حفظ کند.



---

12.9 قابلیت‌های آینده

معماری پیشنهادی بدون بازطراحی، قابلیت افزودن این امکانات را خواهد داشت:

چند صرافی هم‌زمان

چند حساب معاملاتی

چند مدیر (Multi-Admin)

Web Dashboard

Mobile Dashboard

AI Copilot برای تحلیل معاملات

اتصال به TradingView Webhook

افزونه‌های سفارشی (Plugin System)



---

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 13 — Deployment Strategy, Testing, Migration, Rollback & Production Acceptance

> Version: 1.0
Dependency:

Part 1 تا Part 12





---

13.1 هدف این فاز

این بخش مشخص می‌کند چگونه قابلیت‌های جدید تلگرام بدون ایجاد اختلال در سیستم فعلی به پروژه اضافه شوند.

اصل اساسی:

> No Breaking Changes



هیچ بخش پایدار پروژه نباید برای اضافه کردن Telegram UI مجدداً بازنویسی شود.


---

13.2 مراحل پیاده‌سازی

فازها باید به ترتیب زیر انجام شوند:

Phase 1
Infrastructure

↓

Phase 2
Menu System

↓

Phase 3
Backtest

↓

Phase 4
Paper Trading

↓

Phase 5
Live Trading

↓

Phase 6
Optimizer

↓

Phase 7
Reports

↓

Phase 8
Notifications

↓

Phase 9
Charts

↓

Phase 10
Production Validation

هر فاز باید به‌طور مستقل قابل تست و Rollback باشد.


---

13.3 Migration Strategy

قابلیت‌ها به‌صورت تدریجی جایگزین نسخه فعلی شوند:

Current Bot

↓

Compatibility Layer

↓

New Router

↓

New Menus

↓

Old Commands Removed

تا پایان مهاجرت، دستورات قدیمی (مانند /status) همچنان پشتیبانی شوند.


---

13.4 Feature Flags

تمام قابلیت‌های بزرگ باید با Feature Flag فعال شوند:

ENABLE_NEW_MENU

ENABLE_PAPER

ENABLE_LIVE

ENABLE_OPTIMIZER

ENABLE_REPORTS

ENABLE_CHARTS

ENABLE_NOTIFICATIONS

این امکان خاموش/روشن کردن هر بخش بدون تغییر کد را فراهم می‌کند.


---

13.5 Testing Matrix

برای هر ماژول، تست‌های زیر الزامی است:

Unit Test

Permission Manager

State Machine

Callback Router

Session Manager

Message Builder


Integration Test

Telegram → Application

Application → Execution Engine

Execution → Exchange Adapter


End-to-End Test

Menu

↓

Backtest

↓

Report

↓

Paper Trade

↓

Live Trade

↓

Close Position

↓

Export Report


---

13.6 Failure Scenarios

سیستم باید این موارد را مدیریت کند:

قطع WebSocket

قطع REST

Timeout صرافی

Rate Limit

رد سفارش

Session منقضی‌شده

Callback نامعتبر

دسترسی غیرمجاز

از دست رفتن اتصال اینترنت

ری‌استارت ربات



---

13.7 Rollback Plan

در صورت بروز خطا:

Disable Feature Flag

↓

Restore Previous Menu

↓

Restart Telegram Layer

↓

Keep Trading Engine Running

یعنی خرابی رابط تلگرام نباید باعث توقف موتور معامله‌گری شود.


---

13.8 Production Acceptance Checklist

قبل از انتشار نسخه نهایی، تمام موارد زیر باید تأیید شوند:

منوها بدون بن‌بست (Dead End) قابل پیمایش باشند.

تمام دکمه‌های ⬅ Back به وضعیت صحیح بازگردند.

RBAC برای تمام مسیرها بررسی شود.

هیچ Handler مستقیماً به Exchange یا Vault متصل نباشد.

تمام عملیات حساس در Audit Log ثبت شوند.

اعلان‌های مهم (اتمام Optimization، خطای صرافی، Drawdown شدید و...) ارسال شوند.

نمودارها و گزارش‌ها بدون خطا تولید شوند.

تمام Feature Flagها قابل فعال/غیرفعال کردن باشند.

مصرف حافظه و زمان پاسخ‌گویی در محدوده قابل قبول باقی بماند.



---

13.9 Roadmap آینده

معماری پیشنهادی امکان افزودن این قابلیت‌ها را بدون تغییر اساسی فراهم می‌کند:

پشتیبانی از چند صرافی

چند حساب معاملاتی

چند مدیر با سطوح دسترسی متفاوت

داشبورد وب

اپلیکیشن موبایل

افزونه‌های (Plugin) سفارشی

تحلیل‌گر هوشمند مبتنی بر AI

اتصال به TradingView Webhook

مانیتورینگ توزیع‌شده



---

13.10 نکات نهایی برای تیم پیاده‌سازی

لایه Telegram صرفاً رابط کاربری باقی بماند.

منطق کسب‌وکار فقط در Application و Domain قرار گیرد.

وابستگی‌ها از طریق Dependency Injection مدیریت شوند.

تمام ارتباط با صرافی از مسیر ExecutionEngine → IExchangeAdapter → ToobitAdapter → ToobitClient انجام شود.

هیچ میان‌بری برای فراخوانی مستقیم API صرافی از Handlerها ایجاد نشود.

تمام تغییرات به‌صورت افزایشی (Incremental) و با قابلیت Rollback توسعه یابند.



---

APEX TELEGRAM INTEGRATION BLUEPRINT

Part 14 — Security Architecture, Audit Trail, Recovery, High Availability & Long-Term Maintainability

> Version: 1.0
Dependency:

Part 1 تا Part 13





---

14.1 فلسفه امنیتی

از این مرحله به بعد، ربات تلگرام صرفاً یک رابط کاربری نیست، بلکه درگاه کنترل یک سیستم معاملاتی واقعی است. بنابراین طراحی باید بر پایه‌ی اصل Zero Trust انجام شود.

اصول اصلی:

هیچ کاربری ذاتاً مورد اعتماد نیست.

هر درخواست مجدداً اعتبارسنجی می‌شود.

تمام عملیات حساس ثبت می‌شوند.

هیچ عملیات مالی بدون کنترل چندمرحله‌ای اجرا نمی‌شود.



---

14.2 لایه‌های امنیت

Telegram

↓

Identity Validation

↓

Permission Validation

↓

Session Validation

↓

Operation Validation

↓

Risk Validation

↓

Audit Logger

↓

Application Layer

هیچ مرحله‌ای نباید حذف یا دور زده شود.


---

14.3 سطوح دسترسی

چهار سطح دسترسی پیشنهاد می‌شود:

Owner

اختیارات کامل:

مدیریت کاربران

Live Trading

Optimizer

تنظیمات

Export

Rollback

Emergency Stop

Feature Flags

مشاهده Logها



---

Admin

اختیارات:

مدیریت معاملات

مشاهده گزارش‌ها

اجرای Backtest

اجرای Optimization

مدیریت Paper Trading


اما بدون:

مدیریت Vault

حذف Owner

Factory Reset



---

Analyst

اختیارات:

اجرای Backtest

مشاهده گزارش

مشاهده Portfolio

مشاهده وضعیت سیستم


بدون امکان معامله واقعی.


---

Viewer

فقط:

وضعیت سیستم

گزارش‌های عمومی

نتایج Backtest منتشرشده



---

14.4 Audit Trail

هر عملیات باید ثبت شود.

ساختار پیشنهادی:

Timestamp

User

Role

Chat ID

Command

Parameters

Old State

New State

Result

Duration

IP (در صورت وجود)

Correlation ID


---

14.5 عملیاتی که همیشه Audit می‌شوند

ورود مدیر

تغییر تنظیمات

تغییر Feature Flag

اجرای Optimization

Rollback نسخه

فعال‌سازی Live Trading

غیرفعال‌سازی Live Trading

ارسال سفارش

لغو سفارش

تغییر حد ضرر

تغییر Take Profit

تغییر Leverage

Emergency Stop



---

14.6 Disaster Recovery

در صورت بروز خطا:

Telegram Failure

↓

Restart Telegram

↓

Reconnect Sessions

↓

Reload State

↓

Resume Notifications

اگر Exchange قطع شود:

Exchange Offline

↓

Trading Pause

↓

Retry

↓

Reconnect

↓

Resume


---

14.7 Backup Strategy

به‌صورت زمان‌بندی‌شده از موارد زیر نسخه پشتیبان تهیه شود:

تنظیمات

نسخه‌های Optimizer

گزارش‌ها

تاریخچه معاملات

Audit Log

Feature Flags

وضعیت منوها (در صورت نیاز)



---

14.8 Health Supervision

ماژول پایش باید وضعیت این اجزا را کنترل کند:

Telegram Bot

Router

Session Manager

Notification Service

Optimizer

Execution Engine

Portfolio Engine

Exchange REST

Market WebSocket

User WebSocket

Scheduler


در صورت خرابی هر مورد، هشدار مناسب صادر شود.


---

14.9 Performance Targets

اهداف پیشنهادی:

زمان پاسخ منو: کمتر از ۵۰۰ میلی‌ثانیه

پاسخ Callback: کمتر از ۳۰۰ میلی‌ثانیه

ارسال اعلان: کمتر از ۲ ثانیه

بازیابی اتصال WebSocket: کمتر از ۱۰ ثانیه

استفاده از حافظه پایدار و بدون نشت (Memory Leak)



---

14.10 نگهداری و توسعه

برای حفظ کیفیت پروژه:

هر قابلیت جدید به‌صورت ماژولار اضافه شود.

منطق تجاری از رابط کاربری جدا بماند.

تمام APIهای داخلی مستندسازی شوند.

قبل از انتشار، تست‌های واحد، یکپارچه و انتها‌به‌انتها اجرا شوند.

تغییرات مهم همراه با Migration Plan و Rollback Plan باشند.


---

Institutional Minimal UI Specification

Part 15 — APEX Telegram UI Typography & Formatting Design System

> Version: 1.0
Dependency:



هدف

تمام پیام‌های ربات باید طوری طراحی شوند که:

بسیار حرفه‌ای و سازمانی (Institutional) باشند.

ساده و مینیمال باشند.

در نگاه اول اطلاعات مهم دیده شوند.

از شلوغی جلوگیری شود.

تمام صفحات ظاهر یکسان داشته باشند.

کاربر بدون فکر کردن بتواند اطلاعات را پیدا کند.



---

اصل اول

Information Hierarchy

تمام اطلاعات باید دارای سلسله مراتب باشند.

هر پیام باید دقیقاً شامل این ترتیب باشد:

عنوان

زیرعنوان

اطلاعات اصلی

اطلاعات ثانویه

هشدارها

عملیات

Navigation

نه کمتر نه بیشتر.


---

اصل دوم

فقط یک عنوان اصلی

عنوان صفحه باید:

Bold

در اولین خط

همراه با یک Emoji ثابت


مثلاً:

📊 Backtest

📈 Trading

🧠 Optimization

💼 Portfolio

📁 Report

⚙ Settings

❤ Health

📡 Status

❓ Help

👤 Admin

عنوان نباید بیش از یک خط باشد.


---

اصل سوم

استفاده از Bold

Bold فقط برای موارد زیر:

عنوان صفحه

عنوان هر بخش

نام Symbol

Timeframe

وضعیت Running

وضعیت Error

اعداد مهم

هشدارها


مثلاً:

**Symbol**
BTC

**Timeframe**
1H

نه اینکه کل متن Bold شود.


---

اصل چهارم

هر خط فقط یک مفهوم

اشتباه:

PF:1.6 Sharpe:1.3 Trades:250 WinRate:64%

صحیح:

PF ............ 1.60
Sharpe ........ 1.30
Trades ........ 250
Win Rate ...... 64%


---

اصل پنجم

Alignment

تمام Label ها باید تراز باشند.

مثلاً

Profit
Sharpe
Trades

نه

Profit
Number of trades
PF


---

اصل ششم

فاصله‌ها

بین هر بخش یک خط خالی.

مثلاً

📊 Backtest

Symbol
BTC

Timeframe
1H

Performance

PF
2.31

Sharpe
1.61

نه اینکه همه چیز پشت سر هم نوشته شود.


---

اصل هفتم

استفاده بسیار محدود از Emoji

هر Emoji باید معنی داشته باشد.

مجاز:

📊
📈
📉
⚠
❌
✅
💰
🧠
⚙
📁
📡
❤

غیرمجاز:

🔥🚀🎉💥⭐💫✨

اینها ظاهر پروژه را آماتور می‌کنند.


---

اصل هشتم

رنگ ذهنی

اگرچه تلگرام رنگ متن ندارد، اما با Emoji می‌توان حس رنگ ایجاد کرد.

🟢 فعال

🟡 هشدار

🔴 خطا

🔵 اطلاعات

⚪ خنثی


---

اصل نهم

هشدارها

تمام هشدارها دقیقاً قالب یکسان داشته باشند.

⚠ Warning

Real money will be used.

Please confirm.


---

اصل دهم

Error

هیچ Error نباید فقط یک جمله باشد.

فرمت استاندارد:

❌ Error

Reason
Permission denied

Possible Cause
No access to /proc/stat

Suggested Action
Grant permission

Retry


---

اصل یازدهم

Success

✅ Completed

Optimization finished successfully.


---

اصل دوازدهم

Running

🟢 Running

Optimization is currently executing.


---

اصل سیزدهم

Section Header

هر بخش داخلی Bold باشد.

مثلاً

Performance

Risk

Portfolio

Statistics

Recent Signals


---

اصل چهاردهم

اعداد

تمام اعداد Format شوند.

اشتباه

1.234567891

صحیح

1.23

یا

1.234

برای درصد

12.35%

برای پول

2,341.65 USDT


---

اصل پانزدهم

وضعیت

همیشه با Badge متنی.

Status
🟢 Running

Status
🔴 Stopped

Status
🟡 Waiting


---

اصل شانزدهم

اطلاعات مهم در بالا

همیشه

Symbol

Timeframe

Mode

Status

در ابتدای صفحه باشند.


---

اصل هفدهم

اطلاعات کم اهمیت

پایین صفحه.

مثل

Version

Hash

Created

Updated


---

اصل هجدهم

Separator

فقط در صورت نیاز.

──────────

نه بیشتر.


---

اصل نوزدهم

دکمه‌ها

نام دکمه‌ها همیشه کوتاه باشند.

صحیح

Run

Refresh

Inject

Export

Details

Back

Home

اشتباه

Run Optimization Again

Go Back To Previous Menu

Return Home


---

اصل بیستم

متن دکمه

حداکثر دو کلمه.


---

اصل بیست‌ویکم

عدم تکرار

اگر Symbol در ابتدای صفحه نوشته شده، دوباره وسط صفحه تکرار نشود.


---

اصل بیست‌ودوم

نمایش داده‌ها

ابتدا خلاصه، سپس جزئیات.

Summary

Performance

Risk

Statistics

Logs


---

اصل بیست‌وسوم

نمایش لیست

لیست‌ها شماره‌گذاری یا Bullet استاندارد داشته باشند.

• BTC

• ETH

• SOL


---

اصل بیست‌وچهارم

متن‌ها کوتاه

حداکثر دو یا سه خط.

به‌جای پاراگراف‌های طولانی، اطلاعات به بخش‌های کوچک تقسیم شوند.


---

اصل بیست‌وپنجم

متن‌های ثابت

تمام پیام‌های سیستم باید از یک واژگان استاندارد استفاده کنند.

مثلاً همیشه از یک عبارت ثابت برای وضعیت‌ها استفاده شود:

Running

Stopped

Completed

Failed

Pending

Waiting

Canceled


از مترادف‌های مختلف مانند Done، Finished، Executed و... برای یک مفهوم استفاده نشود.


---

اصل بیست‌وششم

لحن نوشتار

تمام متن‌ها باید:

رسمی

کوتاه

دقیق

بدون جملات احساسی

بدون علائم نگارشی اضافی

بدون ایموجی‌های تزئینی


باشند.


---

اصل بیست‌وهفتم

طراحی واکنش‌گرا برای موبایل

تمام پیام‌ها باید طوری طراحی شوند که بدون اسکرول افقی و بدون شکستن ساختار، روی نمایشگر موبایل به‌خوبی دیده شوند. طول خطوط، تعداد ستون‌ها و میزان اطلاعات هر صفحه باید متناسب با عرض معمول تلگرام روی تلفن همراه باشد.


---

اصل بیست‌وهشتم

الگوی ثابت برای تمام صفحات

تمام صفحات ربات باید دقیقاً از این قالب پیروی کنند:

📊 Title

Context
• Symbol
• Timeframe
• Mode
• Status

Summary

Key Metrics

Actions

Navigation

این قالب نباید بین بخش‌های مختلف تغییر کند؛ تنها محتوای هر قسمت متناسب با صفحه عوض می‌شود.



---

پایان Blueprint

این مجموعه اکنون یک طراحی جامع برای لایه تلگرام، اتصال به صرافی، مدیریت معاملات، گزارش‌گیری، امنیت و استقرار ارائه می‌دهد.

