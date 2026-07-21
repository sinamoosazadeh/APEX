بسیار خوب. اکنون که کد فعلی را دیده‌ام، تصمیمم نسبت به قبل قطعی شده است.

من دیگر یک سند صرفاً تئوری نخواهم نوشت، بلکه یک Optimization Implementation Specification خواهم نوشت که مستقیماً روی همین پروژه سوار می‌شود و هوش مصنوعی بعدی می‌تواند آن را بدون شکستن وابستگی‌های فعلی پیاده‌سازی کند.

اما این سند آن‌قدر بزرگ خواهد بود که در یک پاسخ قابل تولید نیست. بنابراین آن را فصل‌به‌فصل تولید می‌کنم.

APEX Optimization Blueprint

Volume I

Chapter 1

Philosophy, Objectives & System Constitution


---

1. Purpose

این سند مرجع نهایی طراحی و پیاده‌سازی زیرسیستم Optimization پروژه APEX است.

این سند جایگزین هیچ بخشی از پروژه فعلی نیست.

این سند مشخص می‌کند چگونه زیرسیستم موجود باید به نسخه Production-grade ارتقاء پیدا کند.

هدف این سند، ایجاد یک موتور Optimization در سطح Institutional است که بتواند بدون ایجاد کوچک‌ترین ناسازگاری با معماری فعلی پروژه، آن را تکامل دهد.


---

2. Fundamental Principle

Optimization در APEX هرگز به معنی:

افزایش سود

پیدا کردن پارامترهای بهتر

تنظیم وزن‌ها


نیست.

بلکه Optimization یعنی:

> پیدا کردن پایدارترین حالت عملکرد سیستم تحت بیشترین تنوع شرایط بازار.



در نتیجه هدف اصلی:

Maximize Robustness

است نه

Maximize Profit.


---

3. Optimization Philosophy

تمام عملیات Optimization باید بر پایه پنج اصل باشد.

Principle 1

Never optimize for one market.

پارامتری که فقط روی BTC جواب بدهد ولی روی ETH شکست بخورد، مردود است.


---

Principle 2

Never optimize for one timeframe.

اگر پارامتر فقط روی M5 مناسب باشد ولی روی H1 شکست بخورد، مردود است.


---

Principle 3

Never optimize for one historical period.

اگر فقط روی Bull Market خوب باشد، پذیرفته نیست.


---

Principle 4

Never optimize only for Profit.

Net Profit تنها یکی از ده‌ها معیار است.


---

Principle 5

Every optimization must survive validation.

هر نتیجه‌ای که مراحل اعتبارسنجی را رد نکند، حتی اگر سود بسیار بالایی داشته باشد، باید کنار گذاشته شود.


---

4. Definition of Optimization

Optimization در APEX عبارت است از:

جستجوی هوشمند فضای پارامترها به‌منظور یافتن مجموعه‌ای از پارامترها که بیشترین Robustness را تحت مجموعه‌ای از قیود از پیش تعریف‌شده ایجاد کند.


---

5. Architecture Philosophy

Optimization نباید مستقیماً چیزی را تغییر دهد.

Optimization فقط Recommendation تولید می‌کند.

سپس Recommendation اعتبارسنجی می‌شود.

سپس نسخه‌بندی می‌شود.

سپس ذخیره می‌شود.

سپس اجازه انتشار پیدا می‌کند.

سپس در زمان مناسب توسط سیستم Load می‌شود.

در نتیجه هیچ Optimizer مجاز نیست مستقیماً:

Risk Engine

Probability Engine

Decision Engine


را تغییر دهد.

بلکه فقط Parameter Package تولید می‌کند.


---

6. Immutable Rule

Optimizer هیچ پارامتری را مستقیماً داخل حافظه تغییر نمی‌دهد.

بلکه همیشه:

Optimize

↓

Validate

↓

Approve

↓

Version

↓

Store

↓

Inject

را طی می‌کند.


---

7. Levels of Optimization

کل سیستم به پنج سطح تقسیم می‌شود.

Level 0

Static Parameters

پارامترهای ثابت پروژه

هرگز توسط Optimizer تغییر نمی‌کنند.


---

Level 1

Signal Parameters

تمام پارامترهای تولید سیگنال


---

Level 2

Risk Parameters

تمام پارامترهای مدیریت ریسک


---

Level 3

Execution Parameters

تمام پارامترهای ورود و خروج


---

Level 4

Meta Parameters

پارامترهای خود Optimizer


---

8. Optimization Domains

Optimization فقط محدود به وزن Evidenceها نیست.

بلکه شامل:

Signal

Probability

Decision

Risk

Execution

Portfolio

Regime

ICT

Order Flow

Liquidity

Research

Backtest

Monitoring

Governance

خواهد بود.


---

9. Independence

هر Domain مستقل Optimize می‌شود.

سپس نتایج توسط Meta Optimizer ترکیب می‌شوند.


---

10. Never Mix Coins

این اصل بسیار مهم است.

هیچ پارامتری که برای BTC تولید شده است

حق ندارد

برای ETH استفاده شود.

یا بالعکس.


---

هر Coin دارای پایگاه دانش مستقل خواهد بود.

Knowledge Base

BTC

ETH

SOL

BNB

...


---

11. Never Mix Timeframes

همین قانون برای تایم‌فریم نیز برقرار است.

پارامتر تولیدشده برای:

BTC M5

هرگز

نباید روی

BTC H4

اعمال شود.


---

12. Parameter Identity

هر Parameter Package دارای هویت یکتاست.

Coin

Timeframe

Market Regime

Optimizer Version

Blueprint Version

Git Revision

Dataset Hash

Creation Time

Validation Time

Approval Time

Expiration Time

اگر حتی یکی از این موارد تغییر کند، Package جدید ایجاد می‌شود.


---

13. No Global Parameters

در نسخه نهایی پروژه چیزی به نام:

optimized_weights.json

به‌صورت سراسری وجود نخواهد داشت.

بلکه ساختار باید به شکل سلسله‌مراتبی باشد؛ به‌گونه‌ای که پارامترها بر اساس نماد، تایم‌فریم، نسخه و وضعیت بازار نگهداری شوند، نه یک فایل واحد که همه شرایط را با هم مخلوط کند.


---

این پایان فصل اول است.

در فصل دوم، معماری کامل زیرسیستم Optimization را طراحی می‌کنم؛ شامل تمام سرویس‌ها، موتورهای داخلی، جریان داده، قراردادهای بین ماژول‌ها، ساختار پوشه‌ها و نحوه اتصال به پروژه فعلی به‌گونه‌ای که هیچ‌یک از وابستگی‌های موجود شکسته نشود.

APEX Optimization Blueprint

Volume I

Chapter 2

Optimization Architecture Specification


---

2.1 Mission

زیرسیستم Optimization نباید یک فایل یا یک کلاس باشد.

بلکه باید یک Subsystem مستقل در معماری APEX باشد که مانند سایر Engineها دارای چرخه عمر (Lifecycle)، قراردادهای مشخص (Contracts)، مدیریت وضعیت (State Management)، نسخه‌بندی و قابلیت توسعه باشد.

این زیرسیستم مسئول «تصمیم‌گیری» نیست؛ مسئول «بهبود کنترل‌شده تصمیم‌گیری» است.


---

2.2 High-Level Architecture

+-----------------------+
                    |   Telegram Interface  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Optimization Service  |
                    +-----------+-----------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
    +---------------------+          +----------------------+
    | Optimization Queue  |          | Scheduler            |
    +----------+----------+          +----------+-----------+
               |                                |
               +---------------+----------------+
                               |
                               v
                +-------------------------------+
                | Optimization Orchestrator     |
                +---------------+---------------+
                                |
      +-----------+-------------+--------------+------------+
      |           |                            |            |
      v           v                            v            v
+------------+ +------------+          +--------------+ +----------------+
| Signal     | | Risk &     |          | Research     | | Meta Optimizer |
| Optimizer  | | Execution  |          | Optimizer    | |                |
|            | | Optimizer  |          |              | |                |
+------+-----+ +------+-----+          +------+-------+ +--------+-------+
       |               |                       |                 |
       +---------------+-----------+-----------+-----------------+
                                   |
                                   v
                    +-------------------------------+
                    | Validation Pipeline           |
                    +---------------+---------------+
                                    |
                                    v
                    +-------------------------------+
                    | Parameter Repository          |
                    +---------------+---------------+
                                    |
                                    v
                    +-------------------------------+
                    | Injection Manager             |
                    +---------------+---------------+
                                    |
                                    v
              Probability / Decision / Risk / Execution Engines


---

2.3 Architectural Layers

Optimization از شش لایه مستقل تشکیل می‌شود.


---

Layer 1 — Orchestration Layer

وظایف:

مدیریت کل فرآیند

زمان‌بندی

ایجاد Job

بازیابی Job

مدیریت صف

کنترل توقف

کنترل ادامه

مدیریت خطا

اولویت‌بندی


این لایه هیچ الگوریتمی اجرا نمی‌کند.


---

Layer 2 — Optimization Engines

این لایه شامل موتورهای واقعی است.

در نسخه نهایی فقط این موتورها مجاز هستند:

SignalOptimizer

RiskExecutionOptimizer

ResearchOptimizer

PortfolioOptimizer

MetaOptimizer

هیچ Optimizer دیگری خارج از این مجموعه مجاز نیست مگر با ثبت در Blueprint.


---

Layer 3 — Validation Layer

هیچ خروجی مستقیماً پذیرفته نمی‌شود.

تمام خروجی‌ها باید از زنجیره زیر عبور کنند:

Walk Forward

↓

Monte Carlo

↓

Stress Test

↓

Cross Asset Validation

↓

Cross Timeframe Validation

↓

Robustness Score

↓

Acceptance

اگر هر مرحله شکست بخورد:

Parameter Package Reject


---

Layer 4 — Repository Layer

تمام نتایج باید نسخه‌بندی شوند.

هیچ فایل نباید overwrite شود.

هر نسخه Immutable است.


---

Layer 5 — Injection Layer

این لایه تنها لایه‌ای است که اجازه دارد پارامترها را به سیستم تزریق کند.

تمام Engineها فقط از این لایه پارامتر دریافت می‌کنند.


---

Layer 6 — Monitoring Layer

این لایه فقط گزارش تولید می‌کند.

هرگز پارامتری را تغییر نمی‌دهد.


---

2.4 Directory Structure

ساختار پیشنهادی:

src/apex/optimization/

    orchestrator/

        orchestrator.py

        scheduler.py

        queue_manager.py

        lifecycle.py

    signal/

        optimizer.py

        search_space.py

        objective.py

        validator.py

    risk/

        optimizer.py

        stop_optimizer.py

        target_optimizer.py

        sizing_optimizer.py

    research/

        optimizer.py

        walk_forward.py

        monte_carlo.py

        robustness.py

    portfolio/

        optimizer.py

    validation/

        validation_pipeline.py

        acceptance.py

        rejection.py

    repository/

        repository.py

        versioning.py

        parameter_store.py

    injection/

        injector.py

        compatibility.py

    reports/

        report_generator.py

        telegram_formatter.py

    models/

        parameter_package.py

        optimization_job.py

        optimization_result.py

        optimization_metrics.py

        optimization_state.py

    tests/


---

2.5 Migration Strategy

بر اساس ممیزی کد فعلی، حذف فایل‌های موجود توصیه نمی‌شود.

مهاجرت باید به این صورت باشد:

فایل فعلی

src/apex/optimizers/meta_optimizer.py

↓

به

Optimization Orchestrator

ارتقا پیدا کند.


---

فایل فعلی

optimizer_suite.py

↓

به

Research Optimizer

تبدیل شود.

این فایل نباید مستقیماً تصمیم معاملاتی تولید کند.

بلکه فقط خروجی‌های تحقیقاتی و نتایج بهینه‌سازی تولید کند.


---

kernel.py

Hook فعلی:

optimized_params

حفظ شود.

اما منبع آن دیگر یک دیکشنری ساده نباشد.

بلکه از:

Injection Manager

تأمین شود.

در نتیجه API بیرونی تغییر نکند و وابستگی‌های فعلی پروژه شکسته نشوند.


---

2.6 Optimization Job Lifecycle

هر عملیات بهینه‌سازی باید یک Job مستقل باشد.

چرخه عمر استاندارد:

Created

↓

Queued

↓

Scheduled

↓

Running

↓

Paused

↓

Resumed

↓

Validation

↓

Approved

↓

Stored

↓

Injected

↓

Archived

هر وضعیت باید دارای زمان ثبت، شناسه یکتا و علت تغییر وضعیت باشد.


---

2.7 Parameter Package

هیچ Optimizer مجاز به بازگرداندن dict خام نیست.

همه خروجی‌ها باید در قالب یک شیء استاندارد مانند ParameterPackage تولید شوند که شامل مواردی مانند:

شناسه یکتا

نسخه

نماد

تایم‌فریم

نوع بازار

پارامترها

معیارهای اعتبارسنجی

امضای داده (Dataset Hash)

تاریخ ایجاد و انقضا


باشد.


---

2.8 Design Principles

در تمام اجزای این زیرسیستم رعایت این اصول الزامی است:

Stateless تا حد امکان.

Immutable بودن خروجی‌ها.

Versioned بودن هر بسته پارامتر.

عدم بازنویسی نسخه‌های قبلی.

قابلیت Rollback.

ثبت کامل Log و Audit Trail.

جداسازی کامل منطق تحقیق (Research) از منطق عملیاتی (Production).



---

پیش از ادامه یک نکته مهم: برخی فایل‌هایی که قبلاً در این گفتگو بارگذاری شده بودند، اکنون منقضی شده‌اند و اگر در فصل‌های بعد لازم باشد دوباره به آن‌ها استناد کنم، باید مجدداً بارگذاری شوند.

در Chapter 3 وارد طراحی کامل Signal Optimizer خواهیم شد؛ شامل فضای جستجو، پارامترهای قابل بهینه‌سازی، قراردادهای API، ساختار داده‌ها، الگوریتم‌ها و نحوه اتصال آن به موتورهای Probability و Decision.

APEX Optimization Blueprint

Volume I

Chapter 3

Signal Optimizer Specification


---

3.1 Mission

Signal Optimizer مسئول «بهینه‌سازی منطق تولید سیگنال» است.

این موتور:

معامله انجام نمی‌دهد.

حد سود تعیین نمی‌کند.

حد ضرر تعیین نمی‌کند.

حجم معامله تعیین نمی‌کند.


بلکه فقط بهترین پارامترهایی را پیدا می‌کند که کیفیت تولید سیگنال را افزایش دهند.

هدف آن افزایش Profit نیست؛ هدف آن افزایش کیفیت تصمیم اولیه است.


---

3.2 Responsibilities

این موتور فقط مجاز است پارامترهای مرتبط با مراحل زیر را تغییر دهد:

Market Data

↓

Indicators

↓

Pattern Detection

↓

Structure Detection

↓

Liquidity Detection

↓

ICT Detection

↓

Evidence Generation

↓

Probability Engine

↓

Decision Threshold

↓

Signal

هر چیزی بعد از Signal متعلق به Risk & Execution Optimizer است.


---

3.3 Scope of Optimization

تمام پارامترهای قابل تنظیم باید در گروه‌های مستقل دسته‌بندی شوند.

Group A — Indicator Parameters

نمونه‌ها:

EMA Length

SMA Length

WMA Length

ATR Length

ATR Multiplier

RSI Length

RSI Smoothing

MACD Fast

MACD Slow

MACD Signal

ADX Length

Bollinger Length

Bollinger StdDev

SuperTrend Length

SuperTrend Factor

VWAP Settings


هر اندیکاتور جدید نیز باید از همین قرارداد تبعیت کند.


---

Group B — Candlestick Parameters

تمام آستانه‌های تشخیص الگوها:

Body Ratio

Shadow Ratio

Gap Threshold

Engulf Threshold

Doji Threshold

Hammer Threshold

Harami Threshold

Morning Star Rules

Evening Star Rules


و هر Pattern دیگر.


---

Group C — Structure Parameters

نمونه‌ها:

Pivot Left

Pivot Right

Swing Sensitivity

BOS Confirmation

CHOCH Confirmation

Structure Window

Trend Confirmation Depth

Break Buffer



---

Group D — Liquidity Parameters

پارامترهای مرتبط با:

Equal High

Equal Low

Liquidity Sweep

Internal Liquidity

External Liquidity

Buy Side Liquidity

Sell Side Liquidity

Stop Hunt Buffer



---

Group E — ICT Parameters

تمام پارامترهای مرتبط با:

Fair Value Gap

Order Block

Breaker Block

Mitigation Block

Inversion FVG

Premium / Discount

Optimal Trade Entry

Balanced Price Range



---

Group F — Evidence Parameters

هر Evidence باید مستقل تنظیم شود.

مثلاً:

Momentum

Structure

Volume

Liquidity

Order Flow

ICT

SMT

Regime

Volatility

Pattern

Trend

Session

Time


---

Group G — Probability Parameters

شامل:

Evidence Weights

Bayesian Prior

Confidence Threshold

Minimum Probability

Calibration Curves

Decision Threshold



---

3.4 Search Space

هر پارامتر باید دارای مشخصات کامل باشد:

نام

نوع

حداقل مقدار

حداکثر مقدار

مقدار پیش‌فرض

گام تغییر

روش نمونه‌برداری (خطی، لگاریتمی، گسسته و ...)

وابستگی‌ها

محدودیت‌ها


هیچ پارامتری نباید به‌صورت «عدد جادویی» در کد باقی بماند.


---

3.5 Dependency Graph

پارامترها مستقل نیستند.

برای مثال:

ATR Length

↓

ATR Value

↓

Stop Width

↓

Risk

↓

Expectancy

بنابراین Optimizer باید وابستگی‌ها را در نظر بگیرد و از ترکیب‌های ناسازگار جلوگیری کند.


---

3.6 Search Strategy

موتور نباید فقط یک الگوریتم جستجو داشته باشد.

باید از یک چارچوب قابل توسعه استفاده کند که امکان انتخاب یا ترکیب روش‌های مختلف را فراهم کند، مانند:

Random Search

Bayesian Optimization

Evolutionary / Genetic Algorithms

CMA-ES

Particle Swarm (در صورت نیاز)

Grid Search برای مجموعه‌های کوچک


انتخاب روش باید بر اساس اندازه فضای جستجو و هزینه ارزیابی انجام شود، نه به‌صورت ثابت.


---

3.7 Objective Function

هدف فقط بیشینه کردن سود نیست.

تابع هدف باید چندمعیاره (Multi-objective) باشد و ترکیبی از معیارهای زیر را ارزیابی کند:

Expectancy

Profit Factor

Sharpe Ratio

Sortino Ratio

Calmar Ratio

Recovery Factor

Maximum Drawdown

Win Rate

Average R Multiple

Trade Stability

Number of Trades

Equity Curve Smoothness

Robustness Score


وزن این معیارها نیز باید قابل تنظیم و نسخه‌بندی باشد.


---

3.8 Validation Pipeline

هر نتیجه باید حداقل مراحل زیر را طی کند:

1. In-sample Optimization


2. Out-of-sample Test


3. Walk-Forward Validation


4. Monte Carlo Simulation


5. Cross-Timeframe Validation


6. Cross-Regime Validation


7. Stability Analysis



در صورت شکست در هر مرحله، بسته پارامتر رد می‌شود.


