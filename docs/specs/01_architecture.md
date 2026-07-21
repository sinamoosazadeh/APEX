کتاب طراحی سیستم
APEX - Autonomous Probabilistic Execution eXchange
Volume I
Complete Technical Design Specification
نسخه 1.0
---
فصل 1
فلسفه طراحی سیستم
---
1.1 مقدمه
این پروژه یک اندیکاتور، یک استراتژی، یک ربات معامله‌گر یا حتی یک موتور تولید سیگنال نیست.
هدف این پروژه طراحی یک سیستم تصمیم‌گیری هوشمند چندلایه برای بازارهای مالی است که بتواند با استفاده از داده‌های خام، دانش آماری، مدل‌های احتمالاتی، منطق Smart Money، تحلیل ساختاری، یادگیری تطبیقی و بهینه‌سازی چندهدفه، بهترین تصمیم معاملاتی ممکن را در هر لحظه اتخاذ کند.
در این معماری، «سیگنال خرید یا فروش» یک محصول نهایی است، نه هسته سیستم.
هسته واقعی سیستم، درک وضعیت بازار (Market Understanding) و تخمین احتمال آینده (Future State Estimation) است.
---
1.2 هدف نهایی
سیستم باید بتواند در هر لحظه به سؤال زیر پاسخ دهد:
> "اگر اکنون وارد معامله شوم، احتمال موفقیت این معامله نسبت به تمام اطلاعات موجود چقدر است؟"
اما این احتمال نباید حاصل چند قانون ثابت باشد.
بلکه باید نتیجه ترکیب هزاران Feature، ده‌ها مدل احتمالاتی، چندین موتور تصمیم‌گیری و تاریخچه کامل عملکرد سیستم باشد.
---
1.3 تفاوت با اندیکاتورهای معمول
اکثر اندیکاتورها این روند را طی می‌کنند:
Price
↓
Indicator
↓
Signal
اما این پروژه چنین معماری‌ای نخواهد داشت.
معماری واقعی به صورت زیر خواهد بود:
Market
↓
Data Acquisition
↓
Data Validation
↓
Feature Engineering
↓
Feature Store
↓
Market State Engine
↓
Market Context Engine
↓
Liquidity Engine
↓
Orderflow Engine
↓
Structure Engine
↓
SMT Engine
↓
Pattern Engine
↓
Statistical Engine
↓
Probability Engine
↓
AI Ensemble
↓
Alpha Engine
↓
Signal Optimizer
↓
Risk Optimizer
↓
Execution Optimizer
↓
Execution Simulator
↓
Performance Engine
↓
Feedback Engine
↓
Learning Engine
↓
Database
↓
Next Decision
بنابراین هیچ تصمیمی مستقیماً از روی قیمت گرفته نخواهد شد.
---
1.4 اصول طراحی
کل پروژه بر اساس چند اصل تغییرناپذیر ساخته می‌شود.
---
اصل اول
Everything is Data
هیچ چیزی نباید به صورت ثابت در کد وجود داشته باشد.
حتی وزن‌ها.
حتی Threshold ها.
حتی پارامترها.
همه باید داده باشند.
---
اصل دوم
Every Decision must have Probability
هیچ تصمیمی Binary نیست.
نباید بنویسیم:
if Bullish
Buy
بلکه باید بنویسیم:
Probability(Bullish)
Confidence
Reliability
Sample Size
Expected Return
Risk
---
اصل سوم
Every Module must Explain Itself
هر ماژول باید بتواند توضیح دهد:
چرا این خروجی را تولید کرده است.
مثلاً:
Signal
↓
83%
↓
Why?
↓
Liquidity
22%
↓
HTF
18%
↓
SMT
14%
↓
Trend
11%
↓
Orderflow
8%
↓
Volume
6%
...
بنابراین سیستم Explainable خواهد بود.
---
اصل چهارم
No Module is Trusted
هیچ موتور تصمیم‌گیری نباید حقیقت مطلق تلقی شود.
حتی اگر Accuracy آن ۹۵٪ باشد.
تمام خروجی‌ها باید توسط موتور اجماع اعتبارسنجی شوند.
---
اصل پنجم
Continuous Learning
سیستم نباید بعد از اجرا ثابت بماند.
هر معامله باید سیستم را تغییر دهد.
---
اصل ششم
Everything must be Adaptive
پارامتر ثابت وجود ندارد.
بازار تغییر می‌کند.
سیستم نیز باید تغییر کند.
---
اصل هفتم
Context before Signal
قبل از تولید سیگنال باید بازار شناخته شود.
مثلاً:
Trend
Range
Distribution
Accumulation
Compression
Expansion
Manipulation
High Volatility
Low Volatility
News
Panic
Capitulation
اگر Context اشتباه باشد،
تمام سیگنال‌ها اشتباه خواهند بود.
---
اصل هشتم
Risk before Profit
سیستم ابتدا باید بررسی کند:
اگر این معامله اشتباه باشد
چقدر ضرر خواهیم کرد.
سپس بررسی کند:
اگر درست باشد
چقدر سود خواهیم کرد.
---
اصل نهم
Every Signal must Compete
هیچ سیگنالی نباید مستقیماً منتشر شود.
ابتدا باید با تمام سیگنال‌های دیگر رقابت کند.
فقط بهترین آنها انتخاب شود.
---
اصل دهم
Evidence is more important than Rules
قانون مهم نیست.
مدرک مهم است.
مثلاً:
وجود Order Block
به تنهایی دلیل خرید نیست.
وجود FVG
دلیل خرید نیست.
وجود SMT
دلیل خرید نیست.
بلکه تمام اینها باید تبدیل شوند به Evidence.
سپس Evidenceها وارد موتور اجماع شوند.
---
1.5 تعریف سیستم
از این لحظه به بعد،
این پروژه دیگر Indicator نیست.
تعریف رسمی آن:
> An Adaptive Multi-Agent Quantitative Decision System for Cryptocurrency Markets
---
1.6 اهداف عملکردی
این سیستم باید بتواند:
بازار را در چند سطح زمانی به صورت همزمان تحلیل کند.
ساختار بازار را استخراج کند.
نقدینگی را مدل‌سازی کند.
رفتار بازیگران بزرگ را تخمین بزند.
داده‌های Order Flow را تحلیل کند.
احتمال موفقیت هر سناریو را محاسبه کند.
پارامترهای خود را به صورت پویا تنظیم کند.
ریسک هر معامله را قبل از ورود برآورد کند.
روش اجرای سفارش را بهینه کند.
از نتایج گذشته یاد بگیرد.
در برابر تغییر رژیم بازار سازگار شود.
عملکرد خود را به طور مداوم ارزیابی و کالیبره کند.
---
1.7 اصل طراحی ماژولار
هر بخش باید یک ماژول مستقل باشد.
هیچ ماژولی نباید مستقیماً به جزئیات داخلی ماژول دیگر وابسته باشد.
ارتباط فقط از طریق Interfaceهای مشخص انجام می‌شود.
بنابراین هر ماژول باید:
ورودی‌های مشخص داشته باشد.
خروجی‌های مشخص داشته باشد.
وضعیت داخلی خود را مدیریت کند.
خطاهای خود را گزارش دهد.
نسخه (Version) مستقل داشته باشد.
قابلیت جایگزینی بدون تغییر سایر بخش‌ها را داشته باشد.
---
1.8 اصل جداسازی مسئولیت‌ها (Single Responsibility)
هر موتور فقط یک مسئولیت اصلی خواهد داشت. برای مثال:
Data Layer فقط مسئول جمع‌آوری، اعتبارسنجی و همگام‌سازی داده‌ها است.
Feature Engineering فقط مسئول استخراج ویژگی‌ها است.
Market State Engine فقط مسئول تشخیص رژیم بازار است.
Signal Engine فقط مسئول تولید فرضیه‌های معاملاتی (Hypotheses) است.
Alpha Optimizer فقط مسئول بهینه‌سازی پارامترهای تولید سیگنال است.
Risk & Execution Optimizer فقط مسئول انتخاب بهترین روش مدیریت ریسک و اجرای سفارش است.
Feedback Engine فقط مسئول ثبت نتایج و ارسال آن‌ها به موتور یادگیری است.
این اصل مانع از ایجاد وابستگی‌های پنهان، پیچیدگی غیرقابل کنترل و دشواری در تست و نگهداری سیستم می‌شود.
---
پایان فصل اول
در بخش بعدی، فصل دوم: معماری کلان سیستم (System Architecture Blueprint) آغاز می‌شود و ساختار کامل سیستم، لایه‌ها، قراردادهای ارتباطی، چرخه عمر داده، مدل اجرای ماژول‌ها، مدیریت همزمانی (Concurrency)، معماری رویدادمحور (Event-Driven) و جریان کامل اطلاعات از ورود داده تا تصمیم نهایی به‌صورت مهندسی و با جزئیات طراحی خواهد شد.
کتاب طراحی سیستم
APEX - Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 2
معماری کلان سیستم (System Architecture Blueprint)
---
2.1 مقدمه
در این پروژه، هیچ ماژولی مستقیماً مسئول تولید سیگنال نیست.
برخلاف اکثر ربات‌های معامله‌گر، سیستم نباید از روی داده خام مستقیماً به تصمیم برسد.
بلکه باید ابتدا بازار را درک کند.
سپس وضعیت آن را مدل‌سازی کند.
سپس آینده را تخمین بزند.
سپس کیفیت تخمین را اعتبارسنجی کند.
سپس بهترین پارامترها را بهینه کند.
سپس ریسک را محاسبه کند.
سپس روش اجرا را انتخاب کند.
و تنها در پایان، تصمیم نهایی صادر شود.
بنابراین کل سیستم باید مانند یک موجود زنده عمل کند.
---
2.2 معماری کلی
سیستم به صورت چند لایه طراحی می‌شود.
External Data Sources
        │
        ▼
Data Acquisition Layer
        │
        ▼
Data Validation Layer
        │
        ▼
Data Synchronization Layer
        │
        ▼
Historical Data Storage
        │
        ▼
Feature Engineering Layer
        │
        ▼
Feature Store
        │
        ▼
Market Intelligence Layer
        │
        ▼
Context Layer
        │
        ▼
Prediction Layer
        │
        ▼
Optimization Layer
        │
        ▼
Execution Layer
        │
        ▼
Learning Layer
        │
        ▼
Monitoring Layer
نکته بسیار مهم:
هیچ ماژولی حق ندارد داده خام را مستقیماً از صرافی بخواند.
تمام داده‌ها فقط از طریق Data Layer وارد سیستم خواهند شد.
---
2.3 معماری مبتنی بر رویداد (Event Driven Architecture)
کل سیستم Event Driven خواهد بود.
نه Sequential.
یعنی:
New Candle
↓
Generate Event
↓
Publish Event
↓
Modules Subscribe
↓
Modules Execute
↓
Publish Results
↓
Aggregator
↓
Next Event
بنابراین هر ماژول مستقل است.
مثلاً:
Market State Engine
اصلاً نمی‌داند
SMT Engine
وجود دارد یا خیر.
---
2.4 انواع Event ها
حداقل Eventهای زیر باید وجود داشته باشند.
Data Events
New Candle
New Tick
New Trade
New Funding
New Open Interest
New Liquidation
New OrderBook
New Depth
Connection Restored
Connection Lost
---
System Events
Startup
Shutdown
Reload
Configuration Changed
Optimizer Finished
Database Saved
Heartbeat
---
Signal Events
Signal Generated
Signal Cancelled
Signal Updated
Signal Confirmed
Signal Rejected
---
Trade Events
Order Sent
Order Filled
Order Partially Filled
Stop Hit
Target Hit
Cancelled
Expired
---
Learning Events
Trade Closed
Performance Updated
Model Updated
Calibration Updated
Optimizer Updated
---
2.5 چرخه عمر یک تصمیم
از لحظه ورود داده تا خروج سیگنال.
Market
↓
Exchange
↓
Collector
↓
Validator
↓
Synchronizer
↓
Database
↓
Feature Generator
↓
Feature Store
↓
Market State
↓
Context
↓
SMC
↓
ICT
↓
RTM
↓
Orderflow
↓
Liquidity
↓
SMT
↓
Pattern
↓
Statistical
↓
AI
↓
Evidence Builder
↓
Consensus Engine
↓
Alpha Optimizer
↓
Risk Optimizer
↓
Execution Optimizer
↓
Decision
↓
Execution
↓
Evaluation
↓
Learning
↓
Database
تمام این مراحل باید مستقل باشند.
---
2.6 هیچ ماژولی State نهایی ندارد
تمام ماژول‌ها فقط
Evidence
تولید می‌کنند.
مثلاً:
SMT
نباید بگوید:
BUY
بلکه باید بگوید:
Bullish SMT
Confidence=0.71
Reliability=0.83
همین.
---
Liquidity Engine
نباید بگوید:
Sell
بلکه:
Liquidity Sweep
Quality
Probability
Age
---
Order Flow
نباید بگوید:
Long
بلکه:
Delta
Absorption
Stacked Imbalance
---
2.7 Consensus Engine
این موتور
قلب سیستم است.
تمام Evidenceها
اینجا جمع می‌شوند.
مثلاً
SMT
↓
0.82
Liquidity
↓
0.74
Trend
↓
0.91
FVG
↓
0.61
Order Block
↓
0.87
Volume
↓
0.77
Orderflow
↓
0.70
سپس
Consensus Engine
آنها را ترکیب می‌کند.
نه با Average.
بلکه با
Evidence Graph.
---
2.8 Evidence Graph
تمام خروجی‌ها
Node
خواهند بود.
Liquidity
↓
SMT
↓
FVG
↓
OB
↓
CHOCH
↓
Trend
↓
HTF
↓
Crypto Context
هر Node
دارای
Weight
Confidence
Reliability
Importance
Age
Decay
Conflict
Support
History
خواهد بود.
---
2.9 Dependency Graph
بین Nodeها
وابستگی وجود دارد.
مثلاً
CHOCH
↓
وابسته به
↓
Structure
یا
SMT
↓
وابسته به
↓
Correlation
یا
Liquidity Grab
↓
وابسته به
↓
Swing Detection
تمام این Dependencyها
باید ثبت شوند.
---
2.10 Confidence Propagation
اگر
Structure
اشتباه باشد.
باید
Confidence
تمام Nodeهای وابسته
کم شود.
مثلاً
Structure
↓
0.31
↓
CHOCH
↓
0.20
↓
SMT
↓
0.15
---
2.11 Reliability Propagation
هر ماژول
دارای
Historical Reliability
است.
مثلاً
SMT
92%
اما
در بازار Range
ممکن است
61%
شود.
پس Reliability
وابسته به رژیم بازار است.
---
2.12 Market Memory
تمام خروجی‌ها
باید ذخیره شوند.
نه فقط معاملات.
بلکه:
Liquidity
SMT
OB
FVG
CHOCH
Trend
Entropy
Funding
Open Interest
Execution
همه.
---
2.13 هیچ چیز حذف نمی‌شود
هیچ Data
پاک نمی‌شود.
بلکه
Archive
خواهد شد.
دلیل:
ممکن است
سه سال بعد
برای آموزش مدل
نیاز باشد.
---
2.14 Data Versioning
اگر
Feature
تغییر کند.
نسخه آن نیز
تغییر می‌کند.
مثلاً
Liquidity Score
v1
v2
v3
تا بدانیم
هر معامله
با کدام نسخه
انجام شده است.
---
2.15 Model Versioning
همین موضوع
برای مدل‌ها.
مثلاً
Risk Model
v7
Signal Model
v4
Consensus
v12
---
2.16 Parameter Versioning
حتی پارامترها.
مثلاً
ATR
v19
زیرا
Optimizer
ممکن است
آن را
تغییر دهد.
---
2.17 Configuration Snapshot
قبل از هر معامله
کل وضعیت سیستم
Snapshot
گرفته می‌شود.
شامل:
نسخه همه ماژول‌ها
نسخه مدل‌ها
نسخه پارامترها
وضعیت بازار
ویژگی‌های استخراج‌شده
امتیاز Evidenceها
خروجی Consensus
تنظیمات Risk
تنظیمات Execution
اگر بعدها نتیجه معامله غیرمنتظره بود، بتوان دقیقاً همان وضعیت را بازسازی (Reproduce) کرد.
---
2.18 Deterministic Replay
یکی از الزامات معماری این است که هر تصمیم گذشته باید قابل بازتولید باشد.
با داشتن Snapshot، داده‌های بازار و نسخه دقیق همه ماژول‌ها، سیستم باید بتواند همان تصمیم را دوباره اجرا کند و همان خروجی را تولید نماید. اگر خروجی متفاوت باشد، به معنی وجود رفتار غیرقطعی (Non-Deterministic) یا خطای نرم‌افزاری است و باید به‌عنوان یک نقص بحرانی ثبت شود.
---
2.19 اصول ارتباط بین ماژول‌ها
هیچ ماژولی اجازه ندارد مستقیماً متغیرهای داخلی ماژول دیگر را بخواند یا تغییر دهد.
ارتباط فقط از طریق Interfaceهای رسمی و پیام‌های استاندارد انجام می‌شود.
هر Interface باید به‌صورت صریح تعریف کند:
ساختار داده ورودی
ساختار داده خروجی
شرایط معتبر بودن داده
کدهای خطا
زمان‌بندی پاسخ
نسخه قرارداد (Contract Version)
این موضوع باعث می‌شود بتوان هر ماژول را بدون شکستن کل سیستم جایگزین یا ارتقا داد.
---
پایان بخش اول فصل دوم
در ادامه فصل دوم، معماری پردازش همزمان (Concurrency)، طراحی Pipelineهای Async، زمان‌بندی موتورهای مختلف، مدیریت منابع، ساختار Thread/Taskها، مدیریت صف‌ها (Queues)، نحوه همگام‌سازی داده‌ها و قراردادهای داخلی بین موتورهای سیستم با جزئیات کامل طراحی خواهد شد. این بخش پایه اصلی پیاده‌سازی سیستم در Python خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 2 (ادامه)
معماری کلان سیستم
---
2.20 معماری پردازش همزمان (Concurrency Architecture)
یکی از بزرگ‌ترین تفاوت‌های این پروژه با اکثر ربات‌های معامله‌گر، معماری اجرای آن است.
تقریباً تمام پروژه‌های موجود به صورت زیر کار می‌کنند:
دریافت کندل
↓
اجرای کل سیستم
↓
دریافت کندل بعدی
این معماری برای سیستم‌های بزرگ مناسب نیست.
در APEX تمام ماژول‌ها باید به صورت مستقل اجرا شوند.
اما نه به صورتی که باعث Race Condition شوند.
---
2.21 اصل Single Source of Truth
یکی از مهم‌ترین قوانین پروژه:
هیچ داده‌ای نباید در دو مکان مختلف حقیقت تلقی شود.
مثلاً
OrderBook
نباید در پنج کلاس مختلف نگهداری شود.
بلکه فقط
Market Cache
مالک آن است.
تمام موتورها فقط Read Only هستند.
---
2.22 Data Ownership
برای هر نوع داده فقط یک Owner وجود دارد.
مثلاً
OHLC
↓
Market Cache
-----------------
Funding
↓
Funding Manager
-----------------
Open Interest
↓
OI Manager
-----------------
Configuration
↓
Config Manager
-----------------
Database
↓
Database Manager
هیچ ماژولی اجازه تغییر مستقیم داده ماژول دیگر را ندارد.
---
2.23 Thread Safety
تمام کلاس‌هایی که داده مشترک دارند باید Thread Safe باشند.
به عنوان مثال:
Market Cache
Database Queue
Feature Store
Learning Buffer
Execution Queue
Optimizer Queue
همگی باید Lock-Free یا Read/Write Lock داشته باشند.
---
2.24 Async Pipeline
اجرای کل سیستم باید مبتنی بر Async باشد.
هر Engine
یک Coroutine مستقل خواهد بود.
مثلاً
Collector
Validator
Feature Builder
Liquidity Engine
Structure Engine
Risk Engine
Execution Engine
Learning Engine
همگی همزمان اجرا می‌شوند.
---
2.25 Scheduler
تمام موتورها زمان اجرای یکسان ندارند.
مثلاً
OrderBook
هر
100ms
آپدیت می‌شود.
اما
Optimizer
شاید
هر ۳۰ دقیقه.
بنابراین
Scheduler
باید وجود داشته باشد.
---
Scheduler باید بتواند:
Fixed Interval
Variable Interval
Cron
Event Driven
Priority
Dynamic Schedule
را مدیریت کند.
---
2.26 Priority System
تمام Taskها
اولویت دارند.
مثلاً
Order Fill
Priority=100
-----------------
Stop Loss
Priority=99
-----------------
New Tick
Priority=95
-----------------
Optimizer
Priority=25
-----------------
Database Backup
Priority=5
---
2.27 Queue Manager
هیچ Event
نباید مستقیم اجرا شود.
همه وارد Queue می‌شوند.
Incoming Queue
↓
Validation Queue
↓
Processing Queue
↓
Execution Queue
↓
Completed Queue
---
2.28 Dead Letter Queue
اگر Event
سه بار شکست بخورد
نباید حذف شود.
بلکه وارد
Dead Letter Queue
شود.
بعداً
توسط Error Manager
بررسی شود.
---
2.29 Watchdog
باید یک Watchdog وجود داشته باشد.
وظیفه آن:
بررسی زنده بودن تمام Engineها.
مثلاً
اگر
Liquidity Engine
پنج ثانیه پاسخ نداد.
باید:
Restart
یا
Disable
یا
Alert
انجام شود.
---
2.30 Health Monitor
هر Engine
باید دائماً گزارش دهد.
Alive
CPU
RAM
Latency
Queue Size
Errors
Warnings
Last Execution
Average Runtime
---
2.31 Performance Budget
برای هر Engine
حداکثر زمان مجاز اجرا تعریف می‌شود.
مثلاً
Liquidity
20ms
-----------------
Feature
40ms
-----------------
Risk
15ms
-----------------
Consensus
8ms
اگر بیشتر شود
Warning
ثبت می‌شود.
---
2.32 Backpressure
اگر
Data Rate
بیشتر از
Processing Rate
شود
نباید سیستم Crash کند.
بلکه
Backpressure
فعال شود.
مثلاً
Optimizer
موقتاً متوقف شود.
ولی
Execution
هرگز.
---
2.33 Memory Budget
هر Engine
بودجه حافظه دارد.
مثلاً
Feature Store
2GB
----------------
History Cache
5GB
----------------
OrderBook
500MB
اگر بیشتر شد
Garbage Collector اختصاصی
فعال شود.
---
2.34 Cache Hierarchy
سه سطح Cache
وجود خواهد داشت.
---
Level 1
RAM
---
Level 2
Memory Mapped File
---
Level 3
Database
---
2.35 Data Lifetime
تمام Data
عمر مشخص دارد.
مثلاً
Tick
5 دقیقه
----------------
OrderBook
30 دقیقه
----------------
Feature
24 ساعت
----------------
Trades
Permanent
---
2.36 Replay Buffer
تمام Eventها
ذخیره می‌شوند.
برای:
Debug
Replay
ML
Optimizer
Backtest
---
2.37 Time Synchronization
یکی از سخت‌ترین مشکلات.
تمام داده‌ها
باید Time Alignment شوند.
مثلاً
Funding
ممکن است
هر ۸ ساعت
باشد.
OrderBook
هر 100ms
باشد.
Tick
هر
5ms
باشد.
همه باید روی یک Time Axis
قرار گیرند.
---
2.38 Multi Exchange Clock
اگر
Binance
و
Bybit
همزمان استفاده شوند.
Clock آنها
ممکن است
چند صد میلی‌ثانیه
اختلاف داشته باشد.
باید
Clock Correction
پیاده شود.
---
2.39 Data Latency Tracking
هر Packet
دارای
Latency
خواهد بود.
Receive Time
Exchange Time
Processing Time
Execution Time
---
2.40 Latency Compensation
اگر
OrderBook
با
800ms
تاخیر رسید.
سیستم نباید
آن را
واقعیت فعلی
بداند.
بلکه
Confidence
آن کاهش پیدا کند.
---
2.41 Deterministic Processing
تمام Engineها
باید
Deterministic
باشند.
یعنی:
Input ثابت
↓
Output ثابت
وجود Random
بدون Seed
ممنوع است.
---
2.42 Randomness Policy
اگر
Genetic Algorithm
یا
Monte Carlo
استفاده شود.
تمام Seedها
ثبت شوند.
تا
Replay
ممکن باشد.
---
2.43 Floating Point Policy
تمام محاسبات حساس
باید
Tolerance
داشته باشند.
مثلاً
1e-9
زیرا
Floating Point
در سیستم‌های مختلف
کمی متفاوت است.
---
2.44 Numerical Stability
تمام الگوریتم‌ها باید در برابر:
Overflow
Underflow
Division by Zero
NaN
Infinity
Denormal Numbers
Catastrophic Cancellation
مقاوم باشند.
هر تابع عددی باید قبل از خروجی، اعتبار نتیجه را بررسی کند و در صورت مشاهده مقادیر نامعتبر، داده را اصلاح، مقدار جایگزین تعیین یا خطای کنترل‌شده تولید کند. هیچ مقدار NaN یا Inf نباید اجازه ورود به موتورهای تصمیم‌گیری، بهینه‌سازی یا یادگیری را داشته باشد؛ زیرا انتشار چنین مقادیری می‌تواند کل زنجیره تصمیم‌گیری را آلوده کند.
---
2.45 اصول Fail-Safe
اگر یک Engine از کار بیفتد، کل سیستم نباید متوقف شود.
معماری باید به گونه‌ای طراحی شود که:
ماژول معیوب ایزوله شود.
علت خرابی ثبت شود.
در صورت امکان، آخرین نسخه سالم ماژول مجدداً راه‌اندازی شود.
اگر بازیابی ممکن نبود، سیستم با قابلیت‌های کاهش‌یافته (Degraded Mode) به کار ادامه دهد.
فقط ماژول‌هایی که برای حفظ سرمایه حیاتی هستند (مانند Execution و Risk) اجازه توقف کل فرآیند را دارند.
این اصل، پایه طراحی یک سامانه معاملاتی قابل اعتماد است؛ زیرا در بازار واقعی، از دست رفتن یک فرصت معاملاتی بسیار کم‌هزینه‌تر از از دست دادن کنترل ریسک یا اجرای نادرست سفارش است.
---
پایان بخش دوم فصل دوم
در ادامه، وارد بخش سوم فصل دوم خواهیم شد که یکی از مهم‌ترین قسمت‌های کل کتاب است: طراحی ساختار پروژه (Project Blueprint)، استاندارد پوشه‌بندی، قراردادهای ماژول‌ها، قوانین نام‌گذاری، ساختار کلاس‌ها، Dependency Injection، Plugin Architecture و استانداردهای توسعه. این بخش پایه‌ای خواهد بود که تمام کدنویسی Python بر اساس آن انجام می‌شود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 2 (ادامه)
بخش سوم
Project Blueprint & Software Architecture
---
2.46 فلسفه طراحی نرم‌افزار
از این لحظه به بعد، دیگر درباره الگوریتم صحبت نمی‌کنیم.
بلکه درباره خود نرم‌افزار صحبت می‌کنیم.
تقریباً تمام پروژه‌های ترید متن‌باز دنیا به مرور زمان به این وضعیت دچار می‌شوند:
main.py
↓
4000 Lines
↓
8000 Lines
↓
15000 Lines
↓
Nobody understands anything.
این پروژه از ابتدا باید طوری طراحی شود که حتی اگر حجم آن به یک میلیون خط کد برسد، همچنان قابل نگهداری باشد.
بنابراین اولین اصل معماری نرم‌افزار:
> Scalability before Simplicity
یعنی از روز اول فرض می‌کنیم که پروژه ده‌ها هزار کلاس، صدها ماژول و میلیون‌ها خط کد خواهد داشت.
---
2.47 قوانین معماری
هیچ فایلی نباید مسئول بیش از یک موضوع باشد.
هیچ کلاس نباید بیش از یک مسئولیت داشته باشد.
هیچ تابعی نباید چند کار انجام دهد.
هیچ ماژولی نباید از جزئیات داخلی ماژول دیگر اطلاع داشته باشد.
هیچ Engine نباید مستقیم به Database متصل شود.
هیچ Engine نباید مستقیم API صرافی را فراخوانی کند.
هیچ Engine نباید Config را مستقیماً بخواند.
تمام ارتباطات باید از طریق Interface انجام شود.
---
2.48 معماری کلی پروژه
پروژه به چند Domain اصلی تقسیم می‌شود.
Core
Infrastructure
Domain
Application
Interface
Research
Optimization
Execution
Learning
Storage
Utilities
Monitoring
Configuration
Testing
Deployment
این تقسیم‌بندی نباید هرگز تغییر کند.
---
2.49 Core Domain
Core قلب سیستم است.
Core هیچ وابستگی خارجی ندارد.
حتی نباید بداند Binance چیست.
یا Bybit چیست.
یا Database چیست.
Core فقط منطق ریاضی و منطقی را می‌شناسد.
---
Core شامل:
Math
Statistics
Probability
Matrix
Graph
Optimization Base
Events
Messaging
Interfaces
Entity
Value Objects
Time
Geometry
Utilities
---
2.50 Infrastructure Layer
Infrastructure تمام ارتباط با دنیای بیرون را انجام می‌دهد.
مثلاً
Binance
Bybit
OKX
Database
Redis
SQLite
PostgreSQL
Websocket
REST
Filesystem
Cloud
Telegram
Discord
Logging
هیچ کدی از Core اجازه Import کردن Infrastructure را ندارد.
وابستگی فقط یک طرفه است.
---
2.51 Domain Layer
Domain
مهم‌ترین بخش پروژه است.
تمام منطق بازار اینجاست.
مثلاً
Liquidity
SMT
ICT
RTM
Wyckoff
Auction
Orderflow
Volume
Market Structure
Execution
Risk
Position
تمام اینها
Pure Domain
هستند.
---
2.52 Application Layer
Application
وظیفه هماهنگی بین Domainها را دارد.
مثلاً
Generate Signal
↓
Read Features
↓
Consensus
↓
Risk
↓
Execution
Application
هیچ محاسبه ریاضی انجام نمی‌دهد.
---
2.53 Interface Layer
تمام ورودی و خروجی سیستم.
CLI
REST API
Dashboard
Web UI
Terminal
Backtest UI
Optimizer UI
---
2.54 Configuration Layer
تمام تنظیمات
فقط اینجا قرار دارند.
هیچ عدد ثابت
داخل کد
وجود ندارد.
مثلاً
ATR Length
SMT Threshold
Risk %
Database
API Keys
Optimizer
Threads
Timeout
Precision
Exchange
---
2.55 Configuration Versioning
هر تغییر Config
دارای
Version
است.
مثلاً
Config
↓
v173
تمام معاملات
ثبت می‌کنند
با کدام Config
اجرا شده‌اند.
---
2.56 Dependency Injection
تمام کلاس‌ها
Dependency Injection
دارند.
نباید بنویسیم
engine = Binance()
بلکه
Container
آن را تزریق می‌کند.
این موضوع سه مزیت مهم دارد:
1. تست‌پذیری
2. جایگزینی آسان
3. حذف وابستگی سخت
---
2.57 Service Locator ممنوع
هیچ کلاس نباید هر زمان که خواست
برود
Service
پیدا کند.
همه چیز
در Constructor
تزریق می‌شود.
---
2.58 Factory Pattern
تمام Engineها
با Factory
ساخته می‌شوند.
مثلاً
SignalEngineFactory
RiskEngineFactory
OptimizerFactory
ExecutionFactory
---
2.59 Repository Pattern
Database
نباید مستقیم استفاده شود.
همیشه
Repository
بین آنها قرار می‌گیرد.
---
2.60 Unit of Work
اگر
سه جدول
همزمان
تغییر کنند.
همه
Transaction
خواهند بود.
یا
همه ذخیره می‌شوند.
یا
هیچ کدام.
---
2.61 Plugin Architecture
یکی از مهم‌ترین بخش‌های کل پروژه.
کل سیستم
Plugin Based
خواهد بود.
مثلاً
امروز
SMT v1
داریم.
فردا
SMT v2
می‌آید.
نباید
حتی
یک خط
از Engine
تغییر کند.
فقط Plugin
عوض می‌شود.
---
2.62 Plugin Contract
هر Plugin
باید Interface
مشخص داشته باشد.
مثلاً
Initialize
Load
Validate
Execute
Shutdown
Version
Capabilities
Health
اگر Plugin
این قرارداد را رعایت نکند
Load
نخواهد شد.
---
2.63 Plugin Registry
تمام Pluginها
ثبت می‌شوند.
مثلاً
Liquidity
↓
v1
v2
v3
و سیستم
انتخاب می‌کند
کدام فعال باشد.
---
2.64 Hot Swap
یکی از قابلیت‌های حرفه‌ای.
اگر
Plugin جدید
آماده شد.
نباید
کل سیستم
Restart
شود.
Plugin
در Runtime
جایگزین می‌شود.
البته فقط زمانی که تمام شرایط زیر برقرار باشد:
نسخه جدید با قرارداد (Interface Contract) سازگار باشد.
وضعیت (State) قابل انتقال باشد یا State مستقل باشد.
هیچ سفارش بازی در حال استفاده از نسخه قدیمی نباشد.
تست سلامت (Health Check) نسخه جدید موفق باشد.
در صورت بروز خطا، امکان Rollback فوری وجود داشته باشد.
---
2.65 Sandbox
هر Plugin
ابتدا
داخل Sandbox
اجرا می‌شود.
اگر
Crash
کرد.
کل سیستم
آسیب نمی‌بیند.
---
2.66 Capability Negotiation
هر Plugin
اعلام می‌کند
چه قابلیت‌هایی دارد.
مثلاً
Supports MultiTF
Supports GPU
Supports Online Learning
Supports Tick
Supports Replay
Supports Optimization
بر اساس این قابلیت‌ها، سیستم تصمیم می‌گیرد که Plugin در کدام سناریوها قابل استفاده است.
---
2.67 Version Compatibility Matrix
برای هر نسخه از هر Plugin باید ماتریس سازگاری نگهداری شود.
به عنوان مثال:
با کدام نسخه Core سازگار است.
با کدام نسخه Feature Store کار می‌کند.
به چه نسخه‌ای از قرارداد Interface نیاز دارد.
چه وابستگی‌هایی دارد.
آیا قابلیت ارتقای بدون توقف (Hot Upgrade) را دارد یا خیر.
این ماتریس از بروز ناسازگاری‌های پنهان جلوگیری می‌کند و پایه استقرار ایمن نسخه‌های جدید خواهد بود.
---
2.68 ممنوعیت Circular Dependency
در کل پروژه هیچ وابستگی حلقوی (Circular Dependency) مجاز نیست.
برای کنترل این موضوع باید:
وابستگی‌ها در زمان Build تحلیل شوند.
نمودار وابستگی (Dependency Graph) تولید شود.
هرگونه چرخه وابستگی به عنوان خطای بحرانی (Build Error) در نظر گرفته شود.
وابستگی‌ها فقط در یک جهت و مطابق معماری لایه‌ای حرکت کنند.
وجود Circular Dependency در پروژه‌ای با این ابعاد، به‌مرور زمان باعث غیرقابل نگهداری شدن کد، دشواری تست و شکست فرآیند توسعه خواهد شد؛ بنابراین این قانون یکی از قوانین غیرقابل‌مذاکره پروژه است.
---
پایان بخش سوم فصل دوم
در ادامه، فصل دوم با استانداردهای طراحی کلاس‌ها، قرارداد دقیق Interfaceها، ساختار Entityها، Value Objectها، Event Contractها، Data Transfer Objectها (DTO)، سیستم پیام‌رسان داخلی و استانداردهای توسعه و تست ادامه خواهد یافت؛ بخشی که مستقیماً مبنای نوشتن کد Python برای کل پروژه خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 2 (ادامه)
بخش چهارم
Domain Model, Contracts, Entities & Internal Communication Standard
---
2.69 مقدمه
از این قسمت به بعد، وارد مهم‌ترین بخش معماری نرم‌افزار می‌شویم.
در اکثر پروژه‌های معاملاتی، کلاس‌ها به مرور زمان بدون ساختار ایجاد می‌شوند و در نهایت پروژه به یک مجموعه از هزاران فایل وابسته تبدیل می‌شود که هیچ‌کس قادر به توسعه یا نگهداری آن نیست.
در APEX چنین چیزی مطلقاً قابل قبول نیست.
از روز اول، تمام موجودیت‌های سیستم (Entities)، اشیای مقداری (Value Objects)، قراردادها (Contracts)، DTOها، Eventها و پیام‌ها باید استاندارد باشند.
---
2.70 طبقه‌بندی انواع کلاس‌ها
کل پروژه فقط اجازه استفاده از دسته‌های زیر را دارد.
Entity
Value Object
Aggregate
Domain Service
Application Service
Infrastructure Service
Factory
Repository
DTO
Contract
Event
Command
Query
Response
Policy
Specification
Adapter
Strategy
Plugin
Manager
Coordinator
Scheduler
Controller
هیچ کلاس خارج از این دسته‌ها نباید ایجاد شود مگر با توجیه معماری.
---
2.71 Entity
Entity شیئی است که هویت دارد.
مثلاً
Trade
Position
Signal
Order
Portfolio
MarketSnapshot
OptimizationSession
ModelVersion
ExchangeConnection
Entityها دارای شناسه یکتا هستند و در طول عمر خود تغییر می‌کنند.
---
2.72 Value Object
برخلاف Entity،
Value Object هویت ندارد.
فقط مقدار دارد.
مثلاً
Price
Volume
Spread
Latency
Probability
Confidence
RiskScore
RewardScore
SharpeRatio
ATR
Timestamp
دو Value Object اگر مقدار برابر داشته باشند، برابر هستند.
---
2.73 Aggregate
چند Entity
تحت کنترل یک Aggregate قرار می‌گیرند.
مثلاً
Portfolio
↓
Position
↓
Orders
↓
Trades
فقط Portfolio اجازه تغییر Position را دارد.
هیچ کلاس دیگری مستقیماً Position را تغییر نمی‌دهد.
---
2.74 Aggregate Root
مثال
Portfolio
Aggregate Root است.
Position
نیست.
---
2.75 Domain Service
تمام منطق‌هایی که متعلق به یک Entity نیستند.
مثلاً
Risk Calculator
Liquidity Ranking
SMT Detection
Execution Cost Estimator
---
2.76 Application Service
هماهنگ‌کننده بین Domainها.
مثلاً
Generate Signal
↓
Read Features
↓
Consensus
↓
Risk
↓
Execution
---
2.77 Infrastructure Service
فقط ارتباط با خارج.
مثلاً
Binance API
SQLite
Redis
Telegram
Filesystem
---
2.78 DTO
DTO
فقط برای انتقال داده است.
هیچ منطق نباید داخل آن باشد.
مثلاً
SignalDTO
MarketDTO
OrderDTO
FeatureDTO
TradeDTO
---
2.79 Event
تمام تغییرات سیستم
Event هستند.
مثلاً
New Candle
New Tick
Signal Created
Trade Closed
Risk Updated
Optimizer Finished
---
2.80 Command
Command
درخواست انجام یک عمل است.
مثلاً
GenerateSignal
CancelOrder
ClosePosition
OptimizeSignal
OptimizeRisk
---
2.81 Query
فقط خواندن.
مثلاً
Get Last Trade
Get Current Position
Get Liquidity
Get Context
---
2.82 Response
هر Command
یا Query
باید Response
داشته باشد.
هیچ تابعی
نباید
void
برگرداند.
Response باید شامل:
Success
Failure
Warnings
Errors
ExecutionTime
Metadata
Version
CorrelationId
باشد.
---
2.83 Correlation ID
یکی از مهم‌ترین قوانین.
از لحظه ورود یک Tick
تا بسته شدن معامله
همه چیز
یک Correlation ID
مشترک دارد.
مثلاً
Tick
↓
Features
↓
Signal
↓
Risk
↓
Execution
↓
Trade
↓
Learning
همه
یک شناسه دارند.
این موضوع Debug و Replay را ممکن می‌کند.
---
2.84 Trace ID
اگر
چند Correlation
به هم مرتبط باشند.
Trace ID
آنها را
گروه‌بندی می‌کند.
---
2.85 Metadata
تمام پیام‌ها
Metadata
دارند.
حداقل:
Time
Exchange
Symbol
Version
Latency
Priority
Source
Destination
---
2.86 Event Contract
هیچ Event
نباید
فرمت متفاوت داشته باشد.
همه باید شامل:
Header
Metadata
Payload
Checksum
Signature
Version
باشند.
---
2.87 Payload Policy
Payload
فقط داده دارد.
نه منطق.
نه تابع.
نه Reference.
فقط داده.
---
2.88 Immutable Messages
تمام Eventها
بعد از ساخته شدن
Immutable
هستند.
هیچ کس
اجازه تغییر
ندارد.
اگر چیزی تغییر کند
Event جدید
تولید می‌شود.
---
2.89 Time Policy
تمام Timestampها
فقط
UTC
هستند.
Timezone
داخل سیستم
ممنوع است.
تبدیل زمان فقط در Interface Layer انجام می‌شود.
---
2.90 Precision Policy
تمام مقادیر مالی باید دارای سیاست دقت مشخص باشند.
برای مثال:
قیمت (Price)
حجم (Volume)
سود و زیان (PnL)
کارمزد (Fee)
نسبت‌ها (Ratios)
نباید به صورت دلخواه گرد شوند. هر نوع داده باید بر اساس قوانین همان صرافی و همان دارایی، دقت (Precision) و گام تغییر (Tick Size / Lot Size) مخصوص خود را داشته باشد.
---
2.91 Validation Pipeline
قبل از ورود هر داده به سیستم، باید از یک Pipeline اعتبارسنجی عبور کند.
این Pipeline حداقل شامل مراحل زیر است:
Schema Validation
↓
Type Validation
↓
Range Validation
↓
Business Rule Validation
↓
Exchange Rule Validation
↓
Integrity Check
↓
Normalization
↓
Acceptance
اگر داده در هر مرحله رد شود، وارد موتورهای تصمیم‌گیری نخواهد شد.
---
2.92 Schema Versioning
اگر ساختار DTO یا Event تغییر کند، نسخه آن نیز باید تغییر کند.
سیستم باید بتواند همزمان چند نسخه از یک قرارداد را پشتیبانی کند تا ارتقای تدریجی (Rolling Upgrade) بدون توقف سیستم امکان‌پذیر باشد.
---
2.93 Message Bus
هیچ ماژولی نباید مستقیماً ماژول دیگری را فراخوانی کند.
تمام ارتباطات داخلی از طریق Message Bus انجام می‌شود.
Message Bus باید قابلیت‌های زیر را داشته باشد:
Publish
Subscribe
Priority Queue
Retry
Dead Letter Queue
Delivery Guarantee
Correlation Tracking
Backpressure Handling
---
2.94 Delivery Guarantees
برای هر نوع پیام باید نوع تضمین تحویل مشخص شود.
به عنوان نمونه:
At Most Once
At Least Once
Exactly Once (در بخش‌های بحرانی مانند ثبت معاملات)
انتخاب نوع تضمین باید بر اساس اهمیت عملیات و هزینه تکرار یا از دست رفتن پیام انجام شود.
---
2.95 اصل Idempotency
تمام Commandهای بحرانی باید Idempotent باشند.
یعنی اگر یک پیام به دلیل خطای شبکه دوباره ارسال شد، اجرای مجدد آن نباید باعث ثبت سفارش تکراری، بسته شدن دوباره موقعیت یا ایجاد تغییرات ناسازگار در سیستم شود.
این اصل برای تمام بخش‌های Execution، Database و Learning الزامی است.
---
پایان بخش چهارم فصل دوم
---
نکته مهم درباره ادامه کتاب
در این مرحله هنوز وارد قلب واقعی پروژه نشده‌ایم. تاکنون فقط زیرساخت مهندسی نرم‌افزار را طراحی کرده‌ایم.
از فصل سوم به بعد وارد طراحی موتورهای اصلی می‌شویم و حجم مطالب به‌مراتب بیشتر خواهد شد. فصل‌های آینده شامل طراحی کامل و در سطح پیاده‌سازی برای موارد زیر خواهند بود:
1. Data Acquisition Layer (جمع‌آوری داده از صرافی‌ها، WebSocket، REST، Order Book، Funding، Open Interest، Liquidations و...)
2. Data Validation & Synchronization Engine
3. Feature Engineering Engine (صدها تا هزاران Feature با تعریف، فرمول، وابستگی و چرخه عمر)
4. Feature Store
5. Market Intelligence Engine
6. Market State Engine
7. Liquidity Intelligence Engine
8. Order Flow Intelligence Engine
9. Smart Money / ICT / RTM Engine
10. SMT Engine
11. Statistical & Probabilistic Engine
12. Alpha Discovery Optimizer
13. Risk, Money Management & Execution Optimizer
14. Meta Optimizer
15. Learning & Feedback System
از اینجا به بعد، هر فصل به‌تنهایی از نظر حجم و جزئیات، چندین برابر فصل‌های مقدماتی خواهد بود و پایه مستقیم پیاده‌سازی کد Python را تشکیل می‌دهد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 3
Data Acquisition Layer
طراحی کامل لایه جمع‌آوری داده
---
3.1 فلسفه طراحی
تقریباً تمام ربات‌های معامله‌گر موجود، داده را به شکل زیر دریافت می‌کنند:
Exchange
↓
OHLCV
↓
Indicator
↓
Signal
این معماری از همان ابتدا شکست خورده است.
دلیل:
بازار فقط از OHLCV تشکیل نشده است.
در واقع OHLCV فقط خلاصه‌ای بسیار کوچک از آن چیزی است که در بازار اتفاق افتاده است.
این خلاصه حتی شاید کمتر از یک درصد اطلاعات واقعی بازار باشد.
بنابراین اولین هدف این پروژه حذف وابستگی به Candle است.
در APEX،
کندل تنها یکی از صدها منبع داده خواهد بود.
---
3.2 هدف Data Layer
Data Layer فقط مسئول جمع‌آوری داده نیست.
بلکه باید:
دریافت کند.
اعتبارسنجی کند.
همگام‌سازی کند.
نرمال‌سازی کند.
نسخه‌بندی کند.
کیفیت را ارزیابی کند.
تأخیر را اندازه‌گیری کند.
داده خراب را حذف کند.
داده مفقود را تشخیص دهد.
داده تکراری را حذف کند.
داده را Cache کند.
داده را آرشیو کند.
داده را در اختیار Feature Layer قرار دهد.
Data Layer هیچ تحلیل بازار انجام نمی‌دهد.
---
3.3 طراحی Data Lake
تمام داده‌های خام ابتدا وارد Data Lake می‌شوند.
هیچ داده‌ای مستقیماً وارد سیستم تصمیم‌گیری نمی‌شود.
Exchange
↓
Raw Data Collector
↓
Raw Queue
↓
Raw Data Lake
↓
Validation
↓
Synchronization
↓
Normalization
↓
Feature Layer
Raw Data باید همیشه نگهداری شود.
حتی اگر خراب باشد.
دلیل:
ممکن است بعداً الگوریتم جدیدی برای اصلاح آن نوشته شود.
---
3.4 طبقه‌بندی داده‌ها
تمام داده‌ها در پروژه به هفت دسته تقسیم می‌شوند.
---
Market Data
Tick
Trade
OHLC
OHLCV
VWAP
Spread
Mid Price
Mark Price
Index Price
Last Price
Best Bid
Best Ask
---
OrderBook Data
Depth
Bid Levels
Ask Levels
Liquidity
Order Count
Market Depth
Book Pressure
Book Imbalance
Book Velocity
Book Acceleration
---
Derivatives Data
Funding
Open Interest
Long Ratio
Short Ratio
Liquidations
Gamma
Delta
Basis
Premium
Borrow Rate
OI Change
Funding Change
---
OnChain Data
Exchange Inflow
Exchange Outflow
Whale Wallet
Stablecoin Mint
Miner Flow
Hash Rate
Difficulty
Network Fees
Mempool
Dormancy
Realized Cap
NVT
MVRV
SOPR
---
Macro Data
DXY
NASDAQ
SP500
Gold
Silver
Oil
Bond Yield
ETF Flow
Interest Rate
Economic Calendar
---
Sentiment Data
News
Twitter
Reddit
Telegram
Google Trend
Fear Index
Greed Index
Developer Activity
---
Internal Data
این داده‌ها توسط خود سیستم تولید می‌شوند.
Feature
Signal
Risk
Optimizer
Execution
Learning
Performance
Replay
Calibration
---
3.5 Exchange Abstraction Layer
یکی از مهم‌ترین بخش‌های معماری.
هیچ قسمت سیستم نباید بداند
Binance چیست.
یا
Bybit چیست.
تمام صرافی‌ها باید پشت یک Interface واحد قرار گیرند.
مثلاً
Exchange
↓
Exchange Adapter
↓
Unified Market Interface
↓
System
بنابراین اگر فردا
OKX
اضافه شود.
هیچ Engine
تغییر نمی‌کند.
---
3.6 Exchange Capability Matrix
هر صرافی قابلیت‌های متفاوتی دارد.
مثلاً
Supports Tick
Supports Depth
Supports Liquidation
Supports Funding
Supports OI
Supports Option
Supports Websocket
Supports Replay
قبل از فعال شدن هر Adapter، این قابلیت‌ها باید شناسایی شوند تا Feature Layer بداند کدام ویژگی‌ها واقعاً قابل محاسبه هستند.
---
3.7 WebSocket Collector
در معاملات زنده، منبع اصلی داده WebSocket است.
این Collector باید ویژگی‌های زیر را داشته باشد:
اتصال همزمان به چندین Stream
تشخیص قطع ارتباط
Reconnect خودکار با Backoff نمایی
Ping/Pong سلامت اتصال
اندازه‌گیری Latency
بافر موقت هنگام قطعی کوتاه
تشخیص پیام‌های تکراری
تشخیص Gap در Sequence Number
ثبت تمام پیام‌های خام برای Replay
---
3.8 REST Collector
REST فقط برای داده‌هایی استفاده می‌شود که Streaming ندارند یا جهت همگام‌سازی اولیه لازم هستند.
نمونه‌ها:
Snapshot اولیه Order Book
Funding History
Open Interest History
Historical Candles
Exchange Metadata
Symbol Information
REST نباید در حلقه اصلی معاملات برای داده‌های پرسرعت استفاده شود مگر در شرایط اضطراری.
---
3.9 Multi-Exchange Collector
سیستم باید بتواند به‌طور همزمان به چندین صرافی متصل باشد.
اما نکته مهم این است که:
هیچ داده‌ای مستقیماً با داده صرافی دیگر مخلوط نمی‌شود.
ابتدا هر صرافی Data Stream مستقل دارد.
سپس یک لایه Cross-Exchange Synchronizer آن‌ها را همگام می‌کند.
---
3.10 Symbol Resolver
یکی از رایج‌ترین خطاها در پروژه‌های کریپتو تفاوت نام نمادها است.
مثلاً:
BTCUSDT
XBTUSDT
BTC-USD
BTC/USDT
همه این‌ها باید به یک شناسه داخلی استاندارد نگاشت شوند.
هیچ Engine نباید با نام خام صرافی کار کند.
---
3.11 Time Resolution Policy
همه زمان‌ها به UTC ذخیره می‌شوند.
اما علاوه بر Timestamp خام، هر رکورد باید شامل موارد زیر باشد:
Exchange Timestamp
Receive Timestamp
Processing Timestamp
Storage Timestamp
Latency Estimate
این اطلاعات بعداً در ارزیابی کیفیت داده و تحلیل عملکرد سیستم استفاده خواهند شد.
---
3.12 Sequence Integrity
تمام Streamهایی که شماره توالی (Sequence Number) دارند باید کنترل شوند.
اگر شماره‌ای جا افتاده باشد:
1. Gap ثبت شود.
2. Data Quality کاهش یابد.
3. در صورت امکان داده از REST بازیابی شود.
4. در غیر این صورت Featureهایی که به آن داده وابسته‌اند با Confidence پایین‌تر محاسبه شوند.
---
3.13 Data Quality Score
هر بسته داده باید یک امتیاز کیفیت داشته باشد.
امتیاز کیفیت بر اساس عواملی مانند:
تأخیر
کامل بودن
عدم وجود Gap
اعتبار Schema
اعتبار Checksum
همخوانی زمانی
سازگاری با Snapshot
محاسبه می‌شود.
هیچ Feature نباید بدون اطلاع از کیفیت داده تولید شود.
---
3.14 Data Provenance
هر داده باید منشأ خود را حفظ کند.
برای هر رکورد باید مشخص باشد:
از کدام صرافی آمده است.
از WebSocket آمده یا REST.
از داده خام است یا بازسازی‌شده.
در چه زمانی دریافت شده است.
توسط کدام نسخه Collector پردازش شده است.
این اطلاعات برای Debug، Audit و Replay ضروری هستند.
---
3.15 Fault Tolerance در Data Layer
اگر یک Collector از کار بیفتد:
سایر Collectorها نباید متوقف شوند.
صف‌های داده نباید از بین بروند.
وضعیت اتصال باید ثبت شود.
بازیابی خودکار انجام شود.
در صورت شکست بازیابی، سیستم به حالت Degraded Mode برود.
موتورهای بالادستی از کاهش کیفیت داده مطلع شوند.
---
3.16 طراحی برای توسعه آینده
Data Layer باید از ابتدا به گونه‌ای طراحی شود که افزودن منابع داده جدید (مانند Options، CME Futures، داده‌های L2/L3، داده‌های DeFi یا داده‌های اختصاصی) تنها با افزودن Adapter جدید امکان‌پذیر باشد و هیچ تغییری در Market Intelligence، Feature Engineering یا Optimizerها ایجاد نکند.
---
پایان بخش اول فصل سوم
در ادامه فصل سوم، Data Validation Engine، Data Synchronization Engine، Data Normalization Engine، Data Quality Engine، Replay Buffer، Historical Storage، Memory Cache و Feature Feed Pipeline با جزئیات کامل طراحی خواهند شد. این بخش‌ها ستون فقرات کل سامانه هستند و کیفیت تمام تصمیم‌های بعدی مستقیماً به صحت طراحی آن‌ها وابسته است.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 3 (ادامه)
بخش دوم
Data Validation Engine
---
3.17 مقدمه
اگر بخواهم فقط یک بخش را به عنوان مهم‌ترین قسمت کل سیستم انتخاب کنم، آن Data Validation Engine خواهد بود.
تقریباً تمام پروژه‌های ترید دنیا فرض می‌کنند داده‌ای که از صرافی دریافت شده صحیح است.
این فرض کاملاً اشتباه است.
بازار کریپتو دائماً دچار موارد زیر می‌شود:
Packet Loss
WebSocket Lag
REST Delay
Out-of-order Messages
Duplicate Messages
Exchange Bugs
API Bugs
Clock Drift
Missing Trades
Wrong Liquidations
Wrong Funding
Flash Crash Glitches
Temporary Bad Ticks
OrderBook Corruption
بنابراین Data Validation صرفاً بررسی نوع داده نیست.
بلکه یک سیستم کامل ارزیابی کیفیت داده است.
---
3.18 اصل بنیادی
هیچ داده‌ای تا زمانی که از تمام مراحل اعتبارسنجی عبور نکند، اجازه ورود به Feature Engineering را ندارد.
قاعده اصلی پروژه:
Raw Data
↓
Validate
↓
Normalize
↓
Synchronize
↓
Score
↓
Accept
↓
Feature Engineering
---
3.19 Validation Pipeline
Pipeline اعتبارسنجی باید دقیقاً به ترتیب زیر اجرا شود.
Packet Validation
↓
Protocol Validation
↓
Schema Validation
↓
Type Validation
↓
Null Validation
↓
Range Validation
↓
Logical Validation
↓
Cross Validation
↓
Temporal Validation
↓
Market Validation
↓
Exchange Validation
↓
Statistical Validation
↓
Quality Scoring
↓
Acceptance
هیچ مرحله‌ای نباید حذف شود.
---
3.20 Packet Validation
اولین مرحله.
بررسی می‌کند:
Packet ناقص نباشد.
اندازه Packet صحیح باشد.
Encoding صحیح باشد.
Compression درست باشد.
JSON خراب نباشد.
Checksum معتبر باشد.
اگر این مرحله رد شود:
Packet مستقیماً وارد Dead Packet Queue می‌شود.
---
3.21 Protocol Validation
بررسی می‌شود:
پیام واقعاً مطابق مستندات همان Exchange باشد.
مثلاً
اگر Binance گفته است:
price
string
ولی
عدد
ارسال شده باشد.
پیام رد می‌شود.
---
3.22 Schema Validation
تمام فیلدها باید وجود داشته باشند.
مثلاً
Trade
باید شامل:
Price
Quantity
Time
Side
TradeId
Symbol
باشد.
کم بودن یا زیاد بودن فیلدها
هر دو
خطا هستند.
---
3.23 Type Validation
نوع داده بررسی می‌شود.
مثلاً
Price
↓
Float
Volume
↓
Float
TradeId
↓
Integer
Time
↓
Datetime
---
3.24 Null Validation
نباید
Null
وجود داشته باشد.
مگر اینکه
Schema
اجازه داده باشد.
---
3.25 Range Validation
تمام مقادیر
دارای بازه معتبر هستند.
مثلاً
Funding
نباید
300%
باشد.
Spread
نباید
منفی
باشد.
Volume
نباید
منفی
باشد.
---
3.26 Precision Validation
تمام داده‌ها باید مطابق Precision همان Symbol باشند.
مثلاً
اگر
BTCUSDT
دارای
0.01
Tick باشد.
قیمت
106543.1234567
نباید قبول شود.
---
3.27 Symbol Validation
بررسی می‌شود:
نماد
واقعاً
وجود داشته باشد.
فعال باشد.
Delist نشده باشد.
---
3.28 Exchange State Validation
اگر
Exchange
در Maintenance
باشد.
سیستم باید آن را تشخیص دهد.
---
3.29 Timestamp Validation
زمان
نباید
در آینده باشد.
نباید
بیش از حد
قدیمی باشد.
---
3.30 Clock Drift Validation
اگر
Exchange Time
با
Local Time
اختلاف زیادی داشت.
ثبت می‌شود.
---
3.31 Duplicate Detection
پیام‌های تکراری
نباید
دوباره پردازش شوند.
برای این کار:
Message Hash
نگهداری می‌شود.
---
3.32 Sequence Validation
اگر
پیام شماره
102
وجود داشته باشد.
بعد
104
بیاید.
سیستم باید تشخیص دهد
103
گم شده است.
---
3.33 Gap Recovery
در صورت وجود Gap
ابتدا
REST
فراخوانی می‌شود.
اگر
داده
پیدا نشد.
Confidence
کاهش پیدا می‌کند.
---
3.34 Out-of-Order Validation
گاهی
پیام‌ها
با ترتیب اشتباه
می‌رسند.
مثلاً
101
103
102
سیستم باید
آنها را
مرتب کند.
---
3.35 Market Rule Validation
مثلاً
قیمت
نباید
منفی باشد.
Spread
نباید
غیرممکن باشد.
High
نباید
از Low
کمتر باشد.
---
3.36 Cross Validation
مثلاً
Trade
باید
داخل
OrderBook
قابل توضیح باشد.
یا
Funding
باید
با
Premium
سازگار باشد.
---
3.37 Candle Validation
کندل‌ها
نباید
تناقض داشته باشند.
مثلاً
High
کمتر از
Open
یا
Low
بیشتر از
Close
---
3.38 Trade Validation
اگر
Trade
بیش از
X برابر
میانگین
بزرگ باشد.
علامت‌گذاری می‌شود.
نه حذف.
---
3.39 Flash Event Detection
گاهی
Exchange
اعداد اشتباه
ارسال می‌کند.
مثلاً
BTC
از
100000
به
1000
برود.
باید تشخیص داده شود.
---
3.40 Market Halt Detection
اگر
چند ثانیه
هیچ Trade
وجود نداشت.
سیستم بررسی می‌کند:
آیا بازار
متوقف شده؟
یا
ارتباط
قطع شده؟
---
3.41 Statistical Validation
هر داده
با گذشته
مقایسه می‌شود.
مثلاً
Z Score
MAD
IQR
Mahalanobis Distance
Robust Statistics
اگر داده به‌شدت دورافتاده (Outlier) باشد، به‌جای حذف مستقیم، با برچسب «مشکوک» وارد مرحله بعدی می‌شود تا موتورهای بالادستی بتوانند بر اساس کیفیت داده تصمیم بگیرند.
---
3.42 Data Repair Policy
اصل مهم:
تا جای ممکن داده تعمیر شود، نه حذف.
نمونه‌ها:
تکمیل Gap با Snapshot معتبر
بازسازی Order Book از Snapshot + Incremental Updates
حذف Duplicateها
مرتب‌سازی پیام‌های Out-of-Order
جایگزینی Timestamp اصلاح‌شده
اصلاح Precision بر اساس قوانین Exchange
هر عملیات Repair باید در Metadata ثبت شود تا منشأ داده از بین نرود.
---
3.43 Confidence Assignment
پس از پایان اعتبارسنجی، هر رکورد علاوه بر مقدار اصلی، یک Confidence Score دریافت می‌کند.
این امتیاز از ترکیب عوامل زیر به دست می‌آید:
کیفیت اتصال
تأخیر
تعداد عملیات Repair
وجود یا عدم وجود Gap
اعتبار آماری
اعتبار زمانی
سازگاری با سایر منابع
به این ترتیب، Feature Engineering و موتورهای تصمیم‌گیری فقط مقدار داده را نمی‌بینند؛ بلکه میزان اعتماد به آن را نیز در محاسبات خود لحاظ می‌کنند.
---
3.44 Audit Trail
تمام مراحل اعتبارسنجی باید قابل ردیابی باشند.
برای هر رکورد باید مشخص باشد:
چه آزمون‌هایی روی آن اجرا شده‌اند.
کدام آزمون‌ها موفق بوده‌اند.
چه اصلاحاتی انجام شده است.
Confidence نهایی چگونه محاسبه شده است.
کدام نسخه از موتور Validation این عملیات را انجام داده است.
این Audit Trail یکی از الزامات اصلی برای Debug، بازتولید نتایج، تحلیل خطا و توسعه آینده سیستم خواهد بود.
---
پایان بخش دوم فصل سوم
در ادامه، وارد Data Synchronization Engine خواهیم شد؛ بخشی که وظیفه همگام‌سازی داده‌های چندصرافی، چندمنبعی و چندفرکانسی را بر عهده دارد و پایه صحیح بودن تمام Featureهای زمانی و بین‌بازاری (Intermarket) است. این بخش یکی از پیچیده‌ترین قسمت‌های کل معماری خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 3 (ادامه)
بخش سوم
Data Synchronization Engine
---
3.45 مقدمه
Data Validation تضمین می‌کند که هر داده به تنهایی معتبر است.
اما این کافی نیست.
حتی اگر تمام داده‌ها کاملاً صحیح باشند، ممکن است در کنار یکدیگر کاملاً اشتباه باشند.
علت:
تمام داده‌ها با یک سرعت تولید نمی‌شوند.
مثلاً
Trade
هر چند میلی‌ثانیه
--------------------
OrderBook
هر 100ms
--------------------
Funding
هر 8 ساعت
--------------------
Open Interest
هر چند ثانیه
--------------------
Economic Data
هر چند هفته
--------------------
OnChain
هر چند دقیقه
اگر این داده‌ها بدون همگام‌سازی وارد سیستم شوند،
تقریباً تمام Featureهای پیشرفته اشتباه خواهند شد.
بنابراین Data Synchronization یکی از مهم‌ترین موتورهای کل پروژه است.
---
3.46 هدف Synchronization Engine
وظیفه این موتور فقط هم‌زمان کردن Timestampها نیست.
بلکه باید:
همگام‌سازی زمانی
همگام‌سازی بین صرافی‌ها
همگام‌سازی بین بازار Spot و Futures
همگام‌سازی بین مشتقات
همگام‌سازی بین داده‌های OnChain
همگام‌سازی بین داده‌های اقتصاد کلان
همگام‌سازی بین داده‌های احساسات بازار
همگام‌سازی Featureها
همگام‌سازی Replay
را انجام دهد.
---
3.47 اصل جهانی زمان
کل سیستم فقط یک ساعت دارد.
آن ساعت:
UTC
است.
هیچ Engine
نباید
از Local Time
استفاده کند.
---
3.48 Internal Timeline
تمام Eventها
بعد از ورود
روی یک Timeline
قرار می‌گیرند.
Exchange Time
↓
Normalized Time
↓
Internal Timeline
↓
Processing
---
3.49 Event Ordering
ترتیب Eventها
نباید
بر اساس
زمان دریافت
باشد.
بلکه
بر اساس
Exchange Timestamp
است.
---
3.50 Watermark System
گاهی
Packet
دیر می‌رسد.
بنابراین
باید Watermark
وجود داشته باشد.
مثلاً
اگر
Watermark
200ms
باشد.
سیستم
قبل از پردازش
200ms
منتظر Eventهای عقب‌مانده می‌ماند.
---
3.51 Late Event Policy
اگر
Packet
بعد از Watermark
برسد.
سه حالت وجود دارد.
---
حالت اول
داده
دیگر
مهم نیست.
Discard
---
حالت دوم
Replay
اصلاح می‌شود.
---
حالت سوم
تمام Featureها
دوباره
محاسبه می‌شوند.
---
تصمیم‌گیری بر اساس سیاست هر ماژول انجام می‌شود.
---
3.52 Multi Frequency Alignment
تمام داده‌ها
باید
روی Grid
قرار گیرند.
مثلاً
Tick
5ms
↓
Grid
↓
50ms
↓
Feature
↓
250ms
↓
Decision
---
3.53 Time Bucket
داده‌ها
داخل Bucket
قرار می‌گیرند.
مثلاً
0-100ms
100-200ms
200-300ms
هر Bucket
دارای
Version
خواهد بود.
---
3.54 Adaptive Bucket
اگر
بازار
بسیار سریع
شود.
Bucket
کوچک‌تر
می‌شود.
اگر
بازار
آرام
شود.
Bucket
بزرگ‌تر
می‌شود.
این اندازه نباید ثابت باشد.
---
3.55 Symbol Synchronization
اگر
BTC
و
ETH
برای SMT
استفاده شوند.
باید
کاملاً
همزمان
باشند.
نه اینکه
BTC
100ms
جلوتر باشد.
---
3.56 Multi Exchange Synchronization
فرض کنیم
BTC
از
Binance
و
Bybit
می‌آید.
ممکن است
اختلاف ساعت
داشته باشند.
Synchronization Engine
باید
Clock Offset
هر Exchange
را
یاد بگیرد.
---
3.57 Drift Learning
اختلاف ساعت
ثابت نیست.
سیستم باید
آن را
دائماً
یاد بگیرد.
مثلاً
Binance
+13ms
↓
+15ms
↓
+11ms
---
3.58 Adaptive Drift Model
برای هر Exchange یک مدل Drift مستقل نگهداری می‌شود.
این مدل باید بتواند:
میانگین Drift
واریانس Drift
روند تغییر Drift
جهش‌های ناگهانی
Confidence تخمین Drift
را محاسبه کند.
در صورت تغییر ناگهانی، داده‌های آن Exchange تا زمان پایدار شدن با Confidence پایین‌تر وارد سیستم می‌شوند.
---
3.59 Cross Exchange Validation
اگر
قیمت
BTC
در
Binance
و
Bybit
اختلاف
غیرعادی
داشته باشد.
باید
علامت‌گذاری شود.
---
3.60 Market Session Alignment
گرچه کریپتو ۲۴ ساعته است،
اما رفتار بازار در Sessionهای مختلف متفاوت است.
Synchronization Engine باید Session را نیز به داده اضافه کند.
نمونه:
Asia
Europe
US
Overlap Asia-Europe
Overlap Europe-US
Low Liquidity Hours
این اطلاعات برای Feature Engineering بسیار مهم هستند.
---
3.61 Economic Event Alignment
اگر
داده CPI
منتشر شد.
تمام داده‌های بازار
باید
علامت‌گذاری شوند.
مثلاً
Before CPI
↓
Release
↓
After CPI
---
3.62 Funding Alignment
Funding
هر
8 ساعت
تغییر می‌کند.
اما
اثر آن
تدریجی است.
بنابراین
Feature
نباید
Step Function
باشد.
بلکه
Decay
داشته باشد.
---
3.63 Open Interest Alignment
OI
دیرتر از Trade
منتشر می‌شود.
بنابراین
باید
Lag Compensation
پیاده شود.
---
3.64 OrderBook Alignment
OrderBook
و
Trades
باید
از یک Snapshot
شروع شوند.
در غیر این صورت
Book Reconstruction
اشتباه می‌شود.
---
3.65 Snapshot Consistency
هر Snapshot
باید
Version
داشته باشد.
Incremental Update
فقط
روی همان Version
اعمال می‌شود.
---
3.66 Replay Synchronization
Replay
باید
دقیقاً
همان ترتیب
Eventها
را
اجرا کند.
نه
ترتیب ذخیره شدن.
---
3.67 Causal Ordering
یکی از مهم‌ترین اصول.
اگر
Trade
باعث
تغییر
OrderBook
شده است.
Replay
نیز
باید
همین ترتیب
را
حفظ کند.
---
3.68 Feature Synchronization
هیچ Feature
قبل از آماده شدن
تمام Inputها
محاسبه نمی‌شود.
مثلاً
SMT
نباید
بدون
ETH
محاسبه شود.
---
3.69 Dependency Barrier
هر Feature
Barrier
دارد.
مثلاً
SMT
↓
BTC
↓
ETH
↓
Correlation
↓
Time Alignment
تا زمانی که همه وابستگی‌ها آماده نباشند، Feature وارد مرحله محاسبه نمی‌شود.
---
3.70 Confidence Decay
اگر
Data
قدیمی
شود.
Confidence
به مرور
کم می‌شود.
نه اینکه
ناگهان
صفر شود.
از توابعی مانند:
Exponential Decay
Hyperbolic Decay
Adaptive Decay
بسته به نوع داده استفاده می‌شود.
---
3.71 Synchronization Metadata
هر داده پس از همگام‌سازی باید اطلاعات زیر را همراه داشته باشد:
Original Timestamp
Corrected Timestamp
Clock Offset
Drift Estimate
Synchronization Quality
Delay Class
Replay Position
Source Priority
---
3.72 Synchronization Quality Score
در پایان فرآیند، هر رکورد یک امتیاز کیفیت همگام‌سازی دریافت می‌کند.
این امتیاز از عوامل زیر تشکیل می‌شود:
دقت Alignment
میزان Drift اصلاح‌شده
تعداد عملیات Repair
اختلاف زمانی با سایر منابع
کیفیت Source
وضعیت Watermark
وضعیت Dependencyها
Feature Engineering این امتیاز را مستقیماً در وزن‌دهی Featureها استفاده خواهد کرد.
---
3.73 Synchronization Failure Policy
اگر همگام‌سازی برای یک داده امکان‌پذیر نباشد، سیستم هرگز نباید تصمیم غیرشفاف بگیرد.
به جای آن یکی از سیاست‌های زیر اعمال می‌شود:
Reject
Defer
Degraded Mode
Predict Missing Data
Skip Dependent Features
انتخاب سیاست به نوع داده، اهمیت آن و وضعیت فعلی بازار وابسته است.
---
3.74 Architecture Output Contract
خروجی Data Synchronization Engine فقط یک داده همگام‌شده نیست.
هر خروجی باید شامل سه بخش باشد:
1. داده نهایی (Normalized Data)
2. اطلاعات کیفیت (Quality & Confidence Metadata)
3. تاریخچه اصلاحات (Repair & Synchronization Audit Trail)
این قرارداد پایه‌ای است که تمام موتورهای Feature Engineering، Market Intelligence و Optimizerها بر اساس آن طراحی خواهند شد.
---
پایان بخش سوم فصل سوم
از بخش بعدی وارد Data Normalization Engine و سپس Feature Engineering Framework خواهیم شد؛ جایی که معماری از لایه زیرساخت داده وارد قلب تحلیلی سیستم می‌شود و طراحی صدها Feature پایه و ترکیبی آغاز خواهد شد. این بخش، مبنای تمام موتورهای هوشمند بعدی از جمله Smart Money، SMT، Probability Engine و دو Optimizer اصلی خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 3 (ادامه)
بخش چهارم
Data Normalization Engine
---
3.75 مقدمه
پس از آنکه داده‌ها اعتبارسنجی و همگام‌سازی شدند، هنوز آماده استفاده نیستند.
اکثر سیستم‌های معاملاتی تصور می‌کنند اگر داده معتبر باشد، مستقیماً می‌توان آن را وارد اندیکاتورها کرد.
این نیز یک اشتباه بزرگ است.
داده معتبر، الزاماً داده قابل مقایسه نیست.
داده قابل مقایسه، الزاماً داده قابل مدل‌سازی نیست.
و داده قابل مدل‌سازی نیز الزاماً داده مناسب برای یادگیری ماشین یا سیستم تصمیم‌گیری احتمالاتی نیست.
بنابراین بین Data Synchronization و Feature Engineering باید یک لایه بسیار مهم قرار گیرد که وظیفه آن ایجاد یک نمایش یکنواخت (Canonical Representation) از کل بازار باشد.
این لایه Data Normalization Engine نام دارد.
---
3.76 هدف موتور
هدف این موتور فقط تغییر فرمت داده نیست.
بلکه باید:
یکنواخت‌سازی تمام داده‌ها
حذف وابستگی به Exchange
حذف وابستگی به Asset
حذف وابستگی به Decimal Precision
حذف وابستگی به Timeframe
حذف وابستگی به Currency
حذف Biasهای ناشی از مقیاس
ایجاد Featureهای قابل مقایسه
تولید داده استاندارد برای تمام موتورهای بعدی
---
3.77 Canonical Market Model
تمام داده‌های بازار در نهایت باید به یک مدل استاندارد داخلی تبدیل شوند.
برای مثال:
Exchange Price
↓
Canonical Price
----------------------
Exchange Volume
↓
Canonical Volume
----------------------
Exchange Funding
↓
Canonical Funding
----------------------
Exchange OrderBook
↓
Canonical OrderBook
از این لحظه به بعد هیچ Engine نباید داده خام Exchange را ببیند.
---
3.78 Unit Standardization
واحد تمام داده‌ها باید مشخص باشد.
نمونه:
Price
↓
USD
Volume
↓
Base Asset
Quote Volume
↓
USD
Funding
↓
Decimal
Latency
↓
Milliseconds
Spread
↓
Basis Points
Distance
↓
ATR Unit
Return
↓
Log Return
---
3.79 Decimal Precision Normalization
صرافی‌ها Precision متفاوتی دارند.
مثلاً
BTC
0.01
ETH
0.001
DOGE
0.000001
تمام این اختلاف‌ها باید حذف شوند.
---
3.80 Tick Size Normalization
حرکت
۱۰ دلار
برای BTC
معادل
۱۰ دلار
برای DOGE
نیست.
بنابراین
Distance
نباید
بر حسب دلار
اندازه‌گیری شود.
بلکه باید
بر حسب Tick
یا ATR
یا Volatility Unit
بیان شود.
---
3.81 Price Space Transformation
تمام موتورهای بالادستی نباید با Price خام کار کنند.
بلکه با نمایش‌های مختلف آن.
مثلاً:
Raw Price
↓
Normalized Price
↓
Log Price
↓
Relative Price
↓
Z Score
↓
Volatility Adjusted Price
---
3.82 Return Normalization
بازده باید به چند شکل محاسبه شود.
حداقل:
Arithmetic Return
Log Return
Relative Return
Volatility Adjusted Return
Session Return
Rolling Return
Cumulative Return
تمام آنها ذخیره می‌شوند.
---
3.83 Volume Normalization
Volume خام
تقریباً هیچ معنایی ندارد.
باید تبدیل شود به:
Relative Volume
Volume Percentile
Volume Z Score
Session Relative Volume
Rolling Volume Ratio
ATR Adjusted Volume
Liquidity Adjusted Volume
---
3.84 Spread Normalization
Spread
همیشه
بر حسب Tick
و
Basis Point
ذخیره می‌شود.
نه دلار.
---
3.85 Volatility Normalization
تمام فاصله‌ها
باید
به Volatility
وابسته شوند.
مثلاً
Distance
↓
ATR
↓
Normalized Distance
یا
Distance
↓
Realized Volatility
↓
Normalized Distance
---
3.86 Regime Normalization
Featureها باید بدانند
بازار در چه رژیمی است.
برای مثال:
اگر ATR بسیار بالا باشد،
Thresholdهای ثابت دیگر معتبر نیستند.
بنابراین قبل از Feature Engineering باید پارامترها نسبت به رژیم بازار نرمال شوند.
---
3.87 Cross Asset Normalization
یکی از بزرگ‌ترین مشکلات سیستم‌های چندنمادی.
مثلاً
BTC
ETH
SOL
DOGE
دارای رفتار کاملاً متفاوت هستند.
اگر داده خام استفاده شود،
مدل Bias پیدا می‌کند.
بنابراین باید:
Volatility Scaling
Liquidity Scaling
Market Cap Scaling
Tick Scaling
Volume Scaling
انجام شود.
---
3.88 Timeframe Normalization
یک حرکت
۱٪
در
۱ دقیقه
معادل
۱٪
در
روزانه
نیست.
تمام Featureها باید
دارای Time Normalization باشند.
---
3.89 Session Normalization
بازار آسیا
رفتار متفاوتی با بازار آمریکا دارد.
بنابراین:
Volume
Spread
Volatility
Liquidity
Funding Effect
همگی نسبت به Session نرمال می‌شوند.
---
3.90 Robust Scaling
به‌جای استفاده از Min-Max Scaling که نسبت به داده‌های پرت حساس است، موتور باید از روش‌های مقاوم استفاده کند.
از جمله:
Median Centering
Median Absolute Deviation (MAD)
Quantile Scaling
Percentile Rank
Robust Z-Score
نوع نرمال‌سازی باید برای هر Feature به‌صورت مستقل قابل انتخاب باشد.
---
3.91 Adaptive Normalization
هیچ پارامتر نرمال‌سازی ثابت نیست.
پنجره‌های آماری باید بر اساس:
نوسان
حجم
رژیم بازار
زمان روز
وضعیت نقدینگی
به صورت پویا تغییر کنند.
---
3.92 Feature Metadata Injection
پس از نرمال‌سازی، هر Feature فقط یک مقدار نیست.
بلکه شامل مجموعه‌ای از Metadata نیز خواهد بود.
حداقل:
Raw Value
Normalized Value
Scaling Method
Confidence
Quality Score
Data Age
Volatility Context
Session Context
Market Regime
Normalization Version
---
3.93 Information Preservation
هیچ عملیات نرمال‌سازی نباید اطلاعات اصلی را از بین ببرد.
داده خام همیشه نگهداری می‌شود.
تمام تبدیل‌ها قابل بازگشت (Reversible) یا حداقل قابل ردیابی هستند.
---
3.94 Transformation Graph
تمام تبدیل‌هایی که روی یک داده انجام می‌شوند باید در قالب یک Graph ثبت شوند.
مثال:
Raw Price
↓
Currency Conversion
↓
Precision Adjustment
↓
Volatility Scaling
↓
Log Transform
↓
Robust Scaling
↓
Final Feature
این Graph در Replay و Debug استفاده خواهد شد.
---
3.95 Feature Lineage
برای هر Feature باید بتوان منشأ آن را تا داده خام ردیابی کرد.
نمونه:
Normalized Delta
↓
Trade Stream
↓
Exchange WebSocket
↓
Binance
↓
Packet ID
↓
Timestamp
این قابلیت برای تحلیل خطا، آموزش مدل و اعتبارسنجی حیاتی است.
---
3.96 Normalization Quality Index (NQI)
در پایان عملیات، برای هر داده یک شاخص کیفیت نرمال‌سازی محاسبه می‌شود.
این شاخص نشان می‌دهد:
آیا داده نیاز به Scaling شدید داشته است؟
آیا Outlier بوده است؟
آیا Repair روی آن انجام شده است؟
آیا نرمال‌سازی باعث از دست رفتن اطلاعات شده است؟
آیا برای مدل‌های آماری قابل اعتماد است؟
NQI مستقیماً وارد موتور وزن‌دهی Featureها خواهد شد.
---
3.97 Output Contract
خروجی Data Normalization Engine باید شامل چهار بخش باشد:
1. Canonical Data
2. Normalization Metadata
3. Transformation Lineage
4. Normalization Quality Index
هیچ Feature Engineering Engine نباید چیزی غیر از این قرارداد دریافت کند.
---
پایان بخش چهارم فصل سوم
---
آغاز بخش پنجم
از این نقطه وارد مهم‌ترین بخش کل پروژه می‌شویم:
Feature Engineering Framework
این فصل صرفاً معرفی چند اندیکاتور یا چند Feature نیست.
در این معماری، قرار نیست ۵۰ یا ۱۰۰ Feature ساخته شود.
هدف طراحی یک Institutional Feature Factory است که بتواند در آینده هزاران Feature را به‌صورت ماژولار، نسخه‌بندی‌شده، قابل بهینه‌سازی و قابل یادگیری تولید و مدیریت کند.
این بخش، قلب واقعی APEX است و تقریباً تمام موتورهای بعدی از جمله:
Market Intelligence
Smart Money Engine
ICT Engine
SMT Engine
Statistical Engine
Probability Engine
Alpha Optimizer
Risk Optimizer
بر روی خروجی همین Feature Factory ساخته خواهند شد.
نکته طراحی مهم: به نظر من، Feature Engineering باید بسیار فراتر از «محاسبه اندیکاتورها» باشد. در ادامه کتاب، آن را به‌صورت یک سیستم چندلایه شامل Feature Graph، Feature Dependency Engine، Feature Quality Engine، Feature Importance Analyzer، Feature Selection Optimizer و Feature Store طراحی خواهیم کرد تا بتواند در مقیاس هزاران Feature بدون ایجاد پیچیدگی غیرقابل‌کنترل عمل کند. این معماری نسبت به رویکرد رایج، توسعه‌پذیری و قابلیت بهینه‌سازی بسیار بیشتری خواهد داشت.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 4
Institutional Feature Engineering Framework
طراحی کامل موتور استخراج ویژگی‌ها
---
4.1 مقدمه
از این فصل به بعد وارد قلب واقعی سیستم می‌شویم.
اگر Data Layer را سیستم عصبی بدن فرض کنیم،
Feature Engineering مغز اولیه سیستم است.
تقریباً تمام پروژه‌های معاملاتی دنیا Feature را به شکل زیر تعریف می‌کنند.
RSI
MACD
ATR
EMA
VWAP
FVG
OB
SMT
اما اینها Feature نیستند.
اینها فقط Indicator هستند.
Feature در این پروژه به معنی:
> هر کمیتی که بتواند بخشی از واقعیت بازار را به صورت عددی، احتمالاتی یا ساختاری توصیف کند.
بنابراین یک Feature ممکن است:
یک عدد باشد.
یک بردار باشد.
یک ماتریس باشد.
یک گراف باشد.
یک توزیع احتمال باشد.
یک مدل دینامیکی باشد.
یک وضعیت (State) باشد.
یک Confidence باشد.
حتی خروجی یک Optimizer باشد.
---
4.2 هدف Feature Factory
Feature Factory نباید فقط Feature تولید کند.
بلکه باید:
Feature Discovery
Feature Extraction
Feature Cleaning
Feature Validation
Feature Normalization
Feature Ranking
Feature Versioning
Feature Selection
Feature Fusion
Feature Storage
Feature Optimization
Feature Monitoring
Feature Retirement
را انجام دهد.
---
4.3 تعریف رسمی Feature
هر Feature باید دارای ساختار زیر باشد.
ID
Name
Category
SubCategory
Version
Dependencies
Input Sources
Calculation Method
Output Type
Confidence
Reliability
Quality
Latency
Refresh Policy
Normalization Policy
Missing Policy
Optimization Policy
Weight
Importance
Feature Age
Feature State
Historical Performance
Creator
Documentation
Unit
Range
Metadata
هیچ Feature نباید بدون این مشخصات ایجاد شود.
---
4.4 Feature Lifecycle
تمام Featureها چرخه عمر دارند.
Design
↓
Prototype
↓
Validation
↓
Testing
↓
Production
↓
Monitoring
↓
Optimization
↓
Deprecated
↓
Archive
هیچ Feature برای همیشه فعال نیست.
---
4.5 Feature Graph
Featureها مستقل نیستند.
بلکه به هم وابسته‌اند.
مثلاً
ATR
↓
Volatility
↓
Risk Score
↓
Position Size
یا
Volume
↓
Delta
↓
Absorption
↓
Orderflow Score
بنابراین کل سیستم Featureها را به صورت Graph نگهداری می‌کند.
---
4.6 Feature Dependency Engine
قبل از محاسبه هر Feature باید بررسی شود.
آیا تمام وابستگی‌ها آماده هستند؟
مثلاً
SMT
نیاز دارد به
BTC
ETH
Correlation
Swing
Time Alignment
اگر یکی وجود نداشت.
Feature
محاسبه نمی‌شود.
---
4.7 Feature Scheduler
همه Featureها با یک سرعت محاسبه نمی‌شوند.
مثلاً
Funding Feature
هر
8 ساعت
اما
Orderflow Feature
هر
100ms
---
بنابراین هر Feature باید داشته باشد.
Refresh Interval
Trigger Type
Priority
Dependency
Execution Cost
---
4.8 Feature Cost
یکی از اشتباهات بزرگ.
همه Featureها را
هر Tick
محاسبه کنیم.
این کار ممنوع است.
هر Feature
دارای Cost
خواهد بود.
مثلاً
EMA
Cost=1
------------
SMT
Cost=7
------------
Monte Carlo
Cost=95
------------
Optimizer
Cost=400
Scheduler
بر اساس Cost
تصمیم می‌گیرد.
---
4.9 Feature Cache
هر Feature
دارای Cache
است.
اگر ورودی تغییر نکرد.
Feature
دوباره محاسبه نمی‌شود.
---
4.10 Incremental Feature Update
اگر
فقط
آخرین Tick
تغییر کرد.
نباید
کل Feature
از ابتدا محاسبه شود.
بلکه فقط
Incremental Update
انجام شود.
---
4.11 Lazy Evaluation
Feature
فقط زمانی
محاسبه می‌شود.
که
واقعاً
لازم باشد.
---
4.12 Feature Registry
تمام Featureها
داخل Registry
ثبت می‌شوند.
مثلاً
Liquidity
↓
v1
↓
v2
↓
v3
---
4.13 Feature Metadata
هر Feature
همیشه
دارای Metadata
است.
Confidence
Quality
Reliability
Age
Version
Execution Time
Memory Usage
Latency
Dependencies
Source
---
4.14 Feature Quality
Feature
خوب یا بد
نیست.
بلکه
Quality
دارد.
مثلاً
SMT
اگر
داده ETH
قدیمی باشد.
Quality
کم می‌شود.
---
4.15 Feature Confidence
Confidence
یعنی
چقدر
به مقدار Feature
اعتماد داریم.
---
4.16 Feature Reliability
Reliability
یعنی
این Feature
در گذشته
چقدر
درست عمل کرده است.
مثلاً
SMT
Bull Market
94%
Range
73%
Crash
61%
---
4.17 Feature Importance
Featureها
اهمیت یکسان ندارند.
مثلاً
Liquidity
شاید
بیشتر از
RSI
مهم باشد.
اما
این مقدار
ثابت نیست.
---
4.18 Dynamic Importance
Importance
وابسته به
Regime
است.
مثلاً
در روند
Structure
مهم‌تر است.
در رنج
Liquidity
مهم‌تر است.
در خبر
Volatility
مهم‌تر است.
---
4.19 Feature Health
هر Feature
باید
Health
داشته باشد.
Healthy
Warning
Critical
Disabled
---
4.20 Feature Retirement
اگر
Feature
سه ماه
هیچ ارزش افزوده‌ای
نداشت.
Retire
می‌شود.
ولی حذف
نمی‌شود.
---
4.21 Feature Categories
در این معماری، Featureها به صورت سلسله‌مراتبی طبقه‌بندی می‌شوند.
Level 0 — Primitive Features
اینها مستقیماً از داده خام استخراج می‌شوند.
نمونه:
Price
Volume
Spread
Trade Count
Bid Size
Ask Size
Funding
Open Interest
Liquidation
VWAP
Delta
---
Level 1 — Derived Features
از ترکیب Primitiveها ساخته می‌شوند.
نمونه:
ATR
Volatility
Relative Volume
Order Book Imbalance
Delta Divergence
Cumulative Delta
Realized Variance
Session VWAP Distance
---
Level 2 — Structural Features
ساختار بازار را توصیف می‌کنند.
نمونه:
BOS
CHOCH
Swing Quality
Internal Structure
External Structure
Trend Strength
Compression Score
Expansion Score
---
Level 3 — Institutional Features
ویژگی‌های مربوط به رفتار بازیگران بزرگ.
نمونه:
Liquidity Sweep Score
Stop Hunt Probability
Order Block Quality
Fair Value Gap Quality
SMT Strength
Wyckoff Phase Score
Distribution Probability
Accumulation Probability
Manipulation Index
---
Level 4 — Contextual Features
زمینه کلی بازار.
نمونه:
Market Regime
Session State
Correlation State
Macro Alignment
Funding Regime
Sentiment State
Volatility Cluster
---
Level 5 — Predictive Features
Featureهایی که خودشان خروجی مدل‌های آماری یا احتمالاتی هستند.
نمونه:
Probability of Trend Continuation
Probability of Mean Reversion
Expected Move
Expected Holding Time
Expected Drawdown
Expected Volatility
Alpha Score
---
Level 6 — Meta Features
Featureهایی که درباره عملکرد سایر Featureها هستند.
نمونه:
Feature Stability
Feature Drift
Historical Accuracy
Information Gain
Mutual Information
Predictive Decay
Feature Confidence Trend
---
4.22 Feature Factory Pipeline
هر Feature دقیقاً از این Pipeline عبور می‌کند.
Request
↓
Dependency Resolution
↓
Input Validation
↓
Data Availability Check
↓
Normalization Check
↓
Feature Computation
↓
Quality Evaluation
↓
Confidence Assignment
↓
Reliability Update
↓
Metadata Injection
↓
Caching
↓
Version Control
↓
Feature Store
هیچ Feature اجازه دور زدن این Pipeline را ندارد.
---
4.23 اصل مهم Feature Engineering
یکی از تغییراتی که نسبت به معماری اولیه پیشنهاد می‌کنم، این است که هیچ موتور هوشمندی (SMT، ICT، Liquidity، Probability، Optimizer و...) نباید مستقیماً به Data Layer متصل شود.
همه آن‌ها فقط از Feature Store تغذیه شوند.
این تصمیم چند مزیت اساسی دارد:
حذف وابستگی بین موتورهای هوشمند و داده خام.
امکان استفاده مجدد از Featureها توسط چندین موتور.
کاهش شدید هزینه محاسباتی.
امکان نسخه‌بندی و مقایسه Featureها.
فراهم شدن بستر مناسب برای دو Optimizer اصلی که قبلاً طراحی کردیم؛ زیرا هر دو Optimizer به جای کار با داده خام، روی فضای استاندارد Featureها عمل خواهند کرد.
---
پایان بخش اول فصل چهارم
در ادامه فصل چهارم، وارد طراحی Feature Store، Feature Selection Engine، Feature Fusion Engine، Feature Importance Optimizer، Feature Drift Detection، Auto Feature Discovery و Feature Evolution Framework خواهیم شد. این بخش، پایه مستقیم Signal Optimizer است و نقش کلیدی در افزایش دقت تولید سیگنال و سازگاری سیستم با تغییرات بازار خواهد داشت.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange
Volume I
---
فصل 4 (ادامه)
بخش دوم
Institutional Feature Store Architecture
---
4.24 مقدمه
اگر بخواهم فقط یک قسمت را به عنوان مهم‌ترین نوآوری کل معماری انتخاب کنم، آن Feature Store خواهد بود.
تقریباً تمام پروژه‌های ترید موجود، هر بار که به یک اندیکاتور نیاز دارند، آن را دوباره محاسبه می‌کنند.
مثلاً
SMT
↓
ATR
↓
EMA
↓
Volume
↓
Volatility
سپس
Liquidity Engine
دوباره
ATR
را محاسبه می‌کند.
بعد
Risk Engine
دوباره
ATR
را محاسبه می‌کند.
بعد
Optimizer
باز هم
ATR
را محاسبه می‌کند.
این معماری بسیار ضعیف است.
---
4.25 فلسفه Feature Store
در این پروژه،
هیچ Engine
اجازه محاسبه Feature
را ندارد.
تمام Featureها
فقط
در Feature Factory
محاسبه می‌شوند.
تمام Engineها
فقط
مصرف‌کننده هستند.
---
4.26 Feature Store چیست؟
Feature Store
در واقع
یک Database
نیست.
یک Cache
نیست.
یک Dictionary
نیست.
بلکه
یک سیستم مدیریت دانش بازار است.
---
Feature Store باید بتواند:
Feature را ذخیره کند.
نسخه Feature را ذخیره کند.
Metadata را ذخیره کند.
Confidence را ذخیره کند.
Reliability را ذخیره کند.
Dependency را ذخیره کند.
تاریخچه Feature را نگهداری کند.
کیفیت Feature را نگهداری کند.
Drift را نگهداری کند.
عمر Feature را نگهداری کند.
---
4.27 Feature Object
هر Feature
در Store
دارای ساختار زیر است.
Feature ID
Feature Name
Version
Raw Value
Normalized Value
Confidence
Reliability
Importance
Quality
Age
Timestamp
Dependencies
Dependency Versions
Source
Normalization Version
Calculation Version
Execution Time
Memory Cost
CPU Cost
Latency
Market State
Session
Exchange
Asset
Feature Hash
---
4.28 سه لایه Feature Store
Feature Store
سه بخش دارد.
---
Layer 1
Hot Store
---
تمام Featureهای فعال
داخل RAM
---
Layer 2
Warm Store
---
آخرین چند روز
داخل
Memory Mapped Storage
---
Layer 3
Cold Store
---
تمام تاریخ
داخل Database
---
4.29 Hot Store
این بخش
کمترین Latency
را دارد.
فقط
Featureهایی که
در حال حاضر
استفاده می‌شوند.
---
مثلاً
Current Trend
Current Liquidity
Current SMT
Current OB
Current FVG
Current Context
---
4.30 Warm Store
آخرین چند روز
برای
Optimizer
Replay
Learning
---
4.31 Cold Store
کل تاریخ.
برای
Research
Walk Forward
Monte Carlo
Model Training
---
4.32 Feature Index
تمام Featureها
چندین Index
دارند.
مثلاً
بر اساس
Feature Name
Asset
Exchange
Time
Category
Importance
Regime
Session
---
4.33 Multi Timeframe Store
Featureها
فقط
یک تایم‌فریم
ندارند.
مثلاً
ATR
↓
1m
↓
5m
↓
15m
↓
1H
↓
4H
↓
1D
همه
داخل Store
وجود دارند.
---
4.34 Multi Asset Store
مثلاً
SMT
برای
BTC
ETH
SOL
همزمان
وجود دارد.
---
4.35 Snapshot Engine
در هر لحظه
Feature Store
باید
Snapshot
بگیرد.
مثلاً
12:00:00.000
تمام وضعیت
بازار
ثبت شود.
---
4.36 Snapshot Version
هر Snapshot
دارای Version
است.
تا
Replay
دقیق
امکان‌پذیر باشد.
---
4.37 Immutable Snapshot
هیچ Snapshot
بعداً
تغییر
نمی‌کند.
---
4.38 Feature Delta
به جای ذخیره کامل
Feature
فقط
تغییرات
نیز ذخیره می‌شوند.
مثلاً
Liquidity
↓
+0.12
---
4.39 Compression
تمام History
باید
فشرده شود.
اما
بدون
از دست رفتن اطلاعات.
---
4.40 Feature Aging
هر Feature
سن دارد.
مثلاً
Liquidity
بعد از
۳ دقیقه
قدیمی می‌شود.
Funding
بعد از
۸ ساعت.
---
سن Feature
باید
در تصمیم
تاثیر داشته باشد.
---
4.41 Feature Freshness
دو Feature
ممکن است
سن برابر
داشته باشند.
اما
Freshness
متفاوت.
مثلاً
Funding
دو ساعت
قدیمی
هنوز
Fresh
است.
اما
OrderBook
دو ثانیه
قدیمی
نیست.
---
4.42 Feature Expiration
برخی Featureها
Expire
می‌شوند.
مثلاً
News Feature
بعد از
چند ساعت.
---
4.43 Confidence Decay
Confidence
Feature
به مرور
کم می‌شود.
---
4.44 Reliability Update
Reliability
Feature
ثابت نیست.
مثلاً
SMT
در
Bull
عملکرد عالی دارد.
در
Range
ضعیف.
پس
Reliability
دائماً
به‌روزرسانی می‌شود.
---
4.45 Feature Drift Engine
یکی از مهم‌ترین قسمت‌های کل پروژه.
تقریباً تمام الگوریتم‌های بازار
بعد از مدتی
دچار
Drift
می‌شوند.
مثلاً
یک Feature
سال گذشته
Accuracy
بالا داشت.
امسال
ندارد.
Feature Store
باید
این تغییر
را
تشخیص دهد.
---
Drift باید در چند سطح بررسی شود.
Mean Drift
Variance Drift
Distribution Drift
Correlation Drift
Importance Drift
Predictive Drift
Regime Drift
---
4.46 Feature Stability
هر Feature
دارای
Stability
است.
Feature
که
هر دقیقه
جهش می‌کند.
برای
Probability
خوب نیست.
---
4.47 Feature Consistency
اگر
Feature
در
1m
و
5m
کاملاً
متناقض باشد.
باید
ثبت شود.
---
4.48 Feature Correlation Matrix
تمام Featureها
باید
Correlation Matrix
داشته باشند.
مثلاً
ATR
↓
Volatility
↓
0.98
----------------
Liquidity
↓
SMT
↓
0.42
----------------
Trend
↓
Momentum
↓
0.91
---
4.49 Redundant Feature Detector
دو Feature
ممکن است
تقریباً
یک چیز
را اندازه بگیرند.
مثلاً
سه اندیکاتور مختلف که همگی مومنتوم را توصیف می‌کنند.
Feature Store
باید
آنها را
پیدا کند.
---
4.50 Information Gain
برای هر Feature باید محاسبه شود:
اگر این Feature حذف شود،
دقت کل سیستم
چقدر کاهش پیدا می‌کند؟
این معیار یکی از مهم‌ترین ورودی‌های Signal Optimizer خواهد بود و اجازه می‌دهد وزن Featureها بر اساس ارزش واقعی اطلاعاتی آن‌ها تنظیم شود، نه بر اساس فرضیات ثابت.
---
4.51 Mutual Information Engine
علاوه بر همبستگی خطی، وابستگی غیرخطی بین Featureها نیز باید اندازه‌گیری شود.
از معیارهایی مانند:
Mutual Information
Conditional Mutual Information
Transfer Entropy (در صورت امکان)
Distance Correlation
برای تشخیص وابستگی واقعی استفاده می‌شود.
این کار مانع از انتخاب Featureهای تکراری و کم‌اطلاعات می‌شود.
---
4.52 Feature Lineage Graph
هر Feature باید دارای یک گراف منشأ باشد.
نمونه:
Raw Trades
        │
        ▼