---

3.9 Coin Isolation

بهینه‌سازی برای هر نماد مستقل است.

برای مثال:

BTC

ETH

SOL

BNB

XRP

...


هر کدام فضای پارامتر و نتایج مستقل دارند.

هیچ نتیجه‌ای نباید بین نمادها به اشتراک گذاشته شود، مگر در قالب یک مدل عمومی که به‌طور جداگانه اعتبارسنجی شده باشد.


---

3.10 Timeframe Isolation

برای هر تایم‌فریم نیز مجموعه پارامتر مستقل نگهداری می‌شود.

به‌عنوان نمونه:

BTC
 ├── 1m
 ├── 5m
 ├── 15m
 ├── 1h
 ├── 4h
 └── 1d

هر شاخه نسخه‌ها و تاریخچه مستقل خود را دارد.


---

3.11 Output Contract

Signal Optimizer نباید فقط یک دیکشنری از پارامترها تولید کند.

خروجی باید شامل موارد زیر باشد:

Parameter Package

نسخه

تاریخ ایجاد

محدوده داده آموزشی

محدوده داده اعتبارسنجی

معیارهای عملکرد

نتایج آزمون‌های پایداری

دلایل پذیرش یا رد

وضعیت اعتبار (Approved / Rejected / Experimental)



---

3.12 Acceptance Criteria

یک بسته پارامتر تنها زمانی قابل انتشار است که:

تمام آزمون‌های اعتبارسنجی را پشت سر گذاشته باشد.

نسبت به نسخه فعال، بهبود معنادار و پایدار نشان دهد.

موجب کاهش غیرقابل‌قبول تعداد معاملات یا افزایش ریسک نشده باشد.

در آزمون‌های برون‌نمونه (Out-of-sample) عملکرد قابل قبول داشته باشد.

قابلیت بازگشت (Rollback) به نسخه قبلی حفظ شود.



---

این فصل مشخص می‌کند که Signal Optimizer فقط مسئول کیفیت تولید سیگنال است و هیچ تغییری در مدیریت ریسک یا اجرای معامله اعمال نمی‌کند. این جداسازی باعث می‌شود مسئولیت‌ها شفاف بمانند و هر زیرسیستم بتواند مستقل ارزیابی و بهینه‌سازی شود.

در فصل بعد، طراحی کامل Risk & Execution Optimizer ارائه می‌شود؛ شامل بهینه‌سازی حد ضرر، حد سود چندمرحله‌ای، اندازه موقعیت، اهرم، مدل‌های خروج، مدیریت ریسک پویا و نحوه تزریق نتایج به موتور اجرای معاملات.

APEX Optimization Blueprint

Volume I

Chapter 4

Risk & Execution Optimizer Specification


---

4.1 Mission

Risk & Execution Optimizer دومین موتور اصلی زیرسیستم Optimization است.

این موتور هیچ سیگنالی تولید نمی‌کند.

سیگنال قبلاً توسط Pipeline اصلی پروژه تولید شده است.

وظیفه این موتور فقط پاسخ به سؤال زیر است:

> «با فرض اینکه این سیگنال صحیح است، بهترین روش اجرای آن چیست؟»



بنابراین این موتور مسئول افزایش کیفیت Execution است، نه افزایش کیفیت Prediction.


---

4.2 Responsibilities

این موتور تنها مجاز به بهینه‌سازی موارد زیر است:

Entry Model

Entry Timing

Position Size

Initial Stop Loss

Dynamic Stop Loss

Multi-Level Take Profit

Partial Exit

Break-Even Logic

Trailing Logic

Time Exit

Emergency Exit

Portfolio Exposure

Leverage

Risk Budget


هیچ پارامتر مربوط به تولید سیگنال نباید در این موتور تغییر کند.


---

4.3 Optimization Domains

این موتور از هشت زیرموتور مستقل تشکیل می‌شود.

Entry Optimizer

↓

Stop Optimizer

↓

Target Optimizer

↓

Position Sizing Optimizer

↓

Leverage Optimizer

↓

Exit Optimizer

↓

Portfolio Risk Optimizer

↓

Execution Validator

هر زیرموتور باید مستقل تست و نسخه‌بندی شود.


---

4.4 Entry Optimizer

این بخش تعیین می‌کند که ورود چگونه انجام شود.

مدل‌های قابل انتخاب:

Market Entry

Limit Entry

Pullback Entry

Liquidity Retest Entry

Order Block Entry

Fair Value Gap Entry

Breakout Entry

Confirmation Entry

Hybrid Entry


Optimizer باید بهترین مدل را برای هر نماد و تایم‌فریم انتخاب کند.


---

4.5 Stop Optimizer

این بخش فقط مسئول تعیین حد ضرر است.

مدل‌های قابل پشتیبانی:

ATR Stop

Structure Stop

Swing Stop

Liquidity Stop

Volatility Stop

OrderBlock Stop

FVG Stop

Hybrid Stop


---

هر مدل باید پارامترهای مستقل خود را داشته باشد.

مثلاً:

ATR Period

ATR Multiplier

Buffer

Swing Depth

Liquidity Offset

Minimum Distance

Maximum Distance

Adaptive Multiplier


---

4.6 Dynamic Stop Engine

حد ضرر نباید ثابت باشد.

سیستم باید بتواند:

Initial Stop

↓

Break Even

↓

ATR Trail

↓

Structure Trail

↓

Liquidity Trail

↓

Emergency Trail

را مدیریت کند.


---

4.7 Target Optimizer

هدف این موتور یافتن بهترین ساختار خروج است.

حداقل باید مدل‌های زیر وجود داشته باشند.

Fixed RR

ATR Target

Liquidity Target

Order Block Target

Structure Target

Dynamic Projection

Hybrid Target


---

4.8 Multi-Level Take Profit

سیستم نباید فقط یک TP داشته باشد.

نسخه Production باید از خروج چندمرحله‌ای پشتیبانی کند.

نمونه:

TP1

Close 30%

TP2

Close 30%

TP3

Close 20%

TP4

Close 20%

تعداد مراحل باید قابل تنظیم باشد.


---

4.9 Exit Strategy Library

تمام مدل‌های خروج باید قابل انتخاب باشند.

از جمله:

Fixed Exit

Trailing Exit

Time Exit

Volatility Exit

Liquidity Exit

Probability Exit

Risk Exit

Hybrid Exit

Optimizer باید بهترین ترکیب را انتخاب کند.


---

4.10 Position Sizing Optimizer

این بخش یکی از مهم‌ترین اجزای پروژه است.

اندازه موقعیت نباید ثابت باشد.

روش‌های قابل پشتیبانی:

Fixed Size

Fixed Risk

Kelly

Half Kelly

Fractional Kelly

ATR Adjusted

Volatility Adjusted

Confidence Adjusted

Portfolio Adjusted

Adaptive Hybrid


---

هر روش باید مستقل اعتبارسنجی شود.


---

4.11 Kelly Engine

در صورت استفاده از Kelly باید محدودیت‌های زیر اعمال شود.

Kelly

↓

Maximum Kelly Cap

↓

Half Kelly

↓

Confidence Scaling

↓

Drawdown Scaling

↓

Exposure Scaling

استفاده مستقیم از Kelly کامل مجاز نیست.


---

4.12 Leverage Optimizer

در بازار Futures، اهرم نیز باید بهینه شود.

پارامترهای قابل بررسی:

Minimum Leverage

Maximum Leverage

ATR Scaling

Drawdown Scaling

Confidence Scaling

Exchange Limits

Liquidation Buffer


اهرم باید به گونه‌ای انتخاب شود که احتمال لیکویید شدن به حداقل برسد.


---

4.13 Portfolio Risk Optimizer

این موتور نباید فقط معامله جاری را ببیند.

باید وضعیت کل پرتفوی را نیز بررسی کند.

نمونه محدودیت‌ها:

Maximum Open Positions

Maximum Sector Exposure

Maximum Correlation

Maximum Daily Loss

Maximum Weekly Loss

Maximum Symbol Exposure

Maximum Timeframe Exposure



---

4.14 Risk Budget

هر معامله باید از بودجه ریسک استفاده کند.

بودجه ریسک بر اساس:

سرمایه

Drawdown فعلی

وضعیت بازار

کیفیت سیگنال

نوسان

تعداد معاملات باز


محاسبه می‌شود.


---

4.15 Execution Validator

قبل از صدور Blueprint نهایی باید بررسی شود:

آیا فاصله Stop منطقی است؟

آیا RR حداقل قابل قبول را دارد؟

آیا حجم با محدودیت سرمایه سازگار است؟

آیا اهرم مجاز است؟

آیا محدودیت‌های صرافی رعایت شده‌اند؟

آیا محدودیت‌های پرتفوی رعایت شده‌اند؟


در صورت شکست هر مورد، معامله رد یا اصلاح می‌شود.


---

4.16 Trade Blueprint

خروجی این موتور باید یک شیء استاندارد باشد.

این شیء حداقل شامل:

Entry Model

Entry Price

Entry Conditions

Stop Model

Stop Price

Dynamic Stop Rules

Target Models

Target Prices

Partial Exit Rules

Position Size

Risk Budget

Leverage

Portfolio Constraints

Expected R

Expected Holding Time

Metadata


باشد.


---

4.17 Coin Isolation

مانند Signal Optimizer، هیچ پارامتر Risk نباید بین دارایی‌ها مشترک باشد.

برای مثال:

BTC

↓

Risk Package

ETH

↓

Risk Package

SOL

↓

Risk Package

همگی باید مستقل باشند.


---

4.18 Timeframe Isolation

پارامترهای اجرای معاملات نیز باید برای هر تایم‌فریم مستقل ذخیره شوند.


---

4.19 Continuous Learning

هر معامله بسته‌شده باید به پایگاه دانش ارسال شود.

اطلاعاتی مانند:

کیفیت ورود

کیفیت خروج

فاصله Stop

میزان لغزش (Slippage)

زمان نگهداری

نتیجه نهایی


ثبت می‌شود تا در بهینه‌سازی‌های بعدی استفاده گردد.


---

4.20 Acceptance Criteria

یک بسته جدید Risk & Execution فقط زمانی قابل انتشار است که:

تمام آزمون‌های اعتبارسنجی را با موفقیت طی کرده باشد.

نسبت به نسخه فعال، بهبود پایدار نشان دهد.

موجب افزایش غیرقابل‌قبول Drawdown یا ریسک نشود.

در آزمون‌های برون‌نمونه نیز عملکرد مناسب داشته باشد.

امکان بازگشت (Rollback) به نسخه قبلی حفظ شود.



---

پایان Chapter 4

در Chapter 5 طراحی کامل Research Optimizer آغاز خواهد شد؛ بخشی که هسته علمی سیستم است و شامل Walk-Forward Optimization، Monte Carlo، Cross-Validation، Multi-Objective Optimization، تحلیل پایداری، کشف Overfitting و تولید نسخه‌های قابل انتشار برای موتورهای Signal و Risk خواهد بود.

# APEX Optimization Blueprint
## Part 5 — Signal Optimizer (Complete Specification)

---

# Mission

Signal Optimizer مسئول بهینه‌سازی کل لایه تولید سیگنال است.

این ماژول **هیچ وظیفه‌ای در مدیریت معامله، حد ضرر، حد سود، اندازه پوزیشن، مدیریت سرمایه یا اجرای سفارش ندارد.**

تنها وظیفه آن، یافتن بهترین مجموعه پارامترهایی است که باعث تولید دقیق‌ترین، پایدارترین و قابل‌اعتمادترین سیگنال‌ها می‌شوند.

به عبارت دیگر:

Market Data │ ▼ All Analysis Engines │ ▼ Evidence │ ▼ Probability Engine │ ▼ Signal Optimizer │ ▼ Optimized Decision │ ▼ Decision

Risk & Execution Optimizer بعد از این مرحله وارد عمل می‌شود.

---

# Scope

Signal Optimizer باید بتواند تمامی پارامترهای موثر در تولید سیگنال را بهینه کند.

نه فقط اندیکاتورها.

بلکه کل Decision Pipeline.

از جمله:

- Indicator Parameters
- Probability Parameters
- Confidence Parameters
- Evidence Weights
- Evidence Thresholds
- ICT Detection Parameters
- Liquidity Detection Parameters
- Market Structure Parameters
- SMT Parameters
- Session Filters
- Volatility Filters
- Trend Filters
- Momentum Filters
- Confirmation Filters
- Noise Filters
- Multi Timeframe Rules
- Regime Detection Parameters
- Adaptive Thresholds
- Entry Validation Rules
- Pattern Detection Parameters
- Timing Parameters
- Lookback Windows
- ATR Multipliers (صرفاً برای اعتبارسنجی سیگنال، نه مدیریت ریسک)
- Swing Detection Parameters
- BOS/CHOCH Parameters
- Order Block Parameters
- Fair Value Gap Parameters
- Liquidity Sweep Parameters
- Volume Filters
- Delta Filters
- Imbalance Detection Parameters

و هر پارامتر دیگری که مستقیماً بر کیفیت تولید سیگنال اثر می‌گذارد.

---

# Dynamic Parameter Discovery

Optimizer هرگز نباید Search Space را به صورت Hardcode تعریف کند.

هر Engine موظف است Interface زیر را پیاده‌سازی نماید:

```python
get_optimizable_parameters()

و لیست کامل پارامترهای قابل بهینه‌سازی خود را بازگرداند.

نمونه:

Parameter(
    name="ema_fast",
    type=int,
    min=5,
    max=50,
    default=20
)

یا

Parameter(
    name="probability_threshold",
    type=float,
    min=0.50,
    max=0.95,
    step=0.01
)

به این ترتیب با اضافه شدن Engineهای جدید، Optimizer بدون تغییر در کد خود قادر به شناسایی و بهینه‌سازی آن‌ها خواهد بود.


---

Search Strategy

فرآیند بهینه‌سازی باید به صورت چندمرحله‌ای انجام شود:

Phase 1 Random Exploration

↓

Phase 2 Latin Hypercube Sampling

↓

Phase 3 Bayesian Optimization (Optuna TPE)

↓

Phase 4 Local Refinement

↓

Phase 5 Sensitivity Analysis

↓

Phase 6 Stability Analysis

↓

Phase 7 Walk Forward Validation

↓

Phase 8 Rolling Window Validation

↓

Phase 9 Monte Carlo Validation

↓

Phase 10 Final Ranking

هیچ مرحله‌ای نباید حذف یا ادغام شود.


---

Objective Function

هدف صرفاً افزایش سود نیست.

Objective باید چندهدفه (Multi-objective) باشد.

مواردی که باید همزمان بیشینه شوند:

Expectancy

Net Profit

Profit Factor

Sharpe Ratio

Sortino Ratio

Calmar Ratio

Recovery Factor

Win Rate

Average Trade

Consistency

Stability Score

Out-of-Sample Performance


در کنار آن، موارد زیر باید به عنوان Penalty لحاظ شوند:

Max Drawdown

Large Losing Streak

Excessive Variance

Overfitting

Parameter Instability

Low Trade Count

High Equity Volatility

Poor Walk-Forward Result

Poor Monte Carlo Result



---

Validation Protocol

هیچ پارامتری تنها بر اساس یک Backtest پذیرفته نمی‌شود.

هر Candidate باید مراحل زیر را با موفقیت طی کند:

1. Full History Backtest


2. Walk Forward Validation


3. Rolling Window Validation


4. Expanding Window Validation


5. Monte Carlo Resampling


6. Sensitivity Analysis


7. Stability Analysis



در صورت شکست در هر مرحله، Candidate رد می‌شود.


---

Symbol & Timeframe Isolation

نتایج هر بهینه‌سازی باید کاملاً مستقل ذخیره شوند.

هر Symbol و هر Timeframe دارای فایل اختصاصی خود است.

نمونه:

BTCUSDT_1m_signal.json
BTCUSDT_5m_signal.json
BTCUSDT_15m_signal.json
BTCUSDT_1h_signal.json

ETHUSDT_15m_signal.json

SOLUSDT_4h_signal.json

هیچ فایل Shared یا Global مجاز نیست.

پارامترهای بهینه BTC فقط برای BTC قابل استفاده هستند.

پارامترهای تایم‌فریم 5 دقیقه فقط برای همان تایم‌فریم معتبر هستند.

هرگونه استفاده متقاطع بین Symbolها یا Timeframeها ممنوع است.


---

Output Specification

هر خروجی باید شامل موارد زیر باشد:

Optimized Parameters

Engine Versions

Optimization Timestamp

Dataset Information

Symbol

Timeframe

Optimization Method

Number of Trials

Objective Values

Validation Scores

Stability Score

Confidence Score

Walk-Forward Result

Monte Carlo Result

Sensitivity Report

Parameter Importance Ranking

SHA256 Hash

Version Number

Digital Signature (در صورت فعال بودن)



---

Acceptance Criteria

یک نتیجه تنها زمانی معتبر است که:

تمامی مراحل اعتبارسنجی را با موفقیت پشت سر گذاشته باشد.

نسبت به نسخه قبلی بهبود معنادار آماری داشته باشد.

از نظر پایداری قابل قبول باشد.

دچار Overfitting نباشد.

برای همان Symbol و Timeframe تولید شده باشد.

قابلیت بارگذاری خودکار توسط سیستم را داشته باشد.


در غیر این صورت، نسخه قبلی باید حفظ شود و نتیجه جدید کنار گذاشته شود.

# APEX Optimization Blueprint
## Part 6 — Risk & Execution Optimizer (Complete Specification)

---

# Mission

Risk & Execution Optimizer دومین بخش اصلی سیستم Optimization است.

برخلاف Signal Optimizer که وظیفه آن یافتن بهترین پارامترهای تولید سیگنال است، این ماژول مسئول بهینه‌سازی کل فرآیند ورود، خروج، مدیریت ریسک، مدیریت معامله و اجرای سفارش است.

این ماژول هرگز حق تغییر Probability یا Evidence یا Logic تولید سیگنال را ندارد.

ورودی آن فقط Decision نهایی است.

```
Market Data
        │
        ▼
Analysis Engines
        │
        ▼
Probability Engine
        │
        ▼
Decision Engine
        │
        ▼
Signal Optimizer Result
        │
        ▼
Decision (Approved)
        │
        ▼
Risk & Execution Optimizer
        │
        ▼
Trade Blueprint
        │
        ▼
Execution Layer
```

---

# Primary Responsibilities

این ماژول مسئول تعیین موارد زیر است:

- Entry Model
- Entry Timing
- Entry Offset
- Stop Loss
- Stop Model
- Number of Stop Levels
- Take Profit Levels
- TP Allocation
- Trailing Logic
- Break Even Logic
- Position Size
- Kelly Fraction
- Portfolio Risk
- Daily Risk
- Weekly Risk
- Maximum Exposure
- Correlation Control
- Pyramid Rules
- Scale In
- Scale Out
- Partial Exit
- Kill Switch
- Trade Validation
- Order Type
- Slippage Protection
- Liquidity Protection
- Execution Timing
- Re-entry Rules

هیچ بخش دیگری نباید این تصمیمات را بگیرد.

---

# Input Sources

Risk Optimizer باید اطلاعات خود را از تمام بخش‌های زیر دریافت کند.

Decision

Probability Report

Evidence Report

Market Structure

ICT Engine

Liquidity Engine

Market Regime

ATR Engine

Volatility Engine

Session Engine

Portfolio State

Account State

Open Positions

Correlation Matrix

Historical Performance

Execution Statistics

Broker Information

Exchange Limits

Order Book Snapshot

Latency Monitor

Spread Monitor

Funding Rate

Open Interest

تمام این اطلاعات باید به صورت Immutable دریافت شوند.

---

# Dynamic Optimization Philosophy

هیچ مقدار ثابتی نباید داخل کد وجود داشته باشد.

مثلاً:

```
SL = ATR × 2
```

غیرقابل قبول است.

در عوض:

```
Optimizer
↓

Best ATR Multiplier

↓

Runtime Injection
```

یا

```
Structure Stop

Liquidity Stop

Hybrid Stop

Volatility Stop

Adaptive Stop
```

Optimizer بهترین مدل را انتخاب می‌کند.

---

# Stop Loss Models

حداقل مدل‌های زیر باید وجود داشته باشند.

ATR Stop

Structure Stop

Swing Stop

Liquidity Stop

ICT Stop

Volatility Stop

Session Stop

Hybrid Stop

Adaptive Stop

Dynamic Stop

AI Selected Stop

Optimizer موظف است بهترین مدل را انتخاب کند.

---

# Take Profit Models

Fixed RR

Liquidity Target

ICT Target

Order Block Target

Fair Value Gap Target

Swing Target

ATR Projection

Volatility Projection

Adaptive Projection

Hybrid Projection

Multiple Projection

---

# Multi-Level TP

سیستم باید از TP چندمرحله‌ای پشتیبانی کند.

نمونه:

```
TP1
TP2
TP3
TP4
TP5
```

هر TP دارای:

- درصد حجم
- دلیل انتخاب
- Expected RR
- Expected Probability

باشد.

---

# Position Sizing Models

Fixed Risk

ATR Risk

Volatility Risk

Kelly

Half Kelly

Fractional Kelly

Drawdown Adjusted

Confidence Adjusted

Probability Adjusted

Portfolio Adjusted

Correlation Adjusted

Hybrid Position Size

Adaptive Position Size

Optimizer بهترین مدل را انتخاب می‌کند.

---

# Portfolio Risk

باید همزمان موارد زیر کنترل شوند.

Maximum Daily Risk

Maximum Weekly Risk

Maximum Monthly Risk

Maximum Symbol Exposure

Maximum Sector Exposure

Maximum Correlation

Maximum Simultaneous Trades

Maximum Floating Drawdown

Maximum Consecutive Losses

Maximum Margin Usage

Maximum Leverage

---

# Execution Models

Market

Limit

Post Only

IOC

FOK

TWAP

VWAP

Iceberg

Adaptive Execution

Liquidity Sensitive Execution

Spread Aware Execution

Latency Aware Execution

---

# Adaptive Runtime

در زمان اجرا Optimizer باید بتواند بسته به شرایط بازار مدل مناسب را انتخاب کند.

مثال:

رنج

↓

Liquidity TP

ترند

↓

Structure TP

نوسان شدید

↓

ATR Stop

خبر

↓

Volatility Stop

Session Open

↓

Conservative Execution

Session Close

↓

Fast Exit

---

# Symbol Isolation

تمام نتایج باید جداگانه ذخیره شوند.

```
BTCUSDT_1m_execution.json

BTCUSDT_5m_execution.json

BTCUSDT_1h_execution.json

ETHUSDT_15m_execution.json

SOLUSDT_4h_execution.json
```

هیچ فایل مشترکی مجاز نیست.

---

# Timeframe Isolation

تنظیمات هر تایم‌فریم فقط برای همان تایم‌فریم معتبر است.

پارامترهای 1m

نباید

روی 4h

استفاده شوند.

---

# Coin Isolation

پارامترهای BTC

هرگز

برای ETH

استفاده نمی‌شوند.

پارامترهای ETH

هرگز

برای SOL

استفاده نمی‌شوند.

Optimizer باید همیشه Symbol را کنترل کند.

---

# Runtime Injection

در Startup

Execution Optimizer

آخرین نسخه معتبر فایل مربوط به همان Symbol و Timeframe را بارگذاری می‌کند.

اگر فایل وجود نداشت:

از نسخه Default استفاده می‌شود.

اگر فایل خراب بود:

آخرین نسخه معتبر Restore می‌شود.

---

# Validation

قبل از ذخیره هر نسخه جدید باید:

Full Backtest

Walk Forward

Rolling Window

Monte Carlo

Stress Test

Sensitivity Test

Execution Simulation

Latency Simulation

Slippage Simulation

Portfolio Simulation

همگی موفق باشند.

در غیر این صورت فایل ذخیره نمی‌شود.

---

# Output Files

هر خروجی باید شامل:

Execution Parameters

Stop Models

TP Models

Position Size Models

Risk Limits

Validation Results

Optimization History

Version

Timestamp

Hash

Compatibility Version

Rollback Version

باشد.

---

# Acceptance Criteria

یک نسخه جدید فقط زمانی پذیرفته می‌شود که:

- نسبت به نسخه قبلی بهبود معنادار داشته باشد.
- در تمام تست‌ها موفق باشد.
- موجب افزایش ریسک سیستم نشود.
- قابلیت Rollback داشته باشد.
- با نسخه فعلی پروژه سازگار باشد.
- برای همان Symbol و همان Timeframe تولید شده باشد.
- بدون تغییر در سایر بخش‌های پروژه قابل تزریق باشد.

---

**ادامه در Part 7: Optimization Orchestrator, Scheduling, Persistence, Versioning, Dependency Injection و چرخه کامل اجرای هر دو Optimizer.**

# APEX Optimization Blueprint
## Part 7 — Optimization Orchestrator, Scheduling, Persistence, Lifecycle & Dependency Injection

---

# Mission

Optimization نباید صرفاً مجموعه‌ای از دو Optimizer مستقل باشد.

کل سیستم باید توسط یک **Optimization Orchestrator** مرکزی مدیریت شود تا تمام فرآیندهای بهینه‌سازی، اعتبارسنجی، زمان‌بندی، ذخیره‌سازی، بارگذاری، نسخه‌بندی، Rollback و تزریق پارامترها به‌صورت هماهنگ انجام شوند.

این Orchestrator تنها نقطه کنترل چرخه حیات (Lifecycle) تمام عملیات Optimization است.

---

# High-Level Architecture

```
Optimization Orchestrator
│
├── Signal Optimizer
│
├── Risk & Execution Optimizer
│
├── Scheduler
│
├── Queue Manager
│
├── Validation Pipeline
│
├── Persistence Manager
│
├── Version Manager
│
├── Rollback Manager
│
├── Runtime Injector
│
├── Health Monitor
│
├── Dependency Manager
│
└── Telegram Integration
```

هیچ Optimizer مجاز نیست مستقیماً فایل ذخیره کند یا پارامترها را وارد Runtime نماید.

---

# Responsibilities

Orchestrator مسئول موارد زیر است:

- ایجاد Job
- صف‌بندی Jobها
- اولویت‌بندی
- زمان‌بندی
- جلوگیری از اجرای همزمان ناسازگار
- مدیریت منابع CPU/RAM
- اجرای Validation
- ذخیره نسخه جدید
- مدیریت نسخه‌ها
- Rollback
- تزریق پارامترها
- گزارش‌گیری
- مانیتورینگ سلامت

---

# Optimization Queue

تمام درخواست‌ها ابتدا وارد Queue می‌شوند.

هر Job شامل:

```
Job ID
Symbol
Timeframe
Optimizer Type
Priority
Creation Time
Estimated Runtime
Retry Count
Status
```

Statusها:

```
Pending
Waiting
Running
Paused
Completed
Failed
Cancelled
RolledBack
```

---

# Scheduler Design

Scheduler باید تطبیقی (Adaptive) باشد.

هدف:

عدم اشغال بیش از حد RAM و CPU، مخصوصاً روی Termux و موبایل.

Scheduler باید فقط در زمان مناسب Job جدید اجرا کند.

پارامترهای قابل تنظیم:

- حداقل RAM آزاد
- حداقل باتری
- وضعیت شارژ
- دمای دستگاه
- حداکثر تعداد Job همزمان (پیش‌فرض: 1)

در صورت کمبود منابع، Job به تعویق می‌افتد، نه اینکه ناقص اجرا شود.

---

# Optimization Cycle

چرخه پیشنهادی:

برای **BTC**:

تمام ۱۴ تایم‌فریم صرافی بررسی شوند.

برای ۹ رمزارز دیگر:

فقط:

- 1m
- 5m
- 15m
- 1h
- 4h
- 1D

در مجموع:

- BTC = 14 Job
- سایر ارزها = 9 × 6 = 54 Job

کل چرخه = 68 Job برای هر Optimizer.

Signal Optimizer و Risk & Execution Optimizer مستقل اجرا می‌شوند، بنابراین هر چرخه کامل شامل 136 Job است.

---

# Adaptive Scheduling

به‌جای اجرای همه Jobها در یک روز، چرخه توزیع می‌شود.

نمونه:

روزانه 8 Job

در نتیجه:

136 ÷ 8 ≈ 17 روز

یا اگر منابع کافی بود:

روزانه 16 Job

≈ 8.5 روز

Scheduler باید این نرخ را بر اساس توان دستگاه تنظیم کند.

---

# Priority Policy

اولویت اجرای Jobها:

1. BTC
2. ETH
3. سایر ارزها بر اساس ارزش بازار
4. Jobهای قدیمی‌تر
5. Jobهایی که قبلاً شکست خورده‌اند (با محدودیت Retry)

---

# Persistence Structure

```
optimization/
│
├── signal/
│   └── BTCUSDT/
│       ├── 1m/
│       ├── 5m/
│       └── ...
│
├── execution/
│   └── BTCUSDT/
│       ├── 1m/
│       ├── 5m/
│       └── ...
│
├── history/
├── reports/
├── backups/
└── versions/
```

هیچ فایل Optimized نباید در مسیرهای متفرقه ذخیره شود.

---

# Versioning

هر خروجی باید دارای نسخه باشد:

```
Major.Minor.Patch

مثال:

3.2.7
```

همراه با:

- Timestamp
- Hash
- Generator Version
- Blueprint Version
- Compatible Project Version

---

# Rollback

اگر نسخه جدید:

- Validation را رد کند،
- باعث افت عملکرد شود،
- یا Runtime آن را ناسالم تشخیص دهد،

باید فوراً به آخرین نسخه پایدار بازگردد.

Rollback باید خودکار و بدون توقف پروژه انجام شود.

---

# Runtime Injection

در Startup:

Runtime Injector باید فقط فایل متناظر با همان Symbol و همان Timeframe را بارگذاری کند.

مثال:

```
BTCUSDT
1h
```

فقط:

```
optimization/signal/BTCUSDT/1h/
optimization/execution/BTCUSDT/1h/
```

را بخواند.

هیچ تزریق متقاطع بین Symbolها یا Timeframeها مجاز نیست.

---

# Dependency Injection

تمام موتورهای زیر باید پارامترهای خود را فقط از Runtime Injector دریافت کنند:

- Probability Engine
- Risk Engine
- Execution Engine
- Position Sizing
- Stop Manager
- TP Manager
- Trade Validator

این موتورها نباید فایل‌های بهینه‌سازی را مستقیماً بخوانند.

---

# Health Monitoring

Orchestrator باید به‌طور مداوم موارد زیر را پایش کند:

- نرخ موفقیت Jobها
- زمان متوسط اجرا
- میزان مصرف RAM
- مصرف CPU
- خطاهای Validation
- تعداد Rollbackها
- عمر آخرین نسخه بهینه‌سازی
- وضعیت صف

در صورت عبور از آستانه‌های تعریف‌شده، هشدار صادر شود.

---

# Telegram Integration

منوی اختصاصی Optimization:

```
Optimization
├── Run Signal Optimization
├── Run Execution Optimization
├── Pause Queue
├── Resume Queue
├── Show Queue
├── Show Progress
├── Last Results
├── Version History
├── Rollback
├── Health Status
└── Scheduler Settings
```

گزارش هر Job باید شامل:

- Symbol
- Timeframe
- Optimizer Type
- مدت اجرا
- نسخه تولیدشده
- نتیجه Validation
- وضعیت ذخیره‌سازی
- امکان Rollback

باشد.

---

# Acceptance Criteria

پیاده‌سازی زمانی کامل تلقی می‌شود که:

- هر دو Optimizer کاملاً مستقل ولی تحت کنترل یک Orchestrator باشند.
- زمان‌بندی تطبیقی و متناسب با منابع دستگاه انجام شود.
- نسخه‌بندی، Rollback و Validation کامل وجود داشته باشد.
- تزریق پارامترها فقط از طریق Runtime Injector انجام شود.
- هیچ پارامتری بین Symbolها و Timeframeها مخلوط نشود.
- سیستم بدون نیاز به دخالت دستی بتواند چرخه‌های بهینه‌سازی را برای مدت طولانی مدیریت کند.
- همه اجزا با معماری ماژولار و بدون ایجاد وابستگی چرخه‌ای (circular dependency) در پروژه ادغام شوند.

---

**ادامه در Part 8: Search Spaces، Objective Functions، Validation Protocols، Test Matrix، KPIها و معیارهای دقیق پذیرش نهایی هر دو Optimizer.**

# APEX Optimization Blueprint
## Part 8 — Search Spaces, Objective Functions, Validation Framework, Acceptance Tests & Quality Gates

---

# Mission

هیچ Optimizer نباید صرفاً با پیدا کردن بیشترین سود (Net Profit) خاتمه یابد.

هدف سیستم یافتن **پایدارترین، قابل تعمیم‌ترین، مقاوم‌ترین و کم‌ریسک‌ترین مجموعه پارامترها** است؛ مجموعه‌ای که در داده‌های دیده‌نشده نیز عملکرد مطلوب داشته باشد و دچار Overfitting نشود.

---

# Global Optimization Philosophy

Optimization در APEX چهار اصل دارد:

1. Generalization
2. Robustness
3. Stability
4. Explainability

هر نتیجه‌ای که صرفاً روی داده‌های آموزشی عالی باشد ولی روی داده‌های جدید افت کند، مردود است.

---

# Optimizable Components

بهینه‌سازی در دو دسته مستقل انجام می‌شود.

---

## Signal Optimizer

مسئول بهینه‌سازی تمام پارامترهایی است که بر تولید سیگنال اثر دارند.

### دسته‌های پارامتر

### Evidence Weights

تمام وزن‌های موتور Probability:

```
Momentum
Structure
Volume
Order Flow
Liquidity
SMC
ICT
FVG
Order Block
SMT
Regime
Volatility
Session
```

محدودیت:

```
تمام وزن‌ها

>=0

و

Sum=1
```

---

### Thresholds

```
Probability Threshold

Confidence Threshold

Evidence Threshold

Confluence Threshold

Minimum Volume

Minimum ATR

Minimum Trend Score

Maximum Noise

Maximum Spread

Minimum Liquidity
```

---

### ICT Parameters

```
FVG Min Size

FVG Max Age

OB Strength

OB Lookback

Breaker Sensitivity

Liquidity Sweep Distance

Liquidity Buffer

Displacement Threshold

BOS Threshold

CHOCH Threshold
```

---

### Market Structure

```
Swing Length

Pivot Detection

Structure Window

Trend Window

Structure Confirmation
```

---

### Filters

```
Session Filters

News Filter

Volatility Filter

Regime Filter

Volume Filter
```

---

### Probability Engine

```
Calibration

Scaling

Penalty

Confidence Curve

Probability Smoothing

Decay Factors
```

---

# Risk & Execution Optimizer

مسئول پارامترهای اجرای معامله است.

---

### Stop Loss

```
ATR Multiplier

Structure Buffer

Liquidity Buffer

Maximum Stop

Minimum Stop

Hybrid Threshold

BreakEven Trigger

Trailing Activation
```

---

### Take Profit

```
TP1 Ratio

TP2 Ratio

TP3 Ratio

Partial Close %

Runner %

Liquidity Priority

Structure Priority
```

---

### Position Sizing

```
Kelly Fraction

Maximum Kelly

Half Kelly Factor

Risk %

Portfolio Exposure

Maximum Exposure

Confidence Scaling

Volatility Scaling
```

---

### Execution

```
Maximum Slippage

Maximum Spread

Order Type

Execution Delay

Retry Count

Cancel Timeout
```

---

### Portfolio Risk

```
Daily Loss

Weekly Loss

Maximum Consecutive Losses

Maximum Correlated Positions

Sector Exposure

Leverage Cap
```

---

# Search Space Definition

هر پارامتر باید دارای:

```
Minimum

Maximum

Type

Distribution

Resolution
```

مثال:

```
ATR Multiplier

min=1.0

max=4.0

step=0.1

distribution=uniform
```

---

پارامترهای گسسته:

```
integer

categorical
```

پارامترهای پیوسته:

```
uniform

loguniform

normal
```

---

# Conditional Parameters

پارامترها نباید همگی همزمان فعال باشند.

مثال:

```
Stop Model

ATR

↓

ATR Multiplier فعال

Structure Buffer غیرفعال
```

یا

```
Structure Stop

↓

Swing Buffer فعال

ATR Multiplier غیرفعال
```

---

# Objective Function

هدف تنها سود نیست.

تابع هدف چندمعیاره است.

نمونه:

```
Score=

Expectancy

×

ProfitFactor

×

Sharpe

×

Sortino

×

RecoveryFactor

×

SQN

×

WinRateWeight

×

TradeCountWeight

×

Consistency

/

DrawdownPenalty

/

OverfitPenalty
```

---

# Metrics

حداقل KPIهای مورد استفاده:

```
Net Profit

Gross Profit

Gross Loss

Profit Factor

Recovery Factor

Expectancy

Average Trade

Median Trade

Max Drawdown

Relative Drawdown

Absolute Drawdown

Sharpe

Sortino

Calmar

Ulcer Index

MAR Ratio

SQN

Payoff Ratio

Average R

Average Holding Time

Trade Frequency

Winning Streak

Losing Streak

Exposure

Volatility Adjusted Return
```

---

# Hard Constraints

اگر هرکدام رخ دهد Trial مردود است.

```
Max Drawdown

>

20%
```

یا

```
Profit Factor

<1.2
```

یا

```
Trades

<100
```

یا

```
Win Rate

<40%
```

یا

```
Expectancy<=0
```

---

# Validation Pipeline

هر Trial باید از تمام مراحل زیر عبور کند.

---

## Stage 1

Backtest

کل تاریخچه همان Symbol و همان Timeframe

---

## Stage 2

Walk Forward Validation

---

## Stage 3

K-Fold Validation

---

## Stage 4

Monte Carlo Simulation

---

## Stage 5

Parameter Stability Analysis

---

## Stage 6

Sensitivity Analysis

---

## Stage 7

Stress Test

---

## Stage 8

Out-of-Sample Test

---

## Stage 9

Regression Test

---

## Stage 10

Acceptance Gate

---

# Monte Carlo

باید:

```
Random Order

Random Slippage

Random Delay

Random Spread

Random Missed Trades
```

را شبیه‌سازی کند.

---

# Walk Forward

نمونه:

```
70%

Train

30%