Delta
        │
        ▼
Cumulative Delta
        │
        ▼
Absorption Score
        │
        ▼
Institutional Buying Probability
در هر زمان باید بتوان مسیر کامل تولید یک Feature را مشاهده و بازسازی کرد.
---
4.53 Feature Provenance
علاوه بر Lineage، برای هر Feature باید مشخص باشد:
اولین بار چه زمانی ایجاد شد.
توسط کدام نسخه الگوریتم محاسبه شد.
از کدام داده خام استفاده کرده است.
چند بار Recomputed شده است.
آخرین زمان اعتبارسنجی آن چه زمانی بوده است.
---
4.54 Feature Store Query Engine
هیچ موتور هوشمندی نباید مستقیماً در حافظه Featureها جستجو کند.
تمام درخواست‌ها از طریق Query Engine انجام می‌شوند.
Query Engine باید از:
Time Slice Query
Multi-Asset Query
Multi-Timeframe Query
Snapshot Query
Regime Query
Session Query
Version Query
پشتیبانی کند.
---
4.55 Feature Consistency Contract
هر Feature قبل از خروج از Store باید پنج شرط را داشته باشد:
1. معتبر (Validated)
2. نرمال‌شده (Normalized)
3. نسخه‌بندی‌شده (Versioned)
4. دارای Confidence و Quality
5. دارای Lineage و Provenance
در غیر این صورت Feature به موتورهای بالادستی تحویل داده نمی‌شود.
---
پایان بخش دوم فصل چهارم
از بخش بعدی وارد Feature Selection Engine خواهیم شد؛ جایی که سیستم به‌صورت تطبیقی تصمیم می‌گیرد از میان هزاران Feature موجود، در هر رژیم بازار، هر نماد و هر تایم‌فریم، دقیقاً کدام Featureها باید وارد موتورهای تصمیم‌گیری شوند. این بخش مستقیماً به طراحی Signal Optimizer متصل خواهد شد و یکی از تفاوت‌های اصلی این معماری با سامانه‌های معاملاتی رایج خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 4 (ادامه)
بخش چهارم
Institutional Feature Fusion Engine
---
4.86 فلسفه طراحی
بعد از اینکه Feature Selection پایان یافت،
هنوز هیچ تصمیم معاملاتی گرفته نشده است.
دلیل بسیار ساده است.
وجود چندین Feature خوب،
به معنی وجود یک سیگنال خوب نیست.
در اکثر سیستم‌های دنیا این اتفاق می‌افتد:
RSI = Bull
MACD = Bull
VWAP = Bull
ATR = Bull
↓
BUY
این معماری تقریباً کاملاً ابتدایی است.
چرا؟
زیرا تمام Featureها مستقل فرض شده‌اند.
در صورتی که بازار یک سیستم بسیار پیچیده، چندلایه، وابسته به زمینه (Contextual)، غیرخطی و دارای روابط علی (Causal) است.
بنابراین مرحله بعدی معماری، ترکیب Featureها نیست.
بلکه مدلسازی روابط بین Featureها است.
---
4.87 تعریف Feature Fusion
Feature Fusion یعنی:
> تبدیل هزاران Feature مستقل به یک نمایش یکتا از وضعیت واقعی بازار.
هدف تولید سیگنال نیست.
هدف تولید درک بازار است.
---
4.88 خروجی Feature Fusion
خروجی این موتور تنها یک عدد نیست.
بلکه مجموعه‌ای از اشیای ساختاریافته است.
Market State Vector
Institutional State
Liquidity State
Volatility State
Trend State
Structure State
Execution State
Risk State
Probability State
Meta State
تمام موتورهای بعدی فقط با این Stateها کار خواهند کرد.
---
4.89 سه مرحله Fusion
Feature Fusion در سه مرحله انجام می‌شود.
Primitive Fusion
↓
Context Fusion
↓
Probabilistic Fusion
---
4.90 Primitive Fusion
ابتدا Featureهای هم‌خانواده ترکیب می‌شوند.
مثلاً
ATR
Realized Volatility
Historical Volatility
Implied Volatility
↓
Unified Volatility
یا
Delta
Book Imbalance
Sweep
Absorption
↓
Liquidity Pressure
---
4.91 Context Fusion
در مرحله دوم
تمام خروجی‌ها
با Context
ترکیب می‌شوند.
مثلاً
Trend
+
Liquidity
+
Session
+
Macro
↓
Context Aware Trend
---
4.92 Probabilistic Fusion
در مرحله سوم
سیستم دیگر
اعداد
را ترکیب نمی‌کند.
بلکه
احتمال‌ها
را ترکیب می‌کند.
مثلاً
Trend Probability
73%
Liquidity Probability
81%
Structure Probability
62%
↓
Joint Probability
---
4.93 Feature Family
Featureها
قبل از Fusion
دسته‌بندی می‌شوند.
---
Family
Trend
---
Family
Momentum
---
Family
Liquidity
---
Family
Structure
---
Family
Volatility
---
Family
Volume
---
Family
Orderflow
---
Family
Macro
---
Family
Sentiment
---
Family
Derivatives
---
Family
OnChain
---
4.94 Hierarchical Fusion
Fusion
درختی است.
مثلاً
Volume
↓
Delta
↓
Absorption
↓
Liquidity
↓
Institutional Activity
↓
Market State
نه اینکه
همه چیز
یکباره
ترکیب شود.
---
4.95 Dependency-aware Fusion
اگر
Liquidity
دارای
Confidence پایین
باشد.
تمام Featureهای
وابسته
نیز
وزنشان
کاهش پیدا می‌کند.
---
4.96 Confidence Propagation
Confidence
در کل Graph
منتشر می‌شود.
مثلاً
Liquidity
0.82
↓
Institutional Buying
0.74
↓
Trend Confirmation
0.69
---
4.97 Quality Propagation
همین موضوع
برای
Quality
نیز
وجود دارد.
---
4.98 Reliability Propagation
Reliability
Feature
به Feature
بعدی
منتقل می‌شود.
---
4.99 Information Conservation
یکی از قوانین اصلی.
هیچ Fusion
نباید
اطلاعات
را نابود کند.
اگر
دو Feature
متناقض باشند.
نباید
میانگین گرفته شود.
بلکه
Conflict
ثبت شود.
---
4.100 Conflict Engine
اگر
Featureها
اختلاف داشته باشند.
سیستم
سه حالت دارد.
---
Confirmation
---
Conflict
---
Unknown
---
Unknown
کاملاً
مجاز است.
---
سیستم
نباید
به زور
تصمیم بگیرد.
---
4.101 Consensus Engine
Featureهایی که
همدیگر را
تأیید می‌کنند.
دارای
Consensus Score
می‌شوند.
مثلاً
Trend
Bull
Momentum
Bull
Liquidity
Bull
↓
Consensus
0.91
---
4.102 Contradiction Engine
برعکس.
Trend
Bull
Liquidity
Bear
Macro
Bear
↓
Conflict
0.83
---
Conflict
خودش
یک Feature
است.
---
4.103 Context Weighting
وزن Featureها
ثابت نیست.
مثلاً
در
News
وزن
Liquidity
کمتر می‌شود.
وزن
Volatility
بیشتر.
---
4.104 Dynamic Fusion Graph
Graph
هر لحظه
تغییر می‌کند.
مثلاً
در
Crash
Featureهای
Risk
به بالای Graph
منتقل می‌شوند.
---
4.105 Attention Layer
یکی از بخش‌هایی که در معماری اولیه وجود نداشت و پیشنهاد می‌کنم اضافه شود.
ایده آن مشابه مکانیزم Attention در مدل‌های مدرن است، اما بدون الزام به استفاده از شبکه عصبی.
در هر لحظه سیستم تعیین می‌کند:
کدام خانواده Featureها در شرایط فعلی بیشترین اطلاعات مفید را دارند.
نمونه:
Current Regime
↓
Trend Market
↓
Attention
Trend = 0.31
Liquidity = 0.26
OrderFlow = 0.18
Macro = 0.09
Sentiment = 0.04
این وزن‌ها در Fusion اعمال می‌شوند و به‌صورت تطبیقی تغییر می‌کنند.
---
4.106 Market State Vector (MSV)
مهم‌ترین خروجی Feature Fusion.
به جای ارسال هزاران Feature،
یک بردار واحد ساخته می‌شود.
به عنوان مثال:
Trend Strength
Liquidity Score
Institutional Activity
Volatility State
Manipulation Probability
Momentum Score
Compression Level
Expansion Probability
Risk Regime
Execution Difficulty
Signal Density
Confidence
Entropy
این بردار نماینده وضعیت کل بازار در همان لحظه است.
---
4.107 Institutional State Vector (ISV)
علاوه بر MSV، یک بردار اختصاصی برای رفتار بازیگران بزرگ ساخته می‌شود.
نمونه مؤلفه‌ها:
Accumulation Probability
Distribution Probability
Stop Hunt Probability
Liquidity Harvest Score
Smart Money Participation
Hidden Absorption
Iceberg Probability
Sweep Intensity
Reversal Trap Probability
این بردار مستقیماً توسط موتورهای ICT/SMC، Probability Engine و Signal Optimizer استفاده می‌شود.
---
4.108 Meta State Vector
سیستم باید از وضعیت خودش نیز آگاه باشد.
Meta State شامل مواردی مانند:
Data Quality
Feature Quality
Average Confidence
Synchronization Quality
Drift Level
Optimizer Freshness
Risk Engine Health
Execution Readiness
است.
اگر Meta State نامناسب باشد، حتی در صورت مناسب بودن بازار، سیستم می‌تواند از تولید سیگنال خودداری کند.
---
4.109 State Consistency Engine
قبل از خروج بردارهای وضعیت، باید سازگاری داخلی آن‌ها بررسی شود.
برای مثال:
Trend بسیار قوی ولی Momentum منفی
نقدینگی بسیار پایین ولی حجم فوق‌العاده بالا
احتمال انباشت بالا همراه با Distribution بسیار بالا
این تناقض‌ها باید ثبت شوند و به‌صورت Feature مستقل به موتورهای بعدی منتقل گردند، نه اینکه نادیده گرفته شوند.
---
4.110 Fusion Audit Trail
تمام مراحل Fusion باید قابل بازسازی باشند.
برای هر State باید مشخص باشد:
از کدام Featureها تشکیل شده است.
وزن هر Feature چه بوده است.
Attention چگونه محاسبه شده است.
چه Conflictهایی وجود داشته است.
Confidence نهایی چگونه به دست آمده است.
نسخه الگوریتم Fusion چه بوده است.
---
4.111 Output Contract
خروجی Feature Fusion Engine شامل موارد زیر است:
1. Market State Vector (MSV)
2. Institutional State Vector (ISV)
3. Meta State Vector
4. Consensus Matrix
5. Conflict Matrix
6. Attention Weights
7. Fusion Confidence
8. Fusion Audit Metadata
این مجموعه، تنها ورودی مجاز برای لایه بعدی معماری خواهد بود.
---
پایان بخش چهارم فصل چهارم
---
آغاز بخش پنجم
در بخش بعدی وارد Market Intelligence Engine خواهیم شد.
این بخش، مهم‌ترین تفاوت APEX با تقریباً تمام پلتفرم‌های معاملاتی موجود است. در اینجا سیستم از «محاسبه اندیکاتور» عبور می‌کند و به یک موتور استنتاج (Inference Engine) تبدیل می‌شود که با استفاده از بردارهای وضعیت، فرضیه‌های مختلف درباره وضعیت بازار را ایجاد، ارزیابی، رتبه‌بندی و به‌روزرسانی می‌کند. این موتور، پایه مستقیم Signal Optimizer، Probability Engine و در نهایت تصمیم‌گیری معاملاتی خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 5
Institutional Market Intelligence Engine
طراحی کامل موتور هوش بازار
---
5.1 مقدمه
اگر Feature Engineering را «بینایی» سیستم بدانیم،
Market Intelligence همان «قشر مغز» است.
تقریباً تمام سیستم‌های معاملاتی موجود دنیا بعد از محاسبه اندیکاتورها مستقیماً وارد تولید سیگنال می‌شوند.
ساختار رایج تقریباً همیشه به شکل زیر است:
Data
↓
Indicators
↓
Rules
↓
Buy / Sell
یا
Features
↓
Machine Learning
↓
Prediction
↓
Trade
اما این معماری یک مرحله بسیار مهم را حذف کرده است.
آن مرحله،
درک بازار (Market Understanding)
است.
یک معامله‌گر حرفه‌ای قبل از اینکه تصمیم بگیرد،
ابتدا سعی می‌کند بفهمد:
"الان بازار دارد چه کاری انجام می‌دهد؟"
نه اینکه
"الان اندیکاتور چه می‌گوید؟"
دقیقاً همین فلسفه باید در معماری سیستم نیز پیاده‌سازی شود.
---
5.2 تعریف رسمی Market Intelligence
Market Intelligence
سیستمی است که:
از روی هزاران Feature
و صدها رابطه
و ده‌ها Context
یک مدل داخلی از وضعیت واقعی بازار می‌سازد.
این مدل
State-Based
است.
نه Rule-Based.
---
5.3 وظایف موتور
این موتور مسئول موارد زیر است:
Market Interpretation
Context Recognition
Hypothesis Generation
Hypothesis Ranking
Evidence Collection
Evidence Fusion
Causal Reasoning
Conflict Resolution
Scenario Simulation
Confidence Estimation
Adaptive Belief Updating
Market Narrative Construction
---
5.4 فلسفه طراحی
بازار
همیشه
دارای
یک حقیقت
نیست.
بلکه
دارای
چندین فرضیه
است.
مثلاً
در یک لحظه ممکن است:
Bull Trend
0.58
------------------
Liquidity Sweep
0.81
------------------
Distribution
0.49
------------------
Stop Hunt
0.74
همه همزمان معتبر باشند.
سیستم نباید فقط یکی را انتخاب کند.
---
5.5 Hypothesis Engine
اولین بخش موتور.
این قسمت
فرضیه تولید می‌کند.
مثلاً
Institutional Accumulation
Distribution
Expansion
Compression
Continuation
Reversal
Manipulation
False Breakout
Liquidity Hunt
Trend Exhaustion
اینها
Prediction
نیستند.
Hypothesis
هستند.
---
5.6 Evidence Engine
برای هر Hypothesis
سیستم
شروع به جمع‌آوری شواهد می‌کند.
مثلاً
Hypothesis
↓
Accumulation
Evidenceها
Liquidity Sweep
Bullish Delta
Absorption
Positive SMT
Discount Zone
High Volume
Weak Selling
Stable Funding
---
5.7 Evidence Weight
تمام Evidenceها
وزن یکسان ندارند.
مثلاً
در
Crash
وجود
Liquidity Sweep
بسیار مهم‌تر از
RSI
است.
---
5.8 Evidence Reliability
اگر
Evidence
از
Feature
با Confidence پایین
تولید شده باشد.
وزن آن
کاهش پیدا می‌کند.
---
5.9 Evidence Correlation
اگر
دو Evidence
تقریباً
یک چیز
را
اندازه بگیرند.
وزن دوم
کاهش پیدا می‌کند.
---
5.10 Evidence Conflict
اگر
Evidenceها
با هم
متناقض باشند.
ثبت می‌شوند.
نه حذف.
---
5.11 Hypothesis Score
هر فرضیه
دارای
Score
است.
Evidence
↓
Confidence
↓
Reliability
↓
Importance
↓
Context
↓
Hypothesis Score
---
5.12 Belief Engine
مهم‌ترین قسمت.
سیستم
دارای
Belief
است.
مثلاً
Bull Trend
72%
اگر
Evidence جدید
بیاید.
Belief
به‌روزرسانی می‌شود.
---
این کار
به صورت
کاملاً
پیوسته
انجام می‌شود.
---
5.13 Bayesian Belief Update
پیشنهاد معماری:
به جای افزایش یا کاهش ساده امتیاز، هر فرضیه دارای یک توزیع احتمال باشد و با ورود شواهد جدید، به‌صورت بیزی (Bayesian Updating) به‌روزرسانی شود.
به این ترتیب:
سیستم می‌تواند عدم قطعیت را حفظ کند.
از تغییرات ناگهانی ناشی از یک Feature جلوگیری می‌شود.
Evidenceهای با Confidence پایین اثر کمتری خواهند داشت.
Beliefها به‌صورت تدریجی تغییر می‌کنند.
---
5.14 Competing Hypotheses
فرضیه‌ها
رقیب
هم هستند.
مثلاً
Accumulation
Distribution
نمی‌توانند
هر دو
۱۰۰٪
درست باشند.
---
سیستم
رقابت
را
مدیریت می‌کند.
---
5.15 Complementary Hypotheses
اما
بعضی فرضیه‌ها
مکمل
هم هستند.
مثلاً
Liquidity Sweep
↓
Accumulation
↓
Trend Reversal
---
5.16 Narrative Engine
یکی از مهم‌ترین نوآوری‌های این معماری.
سیستم فقط عدد تولید نمی‌کند.
بلکه یک «روایت بازار» می‌سازد.
مثلاً:
> بازار در حال خروج از فاز انباشت است. هم‌زمان چندین برداشت نقدینگی در سمت فروش مشاهده شده، فشار فروش در حال کاهش است، جذب سفارش‌ها افزایش یافته و واگرایی مثبت SMT نیز این سناریو را تقویت می‌کند. با این حال، حجم هنوز به سطح تأیید کامل نرسیده و بنابراین Confidence این روایت متوسط ارزیابی می‌شود.
این روایت برای انسان و همچنین برای موتورهای تصمیم‌گیری قابل استفاده است.
---
5.17 Causal Graph
سیستم نباید فقط همبستگی را ببیند.
بلکه تا حد امکان روابط علّی را نیز مدل کند.
نمونه:
Liquidity Sweep
↓
Forced Liquidation
↓
Absorption
↓
Trend Reversal
این گراف جایگزین Ruleهای ثابت نمی‌شود، بلکه به عنوان یک مدل ساختاری در کنار آن‌ها عمل می‌کند.
---
5.18 Scenario Engine
به جای یک نتیجه، چند سناریو ساخته می‌شود.
مثلاً:
سناریو A
ادامه روند
Probability = 41%
---
سناریو B
فیک بریک اوت
Probability = 35%
---
سناریو C
رنج
Probability = 24%
سیستم همزمان روی همه سناریوها فکر می‌کند.
---
5.19 Counterfactual Engine
یکی از قابلیت‌هایی که در سیستم‌های معاملاتی بسیار نادر است.
سیستم سؤال می‌پرسد:
اگر
Liquidity Sweep
وجود نداشت.
آیا
Hypothesis
هنوز
درست بود؟
این تحلیل مشخص می‌کند که کدام Evidenceها واقعاً تعیین‌کننده هستند.
---
5.20 Uncertainty Engine
عدم قطعیت
یک خروجی معتبر است.
اگر
Evidence
ناکافی باشد.
سیستم
باید
بگوید:
Unknown
نه اینکه
Buy
یا
Sell
تولید کند.
---
5.21 Institutional Intent Model
یکی از مهم‌ترین خروجی‌های این موتور.
هدف آن پاسخ به این سؤال است:
> «اگر فرض کنیم رفتار غالب بازار توسط بازیگران بزرگ هدایت می‌شود، محتمل‌ترین نیت فعلی آن‌ها چیست؟»
این مدل خروجی‌هایی مانند:
احتمال انباشت
احتمال توزیع
احتمال جذب نقدینگی
احتمال فریب بازار
احتمال ادامه روند
احتمال تغییر فاز
را تولید می‌کند.
---
5.22 Adaptive Memory
Market Intelligence فقط وضعیت فعلی را نمی‌بیند.
بلکه حافظه دارد.
این حافظه شامل:
آخرین فرضیه‌ها
تغییرات Belief
تاریخچه سناریوها
موفقیت یا شکست روایت‌های قبلی
پایداری Context
است.
به این ترتیب، هر تصمیم در خلأ گرفته نمی‌شود بلکه در بستر تاریخچه اخیر بازار قرار می‌گیرد.
---
5.23 Explainability Layer
برای هر نتیجه باید بتوان توضیح داد:
چرا این فرضیه ایجاد شد؟
کدام Evidenceها بیشترین اثر را داشتند؟
چه Evidenceهایی رد شدند؟
مهم‌ترین تضادها چه بودند؟
Confidence چگونه محاسبه شد؟
این قابلیت برای توسعه، اشکال‌زدایی و اعتماد به سیستم ضروری است.
---
5.24 Output Contract
خروجی Market Intelligence Engine شامل موارد زیر است:
1. Hypothesis Set
2. Belief State
3. Scenario Set
4. Institutional Intent Vector
5. Market Narrative
6. Evidence Graph
7. Conflict Graph
8. Uncertainty Metrics
9. Explainability Metadata
هیچ موتور تصمیم‌گیری یا Optimizer نباید مستقیماً از Feature Fusion استفاده کند؛ همه آن‌ها باید تنها از این قرارداد استاندارد تغذیه شوند.
---
پایان بخش اول فصل پنجم
در بخش بعدی وارد Institutional Probability Engine خواهیم شد؛ جایی که تمام فرضیه‌ها، سناریوها و بردارهای هوش بازار به توزیع‌های احتمال، امید ریاضی، ریسک شرطی، احتمال موفقیت معامله و عدم‌قطعیت قابل‌اندازه‌گیری تبدیل می‌شوند. این موتور مستقیماً ورودی Signal Optimizer و Risk & Execution Optimizer خواهد بود و پایه تصمیم‌گیری کمی (Quantitative Decision Making) کل سامانه را تشکیل می‌دهد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 5 (ادامه)
بخش دوم
Institutional Probability Engine
---
5.25 مقدمه
تا اینجای معماری،
سیستم موفق شده است:
داده‌ها را جمع‌آوری کند.
آنها را اعتبارسنجی کند.
آنها را همگام‌سازی کند.
آنها را نرمال‌سازی کند.
Feature تولید کند.
Featureها را انتخاب کند.
آنها را Fusion کند.
وضعیت بازار را مدل کند.
فرضیه‌ها را ایجاد کند.
اما هنوز یک سؤال اساسی بی‌پاسخ مانده است.
> احتمال اینکه این فرضیه واقعاً صحیح باشد چقدر است؟
اکثر سیستم‌های معاملاتی این مرحله را حذف می‌کنند.
مثلاً می‌گویند:
BUY
Confidence = 83%
اما هیچ توضیحی وجود ندارد که این ۸۳٪ چگونه محاسبه شده است.
در APEX چنین چیزی وجود ندارد.
تمام احتمال‌ها باید دارای پایه آماری، احتمالاتی و قابل ممیزی باشند.
---
5.26 هدف موتور Probability
این موتور مسئول تبدیل تمام اطلاعات قبلی به فضای احتمال است.
ورودی آن:
Market Intelligence
↓
Hypothesis
↓
Scenario
↓
Institutional State
↓
Market State
خروجی آن:
Probability Distribution
↓
Expected Value
↓
Risk Distribution
↓
Decision Confidence
---
5.27 فلسفه طراحی
بازار
یک عدد
نیست.
بازار
یک توزیع احتمال
است.
سیستم نباید بگوید
قیمت بالا می‌رود.
بلکه باید بگوید:
Probability
Up
61%
Range
24%
Down
15%
---
5.28 Probability Space
هر فرضیه
دارای
Distribution
است.
نه
Score.
---
مثلاً
به جای
Bull Score = 84
داریم
Bull Probability Distribution
---
5.29 انواع Probability
سیستم
چندین احتمال
را همزمان
محاسبه می‌کند.
---
Trend Continuation Probability
---
Trend Failure Probability
---
Breakout Probability
---
Fake Breakout Probability
---
Liquidity Sweep Probability
---
Reversal Probability
---
Mean Reversion Probability
---
Expansion Probability
---
Compression Probability
---
Institutional Buying Probability
---
Institutional Selling Probability
---
Execution Success Probability
---
Trade Survival Probability
---
Profit Target Probability
---
Stop Loss Probability
---
5.30 Conditional Probability
هیچ Probability
مطلق نیست.
مثلاً
Reversal
↓
Given
Liquidity Sweep
یا
Breakout
↓
Given
High Volume
---
5.31 Joint Probability
گاهی
دو رویداد
همزمان
اهمیت دارند.
مثلاً
Liquidity Sweep
AND
Positive SMT
---
5.32 Bayesian Engine
تمام احتمال‌ها
دائماً
به‌روزرسانی
می‌شوند.
مثلاً
Prior
↓
New Evidence
↓
Posterior
---
این فرآیند
در تمام عمر
سیستم
ادامه دارد.
---
5.33 Sequential Evidence
Evidence
به ترتیب
وارد می‌شود.
بنابراین
Probability
نیز
به صورت
پیوسته
تغییر می‌کند.
---
5.34 Prior Generator
یکی از قسمت‌های بسیار مهم.
هر Probability
دارای
Prior
است.
اما
Prior
ثابت
نیست.
---
Prior
وابسته است به:
Regime
Session
Asset
Timeframe
Macro State
Liquidity State
Historical Statistics
---
5.35 Posterior Confidence
بعد از
Bayesian Update
دو خروجی
داریم.
---
Probability
---
Confidence
---
ممکن است
Probability
بالا باشد.
ولی
Confidence
پایین.
---
5.36 Predictive Distribution
سیستم
نباید
فقط
جهت
را
پیش‌بینی کند.
بلکه
کل توزیع
را.
مثلاً
Return Distribution
---
5.37 Expected Value Engine
برای هر معامله
امید ریاضی
محاسبه می‌شود.
EV
=
Σ
Probability
×
Outcome
---
اگر
EV
منفی باشد.
سیگنال
رد می‌شود.
---
5.38 Expected Holding Time
یکی از قسمت‌هایی که تقریباً در هیچ اندیکاتوری وجود ندارد.
سیستم
پیش‌بینی می‌کند.
اگر
معامله
باز شود.
احتمالاً
چقدر
طول می‌کشد.
---
5.39 Expected Drawdown
قبل از ورود
سیستم
حداکثر
Drawdown
محتمل
را
محاسبه می‌کند.
---
5.40 Expected Adverse Excursion (EAE)
برای هر سناریوی معامله، موتور احتمال باید بیشترین حرکت نامطلوب مورد انتظار را نیز تخمین بزند.
این مقدار ورودی مستقیم Risk Optimizer خواهد بود و برای تعیین Stop Loss تطبیقی استفاده می‌شود.
---
5.41 Expected Favorable Excursion (EFE)
در کنار EAE، بیشترین حرکت مطلوب مورد انتظار نیز برآورد می‌شود.
این مقدار در تعیین:
Take Profit
Trailing Stop
Partial Exit
استفاده خواهد شد.
---
5.42 Risk Distribution
ریسک
یک عدد
نیست.
بلکه
یک توزیع
است.
مثلاً
Low Risk
18%
Medium Risk
56%
High Risk
26%
---
5.43 Probability Calibration Engine
یکی از حیاتی‌ترین اجزای این موتور.
اگر سیستم بگوید:
Probability = 80%
باید در بلندمدت، حدود ۸۰٪ از این پیش‌بینی‌ها درست باشند.
برای این منظور، موتور باید دائماً کالیبره شود.
روش‌هایی مانند:
Reliability Diagram
Calibration Curve
Brier Score
Expected Calibration Error (ECE)
برای پایش کیفیت احتمال‌ها استفاده می‌شوند.
---
5.44 Probability Drift Detection
بازار تغییر می‌کند.
اگر کیفیت Probabilityها افت کند،
سیستم باید آن را تشخیص دهد.
نمونه Driftها:
Calibration Drift
Regime Drift
Distribution Shift
Outcome Shift
در صورت تشخیص Drift، Optimizerها از این موضوع مطلع می‌شوند.
---
5.45 Scenario Probability Matrix
به جای یک احتمال،
یک ماتریس احتمال ساخته می‌شود.
نمونه:
سناریو</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>احتمال</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>Confidence
ادامه روند</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.42</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.84
برگشت</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.27</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.71
رنج</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.19</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.66
فیک بریک‌اوت</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.12</w:r><w:r><w:rPr><w:rtl/><w:lang w:val="en-US"/></w:rPr><w:t>0.58
این ماتریس ورودی مستقیم موتور تصمیم‌گیری خواهد بود.
---
5.46 Entropy Engine
یکی از مهم‌ترین خروجی‌ها.
Entropy
نشان می‌دهد:
بازار
چقدر
قابل پیش‌بینی است.
---
Entropy
کم
↓
بازار
واضح
---
Entropy
زیاد
↓
بازار
مبهم
---
اگر
Entropy
خیلی زیاد باشد.
ممکن است
اصلاً
سیگنال
تولید نشود.
---
5.47 Decision Readiness Index (DRI)
پیشنهاد جدید برای معماری.
به جای اینکه تنها به Probability نگاه شود، یک شاخص آمادگی تصمیم ساخته می‌شود.
این شاخص از ترکیب موارد زیر تشکیل می‌شود:
Probability Calibration
Average Confidence
Entropy
Data Quality
Feature Quality
Market Stability
Risk Distribution
اگر DRI کمتر از آستانه باشد، کل زنجیره تولید سیگنال متوقف می‌شود.
---
5.48 Probability Explainability
برای هر Probability باید مشخص باشد:
مهم‌ترین Evidenceها
بیشترین عامل افزایش احتمال
بیشترین عامل کاهش احتمال
Prior مورد استفاده
Posterior نهایی
Confidence
Calibration Status
---
5.49 ارتباط با دو Optimizer
در این نقطه، دو Optimizer که قبلاً طراحی کرده‌ایم وارد معماری می‌شوند.
Signal Optimizer
ورودی‌های اصلی:
Market State Vector
Institutional State Vector
Scenario Probability Matrix
Probability Calibration
Expected Value
Entropy
DRI
خروجی:
بهترین پارامترهای تولید سیگنال برای رژیم فعلی بازار
وزن Featureها
آستانه‌های تطبیقی
تنظیمات اختصاصی هر تایم‌فریم و هر نماد
---
Risk & Money Management & Execution Optimizer
ورودی‌های اصلی:
Expected Drawdown
EAE
EFE
Risk Distribution
Trade Survival Probability
Expected Holding Time
Probability Calibration
Scenario Matrix
خروجی:
نوع ورود
نوع Exit
نوع Stop
اندازه موقعیت
Trailing Logic
Break-even Policy
Partial Exit Policy
Execution Mode
این طراحی باعث می‌شود دو Optimizer به جای استفاده از Ruleهای ثابت، روی یک فضای احتمالاتی کاملاً کالیبره‌شده تصمیم‌گیری کنند.
---
5.50 Output Contract
خروجی Probability Engine شامل موارد زیر است:
1. Scenario Probability Matrix
2. Posterior Belief State
3. Expected Value Metrics
4. Expected Drawdown / EAE / EFE
5. Risk Distribution
6. Trade Survival Probability
7. Expected Holding Time
8. Entropy Metrics
9. Decision Readiness Index
10. Probability Calibration Report
11. Probability Explainability Metadata
---
پایان بخش دوم فصل پنجم
از بخش بعدی وارد Signal Optimizer خواهیم شد؛ یکی از دو Optimizer اصلی معماری APEX. در آن بخش، به‌صورت کامل طراحی خواهیم کرد که چگونه سیستم بدون انجام جستجوی کور (Brute Force) روی میلیاردها ترکیب پارامتر، با استفاده از بهینه‌سازی سلسله‌مراتبی، چندهدفه، تطبیقی و Walk-Forward، بهترین مجموعه پارامترهای تولید سیگنال را برای هر نماد، هر تایم‌فریم و هر رژیم بازار پیدا کرده و به‌صورت خودکار در قلب سیستم اعمال می‌کند. این بخش یکی از پیچیده‌ترین و مهم‌ترین قسمت‌های کل معماری خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 6
Institutional Signal Optimizer
طراحی کامل موتور بهینه‌سازی تولید سیگنال
---
6.1 مقدمه
به این فصل که برسیم،
در واقع وارد ارزشمندترین قسمت کل پروژه می‌شویم.
تا اینجا سیستم موفق شده است:
داده‌های بازار را جمع‌آوری کند.
داده‌ها را پاکسازی کند.
هزاران Feature تولید کند.
Featureهای مناسب را انتخاب کند.
آنها را Fusion کند.
وضعیت بازار را درک کند.
فرضیه‌های بازار را بسازد.
احتمال وقوع هر سناریو را محاسبه کند.
اما هنوز هیچ سیگنالی تولید نشده است.
چرا؟
زیرا هنوز سیستم نمی‌داند
بهترین تنظیمات ممکن برای همین بازار چیست.
---
در اکثر اندیکاتورها
پارامترها ثابت هستند.
مثلاً
EMA = 20
ATR = 14
RSI = 14
Swing = 10
FVG Threshold = 0.3
اما بازار
هیچ‌وقت
ثابت نیست.
بنابراین
پارامتر ثابت
تقریباً همیشه
پارامتر اشتباه است.
---
6.2 هدف Signal Optimizer
هدف این موتور
پیدا کردن بهترین پارامترها نیست.
بلکه
پیدا کردن بهترین پارامترها
برای همین وضعیت فعلی بازار
است.
---
به عبارت دیگر
پارامترها
State Dependent
هستند.
نه
Global.
---
6.3 تفاوت با Grid Search
ایده اولیه‌ای که قبلاً مطرح کرده بودیم این بود:
تمام پارامترها
تمام بازه‌ها
تمام Stepها
تمام جایگشت‌ها
اجرا شوند.
اما
اگر این کار انجام شود
فضای جستجو
به سرعت
از
۱۰^۲۰
حالت
بیشتر خواهد شد.
این کار
حتی روی Cluster
نیز
غیرعملی است.
بنابراین معماری باید تغییر کند.
---
6.4 فلسفه جدید Optimizer
Optimizer
نباید
پارامتر
را جستجو کند.
بلکه باید
یاد بگیرد
کجا را
جستجو کند.
---
به عبارت دیگر
Optimization
خودش
دارای
Optimization
خواهد بود.
---
6.5 ساختار کلی
Signal Optimizer
از ده موتور مستقل تشکیل می‌شود.
Search Space Builder
↓
Constraint Engine
↓
Parameter Graph
↓
Candidate Generator
↓
Hierarchical Optimizer
↓
Multi Objective Optimizer
↓
Walk Forward Engine
↓
Robustness Validator
↓
Generalization Engine
↓
Parameter Deployment Engine
---
6.6 Parameter Registry
اولین قسمت.
تمام پارامترهای قابل تنظیم
باید
ثبت شوند.
نه فقط
اندیکاتورها.
بلکه
همه چیز.
---
مثلاً
EMA Length
ATR Length
ATR Multiplier
FVG Threshold
OB Strength
Liquidity Threshold
SMT Distance
Swing Length
Volume Multiplier
Regression Length
VWAP Bands
Session Filters
CHOCH Distance
BOS Threshold
Scoring Weight
Probability Threshold
Risk Threshold
Confidence Threshold
Entropy Threshold
Execution Delay
Signal Cooldown
News Filter
Spread Filter
Volatility Filter
...
---
هیچ پارامتری
نباید
خارج از Registry
وجود داشته باشد.
---
6.7 Parameter Metadata
هر پارامتر
دارای
Metadata
است.
Name
Description
Category
Type
Integer
Float
Boolean
Categorical
Current Value
Default Value
Minimum
Maximum
Suggested Range
Safe Range
Optimization Range
Optimization Step
Importance
Sensitivity
Dependencies
Timeframe Dependency
Asset Dependency
Market Dependency
Version
---
6.8 Parameter Graph
پارامترها
مستقل نیستند.
مثلاً
ATR Length
↓
ATR Stop
↓
Position Size
---
یا
Swing Length
↓
CHOCH
↓
BOS
↓
Structure Score
---
بنابراین
Optimizer
Graph
را
می‌سازد.
---
6.9 Dependency Engine
قبل از تغییر
هر پارامتر
باید بررسی شود.
تغییر آن
چه پارامترهای دیگری
را
تحت تاثیر قرار می‌دهد.
---
6.10 Parameter Constraints
هر پارامتر
دارای
Constraint
است.
مثلاً
ATR Multiplier
>
0
یا
Fast EMA
<
Slow EMA
---
یا
TP
>
SL
---
Constraintها
باید
قبل از
Optimization
اعمال شوند.
---
6.11 Search Space Builder
مهم‌ترین قسمت.
فضای جستجو
به صورت هوشمند
ساخته می‌شود.
---
مثلاً
به جای
ATR
1
↓
100
---
سیستم
ابتدا
بازه منطقی
را پیدا می‌کند.
مثلاً
ATR
7
↓
25
---
سپس
داخل همان
جستجو
می‌کند.
---
6.12 Adaptive Search Space
بازه
وابسته به
Asset
است.
---
وابسته به
Timeframe
است.
---
وابسته به
Volatility
است.
---
وابسته به
Regime
است.
---
بنابراین
فضای جستجو
ثابت
نیست.
---
6.13 Search Space Shrinking
بعد از هر مرحله
فضای جستجو
کوچک‌تر
می‌شود.
مثلاً
5
↓
40
↓
10
↓
20
↓
12
↓
17
↓
13
↓
15
---
6.14 Coarse-to-Fine Optimization
جستجو
در چند سطح انجام می‌شود.
مرحله اول
گام‌های بزرگ.
---
مرحله دوم
گام‌های متوسط.
---
مرحله سوم
گام‌های بسیار کوچک.
---
این روش، هزینه محاسباتی را به‌شدت کاهش می‌دهد و از تمرکز زودهنگام روی یک ناحیه ضعیف جلوگیری می‌کند.
---
6.15 Candidate Generator
به جای تولید تمام حالت‌ها،
سیستم مجموعه‌ای از Candidateهای امیدبخش می‌سازد.
منابع تولید Candidate عبارت‌اند از:
بهترین پارامترهای گذشته در همان Regime
همسایگی بهترین جواب‌های اخیر
مقادیر پیشنهادی بر اساس Market State
نمونه‌های تصادفی کنترل‌شده برای حفظ تنوع
پارامترهای موفق روی دارایی‌های مشابه (در صورت وجود معیار شباهت)
---
6.16 Multi-Objective Optimization
برخلاف بهینه‌سازی تک‌هدفه، هیچ پارامتری صرفاً برای بیشینه کردن سود انتخاب نمی‌شود.
تابع هدف از چندین مؤلفه تشکیل می‌شود.
نمونه:
Maximize:
Net Profit
Sharpe Ratio
Sortino Ratio
Profit Factor
Expectancy
Win Rate
Recovery Factor
Minimize:
Max Drawdown
Ulcer Index
Exposure
Parameter Instability
Overfitting Score
Latency
به جای یک جواب، مجموعه‌ای از جواب‌های پارتو (Pareto Front) تولید می‌شود.
---
6.17 Regime-Specific Parameter Sets
یکی از تغییرات مهم نسبت به ایده اولیه.
سیستم فقط یک مجموعه پارامتر ندارد.
بلکه برای هر Regime یک پروفایل مستقل ایجاد می‌کند.
نمونه:
Trend Regime
→ Parameter Set A
Range Regime
→ Parameter Set B
High Volatility
→ Parameter Set C
Low Liquidity
→ Parameter Set D
در زمان اجرا، با تغییر Regime، پروفایل مناسب فعال می‌شود.
---
6.18 Walk-Forward Optimization
هیچ پارامتری بدون آزمون Walk-Forward پذیرفته نمی‌شود.
چرخه استاندارد:
Train Window
↓
Optimize
↓
Validate
↓
Roll Forward
↓
Repeat
اگر پارامتر فقط روی داده آموزش خوب باشد ولی روی پنجره اعتبارسنجی ضعیف عمل کند، رد خواهد شد.
---
6.19 Stability Score
برای هر مجموعه پارامتر، علاوه بر سود، میزان پایداری نیز محاسبه می‌شود.
پارامتری که فقط در یک بازه کوتاه عالی باشد اما در سایر بازه‌ها فرو بریزد، امتیاز Stability پایینی دریافت می‌کند و انتخاب نمی‌شود.
---
6.20 Overfitting Detector
این موتور به‌طور اختصاصی برای تشخیص بیش‌برازش طراحی می‌شود.
شاخص‌هایی مانند:
اختلاف عملکرد Train و Validation
حساسیت شدید به تغییرات کوچک پارامتر
کاهش ناگهانی عملکرد در Regimeهای جدید
پیچیدگی بیش از حد مدل
برای تولید یک Overfitting Score استفاده می‌شوند.
این امتیاز مستقیماً در تابع هدف وارد می‌شود.
---
پایان بخش اول فصل ششم
در بخش بعدی، وارد طراحی Hierarchical Optimizer، Evolution Engine، Surrogate Models، Bayesian Optimization، Reinforcement-Based Parameter Adaptation، Parameter Memory، Deployment Engine و حلقه بازخورد با Probability Engine و Risk & Execution Optimizer خواهیم شد. این بخش، معماری Optimizer را از یک موتور جستجوی پارامتر به یک سامانه تطبیقی و خودبهینه‌شونده در سطح سازمانی (Institutional Grade) تبدیل می‌کند.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 6 (ادامه)
بخش دوم
Institutional Signal Optimizer
Adaptive Hierarchical Optimization Framework
---
6.21 مقدمه
در بخش قبل،
پارامترها را تعریف کردیم.
اما هنوز مهم‌ترین سؤال باقی مانده است.
چگونه باید آنها را Optimize کنیم؟
تقریباً تمام Optimizerهای موجود از یکی از این روش‌ها استفاده می‌کنند.
Grid Search
Random Search
Bayesian Optimization
Genetic Algorithm
Particle Swarm
Differential Evolution
CMA-ES
Hyperopt
Optuna
مشکل چیست؟
هیچ‌کدام به تنهایی مناسب بازار نیستند.
چرا؟
زیرا بازار
دارای ویژگی‌های زیر است.
Non-Stationary
Regime Switching
Heavy Tail
High Noise
Time Dependency
Concept Drift
Adaptive Behaviour
Reflexivity
در نتیجه
به جای انتخاب یک Optimizer،
خود Optimizer باید تطبیقی باشد.
---
6.22 Meta Optimizer
اولین بخش جدید.
Optimizer
خودش
دارای Optimizer
خواهد بود.
Optimization Engine
↓
Meta Optimizer
↓
Select Best Optimizer
یعنی سیستم ابتدا تشخیص می‌دهد:
برای وضعیت فعلی
کدام الگوریتم
بهینه‌تر است.
مثلاً
Small Search Space
↓
Bayesian
--------------
Huge Space
↓
Evolutionary
--------------
Very Stable Space
↓
Local Search
--------------
High Drift
↓
Randomized Adaptive Search
---
6.23 Hierarchical Optimization
به جای اینکه
هزار پارامتر
همزمان Optimize شوند.
Optimization
به صورت سلسله مراتبی انجام می‌شود.
---
Layer 1
Structural Parameters
↓
Swing
↓
CHOCH
↓
BOS
↓
Trend
---
Layer 2
Liquidity
↓
OB
↓
FVG
↓
SMT
↓
Sweep
---
Layer 3
Probability
↓
Threshold
↓
Weight
↓
Confidence
↓
Entropy
---
Layer 4
Signal Logic
↓
Score
↓
Voting
↓
Decision Threshold
---
Layer 5
Execution
↓
Risk
↓
Money Management
---
به این ترتیب
فضای جستجو
چندین مرتبه کوچک‌تر می‌شود.
---
6.24 Optimization Dependency Graph
تمام پارامترها
داخل یک DAG
قرار می‌گیرند.
مثلاً
Swing Length
↓
Swing Detection
↓
CHOCH
↓
BOS
↓
Trend
↓
Signal Score
↓
Trade
اگر
Swing
عوض شود.
نیازی نیست
Execution
دوباره
از ابتدا Optimize شود.
---
6.25 Sensitivity Analysis Engine
قبل از شروع Optimization
سیستم
برای هر پارامتر
Sensitivity
را محاسبه می‌کند.
مثلاً
ATR Length
Very Sensitive
------------
EMA Source
Low Sensitive
------------
VWAP Session
Medium
پارامترهایی که حساسیت بسیار کمی دارند
در هر چرخه دوباره Optimize نمی‌شوند.
---
6.26 Parameter Interaction Matrix
بزرگ‌ترین اشتباه
Optimize کردن
پارامترها
به صورت مستقل است.
در واقع
پارامترها
روی یکدیگر اثر دارند.
مثلاً
ATR Length
×
ATR Multiplier
↓
Stop Distance
یا
Swing Length
×
FVG Threshold
↓
Liquidity Score
بنابراین
سیستم
Interaction Matrix
را ایجاد می‌کند.
---
6.27 Adaptive Step Engine
در Grid Search
Step
ثابت است.
اینجا
Step
وابسته به
Gradient
خواهد بود.
مثلاً
Flat Region
↓
Large Step
----------------
Steep Region
↓
Tiny Step
---
6.28 Bayesian Optimization Layer
در فضاهای پیوسته
سیستم
Bayesian Optimization
را فعال می‌کند.
اما نه برای همه پارامترها.
فقط
پارامترهایی که
دارای Cost
بالا هستند.
---
6.29 Evolution Engine
برای پارامترهایی که
وابستگی شدید دارند.
Evolution
بهتر عمل می‌کند.
هر Individual
یک Parameter Set
است.
Fitness
بر اساس
توابع هدف
محاسبه می‌شود.
---
اما
Mutation
کاملاً تصادفی نیست.
---
6.30 Intelligent Mutation
Mutation
وابسته به
Sensitivity
خواهد بود.
مثلاً
پارامتری که
حساسیت زیادی دارد.
با
Mutation کوچک
تغییر می‌کند.
پارامتر کم‌اهمیت
با
Mutation بزرگ.
---
6.31 Surrogate Model Engine
یکی از بزرگ‌ترین نوآوری‌های معماری.
قرار نیست
تمام ترکیب‌ها
اجرا شوند.
بلکه
بعد از اجرای بخشی از آنها
یک مدل جانشین
(Surrogate)
ساخته می‌شود.
این مدل
پیش‌بینی می‌کند.
اگر
پارامترها
به این شکل باشند.
احتمالاً
Fitness
چقدر خواهد شد.
در نتیجه
میلیون‌ها اجرای غیرضروری
حذف می‌شوند.
---
6.32 Early Rejection Engine
اگر
در میانه Optimization
مشخص شود
یک Candidate
هیچ شانسی ندارد.
فوراً
متوقف می‌شود.
---
مثلاً
بعد از
۳۰٪
Backtest
اگر
Max Drawdown
از حد مجاز
عبور کرد.
اجرای همان Candidate
قطع می‌شود.
---
6.33 Multi-Fidelity Optimization
همه Candidateها
لازم نیست
روی کل تاریخ
تست شوند.
ابتدا
روی
داده کمتر
تست می‌شوند.
اگر
امیدبخش بودند.
به مرحله بعد
می‌روند.
Quick Test
↓
Medium Test
↓
Full Walk Forward
↓
Stress Test
↓
Production Candidate
---
6.34 Regime Cluster Optimization
به جای یک بهینه‌سازی برای کل تاریخ،
ابتدا تاریخ بازار به خوشه‌های رفتاری تقسیم می‌شود.
نمونه:
Bull Trend
Bear Trend
High Volatility
Low Volatility
Compression
Expansion
News
Weekend
Low Liquidity
سپس برای هر خوشه،
بهینه‌سازی مستقل انجام می‌شود.
---
6.35 Parameter Memory
یکی از بخش‌هایی که در معماری اولیه وجود نداشت.
هر نتیجه Optimization
داخل حافظه ذخیره می‌شود.
مثلاً
BTC
15m
Trend
↓
Parameter Set #184
Sharpe=2.31
PF=2.82
دفعه بعد
نیازی نیست
از صفر
شروع شود.
---
6.36 Transfer Optimization
اگر
پارامترها
برای
BTC
بهینه شدند.
ممکن است
برای
ETH
نیز
نقطه شروع خوبی باشند.
سیستم
از شباهت دارایی‌ها
استفاده می‌کند.
---
6.37 Forgetting Engine
پارامترهای قدیمی
همیشه
معتبر نیستند.
اگر
بازار
Drift
کند.
Parameter Memory
باید
آنها را
کم‌کم
فراموش کند.
---
6.38 Optimizer Confidence
خود Optimizer
نیز
Confidence
دارد.
ممکن است
بهترین پارامتر پیدا شده
خیلی مطمئن
نباشد.
---
این Confidence
به
Decision Engine
ارسال می‌شود.
---
6.39 Optimizer Explainability
برای هر پارامتر انتخاب‌شده باید ثبت شود:
چرا این مقدار انتخاب شد؟
چه Candidateهایی رد شدند؟
کدام تابع هدف بیشترین اثر را داشت؟
حساسیت این پارامتر چقدر است؟
این مقدار در چند Regime پایدار بوده است؟
آخرین زمان اعتبارسنجی آن چه بوده است؟
---
6.40 خروجی Optimizer
Signal Optimizer فقط یک مجموعه پارامتر تولید نمی‌کند.
بلکه خروجی آن شامل موارد زیر است:
Active Parameter Profile
Candidate Ranking
Pareto Frontier
Parameter Stability Report
Optimization Confidence
Regime-specific Parameter Sets
Walk-Forward Validation Report
Overfitting Score
Sensitivity Matrix
Parameter Interaction Matrix
Surrogate Model Snapshot
Optimization Audit Log
---
نکته مهم معماری (ارتقاء نسبت به طرح اولیه)
در نسخه اولیه‌ای که با هم طراحی کردیم، Signal Optimizer تنها مسئول یافتن بهترین پارامترها بود.
در نسخه نهایی APEX، پیشنهاد می‌کنم نقش آن بسیار گسترده‌تر شود و به یک Hyperparameter Intelligence System تبدیل گردد؛ یعنی علاوه بر بهینه‌سازی پارامترها، به‌طور مداوم کیفیت خود فرآیند بهینه‌سازی را نیز ارزیابی کند، Drift پارامترها را تشخیص دهد، عمر مفید هر Parameter Profile را مدیریت کند و در صورت افت عملکرد، قبل از ورود سیستم به فاز زیان‌ده، به‌صورت خودکار فرآیند Re-optimization را آغاز نماید.
این تغییر، Signal Optimizer را از یک ابزار بهینه‌سازی ساده به یک سامانه تصمیم‌یار تطبیقی در سطح مؤسسات مالی تبدیل می‌کند.
---
پایان بخش دوم فصل ششم
در بخش بعدی وارد Online Learning، Continual Optimization، Self-Evaluation، Auto Re-Optimization، Regime Transition Handler، و اتصال کامل Signal Optimizer با Risk & Money Management & Execution Optimizer خواهیم شد؛ جایی که معماری وارد فاز «خودتکامل‌یابنده (Self-Evolving Trading System)» می‌شود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 6 (ادامه)
بخش سوم
Online Adaptive Optimization Framework
Self-Evolving Signal Optimizer
---
6.41 مقدمه
تا اینجا
Signal Optimizer
موفق شده است
بهترین پارامترها را پیدا کند.
اما یک سؤال اساسی باقی مانده است.
اگر بازار
فردا
کاملاً تغییر کند
چه اتفاقی می‌افتد؟
تقریباً تمام سیستم‌های موجود دنیا
در همین نقطه شکست می‌خورند.
آنها تصور می‌کنند
یک بار
Optimization
برای همیشه
کافی است.
در حالی که
بازار
هر روز
در حال تغییر است.
در واقع
پارامتر
نیز
دارای عمر مفید است.
---
6.42 Parameter Lifecycle
هر Parameter Set
دارای چرخه عمر است.
Candidate
↓
Validated
↓
Production
↓
Monitoring
↓
Warning
↓
Reoptimization
↓
Retirement
↓
Archive
بنابراین
هیچ Parameter Set
دائمی نیست.
---
6.43 Parameter Aging
پارامترها
پیر می‌شوند.
مثلاً
پارامتری که
شش ماه
بدون بررسی
فعال مانده
نباید
مورد اعتماد باشد.
سیستم
برای هر Parameter Set
سن محاسبه می‌کند.
---
Age
↓
Fresh
↓
Mature
↓
Old
↓
Expired
---
6.44 Performance Monitor
بعد از هر معامله
Optimizer
خودش
را ارزیابی می‌کند.
موارد زیر
ثبت می‌شوند.
Expected Win Rate
↓
Real Win Rate
---------------
Expected Sharpe
↓
Real Sharpe
---------------
Expected Drawdown
↓
Observed Drawdown
---------------
Expected Profit
↓
Observed Profit
---
6.45 Prediction Error Engine
برای هر پارامتر
خطای پیش‌بینی
محاسبه می‌شود.
Prediction
↓
Reality
↓
Error
این Error
یکی از مهم‌ترین
ورودی‌های
Reoptimization
است.
---
6.46 Calibration Drift
اگر
احتمالات
قبلاً
خوب
کالیبره بودند
اما
دیگر
نیستند.
پارامترها
باید
بازنگری شوند.
---
6.47 Regime Transition Detector
یکی از حیاتی‌ترین بخش‌ها.
بازار
به آرامی
تغییر
نمی‌کند.
بلکه
گاهی
Jump
می‌کند.
مثلاً
Trend
↓
Crash
↓
Recovery
↓
Range
↓
Expansion
سیستم
باید
Transition
را
تشخیص دهد.
---
6.48 Regime Change Policy
با تغییر Regime
سه حالت وجود دارد.
---
Mode A
Reuse Parameters
---
Mode B
Warm Start Optimization
---
Mode C
Full Reoptimization
---
سیستم
خودش
تصمیم می‌گیرد.
---
6.49 Online Learning
اینجا
یکی از تفاوت‌های اصلی
Python
با Pine Script
مشخص می‌شود.
در Pine
تقریباً
Online Learning
غیرممکن است.
اما در Python
کاملاً
امکان‌پذیر است.
---
سیستم
بعد از هر معامله
دانش خود را
به‌روز می‌کند.
نه اینکه
منتظر
Optimization
بعدی بماند.
---
6.50 Continual Learning Buffer
تمام معاملات
داخل یک Buffer
ذخیره می‌شوند.
اما
همه
وزن یکسان
ندارند.
---
معاملات جدید
وزن بیشتری دارند.
---
معاملات قدیمی
کم‌کم
فراموش می‌شوند.
---
6.51 Experience Replay
یکی از بهترین روش‌ها.
گاهی
سیستم
معاملات گذشته
را
دوباره
بررسی می‌کند.
تا
Optimization
پایدارتر شود.
---
6.52 Confidence Decay
اگر
پارامتر
مدت زیادی
استفاده نشده باشد.
Confidence
آن
کم می‌شود.
---
6.53 Parameter Health
هر Parameter Set
دارای Health
است.
Healthy
------------
Warning
------------
Critical
------------
Disabled
---
6.54 Auto Disable
اگر
Parameter
چندین بار
شکست بخورد.
خودکار
غیرفعال
می‌شود.
---
6.55 Auto Recovery
اگر
بازار
دوباره
به همان Regime
برگردد.
Parameter
دوباره
فعال
می‌شود.
---
6.56 Drift Attribution Engine
یکی از نوآوری‌های مهم.
اگر عملکرد افت کند
باید مشخص شود.
علت چیست؟
ممکن است
پارامتر
مشکل نداشته باشد.
بلکه
Feature
خراب شده باشد.
یا
Probability
Drift
کرده باشد.
یا
Risk Engine
اشتباه کند.
بنابراین
Optimizer
نباید
بی‌دلیل
پارامترها
را
تغییر دهد.
---
6.57 Root Cause Analyzer
برای هر افت عملکرد
تحلیل علت ریشه‌ای انجام می‌شود.
نمونه خروجی
Performance Drop
↓
Feature Drift
63%
------------
Regime Change
21%
------------
Execution Slippage
9%
------------
Data Quality
7%
---
6.58 Meta Feedback Loop
تمام بخش‌های معماری
به Optimizer
بازخورد می‌دهند.
Probability Engine
↓
Signal Optimizer
↓
Risk Optimizer
↓
Execution Engine
↓
Trade Result
↓
Optimizer
این حلقه
هرگز
قطع
نمی‌شود.
---
6.59 Self Evaluation Engine
Optimizer
باید
خودش
را
امتیازدهی کند.
نمونه
Optimization Quality
93
--------------
Generalization
91
--------------
Calibration
95
--------------
Robustness
90
--------------
Explainability
97
---
6.60 Optimization Budget Manager
بهینه‌سازی
منابع سیستم
را مصرف می‌کند.
بنابراین
بودجه دارد.
مثلاً
CPU Budget
GPU Budget
RAM Budget
Battery Budget
Storage Budget
Network Budget
نکته مهم برای اجرای روی Termux و گوشی:
از آنجا که هدف این پروژه اجرای دائمی روی تلفن همراه است، Budget Manager باید یک مؤلفه مستقل باشد و وضعیت دستگاه را نیز پایش کند:
درصد باتری
دمای CPU
میزان استفاده از RAM
فضای آزاد ذخیره‌سازی
سرعت و پایداری اینترنت
وضعیت شارژ (Charging / Battery)
در صورت افزایش دما یا کاهش باتری، Optimizer می‌تواند از Full Optimization به Warm Optimization یا حتی Pause تغییر وضعیت دهد تا پایداری سیستم حفظ شود.
---
6.61 Adaptive Scheduling
تمام عملیات بهینه‌سازی لازم نیست بلافاصله اجرا شوند.
Scheduler باید تصمیم بگیرد:
چه چیزی اکنون اجرا شود؟
چه چیزی به تعویق بیفتد؟
چه چیزی لغو شود؟
این Scheduler بر اساس:
اهمیت
فوریت
هزینه محاسباتی
وضعیت دستگاه
وضعیت بازار
تصمیم می‌گیرد.
---
6.62 Live Parameter Deployment
یکی از حساس‌ترین مراحل.
پارامتر جدید
نباید
مستقیماً
جایگزین
پارامتر فعلی شود.
ابتدا
در Shadow Mode
فعال می‌شود.
Current Profile
↓
Shadow Profile
↓
Parallel Evaluation
↓
Promotion
↓
Production
اگر عملکرد Shadow Profile بهتر بود، سپس به Production منتقل می‌شود.
---
6.63 Safe Rollback
اگر پس از استقرار Parameter Set جدید، عملکرد افت کند، سیستم باید بتواند در چند میلی‌ثانیه به آخرین نسخه پایدار بازگردد.
هر Deployment دارای:
Version ID
Timestamp
Validation Report
Rollback Pointer
خواهد بود.
---
6.64 Continuous Walk-Forward
Walk-Forward فقط هنگام طراحی انجام نمی‌شود.
بلکه به‌صورت دائمی ادامه دارد.
به این ترتیب، سیستم همیشه در حال اعتبارسنجی پارامترهای فعال روی داده‌های جدید است.
---
6.65 Shadow Optimization
همزمان با اجرای سیستم، یک Optimizer ثانویه در پس‌زمینه روی داده‌های جدید کار می‌کند.
این Optimizer بدون دخالت در معاملات واقعی، Candidateهای جدید تولید می‌کند.
تنها در صورت اثبات برتری، نتایج آن وارد فرآیند Deployment می‌شوند.
---
6.66 Architecture Upgrade (پیشنهاد جدید)
در اینجا یک پیشنهاد مهم نسبت به طراحی اولیه اضافه می‌شود.
به جای یک Signal Optimizer، سه سطح Optimizer خواهیم داشت:
Level 1 — Fast Optimizer
بسیار سریع
تغییرات کوچک
مناسب اجرای لحظه‌ای
اصلاح آستانه‌ها و وزن‌ها
---
Level 2 — Strategic Optimizer
اجرای دوره‌ای
بهینه‌سازی پارامترهای ساختاری
Walk-Forward
تحلیل پایداری
---
Level 3 — Research Optimizer
اجرای آفلاین
استفاده از تاریخچه کامل
طراحی Candidateهای جدید
آزمایش معماری‌های نو
تولید نسل بعدی Parameter Profileها
این تفکیک باعث می‌شود سیستم روی گوشی نیز قابل اجرا باقی بماند و بخش‌های سنگین فقط هنگام نیاز یا روی سخت‌افزار قوی‌تر اجرا شوند.
---
6.67 خروجی نهایی Signal Optimizer
خروجی این ماژول صرفاً یک فایل تنظیمات نیست، بلکه یک بسته کامل شامل موارد زیر است:
Active Parameter Profile
Regime-specific Profiles
Deployment Manifest
Optimization Confidence
Stability Metrics
Drift Status
Parameter Health
Rollback Package
Audit Trail
Reoptimization Policy
Scheduling Policy
Shadow Evaluation Report
---
پایان فصل ششم
در فصل هفتم وارد دومین Optimizer اصلی معماری خواهیم شد:
Institutional Risk, Money Management & Execution Optimizer
این فصل از نظر پیچیدگی حتی از Signal Optimizer نیز گسترده‌تر خواهد بود، زیرا در آن هر سیگنال به‌صورت مستقل و بر اساس احتمال‌ها، توزیع ریسک، شرایط بازار، کیفیت اجرای سفارش و اهداف پرتفوی، به یک برنامه اجرایی کامل تبدیل می‌شود؛ نه صرفاً یک Stop Loss و Take Profit ثابت. این بخش هسته اصلی مدیریت سرمایه و اجرای معاملات در معماری APEX خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 7
Institutional Risk, Money Management & Execution Optimizer
طراحی کامل موتور مدیریت ریسک، سرمایه و اجرای معاملات
---
7.1 مقدمه
به این نقطه که می‌رسیم،
دیگر مسئله اصلی تولید سیگنال نیست.
در واقع، تجربه بازارهای مالی نشان می‌دهد که دو سیستم می‌توانند سیگنال‌های تقریباً یکسانی تولید کنند، اما به دلیل تفاوت در مدیریت ریسک و اجرا، یکی در بلندمدت سودآور و دیگری زیان‌ده باشد.
در معماری APEX، سیگنال تنها یک پیشنهاد (Trade Intent) است، نه دستور قطعی ورود.
این فصل وظیفه دارد آن پیشنهاد را به یک Execution Plan کامل تبدیل کند.
---
7.2 فلسفه طراحی
در اکثر اندیکاتورها:
BUY
↓
SL = ATR × 2
TP = ATR × 4
↓
Done
این روش برای یک معماری Institutional قابل قبول نیست.
در APEX، هر معامله باید مانند یک پروژه مستقل طراحی شود.
برای هر سیگنال باید پاسخ داده شود:
آیا اصلاً باید وارد شویم؟
اگر بله، با چه حجمی؟
با چه نوع سفارشی؟
در چند مرحله؟
با چه حد ضرری؟
با چه حد سودی؟
تحت چه شرایطی معامله لغو شود؟
تحت چه شرایطی معامله توسعه یابد؟
تحت چه شرایطی زودتر بسته شود؟
---
7.3 Trade Blueprint
قبل از ارسال هر سفارش، یک سند داخلی به نام Trade Blueprint ساخته می‌شود.
نمونه ساختار:
Trade ID
Signal ID
Asset
Timeframe
Direction
Probability
Confidence
Expected Value
Expected Holding Time
Expected Drawdown
Expected Favorable Excursion
Risk Class
Execution Mode
Entry Plan
Exit Plan
Monitoring Rules
Emergency Rules
Expiration Policy
تمام موتورهای بعدی فقط روی این Blueprint کار خواهند کرد.
---
7.4 ورودی‌های Optimizer
ورودی‌های اصلی عبارت‌اند از:
Scenario Probability Matrix
Market State Vector
Institutional State Vector
Signal Confidence
Entropy
Expected Value
EAE
EFE
Trade Survival Probability
Volatility State
Liquidity State
Spread
Funding
Order Book Metrics
Portfolio State
Exposure State
Optimizer Confidence
---
7.5 اهداف Optimizer
بر خلاف Signal Optimizer که هدفش یافتن بهترین پارامترهای تولید سیگنال بود، این موتور چند هدف همزمان دارد.
حداکثرسازی:
Expected Utility
Risk Adjusted Return
Capital Efficiency
Portfolio Stability
حداقل‌سازی:
Max Drawdown
Tail Risk
Slippage
Execution Cost
Concentration Risk
Correlation Risk
---
7.6 Multi-Objective Risk Optimization
تابع هدف این موتور فقط Net Profit نیست.
نمونه:
Maximize
Sharpe
Sortino
Calmar
Omega
Recovery Factor
Expectancy
Utility
Capital Efficiency
-------------------
Minimize
Max DD
CVaR
Tail Loss
Execution Cost
Slippage
Latency
Exposure
Correlation
---
7.7 Dynamic Risk Budget
هر معامله
بودجه ریسک
مخصوص خودش
را دارد.
این بودجه از روی:
کیفیت سیگنال
کیفیت بازار
کیفیت اجرا
وضعیت پرتفوی
سود و زیان اخیر
وضعیت Optimizer
محاسبه می‌شود.
---
7.8 Portfolio Risk Engine
یکی از تفاوت‌های اساسی با اکثر ربات‌های معاملاتی.
سیستم هیچ معامله‌ای را مستقل بررسی نمی‌کند.
بلکه ابتدا وضعیت کل پرتفوی را تحلیل می‌کند.
نمونه متغیرها:
Total Exposure
Sector Exposure
Symbol Exposure
Directional Exposure
Leverage
Free Margin
Correlation Matrix
Beta Exposure
---
7.9 Correlation Manager
اگر همزمان:
BTC
ETH
SOL
همگی
سیگنال خرید داشته باشند،
سیستم نباید هر سه را با ریسک کامل باز کند.
ابتدا همبستگی دارایی‌ها محاسبه می‌شود.
سپس بودجه ریسک بین آنها تقسیم می‌شود.
---
7.10 Adaptive Position Sizing
اندازه موقعیت ثابت نیست.
ورودی‌های آن:
Signal Probability
Confidence
Expected Value
Volatility
Drawdown
Portfolio Risk
Trade Correlation
Entropy
Optimizer Confidence
خروجی:
Position Size
---
7.11 Fractional Position Model
به جای یک ورود کامل،
سیستم می‌تواند موقعیت را به چند بخش تقسیم کند.
نمونه:
20%
↓
30%
↓
50%
ورود هر بخش مشروط به تحقق شرایط جدید است.
---
7.12 Entry Optimizer
نوع ورود نیز بهینه می‌شود.
حالت‌های ممکن:
Market
Limit
Stop
Stop Limit
Passive Limit
Iceberg (در صورت پشتیبانی صرافی)
TWAP Slice
VWAP Slice
انتخاب این حالت وابسته به نقدشوندگی، اسپرد، نوسان و احتمال لغزش قیمت است.
---
7.13 Execution Cost Model
قبل از ارسال سفارش، هزینه اجرای معامله تخمین زده می‌شود.
این مدل شامل:
Maker Fee
Taker Fee
Funding
Spread
Slippage
Latency Cost
است.
اگر هزینه اجرا از Expected Edge بیشتر باشد، معامله رد می‌شود.
---
7.14 Stop Loss Optimizer
برخلاف سیستم‌های رایج، Stop Loss فقط از ATR محاسبه نمی‌شود.
بلکه مجموعه‌ای از Candidateها تولید می‌شود:
Structural Stop
ATR Stop
Volatility Stop
Liquidity Stop
Order Block Stop
Swing Stop
Time Stop
سپس بهترین گزینه با توجه به تابع هدف انتخاب می‌شود.
---
7.15 Hybrid Stop Model
در بسیاری از مواقع، بهترین Stop ترکیبی است.
نمونه:
Max(
ATR Stop,
Structure Stop,
Liquidity Stop
)
یا
Weighted Combination
که وزن‌ها توسط همین Optimizer تعیین می‌شوند.
---
7.16 Adaptive Take Profit
Take Profit نیز ثابت نیست.
کاندیداهای مختلف:
Fixed RR
Structure Target
Liquidity Target
VWAP Target
Regression Target
Probability Target
Volatility Target
سپس بر اساس احتمال رسیدن، بهترین هدف انتخاب می‌شود.
---
7.17 Dynamic RR Optimization
نسبت Risk/Reward از قبل تعیین نمی‌شود.
بلکه برای هر معامله به‌صورت پویا محاسبه می‌شود.
ممکن است بهترین تصمیم:
RR = 1.2
یا
RR = 5.8
باشد.
---
7.18 Time Stop Engine
گاهی بهترین تصمیم خروج، نه برخورد به SL یا TP، بلکه پایان زمان مورد انتظار معامله است.
اگر Expected Holding Time به پایان برسد و معامله هنوز بدون پیشرفت معنادار باشد، سیستم می‌تواند آن را ببندد یا مجدداً ارزیابی کند.
---
7.19 Trade Quality Index (TQI)
پیشنهاد جدید برای معماری.
برای هر معامله یک شاخص کیفیت ساخته می‌شود که از ترکیب موارد زیر تشکیل می‌شود:
Probability
Confidence
EV
Entropy
Execution Cost
Portfolio Risk
Liquidity Quality
Regime Compatibility
TQI مبنای اصلی تعیین اندازه موقعیت و نوع اجرای سفارش خواهد بود.
---
7.20 خروجی مرحله اول
در پایان این بخش، برای هر سیگنال یک Trade Blueprint کامل تولید شده است که شامل:
اندازه موقعیت
نوع سفارش
Stop Candidate
Target Candidate
بودجه ریسک
کیفیت معامله
هزینه اجرا
زمان انقضا
است.
---
نکته مهم معماری
در طراحی اولیه‌ای که قبلاً با هم انجام داده بودیم، Risk Optimizer بیشتر روی یافتن بهترین مقادیر Stop، Take Profit و Position Size تمرکز داشت.
در نسخه نهایی APEX، پیشنهاد می‌کنم این موتور به یک Trade Construction Engine تبدیل شود؛ یعنی به جای «تنظیم چند پارامتر»، مسئول طراحی کامل چرخه عمر هر معامله باشد. در این معماری، هر معامله از لحظه ایجاد تا بسته شدن، یک شیء (Trade Object) با وضعیت، تاریخچه، قوانین، نسخه تنظیمات، معیارهای عملکرد و قابلیت بازپیکربندی خواهد بود. این رویکرد امکان مدیریت بسیار دقیق‌تر، ممیزی کامل و توسعه قابلیت‌های پیشرفته مانند بازطراحی پویا، سناریوهای اضطراری و هماهنگی با کل پرتفوی را فراهم می‌کند.
---
پایان بخش اول فصل هفتم
در بخش بعدی، وارد طراحی Execution Intelligence Engine خواهیم شد؛ بخشی که سفارش‌ها را قبل از ارسال به صرافی تحلیل می‌کند، بهترین روش اجرا را انتخاب می‌کند، کیفیت اجرای واقعی را پایش می‌کند، لغزش قیمت، تأخیر شبکه، وضعیت Order Book و محدودیت‌های API را در نظر می‌گیرد و در صورت نیاز، برنامه اجرای معامله را در لحظه بازطراحی می‌کند. این بخش برای اجرای پایدار روی Python و Termux، به‌ویژه در بازار کریپتو، یکی از مهم‌ترین اجزای کل معماری خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 7 (ادامه)
بخش دوم
Institutional Execution Intelligence Engine
موتور هوشمند اجرای معاملات
---
7.21 مقدمه
تقریباً تمام ربات‌های معامله‌گر دنیا تصور می‌کنند که پس از تولید سیگنال، تنها کاری که باقی مانده ارسال یک دستور خرید یا فروش است.
این بزرگ‌ترین اشتباه ممکن است.
در بازار واقعی، مخصوصاً کریپتو، بین این دو اتفاق یعنی:
Signal Generated
↓
Order Filled
ممکن است ده‌ها رخداد رخ دهد.
از جمله:
تغییر Order Book
تغییر Funding
تغییر Spread
افزایش ناگهانی Volatility
ایجاد Liquidity Sweep
ورود News
کند شدن اینترنت
افزایش Latency
Reject شدن سفارش
Partial Fill
API Timeout
Exchange Maintenance
Rate Limit
Price Jump
در نتیجه،
Execution
خودش
یک موتور
کاملاً مستقل است.
---
7.22 فلسفه طراحی
در APEX
هیچ Order
مستقیماً
ارسال نمی‌شود.
ابتدا وارد
Execution Intelligence
می‌شود.
Trade Blueprint
↓
Execution Intelligence
↓
Execution Plan
↓
Exchange
---
7.23 وظایف موتور
Execution Engine
مسئول:
تحلیل وضعیت صرافی
تحلیل کیفیت نقدینگی
تحلیل کیفیت دفتر سفارش
تحلیل هزینه اجرا
تحلیل تأخیر
تحلیل کیفیت شبکه
تحلیل وضعیت API
انتخاب بهترین روش اجرا
پایش اجرای سفارش
مدیریت خطاها
مدیریت سفارش‌های ناقص
مدیریت بازیابی
است.
---
7.24 Exchange Capability Registry
هر صرافی
قابلیت‌های خاص خود را دارد.
مثلاً
Binance
Iceberg
TWAP
Reduce Only
Post Only
OCO
Trailing
--------------
Bybit
...
--------------
OKX
...
--------------
Execution Engine
ابتدا
Capability
صرافی را
بارگذاری می‌کند.
---
7.25 Symbol Trading Rules
برای هر Symbol
موارد زیر
ذخیره می‌شود.
Minimum Quantity
Maximum Quantity
Minimum Notional
Tick Size
Step Size
Precision
Margin Mode
Leverage Limit
Funding Interval
Trading Hours
---
7.26 Exchange State Monitor
قبل از هر معامله
سیستم
وضعیت صرافی را
بررسی می‌کند.
Normal
↓
Congested
↓
Maintenance
↓
Emergency
---
اگر
Exchange
پایدار نباشد.
معامله
لغو
می‌شود.
---
7.27 Network Health Monitor
یکی از مهم‌ترین قسمت‌ها
برای اجرای روی موبایل.
پارامترها:
Latency
Packet Loss
Bandwidth
Reconnect Count
DNS Delay
Connection Stability
Jitter
---
این اطلاعات
به
Execution Optimizer
ارسال می‌شوند.
---
7.28 Device Health Monitor
از آنجا که پروژه روی Termux اجرا می‌شود،
خود گوشی نیز بخشی از سیستم است.
پارامترها:
Battery
Temperature
CPU Usage
RAM Usage
Storage
Charging
Network Type
Signal Strength
---
اگر
Temperature
زیاد شود.
Execution Mode
تغییر می‌کند.
---
7.29 Order Book Intelligence
یکی از مهم‌ترین بخش‌ها.
سیستم
صرفاً
Best Bid
و
Best Ask
را
نمی‌بیند.
بلکه
کل ساختار
دفتر سفارش
را
مدل می‌کند.
---
موارد قابل استخراج:
Depth Profile
Liquidity Wall
Spoof Probability
Iceberg Detection
Queue Pressure
Bid/Ask Imbalance
Liquidity Vacuum
Hidden Absorption
---
7.30 Liquidity Cost Model
قبل از ارسال سفارش
سیستم
تخمین می‌زند.
اگر
Order
ارسال شود.
احتمالاً
چقدر
Slippage
رخ خواهد داد.
---
خروجی
Expected Slippage
---
7.31 Fill Probability Model
سیستم
برای هر سفارش
احتمال Fill
را
محاسبه می‌کند.
مثلاً
Limit Order
Fill Probability
72%
---
یا
Passive Order
↓
41%
---
7.32 Smart Order Router
در آینده
اگر
چندین صرافی
استفاده شود.
سیستم
بهترین
Exchange
را
انتخاب می‌کند.
بر اساس:
Fee
Spread
Liquidity
Fill Probability
Latency
Reliability
---
7.33 Order Splitting Engine
سفارش‌های بزرگ
نباید
یکجا
ارسال شوند.
سیستم
آنها را
تقسیم می‌کند.
مثلاً
40%
↓
30%
↓
20%
↓
10%
---
این تقسیم
وابسته به
Order Book
است.
---
7.34 Execution Strategy Selector
برای هر معامله
نوع اجرا
انتخاب می‌شود.
نمونه حالت‌ها
Immediate
Passive
TWAP
VWAP
Adaptive
Liquidity Seeking
Stealth
Aggressive
Balanced
---
7.35 Adaptive Execution Mode
Execution Mode
در طول معامله
می‌تواند
تغییر کند.
مثلاً
ابتدا
Passive
اما
اگر
حرکت قیمت
شروع شد.
به
Aggressive
تبدیل شود.
---
7.36 Order Lifecycle Manager
هر سفارش
دارای
چرخه عمر
است.
Created
↓
Validated
↓
Submitted
↓
Accepted
↓
Queued
↓
Partially Filled
↓
Filled
↓
Cancelled
↓
Expired
↓
Rejected
↓
Recovered
↓
Closed
---
7.37 Partial Fill Manager
اگر
فقط
۳۰٪
Order
Fill
شود.
سیستم
نباید
گیج شود.
بلکه
باید
برای
۷۰٪
باقی مانده
تصمیم جدید
بگیرد.
---
7.38 Timeout Manager
اگر
Order
تا
زمان مشخص
Fill
نشود.
یکی از حالت‌های زیر
انتخاب می‌شود.
Cancel
Replace
Modify
Wait
Switch Strategy
---
7.39 Smart Retry Engine
Retry
نباید
ثابت باشد.
هر خطا
Policy
مخصوص
خودش
را دارد.
مثلاً
Timeout
↓
Retry
--------------
Rate Limit
↓
Delay
--------------
Invalid Price
↓
Modify
--------------
Maintenance
↓
Pause
---
7.40 API Error Classifier
تمام خطاهای API
دسته‌بندی می‌شوند.
Temporary
Permanent
Authentication
Permission
Network
Exchange
Validation
Unknown
هر دسته
Recovery
اختصاصی
خود را دارد.
---
7.41 State Recovery Engine
اگر برنامه روی گوشی بسته شود، سیستم ری‌استارت شود یا اینترنت قطع گردد، نباید وضعیت معاملات از بین برود.
Execution Engine باید بتواند پس از راه‌اندازی مجدد:
سفارش‌های باز را بازیابی کند.
موقعیت‌های باز را با صرافی تطبیق دهد.
اختلاف‌های احتمالی را تشخیص دهد.
State داخلی را بازسازی کند.
این بخش برای اجرای ۲۴ ساعته روی Termux حیاتی است.
---
7.42 Event Sourcing
به جای ذخیره صرف آخرین وضعیت، تمام رویدادها ثبت می‌شوند.
نمونه:
Order Created
↓
Order Modified
↓
Order Submitted
↓
Order Accepted
↓
Partial Fill
↓
Stop Updated
↓
Take Profit Updated
↓
Position Closed
از روی این Event Log می‌توان کل وضعیت سیستم را بازسازی کرد.
---
7.43 Audit Trail
تمام تصمیم‌های Execution باید قابل ممیزی باشند.
برای هر تصمیم ثبت می‌شود:
دلیل انتخاب Execution Mode
وضعیت Order Book
Latency
Spread
Slippage Prediction
API Response
Retry History
---
7.44 Fail-Safe Execution
اگر شرایط بحرانی رخ دهد، سیستم وارد حالت Fail-Safe می‌شود.
نمونه شرایط:
از دست رفتن ارتباط با صرافی
افزایش شدید Latency
افزایش غیرعادی Slippage
داغ شدن بیش از حد دستگاه
کمبود شدید باتری
ناهماهنگی Position داخلی و صرافی
در این حالت، بسته به سیاست تعریف‌شده، سیستم می‌تواند:
توقف ورودهای جدید
کاهش اندازه معاملات
بستن موقعیت‌های پرریسک
توقف کامل معاملات
را اجرا کند.
---
7.45 Execution Quality Score (EQS)
پیشنهاد جدید برای معماری.
برای هر اجرای واقعی، یک امتیاز کیفیت محاسبه می‌شود که شامل:
Slippage واقعی نسبت به پیش‌بینی
سرعت اجرا
درصد Fill
هزینه نهایی
تعداد Retry
اختلاف قیمت هدف و قیمت اجرا
است.
این امتیاز به Probability Engine و هر دو Optimizer بازگردانده می‌شود تا سیستم از کیفیت اجرای واقعی نیز یاد بگیرد.
---
7.46 خروجی Execution Intelligence
خروجی این موتور شامل:
Execution Plan
Order Strategy
Exchange Selection
Order Schedule
Retry Policy
Recovery Policy
Execution Quality Metrics
Audit Log
Event Stream
Live Execution State
است.
---
پایان بخش دوم فصل هفتم
در بخش بعدی وارد Dynamic Position Management Engine خواهیم شد؛ جایی که پس از باز شدن معامله، سیستم به‌صورت لحظه‌ای موقعیت را مدیریت می‌کند، حد ضرر و حد سود را بازطراحی می‌کند، خروج‌های پله‌ای، Break-even، Trailing، Hedge، کاهش یا افزایش حجم، و حتی تصمیم به خروج زودهنگام را بر اساس تغییر Probability، Market State و شرایط پرتفوی انجام می‌دهد. این بخش، چرخه عمر معامله را از لحظه Fill شدن تا بسته شدن کامل مدیریت خواهد کرد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 7 (ادامه)
بخش سوم
Dynamic Position Management Engine
موتور مدیریت هوشمند موقعیت‌های باز
---
7.47 مقدمه
یکی از بزرگ‌ترین اشتباهات اکثر ربات‌های معامله‌گر این است که تصور می‌کنند بعد از Fill شدن سفارش، کار سیستم تقریباً تمام شده است.
در واقع دقیقاً از همین لحظه مهم‌ترین بخش معامله آغاز می‌شود.
سیستم‌های معمولی تقریباً به این شکل هستند:
Entry
↓
Wait
↓
TP
or
SL
اما در معماری APEX هیچ معامله‌ای حتی برای یک ثانیه نیز بدون نظارت باقی نمی‌ماند.
هر Position یک موجودیت زنده (Living Entity) است که وضعیت آن دائماً بازارزیابی می‌شود.
---
7.48 Position Object
هر معامله بعد از Fill شدن به یک Position Object تبدیل می‌شود.
ساختار پیشنهادی:
Position ID
Trade ID
Signal Version
Entry Version
Optimizer Version
Market Snapshot
Entry Price
Average Price
Current Price
Floating PnL
Realized PnL
Position Size
Remaining Size
Risk Budget
Current Stop
Current Target
Current Probability
Current Confidence
Current Regime
Current Health
Lifecycle State
History
Audit Trail
---
7.49 Position Lifecycle
Pending
↓
Opened
↓
Monitoring
↓
Scaling
↓
Risk Reduction
↓
Trailing
↓
Exit Preparation
↓
Closing
↓
Closed
↓
Archived
---
هیچ Position
نباید
بدون State
باشد.
---
7.50 Continuous Position Evaluation
برخلاف سیستم‌های سنتی،
Position فقط هنگام تشکیل کندل بررسی نمی‌شود.
بلکه با هر Event مهم بازار نیز بازارزیابی می‌شود.
نمونه Eventها:
تشکیل کندل جدید
تغییر Market State
تغییر Probability
تغییر Regime
Liquidity Sweep
افزایش شدید Volatility
تغییر Funding
Partial Fill
تغییر Portfolio Exposure
News Event
---
7.51 Position Health Engine
هر Position
دارای Health
است.
Excellent
↓
Healthy
↓
Stable
↓
Warning
↓
Critical
↓
Emergency
Health از ترکیب موارد زیر ساخته می‌شود:
Probability Drift
Execution Quality
Floating Drawdown
Regime Stability
Liquidity Quality
Portfolio Exposure
Volatility
---
7.52 Position Confidence
احتمال موفقیت معامله
ثابت نیست.
بعد از ورود
Probability
دوباره محاسبه می‌شود.
مثلاً
Entry
Probability
76%
↓
10 Minutes Later
63%
↓
30 Minutes Later
48%
ممکن است معامله هنوز سودده باشد
اما Confidence
کاهش یافته باشد.
---
7.53 Position Reclassification
گاهی معامله
دیگر
همان معامله اولیه نیست.
مثلاً
Trend Trade
↓
Range Trade
یا
Breakout
↓
Mean Reversion
در این صورت
کل Blueprint
دوباره ساخته می‌شود.
---
7.54 Dynamic Stop Optimizer
Stop Loss
یک خط ثابت نیست.
بلکه
یک فرآیند است.
Candidateهای جدید دائماً تولید می‌شوند.
نمونه:
ATR Stop
↓
Structure Stop
↓
Liquidity Stop
↓
VWAP Stop
↓
Regression Stop
↓
Probability Stop
↓
Portfolio Stop
---
سپس بهترین Stop
انتخاب می‌شود.
---
7.55 Stop Promotion Rules
Stop فقط
به سمت کاهش ریسک
حرکت می‌کند.
هرگز
نباید
ریسک معامله
بعد از ورود
بدون دلیل
افزایش یابد.
---
7.56 Adaptive Break-even Engine
انتقال به Break-even
نباید
بر اساس
RR ثابت
باشد.
بلکه بر اساس:
Probability
Expected Value
Liquidity
Regime
Entropy
Volatility
تصمیم گرفته می‌شود.
---
7.57 Intelligent Trailing Engine
Trailing
صرفاً
ATR
نیست.
سیستم چندین Candidate دارد.
ATR Trail
Structure Trail
Liquidity Trail
Regression Trail
VWAP Trail
Volatility Trail
Probability Trail
Hybrid Trail
Optimizer
بهترین مدل
را انتخاب می‌کند.
---
7.58 Partial Exit Optimizer
یکی از مهم‌ترین بخش‌ها.
به جای
50%
↓
50%
سیستم
بهینه‌سازی می‌کند.
مثلاً
15%
↓
20%
↓
18%
↓
47%
یا
اصلاً
Partial Exit
نداشته باشد.
---
7.59 Scale-In Optimizer
گاهی
افزایش حجم
بهترین تصمیم است.
اما فقط اگر:
Probability افزایش یافته باشد.
Risk Budget آزاد باشد.
Portfolio اجازه دهد.
Regime تأیید شود.
Execution مناسب باشد.
---
7.60 Scale-Out Optimizer
گاهی بهترین تصمیم
کاهش حجم است.
نه خروج کامل.
مثلاً
100%
↓
75%
↓
40%
↓
15%
---
7.61 Emergency Exit Engine
گاهی
خروج فوری
تنها تصمیم منطقی است.
نمونه دلایل:
Probability Collapse
Flash Crash
Exchange Failure
API Instability
Massive Liquidity Loss
Device Failure
Portfolio Risk Explosion
---
7.62 Trade Survival Monitor
این موتور
دائماً احتمال زنده ماندن معامله
تا رسیدن به Target
را محاسبه می‌کند.
Trade Survival Probability
اگر این احتمال
به شدت افت کند،
سیستم
خروج زودهنگام را بررسی می‌کند.
---
7.63 Opportunity Cost Engine
یکی از قابلیت‌هایی که تقریباً هیچ رباتی ندارد.
ممکن است معامله فعلی
بد نباشد.
اما
همزمان
معامله بسیار بهتری
ایجاد شده باشد.
سیستم
Opportunity Cost
را محاسبه می‌کند.
اگر:
Expected Utility(New Trade)
>
Expected Utility(Current Trade)
ممکن است
معامله فعلی
بسته شود.
---
7.64 Capital Reallocation Engine
در ادامه بخش قبل،
سرمایه آزاد شده
هوشمندانه
به معامله جدید
منتقل می‌شود.
این فرآیند
وابسته به:
Portfolio
Correlation
Risk Budget
Expected Utility
است.
---
7.65 Position Drift Detector
گاهی
بازار تغییر کرده است.
اما Position
هنوز
قدیمی فکر می‌کند.
این موتور
Drift
را
تشخیص می‌دهد.
---
7.66 Position Rebuild Engine
اگر Drift
شدید باشد.
Position
دوباره
از صفر
ارزیابی می‌شود.
شامل:
Entry Thesis
Probability
Risk
Stop
Target
Holding Time
---
7.67 Position Explainability
برای هر تغییر
ثبت می‌شود.
مثلاً
Stop Updated
↓
Reason
Liquidity Sweep
Probability Increased
Regime Stable
یا
Partial Exit
↓
Reason
Entropy Increased
---
7.68 Position Timeline
تمام عمر معامله
ثبت می‌شود.
Entry
↓
Scale In
↓
Stop Update
↓
Partial Exit
↓
Trailing
↓
Target Update
↓
Exit
↓
Archive
---
7.69 Live Trade Dashboard
هر معامله
دارای داشبورد داخلی است.
شامل:
Probability
Confidence
EV
Floating Risk
Remaining Risk
Portfolio Impact
Stop Distance
Target Distance
Position Health
Execution Quality
Time Remaining
Holding Efficiency
---
7.70 Portfolio Feedback Loop
هر تغییر
در Position
باید
به کل سیستم
بازگردد.
Position
↓
Portfolio
↓
Risk Budget
↓
Signal Optimizer
↓
Probability Engine
↓
Execution Engine
به این ترتیب هیچ معامله‌ای به‌صورت مستقل تصمیم‌گیری نمی‌شود؛ هر تغییر در یک موقعیت می‌تواند بودجه ریسک، کیفیت فرصت‌های جدید و حتی آستانه تولید سیگنال سایر معاملات را تغییر دهد.
---
7.71 Meta Position Manager (ارتقاء جدید)
این بخش را پیشنهاد می‌کنم به معماری اضافه کنیم، زیرا در طراحی اولیه وجود نداشت.
به جای اینکه هر Position جداگانه مدیریت شود، یک Meta Position Manager بر کل موقعیت‌های باز نظارت می‌کند.
وظایف آن:
تشخیص تداخل بین معاملات
اولویت‌بندی موقعیت‌ها
تخصیص مجدد سرمایه
کنترل ریسک تجمعی
هماهنگ‌سازی Trailing بین معاملات همبسته
مدیریت هم‌زمان خروج‌های اضطراری
جلوگیری از تمرکز بیش از حد روی یک سناریوی بازار
در عمل، این لایه Positionها را مانند اعضای یک پرتفوی واحد مدیریت می‌کند، نه مجموعه‌ای از معاملات مستقل.
---
پایان بخش سوم فصل هفتم
در بخش بعدی وارد Institutional Portfolio Intelligence Engine خواهیم شد؛ جایی که کل پرتفوی به‌عنوان یک سیستم پویا مدل‌سازی می‌شود، ریسک تجمعی، همبستگی دارایی‌ها، تخصیص سرمایه، سناریوهای کلان، کنترل Drawdown، Kill-Switch چندلایه و سیاست‌های بقای سرمایه طراحی می‌شوند. این بخش مرز بین یک ربات معامله‌گر و یک سامانه مدیریت سرمایه در سطح صندوق‌های سرمایه‌گذاری را مشخص خواهد کرد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 8
Institutional Portfolio Intelligence Engine
موتور هوشمند مدیریت پرتفوی
---
8.1 مقدمه
اکثر ربات‌های معاملاتی دنیا
اصلاً
مفهومی به نام
Portfolio
ندارند.
آنها فقط
معامله
می‌کنند.
یعنی
Signal
↓
Trade
↓
Signal
↓
Trade
↓
Signal
↓
Trade
هر معامله
کاملاً مستقل است.
در حالی که
در مؤسسات مالی
اصلاً
چنین چیزی وجود ندارد.
آنچه مدیریت می‌شود
Trade
نیست.
بلکه
Portfolio
است.
در حقیقت
تمام معامله‌ها
فقط ابزارهایی هستند
برای مدیریت یک Portfolio.
---
8.2 فلسفه طراحی
در APEX
هیچ معامله‌ای
بدون اجازه
Portfolio
باز نمی‌شود.
معماری
به صورت زیر است.
Signal
↓
Probability
↓
Risk Optimizer
↓
Portfolio Intelligence
↓
Execution
یعنی
آخرین تصمیم
همیشه
توسط Portfolio
گرفته می‌شود.
---
8.3 تعریف Portfolio State
Portfolio
خودش
یک موجودیت مستقل است.
دارای State.
Portfolio State
↓
Risk
↓
Exposure
↓
Health
↓
Liquidity
↓
Capital
↓
Performance
↓
Capacity
---
8.4 Portfolio Object
ساختار پیشنهادی
Portfolio ID
Owner
Version
Total Capital
Available Capital
Locked Capital
Floating PnL
Realized PnL
Exposure
Leverage
Margin
Portfolio Risk
Portfolio Volatility
Portfolio Beta
Portfolio Health
Current Regime
Drawdown
Max Drawdown
Recovery
Open Positions
Closed Positions
Audit Log
---
8.5 Portfolio Health
همانند Position
Portfolio
نیز
دارای Health
است.
Excellent
Healthy
Stable
Warning
Critical
Emergency
Frozen
---
8.6 Portfolio Exposure Engine
Exposure
فقط
مجموع Positionها
نیست.
بلکه
به چندین بعد
تقسیم می‌شود.
---
Directional Exposure
---
Sector Exposure
---
Coin Exposure
---
Exchange Exposure
---
Stablecoin Exposure
---
Leverage Exposure
---
Volatility Exposure
---
Liquidity Exposure
---
Tail Exposure
---
8.7 Dynamic Capital Allocation
سرمایه
نباید
ثابت تقسیم شود.
مثلاً
Trade A
30%
Trade B
25%
Trade C
45%
بلکه
وابسته است به
Expected Utility
و
Portfolio Utility
---
8.8 Utility Maximizer
هدف
بیشترین سود
نیست.
هدف
بیشترین Utility
است.
Utility
ترکیبی از:
سود
ریسک
احتمال
سرمایه آزاد
تنوع
نقدشوندگی
خواهد بود.
---
8.9 Portfolio Correlation Engine
همبستگی
بین Positionها
دائماً
محاسبه می‌شود.
نه فقط
Correlation کلاسیک.
بلکه
چندین نوع.
---
Linear
---
Rank
---
Tail
---
Volatility
---
Liquidity
---
Behavioral
---
Regime
---
8.10 Correlation Graph
سیستم
Graph
می‌سازد.
BTC
↓
ETH
↓
SOL
↓
AVAX
↓
LINK
وزن یال‌ها
وابسته به
Correlation
است.
---
8.11 Hidden Correlation
گاهی
دو دارایی
Correlation
ندارند.
اما
در Crash
کاملاً
همسو
می‌شوند.
سیستم
باید
Hidden Correlation
را
تشخیص دهد.
---
8.12 Concentration Risk Engine
اگر
تمام معاملات
تقریباً
روی
یک Theme
باشند.
ریسک
بسیار زیاد است.
مثلاً
تمام معاملات
AI Token
باشند.
---
یا
تمام معاملات
Layer1
باشند.
---
یا
همه
Long
باشند.
---
8.13 Diversification Score
سیستم
درجه تنوع
را
محاسبه می‌کند.
Diversification Score
0
↓
100
---
8.14 Portfolio Entropy
Entropy
فقط
برای بازار
نیست.
Portfolio
نیز
Entropy
دارد.
---
اگر
تمام سرمایه
روی
یک دارایی
باشد.
Entropy
کم است.
---
اگر
به شکل مناسبی
پخش شده باشد.
Entropy
زیادتر خواهد بود.
---
8.15 Portfolio Risk Budget
کل Portfolio
دارای
بودجه ریسک
است.
مثلاً
2%
Per Day
--------------
5%
Per Week
--------------
10%
Per Month
اگر
بودجه
تمام شود.
هیچ معامله جدیدی
باز
نمی‌شود.
---
8.16 Adaptive Exposure Limit
حداکثر Exposure
ثابت نیست.
وابسته است به:
Market Regime
Volatility
Confidence
Drawdown
Probability
Optimizer Confidence
---
8.17 Capital Reservation Engine
تمام سرمایه
نباید
همیشه
درگیر باشد.
سیستم
درصدی
از سرمایه
را
برای
فرصت‌های آینده
رزرو می‌کند.
---
8.18 Opportunity Queue
تمام سیگنال‌ها
بلافاصله
اجرا
نمی‌شوند.
ابتدا
داخل
Opportunity Queue
قرار می‌گیرند.
---
سپس
Ranking
می‌شوند.
---
8.19 Opportunity Ranking
هر سیگنال
امتیاز می‌گیرد.
Probability
Confidence
Expected Utility
Portfolio Impact
Risk
Execution Cost
Liquidity
Correlation
Capital Efficiency
---
سپس
بر اساس
Ranking
اجرا
می‌شود.
---
8.20 Portfolio Optimizer
این موتور
تصمیم می‌گیرد.
اگر
همزمان
۱۰ معامله
وجود داشته باشد.
کدام
باید
باز شوند.
---
ممکن است
بهترین معامله
از نظر خودش
اصلاً
باز نشود.
زیرا
Portfolio
نیازی به آن
ندارد.
---
8.21 Portfolio Utility Function
تابع هدف پرتفوی صرفاً جمع سود معاملات نیست.
نمونه:
Maximize
Expected Portfolio Utility
Risk Adjusted Return
Diversification
Capital Efficiency
Recovery Speed
----------------
Minimize
Portfolio Drawdown
Correlation
Tail Risk
Liquidity Risk
Exposure
Capital Lock Time
---
8.22 Dynamic Exposure Rebalancer
با تغییر شرایط بازار، نسبت سرمایه اختصاص‌یافته به موقعیت‌های باز می‌تواند تغییر کند.
نمونه:
BTC
35%
↓
25%
ETH
20%
↓
30%
Cash
10%
↓
25%
این تغییر لزوماً به معنای بستن معامله نیست؛ ممکن است از طریق کاهش یا افزایش تدریجی حجم انجام شود.
---
8.23 Portfolio Stress Testing
قبل از هر تصمیم مهم، پرتفوی تحت سناریوهای فرضی آزمایش می‌شود.
نمونه سناریوها:
Flash Crash
Gap Down
API Failure
Exchange Outage
Funding Spike
Volatility Explosion
Stablecoin Depeg
Network Congestion
برای هر سناریو، اثر بر سرمایه، نقدینگی و بودجه ریسک محاسبه می‌شود.
---
8.24 Tail Risk Engine
تمرکز این موتور بر رویدادهای کم‌احتمال اما بسیار پرهزینه است.
نمونه:
سقوط ناگهانی ۳۰٪ بازار
توقف برداشت از صرافی
از دست رفتن اتصال اینترنت
همبستگی کامل دارایی‌ها در بحران
خروجی این موتور مستقیماً روی اندازه موقعیت و Kill-Switch اثر می‌گذارد.
---
8.25 Portfolio Survival Probability
در کنار احتمال موفقیت هر معامله، احتمال بقای کل پرتفوی نیز محاسبه می‌شود.
این شاخص نشان می‌دهد:
> اگر شرایط بسیار نامطلوب رخ دهد، احتمال حفظ سرمایه در محدوده قابل‌قبول چقدر است؟
---
8.26 Recovery Engine
پس از هر دوره زیان، سیستم مستقیماً به حالت عادی بازنمی‌گردد.
مراحل:
Drawdown
↓
Capital Protection
↓
Reduced Risk
↓
Performance Recovery
↓
Normal Mode
در هر مرحله، بودجه ریسک و اندازه موقعیت‌ها متفاوت خواهد بود.
---
8.27 Dynamic Kill-Switch
در طراحی اولیه، Kill-Switch صرفاً بر اساس Drawdown بود.
در نسخه نهایی، Kill-Switch چندلایه است و می‌تواند بر اساس هر یک از عوامل زیر فعال شود:
Max Drawdown
Tail Risk
Portfolio Health
Execution Failure
Probability Collapse
Device Failure
Exchange Instability
Data Integrity Failure
Optimizer Failure
---
8.28 Portfolio Explainability
برای هر تصمیم پرتفوی باید ثبت شود:
چرا این معامله پذیرفته شد؟
چرا معامله دیگری رد شد؟
بودجه ریسک چگونه تخصیص یافت؟
چرا اندازه موقعیت تغییر کرد؟
چرا Kill-Switch فعال شد؟
چرا سرمایه رزرو شد؟
---
8.29 Portfolio Digital Twin (پیشنهاد جدید)
این قابلیت را پیشنهاد می‌کنم به معماری اضافه کنیم.
یک نسخه مجازی از پرتفوی ساخته می‌شود که تمام تصمیم‌های آینده ابتدا روی آن اجرا می‌شوند.
اگر نتیجه شبیه‌سازی مطلوب بود، همان تصمیم روی پرتفوی واقعی اعمال می‌شود.
این Digital Twin می‌تواند:
تغییرات سرمایه
تغییرات Exposure
تغییرات Correlation
تغییرات Utility
اثر سناریوهای مختلف
را بدون ریسک واقعی ارزیابی کند.
---
8.30 خروجی Portfolio Intelligence
خروجی این موتور شامل:
Portfolio State
Portfolio Health
Exposure Matrix
Correlation Graph
Opportunity Queue
Opportunity Ranking
Capital Allocation Plan
Risk Budget Status
Stress Test Report
Tail Risk Report
Survival Probability
Kill-Switch Status
Digital Twin Evaluation
Explainability Report
است.
---
پایان بخش اول فصل هشتم
در بخش بعدی وارد Institutional Regime Intelligence Engine خواهیم شد؛ موتوری که وظیفه آن شناسایی چرخه‌های رفتاری بازار، تغییر رژیم‌ها، فازهای ساختاری، محیط‌های آماری و انتقال بین حالت‌های مختلف بازار است. این موتور به تمام بخش‌های معماری، از Probability Engine گرفته تا Signal Optimizer، Risk Optimizer و Portfolio Intelligence، اعلام می‌کند که «اکنون بازار در چه جهانی قرار دارد» تا کل سیستم به‌صورت هماهنگ رفتار خود را با آن تطبیق دهد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 8 (ادامه)
بخش دوم
Institutional Regime Intelligence Engine
موتور هوشمند تشخیص رژیم‌های بازار
---
8.31 مقدمه
تقریباً تمام اندیکاتورها و حتی بسیاری از الگوریتم‌های معاملاتی، فرض می‌کنند که قوانین بازار همیشه ثابت هستند.
این فرض، بزرگ‌ترین منشأ Overfitting در سیستم‌های معاملاتی است.
در واقع بازار یک سیستم ثابت نیست، بلکه دائماً بین رژیم‌های مختلف جابه‌جا می‌شود.
ممکن است امروز:
روندی (Trend)
فردا رنج (Range)
سپس نوسانی (High Volatility)
سپس کم‌نوسان (Compression)
سپس خبرمحور (News Driven)
باشد.
اگر یک مدل بدون تشخیص Regime روی همه این شرایط اجرا شود، دیر یا زود شکست خواهد خورد.
به همین دلیل، در معماری APEX هیچ ماژولی مستقیماً از داده بازار استفاده نمی‌کند؛ ابتدا باید Regime Intelligence Engine وضعیت بازار را تفسیر کند.
---
8.32 فلسفه طراحی
Regime Engine یک اندیکاتور نیست.
یک Context Generator است.
Raw Market Data
↓
Feature Extraction
↓
Regime Intelligence
↓
Market Context
↓
All Other Engines
یعنی خروجی این موتور به تمام بخش‌های سیستم ارسال می‌شود.
---
8.33 تعریف Regime
در این معماری، Regime فقط به معنای Trend یا Range نیست.
بلکه یک بردار چندبعدی است.
نمونه:
Trend State
Volatility State
Liquidity State
Participation State
Structural State
Behavioral State
Macro State
Risk State
Execution State
بنابراین ممکن است بازار همزمان:
روند صعودی
با نوسان زیاد
نقدشوندگی پایین
مشارکت ضعیف
ساختار سالم
رفتار هیجانی
داشته باشد.
---
8.34 Regime Object
Regime ID
Timestamp
Version
Trend Class
Volatility Class
Liquidity Class
Structure Class
Behavior Class
Confidence
Entropy
Expected Duration
Transition Probability
Stability
Health
History
---
8.35 Trend Classification Engine
این موتور فقط Up یا Down تولید نمی‌کند.
بلکه کلاس‌های دقیق‌تر.
Strong Bull
Bull
Weak Bull
Neutral
Weak Bear
Bear
Strong Bear
و همچنین
قدرت هر کلاس
را نیز اندازه‌گیری می‌کند.
---
8.36 Structure Intelligence
ساختار بازار
صرفاً
BOS
یا
CHOCH
نیست.
سیستم
موارد زیر را مدل می‌کند.
Market Structure
Swing Geometry
Internal Structure
External Structure
Liquidity Structure
Compression Structure
Expansion Structure
---
8.37 Volatility Regime
به جای استفاده صرف از ATR، چندین شاخص نوسان ترکیب می‌شوند.
خروجی:
Ultra Low
Low
Normal
High
Extreme
همراه با احتمال انتقال به هر سطح.
---
8.38 Liquidity Regime
بازار از نظر کیفیت نقدشوندگی نیز طبقه‌بندی می‌شود.
Deep
Healthy
Normal
Thin
Critical
این خروجی روی نوع سفارش، اندازه موقعیت و حتی مجاز بودن ورود اثر می‌گذارد.
---
8.39 Participation Regime
یکی از قابلیت‌هایی که معمولاً در Pine Script قابل پیاده‌سازی کامل نیست.
هدف، تخمین کیفیت مشارکت بازیگران بازار است.
شاخص‌هایی مانند:
حجم نسبی
سرعت گردش معاملات
تغییرات Open Interest (در صورت دسترسی)
Funding
جریان سفارش‌ها
برای برآورد این وضعیت استفاده می‌شوند.
---
8.40 Behavioral Regime
بازار فقط با اعداد توصیف نمی‌شود.
رفتار نیز مهم است.
نمونه کلاس‌ها:
Fear
Panic
Capitulation
Recovery
Greed
Euphoria
Distribution
Accumulation
این طبقه‌بندی بر اساس مجموعه‌ای از ویژگی‌های آماری و رفتاری انجام می‌شود.
---
8.41 Structural Stability Score
هر ساختار بازار دارای میزان پایداری است.
مثلاً ممکن است یک روند صعودی وجود داشته باشد، اما بسیار شکننده باشد.
این شاخص به Signal Optimizer اعلام می‌کند که آیا می‌توان به ساختار فعلی اعتماد کرد یا خیر.
---
8.42 Regime Transition Matrix
یکی از مهم‌ترین بخش‌های معماری.
سیستم احتمال انتقال بین رژیم‌ها را مدل می‌کند.
نمونه:
Bull
↓
Bull
72%
↓
Range
18%
↓
Bear
10%
به این ترتیب، سیستم فقط وضعیت فعلی را نمی‌داند؛ بلکه احتمال وضعیت بعدی را نیز تخمین می‌زند.
---
8.43 Regime Persistence Model
برای هر Regime، طول عمر مورد انتظار محاسبه می‌شود.
نمونه:
Expected Remaining Duration
42 Minutes
این مقدار در تعیین:
زمان نگهداری معامله
نوع حد سود
نوع Trailing
به کار می‌رود.
---
8.44 Regime Confidence
تشخیص Regime نیز دارای عدم قطعیت است.
بنابراین علاوه بر Regime، میزان Confidence آن نیز محاسبه می‌شود.
اگر Confidence پایین باشد، تمام موتورهای دیگر رفتار محافظه‌کارانه‌تری اتخاذ می‌کنند.
---
8.45 Regime Entropy
اگر چندین Regime با احتمال مشابه وجود داشته باشند، یعنی سیستم مطمئن نیست.
این عدم قطعیت با شاخص Entropy اندازه‌گیری می‌شود.
هرچه Entropy بیشتر باشد:
اندازه موقعیت کاهش می‌یابد.
Threshold ورود سخت‌تر می‌شود.
ریسک کمتر تخصیص می‌یابد.
---
8.46 Regime Drift Detector
بازار ممکن است به‌آرامی تغییر کند.
این موتور تغییرات تدریجی را تشخیص می‌دهد.
نمونه:
Bull
↓
Weak Bull
↓
Neutral
↓
Weak Bear
در این حالت، نیازی به Re-optimization کامل نیست و فقط تنظیمات جزئی اعمال می‌شود.
---
8.47 Abrupt Regime Change Detector
برخلاف بخش قبل، این موتور تغییرات ناگهانی را تشخیص می‌دهد.
نمونه:
Flash Crash
News Shock
Liquidity Collapse
Volatility Explosion
در این شرایط، پیام اضطراری به تمام موتورهای سیستم ارسال می‌شود.
---
8.48 Regime Memory
تمام Regimeهای گذشته ذخیره می‌شوند.
سیستم می‌تواند بررسی کند:
آخرین بار چه زمانی چنین شرایطی رخ داده بود؟
آن زمان کدام پارامترها بهترین عملکرد را داشتند؟
کدام استراتژی بیشترین Utility را ایجاد کرد؟
این حافظه مستقیماً توسط Signal Optimizer و Risk Optimizer استفاده می‌شود.
---
8.49 Regime Explainability
برای هر تشخیص باید مشخص باشد:
چرا این Regime انتخاب شد؟
مهم‌ترین Featureهای مؤثر چه بودند؟
Confidence چگونه محاسبه شد؟
چه Regimeهای دیگری محتمل بودند؟
احتمال انتقال به وضعیت بعدی چقدر است؟
---
8.50 Regime Service Bus (ارتقاء مهم معماری)
این بخش را پیشنهاد می‌کنم به‌عنوان یکی از اجزای مرکزی معماری اضافه کنیم.
به جای اینکه هر ماژول مستقیماً Regime را محاسبه کند، تنها Regime Intelligence Engine مسئول تولید Context باشد و از طریق یک Service Bus آن را منتشر کند.
تمام موتورهای دیگر مشترک (Subscriber) این سرویس خواهند بود:
Probability Engine
Signal Optimizer
Risk Optimizer
Execution Engine
Position Manager
Portfolio Intelligence
Optimizer Scheduler
Kill-Switch
Monitoring System
به این ترتیب:
تنها یک منبع حقیقت (Single Source of Truth) برای Regime وجود دارد.
ناسازگاری بین ماژول‌ها از بین می‌رود.
تغییر الگوریتم تشخیص Regime فقط در یک نقطه انجام می‌شود.
توسعه و تست سیستم بسیار ساده‌تر خواهد شد.
---
خروجی Regime Intelligence Engine
این موتور خروجی‌های زیر را تولید می‌کند:
Current Regime Vector
Regime Confidence
Regime Entropy
Transition Matrix
Transition Probability
Expected Regime Duration
Structural Stability Score
Liquidity Regime
Volatility Regime
Behavioral Regime
Regime Drift Status
Emergency Transition Alerts
Regime Memory Reference
Explainability Report
Published Context (Service Bus)
---
پیشنهاد معماری کلان
در این مرحله، معماری APEX از یک مجموعه ماژول مستقل فراتر رفته است. پیشنهاد می‌کنم در ادامه کتاب، تمام این موتورها (Probability، Signal Optimizer، Risk Optimizer، Execution، Position، Portfolio و Regime) تحت یک Central Decision Kernel قرار گیرند که به‌عنوان هسته تصمیم‌گیری سیستم عمل کند. این هسته مسئول هماهنگی، زمان‌بندی، اولویت‌بندی، حل تعارض بین موتورها و انتشار تصمیم نهایی خواهد بود. این لایه، معماری را از یک سیستم ماژولار به یک سیستم چندعاملی (Multi-Agent) با هماهنگی مرکزی ارتقا می‌دهد و پایه مناسبی برای افزودن قابلیت‌های پیشرفته‌تر در جلدهای بعدی فراهم می‌کند.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 9
Central Decision Kernel (CDK)
هسته مرکزی تصمیم‌گیری سیستم
---
9.1 مقدمه
تا اینجای معماری، موتورهای متعددی طراحی کرده‌ایم:
Market Data Engine
Feature Engine
SMC Engine
Probability Engine
Signal Optimizer
Risk Optimizer
Execution Engine
Position Manager
Portfolio Engine
Regime Engine
اما یک سؤال اساسی باقی می‌ماند.
اگر دو موتور با هم اختلاف نظر داشته باشند، چه کسی تصمیم نهایی را می‌گیرد؟
مثلاً:
Probability Engine
می‌گوید
BUY
اما
Portfolio Engine
به علت افزایش Exposure
می‌گوید
NO
یا
Signal Optimizer
Confidence=96%
اعلام می‌کند
اما
Execution Engine
به علت Slippage زیاد
ورود را مناسب نمی‌داند.
اگر معماری مرکزی وجود نداشته باشد،
هر ماژول
تصمیم مستقل خواهد گرفت
و سیستم دچار رفتارهای متناقض خواهد شد.
به همین علت،
معماری APEX دارای یک هسته مرکزی است.
---
9.2 فلسفه طراحی
هیچ ماژولی
اجازه ارسال مستقیم
دستور معامله
را ندارد.
تمام تصمیم‌ها
ابتدا
وارد
Central Decision Kernel
می‌شوند.
Signal
↓
Probability
↓
Risk
↓
Portfolio
↓
Execution
↓
Decision Kernel
↓
Final Decision
---
9.3 نقش CDK
CDK
وظیفه تولید سیگنال ندارد.
وظیفه آن
هماهنگ‌سازی
کل سیستم است.
---
وظایف اصلی
تصمیم نهایی
هماهنگ سازی
مدیریت تعارض
اولویت بندی
مدیریت زمان
مدیریت منابع
کنترل سلامت
کنترل امنیت
انتشار تصمیم
---
9.4 Internal Decision Bus
تمام ماژول‌ها
از طریق
Event Bus
با CDK
ارتباط برقرار می‌کنند.
هیچ ارتباط مستقیم
بین دو ماژول
وجود ندارد.
Probability
↓
Bus
↓
CDK
↓
Bus
↓
Execution
این معماری
وابستگی
(Coupling)
را بسیار کاهش می‌دهد.
---
9.5 Universal Context Object
تمام موتورها
از یک Context
مشترک
استفاده می‌کنند.
Market Context
Portfolio Context
Execution Context
Risk Context
Probability Context
Regime Context
Optimizer Context
Device Context
Exchange Context
تمام Contextها
داخل
یک شیء واحد
قرار می‌گیرند.
---
9.6 Decision Graph
تصمیم نهایی
به صورت Graph
مدل می‌شود.
Signal
↓
Probability
↓
Risk
↓
Portfolio
↓
Execution
↓
Decision
هر Node
دارای
Weight
Confidence
Latency
Validity
است.
---
9.7 Decision State Machine
هر تصمیم
دارای State است.
Created
↓
Pending
↓
Waiting
↓
Evaluating
↓
Approved
↓
Rejected
↓
Delayed
↓
Executed
↓
Archived
---
9.8 Decision Object
Decision ID
Signal ID
Timestamp
Priority
Confidence
Utility
Risk
Status
Reason
Dependencies
Expiration
Owner
Audit
History
---
9.9 Dependency Engine
هر تصمیم
وابسته به
تصمیم‌های دیگر است.
مثلاً
Open BTC
↓
Depends
↓
Portfolio Risk
یا
Close ETH
↓
Depends
↓
Execution State
---
9.10 Conflict Resolver
یکی از مهم‌ترین قسمت‌ها.
فرض کنید.
Probability
می‌گوید
BUY
اما
Portfolio
می‌گوید
NO
یا
Execution
می‌گوید
WAIT
---
Conflict Resolver
باید
این اختلاف را
حل کند.
---
9.11 Conflict Priority
برای هر موتور
وزن تصمیم
وجود دارد.
مثلاً
Emergency
100
---------
Portfolio
95
---------
Execution
90
---------
Risk
85
---------
Probability
80
---------
Signal
75
---
اما
این وزن‌ها
ثابت نیستند.
---
9.12 Adaptive Authority
Authority
وابسته به
Regime
است.
مثلاً
در Flash Crash
Execution
بالاترین Authority
را دارد.
در بازار آرام
Portfolio
Authority
بیشتری دارد.
---
9.13 Decision Confidence Fusion
تمام Confidenceها
با هم
ترکیب می‌شوند.
نه میانگین.
بلکه
مدل احتمالاتی.
مثلاً
Signal
92
Probability
94
Risk
89
Portfolio
97
Execution
93
↓
Global Confidence
95.4
---
9.14 Decision Utility
هر تصمیم
دارای Utility
است.
مثلاً
Expected Profit
+
Expected Risk
+
Capital Efficiency
+
Portfolio Utility
+
Execution Quality
↓
Decision Utility
---
9.15 Decision Latency
تصمیم‌ها
باید
Deadline
داشته باشند.
اگر
بیش از حد
طول بکشند.
خودکار
منقضی
می‌شوند.
---
9.16 Decision Expiration
مثلاً
BUY
Valid
30 Seconds
اگر
۳۰ ثانیه
بگذرد.
تصمیم
باطل
می‌شود.
---
9.17 Emergency Decision Channel
تمام تصمیم‌های اضطراری
مسیر جداگانه دارند.
Flash Crash
↓
Emergency Channel
↓
Immediate Execution
این مسیر
هیچ صفی
ندارد.
---
9.18 Decision Queue
تمام تصمیم‌ها
داخل صف
قرار می‌گیرند.
اما
Priority Queue.
---
Priority
وابسته به
Utility
Risk
Time
Regime
Emergency
---
9.19 Scheduler
CDK
زمان اجرای
تمام ماژول‌ها
را کنترل می‌کند.
مثلاً
Probability
100ms
-----------
Execution
50ms
-----------
Portfolio
500ms
-----------
Optimizer
30 Minutes
---
9.20 CPU Budget Manager
اجرای روی موبایل
نیازمند
کنترل منابع است.
برای هر موتور
بودجه تعریف می‌شود.
Probability
15%
CPU
---------
Optimizer
25%
---------
Execution
10%
---------
Monitoring
5%
---
9.21 Memory Budget
تمام ماژول‌ها
مجاز نیستند
هر مقدار RAM
مصرف کنند.
CDK
بودجه حافظه
را
کنترل می‌کند.
---
9.22 Battery Awareness
یکی از قابلیت‌هایی که مخصوص نسخه Python روی Termux پیشنهاد می‌کنم.
CDK دائماً وضعیت دستگاه را بررسی می‌کند:
درصد باتری
دمای CPU
وضعیت شارژ
Thermal Throttling
وضعیت شبکه
اگر دستگاه وارد وضعیت بحرانی شود، هسته مرکزی می‌تواند:
بهینه‌سازی‌های سنگین را متوقف کند.
نرخ پردازش را کاهش دهد.
فقط ماژول‌های حیاتی را فعال نگه دارد.
در شرایط بسیار بحرانی، سیستم را به Safe Mode منتقل کند.
---
9.23 Decision Explainability
برای هر تصمیم باید ثبت شود:
چه ماژول‌هایی در تصمیم مشارکت داشتند؟
وزن هر ماژول چه بود؟
چه داده‌هایی استفاده شد؟
چه گزینه‌هایی رد شدند؟
دلیل تصمیم نهایی چه بود؟
---
9.24 Decision Replay Engine
تمام تصمیم‌ها قابل بازپخش هستند.
یعنی بتوان در آینده دقیقاً بازسازی کرد که:
بازار چگونه بود؟
هر موتور چه خروجی‌ای تولید کرد؟
CDK چرا آن تصمیم را گرفت؟
این قابلیت برای Debug، Audit و آموزش مدل‌های آینده بسیار ارزشمند است.
---
9.25 Decision Versioning
هر تصمیم با نسخه‌های تمام اجزای مؤثر بر آن ثبت می‌شود:
نسخه Feature Engine
نسخه Probability Engine
نسخه Signal Optimizer
نسخه Risk Optimizer
نسخه Execution Engine
نسخه پارامترها
نسخه مدل‌ها
به این ترتیب، بازتولید کامل هر تصمیم در آینده امکان‌پذیر خواهد بود.
---
9.26 Meta Decision Score
پیشنهاد جدید برای معماری.
CDK فقط تصمیم نمی‌گیرد؛ کیفیت تصمیم خود را نیز ارزیابی می‌کند.
برای هر تصمیم، یک Meta Decision Score محاسبه می‌شود که پس از بسته شدن معامله، با نتیجه واقعی مقایسه می‌گردد.
این امتیاز به سیستم کمک می‌کند تا به‌مرور کیفیت فرآیند تصمیم‌گیری خود را بهبود دهد.
---
9.27 System Modes
CDK مسئول مدیریت حالت‌های کلی سیستم نیز هست.
نمونه:
Research Mode
↓
Paper Trading Mode
↓
Shadow Trading Mode
↓
Live Trading Mode
↓
Capital Protection Mode
↓
Emergency Mode
↓
Maintenance Mode
تمام ماژول‌ها رفتار خود را بر اساس Mode جاری تنظیم می‌کنند.
---
9.28 Central Knowledge Graph (ارتقاء بزرگ معماری)
این قابلیت را به‌عنوان یکی از مهم‌ترین ارتقاهای معماری پیشنهاد می‌کنم.
تمام اشیای سیستم در یک Knowledge Graph ثبت می‌شوند:
Featureها
Signalها
Positionها
Portfolio
Regimeها
Optimizerها
Exchangeها
تصمیم‌ها
روابط بین آن‌ها نیز ذخیره می‌شود.
به این ترتیب سیستم می‌تواند وابستگی‌ها را بهتر تحلیل کند، علت‌یابی انجام دهد و از تاریخچه خود یاد بگیرد.
---
9.29 خروجی CDK
خروجی هسته مرکزی شامل:
Final Decision
Decision Confidence
Decision Utility
Decision Priority
Decision Expiration
Explainability Report
Audit Package
Decision Timeline
Resource Allocation
System Mode
Event Publications
Knowledge Graph Update
است.
---
پایان فصل نهم
از این نقطه به بعد، معماری از مجموعه‌ای از موتورهای مستقل به یک سیستم عامل معاملاتی (Trading Operating System) تبدیل شده است.
در فصل دهم، معماری وارد لایه‌ای خواهد شد که معمولاً حتی در بسیاری از سامانه‌های سازمانی نیز وجود ندارد:
System Observability, Telemetry & Autonomous Monitoring Layer
این فصل تمام زیرساخت پایش، ثبت رخداد، سلامت سیستم، متریک‌ها، هشدارها، خودتشخیصی (Self-Diagnostics)، پیش‌بینی خرابی، و قابلیت مشاهده کامل (Full Observability) را طراحی خواهد کرد؛ لایه‌ای که برای اجرای پایدار و ۲۴/۷ روی Python و Termux ضروری است.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 10
System Observability, Telemetry & Autonomous Monitoring Layer
معماری پایش، مانیتورینگ، خودتشخیصی و مشاهده‌پذیری سیستم
---
10.1 مقدمه
تقریباً تمام ربات‌های معاملاتی دنیا فقط معامله می‌کنند.
آنها نمی‌دانند:
آیا سالم هستند؟
آیا داده‌ها سالم هستند؟
آیا API درست کار می‌کند؟
آیا حافظه در حال نشت است؟
آیا سرعت پردازش افت کرده است؟
آیا Optimizer قفل کرده است؟
آیا احتمال خرابی وجود دارد؟
در معماری APEX،
سیستم باید قبل از اینکه خراب شود،
بداند که در حال خراب شدن است.
---
10.2 فلسفه طراحی
Observability
با Monitoring
فرق دارد.
Monitoring
می‌گوید:
CPU = 81%
اما
Observability
پاسخ می‌دهد:
> چرا CPU ناگهان از ۲۵٪ به ۸۱٪ رسید؟
---
10.3 سه ستون اصلی Observability
معماری بر سه پایه استوار است.
Metrics
↓
Logs
↓
Traces
اما
APEX
سه ستون دیگر نیز اضافه می‌کند.
State
Events
Knowledge
بنابراین معماری نهایی شامل شش ستون خواهد بود.
Metrics
Logs
Traces
States
Events
Knowledge
---
10.4 Universal Telemetry Bus
تمام موتورها
Telemetry
تولید می‌کنند.
اما
هیچ ماژولی
مستقیماً
چیزی ذخیره نمی‌کند.
همه چیز
ابتدا وارد
Telemetry Bus
می‌شود.
Probability
↓
Bus
↓
Storage
↓
Dashboard
---
10.5 Metrics Engine
برای هر ماژول
صدها Metric
تعریف می‌شود.
نمونه
Probability Engine
Inference Time
Cache Hit
Confidence Mean
Entropy Mean
Error Rate
Execution
Fill Rate
Latency
Retry Count
Slippage
API Errors
Portfolio
Exposure
Risk
Utility
Diversification
Recovery
Optimizer
Iteration
Convergence
Population
Mutation
Fitness
---
10.6 Health Engine
هر موتور
دارای Health
است.
Healthy
↓
Stable
↓
Warning
↓
Critical
↓
Offline
Health
ترکیبی است از:
سرعت
خطا
مصرف RAM
مصرف CPU
کیفیت خروجی
نرخ Exception
---
10.7 Dependency Health
سلامت
فقط
سلامت ماژول
نیست.
وابستگی‌ها
نیز
بررسی می‌شوند.
مثلاً
Execution
↓
Depends
↓
Exchange API
اگر
Exchange
خراب شود.
Execution
نیز
Healthy
نیست.
---
10.8 Heartbeat System
تمام سرویس‌ها
باید
Heartbeat
ارسال کنند.
مثلاً
هر
۵ ثانیه.
Signal Optimizer
Alive
Execution
Alive
Probability
Alive
Portfolio
Alive
اگر
Heartbeat
قطع شود.
Recovery
شروع می‌شود.
---
10.9 Deadlock Detector
اگر
دو موتور
منتظر
یکدیگر
بمانند.
Deadlock
رخ می‌دهد.
CDK
باید
آن را
تشخیص دهد.
---
10.10 Watchdog Engine
Watchdog
بر تمام سیستم
نظارت می‌کند.
اگر
هر ماژول
قفل شود.
Restart
می‌شود.
---
10.11 Latency Monitor
برای هر ماژول
Latency
اندازه‌گیری می‌شود.
Probability
24 ms
Execution
8 ms
Portfolio
91 ms
Optimizer
2.4 sec
---
10.12 End-to-End Trace
یکی از مهم‌ترین قابلیت‌ها.
برای هر معامله
کل مسیر
ثبت می‌شود.
Market Data
↓
Feature
↓
Probability
↓
Signal
↓
Optimizer
↓
Risk
↓
Portfolio
↓
Execution
↓
Exchange
↓
Fill
در نتیجه
هر معامله
کاملاً
قابل بازسازی است.
---
10.13 Distributed Trace ID
هر Event
دارای Trace ID
است.
تمام Logها
با همان Trace
ثبت می‌شوند.
---
10.14 Structured Logging
هیچ Log
نباید
متن ساده باشد.
همه Logها
دارای ساختار هستند.
مثلاً
Timestamp
Module
Level
Trace ID
Position ID
Signal ID
Exchange
Message
Exception
---
10.15 Log Levels
DEBUG
INFO
NOTICE
WARNING
ERROR
CRITICAL
EMERGENCY
---
10.16 Event Journal
هر Event
ثبت می‌شود.
مثلاً
Signal Created
↓
Optimizer Updated
↓
Trade Opened
↓
Partial Exit
↓
Stop Updated
↓
Trade Closed
---
10.17 State Snapshot
هر چند دقیقه
کل State
سیستم
Snapshot
می‌شود.
شامل
Portfolio
Position
Optimizer
Execution
Probability
Scheduler
Cache
---
10.18 Replay Engine
اگر
سیستم
Crash
کند.
Replay
از آخرین Snapshot
شروع می‌شود.
سپس
Eventها
بازپخش می‌شوند.
---
10.19 Self Diagnostics
سیستم
خودش
تست اجرا می‌کند.
نمونه
API Test
Disk Test
RAM Test
CPU Test
Clock Test
Database Test
Network Test
Exchange Test
---
10.20 Data Integrity Monitor
یکی از مهم‌ترین قسمت‌ها.
اگر
کندل
خراب باشد.
یا
Timestamp
اشتباه باشد.
یا
Gap
وجود داشته باشد.
باید
تشخیص داده شود.
---
10.21 Feature Integrity Monitor
گاهی
خود داده
صحیح است.
اما
Feature
خراب شده است.
مثلاً
NaN
تولید شده.
یا
Overflow.
یا
Value
غیرممکن.
---
10.22 Model Integrity Monitor
Probability Engine
باید
خودش
را بررسی کند.
مثلاً
اگر
Probability
همیشه
99%
تولید کند.
مدل
خراب شده است.
---
10.23 Drift Monitoring
تمام موتورها
دارای Drift
هستند.
مثلاً
Feature Drift
Probability Drift
Optimizer Drift
Portfolio Drift
Execution Drift
Latency Drift
Performance Drift
---
10.24 Anomaly Detection Engine
سیستم
تمام رفتارهای غیرعادی
را
تشخیص می‌دهد.
مثلاً
CPU Spike
Memory Leak
Latency Spike
API Storm
Error Burst
Trade Explosion
Signal Flood
---
10.25 Predictive Failure Engine
این بخش یکی از مهم‌ترین ارتقاها نسبت به طراحی اولیه است.
سیستم فقط خرابی را تشخیص نمی‌دهد؛ بلکه احتمال خرابی آینده را نیز تخمین می‌زند.
نمونه:
احتمال پر شدن حافظه تا ۱۰ دقیقه آینده
احتمال قطع اتصال اینترنت
احتمال رسیدن CPU به آستانه Thermal Throttling
احتمال برخورد با Rate Limit صرافی
احتمال از کار افتادن سرویس خاص
در صورت عبور احتمال از آستانه تعیین‌شده، اقدامات پیشگیرانه آغاز می‌شوند.
---
10.26 Autonomous Recovery Manager
پس از تشخیص خرابی، سیستم بر اساس نوع خطا یکی از سیاست‌های زیر را اجرا می‌کند:
Retry
↓
Restart Module
↓
Reload State
↓
Switch Backup
↓
Safe Mode
↓
Emergency Shutdown
تمام این مراحل باید بدون دخالت کاربر انجام شوند.
---
10.27 Continuous Performance Profiler
Profiler فقط هنگام توسعه استفاده نمی‌شود.
در APEX، Profiler دائماً فعال است و برای هر ماژول موارد زیر را ثبت می‌کند:
زمان اجرا
مصرف CPU
مصرف RAM
تعداد تخصیص حافظه
نرخ Garbage Collection
نرخ Cache Hit
نقاط داغ (Hotspots)
این اطلاعات به Scheduler و Budget Manager بازگردانده می‌شوند.
---
10.28 Unified Operations Dashboard (پیشنهاد مهم)
پیشنهاد می‌کنم یک داشبورد عملیاتی واحد نیز به معماری اضافه شود.
این داشبورد تمام اطلاعات زیر را به‌صورت زنده نمایش می‌دهد:
سلامت سیستم
وضعیت تمام ماژول‌ها
وضعیت Optimizerها
وضعیت پرتفوی
Regime فعلی
صف تصمیم‌ها
کیفیت اجرای سفارش‌ها
هشدارها
مصرف منابع گوشی
وضعیت APIها
وضعیت اینترنت
آخرین Exceptionها
به این ترتیب، کل سیستم مانند یک مرکز کنترل (Mission Control Center) قابل مشاهده خواهد بود.
---
10.29 خروجی لایه Observability
این لایه خروجی‌های زیر را تولید می‌کند:
Metrics Stream
Structured Logs
Distributed Traces
Event Journal
State Snapshots
Health Reports
Drift Reports
Anomaly Reports
Predictive Failure Alerts
Recovery Reports
Performance Profiles
Audit Records
Dashboard Data Feed
---
ارتقای پیشنهادی معماری
تا اینجا تقریباً تمام اجزای عملیاتی سیستم طراحی شده‌اند.
اما هنوز یک مؤلفه بسیار مهم که در معماری‌های مدرن صندوق‌های کمی و سامانه‌های خودمختار دیده می‌شود، باقی مانده است:
Knowledge & Learning Layer
این لایه صرفاً داده ذخیره نمی‌کند؛ بلکه تجربه‌های سیستم را به دانش قابل استفاده تبدیل می‌کند. هر معامله، هر بهینه‌سازی، هر خطا، هر تغییر Regime و هر تصمیم به‌تدریج به بخشی از «حافظه بلندمدت» سیستم تبدیل می‌شود تا نسخه‌های آینده APEX از تجربه گذشته خود بیاموزند، نه اینکه فقط از داده خام استفاده کنند.
این فصل، پایه معماری Self-Improving Trading Operating System خواهد بود و یکی از مهم‌ترین تفاوت‌های APEX با یک ربات معامله‌گر معمولی محسوب می‌شود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 11
Knowledge, Memory & Autonomous Learning Layer
معماری حافظه، دانش، یادگیری و تکامل خودکار سیستم
---
11.1 مقدمه
تا اینجا
تقریباً تمام اجزای یک سیستم معاملاتی در سطح مؤسسات طراحی شده‌اند.
اما هنوز یک سؤال بنیادی باقی مانده است.
وقتی سیستم
ده هزار معامله انجام داد،
دقیقاً چه چیزی از آن ده هزار معامله یاد گرفته است؟
در اکثر ربات‌های معاملاتی پاسخ این است:
هیچ چیز.
در بهترین حالت فقط فایل Log بزرگ‌تر شده است.
اما در معماری APEX،
هر معامله،
هر شکست،
هر موفقیت،
هر بهینه‌سازی،
هر تغییر Regime،
هر Exception،
و حتی هر تصمیم اشتباه،
باید به دانش دائمی سیستم تبدیل شود.
---
11.2 فلسفه طراحی
باید بین چهار مفهوم تفاوت قائل شویم.
Data
↓
Information
↓
Knowledge
↓
Wisdom
داده خام
دانش نیست.
Log
دانش نیست.
Backtest
دانش نیست.
Knowledge
یعنی
اطلاعاتی که بتواند
تصمیم آینده را
بهبود دهد.
---
11.3 چهار لایه حافظه
سیستم دارای چهار نوع حافظه خواهد بود.
Working Memory
↓
Short-Term Memory
↓
Long-Term Memory
↓
Knowledge Base
---
Working Memory
حافظه لحظه‌ای.
مثلاً
آخرین کندل‌ها.
آخرین Positionها.
آخرین وضعیت API.
---
Short-Term Memory
حافظه چند ساعت یا چند روز.
مثلاً
آخرین معاملات.
آخرین Optimizationها.
آخرین Regimeها.
---
Long-Term Memory
چندین ماه یا چندین سال.
مثلاً
تمام رفتارهای بازار.
تمام Optimizationها.
تمام Performanceها.
---
Knowledge Base
نتیجه پردازش حافظه‌ها.
اینجا
دانش ذخیره می‌شود.
نه داده.
---
11.4 Knowledge Object
هر دانش
به صورت یک شیء ذخیره می‌شود.
Knowledge ID
Type
Source
Confidence
Evidence
Validity
Dependencies
Creation Time
Update Time
Expiration
Importance
References
Explanation
---
11.5 Experience Engine
هر معامله
یک Experience است.
نه فقط
یک Trade.
نمونه
Entry
↓
Execution
↓
Position Management
↓
Exit
↓
Evaluation
↓
Experience
---
11.6 Experience Repository
تمام تجربه‌ها
داخل Repository
ذخیره می‌شوند.
اما
فقط
به صورت خام
ذخیره نمی‌شوند.
بلکه
Index
می‌شوند.
بر اساس
Regime
Symbol
Timeframe
Strategy
Pattern
Probability
Outcome
Drawdown
Utility
---
11.7 Pattern Memory
یکی از مهم‌ترین بخش‌ها.
سیستم
الگوها را
حفظ می‌کند.
مثلاً
Liquidity Sweep
+
FVG
+
Bull Regime
+
Low Funding
↓
84%
Success
---
این
دیگر
فقط
Backtest
نیست.
---
11.8 Failure Memory
شکست‌ها
مهم‌تر از موفقیت‌ها هستند.
سیستم
تمام Failureها
را
طبقه‌بندی می‌کند.
مثلاً
Signal Failure
Execution Failure
Risk Failure
Optimizer Failure
Exchange Failure
Device Failure
Data Failure
---
11.9 Success Memory
معاملات موفق
نیز
طبقه‌بندی می‌شوند.
اما
نه فقط
بر اساس سود.
بلکه
بر اساس
کیفیت.
---
11.10 Knowledge Extraction Engine
هر شب
یا
هر زمان مناسب
سیستم
تمام Experienceها
را
تحلیل می‌کند.
هدف
استخراج
Knowledge
است.
---
مثلاً
Across
42,000 Trades
↓
Liquidity Sweep
Before
NY Open
↓
High Probability
---
این
Knowledge
به
Probability Engine
بازگردانده می‌شود.
---
11.11 Rule Discovery Engine
یکی از بزرگ‌ترین قابلیت‌ها.
سیستم
قوانین جدید
را
کشف می‌کند.
مثلاً
اگر
ده‌ها هزار معامله
نشان دهند.
که
High Volatility
+
High Entropy
↓
Bad Outcome
سیستم
این را
به صورت
Rule
ثبت می‌کند.
---
11.12 Knowledge Validation
هر Knowledge
قبل از استفاده
اعتبارسنجی
می‌شود.
بر اساس
Sample Size
Confidence
Stability
Time
Regime
Generalization
---
11.13 Knowledge Aging
دانش نیز
پیر می‌شود.
مثلاً
قانونی که
سه سال پیش
صحیح بوده.
ممکن است
امروز
کاملاً غلط باشد.
---
11.14 Knowledge Confidence
هر دانش
Confidence
دارد.
Very Low
Low
Medium
High
Very High
---
11.15 Knowledge Graph
یکی از مهم‌ترین بخش‌های معماری.
تمام دانش‌ها
به هم
متصل هستند.
مثلاً
Liquidity Sweep
↓
FVG
↓
OB
↓
Bull Regime
↓
High Success
---
این
یک Graph
است.
نه
Database.
---
11.16 Semantic Search
سیستم
نباید
فقط
Keyword Search
داشته باشد.
بلکه
Semantic Search.
مثلاً
بتواند
بپرسد.
Show me
similar situations
و
دانش‌های مشابه
را
پیدا کند.
---
11.17 Contextual Memory Retrieval
وقتی
Probability Engine
نیاز به دانش دارد.
نباید
کل حافظه
را
بارگذاری کند.
بلکه
فقط
Context
فعلی.
مثلاً
BTC
15m
Bull
High Volatility
Liquidity Sweep
↓
Relevant Memories
---
11.18 Meta Learning
سیستم
فقط
بازار
را
یاد نمی‌گیرد.
بلکه
یاد می‌گیرد
که
چگونه
بهتر
یاد بگیرد.
---
مثلاً
متوجه می‌شود.
که
در
High Volatility
پارامترهای خاص
باید
سریع‌تر
Update
شوند.
---
11.19 Knowledge Conflict Resolver
ممکن است
دو Knowledge
متناقض باشند.
مثلاً
Rule A
BUY
اما
Rule B
DON'T BUY
Resolver
باید
بر اساس
Confidence
Sample
Regime
Time
تصمیم بگیرد.
---
11.20 Knowledge Versioning
هر دانش
نسخه دارد.
مثلاً
Liquidity Rule
v1
↓
v2
↓
v3
هیچ دانشی
Overwrite
نمی‌شود.
---
11.21 Knowledge Compression
پس از سال‌ها فعالیت، سیستم ممکن است میلیون‌ها Experience ثبت کند.
نگهداری همه آن‌ها به شکل خام عملی نیست، به‌ویژه روی تلفن همراه.
بنابراین یک موتور Knowledge Compression پیشنهاد می‌شود که:
تجربه‌های تکراری را ادغام کند.
نمونه‌های کم‌ارزش را آرشیو کند.
الگوهای پایدار را به Rule تبدیل کند.
فقط Experienceهای منحصربه‌فرد را در حافظه فعال نگه دارد.
---
11.22 Knowledge Integrity
پایگاه دانش نیز باید مانند داده‌های بازار اعتبارسنجی شود.
هر Rule یا Knowledge باید:
منبع مشخص
شواهد
تاریخ اعتبار
سطح اطمینان
وضعیت فعال/غیرفعال
داشته باشد.
---
11.23 Knowledge Deployment
همه دانش‌های جدید بلافاصله وارد سیستم عملیاتی نمی‌شوند.
مراحل استقرار:
Candidate
↓
Validation
↓
Shadow Usage
↓
Production
↓
Monitoring
مشابه فرآیندی که برای پارامترهای بهینه‌سازی طراحی شد.
---
11.24 Autonomous Learning Policy
سیستم باید سیاست یادگیری مشخصی داشته باشد.
برای مثال:
چه زمانی دانش جدید استخراج شود؟
چه زمانی Ruleها بازنگری شوند؟
چه زمانی دانش قدیمی حذف یا آرشیو شود؟
چه زمانی فرآیند یادگیری متوقف شود تا به عملکرد لحظه‌ای آسیب نزند؟
---
11.25 Collective Intelligence (پیشنهاد معماری)
این بخش را به‌عنوان یک ارتقای مهم پیشنهاد می‌کنم.
در آینده اگر چندین Instance از APEX روی چند دستگاه یا سرور اجرا شوند، هر کدام می‌توانند دانش خود را تولید کنند.
سپس بدون انتقال داده‌های خام یا اطلاعات حساس، فقط Knowledgeهای اعتبارسنجی‌شده بین آن‌ها همگام‌سازی شود.
در نتیجه، کل سامانه به یک شبکه یادگیرنده تبدیل می‌شود که هر گره از تجربه سایر گره‌ها نیز بهره می‌برد.
---
11.26 خروجی Knowledge Layer
این لایه خروجی‌های زیر را تولید می‌کند:
Knowledge Base
Knowledge Graph
Experience Repository
Rule Repository
Memory Index
Semantic Search Index
Context Retrieval Service
Knowledge Confidence Report
Knowledge Aging Report
Learning Policy Status
Knowledge Deployment Queue
Collective Intelligence Sync Package
---
پایان فصل یازدهم
در این نقطه، معماری APEX دیگر صرفاً یک «ربات معامله‌گر» نیست، بلکه به یک Trading Operating System خودتطبیق، خودپایش و خودیادگیر تبدیل شده است.
با این حال، هنوز یک بخش بنیادین باقی مانده که می‌تواند این معماری را به سطحی نزدیک به سامانه‌های تحقیقاتی صندوق‌های کمی بزرگ برساند: Research, Experimentation & Simulation Framework؛ لایه‌ای که در آن سیستم می‌تواند فرضیه‌های جدید بسازد، آن‌ها را روی داده‌های تاریخی و شبیه‌سازی‌شده آزمایش کند، نتایج را اعتبارسنجی کند و تنها در صورت موفقیت، آن‌ها را به معماری عملیاتی وارد کند. این لایه مرز بین یک سیستم صرفاً اجرایی و یک سامانه پژوهشی خودتکامل‌یابنده را مشخص خواهد کرد.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 12
Research, Experimentation & Autonomous Simulation Framework
چارچوب تحقیق، آزمایش، اعتبارسنجی و شبیه‌سازی خودکار
---
12.1 مقدمه
یکی از بزرگ‌ترین تفاوت‌های شرکت‌های ترید کمی (Quantitative Trading Firms) با معامله‌گران معمولی این است که بیشتر زمان خود را صرف تحقیق می‌کنند، نه معامله.
در بسیاری از صندوق‌های سرمایه‌گذاری، نسبت زمان به صورت تقریبی چنین است:
Research
80%
↓
Live Trading
20%
در مقابل، اکثر ربات‌های معاملاتی تنها دو حالت دارند:
Write Code
↓
Run Bot
این معماری برای یک سیستم در سطح مؤسسه کافی نیست.
APEX باید بتواند مانند یک آزمایشگاه تحقیقاتی عمل کند.
---
12.2 فلسفه طراحی
هیچ ایده‌ای نباید مستقیماً وارد سیستم واقعی شود.
تمام ایده‌ها ابتدا باید وارد چرخه زیر شوند.
Idea
↓
Research
↓
Experiment
↓
Simulation
↓
Validation
↓
Shadow Deployment
↓
Production
این چرخه برای تمام اجزای سیستم اعمال می‌شود:
Featureهای جدید
Probability Modelها
Signalها
Ruleهای جدید
Optimizerها
Execution Logic
Risk Policy
Portfolio Policy
---
12.3 Research Workspace
سیستم دارای یک محیط تحقیق مستقل خواهد بود.
در این محیط:
هیچ معامله واقعی انجام نمی‌شود.
هیچ تغییری وارد سیستم عملیاتی نمی‌شود.
تمام آزمایش‌ها ایزوله هستند.
---
12.4 Hypothesis Object
هر تحقیق با یک فرضیه آغاز می‌شود.
ساختار:
Hypothesis ID
Title
Author
Version
Description
Expected Effect
Metrics
Target Module
Priority
Dependencies
Status
---
12.5 Experiment Object
هر فرضیه
به یک Experiment تبدیل می‌شود.
Experiment ID
Hypothesis
Dataset
Features
Parameters
Optimizer
Validation Method
Start Time
Finish Time
Results
---
12.6 Experiment Registry
تمام آزمایش‌ها ثبت می‌شوند.
هیچ آزمایشی حذف نمی‌شود.
هر Experiment دارای:
Version
Hash
Dependencies
Dataset Version
Code Version
Parameter Version
خواهد بود.
---
12.7 Dataset Manager
یکی از مهم‌ترین قسمت‌های معماری.
تمام داده‌های تاریخی نسخه‌بندی می‌شوند.
BTC
1m
v1
↓
v2
↓
v3
به این ترتیب
آزمایش‌ها همیشه قابل بازتولید خواهند بود.
---
12.8 Synthetic Market Generator
یکی از بزرگ‌ترین ارتقاهای نسبت به طراحی اولیه.
سیستم فقط روی داده واقعی آزمایش نمی‌کند.
بلکه بازار مصنوعی نیز تولید می‌کند.
نمونه سناریوها:
Flash Crash
Sideway Market
Strong Trend
Hyper Volatility
Liquidity Vacuum
Fake Breakout
Stop Hunt Cascade
Exchange Freeze
Weekend Crypto Behavior
این سناریوها برای تست مقاومت الگوریتم‌ها استفاده می‌شوند.
---
12.9 Scenario Engine
هر سناریو دارای مشخصات کامل است.
Scenario ID
Market Type
Volatility
Liquidity
Trend
Noise
Gap
Duration
Probability
---
12.10 Monte Carlo Laboratory
هر استراتژی
باید هزاران بار
روی سناریوهای تصادفی اجرا شود.
هدف:
اندازه‌گیری
پایداری.
نه
بهترین سود.
---
12.11 Robustness Laboratory
سیستم
به صورت عمدی
شرایط را خراب می‌کند.
مثلاً
حذف کندل‌ها
تأخیر API
Slippage زیاد
Latency
داده ناقص
اسپرد بالا
اگر الگوریتم همچنان عملکرد قابل قبول داشته باشد،
Robust محسوب می‌شود.
---
12.12 Ablation Engine
برای فهمیدن ارزش واقعی هر ماژول،
سیستم آن را حذف می‌کند.
مثلاً
Without SMT
↓
Performance
یا
Without Liquidity Engine
↓
Performance
اگر حذف یک ماژول تأثیر معناداری نداشته باشد،
احتمالاً آن ماژول فقط پیچیدگی ایجاد کرده است.
---
12.13 Feature Importance Laboratory
هر Feature
به صورت جداگانه
ارزیابی می‌شود.
خروجی:
Feature
Importance
Contribution
Interaction
Stability
Drift
---
12.14 Strategy Mutation Engine
یکی از پیشنهادهای مهم.
سیستم می‌تواند نسخه‌های جدیدی از استراتژی را ایجاد کند.
مثلاً:
تغییر ترتیب تأییدها
حذف بعضی فیلترها
اضافه کردن Feature جدید
تغییر وزن‌ها
سپس همه نسخه‌ها آزمایش می‌شوند.
---
12.15 Optimizer Benchmark Suite
دو Optimizer اصلی که قبلاً طراحی کردیم نیز باید دائماً ارزیابی شوند.
الف) Signal Optimizer
معیارها:
سرعت همگرایی
کیفیت جواب
پایداری
میزان Overfitting
هزینه محاسباتی
ب) Risk & Execution Optimizer
معیارها:
Utility
Sharpe
Sortino
Calmar
Profit Factor
Recovery Factor
Max Drawdown
Capital Efficiency
Tail Risk
---
12.16 Walk-Forward Research Engine
تمام آزمایش‌ها
باید
Walk Forward
داشته باشند.
Train
↓
Validate
↓
Forward Test
↓
Roll
↓
Repeat
---
12.17 Multi-Regime Validation
هیچ الگوریتمی
نباید
فقط
روی
Trend
تست شود.
بلکه
روی تمام Regimeها.
Bull
Bear
Sideway
High Volatility
Low Liquidity
Crisis
Recovery
---
12.18 Meta Research Score
هر تحقیق
امتیاز می‌گیرد.
نمونه:
Innovation
Scientific Validity
Robustness
Generalization
Deployment Safety
Utility
---
12.19 Automatic Paper Generation (پیشنهاد جدید)
پس از پایان هر تحقیق، سیستم به‌طور خودکار یک گزارش پژوهشی تولید می‌کند.
این گزارش شامل:
هدف تحقیق
فرضیه
داده‌های استفاده‌شده
روش آزمایش
نتایج
تحلیل آماری
نمودارها
دلایل پذیرش یا رد فرضیه
خواهد بود.
به این ترتیب، تاریخچه پژوهش‌های سیستم مانند یک آزمایشگاه علمی حفظ می‌شود.
---
12.20 Deployment Gate
هیچ نتیجه پژوهشی مستقیماً وارد نسخه عملیاتی نمی‌شود.
مراحل:
Research
↓
Internal Validation
↓
Stress Test
↓
Shadow Trading
↓
Limited Deployment
↓
Full Deployment
در هر مرحله، امکان بازگشت (Rollback) وجود دارد.
---
12.21 Scientific Integrity Engine
برای جلوگیری از نتایج گمراه‌کننده، سیستم باید به‌طور خودکار موارد زیر را بررسی کند:
Data Leakage
Look-Ahead Bias
Survivorship Bias
Selection Bias
Overfitting
Data Snooping
Multiple Testing Bias
اگر هر یک از این موارد تشخیص داده شود، نتیجه تحقیق نامعتبر اعلام می‌شود.
---
12.22 Continuous Research Scheduler
پژوهش نباید فقط با دخالت کاربر انجام شود.
Scheduler مشخص می‌کند:
چه زمانی آزمایش جدید اجرا شود.
چه زمانی Optimizerها دوباره آموزش ببینند.
چه زمانی تحقیقات متوقف شوند تا منابع دستگاه حفظ شود.
اولویت هر پروژه پژوهشی چگونه باشد.
---
12.23 Research Knowledge Integration
پس از پایان موفق هر تحقیق:
Research
↓
Validation
↓
Knowledge Layer
↓
Signal Optimizer
↓
Risk Optimizer
↓
Production
به این ترتیب، تمام پژوهش‌ها به بخشی از حافظه و دانش سیستم تبدیل می‌شوند.
---
12.24 Research Governance (ارتقای مهم)
برای جلوگیری از تغییرات کنترل‌نشده، هر تغییر باید دارای:
شناسه
نسخه
دلیل ایجاد
نتایج آزمایش
سطح ریسک
تأییدیه استقرار
باشد.
این بخش، معماری را به استانداردهای مدیریت تغییر در سامانه‌های سازمانی نزدیک می‌کند.
---
12.25 خروجی Research Framework
این چارچوب خروجی‌های زیر را تولید می‌کند:
Experiment Registry
Hypothesis Repository
Scenario Library
Synthetic Market Library
Monte Carlo Reports
Walk-Forward Reports
Feature Importance Reports
Ablation Reports
Optimizer Benchmarks
Scientific Integrity Reports
Deployment Recommendations
Research Papers
Research Knowledge Packages
---
پایان فصل دوازدهم
پیشنهاد بزرگ برای ادامه معماری
در این مرحله، تقریباً تمام اجزای لازم برای یک سیستم معاملاتی خودمختار طراحی شده‌اند. اما هنوز یک حوزه بسیار مهم باقی مانده که در بسیاری از سامانه‌های حرفه‌ای نیز به این سطح از جزئیات طراحی نمی‌شود:
Security, Reliability & Fault-Tolerant Infrastructure
این فصل به طراحی زیرساخت امنیتی، مدیریت کلیدهای API، رمزنگاری، کنترل دسترسی، بازیابی پس از خرابی، افزونگی (Redundancy)، تحمل خطا (Fault Tolerance)، مدیریت نسخه‌ها، Rollback، محافظت در برابر خرابی سخت‌افزار، قطعی اینترنت و بازیابی خودکار اختصاص خواهد داشت. این لایه برای اجرای ۲۴/۷ روی محیط Python و Termux حیاتی است و آخرین گام برای تبدیل APEX به یک سامانه عملیاتی در سطح سازمانی خواهد بود.
کتاب طراحی سیستم
APEX – Autonomous Probabilistic Execution eXchange (APEX)
Volume I
---
فصل 13
Security, Reliability & Fault-Tolerant Infrastructure
معماری امنیت، قابلیت اطمینان، تحمل خطا و زیرساخت عملیاتی
---
13.1 مقدمه
تقریباً تمام معامله‌گران تصور می‌کنند که بزرگ‌ترین خطر برای سرمایه،
بازار است.
در حالی که در عمل، بخش بزرگی از ضررهای واقعی ناشی از مواردی مانند:
خرابی API
قطعی اینترنت
کرش نرم‌افزار
پر شدن حافظه
اشتباه برنامه‌نویسی
ارسال سفارش تکراری
اجرای ناقص سفارش
Sync نبودن Position
خرابی دیتابیس
ریبوت شدن گوشی
خاموش شدن گوشی
اتمام باتری
از بین رفتن Session
تغییر ساعت سیستم
خطای DNS
Rate Limit
تغییر API صرافی
Data Corruption
است.
در معماری APEX
بازار
فقط
یکی
از منابع ریسک است.
---
13.2 فلسفه طراحی
هر قسمت سیستم باید فرض کند
تمام قسمت‌های دیگر
ممکن است
همین الان
خراب شوند.
این اصل
Failure First Architecture
نامیده می‌شود.
---
13.3 انواع Failure
Hardware Failure
Software Failure
API Failure
Exchange Failure
Data Failure
Network Failure
Human Failure
Optimizer Failure
Execution Failure
Model Failure
Storage Failure
Authentication Failure
---
13.4 Failure Domain Isolation
هیچ Failure
نباید
به کل سیستم
منتقل شود.
مثلاً
اگر
Probability Engine
کرش کند
نباید
Execution
نیز متوقف شود.
هر ماژول
Sandbox
خودش را دارد.
---
13.5 Trust Boundary
هر داده
دارای
Trust Level
است.
مثلاً
Exchange API
95
--------------
Internal Cache
98
--------------
Synthetic Data
50
--------------
External News
65
تمام تصمیم‌ها
با توجه به
سطح اعتماد
وزن‌دهی می‌شوند.
---
13.6 Zero Trust Architecture
هیچ داده‌ای
به صورت پیش‌فرض
قابل اعتماد نیست.
حتی
خروجی
ماژول‌های داخلی.
همه چیز
اعتبارسنجی می‌شود.
---
13.7 API Credential Vault
API Key
نباید
داخل
کد
باشد.
نباید
داخل فایل تنظیمات
باشد.
نباید
داخل Log
ثبت شود.
تمام کلیدها
داخل
Vault
رمزنگاری شده
نگهداری می‌شوند.
---
13.8 Encryption Layer
تمام اطلاعات حساس
رمزنگاری می‌شوند.
شامل
API Keys
Secrets
Portfolio
Position History
Optimizer Results
Research Data
Audit Data
---
13.9 Secure Configuration Manager
تمام Configها
دارای Version
هستند.
هیچ Config
Overwrite
نمی‌شود.
هر تغییر
Audit
می‌شود.
---
13.10 Configuration Signature
قبل از اجرا
تمام Configها
Hash
می‌شوند.
اگر
کوچک‌ترین تغییری
رخ دهد.
سیستم
متوجه خواهد شد.
---
13.11 Secure Boot
قبل از شروع معامله
سیستم
چک می‌کند.
Version
Config
Database
Cache
Optimizer
Models
Clock
API
Network
اگر
هر مورد
مشکل داشته باشد.
Live Trading
شروع نمی‌شود.
---
13.12 Session Manager
تمام Sessionها
مدیریت می‌شوند.
شامل
Exchange Session
Optimizer Session
Device Session
User Session
---
13.13 Authentication Manager
تمام ارتباطات
دارای
Authentication
هستند.
هیچ API
بدون
Token
فراخوانی نمی‌شود.
---
13.14 Authorization Layer
هر ماژول
فقط
اجازه دسترسی
به منابع موردنیاز
خود را دارد.
مثلاً
Optimizer
اجازه ارسال Order
ندارد.
---
13.15 Duplicate Order Protection
یکی از مهم‌ترین قسمت‌ها.
قبل از ارسال هر سفارش
سیستم بررسی می‌کند.
آیا
قبلاً
همین سفارش
ارسال شده است؟
اگر
بله.
ارسال
لغو می‌شود.
---
13.16 Idempotency Engine
تمام عملیات
Idempotent
هستند.
اگر
یک درخواست
به دلیل قطعی شبکه
سه بار
ارسال شود.
نباید
سه معامله
باز شود.
---
13.17 Transaction Manager
هر عملیات
داخل
Transaction
انجام می‌شود.
نمونه
Create Order
↓
Send API
↓
Receive Ack
↓
Store Database
↓
Update Portfolio
↓
Commit
اگر
هر مرحله
شکست بخورد.
Rollback
انجام می‌شود.
---
13.18 Rollback Engine
اگر
Config جدید
خراب باشد.
یا
Optimizer
خروجی اشتباه بدهد.
یا
Deployment
ناموفق باشد.
Rollback
به نسخه قبل
انجام می‌شود.
---
13.19 Checkpoint Manager
هر چند دقیقه
Checkpoint
گرفته می‌شود.
شامل
Portfolio
Position
Cache
Models
Scheduler
Optimizer
---
13.20 Disaster Recovery Engine
اگر
گوشی
خاموش شود.
یا
برنامه
کرش کند.
بعد از اجرا
سیستم
از آخرین Checkpoint
بازیابی می‌شود.
---
13.21 Internet Failure Manager
اگر
اینترنت
قطع شود.
سیستم
باید
بداند.
چه کاری انجام دهد.
مثلاً
Continue Monitoring
↓
Cancel Pending Orders
↓
Freeze Optimizer
↓
Keep Risk Engine Alive
↓
Wait Reconnect
---
13.22 Exchange Failure Manager
اگر
صرافی
پاسخ ندهد.
یا
Maintenance
باشد.
سیستم
باید
حالت
Degraded Mode
را فعال کند.
---
13.23 Clock Synchronization
یکی از مواردی که اغلب نادیده گرفته می‌شود.
تمام Timestampها
باید
با زمان صرافی
همگام شوند.
اختلاف ساعت
می‌تواند
باعث:
اشتباه در کندل‌ها
انقضای سفارش
خطای Replay
خطای Backtest
شود.
---
13.24 Persistent Event Store
تمام Eventها
در یک Event Store
غیرقابل تغییر
(Append-Only)
ذخیره می‌شوند.
هیچ Event
ویرایش نمی‌شود.
---
13.25 Audit Ledger
هر تصمیم
هر تغییر
هر پارامتر
هر Deployment
هر Order
هر Exception
ثبت می‌شود.
Audit
باید
غیرقابل تغییر
باشد.
---
13.26 Byzantine Validation (پیشنهاد ارتقای مهم)
برای تصمیم‌های بسیار حساس، می‌توان از چندین ماژول مستقل برای اعتبارسنجی استفاده کرد.
مثلاً:
Probability Engine نسخه A
Probability Engine نسخه B
Rule-Based Validator
اگر نتایج اختلاف زیادی داشته باشند، تصمیم به حالت Review Required می‌رود یا با ریسک کمتر اجرا می‌شود.
این ایده از سامانه‌های تحمل خطای توزیع‌شده الهام گرفته شده و می‌تواند احتمال تصمیم‌های اشتباه ناشی از خرابی یک ماژول را کاهش دهد.
---
13.27 Safe Mode
در صورت بروز خطاهای شدید، سیستم وارد حالت ایمن می‌شود.
در Safe Mode:
معامله جدید باز نمی‌شود.
Positionهای موجود فقط مدیریت می‌شوند.
Optimizerها متوقف می‌شوند.
Research غیرفعال می‌شود.
فقط ماژول‌های حیاتی فعال می‌مانند.
---
13.28 Autonomous Reliability Score
پیشنهاد می‌کنم کل سیستم یک شاخص کلی قابلیت اطمینان نیز داشته باشد.
این امتیاز از ترکیب موارد زیر ساخته می‌شود:
Health همه ماژول‌ها
کیفیت داده
کیفیت اینترنت
کیفیت API
میزان Exception
Drift
مصرف منابع
وضعیت دستگاه
اگر این امتیاز از آستانه مشخصی پایین‌تر بیاید، CDK می‌تواند:
اندازه موقعیت‌ها را کاهش دهد.
Risk Budget را محدود کند.
ورودهای جدید را متوقف کند.
Safe Mode را فعال کند.
---
13.29 خروجی زیرساخت امنیت و قابلیت اطمینان
این لایه خروجی‌های زیر را تولید می‌کند:
Security Status
Reliability Score
Vault Status
Authentication Status
Configuration Integrity Report
Disaster Recovery Status
Checkpoint Status
Rollback Status
Network Health
Exchange Health
Audit Ledger
Event Store
Safe Mode Status
---
پایان فصل سیزدهم
پیشنهاد برای جلد دوم
تا اینجا، معماری APEX تقریباً تمام مؤلفه‌های لازم برای یک Trading Operating System عملیاتی را پوشش می‌دهد. با این حال، اگر هدف رسیدن به سطحی نزدیک به زیرساخت‌های پژوهشی و معاملاتی مؤسسات پیشرفته باشد، جلد دوم می‌تواند بر موضوعاتی متمرکز شود که نیازمند طراحی بسیار عمیق‌تر هستند، از جمله:
Advanced Quantitative Modeling (مدل‌های آماری و احتمالاتی پیشرفته)
Multi-Agent Intelligence (معماری چندعاملی و هماهنگی عامل‌ها)
Online Learning و Bayesian Updating
Reinforcement Learning تحت محدودیت‌های ریسک
Microstructure Modeling برای بازار کریپتو
Portfolio Optimization چندهدفه و پویا
Meta-Optimization Framework برای بهینه‌سازی خود Optimizerها
High-Performance Computing Architecture برای اجرای موازی روی Python
Formal Verification برای اعتبارسنجی منطق تصمیم‌گیری
Self-Evolving Trading System که بتواند معماری و سیاست‌های داخلی خود را به‌صورت کنترل‌شده و قابل‌ممیزی تکامل دهد.
این مباحث از نظر پیچیدگی یک لایه بالاتر از معماری فعلی قرار می‌گیرند و مناسب جلد دوم خواهند بود، در حالی که جلد اول یک بلوپرینت کامل و عملیاتی برای پیاده‌سازی هسته سامانه در Python و اجرای آن در محیطی مانند Termux ارائه می‌دهد.