Test
```

سپس پنجره حرکت کند.

---

# Stability Analysis

بهترین پارامتر نباید تنها در یک نقطه جواب دهد.

اطراف آن نیز باید عملکرد مشابه داشته باشد.

اگر فقط یک نقطه عملکرد عالی داشته باشد:

Rejected

---

# Sensitivity Analysis

پارامترها

±5%

±10%

±20%

تغییر داده شوند.

اگر عملکرد فرو بریزد:

پارامتر ناپایدار است.

---

# Stress Test

سناریوهای زیر:

```
Flash Crash

Low Liquidity

High Volatility

Gap

Spread Expansion

API Delay

Missing Candles
```

---

# Acceptance Gates

فقط زمانی نسخه جدید ذخیره شود که:

```
Drawdown کمتر

Profit Factor بیشتر

Expectancy بیشتر

Sharpe بیشتر

و

هیچ معیار بحرانی بدتر نشده باشد.
```

---

# Quality Gates

نسخه جدید باید نسبت به نسخه فعال:

```
بهبود واقعی

نه صرفاً اختلاف آماری
```

داشته باشد.

---

# Reporting

هر اجرای Optimizer باید گزارش کامل تولید کند.

شامل:

```
Search Space

Trials

Rejected Trials

Accepted Trials

Validation Scores

Best Parameters

Metric Improvements

Execution Time

CPU

RAM

Warnings

Failure Reasons

Recommendations
```

---

# Final Acceptance Criteria

بخش Optimization تنها زمانی Completed محسوب می‌شود که:

- هر دو Optimizer دارای Search Space کامل باشند.
- تابع هدف چندمعیاره و مقاوم استفاده شود.
- اعتبارسنجی چندمرحله‌ای اجرا گردد.
- هیچ پارامتر بدون Validation ذخیره نشود.
- تمام KPIها ثبت شوند.
- گزارش کامل و قابل ردیابی تولید شود.
- نسخه جدید فقط پس از عبور از تمام Quality Gateها فعال گردد.
- کل فرآیند بدون Overfitting و با قابلیت تعمیم به داده‌های آینده طراحی شده باشد.

---

**ادامه در Part 9: File Formats، Storage Schema، Configuration Contracts، API Interfaces، Telegram Commands، CLI، Runtime Contracts و Integration Specification.**

# APEX Optimization Blueprint
## Part 9 — Storage Architecture, Runtime Contracts, API Specification, Configuration Management & Integration Layer

---

# Mission

هیچ خروجی تولیدشده توسط Optimizer نباید صرفاً یک فایل JSON ساده باشد.

هر خروجی باید یک **Optimization Artifact** کامل، نسخه‌بندی‌شده، قابل اعتبارسنجی، قابل ردیابی (Traceable)، قابل Rollback و قابل تزریق به Runtime باشد.

کل سیستم باید مانند یک Configuration Management System حرفه‌ای رفتار کند، نه مجموعه‌ای از فایل‌های پراکنده.

---

# Storage Architecture

ساختار پیشنهادی:

```
optimization/

├── signal/
│
│   ├── BTCUSDT/
│   │
│   ├── 1m/
│   ├── 5m/
│   ├── 15m/
│   ├── 30m/
│   ├── 1h/
│   ├── 4h/
│   ├── 1d/
│   └── ...
│
│
├── execution/
│
├── validation/
│
├── reports/
│
├── backups/
│
├── versions/
│
├── active/
│
├── archive/
│
└── metadata/
```

هیچ فایل دیگری خارج از این ساختار مجاز نیست.

---

# Optimization Artifact

هر نتیجه بهینه‌سازی باید شامل:

```
metadata.yaml

optimized_parameters.json

validation.json

metrics.json

history.json

optimizer.log

signature.sha256
```

باشد.

---

# Metadata

نمونه:

```yaml
artifact_version: 3.1.2

optimizer:

SignalOptimizer

symbol:

BTCUSDT

timeframe:

1h

generated_at:

UTC Timestamp

blueprint_version:

APEX v4

generator:

Parameter Optimizer

validation:

PASSED

status:

ACTIVE
```

---

# Optimized Parameters

فقط شامل پارامترهای قابل تزریق باشد.

نمونه:

```
Probability Threshold

Evidence Weights

ATR Multiplier

Kelly Fraction

Liquidity Buffer

TP Ratios

Risk %

...
```

نباید اطلاعات اضافه ذخیره شود.

---

# Validation File

باید نتایج تمام Validationها را نگهداری کند.

```
Walk Forward

PASS

Monte Carlo

PASS

Stress Test

PASS

Sensitivity

PASS

KFold

PASS
```

---

# Metrics File

تمام KPIها:

```
Profit Factor

Drawdown

Sharpe

Sortino

SQN

Recovery

Expectancy

Trades

...

```

---

# History

تمام Trialها:

```
Trial ID

Parameters

Metrics

Rejected Reason

Execution Time

Seed

Random State

```

---

# Signature

برای جلوگیری از خراب شدن فایل‌ها.

```
SHA256
```

در Startup اعتبارسنجی شود.

---

# Runtime Contracts

هر Engine فقط از طریق Contract با Optimizer ارتباط دارد.

هیچ وابستگی مستقیم مجاز نیست.

---

# Signal Optimizer Contract

```
interface SignalOptimizationProvider

load(symbol,timeframe)

validate()

get_parameters()

version()

metadata()

```

---

# Execution Optimizer Contract

```
interface ExecutionOptimizationProvider

load(symbol,timeframe)

get_risk()

get_stop_model()

get_tp_model()

get_position_model()

version()

```

---

# Runtime Injection Flow

```
Bootstrap

↓

Optimization Loader

↓

Validation

↓

Signature Check

↓

Version Check

↓

Dependency Injection

↓

Probability Engine

↓

Risk Engine

↓

Execution Engine

↓

Trading
```

---

اگر Validation شکست بخورد:

Runtime باید آخرین نسخه معتبر را بارگذاری کند.

---

# API Specification

هر Optimizer باید API داخلی داشته باشد.

---

## Load

```
load(symbol,timeframe)
```

---

## Validate

```
validate()

```

---

## Generate

```
generate()

```

---

## Save

```
save()

```

---

## Activate

```
activate(version)

```

---

## Rollback

```
rollback(version)

```

---

## Status

```
status()

```

---

## Metrics

```
metrics()

```

---

## Report

```
report()

```

---

# Configuration Management

هیچ مقدار Hard-Coded مجاز نیست.

تمام تنظیمات باید در:

```
optimization/config/
```

قرار گیرد.

---

نمونه:

```
optimizer.yaml

scheduler.yaml

validation.yaml

risk.yaml

search_space.yaml

telegram.yaml

runtime.yaml
```

---

# Configuration Rules

هر Config باید شامل:

```
schema

default

validation

allowed range

documentation
```

باشد.

---

# Dynamic Reload

اگر Config تغییر کند:

بدون Restart

Runtime باید Reload شود.

---

# Dependency Rules

مجاز:

```
Optimizer

↓

Backtest

↓

Probability

↓

Risk

↓

Execution
```

غیرمجاز:

```
Probability

↓

Optimizer

```

یا

```
Risk

↓

Optimizer
```

وابستگی چرخه‌ای ممنوع است.

---

# Telegram Integration

منوی کامل:

```
Optimization

├── Signal Optimizer

│      Run

│      Status

│      History

│      Report

│

├── Execution Optimizer

│      Run

│      Status

│      History

│      Report

│

├── Scheduler

├── Queue

├── Active Versions

├── Rollback

├── Validation

├── Health

├── Statistics

└── Configuration

```

---

# CLI

```
apex optimize signal BTCUSDT 1h

apex optimize execution BTCUSDT 1h

apex optimize all

apex optimize validate

apex optimize rollback

apex optimize report

apex optimize status

```

---

# Runtime Safety

در هیچ شرایطی:

```
Partial Artifact

Broken Artifact

Corrupted Artifact

Incomplete Artifact
```

نباید Load شود.

---

# Atomic Update

نسخه جدید ابتدا:

```
Temp

↓

Validate

↓

Rename

↓

Activate
```

شود.

هیچ فایل فعالی مستقیماً Overwrite نشود.

---

# Logging

تمام عملیات:

```
Start

Finish

Validation

Reject

Accept

Rollback

Injection

Load

Failure

```

باید Log شوند.

---

# Audit Trail

برای هر نسخه:

```
Who Generated

When

Why

Source Version

Validation Result

Previous Version

Next Version

```

ثبت شود.

---

# Final Acceptance Criteria

این بخش تنها زمانی Completed محسوب می‌شود که:

- ساختار ذخیره‌سازی استاندارد و نسخه‌بندی‌شده پیاده‌سازی شده باشد.
- هر Artifact دارای Metadata، Metrics، Validation، History و Signature باشد.
- قراردادهای Runtime و API کاملاً تعریف و رعایت شوند.
- تزریق پارامترها فقط از طریق Runtime Contracts انجام شود.
- بروزرسانی‌ها Atomic باشند.
- Rollback بدون توقف سیستم انجام شود.
- هیچ وابستگی چرخه‌ای ایجاد نشود.
- سیستم مدیریت تنظیمات (Configuration Management) کامل و قابل توسعه باشد.

---

**ادامه در Part 10: Testing Strategy، Failure Scenarios، Chaos Testing، Performance Benchmarkها، Security، Production Readiness و Definition of Done نهایی برای کل زیرسیستم Optimization.**

# APEX Optimization Blueprint
## Part 10 — Testing Strategy, Failure Handling, Performance Engineering, Security, Production Readiness & Definition of Done

---

# Mission

بخش Optimization تنها زمانی Production-Grade محسوب می‌شود که علاوه بر تولید پارامترهای بهینه، در برابر خطاها مقاوم، قابل بازیابی، قابل پایش، قابل تست و قابل اعتماد باشد.

هدف این فصل تعریف استانداردهای نهایی برای تضمین کیفیت کل زیرسیستم Optimization است.

---

# Testing Pyramid

تمام زیرسیستم Optimization باید حداقل شامل لایه‌های زیر باشد:

```
                E2E Tests
          Integration Tests
            Component Tests
               Unit Tests
```

هیچ ماژولی نباید بدون پوشش تست وارد نسخه Production شود.

---

# Unit Tests

برای هر کلاس:

- Signal Optimizer
- Risk & Execution Optimizer
- Scheduler
- Queue Manager
- Validation Pipeline
- Runtime Injector
- Version Manager
- Rollback Manager
- Persistence Manager
- Health Monitor

باید Unit Test مستقل وجود داشته باشد.

حداقل پوشش:

```
Coverage >= 90%
```

---

# Integration Tests

موارد زیر باید تست شوند:

```
Optimizer
↓

Backtest Engine

↓

Validation

↓

Persistence

↓

Runtime Injection

↓

Probability Engine

↓

Trading Engine
```

هر وابستگی باید مستقل اعتبارسنجی شود.

---

# End-to-End Tests

سناریوی کامل:

```
Load History

↓

Optimization

↓

Validation

↓

Artifact Generation

↓

Activation

↓

Trading

↓

Rollback

↓

Recovery
```

باید بدون دخالت دستی اجرا شود.

---

# Regression Tests

هر تغییر جدید نباید باعث خراب شدن:

- Probability Engine
- Risk Engine
- Execution Engine
- Telegram
- Backtest
- Live Trading

شود.

Regression Suite باید قبل از Merge اجرا گردد.

---

# Failure Scenarios

سیستم باید حداقل سناریوهای زیر را مدیریت کند:

---

## فایل خراب

```
Corrupted JSON

Corrupted YAML

Broken Metadata

Missing Signature
```

رفتار:

```
Reject

Rollback

Log

Alert
```

---

## نسخه ناقص

```
Missing Metrics

Missing Validation

Missing History
```

رفتار:

```
Reject
```

---

## قطع برق

اگر هنگام ذخیره Artifact سیستم خاموش شود:

نسخه قبلی باید سالم باقی بماند.

---

## Crash هنگام Optimization

پس از Restart:

```
Queue Recovery

Resume

یا

Restart Job
```

---

## کمبود RAM

Scheduler باید Job را Pause کند.

---

## قطع اینترنت

Optimization آفلاین باید ادامه پیدا کند.

فقط دریافت داده متوقف شود.

---

## خرابی Backtest

هیچ نسخه‌ای ذخیره نشود.

---

## Validation Failure

نسخه فعال تغییر نکند.

---

# Chaos Testing

به صورت تصادفی:

```
Kill Process

Delete Temp Files

Delay IO

Delay API

Corrupt Cache

Random Restart
```

اعمال شود.

سیستم باید بازیابی شود.

---

# Performance Benchmarks

حداکثر زمان Startup:

```
<10 sec
```

بارگذاری Artifact:

```
<1 sec
```

تزریق پارامترها:

```
<200 ms
```

Rollback:

```
<1 sec
```

Queue Scheduling:

```
<100 ms
```

---

# Memory Budget

روی Termux:

```
Target RAM

<500 MB
```

Optimization باید به صورت Streaming انجام شود.

کل تاریخچه نباید همزمان وارد RAM گردد.

---

# CPU Budget

در حالت Background:

```
Target

<50%
```

در حالت شارژ:

امکان افزایش مصرف وجود دارد.

---

# Logging Standard

سطوح:

```
TRACE

DEBUG

INFO

WARNING

ERROR

CRITICAL
```

هر پیام باید شامل:

```
Timestamp

Module

Symbol

Timeframe

Job ID

Optimizer

Thread

Version
```

باشد.

---

# Monitoring Dashboard

شاخص‌های اصلی:

```
Queue Size

Running Jobs

Completed Jobs

Failed Jobs

Retry Count

Average Runtime

CPU

RAM

Last Optimization

Current Version

Rollback Count

Validation Success Rate
```

---

# Security

تمام Artifactها باید:

- دارای Signature باشند.
- قبل از Load اعتبارسنجی شوند.
- فقط از مسیرهای مجاز بارگذاری شوند.
- از جایگزینی فایل‌های نامعتبر جلوگیری شود.

هیچ فایل ناشناس نباید وارد Runtime گردد.

---

# Backup Strategy

پس از هر نسخه موفق:

```
Active

↓

Backup

↓

Archive
```

حداقل:

```
Last 20 Versions
```

نگهداری شوند.

---

# Compatibility Rules

هر Artifact باید مشخص کند:

```
Compatible Blueprint Version

Compatible Project Version

Compatible Schema Version
```

عدم سازگاری:

```
Reject
```

---

# Production Checklist

قبل از فعال شدن نسخه جدید، تمام موارد زیر باید PASS باشند:

- Unit Tests
- Integration Tests
- End-to-End Tests
- Regression Tests
- Walk-Forward Validation
- Monte Carlo Validation
- Stress Tests
- Sensitivity Analysis
- Stability Analysis
- Signature Validation
- Schema Validation
- Performance Benchmark
- Memory Budget
- CPU Budget

حتی یک Failure نیز نباید نادیده گرفته شود.

---

# Definition of Done (Optimization Subsystem)

زیرسیستم Optimization تنها زمانی **100% Completed** محسوب می‌شود که:

- Signal Optimizer به طور کامل پیاده‌سازی شده باشد.
- Risk & Execution Optimizer به طور کامل پیاده‌سازی شده باشد.
- هر دو Optimizer مستقل ولی تحت مدیریت یک Orchestrator مرکزی باشند.
- Search Spaceها به طور کامل تعریف شده باشند.
- Objective Function چندمعیاره پیاده‌سازی شده باشد.
- تمام Validationها اجرا شوند.
- Overfitting Detection فعال باشد.
- Runtime Injection ایمن انجام شود.
- Versioning، Rollback و Persistence کامل باشند.
- Telegram، CLI و API داخلی به طور کامل متصل باشند.
- هیچ وابستگی چرخه‌ای وجود نداشته باشد.
- تست‌های واحد، یکپارچه، انتها‌به‌انتها و رگرسیون همگی PASS شوند.
- مستندسازی کامل توسعه‌دهندگان و کاربران تهیه شده باشد.
- زیرسیستم بدون نیاز به مداخله دستی بتواند برای مدت طولانی در محیط Production کار کند.
- هیچ قابلیت تعریف‌شده در این Blueprint حذف، ساده‌سازی یا به صورت اسکلتی پیاده‌سازی نشده باشد.

---

# Implementation Rule (Mandatory)

در زمان پیاده‌سازی این Blueprint رعایت موارد زیر الزامی است:

- هیچ بخشی به دلیل محدودیت مدل، زمان، حافظه یا حجم پروژه حذف یا خلاصه نشود.
- هیچ تصمیم معماری بدون مستندسازی و تأیید کاربر اتخاذ نشود.
- اگر پیاده‌سازی هر بخش نیازمند تغییر در کد موجود است، تغییر به صورت **Backward Compatible** انجام شود؛ مگر آنکه ناسازگاری اجتناب‌ناپذیر باشد که در این صورت باید مستند و به تأیید کاربر برسد.
- هیچ Placeholder، TODO، Stub یا Mock نباید در نسخه نهایی باقی بماند.
- تمام اجزای جدید باید با معماری موجود پروژه ادغام شوند و باعث شکستن بخش‌های دیگر نشوند.
- تمام قابلیت‌ها باید با تست، مستندات و گزارش‌های قابل ردیابی همراه باشند.

---

**پایان Blueprint Optimization Subsystem v1.0**

# APEX Optimization Blueprint
## Appendix A — Scheduler, Orchestration, Multi-Asset Strategy, Resource Management & Continuous Optimization Lifecycle

---

# Mission

هدف این بخش طراحی موتور مرکزی (Optimization Orchestrator) است که مسئول زمان‌بندی، اولویت‌بندی، تخصیص منابع، جلوگیری از تداخل Jobها و مدیریت چرخه دائمی بهینه‌سازی در کل سیستم APEX می‌باشد.

دو Optimizer مستقل هستند اما هرگز مستقل اجرا نمی‌شوند.

همیشه یک Orchestrator مرکزی مسئول مدیریت آن‌ها است.

---

# High Level Architecture

```
Optimization Orchestrator

│

├── Scheduler

├── Queue Manager

├── Resource Manager

├── Job Dispatcher

├── Validation Coordinator

├── Artifact Manager

├── Version Manager

├── Rollback Manager

├── Health Monitor

├── Statistics Engine

└── Notification Manager
```

---

# Optimization Lifecycle

هر چرخه بهینه‌سازی شامل مراحل زیر است:

```
Collect Historical Data

↓

Prepare Dataset

↓

Build Optimization Job

↓

Queue

↓

Execute

↓

Validation

↓

Acceptance

↓

Artifact Generation

↓

Version Registration

↓

Deployment

↓

Monitoring

↓

Archive
```

هیچ مرحله‌ای نباید حذف شود.

---

# Asset Isolation Principle

یکی از مهم‌ترین قوانین پروژه:

هر Symbol مستقل است.

هر Timeframe مستقل است.

هیچ پارامتری بین Symbolهای مختلف نباید به اشتراک گذاشته شود مگر اینکه صراحتاً در Blueprint تعریف شده باشد.

مثال:

```
BTCUSDT

1H

↓

Optimization

↓

BTCUSDT 1H فقط
```

خروجی آن نباید روی:

```
ETH

1H

یا

BTC

4H
```

اعمال شود.

---

# Optimization Scope Matrix

## Bitcoin

به دلیل نقش مرجع بازار:

تمام تایم‌فریم‌های موجود در Toobit باید بهینه شوند.

نمونه:

```
1m

3m

5m

15m

30m

1h

2h

4h

6h

12h

1d

1w

...

(تمام TFهای قابل دریافت)
```

---

## سایر ارزها

فقط تایم‌فریم‌های اصلی:

```
1m

5m

15m

1h

4h

1d
```

بهینه می‌شوند.

---

# Independent Parameter Sets

ساختار ذخیره‌سازی:

```
BTCUSDT

↓

1h

↓

Signal Parameters

Execution Parameters

Validation

History
```

و به همین ترتیب:

```
ETHUSDT

↓

1h

↓

کاملاً مستقل
```

---

# Runtime Injection Rule

هنگام اجرای معامله:

```
Incoming Symbol

↓

Incoming Timeframe

↓

Lookup Optimization Artifact

↓

Validation

↓

Inject

↓

Probability

↓

Risk

↓

Execution
```

هیچ Lookup تقریبی یا نزدیک‌ترین نسخه مجاز نیست.

اگر Artifact معتبر وجود نداشت:

از پارامترهای پیش‌فرض Blueprint استفاده شود و هشدار ثبت گردد.

---

# Continuous Optimization Strategy

بهینه‌سازی دائماً در پس‌زمینه انجام می‌شود، اما با مصرف کنترل‌شده منابع.

---

# Scheduling Policy

Scheduler باید:

- وضعیت CPU
- وضعیت RAM
- شارژ باتری
- اتصال اینترنت
- فعال بودن Backtest
- فعال بودن Live Trading

را بررسی کند.

اگر سیستم تحت فشار باشد:

Jobها به تعویق می‌افتند.

---

# Priority Levels

```
Critical

High

Normal

Low
```

---

اولویت‌ها:

```
BTC

تمام TFها

↓

High
```

```
سایر ارزها

↓

Normal
```

```
Optimization دستی کاربر

↓

Critical
```

---

# Queue Policy

```
FIFO
```

به‌صورت پیش‌فرض.

در صورت Job بحرانی:

```
Priority Queue
```

فعال می‌شود.

---

# Resource Budget

برای Termux:

```
حداکثر RAM هدف:

500 MB
```

```
حداکثر CPU هدف:

50%
```

در زمان شارژ و بیکار بودن دستگاه:

امکان افزایش بودجه وجود دارد.

---

# Parallelism

به دلیل محدودیت موبایل:

به‌صورت پیش‌فرض:

```
Single Active Optimization Job
```

فقط یک Job هم‌زمان اجرا شود.

در سیستم‌های قوی‌تر:

```
Configurable Worker Count
```

---

# Daily Optimization Cycle (نمونه پیشنهادی)

فرض:

- BTC: 14 Timeframe
- 9 آلت‌کوین × 6 Timeframe = 54

جمع:

```
68 Optimization Targets
```

اگر Scheduler روزانه 4 نوبت اجرا شود و در هر نوبت 4 هدف را کامل پردازش کند:

```
16 Target / Day
```

کل چرخه تقریباً:

```
68 / 16 ≈ 4.25 روز
```

طول می‌کشد.

این زمان برای بیشتر پارامترهای میان‌مدت مناسب است، زیرا بهینه‌سازی نیازی به اجرای لحظه‌ای ندارد.

---

# Adaptive Scheduling

اگر بازار وارد وضعیت غیرعادی شود (مثلاً نوسان شدید یا تغییر رژیم بازار):

Scheduler می‌تواند خارج از برنامه یک Job اضافی برای Symbolهای درگیر ایجاد کند.

---

# Job States

```
Pending

Preparing

Running

Paused

Waiting

Validating

Accepted

Rejected

Archived

Failed

Cancelled
```

تمام وضعیت‌ها باید قابل مشاهده در Telegram و CLI باشند.

---

# Failure Recovery

در صورت شکست هر Job:

- دلیل Failure ثبت شود.
- در صورت امکان Retry انجام شود.
- در غیر این صورت Job به حالت Failed منتقل و نسخه فعال بدون تغییر باقی بماند.

---

# Notifications

پس از پایان هر Job:

گزارشی شامل:

- Symbol
- Timeframe
- مدت اجرا
- نتیجه Validation
- بهبود نسبت به نسخه قبل
- نسخه فعال جدید (در صورت پذیرش)

در Telegram و Log ثبت شود.

---

# Final Acceptance Criteria

این بخش زمانی Completed محسوب می‌شود که:

- Orchestrator مرکزی پیاده‌سازی شده باشد.
- Scheduler و Queue Manager فعال باشند.
- بهینه‌سازی برای هر Symbol و Timeframe کاملاً مستقل انجام شود.
- تزریق پارامترها فقط بر اساس همان Symbol و همان Timeframe انجام شود.
- مصرف منابع متناسب با محدودیت‌های Termux مدیریت گردد.
- چرخه بهینه‌سازی پیوسته، قابل بازیابی و قابل پایش باشد.
- هیچ تداخلی بین نسخه‌های مختلف پارامترها ایجاد نشود.

---

**ادامه در Appendix B: طراحی داخلی Signal Optimizer شامل الگوریتم‌ها، فضای جستجوی تخصصی، مدل‌های امتیازدهی، تعامل با Probability Engine و قراردادهای دقیق پیاده‌سازی.**

# APEX Optimization Blueprint
## Appendix B — Signal Optimizer Internal Design, Optimization Algorithms, Search Strategy & Integration Contracts

---

# Mission

Signal Optimizer مسئول بهینه‌سازی تمام اجزایی است که مستقیماً بر کیفیت تولید سیگنال اثر می‌گذارند.

این Optimizer نباید صرفاً چند عدد Threshold را تغییر دهد؛ بلکه باید کل زنجیره تولید سیگنال را به‌صورت یک سیستم یکپارچه، داده‌محور و قابل اعتبارسنجی تنظیم کند.

---

# Architectural Position

```
Historical Data
        │
        ▼
Feature Extraction
        │
        ▼
Evidence Engines (13)
        │
        ▼
Probability Engine
        │
        ▼
Signal Optimizer (Offline)
        │
        ▼
Optimized Parameters
        │
        ▼
Artifact
        │
        ▼
Runtime Injection
        │
        ▼
Probability Engine
        │
        ▼
Decision Engine
```

Signal Optimizer هیچ‌گاه در مسیر Live Trading اجرا نمی‌شود و فقط پارامترهای نسخه بعدی را تولید می‌کند.

---

# Internal Modules

```
Signal Optimizer

├── Dataset Builder
├── Feature Validator
├── Search Space Manager
├── Trial Generator
├── Backtest Adapter
├── Objective Evaluator
├── Validation Coordinator
├── Stability Analyzer
├── Sensitivity Analyzer
├── Artifact Generator
└── Report Generator
```

---

# Dataset Builder

وظایف:

- دریافت تمام کندل‌های موجود از Toobit برای Symbol و Timeframe مربوطه.
- بررسی پیوستگی داده‌ها.
- حذف داده‌های خراب یا تکراری.
- نرمال‌سازی Timestampها.
- تولید Dataset نسخه‌بندی‌شده.

هیچ محدودیت مصنوعی برای تعداد کندل‌ها اعمال نشود؛ معیار، تمام تاریخچه قابل دریافت از صرافی است.

---

# Feature Validation

قبل از شروع هر Trial باید صحت تمام Featureها بررسی شود:

- ATR
- EMA
- VWAP
- Liquidity Levels
- Swing Points
- ICT Structures
- Order Blocks
- FVG
- BOS / CHOCH
- Volume Metrics
- Regime Features
- Probability Inputs

در صورت خرابی هر Feature، Trial آغاز نشود.

---

# Search Space Categories

پارامترها در گروه‌های مستقل مدیریت شوند:

- Evidence Weights
- Thresholds
- ICT Parameters
- Structure Parameters
- Liquidity Parameters
- Volatility Parameters
- Regime Filters
- Session Filters
- Probability Calibration
- Signal Acceptance Rules

هر گروه Schema مستقل و قابل توسعه داشته باشد.

---

# Optimization Strategy

روش پیش‌فرض:

1. فضای جستجو تعریف شود.
2. نمونه‌برداری هوشمند انجام شود.
3. Trial اجرا شود.
4. اعتبارسنجی چندمرحله‌ای انجام شود.
5. نتیجه امتیازدهی گردد.
6. بهترین نسخه ثبت شود.

پیاده‌سازی باید به گونه‌ای باشد که در آینده امکان جایگزینی الگوریتم جستجو (مانند Bayesian، Evolutionary یا سایر روش‌ها) بدون تغییر معماری فراهم باشد.

---

# Objective Evaluation

امتیاز هر Trial از ترکیب چند شاخص مستقل محاسبه شود.

هیچ معیار منفردی (مانند سود خالص) نباید تعیین‌کننده باشد.

سیستم باید بین سود، پایداری، ریسک، تعداد معاملات، کیفیت سیگنال و قابلیت تعمیم تعادل برقرار کند.

---

# Signal Quality Metrics

علاوه بر KPIهای مالی، کیفیت سیگنال نیز ارزیابی شود:

- Precision
- Recall
- False Positive Rate
- False Negative Rate
- Average Confidence
- Probability Calibration Error
- Signal Stability
- Direction Accuracy

---

# Overfitting Detection

اگر اختلاف عملکرد بین داده آموزشی و داده آزمایشی از حد مجاز بیشتر شود:

```
Reject Trial
```

همچنین اگر بهترین پارامتر فقط در یک نقطه بسیار خاص عملکرد عالی داشته باشد و نسبت به تغییرات کوچک حساس باشد، Trial مردود است.

---

# Parameter Stability Map

برای پارامترهای مهم، نقشه پایداری تولید شود تا مشخص گردد:

- ناحیه‌های پایدار
- ناحیه‌های ناپایدار
- حساسیت هر پارامتر

هدف یافتن «منطقه پایدار» است، نه صرفاً «بهترین نقطه».

---

# Runtime Integration Contract

Probability Engine فقط از طریق Provider رسمی پارامترها را دریافت کند.

هیچ مقدار Hard-Coded یا Override دستی در Runtime مجاز نیست مگر با ثبت در Log و تأیید کاربر.

---

# Reporting

گزارش Signal Optimizer باید شامل موارد زیر باشد:

- فضای جستجو
- تعداد Trialها
- Trialهای ردشده
- بهترین Trial
- دلایل رد Trialها
- نمودار بهبود KPIها
- تحلیل حساسیت
- تحلیل پایداری
- پیشنهادهای مهندسی برای نسخه بعدی

---

# Final Acceptance Criteria

Signal Optimizer تنها زمانی Completed محسوب می‌شود که:

- تمام پارامترهای مؤثر بر تولید سیگنال قابل بهینه‌سازی باشند.
- اعتبارسنجی چندمرحله‌ای برای هر Trial اجرا شود.
- تشخیص Overfitting فعال باشد.
- پارامترها به‌صورت نسخه‌بندی‌شده ذخیره شوند.
- Runtime فقط از Artifact معتبر استفاده کند.
- هیچ بخش Placeholder، Stub یا TODO باقی نمانده باشد.

---

**ادامه در Appendix C: طراحی داخلی Risk & Execution Optimizer شامل مدل‌های Stop Loss، Take Profit، Position Sizing، مدیریت ریسک پرتفوی، سیاست‌های اهرم، قوانین اجرای سفارش و قراردادهای اتصال با Trading Engine.**

# APEX Optimization Blueprint
## Appendix C — Risk & Execution Optimizer Internal Design, Portfolio Risk Management, Order Execution, Adaptive Risk Models & Production Integration

---

# Mission

Risk & Execution Optimizer مسئول بهینه‌سازی تمام پارامترهای مرتبط با اجرای معامله است.

هدف آن افزایش سود نیست.

هدف آن **حداکثر کردن امید ریاضی (Expectancy)، کنترل ریسک، کاهش Drawdown، افزایش بقا (Survivability) و بهینه‌سازی کیفیت اجرای معاملات** است.

این Optimizer نباید هیچ دخالتی در تولید سیگنال داشته باشد.

تصمیم ورود توسط Signal Stack گرفته می‌شود و این Optimizer فقط بهترین روش اجرای همان تصمیم را تعیین می‌کند.

---

# Architectural Position

```
Decision Engine
        │
        ▼
Approved Signal
        │
        ▼
Risk & Execution Optimizer
        │
        ▼
Trade Blueprint
        │
        ▼
Execution Engine
        │
        ▼
Exchange (Toobit)
```

---

# Internal Architecture

```
RiskExecutionOptimizer

├── Risk Model Selector
├── Stop Loss Optimizer
├── Take Profit Optimizer
├── Position Size Optimizer
├── Portfolio Risk Manager
├── Leverage Manager
├── Execution Strategy Optimizer
├── Trade Validator
├── Runtime Adapter
├── Artifact Generator
└── Report Generator
```

---

# Principle of Operation

هر Symbol و هر Timeframe دارای مدل ریسک مستقل است.

مثال:

```
BTCUSDT
1H
```

دارای پارامترهای مستقل است.

```
ETHUSDT
1H
```

نباید همان پارامترها را استفاده کند.

---

# Optimization Targets

پارامترهای قابل بهینه‌سازی شامل:

## Stop Loss

- ATR Multiplier
- Structure Buffer
- Liquidity Buffer
- Swing Buffer
- BreakEven Trigger
- Trailing Trigger
- Trailing Distance
- Dynamic Stop Model
- Hybrid Stop Logic

---

## Take Profit

- TP1 Distance
- TP2 Distance
- TP3 Distance
- Partial Close Ratios
- Runner Allocation
- Liquidity Target Priority
- Structure Target Priority
- Dynamic Exit Rules

---

## Position Sizing

- Base Risk %
- Kelly Fraction
- Half Kelly Factor
- Confidence Multiplier
- Volatility Multiplier
- Equity Curve Adjustment
- Drawdown Adjustment

---

## Portfolio Controls

- Maximum Concurrent Positions
- Maximum Correlation
- Daily Loss Limit
- Weekly Loss Limit
- Maximum Exposure
- Maximum Symbol Exposure
- Maximum Sector Exposure

---

## Leverage

Leverage نباید مقدار ثابت باشد.

باید تابعی از:

- Stop Distance
- ATR
- Confidence
- Market Regime
- Portfolio Risk
- Exchange Limits

باشد.

---

# Stop Model Selection

سیستم باید بتواند بین مدل‌های زیر انتخاب کند:

```
ATR Only

Structure Only

Liquidity Only

ATR + Structure

ATR + Liquidity

Structure + Liquidity

Hybrid Adaptive
```

انتخاب مدل نیز قابل بهینه‌سازی است.

---

# Dynamic Take Profit

به‌جای TP ثابت، سیستم باید بتواند:

- خروج مرحله‌ای
- خروج مبتنی بر Liquidity
- خروج مبتنی بر Structure
- خروج مبتنی بر Volatility
- خروج مبتنی بر Time

را انتخاب کند.

---

# Position Size Engine

سایز معامله باید تابع موارد زیر باشد:

```
Account Equity

×

Kelly

×

Confidence

×

Volatility Adjustment

×

Portfolio Exposure Adjustment

×

Risk Budget
```

هر عامل باید مستقل قابل تنظیم باشد.

---

# Portfolio Awareness

این Optimizer نباید فقط معامله جاری را ببیند.

باید وضعیت کل پرتفوی را لحاظ کند.

از جمله:

- تعداد معاملات باز
- همبستگی دارایی‌ها
- ریسک تجمعی
- سود و زیان روز
- سود و زیان هفته
- میزان سرمایه آزاد

---

# Execution Strategy

برای هر معامله باید مناسب‌ترین روش اجرا انتخاب شود:

- Market
- Limit
- Stop
- Stop Limit
- Reduce Only
- Post Only

در صورت پشتیبانی صرافی.

---

# Slippage Management

قبل از ارسال سفارش:

- بررسی Spread
- بررسی عمق بازار
- بررسی نقدشوندگی

انجام شود.

در صورت عبور از حد مجاز:

```
Reject Trade
```

یا

```
Reduce Size
```

---

# Adaptive Risk

در صورت تغییر Regime بازار:

پارامترهای ریسک باید تغییر کنند.

نمونه:

```
Low Volatility

↓

Risk = 1%
```

```
High Volatility

↓

Risk = 0.4%
```

---

# Drawdown Protection

اگر افت سرمایه افزایش یابد:

سیستم باید به‌صورت تدریجی:

- سایز معاملات
- اهرم
- ریسک

را کاهش دهد.

---

# Kill Switch

شرایط نمونه:

- Daily Loss Limit
- Weekly Loss Limit
- Maximum Consecutive Losses
- Exchange Failure
- Data Corruption

در صورت فعال شدن:

```
No New Trades
```

تا رفع شرایط.

---

# Validation

هر Trial باید روی کل تاریخچه همان Symbol و همان Timeframe اجرا شود.

سپس:

- Walk Forward
- Monte Carlo
- Stress Test
- Sensitivity
- Stability

اجرا گردد.

---

# Artifact

خروجی Risk Optimizer باید شامل:

- Risk Parameters
- Execution Parameters
- Validation
- Metrics
- Metadata
- Version
- Signature

باشد.

---

# Runtime Injection

Execution Engine فقط از طریق Runtime Contract پارامترها را دریافت کند.

هیچ Override دستی بدون ثبت در Audit Log مجاز نیست.

---

# Reporting

گزارش Risk Optimizer باید شامل:

- تغییرات نسبت به نسخه قبل
- بهبود Expectancy
- تغییر Drawdown
- تغییر Profit Factor
- تغییر Sharpe
- تغییر Recovery Factor
- تغییر Average R
- دلایل رد Trialها
- تحلیل حساسیت
- تحلیل پایداری

باشد.

---

# Final Acceptance Criteria

Risk & Execution Optimizer تنها زمانی Completed محسوب می‌شود که:

- تمام مدل‌های ریسک قابل انتخاب و قابل بهینه‌سازی باشند.
- Stop، TP، Position Size، Leverage و Portfolio Rules همگی بهینه‌سازی شوند.
- تمام Validationها اجرا شوند.
- خروجی نسخه‌بندی‌شده و قابل Rollback باشد.
- Runtime Injection ایمن انجام شود.
- هیچ پارامتر Hard-Coded در Runtime باقی نمانده باشد.
- هیچ بخش Placeholder، Stub یا TODO در نسخه نهایی وجود نداشته باشد.

---

**ادامه در Appendix D: Meta Optimization، Cross-Version Learning، Knowledge Base، Adaptive Evolution، Self-Improvement Loop و طراحی سامانه یادگیری مستمر APEX.**

# APEX Optimization Blueprint
## Appendix D — Meta Optimization, Knowledge Base, Continuous Learning, Adaptive Evolution & Self-Improvement Architecture

---

# Mission

دو Optimizer قبلی تنها مسئول یافتن بهترین پارامترها هستند.

اما این بخش مسئول آن است که خود سیستم APEX در طول زمان از عملکرد گذشته خود یاد بگیرد، کیفیت تصمیم‌های خود را اندازه‌گیری کند و به‌صورت کنترل‌شده تکامل یابد، بدون آنکه دچار Drift یا Overfitting شود.

این بخش **هیچ مدل هوش مصنوعی جدید تولید نمی‌کند** و نباید به یک سیستم خودمختار غیرقابل کنترل تبدیل شود. هدف آن مدیریت دانش استخراج‌شده از نتایج واقعی سیستم است.

---

# High-Level Architecture

```
Historical Backtests
           │
           ▼
Optimization Artifacts
           │
           ▼
Knowledge Extractor
           │
           ▼
Knowledge Base
           │
           ▼
Meta Analyzer
           │
           ▼
Recommendation Engine
           │
           ▼
Optimizer Orchestrator
```

---

# Core Components

```
Meta Optimization

├── Knowledge Collector
├── Knowledge Validator
├── Pattern Miner
├── Performance Analyzer
├── Regime Analyzer
├── Drift Detector
├── Recommendation Engine
├── Strategy Evolution Manager
├── Knowledge Base Manager
└── Audit Recorder
```

---

# Knowledge Base

Knowledge Base محل ذخیره پارامترها نیست.

محل ذخیره **دانش استخراج‌شده** است.

نمونه اطلاعات:

- عملکرد هر پارامتر در طول زمان
- شرایط موفقیت هر مدل
- شرایط شکست
- رفتار هر Symbol
- رفتار هر Timeframe
- رفتار هر Regime
- تغییرات بازار
- کیفیت پیش‌بینی Probability Engine
- کیفیت مدیریت ریسک

---

# Asset Isolation

Knowledge باید برای هر دارایی مستقل نگهداری شود.

```
Knowledge

BTCUSDT

↓

1H

↓

Knowledge
```

کاملاً مستقل از

```
ETHUSDT

↓

1H
```

باشد.

---

# Timeframe Isolation

هر تایم‌فریم دارای Knowledge مستقل است.

هیچ نتیجه‌ای از:

```
BTC

5m
```

نباید مستقیماً وارد

```
BTC

4H
```

شود.

---

# Regime Awareness

Knowledge باید بر اساس Regime نیز دسته‌بندی شود.

مثلاً:

```
Trending Bull

Trending Bear

Sideway

High Volatility

Low Volatility

News Event
```

---

# Pattern Mining

سیستم باید بتواند الگوهای زیر را استخراج کند:

- کدام پارامترها پایدارتر بوده‌اند.
- کدام ترکیب پارامترها دائماً شکست خورده‌اند.
- کدام Evidenceها ارزش بیشتری داشته‌اند.
- کدام پارامترها نسبت به تغییر بازار حساس هستند.

---

# Performance Drift Detection

سیستم باید دائماً بررسی کند:

آیا کیفیت نسخه فعال در حال کاهش است؟

نمونه شاخص‌ها:

- افت Profit Factor
- افت Expectancy
- افزایش Drawdown
- کاهش Win Rate
- افزایش Calibration Error

اگر Drift تشخیص داده شود:

```
Recommendation
```

برای اجرای Optimization جدید تولید شود.

---

# Recommendation Engine

این بخش **حق تغییر مستقیم سیستم را ندارد**.

فقط پیشنهاد تولید می‌کند.

نمونه پیشنهادها:

- اجرای مجدد Signal Optimization
- اجرای مجدد Risk Optimization
- افزایش تعداد Trial
- تغییر Search Space
- حذف پارامترهای ناکارآمد
- افزودن Validation بیشتر

اجرای پیشنهاد فقط توسط Orchestrator و پس از اعتبارسنجی انجام می‌شود.

---

# Continuous Learning Loop

```
Trading

↓

Results

↓

Backtest Comparison

↓

Knowledge Extraction

↓

Knowledge Validation

↓

Knowledge Base

↓

Recommendation

↓

Optimization

↓

Validation

↓

Deployment
```

این چرخه باید کاملاً قابل ردیابی باشد.

---

# Knowledge Validation

هر دانش استخراج‌شده باید قبل از ثبت:

- از چند منبع تأیید شود.
- روی داده‌های مستقل بررسی شود.
- با نسخه‌های قبلی مقایسه شود.

در صورت عدم اعتبار:

```
Reject
```

---

# Evolution Policy

هیچ نسخه جدیدی صرفاً به دلیل بهتر بودن روی داده‌های آموزشی پذیرفته نشود.

پذیرش تنها در صورتی مجاز است که:

- Validation کامل PASS باشد.
- پایداری تأیید شود.
- نسبت به نسخه فعال برتری معنادار داشته باشد.
- ریسک افزایش نیافته باشد.

---

# Audit Trail

برای هر تغییر ثبت شود:

- چه دانشی استخراج شد.
- از چه داده‌هایی استخراج شد.
- چه پیشنهادی ایجاد شد.
- چه کسی یا چه فرآیندی آن را پذیرفت.
- چه نسخه‌ای جایگزین شد.

---

# Safety Rules

Meta Optimization هرگز مجاز نیست:

- پارامترها را مستقیماً تغییر دهد.
- Artifact فعال را بازنویسی کند.
- Validation را دور بزند.
- نسخه‌ای را بدون تأیید Pipeline فعال کند.

---

# Explainability

برای هر پیشنهاد باید توضیح قابل فهم تولید شود:

- دلیل پیشنهاد
- داده‌های مورد استفاده
- شاخص‌های مؤثر
- مزایا
- ریسک‌های احتمالی

---

# Final Acceptance Criteria

این بخش تنها زمانی Completed محسوب می‌شود که:

- Knowledge Base مستقل برای هر Symbol و Timeframe وجود داشته باشد.
- Drift Detection فعال باشد.
- Recommendation Engine فقط پیشنهاد تولید کند.
- هیچ تغییر مستقیمی بدون عبور از Pipeline رسمی انجام نشود.
- تمام تغییرات قابل Audit و Rollback باشند.
- یادگیری مستمر بدون ایجاد Overfitting یا رفتار غیرقابل پیش‌بینی انجام شود.

---

**ادامه در Appendix E: Schemaهای دقیق فایل‌ها، قراردادهای داده (Data Contracts)، ساختار JSON/YAML، نسخه‌بندی Schema، Migration Rules و استانداردهای توسعه برای پیاده‌سازی کامل زیرسیستم Optimization.**

# Appendix E — Data Contracts, Artifact Schema, Versioning, Storage Layout & Deployment Architecture

---

# Mission

این سند استاندارد رسمی تمام داده‌هایی است که بین دو Optimizer، Backtest Engine، Probability Engine، Risk Engine، Telegram، Bootstrap و Knowledge Base رد و بدل می‌شوند.

هیچ ماژولی مجاز نیست خارج از این قراردادها داده تولید یا مصرف کند.

تمام فایل‌ها Versioned هستند.

Backward Compatibility اجباری است.

---

# Root Directory

```
knowledge_base/

    BTCUSDT/
        1m/
        5m/
        15m/
        30m/
        1h/
        4h/
        1d/

    ETHUSDT/
        ...

artifacts/

optimizer/

validation/

audit/

history/

reports/
```

---

# Symbol Isolation

هر Symbol دارای دایرکتوری مستقل است.

مثال:

```
knowledge_base/

BTCUSDT/

ETHUSDT/

SOLUSDT/

BNBUSDT/

XRPUSDT/
```

هیچ فایل مشترکی بین آنها وجود ندارد.

---

# Timeframe Isolation

داخل هر Symbol:

```
1m

5m

15m

30m

1h

4h

1d

...
```

هر تایم‌فریم دارای Artifact مستقل است.

---

# Artifact Types

```
signal_optimizer.json

risk_optimizer.json

validation_report.json

performance_metrics.json

knowledge.json

history.json

audit.json

deployment.json
```

---

# Signal Optimizer Artifact

```
schema_version

created_at

symbol

timeframe

dataset_hash

optimization_id

optimizer_version

search_algorithm

search_space_hash

objective_function

best_score

validation_score

generalization_score

overfitting_score

accepted

parameters

metrics

feature_importance

recommendations
```

---

# Risk Optimizer Artifact

```
schema_version

symbol

timeframe

risk_model

sl_model

tp_model

position_sizing

partial_exit

trailing

breakeven

validation

deployment_ready
```

---

# Validation Report

```
walk_forward

cross_validation

monte_carlo

bootstrap

stress_test

out_of_sample

regime_test

latency_test

memory_test

result

reason
```

---

# Performance Metrics

```
Net Profit

Gross Profit

Gross Loss

Profit Factor

Expectancy

Sharpe

Sortino

Calmar

Ulcer Index

Recovery Factor

Max Drawdown

Average Drawdown

Trade Count

Long Trades

Short Trades

Average RR

Average Hold Time

Exposure

Daily Return

Monthly Return

Volatility

Kelly

Win Rate

Loss Rate

Commission

Slippage

Latency

Execution Cost
```

---

# Knowledge Artifact

```
Market Behaviour

Stable Parameters

Unstable Parameters

Regime Behaviour

Evidence Statistics

Failure Reasons

Successful Configurations

Risk Statistics

Execution Statistics

Confidence Calibration

Probability Calibration
```

---

# Audit Artifact

برای هر Optimization:

```
Optimization ID

Start Time

End Time

Machine

Git Commit

Blueprint Version

Schema Version

Dataset Hash

Random Seed

Optimizer Version

Validation Version

Accepted

Rollback Available
```

---

# History Artifact

تمام نسخه‌های قبلی نگهداری می‌شوند.

```
v1

v2

v3

v4

...

Current
```

Rollback همیشه ممکن است.

---

# Dataset Hash

هر Optimization باید روی Dataset مشخص انجام شود.

بنابراین Hash داده ذخیره می‌شود.

```
SHA256
```

در صورت تغییر داده:

Optimization جدید لازم است.

---

# Search Space Hash

برای جلوگیری از اشتباه:

Search Space نیز Hash می‌شود.

اگر Search Space تغییر کند:

نسخه جدید Optimization ایجاد می‌شود.

---

# Schema Version

تمام Artifactها:

```
schema_version

optimizer_version

blueprint_version

```

دارند.

---

# Deployment Policy

تنها فایل دارای:

```
deployment_ready=true
```

قابل Load شدن توسط Bootstrap است.

---

# Bootstrap Loading Order

```
Read

↓

Validate

↓

Schema Check

↓

Hash Check

↓

Compatibility Check

↓

Load

↓

Activate
```

---

# Rollback

در صورت شکست:

```
Current

↓

Previous Stable

↓

Activate
```

هیچ Downtime نباید ایجاد شود.

---

# Atomic Deployment

هیچ فایل نیمه‌نوشته نباید Load شود.

ابتدا:

```
temp
```

سپس:

```
rename
```

اتمیک.

---

# File Locking

هنگام نوشتن:

```
.lock
```

ایجاد شود.

Bootstrap فایل Lock شده را Load نمی‌کند.

---

# Corruption Detection

قبل از Load:

- Hash
- Size
- Schema
- Required Fields

کنترل شوند.

---

# Missing Artifact Policy

اگر Artifact وجود نداشت:

سیستم باید با Defaultهای Blueprint اجرا شود.

نه اینکه Crash کند.

---

# Telegram Integration

بخش Optimization باید بتواند گزارش زیر را نمایش دهد:

- نسخه فعال
- تاریخ آخرین Optimization
- نسخه Schema
- وضعیت Validation
- کیفیت نسخه
- درصد بهبود
- وضعیت Drift
- زمان Optimization بعدی

---

# CLI Commands

```
optimize

validate

rollback

history

status

report

knowledge

audit

export

import
```

همگی باید پیاده‌سازی شوند.

---

# Final Acceptance Criteria

این بخش تنها زمانی Completed است که:

- تمام Artifactها Versioned باشند.
- تمام فایل‌ها Schema داشته باشند.
- تمام Deploymentها Atomic باشند.
- Rollback تضمین شده باشد.
- Bootstrap فقط نسخه معتبر را Load کند.
- هیچ Optimizer مستقیماً فایل فعال را بازنویسی نکند.
- کل زیرسیستم قابل Audit، قابل Reproduce و قابل Version Control باشد.

---

**ادامه در Appendix F: طراحی کامل Pipeline اجرای Signal Optimizer و Risk Optimizer، Scheduler، State Machine، چرخه کامل اجرا، Dependency Graph و پروتکل‌های هماهنگی بین تمام موتورهای APEX.**
```

# Appendix F — End-to-End Optimization Execution Pipeline, Scheduler, State Machines, Dependency Graph & Runtime Protocols

---

# Mission

این سند رفتار اجرایی کل زیرسیستم Optimization را تعریف می‌کند.

از لحظه‌ای که Scheduler فعال می‌شود تا زمانی که نسخه جدید وارد سیستم معاملاتی گردد، هیچ رفتار مبهمی نباید وجود داشته باشد.

هیچ مرحله‌ای نباید حذف، ساده‌سازی یا تفسیر شود.

---

# High-Level Architecture

```
Scheduler
      │
      ▼
Optimization Queue
      │
      ▼
Dataset Builder
      │
      ▼
Data Validation
      │
      ▼
Signal Optimizer
      │
      ▼
Risk & Execution Optimizer
      │
      ▼
Validation Pipeline
      │
      ▼
Acceptance Gate
      │
      ▼
Knowledge Base Writer
      │
      ▼
Artifact Versioning
      │
      ▼
Bootstrap Loader
      │
      ▼
Live Trading
```

---

# Global Optimization State Machine

هر Job باید فقط در یکی از وضعیت‌های زیر باشد:

```
IDLE

↓

QUEUED

↓

PREPARING_DATA

↓

DATA_VALIDATION

↓

SIGNAL_OPTIMIZATION

↓

RISK_OPTIMIZATION

↓

CROSS_VALIDATION

↓

MONTE_CARLO

↓

STRESS_TEST

↓

OUT_OF_SAMPLE

↓

SCORING

↓

ACCEPTED

↓

DEPLOYED
```

اگر شکست رخ دهد:

```
FAILED

↓

LOG

↓

RETRY

یا

ROLLBACK
```

---

# Scheduler Responsibilities

Scheduler تنها مسئول زمان‌بندی است.

حق انجام هیچ Optimization را ندارد.

وظایف:

- ساخت Queue
- جلوگیری از هم‌پوشانی Jobها
- مدیریت اولویت‌ها
- کنترل مصرف CPU
- کنترل RAM
- کنترل Battery (در موبایل)
- Resume پس از Restart
- ثبت Log

---

# Optimization Queue

هر Job شامل:

```
Job ID

Priority

Coin

Timeframe

Optimizer Type

Created Time

Retry Count

Dependencies

Dataset Version

Status
```

---

# Queue Priority Policy

اولویت‌ها:

```
BTC

↓

ETH

↓

BNB

↓

SOL

↓

XRP

↓

...

```

و داخل هر کوین:

BTC:

```
تمام 14 تایم‌فریم
```

سایر ارزها:

```
1m

5m

15m

1h

4h

1d
```

---

# Dependency Graph

Signal Optimizer همیشه قبل از Risk Optimizer اجرا می‌شود.

```
Dataset

↓

Signal Optimizer

↓

Validation

↓

Risk Optimizer

↓

Validation

↓

Deployment
```

Risk Optimizer هرگز اجازه ندارد روی پارامترهای قدیمی اجرا شود.

---

# Dataset Preparation Pipeline

قبل از هر Optimization:

1. دریافت کامل تاریخچه از Toobit
2. بررسی Missing Candle
3. بررسی ترتیب زمانی
4. حذف Duplicate
5. بررسی Gap
6. بررسی Timezone
7. محاسبه اندیکاتورها
8. ساخت Featureها
9. ذخیره Dataset
10. تولید Dataset Hash

---

# Data Integrity Rules

Optimization باید متوقف شود اگر:

- Missing Candle
- Duplicate Candle
- NaN Feature
- Infinite Value
- Timestamp Disorder
- Invalid OHLC
- Invalid Volume

وجود داشته باشد.

---

# Signal Optimizer Runtime

```
Load Dataset

↓

Generate Search Space

↓

Sample Parameters

↓

Run Full Backtest

↓

Collect Metrics

↓

Evaluate Objective

↓

Store Trial

↓

Next Trial
```

تا پایان Trialها.

---

# Risk Optimizer Runtime

```
Load Winning Parameters

↓

Replay Full History

↓

Generate SL Models

↓

Generate TP Models

↓

Generate Position Models

↓

Evaluate

↓

Store Best Risk Blueprint
```

---

# Validation Pipeline

هر دو Optimizer باید دقیقاً از Validation مشترک استفاده کنند.

Validation شامل:

- Walk Forward
- Cross Validation
- Monte Carlo
- Bootstrap
- Stress Test
- Regime Test
- Outlier Test
- Stability Test

---

# Acceptance Gate

Optimization تنها زمانی پذیرفته می‌شود که:

- Generalization کافی باشد.
- Overfitting کمتر از حد مجاز باشد.
- Drawdown افزایش غیرمجاز نداشته باشد.
- Profit Factor کاهش نیافته باشد.
- Sharpe کاهش نیافته باشد.
- Stability مناسب باشد.

در غیر این صورت:

```
Rejected
```

---

# Deployment Protocol

فقط Artifactهای Accepted اجازه Deployment دارند.

مراحل:

```
Backup Current

↓

Write Temp

↓

Verify

↓

Atomic Rename

↓

Bootstrap Reload

↓

Activation

↓

Health Check
```

---

# Rollback Protocol

اگر Health Check شکست بخورد:

```
Deactivate

↓

Restore Previous

↓

Restart Engines

↓

Log Incident
```

---

# Runtime Isolation

در زمان Optimization:

- Trading متوقف نمی‌شود.
- Backtest متوقف نمی‌شود.
- Telegram فعال می‌ماند.
- Probability Engine نسخه فعلی را استفاده می‌کند.

نسخه جدید فقط پس از Acceptance جایگزین می‌شود.

---

# Failure Recovery

در صورت Crash:

```
Read Queue

↓

Resume Last Job

↓

Continue Remaining Trials
```

هیچ Trial نباید از ابتدا تکرار شود مگر Dataset تغییر کرده باشد.

---

# Logging Requirements

برای هر مرحله ثبت شود:

- Start Time
- End Time
- Duration
- Memory Usage
- CPU Usage
- Dataset Hash
- Optimizer Version
- Exception (در صورت وجود)
- Result

---

# Monitoring Metrics

Scheduler باید به‌صورت دائمی پایش کند:

- Queue Length
- Pending Jobs
- Running Jobs
- Failed Jobs
- Average Runtime
- Average Memory
- Average CPU
- Success Rate
- Acceptance Rate

---

# End-to-End Completion Criteria

این زیرسیستم تنها زمانی کامل تلقی می‌شود که:

- چرخه اجرای کامل از Scheduler تا Deployment بدون دخالت دستی انجام شود.
- تمام وضعیت‌ها قابل بازیابی (Recoverable) باشند.
- هیچ Optimizer باعث توقف سیستم معاملاتی نشود.
- تمام مراحل دارای Log، Audit و Version مستقل باشند.
- کل Pipeline قابل تکرار (Reproducible)، قابل بررسی (Auditable) و قابل بازگشت (Rollback-safe) باشد.

---

**ادامه در Appendix G: طراحی کامل Signal Optimizer (ساختار داخلی، ماژول‌ها، Search Space، Objective Functions، Feature Groups، Trial Lifecycle و تمامی جزئیات پیاده‌سازی).**

# Appendix G — Signal Optimizer Complete Internal Architecture, Search Space, Objective System, Trial Lifecycle & Integration Protocol

---

# Mission

Signal Optimizer مهم‌ترین بخش سیستم APEX است.

وظیفه آن **بهینه‌سازی منطق تولید سیگنال** است، نه مدیریت معامله.

این Optimizer باید بتواند بدون تغییر کدنویسی موتورهای تحلیل، بهترین ترکیب پارامترها را برای هر Symbol و هر Timeframe پیدا کند و نسخه‌ای پایدار، قابل تعمیم و مقاوم در برابر Overfitting تولید نماید.

---

# Responsibilities

Signal Optimizer مسئول موارد زیر است:

- بهینه‌سازی پارامترهای تمامی موتورهای تحلیل
- بهینه‌سازی وزن Evidenceها
- بهینه‌سازی Thresholdهای Probability Engine
- بهینه‌سازی فیلترهای ورود
- بهینه‌سازی تنظیمات Market Regime
- بهینه‌سازی پارامترهای ICT
- بهینه‌سازی پارامترهای Liquidity
- بهینه‌سازی پارامترهای Volume
- بهینه‌سازی پارامترهای Structure
- تولید نسخه جدید Knowledge Base

این Optimizer **هرگز** مسئول تعیین SL، TP، Position Size یا Leverage نیست؛ این وظایف فقط متعلق به Risk & Execution Optimizer هستند.

---

# Internal Modules

```
SignalOptimizer

├── DatasetManager
├── SearchSpaceBuilder
├── TrialGenerator
├── ConstraintManager
├── ObjectiveEvaluator
├── ValidationManager
├── StabilityAnalyzer
├── GeneralizationAnalyzer
├── FeatureImportanceAnalyzer
├── KnowledgeExtractor
├── ArtifactBuilder
├── DeploymentCandidateBuilder
└── ReportGenerator
```

---

# Input Dependencies

Signal Optimizer فقط از داده‌های زیر استفاده می‌کند:

```
Historical OHLCV

Indicators

Evidence Reports

ICT Engine

Liquidity Engine

Structure Engine

Momentum Engine

Volume Engine

Order Flow Engine

Probability Engine

Regime Engine

Backtest Engine

Research Engine
```

به هیچ وجه نباید از اطلاعات آینده (Future Leakage) استفاده شود.

---

# Search Space Categories

بهینه‌سازی فقط محدود به Weightها نیست.

Search Space باید شامل تمام پارامترهای قابل تنظیم سیستم باشد.

---

## Group 1 — Evidence Weights

برای تمام Evidenceها:

```
Momentum

Structure

Liquidity

ICT

Order Flow

Volume

Regime

SMT

FVG

Breaker

Market Context

Trend

Confirmation
```

تمام وزن‌ها باید در پایان Normalize شوند تا مجموع آنها برابر 1 باشد.

---

## Group 2 — Probability Thresholds

```
minimum_probability

minimum_confidence

confirmation_threshold

agreement_threshold

reversal_threshold

continuation_threshold
```

---

## Group 3 — ICT Parameters

نمونه:

```
FVG Minimum Size

OB Strength

Breaker Distance

Mitigation Distance

Sweep Buffer

Displacement Size

Premium Discount Zones

OTE Range
```

---

## Group 4 — Liquidity Parameters

```
Liquidity Window

Equal High Sensitivity

Equal Low Sensitivity

Liquidity Sweep Threshold

Liquidity Confirmation

Liquidity Cluster Size
```

---

## Group 5 — Structure Parameters

```
Swing Length

BOS Confirmation

CHOCH Confirmation

Internal Structure Window

External Structure Window

Structure Buffer
```

---

## Group 6 — Momentum Parameters

```
Momentum Period

Momentum Threshold

Acceleration Threshold

Slope Filter
```

---

## Group 7 — Volume Parameters

```
Volume Spike

Relative Volume

Delta Threshold

Volume Imbalance
```

---

## Group 8 — Market Regime

```
Trend Threshold

Range Threshold

Volatility Threshold

Regime Persistence

Regime Confidence
```

---

# Constraints

Search Space باید دارای محدودیت باشد.

مثال:

```
Weight Sum = 1

Probability < 100%

Confidence <= Probability

ATR Multiplier > 0

Thresholds منطقی باشند.
```

هیچ Trial نامعتبر نباید اجرا شود.

---

# Trial Lifecycle

هر Trial دقیقاً مراحل زیر را طی می‌کند:

```
Generate Parameters

↓

Validate Constraints

↓

Inject Parameters

↓

Run Full Historical Backtest

↓

Collect Metrics

↓

Calculate Objective

↓

Run Validation

↓

Store Trial

↓

Rank Trial
```

---

# Objective Function

Objective نباید فقط سود را بیشینه کند.

باید چندهدفه (Multi-objective) باشد.

تابع امتیاز باید ترکیبی از معیارهای زیر باشد:

- Net Profit
- Profit Factor
- Expectancy
- Sharpe Ratio
- Sortino Ratio
- Recovery Factor
- Maximum Drawdown (Penalty)
- Stability Score
- Win Rate
- Average R Multiple
- Trade Quality
- Exposure Efficiency
- Generalization Score

وجود پنالتی برای موارد زیر الزامی است:

- Overfitting
- تعداد معاملات بسیار کم
- Drawdown غیرعادی
- ناپایداری بین Foldها
- سود زیاد همراه با ریسک غیرقابل قبول

---

# Validation Sequence

هر Trial منتخب باید از تمام مراحل زیر عبور کند:

```
Walk Forward

↓

K-Fold Cross Validation

↓

Out-of-Sample Validation

↓

Monte Carlo Simulation

↓

Bootstrap Resampling

↓

Regime Validation

↓

Stress Test

↓

Sensitivity Analysis
```

در صورت رد شدن در هر مرحله، Trial مردود است.

---

# Feature Importance Analysis

پس از پایان Optimization، سیستم باید مشخص کند:

- کدام پارامترها بیشترین اثر را داشته‌اند.
- کدام پارامترها تقریباً بی‌اثر بوده‌اند.
- کدام پارامترها ناپایدار هستند.
- کدام پارامترها وابستگی متقابل دارند.

این تحلیل باید به صورت Artifact ذخیره شود.

---

# Knowledge Extraction

از بهترین Trial فقط پارامتر استخراج نمی‌شود؛ بلکه دانش زیر نیز ذخیره می‌شود:

- رفتار بازار در این Symbol و Timeframe
- حساسیت Evidenceها
- الگوهای موفق
- الگوهای ناموفق
- شرایط شکست
- شرایطی که نباید معامله انجام شود
- پارامترهای پایدار
- پارامترهای ناپایدار

---

# Deployment Candidate

خروجی Signal Optimizer نباید مستقیماً فعال شود.

ابتدا باید به صورت Deployment Candidate ذخیره گردد.

فقط پس از تأیید کامل Validation Pipeline اجازه فعال‌سازی دارد.

---

# Integration Rules

Signal Optimizer باید بتواند بدون تغییر در کد سایر موتورها، پارامترها را از طریق یک لایه Injection به آنها اعمال کند.

هیچ Engine نباید پارامترهای ثابت (Hard-coded) داشته باشد.

تمام پارامترهای قابل تنظیم باید از Configuration Layer یا Artifactهای نسخه‌بندی‌شده خوانده شوند.

---

# Completion Criteria

این بخش تنها زمانی Completed محسوب می‌شود که:

- تمام گروه‌های پارامتر قابل بهینه‌سازی باشند.
- هیچ Future Leakage وجود نداشته باشد.
- Search Space قابل توسعه باشد.
- Objective چندهدفه باشد.
- Validation چندمرحله‌ای اجرا شود.
- Feature Importance تولید گردد.
- Knowledge استخراج شود.
- خروجی فقط از طریق Deployment Pipeline فعال گردد.
- تمامی نتایج Versioned، Auditable و Reproducible باشند.

---

**ادامه در Appendix H: طراحی کامل Risk & Execution Optimizer (معماری داخلی، مدل‌های Stop Loss و Take Profit، Position Sizing، Leverage، Execution Policies، Portfolio Constraints، Dynamic Risk Control و تمامی جزئیات پیاده‌سازی).**

# Appendix H — Risk & Execution Optimizer Complete Architecture (Part 1)

---

# Mission

Risk & Execution Optimizer دومین Optimizer اصلی پروژه APEX است.

برخلاف Signal Optimizer که منطق تولید سیگنال را بهینه می‌کند، این Optimizer مسئول **بهینه‌سازی کل فرآیند ورود، مدیریت معامله، مدیریت سرمایه، مدیریت ریسک و خروج از معامله** است.

این Optimizer هیچ تصمیمی درباره LONG یا SHORT نمی‌گیرد؛ بلکه پس از تأیید سیگنال توسط موتورهای تحلیلی، بهترین روش اجرای آن سیگنال را طراحی می‌کند.

---

# Core Responsibilities

Risk & Execution Optimizer مسئول تمامی موارد زیر است:

- تعیین بهترین Stop Loss
- تعیین بهترین Take Profit
- تعیین تعداد TPها
- تعیین نوع Stop
- تعیین نوع TP
- تعیین Position Size
- تعیین Leverage
- تعیین Risk Percentage
- تعیین مدیریت معامله
- تعیین Break Even
- تعیین Trailing Stop
- تعیین Partial Exit
- تعیین شرایط لغو معامله
- تعیین شرایط عدم ورود
- تعیین سیاست اجرای سفارش
- تعیین سیاست مدیریت سرمایه
- تعیین سیاست مدیریت Drawdown
- تعیین سیاست Portfolio Risk

---

# Internal Architecture

```
RiskExecutionOptimizer

├── EntryAnalyzer
├── StopLossOptimizer
├── TakeProfitOptimizer
├── PositionSizingOptimizer
├── LeverageOptimizer
├── RiskBudgetAllocator
├── TradeLifecycleManager
├── PartialExitPlanner
├── TrailingEngine
├── BreakEvenEngine
├── PortfolioRiskManager
├── CorrelationManager
├── ExposureManager
├── DrawdownController
├── ExecutionPolicyEngine
├── TradeValidator
├── ExecutionSimulator
├── KnowledgeExtractor
├── ArtifactBuilder
└── ReportGenerator
```

---

# Input Dependencies

این Optimizer باید اطلاعات خود را از بخش‌های زیر دریافت کند:

```
Decision Engine

Probability Engine

Evidence Report

Market Structure

Liquidity Engine

ICT Engine

Order Flow

Momentum

Volume

ATR

Volatility

Spread

Exchange Constraints

Portfolio State

Account Balance

Open Positions

Historical Optimization Artifacts
```

هیچ مقدار ثابت (Hard-coded) مجاز نیست.

---

# Entry Analysis

قبل از طراحی معامله باید کیفیت ورود بررسی شود.

پارامترهای بررسی:

- Probability
- Confidence
- Evidence Agreement
- Market Regime
- Volatility
- Liquidity
- Distance تا BOS
- Distance تا OB
- Distance تا FVG
- Distance تا Liquidity Pool
- Session
- Spread
- Funding
- Correlation با معاملات باز

اگر کیفیت ورود پایین باشد، معامله لغو می‌شود حتی اگر سیگنال معتبر باشد.

---

# Stop Loss Optimization

سیستم نباید فقط یک مدل Stop داشته باشد.

بلکه باید چندین مدل را محاسبه کرده و بهترین را انتخاب کند.

مدل‌های الزامی:

```
ATR Stop

Swing Stop

Structure Stop

Liquidity Stop

ICT Stop

Order Block Stop

FVG Stop

Breaker Stop

Hybrid Stop

Adaptive Stop
```

---

# Hybrid Stop Logic

Hybrid Stop باید بتواند چند مدل را ترکیب کند.

مثال:

```
Candidate1 = ATR

Candidate2 = Swing

Candidate3 = Liquidity

Candidate4 = ICT

↓

Risk Scoring

↓

Best Candidate

↓

Safety Buffer

↓

Final Stop
```

---

# Stop Evaluation Criteria

هر Stop باید با معیارهای زیر امتیازدهی شود:

- احتمال فعال شدن
- فاصله از نویز بازار
- نسبت R/R
- محل لیکوییدیتی
- ساختار بازار
- ATR
- نوسان
- ریسک مالی
- کیفیت تاریخی

بهترین گزینه انتخاب می‌شود.

---

# Take Profit Optimization

TP نباید ثابت باشد.

سیستم باید چندین هدف مختلف را تولید کند.

مدل‌های مجاز:

```
Liquidity TP

ATR TP

Structure TP

OrderBlock TP

FVG TP

Swing TP

Measured Move TP

Volatility TP

Adaptive TP
```

---

# Multi-Level Exit

سیستم باید بتواند خروج چندمرحله‌ای تولید کند.

مثال:

```
TP1

TP2

TP3

TP4

Runner
```

برای هر سطح باید موارد زیر ذخیره شود:

- حجم خروج
- R Multiple
- احتمال رسیدن
- Expected Return
- فاصله زمانی مورد انتظار

---

# Exit Allocation

مثال:

```
TP1 = 25%

TP2 = 25%

TP3 = 20%

TP4 = 15%

Runner = 15%
```

این مقادیر نیز باید توسط Optimizer قابل بهینه‌سازی باشند و نباید ثابت باشند.

---

# Position Size Optimization

Position Size فقط بر اساس سرمایه تعیین نمی‌شود.

باید از ترکیب عوامل زیر استفاده شود:

- Kelly Fraction
- Half Kelly
- Confidence
- Probability
- Volatility
- Current Drawdown
- Portfolio Exposure
- Correlation
- Regime Risk
- Maximum Daily Risk

---

# Position Sizing Models

حداقل مدل‌های زیر باید وجود داشته باشند:

```
Fixed Fractional

Kelly

Half Kelly

Volatility Adjusted

ATR Based

Confidence Based

Portfolio Adjusted

Adaptive Hybrid
```

Risk & Execution Optimizer باید بتواند بین این مدل‌ها انتخاب کرده یا آنها را به‌صورت ترکیبی به کار گیرد.

---

# Dynamic Risk Percentage

درصد ریسک هر معامله نباید ثابت باشد.

باید بر اساس:

- کیفیت سیگنال
- وضعیت بازار
- وضعیت حساب
- وضعیت پرتفوی
- میزان Drawdown
- همبستگی معاملات
- نوسانات فعلی

به‌صورت پویا تعیین شود.

---

# Completion Criteria (Part 1)

این بخش تنها زمانی Completed محسوب می‌شود که:

- تمامی مدل‌های Stop پیاده‌سازی شده باشند.
- تمامی مدل‌های TP پیاده‌سازی شده باشند.
- Position Sizing کاملاً پویا باشد.
- Risk Percentage پویا باشد.
- تمامی پارامترها از طریق Artifactهای نسخه‌بندی‌شده قابل تنظیم باشند.
- هیچ مقدار Hard-coded در منطق مدیریت ریسک باقی نماند.

---

**ادامه در Appendix H (Part 2): Trailing Stop، Break-Even، Portfolio Risk Management، Correlation Control، Execution Policies، سفارش‌گذاری در Toobit Futures، مدیریت همزمان معاملات، Artifactهای خروجی، Validation، Testing و Integration کامل.**

# Appendix H — Risk & Execution Optimizer Complete Architecture (Part 2)

---

# Trailing Stop Engine

Trailing Stop نباید یک الگوریتم ثابت باشد.

بلکه باید بتواند بر اساس نوع بازار، رفتار قیمت و وضعیت معامله، مناسب‌ترین مدل را انتخاب نماید.

مدل‌های الزامی:

```
ATR Trailing

Swing Trailing

Structure Trailing

Liquidity Trailing

Moving Average Trailing

Volatility Trailing

Time Based Trailing

Adaptive Hybrid Trailing
```

هر مدل باید مستقل قابل بهینه‌سازی باشد.

---

# Break-Even Engine

جابجایی Stop به نقطه سر به سر نباید صرفاً پس از رسیدن قیمت به مقدار مشخصی انجام شود.

شرایط انتقال باید تابعی از:

- احتمال موفقیت معامله
- کیفیت سیگنال
- میزان سود تحقق‌نیافته
- وضعیت ساختار بازار
- نوسانات
- Liquidity
- Regime

باشد.

پارامترهای قابل بهینه‌سازی:

```
BreakEven Trigger

BreakEven Offset

Minimum Profit

Confirmation Requirement

Partial Exit Dependency
```

---

# Trade Lifecycle Manager

هر معامله باید دارای چرخه حیات مشخص باشد.

```
Signal Approved

↓

Entry Waiting

↓

Order Submitted

↓

Order Filled

↓

Risk Monitoring

↓

Partial Exit

↓

Trailing

↓

Break Even

↓

Final Exit

↓

Trade Closed

↓

Knowledge Extraction
```

هیچ مرحله‌ای نباید حذف شود.

---

# Portfolio Risk Manager

مدیریت ریسک فقط در سطح یک معامله انجام نمی‌شود.

کل پرتفوی باید همواره کنترل گردد.

شاخص‌های الزامی:

```
Portfolio Exposure

Symbol Exposure

Sector Exposure

Net Exposure

Gross Exposure

Directional Bias

Margin Usage

Available Equity

Open Risk

Expected Portfolio Drawdown
```

---

# Correlation Manager

قبل از ورود معامله جدید باید همبستگی آن با معاملات باز بررسی گردد.

روش‌های مجاز:

```
Pearson

Spearman

Rolling Correlation

Dynamic Correlation Matrix
```

اگر همبستگی از حد تعیین‌شده بیشتر باشد:

- کاهش Position Size
- یا رد معامله

باید به صورت خودکار انجام شود.

---

# Exposure Manager

برای هر Symbol، گروه دارایی و کل حساب محدودیت‌های مستقل تعریف شود.

نمونه:

```
Maximum Exposure Per Symbol

Maximum Exposure Per Direction

Maximum Total Long Exposure

Maximum Total Short Exposure

Maximum Portfolio Exposure
```

تمام این حدود باید توسط Risk Optimizer قابل تنظیم باشند.

---

# Drawdown Controller

سیستم باید به صورت تطبیقی نسبت به افت سرمایه واکنش نشان دهد.

نمونه رفتار:

```
Drawdown < 5%
↓

Normal Risk

5% ≤ Drawdown < 10%
↓

Risk × 0.75

10% ≤ Drawdown < 15%
↓

Risk × 0.50

15% ≤ Drawdown
↓

Trading Suspension Candidate
```

آستانه‌ها نیز باید قابل بهینه‌سازی باشند.

---

# Execution Policy Engine

برای هر معامله بهترین روش ارسال سفارش انتخاب شود.

گزینه‌های پشتیبانی‌شده:

```
Market

Limit

Post Only

Reduce Only

IOC

FOK

Stop Market

Stop Limit
```

انتخاب سیاست اجرا باید تابعی از:

- نقدشوندگی
- اسپرد
- نوسانات
- اندازه سفارش
- شرایط بازار

باشد.

---

# Slippage Protection

پیش از ارسال سفارش موارد زیر ارزیابی شوند:

- Spread
- Book Depth
- Estimated Slippage
- Liquidity Availability

در صورت عبور از حدود مجاز:

```
Reduce Position

Delay Entry

Reject Trade
```

---

# Toobit Integration Contract

Execution Optimizer نباید مستقیماً API صرافی را فراخوانی کند.

بلکه باید یک **Trade Blueprint** استاندارد تولید نماید که توسط Execution Layer مصرف شود.

نمونه:

```yaml
trade_blueprint:
  symbol:
  side:
  entry_type:
  leverage:
  position_size:
  stop_model:
  stop_loss:
  take_profits:
  trailing_policy:
  break_even_policy:
  risk_budget:
  metadata:
```

---

# Validation Pipeline

هر مدل ریسک باید علاوه بر Backtest از آزمون‌های زیر عبور کند:

```
Walk Forward

↓

Monte Carlo

↓

Stress Test

↓

Liquidity Stress

↓

High Volatility Test

↓

Gap Simulation

↓

Latency Simulation

↓

Exchange Constraint Test
```

---

# Knowledge Extraction

پس از پایان هر Optimization اطلاعات زیر استخراج شود:

- موفق‌ترین مدل‌های Stop
- موفق‌ترین مدل‌های TP
- بهترین Position Sizing
- رفتار هر Regime
- حساسیت پارامترها
- علل شکست
- دلایل خروج زودهنگام
- دلایل فعال شدن Stop

---

# Artifact Structure

خروجی Risk Optimizer باید شامل بخش‌های زیر باشد:

```
Risk Models

Execution Models

Position Models

Portfolio Policies

Validation Results

Performance Metrics

Knowledge Summary

Metadata

Version

Signature
```

---

# Integration Rules

Risk & Execution Optimizer باید بدون تغییر در سایر Engineها قابل اتصال باشد.

ارتباط فقط از طریق Interfaceهای رسمی و Data Contractهای تعریف‌شده انجام شود.

هیچ وابستگی مستقیم (Tight Coupling) مجاز نیست.

---

# Testing Requirements

حداقل آزمون‌های الزامی:

- Unit Tests
- Integration Tests
- Property-Based Tests
- Regression Tests
- Replay Tests
- Exchange Mock Tests
- Performance Tests
- Memory Leak Tests
- Recovery Tests
- Rollback Tests

---

# Production Safety

نسخه جدید فقط زمانی فعال شود که:

- تمامی Validationها PASS باشند.
- نسبت به نسخه فعال بهبود معنادار داشته باشد.
- ریسک سیستم افزایش نیافته باشد.
- Artifact امضا و نسخه‌بندی شده باشد.
- Health Check پس از استقرار موفق باشد.

---

# Final Completion Criteria

Risk & Execution Optimizer تنها زمانی Completed محسوب می‌شود که:

- تمامی مدل‌های مدیریت ریسک، ورود و خروج به‌صورت پویا و قابل بهینه‌سازی پیاده‌سازی شده باشند.
- مدیریت پرتفوی، همبستگی، اکسپوژر و افت سرمایه به‌صورت یکپارچه کنترل شوند.
- اتصال به موتور اجرا فقط از طریق Trade Blueprint استاندارد انجام شود.
- کل زیرسیستم دارای Validation، Audit، Versioning، Rollback و Testing کامل باشد.
- هیچ مقدار ثابت، Placeholder، Stub یا TODO در کد باقی نمانده باشد.

---

**ادامه در Appendix I: طراحی کامل Meta Optimization Orchestrator، زمان‌بندی هوشمند، سیاست اجرای بهینه‌سازی برای ۱۰ دارایی و ۱۴ تایم‌فریم، مدیریت منابع روی Termux/Android، برنامه‌ریزی چرخه‌های بهینه‌سازی و هماهنگی میان دو Optimizer.**

# Appendix I — Meta Optimization Orchestrator, Intelligent Scheduling, Resource Management, Adaptive Optimization Cycles & Production Orchestration

---

# Mission

Meta Optimization Orchestrator مغز مدیریتی کل زیرسیستم Optimization است.

دو Optimizer اصلی (Signal Optimizer و Risk & Execution Optimizer) هیچ‌گاه مستقیماً اجرا نمی‌شوند.

تمام عملیات فقط توسط این Orchestrator برنامه‌ریزی، زمان‌بندی، هماهنگ، پایش و مدیریت می‌شود.

هدف اصلی:

- بیشترین کیفیت Optimization
- کمترین مصرف CPU
- کمترین مصرف RAM
- کمترین مصرف باتری
- عدم اختلال در Live Trading
- قابلیت Resume
- قابلیت Recovery
- قابلیت Scale

---

# High-Level Architecture

```
Optimization Scheduler
          │
          ▼
Job Planner
          │
          ▼
Priority Manager
          │
          ▼
Resource Manager
          │
          ▼
Optimization Queue
          │
          ▼
Signal Optimizer
          │
          ▼
Risk Optimizer
          │
          ▼
Validation
          │
          ▼
Deployment Manager
```

---

# Internal Modules

```
MetaOptimizationOrchestrator

├── Scheduler
├── QueueManager
├── ResourceMonitor
├── DeviceProfiler
├── JobPlanner
├── DependencyResolver
├── RetryManager
├── FailureManager
├── DeploymentCoordinator
├── HealthMonitor
├── AuditLogger
└── NotificationManager
```

---

# Optimization Scope

بهینه‌سازی باید برای هر ترکیب Symbol و Timeframe مستقل انجام شود.

هیچ پارامتری بین دارایی‌های مختلف به اشتراک گذاشته نشود.

---

# Supported Assets

```
BTCUSDT
ETHUSDT
BNBUSDT
SOLUSDT
XRPUSDT
DOGEUSDT
ADAUSDT
TRXUSDT
LINKUSDT
AVAXUSDT
```

(یا هر ۱۰ دارایی منتخب پروژه)

---

# Timeframe Policy

### BTC

به دلیل نقش مرجع بازار:

تمام ۱۴ تایم‌فریم موجود در Toobit باید بهینه شوند.

---

### سایر دارایی‌ها

به‌صورت پیش‌فرض:

```
1m
5m
15m
1h
4h
1d
```

اما این لیست باید قابل تغییر از طریق Configuration باشد.

---

# Independent Optimization Policy

برای هر ترکیب:

```
BTC + 1H

ETH + 1H

SOL + 1H
```

سه Optimization کاملاً مستقل ایجاد می‌شود.

نتایج هرگز بین آنها منتقل نمی‌شود.

---

# Optimization Lifecycle

هر Job شامل مراحل زیر است:

```
Create

↓

Prepare Dataset

↓

Signal Optimization

↓

Validation

↓

Risk Optimization

↓

Validation

↓

Knowledge Extraction

↓

Artifact Generation

↓

Deployment Candidate

↓

Archive
```

---

# Adaptive Scheduling

Scheduler نباید زمان‌بندی ثابت داشته باشد.

بلکه باید بر اساس شرایط سیستم تصمیم بگیرد.

پارامترهای تصمیم:

- Battery Level
- Charging Status
- CPU Usage
- RAM Usage
- Device Temperature
- Active Trading
- Telegram Activity
- Pending Jobs

---

# Android / Termux Policy

در صورت اجرا روی موبایل:

اگر:

- باتری کمتر از حد تعیین‌شده باشد،
- دستگاه در حال شارژ نباشد،
- یا فشار پردازشی زیاد باشد،

Optimization به تعویق بیفتد.

---

# Optimization Budget

هر اجرا دارای بودجه منابع است:

```
Max CPU

Max RAM

Max Runtime

Max Temperature

Max Battery Usage
```

در صورت عبور از حدود، Job به‌صورت کنترل‌شده Pause یا Resume شود، نه اینکه از ابتدا تکرار گردد.

---

# Queue Strategy

اولویت پیش‌فرض:

```
BTC (14 TF)

↓

ETH

↓

BNB

↓

SOL

↓

XRP

↓

...

```

داخل هر دارایی نیز تایم‌فریم‌ها بر اساس اهمیت مرتب شوند.

---

# Incremental Optimization

اگر Dataset یک Symbol تغییر نکرده باشد و Drift نیز تشخیص داده نشود، اجرای مجدد Optimization الزامی نیست.

این سیاست باعث کاهش مصرف منابع می‌شود.

---

# Drift-Driven Execution

Optimization جدید فقط در یکی از شرایط زیر آغاز شود:

- پایان دوره زمان‌بندی‌شده
- تشخیص Drift
- تغییر محسوس Regime
- درخواست دستی کاربر
- تغییر Blueprint یا Search Space
- تغییر نسخه Engineها

---

# Retry Policy

در صورت شکست:

```
Retry #1

↓

Retry #2

↓

Retry #3

↓

Failure Archive

↓

Notification
```

هر Retry باید دلیل شکست قبلی را ثبت کند.

---

# Deployment Coordination

در هر لحظه فقط یک نسخه Active وجود دارد.

نسخه جدید ابتدا در حالت Candidate باقی می‌ماند.

پس از عبور از تمام Validationها و Health Check، به نسخه Active تبدیل می‌شود.

---

# Notifications

Orchestrator باید بتواند رویدادهای مهم را گزارش کند:

- شروع Optimization
- پایان موفق
- شکست
- Rollback
- Drift Detection
- Deployment
- Health Warning

این گزارش‌ها باید برای Telegram و Log داخلی قابل استفاده باشند.

---

# Completion Metrics

موفقیت Orchestrator فقط بر اساس پایان Trialها سنجیده نمی‌شود.

شاخص‌های کلیدی:

- Success Rate
- Average Runtime
- Resource Efficiency
- Acceptance Rate
- Deployment Success
- Recovery Success
- Rollback Success
- Queue Latency

---

# Final Acceptance Criteria

Meta Optimization Orchestrator تنها زمانی Completed محسوب می‌شود که:

- اجرای دو Optimizer را به‌صورت کامل مدیریت کند.
- برای هر Symbol و Timeframe چرخه مستقل داشته باشد.
- منابع دستگاه را به‌صورت تطبیقی مدیریت کند.
- در برابر Crash قابل بازیابی باشد.
- هیچ تداخلی با Live Trading ایجاد نکند.
- تمام عملیات قابل Audit، Versioning، Resume و Rollback باشند.
- هیچ بخش Placeholder، Stub یا TODO در پیاده‌سازی باقی نمانده باشد.

---

**ادامه در Appendix J: Testing Framework، Benchmark Suite، Validation Matrix، Production Acceptance Tests، KPIهای نهایی، معیارهای تحویل و Definition of Done برای کل زیرسیستم Optimization.**

# Appendix J — Testing Framework, Validation Matrix, Benchmark Suite, Production Acceptance & Definition of Done

---

# Mission

هیچ Optimizer صرفاً به دلیل اجرا شدن یا یافتن پارامترهای جدید، موفق تلقی نمی‌شود.

هر نسخه باید پیش از ورود به Production از چندین لایه اعتبارسنجی، آزمون، Benchmark، تحلیل آماری و کنترل کیفیت عبور کند.

هدف این فصل تضمین آن است که هیچ نسخه‌ای موجب کاهش کیفیت سیستم، افزایش ریسک یا ایجاد رفتار غیرقابل پیش‌بینی نشود.

---

# Multi-Layer Validation Pipeline

هر Artifact تولیدشده توسط Signal Optimizer یا Risk & Execution Optimizer باید به ترتیب از مراحل زیر عبور کند:

```
Parameter Validation
        │
        ▼
Configuration Validation
        │
        ▼
Historical Backtest
        │
        ▼
Walk-Forward Validation
        │
        ▼
Cross Validation
        │
        ▼
Monte Carlo Simulation
        │
        ▼
Stress Testing
        │
        ▼
Liquidity Simulation
        │
        ▼
Execution Simulation
        │
        ▼
Shadow Deployment
        │
        ▼
Production Candidate
```

هیچ مرحله‌ای نباید حذف یا Skip شود.

---

# Unit Testing

تمام ماژول‌های Optimization باید دارای تست واحد باشند.

حداقل پوشش:

- Search Space
- Objective Function
- Samplers
- Pruners
- Parameter Constraints
- Serialization
- Resume
- Checkpoint
- Artifact Writer
- Deployment Loader

هدف:

```
Code Coverage ≥ 95%
```

---

# Integration Testing

باید بررسی شود که Optimizer با تمام زیرسیستم‌ها بدون اختلال کار می‌کند.

لیست الزامی:

```
Probability Engine

Evidence Engine

Research Engine

Backtest Engine

Knowledge Base

Risk Engine

Execution Engine

Telegram Layer

Configuration System

Persistence Layer
```

---

# Regression Testing

هر نسخه جدید باید روی مجموعه ثابتی از داده‌های مرجع اجرا شود.

در صورت کاهش عملکرد نسبت به Baseline:

```
Deployment = Rejected
```

---

# Historical Replay Testing

Replay باید Tick-by-Tick یا Candle-by-Candle انجام شود.

هیچ Shortcut مجاز نیست.

Replay باید دقیقاً همان داده‌هایی را مصرف کند که سیستم Live دریافت می‌کند.

---

# Walk-Forward Validation

برای جلوگیری از Overfitting:

```
Train

↓

Validate

↓

Roll Window

↓

Repeat
```

پیاده‌سازی باید از پنجره‌های زمانی متحرک استفاده کند.

---

# Cross Validation

در صورت امکان داده‌ها به چند Fold تقسیم شوند.

هر Fold یک Optimization مستقل تولید کند.

پایداری پارامترها بررسی شود.

---

# Monte Carlo Validation

پارامترهای منتخب باید تحت هزاران سناریوی تصادفی آزمایش شوند.

نمونه‌ها:

- Random Trade Order
- Bootstrap Sampling
- Random Missing Candles
- Random Slippage
- Random Spread
- Random Latency

هدف:

اندازه‌گیری Robustness.

---

# Stress Testing

سناریوهای الزامی:

```
Extreme Volatility

Flash Crash

Flash Pump

Exchange Freeze

API Delay

Network Failure

Gap

Liquidity Collapse

Massive Spread

Partial Fill
```

Optimizer باید در تمام این شرایط رفتار قابل قبول داشته باشد.

---

# Sensitivity Analysis

برای هر پارامتر بهینه‌شده باید حساسیت سیستم اندازه‌گیری شود.

خروجی:

```
Parameter Importance

Local Sensitivity

Global Sensitivity

Interaction Effects
```

پارامترهایی که بسیار حساس هستند باید علامت‌گذاری شوند.

---

# Stability Analysis

نسخه جدید نباید فقط سود بیشتری داشته باشد.

بلکه باید پایدارتر نیز باشد.

شاخص‌های الزامی:

- Variance
- Standard Deviation
- Stability Score
- Robustness Score
- Confidence Interval

---

# Benchmark Suite

نسخه جدید باید با نسخه‌های زیر مقایسه شود:

```
Baseline

Previous Active

Previous Candidate

Random Parameters

Default Parameters
```

---

# KPI Evaluation

شاخص‌های اصلی:

```
Net Profit

Profit Factor

Expectancy

Sharpe Ratio

Sortino Ratio

Calmar Ratio

Max Drawdown

Average Drawdown

Recovery Factor

Win Rate

Average R

Average Holding Time

Trade Count

Exposure Efficiency

Risk Efficiency
```

---

# Signal Quality Metrics

ویژه Signal Optimizer:

```
Precision

Recall

F1 Score

ROC AUC

Calibration Error

Probability Reliability

False Positive Rate

False Negative Rate
```

---

# Risk Metrics

ویژه Risk Optimizer:

```
Average RR

Effective RR

Stop Efficiency

Trailing Efficiency

BreakEven Efficiency

Capital Utilization

Position Sizing Accuracy

Risk Consistency
```

---

# Drift Validation

قبل از پذیرش نسخه جدید بررسی شود:

- آیا بازار تغییر کرده است؟
- آیا پارامترهای قبلی هنوز معتبرند؟
- آیا Drift رخ داده است؟

در صورت عدم وجود Drift ممکن است Deployment جدید ضروری نباشد.

---

# Shadow Deployment

قبل از فعال‌سازی واقعی:

نسخه جدید باید به‌صورت Shadow اجرا شود.

```
Active Version

↓

Shadow Version

↓

Compare Outputs

↓

Promote Candidate
```

در Shadow هیچ سفارشی ارسال نمی‌شود.

---

# Rollback Testing

باید اطمینان حاصل شود که بازگشت به نسخه قبلی در هر لحظه ممکن است.

Rollback باید:

- Atomic
- Safe
- Auditable
- Versioned

باشد.

---

# Artifact Verification

هر Artifact باید شامل:

```
Metadata

Version

Blueprint Version

Dataset Hash

Configuration Hash

Git Commit

Timestamp

Checksum

Digital Signature
```

باشد.

در صورت عدم تطابق Hash:

```
Artifact Invalid
```

---

# Production Acceptance Checklist

قبل از فعال‌سازی:

✓ تمام تست‌ها PASS

✓ تمام Validationها PASS

✓ Benchmark بهتر از Baseline

✓ Overfitting مشاهده نشده

✓ Drift بررسی شده

✓ Artifact معتبر

✓ Health Check موفق

✓ Rollback آماده

✓ Audit ثبت شده

---

# Continuous Monitoring

پس از Deployment نیز عملکرد نسخه باید دائماً پایش شود.

شاخص‌ها:

- Live Performance
- Prediction Drift
- Risk Drift
- Resource Usage
- Failure Rate
- Exception Count
- Latency
- Memory Consumption

در صورت مشاهده افت معنادار، Candidate به‌صورت خودکار غیرفعال و آخرین نسخه پایدار بازیابی شود.

---

# Documentation Requirements

هر نسخه باید مستندات کامل تولید کند:

```
Optimization Report

Parameter Report

Validation Report

Benchmark Report

Knowledge Summary

Deployment Report

Audit Report

Change Log
```

تمام گزارش‌ها باید Machine-Readable و Human-Readable باشند.

---

# Definition of Done (DoD)

زیرسیستم Optimization تنها زمانی 100% Completed محسوب می‌شود که:

- هر دو Optimizer (Signal Optimizer و Risk & Execution Optimizer) به‌صورت مستقل، ماژولار و قابل توسعه پیاده‌سازی شده باشند.
- Meta Optimization Orchestrator چرخه کامل زمان‌بندی، مدیریت منابع، صف، Resume، Retry و Deployment را مدیریت کند.
- تمام پارامترها، سیاست‌ها و مدل‌ها قابل بهینه‌سازی بوده و هیچ مقدار Hard-Coded وجود نداشته باشد مگر در مواردی که در Blueprint صراحتاً ثابت تعریف شده‌اند.
- سیستم دارای Validation چندلایه، Benchmark، آزمون‌های آماری، Stress Test، Shadow Deployment، Rollback و Audit کامل باشد.
- نتایج بهینه‌سازی برای هر Symbol و Timeframe به‌صورت مستقل نسخه‌بندی، ذخیره و بارگذاری شوند.
- هیچ Placeholder، Stub، TODO، Mock یا پیاده‌سازی ناقص در کد باقی نمانده باشد.
- هیچ تغییری باعث شکست Backward Compatibility یا اختلال در سایر Engineها نشود.
- کل زیرسیستم با معماری APEX، قراردادهای داده (Data Contracts)، Interfaceها و Blueprintهای اصلی کاملاً منطبق باشد.
- تمام قابلیت‌ها دارای تست، مستندات، لاگ، نسخه‌بندی و قابلیت نگهداری (Maintainability) باشند.
- زیرسیستم آماده استقرار در محیط Production بدون نیاز به بازطراحی معماری باشد.

---

# End of Optimization Blueprint

این فصل پایان مشخصات فنی زیرسیستم Optimization است. هرگونه توسعه آینده (مانند Reinforcement Learning، Multi-Agent Optimization یا Online Continual Learning) باید به‌صورت ماژول‌های افزوده و بدون نقض قراردادهای تعریف‌شده در این سند انجام شود.

