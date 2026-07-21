//@version=6
indicator(
     "AICE - Adaptive Institutional Confluence Engine (sina)",
     overlay=true,
     max_lines_count=500,
     max_labels_count=500,
     max_boxes_count=500,
     max_bars_back=5000,
     dynamic_requests=true)

SCRIPT_TITLE = "AICE (sina)"

//──────────────────────────────────────────────────────────────────────
// INPUTS
//──────────────────────────────────────────────────────────────────────
gC = "═══ Core Context ═══"
use_htf       = input.bool(true, "Use HTF Context", group=gC)
macro_tf1     = input.timeframe("60", "Macro TF 1", group=gC)
macro_tf2     = input.timeframe("240", "Macro TF 2", group=gC)

gCrypto = "═══ Crypto Context ═══"
use_crypto_ctx     = input.bool(true, "Use Crypto Market Context", group=gCrypto)
crypto_tf          = input.timeframe("240", "Crypto Context TF", group=gCrypto)
crypto_total_sym   = input.symbol("CRYPTOCAP:TOTAL", "TOTAL", group=gCrypto)
crypto_total2_sym  = input.symbol("CRYPTOCAP:TOTAL2", "TOTAL2", group=gCrypto)
crypto_usdt_d_sym  = input.symbol("CRYPTOCAP:USDT.D", "USDT.D", group=gCrypto)
crypto_btc_d_sym   = input.symbol("CRYPTOCAP:BTC.D", "BTC.D", group=gCrypto)

gN = "═══ Normalization ═══"
norm_win  = input.int(200, "Normalization Window", minval=50, maxval=2000, group=gN)
winsor_z  = input.float(3.0, "Winsor Z Clip", minval=1.5, maxval=6.0, step=0.5, group=gN)

gLearn = "═══ Adaptive Bayesian Learning ═══"
use_adaptive_weights = input.bool(true, "Adaptive Bayesian Feature Weighting", group=gLearn)
feature_prior        = input.float(6.0, "Beta Prior Strength", minval=1.0, maxval=50.0, step=1.0, group=gLearn)
adapt_strength       = input.float(0.65, "Performance Adaptation Strength", minval=0.0, maxval=2.0, step=0.05, group=gLearn)
feature_min_sample   = input.float(25.0, "Feature Sample For Full Trust", minval=5.0, maxval=200.0, step=5.0, group=gLearn)
ic_len               = input.int(200, "Rolling IC Window", minval=50, maxval=1000, group=gLearn)
ic_horizon           = input.int(12, "IC Forward Horizon Bars", minval=2, maxval=100, group=gLearn)
ic_strength          = input.float(0.35, "IC Weight Influence", minval=0.0, maxval=1.0, step=0.05, group=gLearn)

gCal = "═══ Probability Calibration ═══"
use_prob_calibration = input.bool(true, "Bayesian Probability Calibration", group=gCal)
cal_min_sample       = input.float(25.0, "Calibration Bin Sample", minval=5, maxval=200, step=5, group=gCal)
cal_max_blend        = input.float(0.65, "Max Calibration Blend", minval=0.0, maxval=1.0, step=0.05, group=gCal)
use_prob_smoothing   = input.bool(false, "Smooth Probabilities", group=gCal)
prob_smooth_len      = input.int(2, "Probability Smoothing Length", minval=1, maxval=20, group=gCal)

gS = "═══ Structure / SMC ═══"
piv_lb          = input.int(8, "Chart Pivot Lookback", minval=2, maxval=100, group=gS)
int_piv_lb      = input.int(3, "Internal Pivot Lookback", minval=2, maxval=50, group=gS)
ext_piv_lb      = input.int(21, "External Pivot Lookback", minval=5, maxval=150, group=gS)
ob_lb           = input.int(150, "OB Search Depth", minval=20, maxval=1000, group=gS)
ob_scan_cap     = input.int(300, "OB Scan Cap", minval=20, maxval=1000, group=gS)
eq_tol_atr      = input.float(0.10, "Equal High/Low Tolerance ATR", minval=0.01, step=0.01, group=gS)
disp_atr        = input.float(1.20, "Displacement Body ATR", minval=0.3, step=0.1, group=gS)
show_struct     = input.bool(true, "Show Structure / Liquidity", group=gS)
show_zones      = input.bool(true, "Show OB/FVG Zones", group=gS)

gSMT = "═══ Institutional SMT Intelligence Layer ═══"
use_smt        = input.bool(true, "Enable Institutional SMT Layer", group=gSMT)
smt_tf         = input.timeframe("", "SMT TF blank = chart", group=gSMT)
smt_piv_lb     = input.int(5, "SMT Pivot Lookback", minval=2, maxval=50, group=gSMT)
smt_max_age    = input.int(10, "Max SMT Pivot Age", minval=1, maxval=80, group=gSMT)
smt_crypto_only = input.bool(true, "Crypto Only SMT Engine", group=gSMT)

smt_pair_mode = input.string(
     "Auto Crypto Pair Manager",
     "Pair Manager Mode",
     options=["Auto Crypto Pair Manager", "Manual Symbols"],
     group=gSMT)

smt_auto_profile = input.string(
     "Major Basket",
     "Auto Crypto SMT Profile",
     options=[
         "Major Basket",
         "BTC ⇄ ETH",
         "BTC ⇄ TOTAL",
         "ETH ⇄ TOTAL2",
         "Dominance Context"
     ],
     group=gSMT)

smt_btc_sym    = input.symbol("BINANCE:BTCUSDT", "BTCUSDT", group=gSMT)
smt_eth_sym    = input.symbol("BINANCE:ETHUSDT", "ETHUSDT", group=gSMT)
smt_bnb_sym    = input.symbol("BINANCE:BNBUSDT", "BNBUSDT", group=gSMT)
smt_sol_sym    = input.symbol("BINANCE:SOLUSDT", "SOLUSDT", group=gSMT)
smt_xrp_sym    = input.symbol("BINANCE:XRPUSDT", "XRPUSDT", group=gSMT)
smt_total_sym  = input.symbol("CRYPTOCAP:TOTAL", "TOTAL", group=gSMT)
smt_total2_sym = input.symbol("CRYPTOCAP:TOTAL2", "TOTAL2", group=gSMT)
smt_usdt_d_sym = input.symbol("CRYPTOCAP:USDT.D", "USDT.D", group=gSMT)
smt_btc_d_sym  = input.symbol("CRYPTOCAP:BTC.D", "BTC.D", group=gSMT)

smt_sym1 = input.symbol("BINANCE:BTCUSDT", "Manual SMT Symbol 1", group=gSMT)
smt_sym2 = input.symbol("BINANCE:ETHUSDT", "Manual SMT Symbol 2", group=gSMT)
smt_sym3 = input.symbol("CRYPTOCAP:TOTAL", "Manual SMT Symbol 3", group=gSMT)

smt_inv1 = input.bool(false, "Manual Symbol 1 Is Inverse", group=gSMT)
smt_inv2 = input.bool(false, "Manual Symbol 2 Is Inverse", group=gSMT)
smt_inv3 = input.bool(false, "Manual Symbol 3 Is Inverse", group=gSMT)

smt_dom_inverse = input.bool(true, "Treat Dominance Symbols As Inverse", group=gSMT)
smt_corr_len       = input.int(120, "Rolling Correlation Length", minval=20, maxval=1000, group=gSMT)
smt_corr_min       = input.float(0.60, "Minimum Correlation / Abs-Correlation", minval=0.10, maxval=0.95, step=0.01, group=gSMT)
smt_corr_slope_len = input.int(34, "Dynamic Correlation Slope Length", minval=5, maxval=300, group=gSMT)
smt_min_score    = input.float(0.35, "Minimum SMT Strength Score", minval=0.05, maxval=0.95, step=0.01, group=gSMT)
smt_decay_rate   = input.float(0.985, "SMT Decay Rate", minval=0.90, maxval=1.0, step=0.001, group=gSMT)
smt_entry_window = input.int(8, "Institutional Entry Window Bars", minval=1, maxval=50, group=gSMT)
smt_zone_lookback = input.int(80, "SMT FVG / OB Proxy Lookback", minval=10, maxval=500, group=gSMT)
smt_merge_bars = input.int(10, "SMT Merge Window Bars", minval=1, maxval=100, group=gSMT)
smt_merge_atr  = input.float(0.80, "SMT Merge Distance ATR", minval=0.10, maxval=5.0, step=0.05, group=gSMT)
smt_event_max_age = input.int(80, "SMT Lifecycle Max Age", minval=5, maxval=500, group=gSMT)
smt_event_cap     = input.int(30, "Max SMT Lifecycle Events", minval=5, maxval=100, group=gSMT)
smt_failure_atr   = input.float(0.45, "SMT Failure ATR Break", minval=0.10, maxval=3.0, step=0.05, group=gSMT)
smt_show_events = input.bool(true, "Show Institutional SMT Labels", group=gSMT)

gK = "═══ Kinetic / Momentum ═══"
wt_ch   = input.int(10, "WaveTrend Channel", minval=3, group=gK)
wt_avg  = input.int(21, "WaveTrend Average", minval=3, group=gK)
stc_len = input.int(48, "STC Cycle", minval=10, group=gK)
stc_fast = input.int(23, "STC Fast", minval=5, group=gK)
stc_slow = input.int(50, "STC Slow", minval=10, group=gK)
cci_len = input.int(20, "CCI Length", minval=5, group=gK)

gV = "═══ Volume / Volatility / Profile ═══"
atr_len       = input.int(14, "ATR Length", minval=5, group=gV)
rank_len      = input.int(200, "Volatility Rank Period", minval=50, maxval=2000, group=gV)
use_rvol_gate = input.bool(true, "Use RVOL Gate", group=gV)
rvol_cut      = input.float(1.5, "RVOL Cutoff", minval=1.0, step=0.1, group=gV)
min_atr_pct   = input.float(0.01, "Minimum ATR %", minval=0.0, step=0.01, group=gV)
max_atr_pct   = input.float(5.0, "Maximum ATR %", minval=0.1, step=0.1, group=gV)
use_volume_profile = input.bool(true, "Rolling Volume Profile Approximation", group=gV)
vp_len        = input.int(96, "VP Lookback Bars", minval=30, maxval=250, group=gV)
vp_bins       = input.int(16, "VP Bins", minval=6, maxval=32, group=gV)
vol_fc_len    = input.int(50, "EWMA Vol Forecast Length", minval=10, maxval=300, group=gV)
use_adaptive_atr = input.bool(true, "Adaptive ATR Risk Model", group=gV)

gReg = "═══ Regime / Oracle ═══"
adx_len       = input.int(14, "ADX Length", minval=5, group=gReg)
adx_trend     = input.float(23.0, "ADX Trend Threshold", minval=10, group=gReg)
er_len        = input.int(20, "Efficiency Ratio Length", minval=5, group=gReg)
hurst_len     = input.int(50, "Hurst / Entropy Window", minval=20, maxval=500, group=gReg)
use_entropy_standby = input.bool(true, "Use Entropy Standby", group=gReg)
entropy_max   = input.float(0.78, "Maximum Entropy", minval=0.40, maxval=0.98, step=0.01, group=gReg)
use_oracle_filter = input.bool(true, "Use Failure-Risk Oracle", group=gReg)
oracle_fail_max = input.float(0.72, "Max Oracle Failure Risk", minval=0.40, maxval=0.95, step=0.01, group=gReg)
use_equity_guard = input.bool(true, "Virtual Equity Guard", group=gReg)
equity_guard_min_trades = input.int(12, "Equity Guard Min Trades", minval=1, group=gReg)
equity_guard_ma_len = input.int(50, "Equity Guard EMA", minval=5, maxval=300, group=gReg)

gKalman = "═══ Zero Lag / Kalman Filters ═══"
zpf_fast_len             = input.int(12, "ZPF Fast Length", group=gKalman)
zpf_slow_len             = input.int(26, "ZPF Slow Length", group=gKalman)
kalman_q_base            = input.float(0.01, "Kalman Q Process Noise", group=gKalman)
kalman_r_base            = input.float(1.0, "Kalman R Measurement Noise", group=gKalman)
use_kalman_signal_filter = input.bool(true, "Use Kalman Signal Filter", group=gKalman)

gO = "═══ Object Lifecycle ═══"
ob_decay        = input.float(0.985, "OB Decay", minval=0.90, maxval=1.0, step=0.001, group=gO)
fvg_decay       = input.float(0.975, "FVG Decay", minval=0.90, maxval=1.0, step=0.001, group=gO)
liq_decay       = input.float(0.990, "Liquidity Decay", minval=0.90, maxval=1.0, step=0.001, group=gO)
max_live_objects = input.int(12, "Max Live OB/FVG Per Side", minval=1, maxval=50, group=gO)
max_object_age   = input.int(300, "Max Object Age", minval=20, maxval=2000, group=gO)
min_fvg_atr      = input.float(0.05, "Minimum FVG ATR", minval=0.0, step=0.01, group=gO)

gExec = "═══ Execution / Expectancy ═══"
prob_threshold = input.float(0.62, "Probability Threshold", minval=0.5, maxval=0.95, step=0.01, group=gExec)
prob_edge      = input.float(0.03, "Minimum L/S Probability Edge", minval=0.0, maxval=0.30, step=0.01, group=gExec)
unc_max        = input.float(0.45, "Maximum Uncertainty", minval=0.1, maxval=0.9, step=0.05, group=gExec)
exec_profile   = input.string("Balanced", "Execution Profile", options=["Aggressive", "Balanced", "Conservative"], group=gExec)
exec_timing    = input.string("Retest + Micro BOS", "Execution Timing", options=["Immediate", "Trigger Candle", "Retest + Micro BOS"], group=gExec)
pending_max_bars = input.int(12, "Pending Setup Max Bars", minval=1, maxval=100, group=gExec)
micro_bos_len  = input.int(3, "Micro BOS Length", minval=2, maxval=20, group=gExec)
trigger_close_loc = input.float(0.62, "Trigger Close Location", minval=0.50, maxval=0.95, step=0.01, group=gExec)
sl_mult        = input.float(2.0, "ATR Stop Base", minval=0.5, step=0.1, group=gExec)
tp_mult        = input.float(3.5, "ATR TP Reference", minval=0.5, step=0.1, group=gExec)
sl_model       = input.string("Structure Hybrid", "Stop Model", options=["ATR", "Structure Hybrid"], group=gExec)
use_liquidity_targets = input.bool(true, "Use Liquidity Target Resolver", group=gExec)
cooldown       = input.int(24, "Cooldown Bars", minval=0, group=gExec)
min_contributors = input.int(3, "Minimum Evidence Contributors", minval=1, maxval=13, group=gExec)
use_expectancy_gate = input.bool(true, "Use Expected-R Gate", group=gExec)
min_expected_R = input.float(0.10, "Minimum Expected R", minval=-1.0, maxval=3.0, step=0.05, group=gExec)
min_expected_edge_R = input.float(0.03, "Minimum Expected-R Edge", minval=0.0, maxval=1.0, step=0.01, group=gExec)
fee_slippage_R = input.float(0.02, "Fee/Slippage Cost in R", minval=0.0, maxval=0.5, step=0.01, group=gExec)
conservative_resolver = input.bool(true, "Conservative TP/SL Same-Bar Resolver", group=gExec)
riskPct        = input.float(1.0, "Risk Per Trade (%)", minval=0.1, maxval=10.0, step=0.1, group=gExec)

gCluster = "═══ Signal Clustering ═══"
use_similarity_cooldown = input.bool(true, "Feature-Similarity Cooldown", group=gCluster)
similarity_threshold = input.float(0.88, "Similarity Threshold", minval=0.50, maxval=0.99, step=0.01, group=gCluster)
similar_cooldown = input.int(60, "Similar Signal Cooldown Bars", minval=1, maxval=500, group=gCluster)

gD = "═══ Display ═══"
show_dash   = input.bool(true, "Show Dashboard", group=gD)
show_attr   = input.bool(true, "Show Feature Importance", group=gD)
dash_pos_opt = input.string("Top Right", "Dashboard Position", options=["Top Left", "Top Right", "Bottom Left", "Bottom Right"], group=gD)
attr_pos_opt = input.string("Bottom Right", "Attribution Position", options=["Top Left", "Top Right", "Bottom Left", "Bottom Right"], group=gD)
show_sig    = input.bool(true, "Show Signal Arrows", group=gD)
show_tag    = input.bool(true, "Show Setup Tags", group=gD)
show_tpsl   = input.bool(true, "Show TP/SL Grid", group=gD)

gStyle = "═══ Style ═══"
bull_col = input.color(color.rgb(16, 185, 129), "Bull Color (Subtle Emerald)", group=gStyle)
bear_col = input.color(color.rgb(244, 63, 94), "Bear Color (Subtle Crimson)", group=gStyle)
warn_col = input.color(color.rgb(245, 158, 11), "Warn Color (Subtle Amber)", group=gStyle)
info_col = input.color(color.rgb(14, 165, 233), "Info Color (Subtle Sky)", group=gStyle)
text_col = input.color(color.rgb(241, 245, 249), "Text Color", group=gStyle)
dash_bg  = input.color(color.rgb(15, 23, 42), "Dashboard BG", group=gStyle)
dash_header_bg = input.color(color.rgb(2, 6, 23), "Dashboard Header BG", group=gStyle)
zone_forward_bars = input.int(60, "Zone Forward Bars", minval=1, maxval=300, group=gStyle)

//──────────────────────────────────────────────────────────────────────
// HELPERS
//──────────────────────────────────────────────────────────────────────
f_table_pos(_p) =>
    switch _p
        "Top Left" => position.top_left
        "Top Right" => position.top_right
        "Bottom Left" => position.bottom_left
        "Bottom Right" => position.bottom_right
        => position.top_right

f_cell(_t, _c, _r, _txt, _bg, _tc) =>
    table.cell(_t, _c, _r, _txt, bgcolor=_bg, text_color=_tc, text_size=size.tiny, text_font_family=font.family_monospace)

f_clamp(x, lo, hi) =>
    xx = na(x) ? (lo + hi) / 2.0 : x
    math.max(math.min(xx, hi), lo)

f_squash(x) =>
    1.0 / (1.0 + math.exp(-nz(x, 0.0)))

f_pct(src, len) =>
    pr = ta.percentrank(src, len)
    na(pr) ? 0.5 : pr / 100.0

f_minmax(src, len) =>
    lo = ta.lowest(src, len)
    hi = ta.highest(src, len)
    rng = hi - lo
    not na(rng) and rng > 0 ? (src - lo) / rng : 0.5

f_zrobust(src, len) =>
    m = ta.sma(src, len)
    sd = ta.stdev(src, len)
    z = not na(m) and not na(sd) and sd > 0 ? (src - m) / sd : 0.0
    f_clamp(z, -winsor_z, winsor_z)

f_entropy01(p) =>
    pc = f_clamp(p, 0.0001, 0.9999)
    -(pc * math.log(pc) + (1.0 - pc) * math.log(1.0 - pc)) / math.log(2.0)

f_zpf(src, len) =>
    e1 = ta.ema(src, len)
    e2 = ta.ema(e1, len)
    e1 + (e1 - e2)

f_delete_box(_bx) =>
    if not na(_bx)
        box.delete(_bx)
    0

f_delete_line(_ln) =>
    if not na(_ln)
        line.delete(_ln)
    0

f_delete_label(_lb) =>
    if not na(_lb)
        label.delete(_lb)
    0

f_zone_box(_left, _top, _right, _bottom, _border, _bg, _txt) =>
    box.new(
         left=_left,
         top=_top,
         right=_right,
         bottom=_bottom,
         xloc=xloc.bar_index,
         border_color=_border,
         border_width=1,
         bgcolor=_bg,
         text=_txt,
         text_color=text_col,
         text_size=size.tiny,
         text_font_family=font.family_monospace,
         text_halign=text.align_left,
         text_valign=text.align_center)

f_update_zone(_bx, _right, _txt, _border, _bg) =>
    if not na(_bx)
        box.set_right(_bx, _right)
        box.set_text(_bx, _txt)
        box.set_border_color(_bx, _border)
        box.set_bgcolor(_bx, _bg)
    0

f_clean_setup(_s) =>
    x = str.replace_all(_s, " Long", "")
    x := str.replace_all(x, " Short", "")
    x

f_crypto_bias_expr() =>
    f = ta.ema(close, 20)
    s = ta.ema(close, 50)
    close > s and f > s ? 1 : close < s and f < s ? -1 : 0

f_crypto_inverse_bias_expr() =>
    f = ta.ema(close, 20)
    s = ta.ema(close, 50)
    close < s and f < s ? 1 : close > s and f > s ? -1 : 0

f_struct_pack(_lb) =>
    _ph = ta.pivothigh(high, _lb, _lb)
    _pl = ta.pivotlow(low, _lb, _lb)
    _lastPH = ta.valuewhen(not na(_ph), _ph, 0)
    _lastPL = ta.valuewhen(not na(_pl), _pl, 0)
    _ema = ta.ema(close, 50)
    _bias = not na(_lastPH) and close > _lastPH ? 1 : not na(_lastPL) and close < _lastPL ? -1 : close > _ema ? 1 : close < _ema ? -1 : 0
    _eq = not na(_lastPH) and not na(_lastPL) ? (_lastPH + _lastPL) / 2.0 : na
    _hi = ta.highest(high, _lb * 8)[1]
    _lo = ta.lowest(low, _lb * 8)[1]
    [_bias, _eq, _hi, _lo]

f_smt_pack(_lb) =>
    _ph = ta.pivothigh(high, _lb, _lb)
    _pl = ta.pivotlow(low, _lb, _lb)
    _lp = ta.valuewhen(not na(_pl), _pl, 0)
    _pp = ta.valuewhen(not na(_pl), _pl, 1)
    _lh = ta.valuewhen(not na(_ph), _ph, 0)
    _phh = ta.valuewhen(not na(_ph), _ph, 1)
    _plAgeI = ta.barssince(not na(_pl))
    _phAgeI = ta.barssince(not na(_ph))
    _plAge = na(_plAgeI) ? na : _plAgeI * 1.0
    _phAge = na(_phAgeI) ? na : _phAgeI * 1.0
    [_lp, _pp, _lh, _phh, _plAge, _phAge]

f_smt_bull(_clp, _cpp, _rlp, _rpp, _cAge, _rAge, _maxAge) =>
    ok = not na(_clp) and not na(_cpp) and not na(_rlp) and not na(_rpp) and not na(_cAge) and not na(_rAge) and _cAge <= _maxAge and _rAge <= _maxAge
    ok and ((_clp < _cpp and _rlp >= _rpp) or (_clp >= _cpp and _rlp < _rpp))

f_smt_bear(_clh, _cph, _rlh, _rph, _cAge, _rAge, _maxAge) =>
    ok = not na(_clh) and not na(_cph) and not na(_rlh) and not na(_rph) and not na(_cAge) and not na(_rAge) and _cAge <= _maxAge and _rAge <= _maxAge
    ok and ((_clh > _cph and _rlh <= _rph) or (_clh <= _cph and _rlh > _rph))

f_stc(src, fast, slow, cyc) =>
    ml = ta.ema(src, fast) - ta.ema(src, slow)
    k = ta.stoch(ml, ml, ml, cyc)
    var float d = na
    d := na(d[1]) ? k : d[1] + 0.5 * (k - d[1])
    kd = ta.stoch(d, d, d, cyc)
    var float st = na
    st := na(st[1]) ? kd : st[1] + 0.5 * (kd - st[1])
    f_clamp(nz(st, 50.0), 0.0, 100.0)

f_ic(_feat, _h, _len) =>
    _ret = not na(close[_h]) and close[_h] != 0.0 ? close / close[_h] - 1.0 : 0.0
    nz(ta.correlation(_feat[_h], _ret, _len), 0.0)

f_cos13(
     a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12,
     b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12) =>
    dot = a0*b0 + a1*b1 + a2*b2 + a3*b3 + a4*b4 + a5*b5 + a6*b6 + a7*b7 + a8*b8 + a9*b9 + a10*b10 + a11*b11 + a12*b12
    n1 = a0*a0 + a1*a1 + a2*a2 + a3*a3 + a4*a4 + a5*a5 + a6*a6 + a7*a7 + a8*a8 + a9*a9 + a10*a10 + a11*a11 + a12*a12
    n2 = b0*b0 + b1*b1 + b2*b2 + b3*b3 + b4*b4 + b5*b5 + b6*b6 + b7*b7 + b8*b8 + b9*b9 + b10*b10 + b11*b11 + b12*b12
    n1 > 0 and n2 > 0 ? dot / (math.sqrt(n1) * math.sqrt(n2)) : 0.0

f_feat_name(_i) =>
    switch _i
        0 => "Structure"
        1 => "Liquidity"
        2 => "Order Block"
        3 => "FVG"
        4 => "Zone"
        5 => "Candle DNA"
        6 => "Kinetic"
        7 => "Delta/Volume"
        8 => "Sequence"
        9 => "Trend/VWAP/Kalman"
        10 => "Nested MTF"
        11 => "Institutional SMT"
        12 => "Profile/Session"
        => "Unknown"

//──────────────────────────────────────────────────────────────────────
// INSTITUTIONAL SMT HELPERS
//──────────────────────────────────────────────────────────────────────
f_xor(_a, _b) =>
    (_a and not _b) or (not _a and _b)

f_smt_is_dom(_sym) =>
    str.contains(_sym, "USDT.D") or str.contains(_sym, "BTC.D")

f_smt_corr_q(_corr, _minCorr) =>
    ca = math.abs(nz(_corr, 0.0))
    f_clamp((ca - _minCorr) / math.max(1.0 - _minCorr, 0.0001), 0.0, 1.0)

f_smt_conf_label(_s) =>
    _s >= 0.80 ? "Institutional" :
     _s >= 0.65 ? "Strong" :
     _s >= 0.48 ? "Medium" :
     _s >= 0.30 ? "Weak" : "Very Weak"

f_smt_state_name(_s) =>
    switch _s
        0 => "Detected"
        1 => "Waiting"
        2 => "Confirmed"
        3 => "Triggered"
        4 => "Mitigated"
        5 => "Broken"
        6 => "Archived"
        => "Unknown"

f_smt_type_name(_id) =>
    switch _id
        1 => "Classic SMT"
        2 => "Hidden SMT"
        3 => "Reverse SMT"
        4 => "Simple SMT"
        5 => "Liquidity SMT"
        6 => "Stop Hunt SMT"
        7 => "FVG SMT"
        8 => "Order Block SMT"
        9 => "CHOCH SMT"
        10 => "BOS SMT"
        11 => "Inducement SMT"
        12 => "Premium SMT"
        13 => "Discount SMT"
        14 => "Internal SMT"
        15 => "External SMT"
        => "No SMT"

f_smt_inst_pack(_lb) =>
    _atr = ta.atr(atr_len)

    _ph = ta.pivothigh(high, _lb, _lb)
    _pl = ta.pivotlow(low, _lb, _lb)

    _lp  = ta.valuewhen(not na(_pl), _pl, 0)
    _pp  = ta.valuewhen(not na(_pl), _pl, 1)
    _lh  = ta.valuewhen(not na(_ph), _ph, 0)
    _phh = ta.valuewhen(not na(_ph), _ph, 1)

    _plAgeI = ta.barssince(not na(_pl))
    _phAgeI = ta.barssince(not na(_ph))

    _plAge = na(_plAgeI) ? na : _plAgeI * 1.0
    _phAge = na(_phAgeI) ? na : _phAgeI * 1.0

    _highest_val = ta.highest(high, _lb * 2 + 1)
    _lowest_val = ta.lowest(low, _lb * 2 + 1)

    _plStrNow = not na(_pl) and _atr > 0 ? f_clamp((_highest_val - _pl) / (_atr * 2.0), 0.0, 1.0) : na
    _phStrNow = not na(_ph) and _atr > 0 ? f_clamp((_ph - _lowest_val) / (_atr * 2.0), 0.0, 1.0) : na

    _plStr = ta.valuewhen(not na(_pl), _plStrNow, 0)
    _phStr = ta.valuewhen(not na(_ph), _phStrNow, 0)

    _lpAtr = not na(_lp) and not na(_pp) and _atr > 0 ? math.abs(_lp - _pp) / _atr : 0.0
    _lhAtr = not na(_lh) and not na(_phh) and _atr > 0 ? math.abs(_lh - _phh) / _atr : 0.0

    _sweepLow  = not na(_lp) and low < _lp and close > _lp
    _sweepHigh = not na(_lh) and high > _lh and close < _lh

    _eqLow  = not na(_pl) and not na(_pp) and _atr > 0 and math.abs(_pl - _pp) <= _atr * eq_tol_atr
    _eqHigh = not na(_ph) and not na(_phh) and _atr > 0 and math.abs(_ph - _phh) <= _atr * eq_tol_atr

    _bullFvgRaw = not na(high[2]) and low > high[2]
    _bearFvgRaw = not na(low[2]) and high < low[2]

    _bfTop = ta.valuewhen(_bullFvgRaw, low, 0)
    _bfBot = ta.valuewhen(_bullFvgRaw, high[2], 0)
    _bfAge = ta.barssince(_bullFvgRaw)
    _inBullFvg = not na(_bfAge) and _bfAge <= smt_zone_lookback and not na(_bfTop) and not na(_bfBot) and low <= _bfTop and high >= _bfBot

    _sfTop = ta.valuewhen(_bearFvgRaw, low[2], 0)
    _sfBot = ta.valuewhen(_bearFvgRaw, high, 0)
    _sfAge = ta.barssince(_bearFvgRaw)
    _inBearFvg = not na(_sfAge) and _sfAge <= smt_zone_lookback and not na(_sfTop) and not na(_sfBot) and high >= _sfBot and low <= _sfTop

    _body = math.abs(close - open)
    _bodyAtr = _atr > 0 ? _body / _atr : 0.0

    _bullObEvent = close[1] < open[1] and close > high[1] and _bodyAtr >= disp_atr * 0.55
    _bearObEvent = close[1] > open[1] and close < low[1] and _bodyAtr >= disp_atr * 0.55

    _boTop = ta.valuewhen(_bullObEvent, high[1], 0)
    _boBot = ta.valuewhen(_bullObEvent, low[1], 0)
    _boAge = ta.barssince(_bullObEvent)
    _inBullOb = not na(_boAge) and _boAge <= smt_zone_lookback and not na(_boTop) and not na(_boBot) and low <= _boTop and high >= _boBot

    _soTop = ta.valuewhen(_bearObEvent, high[1], 0)
    _soBot = ta.valuewhen(_bearObEvent, low[1], 0)
    _soAge = ta.barssince(_bearObEvent)
    _inBearOb = not na(_soAge) and _soAge <= smt_zone_lookback and not na(_soTop) and not na(_soBot) and high >= _soBot and low <= _soTop

    _ema = ta.ema(close, 50)
    _bias = not na(_lh) and close > _lh ? 1.0 : not na(_lp) and close < _lp ? -1.0 : close > _ema ? 1.0 : close < _ema ? -1.0 : 0.0

    _rngTop = not na(_lh) and not na(_lp) ? math.max(_lh, _lp) : na
    _rngBot = not na(_lh) and not na(_lp) ? math.min(_lh, _lp) : na
    _rng = not na(_rngTop) and not na(_rngBot) ? _rngTop - _rngBot : na
    _pos = not na(_rng) and _rng > 0 ? f_clamp((close - _rngBot) / _rng, 0.0, 1.0) : 0.5

    _ret = close > 0 and close[1] > 0 ? math.log(close / close[1]) : 0.0

    [
         close,
         _ret,
         _lp,
         _pp,
         _lh,
         _phh,
         _plAge,
         _phAge,
         nz(_plStr, 0.0),
         nz(_phStr, 0.0),
         nz(_lpAtr, 0.0),
         nz(_lhAtr, 0.0),
         _sweepLow ? 1.0 : 0.0,
         _sweepHigh ? 1.0 : 0.0,
         _eqLow ? 1.0 : 0.0,
         _eqHigh ? 1.0 : 0.0,
         _inBullFvg ? 1.0 : 0.0,
         _inBearFvg ? 1.0 : 0.0,
         _inBullOb ? 1.0 : 0.0,
         _inBearOb ? 1.0 : 0.0,
         _bias,
         _pos
     ]

f_smt_eval_ref(
     _enabled,
     _corrQ,
     _inverse,

     _c_lp,
     _c_pp,
     _c_lh,
     _c_phh,
     _c_pl_age,
     _c_ph_age,

     _r_lp,
     _r_pp,
     _r_lh,
     _r_phh,
     _r_pl_age,
     _r_ph_age,

     _r_sweepLow,
     _r_sweepHigh,
     _r_eqLow,
     _r_eqHigh,
     _r_fvgBull,
     _r_fvgBear,
     _r_obBull,
     _r_obBear,

     _liqL,
     _liqS,
     _sweepL,
     _sweepS,
     _stopL,
     _stopS,
     _structL,
     _structS,
     _fvgL,
     _fvgS,
     _obL,
     _obS,
     _trendL,
     _trendS,
     _htfL,
     _htfS,
     _cryptoL,
     _cryptoS,
     _candleL,
     _candleS,
     _pdL,
     _pdS,
     _internalL,
     _internalS,
     _externalL,
     _externalS,

     _maxAge,
     _decayRate,
     _entryWindow,
     _regimeMult) =>

    _rDownAge = _inverse ? _r_ph_age : _r_pl_age
    _rUpAge   = _inverse ? _r_pl_age : _r_ph_age

    _validBull =
         _enabled and
         _corrQ > 0 and
         not na(_c_lp) and not na(_c_pp) and
         not na(_r_lp) and not na(_r_pp) and not na(_r_lh) and not na(_r_phh) and
         not na(_c_pl_age) and not na(_rDownAge) and
         _c_pl_age <= _maxAge and _rDownAge <= _maxAge

    _validBear =
         _enabled and
         _corrQ > 0 and
         not na(_c_lh) and not na(_c_phh) and
         not na(_r_lp) and not na(_r_pp) and not na(_r_lh) and not na(_r_phh) and
         not na(_c_ph_age) and not na(_rUpAge) and
         _c_ph_age <= _maxAge and _rUpAge <= _maxAge

    _cDown = _c_lp < _c_pp
    _cHL   = _c_lp >= _c_pp
    _cUp   = _c_lh > _c_phh
    _cLH   = _c_lh <= _c_phh

    _rDown = _inverse ? _r_lh > _r_phh : _r_lp < _r_pp
    _rUp   = _inverse ? _r_lp < _r_pp : _r_lh > _r_phh

    _rSweepDown = _inverse ? _r_sweepHigh > 0.5 : _r_sweepLow > 0.5
    _rSweepUp   = _inverse ? _r_sweepLow > 0.5 : _r_sweepHigh > 0.5

    _rEqDown = _inverse ? _r_eqHigh > 0.5 : _r_eqLow > 0.5
    _rEqUp   = _inverse ? _r_eqLow > 0.5 : _r_eqHigh > 0.5

    _rFvgBullEff = _inverse ? _r_fvgBear > 0.5 : _r_fvgBull > 0.5
    _rFvgBearEff = _inverse ? _r_fvgBull > 0.5 : _r_fvgBear > 0.5

    _rObBullEff = _inverse ? _r_obBear > 0.5 : _r_obBull > 0.5
    _rObBearEff = _inverse ? _r_obBull > 0.5 : _r_obBear > 0.5

    // 1. Classic SMT
    _classicBull = _validBull and ((_cDown and not _rDown) or (not _cDown and _rDown))
    _classicBear = _validBear and ((_cUp and not _rUp) or (not _cUp and _rUp))

    // 2. Hidden SMT
    _hiddenBull = _validBull and _cHL and _rDown and _trendL > 0.35
    _hiddenBear = _validBear and _cLH and _rUp and _trendS > 0.35

    // 3. Reverse SMT
    _reverseBull = _validBull and not _cDown and _rDown and _liqL > 0.25
    _reverseBear = _validBear and not _cUp and _rUp and _liqS > 0.25

    // 4. Simple SMT
    _simpleBull = _classicBull or _hiddenBull or _reverseBull
    _simpleBear = _classicBear or _hiddenBear or _reverseBear

    // 5. Liquidity SMT
    _liqBull = _simpleBull and (_sweepL > 0.35 or _rSweepDown)
    _liqBear = _simpleBear and (_sweepS > 0.35 or _rSweepUp)

    // 6. Stop Hunt SMT
    _stopBull = _simpleBull and (_stopL > 0.5 or _rEqDown)
    _stopBear = _simpleBear and (_stopS > 0.5 or _rEqUp)

    // 7. FVG SMT
    _fvgBull = _simpleBull and f_xor(_fvgL > 0.35, _rFvgBullEff)
    _fvgBear = _simpleBear and f_xor(_fvgS > 0.35, _rFvgBearEff)

    // 8. OB SMT
    _obBull = _simpleBull and f_xor(_obL > 0.35, _rObBullEff)
    _obBear = _simpleBear and f_xor(_obS > 0.35, _rObBearEff)

    // 9. CHOCH SMT
    _chochBull = _simpleBull and _structL > 0.55
    _chochBear = _simpleBear and _structS > 0.55

    // 10. BOS SMT
    _bosBull = _simpleBull and _structL > 0.35
    _bosBear = _simpleBear and _structS > 0.35

    // 11. Inducement SMT
    _indBull = _simpleBull and _liqL > 0.60 and _structL > 0.25
    _indBear = _simpleBear and _liqS > 0.60 and _structS > 0.25

    // 12 / 13. Premium / Discount SMT
    _discBull = _simpleBull and _pdL > 0.45
    _premBear = _simpleBear and _pdS > 0.45

    // 14. Internal SMT
    _intBull = _simpleBull and _internalL > 0.45
    _intBear = _simpleBear and _internalS > 0.45

    // 15. External SMT
    _extBull = _simpleBull and _externalL > 0.45
    _extBear = _simpleBear and _externalS > 0.45

    _bullTypeScore = 0.0
    _bullTypeScore += _classicBull ? 0.16 : 0.0
    _bullTypeScore += _hiddenBull ? 0.08 : 0.0
    _bullTypeScore += _reverseBull ? 0.07 : 0.0
    _bullTypeScore += _simpleBull ? 0.04 : 0.0
    _bullTypeScore += _liqBull ? 0.11 : 0.0
    _bullTypeScore += _stopBull ? 0.09 : 0.0
    _bullTypeScore += _fvgBull ? 0.08 : 0.0
    _bullTypeScore += _obBull ? 0.08 : 0.0
    _bullTypeScore += _chochBull ? 0.08 : 0.0
    _bullTypeScore += _bosBull ? 0.05 : 0.0
    _bullTypeScore += _indBull ? 0.06 : 0.0
    _bullTypeScore += _discBull ? 0.05 : 0.0
    _bullTypeScore += _intBull ? 0.04 : 0.0
    _bullTypeScore += _extBull ? 0.06 : 0.0
    _bullTypeScore := f_clamp(_bullTypeScore, 0.0, 1.0)

    _bearTypeScore = 0.0
    _bearTypeScore += _classicBear ? 0.16 : 0.0
    _bearTypeScore += _hiddenBear ? 0.08 : 0.0
    _bearTypeScore += _reverseBear ? 0.07 : 0.0
    _bearTypeScore += _simpleBear ? 0.04 : 0.0
    _bearTypeScore += _liqBear ? 0.11 : 0.0
    _bearTypeScore += _stopBear ? 0.09 : 0.0
    _bearTypeScore += _fvgBear ? 0.08 : 0.0
    _bearTypeScore += _obBear ? 0.08 : 0.0
    _bearTypeScore += _chochBear ? 0.08 : 0.0
    _bearTypeScore += _bosBear ? 0.05 : 0.0
    _bearTypeScore += _indBear ? 0.06 : 0.0
    _bearTypeScore += _premBear ? 0.05 : 0.0
    _bearTypeScore += _intBear ? 0.04 : 0.0
    _bearTypeScore += _extBear ? 0.06 : 0.0
    _bearTypeScore := f_clamp(_bearTypeScore, 0.0, 1.0)

    _probBull =
         _corrQ * 0.15 +
         _liqL * 0.20 +
         _sweepL * 0.15 +
         _structL * 0.15 +
         _fvgL * 0.10 +
         _obL * 0.10 +
         _trendL * 0.05 +
         _htfL * 0.05 +
         _cryptoL * 0.05

    _probBear =
         _corrQ * 0.15 +
         _liqS * 0.20 +
         _sweepS * 0.15 +
         _structS * 0.15 +
         _fvgS * 0.10 +
         _obS * 0.10 +
         _trendS * 0.05 +
         _htfS * 0.05 +
         _cryptoS * 0.05

    _ageBull = math.min(nz(_c_pl_age, 999.0), nz(_rDownAge, 999.0))
    _ageBear = math.min(nz(_c_ph_age, 999.0), nz(_rUpAge, 999.0))

    _decBull = math.pow(_decayRate, _ageBull)
    _decBear = math.pow(_decayRate, _ageBear)

    _winBull = _ageBull <= _entryWindow ? 1.08 : 0.92
    _winBear = _ageBear <= _entryWindow ? 1.08 : 0.92

    _bullScore =
         _simpleBull ?
         f_clamp(
             (_probBull * 0.68 + _bullTypeScore * 0.32) *
             (0.70 + _candleL * 0.30) *
             _decBull *
             _winBull *
             _regimeMult,
             0.0,
             1.0) :
         0.0

    _bearScore =
         _simpleBear ?
         f_clamp(
             (_probBear * 0.68 + _bearTypeScore * 0.32) *
             (0.70 + _candleS * 0.30) *
             _decBear *
             _winBear *
             _regimeMult,
             0.0,
             1.0) :
         0.0

    int _bullTypeId = 0
    if _stopBull
        _bullTypeId := 6
    else if _liqBull
        _bullTypeId := 5
    else if _fvgBull
        _bullTypeId := 7
    else if _obBull
        _bullTypeId := 8
    else if _chochBull
        _bullTypeId := 9
    else if _bosBull
        _bullTypeId := 10
    else if _indBull
        _bullTypeId := 11
    else if _extBull
        _bullTypeId := 15
    else if _intBull
        _bullTypeId := 14
    else if _discBull
        _bullTypeId := 13
    else if _hiddenBull
        _bullTypeId := 2
    else if _reverseBull
        _bullTypeId := 3
    else if _classicBull
        _bullTypeId := 1
    else if _simpleBull
        _bullTypeId := 4

    int _bearTypeId = 0
    if _stopBear
        _bearTypeId := 6
    else if _liqBear
        _bearTypeId := 5
    else if _fvgBear
        _bearTypeId := 7
    else if _obBear
        _bearTypeId := 8
    else if _chochBear
        _bearTypeId := 9
    else if _bosBear
        _bearTypeId := 10
    else if _indBear
        _bearTypeId := 11
    else if _extBear
        _bearTypeId := 15
    else if _intBear
        _bearTypeId := 14
    else if _premBear
        _bearTypeId := 12
    else if _hiddenBear
        _bearTypeId := 2
    else if _reverseBear
        _bearTypeId := 3
    else if _classicBear
        _bearTypeId := 1
    else if _simpleBear
        _bearTypeId := 4

    [
         _bullScore,
         _bearScore,
         _bullTypeScore,
         _bearTypeScore,
         _bullTypeId * 1.0,
         _bearTypeId * 1.0
     ]

type SMTEvent
    int dir
    float origin
    float quality
    float corrQ
    float liqQ
    int born
    int state
    string kind
    string ref
    label lb

//──────────────────────────────────────────────────────────────────────
// ONLINE LEARNING ARRAYS
//──────────────────────────────────────────────────────────────────────
FEATURE_COUNT = 13

var array<float> feat_alpha = array.new_float()
var array<float> feat_beta  = array.new_float()
var array<float> feat_rsum  = array.new_float()
var array<float> feat_trades = array.new_float()

var array<float> cal_wins = array.new_float()
var array<float> cal_trades = array.new_float()

var array<string> setup_names = array.new_string()
var array<float> setup_wins = array.new_float()
var array<float> setup_trades = array.new_float()
var array<float> setup_rsum = array.new_float()

if barstate.isfirst
    if array.size(feat_alpha) == 0
        for i = 0 to FEATURE_COUNT - 1
            array.push(feat_alpha, feature_prior)
            array.push(feat_beta, feature_prior)
            array.push(feat_rsum, 0.0)
            array.push(feat_trades, 0.0)
    if array.size(cal_wins) == 0
        for i = 0 to 9
            array.push(cal_wins, 0.0)
            array.push(cal_trades, 0.0)

f_feature_factor(_idx) =>
    factor = 1.0
    if use_adaptive_weights and array.size(feat_alpha) > _idx
        a = array.get(feat_alpha, _idx)
        b = array.get(feat_beta, _idx)
        tr = array.get(feat_trades, _idx)
        rs = array.get(feat_rsum, _idx)
        post = (a) / math.max(a + b, 0.0001)
        expR = tr > 0 ? rs / tr : 0.0
        sample = f_clamp(tr / feature_min_sample, 0.0, 1.0)
        perfEdge = (post - 0.5) * 2.0
        rEdge = f_clamp(expR, -1.0, 1.0)
        factor := f_clamp(1.0 + adapt_strength * sample * (perfEdge * 0.70 + rEdge * 0.30), 0.45, 1.75)
    factor

f_update_feature(_idx, _score, _win, _r) =>
    s = f_clamp(_score, 0.0, 1.0)
    if array.size(feat_alpha) > _idx and s >= 0.20
        a = array.get(feat_alpha, _idx)
        b = array.get(feat_beta, _idx)
        rs = array.get(feat_rsum, _idx)
        tr = array.get(feat_trades, _idx)
        array.set(feat_alpha, _idx, a + (_win ? s : 0.0))
        array.set(feat_beta, _idx, b + (_win ? 0.0 : s))
        array.set(feat_rsum, _idx, rs + _r * s)
        array.set(feat_trades, _idx, tr + s)
    0

f_cal_bin(_p) =>
    int(math.floor(f_clamp(_p, 0.0, 0.9999) * 10.0))

f_calibrate(_p) =>
    pp = f_clamp(_p, 0.01, 0.99)
    if use_prob_calibration and array.size(cal_wins) == 10
        b = f_cal_bin(pp)
        w = array.get(cal_wins, b)
        t = array.get(cal_trades, b)
        wr = (w + 1.0) / (t + 2.0)
        blend = f_clamp(t / cal_min_sample, 0.0, cal_max_blend)
        pp := f_clamp(pp * (1.0 - blend) + wr * blend, 0.01, 0.99)
    pp

f_update_cal(_p, _win) =>
    if array.size(cal_wins) == 10
        b = f_cal_bin(_p)
        array.set(cal_trades, b, array.get(cal_trades, b) + 1.0)
        array.set(cal_wins, b, array.get(cal_wins, b) + (_win ? 1.0 : 0.0))
    0

f_setup_index(_name) =>
    idx = -1
    if array.size(setup_names) > 0
        for i = 0 to array.size(setup_names) - 1
            if array.get(setup_names, i) == _name
                idx := i
                break
    idx

f_ensure_setup(_name) =>
    idx = f_setup_index(_name)
    if idx == -1
        array.push(setup_names, _name)
        array.push(setup_wins, 0.0)
        array.push(setup_trades, 0.0)
        array.push(setup_rsum, 0.0)
        idx := array.size(setup_names) - 1
    idx

f_record_setup(_name, _win, _r) =>
    nm = _name == "" ? "Confluence" : _name
    idx = f_ensure_setup(nm)
    array.set(setup_trades, idx, array.get(setup_trades, idx) + 1.0)
    array.set(setup_wins, idx, array.get(setup_wins, idx) + (_win ? 1.0 : 0.0))
    array.set(setup_rsum, idx, array.get(setup_rsum, idx) + _r)
    0

f_setup_factor(_name) =>
    idx = f_setup_index(_name)
    factor = 1.0
    if idx != -1
        tr = array.get(setup_trades, idx)
        wr = (array.get(setup_wins, idx) + 1.0) / (tr + 2.0)
        expR = tr > 0 ? array.get(setup_rsum, idx) / tr : 0.0
        sample = f_clamp(tr / 30.0, 0.0, 1.0)
        factor := f_clamp(1.0 + sample * ((wr - 0.5) * 0.50 + f_clamp(expR, -1.0, 1.0) * 0.20), 0.80, 1.25)
    factor

//──────────────────────────────────────────────────────────────────────
// WARMUP / CORE STATISTICS
//──────────────────────────────────────────────────────────────────────
warmup_bars = math.max(math.max(norm_win, rank_len), math.max(math.max(ob_lb, hurst_len), vp_len))
warmup_ok = bar_index > warmup_bars

tr_val = ta.tr(true)
atr_raw = ta.atr(atr_len)
atr_val = nz(atr_raw, tr_val)
atr_pctile = f_pct(atr_val, rank_len)
atr_sma = ta.sma(atr_val, rank_len)
vol_width = not na(atr_sma) and atr_sma > 0 ? atr_val / atr_sma : 1.0
vol_factor = vol_width > 1.5 ? 1.3 : vol_width < 0.6 ? 0.75 : 1.0

bar_range = high - low
body = math.abs(close - open)
body_atr = atr_val > 0 ? body / atr_val : 0.0
upper_wick = high - math.max(open, close)
lower_wick = math.min(open, close) - low
close_loc = bar_range > 0 ? (close - low) / bar_range : 0.5
body_frac = bar_range > 0 ? body / bar_range : 0.0

vol = nz(volume, 0.0)
volume_available = not na(volume) and volume > 0
vol_sma = ta.sma(vol, 20)
rvol = not na(vol_sma) and vol_sma > 0 ? vol / vol_sma : 1.0

log_ret = close > 0 and close[1] > 0 ? math.log(close / close[1]) : 0.0
lambda = 2.0 / (vol_fc_len + 1.0)
var float ewma_var = na
ewma_var := na(ewma_var[1]) ? log_ret * log_ret : ewma_var[1] * (1.0 - lambda) + lambda * log_ret * log_ret
ewma_vol = math.sqrt(math.max(nz(ewma_var), 0.0))
hist_vol = ta.stdev(log_ret, vol_fc_len)
vol_fc_ratio = not na(hist_vol) and hist_vol > 0 ? ewma_vol / hist_vol : 1.0
atr_adaptive = atr_val * f_clamp(0.85 + 0.25 * (vol_fc_ratio - 1.0) + 0.30 * (atr_pctile - 0.5), 0.65, 1.45)
risk_atr = use_adaptive_atr ? atr_adaptive : atr_val

vwap_val = ta.vwap(hlc3)
vwap_valid = not na(vwap_val)
vwap_dev_atr = vwap_valid and atr_val > 0 ? (close - vwap_val) / atr_val : 0.0
vwap_dev_z = f_zrobust(vwap_valid ? close - vwap_val : 0.0, norm_win)

//──────────────────────────────────────────────────────────────────────
// REGIME
//──────────────────────────────────────────────────────────────────────
[diP, diM, adx_val] = ta.dmi(adx_len, adx_len)
er_change = not na(close[er_len]) ? math.abs(close - close[er_len]) : 0.0
er_vol = math.sum(math.abs(close - close[1]), er_len)
eff_ratio = not na(er_vol) and er_vol > 0 ? er_change / er_vol : 0.0

ret_std = ta.stdev(log_ret, hurst_len)
net_ret = close > 0 and close[hurst_len] > 0 ? math.log(close / close[hurst_len]) : 0.0
where_vr = not na(ret_std) and ret_std > 0 ? math.abs(net_ret) / (ret_std * math.sqrt(hurst_len)) : 1.0
hurst_proxy = f_clamp(0.5 + (where_vr - 1.0) * 0.20, 0.0, 1.0)
ret_norm = not na(ret_std) and ret_std > 0 ? math.abs(log_ret) / ret_std : 0.0
ret_entropy = f_entropy01(f_minmax(ret_norm, hurst_len))

slope_corr = ta.correlation(close, bar_index * 1.0, er_len)
slope_quality = na(slope_corr) ? 0.0 : math.abs(slope_corr)
vol_cluster_raw = ta.correlation(math.abs(log_ret), math.abs(log_ret[1]), hurst_len)
vol_cluster = na(vol_cluster_raw) ? 0.0 : vol_cluster_raw

rng_sma = ta.sma(bar_range, 14)
is_expansion = not na(rng_sma) and rng_sma > 0 and bar_range > rng_sma * 1.5
is_compression = not na(rng_sma) and rng_sma > 0 and bar_range < rng_sma * 0.6

trend_evidence = 0.0
trend_evidence += (adx_val > adx_trend ? 1.0 : adx_val / adx_trend) * 0.30
trend_evidence += eff_ratio * 0.25
trend_evidence += hurst_proxy * 0.20
trend_evidence += slope_quality * 0.15
trend_evidence += (1.0 - ret_entropy) * 0.10
trend_conf = f_clamp(trend_evidence, 0.0, 1.0)

is_trending = trend_conf >= 0.55
is_ranging = trend_conf < 0.45
is_transition = not is_trending and not is_ranging
market_entropy = f_clamp(ret_entropy * 0.60 + (is_transition ? 0.25 : 0.0) + (is_compression ? 0.15 : 0.0), 0.0, 1.0)
entropy_standby = use_entropy_standby and market_entropy > entropy_max
regime_str = is_trending ? "TREND" : is_ranging ? "RANGE" : "TRANSITION"
regime_str := is_compression ? regime_str + "/COMP" : is_expansion ? regime_str + "/EXP" : regime_str

//──────────────────────────────────────────────────────────────────────
// TREND / KALMAN / HTF / CRYPTO
//──────────────────────────────────────────────────────────────────────
zpf_slow = f_zpf(close, zpf_slow_len)
zpf_fast = f_zpf(close, zpf_fast_len)
zpf_slope = zpf_slow - zpf_slow[3]
zpf_slope_norm = f_squash(f_zrobust(nz(zpf_slope, 0.0), norm_win))
local_bull = zpf_fast > zpf_slow and zpf_slope > 0
local_bear = zpf_fast < zpf_slow and zpf_slope < 0

ema20 = ta.ema(close, 20)
ema50 = ta.ema(close, 50)
ema200 = ta.ema(close, 200)

var float kalman = na
var float kalman_p = 1.0
kalman_q = kalman_q_base * (0.5 + atr_pctile * 1.5)
kalman_r = kalman_r_base * (is_compression ? 1.6 : is_expansion ? 0.75 : 1.0)
kalman_p += kalman_q
kalman_k = kalman_p / (kalman_p + kalman_r)
kalman := na(kalman) ? close : kalman + kalman_k * (close - kalman)
kalman_p := (1.0 - kalman_k) * kalman_p
kalman_slope = kalman - kalman[3]
kalman_bull = close > kalman and kalman_slope > 0
kalman_bear = close < kalman and kalman_slope < 0

[int_bias, int_eq, int_hi, int_lo] = f_struct_pack(int_piv_lb)
[ext_bias, ext_eq, ext_hi, ext_lo] = f_struct_pack(ext_piv_lb)

[htf1_bias, htf1_eq, htf1_hi, htf1_lo] = request.security(syminfo.tickerid, macro_tf1, f_struct_pack(piv_lb), lookahead=barmerge.lookahead_off)
[htf2_bias, htf2_eq, htf2_hi, htf2_lo] = request.security(syminfo.tickerid, macro_tf2, f_struct_pack(piv_lb), lookahead=barmerge.lookahead_off)

htf_align = htf1_bias + htf2_bias
htf_bull_ctx = htf_align > 0
htf_bear_ctx = htf_align < 0
htf_conf = math.abs(htf_align) / 2.0
htf_in_discount = not na(htf1_eq) and close < htf1_eq
htf_in_premium = not na(htf1_eq) and close > htf1_eq
htf_long_ok = not use_htf or htf_align >= 0
htf_short_ok = not use_htf or htf_align <= 0

crypto_total_bias_raw = request.security(crypto_total_sym, crypto_tf, f_crypto_bias_expr(), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)
crypto_total2_bias_raw = request.security(crypto_total2_sym, crypto_tf, f_crypto_bias_expr(), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)
crypto_usdt_bias_raw = request.security(crypto_usdt_d_sym, crypto_tf, f_crypto_inverse_bias_expr(), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)
crypto_btc_bias_raw = request.security(crypto_btc_d_sym, crypto_tf, f_crypto_bias_expr(), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)

crypto_total_bias = nz(crypto_total_bias_raw, 0)
crypto_total2_bias = nz(crypto_total2_bias_raw, 0)
crypto_usdt_bias = nz(crypto_usdt_bias_raw, 0)
crypto_btc_bias = nz(crypto_btc_bias_raw, 0)
crypto_ctx_score = use_crypto_ctx ? f_clamp(crypto_total_bias * 0.45 + crypto_total2_bias * 0.20 + crypto_usdt_bias * 0.30 + crypto_btc_bias * 0.05, -1.0, 1.0) : 0.0
crypto_long_ok = not use_crypto_ctx or crypto_ctx_score > -0.70
crypto_short_ok = not use_crypto_ctx or crypto_ctx_score < 0.70

//──────────────────────────────────────────────────────────────────────
// STRUCTURE / LIQUIDITY HIERARCHY
//──────────────────────────────────────────────────────────────────────
ph = ta.pivothigh(high, piv_lb, piv_lb)
pl = ta.pivotlow(low, piv_lb, piv_lb)

var float last_ph = na
var float last_pl = na
var float prev_ph = na
var float prev_pl = na
var int trend_dir = 0
var float protected_high = na
var float protected_low = na

if not na(ph)
    prev_ph := last_ph
    last_ph := ph

if not na(pl)
    prev_pl := last_pl
    last_pl := pl

equal_highs = not na(ph) and not na(prev_ph) and math.abs(ph - prev_ph) <= atr_val * eq_tol_atr
equal_lows  = not na(pl) and not na(prev_pl) and math.abs(pl - prev_pl) <= atr_val * eq_tol_atr

is_displacement = body_atr >= disp_atr

var bool bos_up = false
var bool bos_dn = false
var bool choch_up = false
var bool choch_dn = false
var bool mss_up = false
var bool mss_dn = false
var float break_quality = 0.0
var int last_break_bar = na

bos_up := false
bos_dn := false
choch_up := false
choch_dn := false
mss_up := false
mss_dn := false

if not na(last_ph) and close > last_ph and nz(close[1], close) <= last_ph
    if trend_dir == -1
        choch_up := true
        mss_up := true
    else
        bos_up := true
    trend_dir := 1
    protected_low := last_pl
    break_quality := f_clamp(body_atr / (disp_atr * 1.5), 0.0, 1.0)
    last_break_bar := bar_index

if not na(last_pl) and close < last_pl and nz(close[1], close) >= last_pl
    if trend_dir == 1
        choch_dn := true
        mss_dn := true
    else
        bos_dn := true
    trend_dir := -1
    protected_high := last_ph
    break_quality := f_clamp(body_atr / (disp_atr * 1.5), 0.0, 1.0)
    last_break_bar := bar_index

break_age = not na(last_break_bar) ? bar_index - last_break_bar : 9999
break_quality_live = not na(last_break_bar) ? break_quality * math.pow(0.985, break_age) : 0.0

strong_break_up = (bos_up or choch_up) and is_displacement
strong_break_dn = (bos_dn or choch_dn) and is_displacement
weak_bos_up = bos_up and not is_displacement
weak_bos_dn = bos_dn and not is_displacement

range_top = not na(last_ph) and not na(last_pl) ? math.max(last_ph, last_pl) : na
range_bot = not na(last_ph) and not na(last_pl) ? math.min(last_ph, last_pl) : na
range_sz = not na(range_top) and not na(range_bot) ? range_top - range_bot : na
range_eq = not na(range_sz) and range_sz > 0 ? (range_top + range_bot) / 2.0 : na
dr_pos = not na(range_sz) and range_sz > 0 ? f_clamp((close - range_bot) / range_sz, 0.0, 1.0) : 0.5
in_discount = not na(range_eq) and close < range_eq
in_premium = not na(range_eq) and close > range_eq
in_ote_long = dr_pos >= 0.21 and dr_pos <= 0.38
in_ote_short = dr_pos >= 0.62 and dr_pos <= 0.79

sweep_high = not na(last_ph) and high > last_ph and close < last_ph
sweep_low = not na(last_pl) and low < last_pl and close > last_pl
stop_hunt_high = sweep_high and equal_highs
stop_hunt_low = sweep_low and equal_lows

sweep_low_eff = sweep_low and bar_range > 0 ? (close - low) / bar_range : 0.0
sweep_high_eff = sweep_high and bar_range > 0 ? (high - close) / bar_range : 0.0

int_ph = ta.pivothigh(high, int_piv_lb, int_piv_lb)
int_pl = ta.pivotlow(low, int_piv_lb, int_piv_lb)
int_prev_ph = ta.valuewhen(not na(int_ph), int_ph, 1)
int_prev_pl = ta.valuewhen(not na(int_pl), int_pl, 1)
int_equal_highs = not na(int_ph) and not na(int_prev_ph) and math.abs(int_ph - int_prev_ph) <= atr_val * eq_tol_atr
int_equal_lows = not na(int_pl) and not na(int_prev_pl) and math.abs(int_pl - int_prev_pl) <= atr_val * eq_tol_atr

ext_ph = ta.pivothigh(high, ext_piv_lb, ext_piv_lb)
ext_pl = ta.pivotlow(low, ext_piv_lb, ext_piv_lb)
ext_prev_ph = ta.valuewhen(not na(ext_ph), ext_ph, 1)
ext_prev_pl = ta.valuewhen(not na(ext_pl), ext_pl, 1)
ext_equal_highs = not na(ext_ph) and not na(ext_prev_ph) and math.abs(ext_ph - ext_prev_ph) <= atr_val * eq_tol_atr
ext_equal_lows = not na(ext_pl) and not na(ext_prev_pl) and math.abs(ext_pl - ext_prev_pl) <= atr_val * eq_tol_atr

external_high_prox = not na(ext_hi) and atr_val > 0 ? f_clamp(1.0 - math.abs(ext_hi - close) / (atr_val * 10.0), 0.0, 1.0) : 0.0
external_low_prox = not na(ext_lo) and atr_val > 0 ? f_clamp(1.0 - math.abs(close - ext_lo) / (atr_val * 10.0), 0.0, 1.0) : 0.0

var float liq_low_conf = 0.0
var float liq_high_conf = 0.0
liq_low_conf := liq_low_conf * liq_decay
liq_high_conf := liq_high_conf * liq_decay

if equal_lows or int_equal_lows or ext_equal_lows
    liq_low_conf := math.min(liq_low_conf + (ext_equal_lows ? 0.45 : int_equal_lows ? 0.25 : 0.35), 1.0)

if equal_highs or int_equal_highs or ext_equal_highs
    liq_high_conf := math.min(liq_high_conf + (ext_equal_highs ? 0.45 : int_equal_highs ? 0.25 : 0.35), 1.0)

liq_low_conf_pre = liq_low_conf
liq_high_conf_pre = liq_high_conf

rest_liq_low = f_clamp(liq_low_conf_pre * 0.35 + (int_equal_lows ? 0.20 : 0.0) + (ext_equal_lows ? 0.30 : 0.0) + external_low_prox * 0.15, 0.0, 1.0)
rest_liq_high = f_clamp(liq_high_conf_pre * 0.35 + (int_equal_highs ? 0.20 : 0.0) + (ext_equal_highs ? 0.30 : 0.0) + external_high_prox * 0.15, 0.0, 1.0)

if sweep_low
    liq_low_conf := 0.0

if sweep_high
    liq_high_conf := 0.0

inducement_long = sweep_low and trend_dir >= 0 and int_bias >= 0
inducement_short = sweep_high and trend_dir <= 0 and int_bias <= 0

//──────────────────────────────────────────────────────────────────────
// ORDER BLOCKS / FVG
//──────────────────────────────────────────────────────────────────────
type OB
    float top
    float bot
    float conf
    float quality
    int born
    int retests
    bool wasInside
    bool nested
    bool imbalance
    box bx

type FVG
    float top
    float bot
    float conf
    float quality
    float size_atr
    int born
    float fill
    bool wasInside
    box bx

var array<OB> bullOBs = array.new<OB>()
var array<OB> bearOBs = array.new<OB>()
var array<FVG> bullFVGs = array.new<FVG>()
var array<FVG> bearFVGs = array.new<FVG>()

ob_bull_border_col = color.new(bull_col, 25)
ob_bull_bg_col = color.new(bull_col, 88)
ob_bear_border_col = color.new(bear_col, 25)
ob_bear_bg_col = color.new(bear_col, 88)
fvg_bull_border_col = color.new(info_col, 35)
fvg_bull_bg_col = color.new(info_col, 90)
fvg_bear_border_col = color.new(color.rgb(234, 88, 12), 35)
fvg_bear_bg_col = color.new(color.rgb(234, 88, 12), 90)

raw_new_bull_fvg = not na(high[2]) and low > high[2]
raw_new_bear_fvg = not na(low[2]) and high < low[2]

f_ob_quality(_bodyAtr, _rvol, _breakQ, _dispQ, _absorbQ, _locQ, _nested, _imbalance, _mtfQ) =>
    q = 0.0
    q += f_clamp(_bodyAtr / 1.5, 0.0, 1.0) * 0.18
    q += f_clamp(_rvol / 2.5, 0.0, 1.0) * 0.16
    q += _breakQ * 0.18
    q += _dispQ * 0.14
    q += _absorbQ * 0.10
    q += _locQ * 0.10
    q += (_nested ? 1.0 : 0.0) * 0.06
    q += (_imbalance ? 1.0 : 0.0) * 0.05
    q += _mtfQ * 0.03
    f_clamp(q, 0.0, 1.0)

f_fvg_quality(_sizeAtr, _dispQ, _rvolQ, _trendQ, _locQ, _htfQ) =>
    q = 0.0
    q += f_clamp(_sizeAtr / 1.5, 0.0, 1.0) * 0.25
    q += _dispQ * 0.25
    q += _rvolQ * 0.18
    q += _trendQ * 0.18
    q += _locQ * 0.14
    q += _htfQ * 0.10
    f_clamp(q, 0.0, 1.0)

bull_breaker = false
bear_breaker = false

if (bos_up or choch_up) and bar_index > 5
    maxLook = math.min(math.min(ob_lb, ob_scan_cap), bar_index)
    float bestQ = -1.0
    int bestI = na
    bool bestNested = false
    bool bestImb = false
    if maxLook >= 1
        for i = 1 to maxLook
            if close[i] < open[i]
                nested = false
                if array.size(bullOBs) > 0
                    for n = 0 to array.size(bullOBs) - 1
                        old = array.get(bullOBs, n)
                        if high[i] <= old.top and low[i] >= old.bot
                            nested := true
                bdy = atr_val[i] > 0 ? math.abs(close[i] - open[i]) / atr_val[i] : 0.0
                rv = not na(vol_sma[i]) and vol_sma[i] > 0 ? vol[i] / vol_sma[i] : 1.0
                absorbQ = rv > 1.3 and not na(rng_sma[i]) and rng_sma[i] > 0 and (high[i] - low[i]) < rng_sma[i] ? 1.0 : 0.0
                locQ = not na(range_eq[i]) ? (low[i] < range_eq[i] ? 1.0 : 0.45) : 0.5
                mtfQ = htf_bull_ctx ? 1.0 : htf_align == 0 ? 0.6 : 0.25
                imb = raw_new_bull_fvg or is_displacement
                q = f_ob_quality(bdy, rv, break_quality, f_clamp(body_atr / disp_atr, 0.0, 1.0), absorbQ, locQ, nested, imb, mtfQ)
                if q > bestQ
                    bestQ := q
                    bestI := i
                    bestNested := nested
                    bestImb := imb
    if not na(bestI)
        bx = show_zones ? f_zone_box(bar_index - bestI, high[bestI], bar_index + zone_forward_bars, low[bestI], ob_bull_border_col, ob_bull_bg_col, "Bull OB") : na
        array.push(bullOBs, OB.new(high[bestI], low[bestI], math.max(0.45, bestQ), bestQ, bar_index, 0, false, bestNested, bestImb, bx))
        if array.size(bullOBs) > max_live_objects
            oldOb = array.shift(bullOBs)
            f_delete_box(oldOb.bx)

if (bos_dn or choch_dn) and bar_index > 5
    maxLook = math.min(math.min(ob_lb, ob_scan_cap), bar_index)
    float bestQ = -1.0
    int bestI = na
    bool bestNested = false
    bool bestImb = false
    if maxLook >= 1
        for i = 1 to maxLook
            if close[i] > open[i]
                nested = false
                if array.size(bearOBs) > 0
                    for n = 0 to array.size(bearOBs) - 1
                        old = array.get(bearOBs, n)
                        if high[i] <= old.top and low[i] >= old.bot
                            nested := true
                bdy = atr_val[i] > 0 ? math.abs(close[i] - open[i]) / atr_val[i] : 0.0
                rv = not na(vol_sma[i]) and vol_sma[i] > 0 ? vol[i] / vol_sma[i] : 1.0
                absorbQ = rv > 1.3 and not na(rng_sma[i]) and rng_sma[i] > 0 and (high[i] - low[i]) < rng_sma[i] ? 1.0 : 0.0
                locQ = not na(range_eq[i]) ? (high[i] > range_eq[i] ? 1.0 : 0.45) : 0.5
                mtfQ = htf_bear_ctx ? 1.0 : htf_align == 0 ? 0.6 : 0.25
                imb = raw_new_bear_fvg or is_displacement
                q = f_ob_quality(bdy, rv, break_quality, f_clamp(body_atr / disp_atr, 0.0, 1.0), absorbQ, locQ, nested, imb, mtfQ)
                if q > bestQ
                    bestQ := q
                    bestI := i
                    bestNested := nested
                    bestImb := imb
    if not na(bestI)
        bx = show_zones ? f_zone_box(bar_index - bestI, high[bestI], bar_index + zone_forward_bars, low[bestI], ob_bear_border_col, ob_bear_bg_col, "Bear OB") : na
        array.push(bearOBs, OB.new(high[bestI], low[bestI], math.max(0.45, bestQ), bestQ, bar_index, 0, false, bestNested, bestImb, bx))
        if array.size(bearOBs) > max_live_objects
            oldOb = array.shift(bearOBs)
            f_delete_box(oldOb.bx)

bj = array.size(bullOBs) - 1
while bj >= 0
    ob = array.get(bullOBs, bj)
    inside = low <= ob.top and high >= ob.bot
    age = bar_index - ob.born
    ob.conf := f_clamp(ob.conf * ob_decay, 0.0, 1.0)
    if inside and not ob.wasInside
        ob.retests += 1
        ob.conf := f_clamp(ob.conf + 0.05 * math.max(0.0, 1.0 - ob.retests * 0.12), 0.0, 1.0)
    ob.wasInside := inside
    if show_zones
        txt = "Bull OB " + str.tostring(ob.conf * 100.0, "#") + "%" + (ob.nested ? " · Nested" : "") + (ob.imbalance ? " · Imb" : "")
        f_update_zone(ob.bx, bar_index + zone_forward_bars, txt, ob_bull_border_col, ob_bull_bg_col)
    mitigated = close < ob.bot
    expired = age > max_object_age or ob.conf < 0.03
    if mitigated
        bull_breaker := true
        f_delete_box(ob.bx)
        array.remove(bullOBs, bj)
    else if expired
        f_delete_box(ob.bx)
        array.remove(bullOBs, bj)
    else
        array.set(bullOBs, bj, ob)
    bj -= 1

sj = array.size(bearOBs) - 1
while sj >= 0
    ob = array.get(bearOBs, sj)
    inside = high >= ob.bot and low <= ob.top
    age = bar_index - ob.born
    ob.conf := f_clamp(ob.conf * ob_decay, 0.0, 1.0)
    if inside and not ob.wasInside
        ob.retests += 1
        ob.conf := f_clamp(ob.conf + 0.05 * math.max(0.0, 1.0 - ob.retests * 0.12), 0.0, 1.0)
    ob.wasInside := inside
    if show_zones
        txt = "Bear OB " + str.tostring(ob.conf * 100.0, "#") + "%" + (ob.nested ? " · Nested" : "") + (ob.imbalance ? " · Imb" : "")
        f_update_zone(ob.bx, bar_index + zone_forward_bars, txt, ob_bear_border_col, ob_bear_bg_col)
    mitigated = close > ob.top
    expired = age > max_object_age or ob.conf < 0.03
    if mitigated
        bear_breaker := true
        f_delete_box(ob.bx)
        array.remove(bearOBs, sj)
    else if expired
        f_delete_box(ob.bx)
        array.remove(bearOBs, sj)
    else
        array.set(bearOBs, sj, ob)
    sj -= 1

float ob_long_conf = 0.0
float ob_short_conf = 0.0
float ob_long_fresh = 0.0
float ob_short_fresh = 0.0
float ob_long_bot = na
float ob_short_top = na
bool in_bull_ob = false
bool in_bear_ob = false

best_ob_L = -1.0
if array.size(bullOBs) > 0
    for i = 0 to array.size(bullOBs) - 1
        ob = array.get(bullOBs, i)
        inside = low <= ob.top and high >= ob.bot
        dist = close > ob.top ? close - ob.top : close < ob.bot ? ob.bot - close : 0.0
        prox = atr_val > 0 ? f_clamp(1.0 - dist / (atr_val * 3.0), 0.0, 1.0) : 0.0
        freshness = f_clamp(1.0 - (bar_index - ob.born) / math.max(max_object_age, 1), 0.0, 1.0)
        retestQ = f_clamp(1.0 - math.max(ob.retests - 1, 0) * 0.12, 0.35, 1.0)
        nestedQ = ob.nested ? 1.08 : 1.0
        effective = ob.conf * (0.45 + 0.55 * prox) * retestQ * nestedQ + (inside ? 0.10 * ob.quality : 0.0)
        if effective > best_ob_L
            best_ob_L := effective
            ob_long_conf := f_clamp(effective, 0.0, 1.0)
            ob_long_fresh := freshness
            ob_long_bot := ob.bot
            in_bull_ob := inside

best_ob_S = -1.0
if array.size(bearOBs) > 0
    for i = 0 to array.size(bearOBs) - 1
        ob = array.get(bearOBs, i)
        inside = high >= ob.bot and low <= ob.top
        dist = close > ob.top ? close - ob.top : close < ob.bot ? ob.bot - close : 0.0
        prox = atr_val > 0 ? f_clamp(1.0 - dist / (atr_val * 3.0), 0.0, 1.0) : 0.0
        freshness = f_clamp(1.0 - (bar_index - ob.born) / math.max(max_object_age, 1), 0.0, 1.0)
        retestQ = f_clamp(1.0 - math.max(ob.retests - 1, 0) * 0.12, 0.35, 1.0)
        nestedQ = ob.nested ? 1.08 : 1.0
        effective = ob.conf * (0.45 + 0.55 * prox) * retestQ * nestedQ + (inside ? 0.10 * ob.quality : 0.0)
        if effective > best_ob_S
            best_ob_S := effective
            ob_short_conf := f_clamp(effective, 0.0, 1.0)
            ob_short_fresh := freshness
            ob_short_top := ob.top
            in_bear_ob := inside

bool new_bull_fvg = false
bool new_bear_fvg = false

if raw_new_bull_fvg
    sz = atr_val > 0 ? (low - high[2]) / atr_val : 0.0
    if sz >= min_fvg_atr
        dispQ = f_clamp(body_atr / disp_atr, 0.0, 1.0)
        rvQ = f_clamp(rvol / 2.5, 0.0, 1.0)
        trendQ = local_bull ? 1.0 : trend_dir == 1 ? 0.75 : 0.35
        locQ = in_discount ? 1.0 : htf_in_discount ? 0.75 : 0.45
        htfQ = htf_bull_ctx ? 1.0 : htf_align == 0 ? 0.60 : 0.25
        q = f_fvg_quality(sz, dispQ, rvQ, trendQ, locQ, htfQ)
        bx = show_zones ? f_zone_box(bar_index - 2, low, bar_index + zone_forward_bars, high[2], fvg_bull_border_col, fvg_bull_bg_col, "Bull FVG") : na
        array.push(bullFVGs, FVG.new(low, high[2], math.max(0.35, q), q, sz, bar_index, 0.0, false, bx))
        if array.size(bullFVGs) > max_live_objects
            oldF = array.shift(bullFVGs)
            f_delete_box(oldF.bx)
        new_bull_fvg := true

if raw_new_bear_fvg
    sz = atr_val > 0 ? (low[2] - high) / atr_val : 0.0
    if sz >= min_fvg_atr
        dispQ = f_clamp(body_atr / disp_atr, 0.0, 1.0)
        rvQ = f_clamp(rvol / 2.5, 0.0, 1.0)
        trendQ = local_bear ? 1.0 : trend_dir == -1 ? 0.75 : 0.35
        locQ = in_premium ? 1.0 : htf_in_premium ? 0.75 : 0.45
        htfQ = htf_bear_ctx ? 1.0 : htf_align == 0 ? 0.60 : 0.25
        q = f_fvg_quality(sz, dispQ, rvQ, trendQ, locQ, htfQ)
        bx = show_zones ? f_zone_box(bar_index - 2, low[2], bar_index + zone_forward_bars, high, fvg_bear_border_col, fvg_bear_bg_col, "Bear FVG") : na
        array.push(bearFVGs, FVG.new(low[2], high, math.max(0.35, q), q, sz, bar_index, 0.0, false, bx))
        if array.size(bearFVGs) > max_live_objects
            oldF = array.shift(bearFVGs)
            f_delete_box(oldF.bx)
        new_bear_fvg := true

bool ifvg_bull = false
bool ifvg_bear = false

fj = array.size(bullFVGs) - 1
while fj >= 0
    f = array.get(bullFVGs, fj)
    gap = f.top - f.bot
    fill_now = gap > 0 ? (low <= f.bot ? 1.0 : low < f.top ? (f.top - low) / gap : 0.0) : 0.0
    f.fill := math.max(f.fill, f_clamp(fill_now, 0.0, 1.0))
    f.conf := f_clamp(f.conf * fvg_decay, 0.0, 1.0)
    if show_zones
        f_update_zone(f.bx, bar_index + zone_forward_bars, "Bull FVG " + str.tostring((1.0 - f.fill) * 100.0, "#") + "%", fvg_bull_border_col, fvg_bull_bg_col)
    inverted = close < f.bot
    expired = bar_index - f.born > max_object_age or f.conf < 0.03
    if inverted or expired
        ifvg_bear := inverted
        f_delete_box(f.bx)
        array.remove(bullFVGs, fj)
    else
        array.set(bullFVGs, fj, f)
    fj -= 1

fk = array.size(bearFVGs) - 1
while fk >= 0
    f = array.get(bearFVGs, fk)
    gap = f.top - f.bot
    fill_now = gap > 0 ? (high >= f.top ? 1.0 : high > f.bot ? (high - f.bot) / gap : 0.0) : 0.0
    f.fill := math.max(f.fill, f_clamp(fill_now, 0.0, 1.0))
    f.conf := f_clamp(f.conf * fvg_decay, 0.0, 1.0)
    if show_zones
        f_update_zone(f.bx, bar_index + zone_forward_bars, "Bear FVG " + str.tostring((1.0 - f.fill) * 100.0, "#") + "%", fvg_bear_border_col, fvg_bear_bg_col)
    inverted = close > f.top
    expired = bar_index - f.born > max_object_age or f.conf < 0.03
    if inverted or expired
        ifvg_bull := inverted
        f_delete_box(f.bx)
        array.remove(bearFVGs, fk)
    else
        array.set(bearFVGs, fk, f)
    fk -= 1

float fvg_long_conf = 0.0
float fvg_short_conf = 0.0
bool in_bull_fvg = false
bool in_bear_fvg = false
bool bullFVG_active = false
bool bearFVG_active = false

best_fvg_L = -1.0
if array.size(bullFVGs) > 0
    for i = 0 to array.size(bullFVGs) - 1
        f = array.get(bullFVGs, i)
        inside = low <= f.top and high >= f.bot
        dist = close > f.top ? close - f.top : close < f.bot ? f.bot - close : 0.0
        prox = atr_val > 0 ? f_clamp(1.0 - dist / (atr_val * 3.0), 0.0, 1.0) : 0.0
        score = f.conf * (0.45 + 0.55 * prox) * (1.0 - 0.20 * f.fill) + (inside ? 0.08 * f.quality : 0.0)
        if score > best_fvg_L
            best_fvg_L := score
            fvg_long_conf := f_clamp(score, 0.0, 1.0)
            in_bull_fvg := inside
            bullFVG_active := true

best_fvg_S = -1.0
if array.size(bearFVGs) > 0
    for i = 0 to array.size(bearFVGs) - 1
        f = array.get(bearFVGs, i)
        inside = high >= f.bot and low <= f.top
        dist = close > f.top ? close - f.top : close < f.bot ? f.bot - close : 0.0
        prox = atr_val > 0 ? f_clamp(1.0 - dist / (atr_val * 3.0), 0.0, 1.0) : 0.0
        score = f.conf * (0.45 + 0.55 * prox) * (1.0 - 0.20 * f.fill) + (inside ? 0.08 * f.quality : 0.0)
        if score > best_fvg_S
            best_fvg_S := score
            fvg_short_conf := f_clamp(score, 0.0, 1.0)
            in_bear_fvg := inside
            bearFVG_active := true

bpr_bull = new_bull_fvg and new_bear_fvg[1]
bpr_bear = new_bear_fvg and new_bull_fvg[1]

//──────────────────────────────────────────────────────────────────────
// VOLUME PROFILE APPROXIMATION
//──────────────────────────────────────────────────────────────────────
float vp_poc = na
float vp_acceptance = 0.5
float vp_cur_vol = 0.0
float vp_max_vol = 0.0

vp_lo_calc = ta.lowest(low, vp_len)
vp_hi_calc = ta.highest(high, vp_len)

if use_volume_profile and bar_index > vp_len
    vp_lo = vp_lo_calc
    vp_hi = vp_hi_calc
    vp_rng = vp_hi - vp_lo
    if vp_rng > 0
        bin_sz = vp_rng / vp_bins
        int poc_bin = 0
        for b = 0 to vp_bins - 1
            binLo = vp_lo + bin_sz * b
            binHi = b == vp_bins - 1 ? vp_hi + syminfo.mintick : binLo + bin_sz
            float sumVol = 0.0
            for j = 0 to vp_len - 1
                tp = hlc3[j]
                if tp >= binLo and tp < binHi
                    sumVol += nz(volume[j], 0.0)
            if close >= binLo and close < binHi
                vp_cur_vol := sumVol
            if sumVol > vp_max_vol
                vp_max_vol := sumVol
                poc_bin := b
        vp_poc := vp_lo + bin_sz * (poc_bin + 0.5)
        vp_acceptance := vp_max_vol > 0 ? f_clamp(vp_cur_vol / vp_max_vol, 0.0, 1.0) : 0.5

vp_dist_atr = not na(vp_poc) and atr_val > 0 ? math.abs(close - vp_poc) / atr_val : 0.0

//──────────────────────────────────────────────────────────────────────
// CANDLE DNA / KINETIC / DELTA APPROXIMATION
//──────────────────────────────────────────────────────────────────────
dir_now = close > open ? 1 : close < open ? -1 : 0
dir_1 = close[1] > open[1] ? 1 : close[1] < open[1] ? -1 : 0
dir_2 = close[2] > open[2] ? 1 : close[2] < open[2] ? -1 : 0
dir_3 = close[3] > open[3] ? 1 : close[3] < open[3] ? -1 : 0
dir_4 = close[4] > open[4] ? 1 : close[4] < open[4] ? -1 : 0

f_persist = dir_now == 0 ? 0.0 : ((dir_now == dir_1 ? 1.0 : 0.0) + (dir_now == dir_2 ? 1.0 : 0.0) + (dir_now == dir_3 ? 1.0 : 0.0) + (dir_now == dir_4 ? 1.0 : 0.0)) / 4.0
f_body_rank = f_pct(body, norm_win)
imp_change = not na(close[3]) ? math.abs(close - close[3]) : 0.0
imp_path = math.sum(bar_range, 3)
f_impulse_eff = not na(imp_path) and imp_path > 0 ? imp_change / imp_path : 0.0

lower_reject = lower_wick / math.max(body + atr_val * 0.1, syminfo.mintick)
upper_reject = upper_wick / math.max(body + atr_val * 0.1, syminfo.mintick)

dna_bull = 0.0
dna_bull += close_loc * 0.25
dna_bull += f_persist * (dir_now == 1 ? 1.0 : 0.0) * 0.15
dna_bull += f_clamp(lower_reject / 3.0, 0.0, 1.0) * 0.20
dna_bull += f_impulse_eff * (close > close[3] ? 1.0 : 0.0) * 0.20
dna_bull += f_body_rank * (dir_now == 1 ? 1.0 : 0.0) * 0.20
dna_bull := f_clamp(dna_bull, 0.0, 1.0)

dna_bear = 0.0
dna_bear += (1.0 - close_loc) * 0.25
dna_bear += f_persist * (dir_now == -1 ? 1.0 : 0.0) * 0.15
dna_bear += f_clamp(upper_reject / 3.0, 0.0, 1.0) * 0.20
dna_bear += f_impulse_eff * (close < close[3] ? 1.0 : 0.0) * 0.20
dna_bear += f_body_rank * (dir_now == -1 ? 1.0 : 0.0) * 0.20
dna_bear := f_clamp(dna_bear, 0.0, 1.0)

upper_dom = upper_wick > lower_wick and upper_wick > body
lower_dom = lower_wick > upper_wick and lower_wick > body
bull_engulf = close > open and close[1] < open[1] and close >= open[1] and open <= close[1]
bear_engulf = close < open and close[1] > open[1] and close <= open[1] and open >= close[1]
pin_bull = lower_wick > body * 2.0 and upper_wick < body
pin_bear = upper_wick > body * 2.0 and lower_wick < body
hammer = lower_dom and lower_wick > body * 2.0 and close_loc > 0.5
shooting_star = upper_dom and upper_wick > body * 2.0 and close_loc < 0.5
doji = body <= bar_range * 0.1

seq_net = dir_now + dir_1 + dir_2 + dir_3 + dir_4
seq_bull_bias = math.max(0.0, seq_net) / 5.0
seq_bear_bias = math.max(0.0, -seq_net) / 5.0
dir_flip_bull = dir_now == 1 and dir_now[1] == -1 and f_body_rank > 0.6
dir_flip_bear = dir_now == -1 and dir_now[1] == 1 and f_body_rank > 0.6

esa = ta.ema(hlc3, wt_ch)
de = ta.ema(math.abs(hlc3 - esa), wt_ch)
ci = de != 0 ? (hlc3 - esa) / (0.015 * de) : 0.0
wt1 = ta.ema(ci, wt_avg)
wt2 = ta.sma(wt1, 4)
wt_ob = 53.0 * vol_factor
wt_os = -53.0 * vol_factor
wt_bull_cross = ta.crossover(wt1, wt2) and wt1 < wt_os
wt_bear_cross = ta.crossunder(wt1, wt2) and wt1 > wt_ob
wt_bull = wt1 > wt2
wt_bear = wt1 < wt2

stc_val = f_stc(close, stc_fast, stc_slow, stc_len)
stc_bull = ta.crossover(stc_val, 25)
stc_bear = ta.crossunder(stc_val, 75)
stc_up = stc_val > stc_val[1]
stc_dn = stc_val < stc_val[1]
cci_val = ta.cci(hlc3, cci_len)
cci_bull = ta.crossover(cci_val, -100.0 * vol_factor)
cci_bear = ta.crossunder(cci_val, 100.0 * vol_factor)

kin_long = math.min((wt_bull_cross ? 0.35 : wt_bull ? 0.12 : 0.0) + (stc_bull ? 0.30 : stc_up ? 0.12 : 0.0) + (cci_bull ? 0.20 : cci_val > 0 ? 0.08 : 0.0) + (wt1 < wt_os ? 0.15 : 0.0), 1.0)
kin_short = math.min((wt_bear_cross ? 0.35 : wt_bear ? 0.12 : 0.0) + (stc_bear ? 0.30 : stc_dn ? 0.12 : 0.0) + (cci_bear ? 0.20 : cci_val < 0 ? 0.08 : 0.0) + (wt1 > wt_ob ? 0.15 : 0.0), 1.0)

net_delta = bar_range > 0 ? vol * ((close - low) - (high - close)) / bar_range : 0.0
var float cum_delta = 0.0
cum_delta += net_delta
roll_delta = math.sum(net_delta, 50)
cum_delta_bias = cum_delta - ta.ema(cum_delta, 100)

buy_vol = vol * close_loc
sell_vol = vol * (1.0 - close_loc)
aggression = not na(vol_sma) and vol_sma > 0 ? (buy_vol - sell_vol) / vol_sma : 0.0
absorption_buy = rvol > 1.3 and lower_wick > body * 1.2 and close_loc > 0.55 and not na(rng_sma) and bar_range < rng_sma
absorption_sell = rvol > 1.3 and upper_wick > body * 1.2 and close_loc < 0.45 and not na(rng_sma) and bar_range < rng_sma

vol_spike = not na(vol_sma) and vol > vol_sma * 2.0
selling_climax = vol_spike and lower_dom and aggression > 0
buying_climax = vol_spike and upper_dom and aggression < 0
spring = sweep_low and close > open and is_expansion
upthrust = sweep_high and close < open and is_expansion
sos = strong_break_up and aggression > 0
sow = strong_break_dn and aggression < 0
effort_result = rvol > 1.5 and not na(rng_sma) and rng_sma > 0 and bar_range < rng_sma ? 1.0 : 0.0

//──────────────────────────────────────────────────────────────────────
// INSTITUTIONAL SMT INTELLIGENCE LAYER
//──────────────────────────────────────────────────────────────────────
smt_tf_eff = smt_tf == "" ? timeframe.period : smt_tf

smt_chart_is_btc = str.contains(syminfo.ticker, "BTC")
smt_chart_is_eth = str.contains(syminfo.ticker, "ETH")
smt_chart_is_bnb = str.contains(syminfo.ticker, "BNB")
smt_chart_is_sol = str.contains(syminfo.ticker, "SOL")
smt_chart_is_xrp = str.contains(syminfo.ticker, "XRP")

smt_crypto_chart =
     syminfo.type == "crypto" or
     str.contains(syminfo.tickerid, "CRYPTOCAP:") or
     str.contains(syminfo.ticker, "USDT") or
     str.contains(syminfo.ticker, "USD")

string smt_auto_ref1 = smt_eth_sym
string smt_auto_ref2 = smt_total_sym
string smt_auto_ref3 = smt_usdt_d_sym

if smt_auto_profile == "BTC ⇄ ETH"
    smt_auto_ref1 := smt_eth_sym
    smt_auto_ref2 := smt_total_sym
    smt_auto_ref3 := smt_usdt_d_sym
else if smt_auto_profile == "BTC ⇄ TOTAL"
    smt_auto_ref1 := smt_total_sym
    smt_auto_ref2 := smt_eth_sym
    smt_auto_ref3 := smt_btc_d_sym
else if smt_auto_profile == "ETH ⇄ TOTAL2"
    smt_auto_ref1 := smt_total2_sym
    smt_auto_ref2 := smt_btc_sym
    smt_auto_ref3 := smt_usdt_d_sym
else if smt_auto_profile == "Dominance Context"
    smt_auto_ref1 := smt_btc_d_sym
    smt_auto_ref2 := smt_usdt_d_sym
    smt_auto_ref3 := smt_total_sym
else
    if smt_chart_is_btc
        smt_auto_ref1 := smt_eth_sym
        smt_auto_ref2 := smt_total_sym
        smt_auto_ref3 := smt_btc_d_sym
    else if smt_chart_is_eth
        smt_auto_ref1 := smt_btc_sym
        smt_auto_ref2 := smt_total2_sym
        smt_auto_ref3 := smt_usdt_d_sym
    else if smt_chart_is_bnb
        smt_auto_ref1 := smt_btc_sym
        smt_auto_ref2 := smt_total2_sym
        smt_auto_ref3 := smt_usdt_d_sym
    else if smt_chart_is_sol
        smt_auto_ref1 := smt_btc_sym
        smt_auto_ref2 := smt_total2_sym
        smt_auto_ref3 := smt_usdt_d_sym
    else if smt_chart_is_xrp
        smt_auto_ref1 := smt_btc_sym
        smt_auto_ref2 := smt_total2_sym
        smt_auto_ref3 := smt_usdt_d_sym
    else
        smt_auto_ref1 := smt_btc_sym
        smt_auto_ref2 := smt_eth_sym
        smt_auto_ref3 := smt_total2_sym

string smt_ref1 = smt_pair_mode == "Manual Symbols" ? smt_sym1 : smt_auto_ref1
string smt_ref2 = smt_pair_mode == "Manual Symbols" ? smt_sym2 : smt_auto_ref2
string smt_ref3 = smt_pair_mode == "Manual Symbols" ? smt_sym3 : smt_auto_ref3

smt_ref1_inverse = smt_pair_mode == "Manual Symbols" ? smt_inv1 : smt_dom_inverse and f_smt_is_dom(smt_ref1)
smt_ref2_inverse = smt_pair_mode == "Manual Symbols" ? smt_inv2 : smt_dom_inverse and f_smt_is_dom(smt_ref2)
smt_ref3_inverse = smt_pair_mode == "Manual Symbols" ? smt_inv3 : smt_dom_inverse and f_smt_is_dom(smt_ref3)

[c_smt_close, c_smt_ret, c_lp, c_pp, c_lh, c_phh, c_pl_age, c_ph_age, c_pl_strength, c_ph_strength, c_pl_atr_size, c_ph_atr_size, c_sweep_low_f, c_sweep_high_f, c_eq_low_f, c_eq_high_f, c_fvg_bull_f, c_fvg_bear_f, c_ob_bull_f, c_ob_bear_f, c_smt_bias, c_smt_pos] = request.security(syminfo.tickerid, smt_tf_eff, f_smt_inst_pack(smt_piv_lb), lookahead=barmerge.lookahead_off)

[r1_close, r1_ret, r1_lp, r1_pp, r1_lh, r1_phh, r1_pl_age, r1_ph_age, r1_pl_strength, r1_ph_strength, r1_pl_atr_size, r1_ph_atr_size, r1_sweep_low_f, r1_sweep_high_f, r1_eq_low_f, r1_eq_high_f, r1_fvg_bull_f, r1_fvg_bear_f, r1_ob_bull_f, r1_ob_bear_f, r1_smt_bias, r1_smt_pos] = request.security(smt_ref1, smt_tf_eff, f_smt_inst_pack(smt_piv_lb), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)

[r2_close, r2_ret, r2_lp, r2_pp, r2_lh, r2_phh, r2_pl_age, r2_ph_age, r2_pl_strength, r2_ph_strength, r2_pl_atr_size, r2_ph_atr_size, r2_sweep_low_f, r2_sweep_high_f, r2_eq_low_f, r2_eq_high_f, r2_fvg_bull_f, r2_fvg_bear_f, r2_ob_bull_f, r2_ob_bear_f, r2_smt_bias, r2_smt_pos] = request.security(smt_ref2, smt_tf_eff, f_smt_inst_pack(smt_piv_lb), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)

[r3_close, r3_ret, r3_lp, r3_pp, r3_lh, r3_phh, r3_pl_age, r3_ph_age, r3_pl_strength, r3_ph_strength, r3_pl_atr_size, r3_ph_atr_size, r3_sweep_low_f, r3_sweep_high_f, r3_eq_low_f, r3_eq_high_f, r3_fvg_bull_f, r3_fvg_bear_f, r3_ob_bull_f, r3_ob_bear_f, r3_smt_bias, r3_smt_pos] = request.security(smt_ref3, smt_tf_eff, f_smt_inst_pack(smt_piv_lb), lookahead=barmerge.lookahead_off, ignore_invalid_symbol=true)

// Correlation Engine
smt_corr1_raw = ta.correlation(c_smt_ret, r1_ret, smt_corr_len)
smt_corr2_raw = ta.correlation(c_smt_ret, r2_ret, smt_corr_len)
smt_corr3_raw = ta.correlation(c_smt_ret, r3_ret, smt_corr_len)

smt_corr1_abs = math.abs(nz(smt_corr1_raw, 0.0))
smt_corr2_abs = math.abs(nz(smt_corr2_raw, 0.0))
smt_corr3_abs = math.abs(nz(smt_corr3_raw, 0.0))

smt_corr1_ma = ta.ema(smt_corr1_abs, smt_corr_slope_len)
smt_corr2_ma = ta.ema(smt_corr2_abs, smt_corr_slope_len)
smt_corr3_ma = ta.ema(smt_corr3_abs, smt_corr_slope_len)

smt_corr1_dyn = smt_corr1_ma > 0 ? f_clamp(smt_corr1_abs / smt_corr1_ma, 0.35, 1.15) : 1.0
smt_corr2_dyn = smt_corr2_ma > 0 ? f_clamp(smt_corr2_abs / smt_corr2_ma, 0.35, 1.15) : 1.0
smt_corr3_dyn = smt_corr3_ma > 0 ? f_clamp(smt_corr3_abs / smt_corr3_ma, 0.35, 1.15) : 1.0

smt_corr_q1 = f_smt_corr_q(smt_corr1_raw, smt_corr_min) * math.min(smt_corr1_dyn, 1.0)
smt_corr_q2 = f_smt_corr_q(smt_corr2_raw, smt_corr_min) * math.min(smt_corr2_dyn, 1.0)
smt_corr_q3 = f_smt_corr_q(smt_corr3_raw, smt_corr_min) * math.min(smt_corr3_dyn, 1.0)

smt_corr_quality_den =
     (smt_corr_q1 > 0 ? 1.0 : 0.0) +
     (smt_corr_q2 > 0 ? 1.0 : 0.0) +
     (smt_corr_q3 > 0 ? 1.0 : 0.0)

smt_corr_quality =
     smt_corr_quality_den > 0 ?
     (smt_corr_q1 + smt_corr_q2 + smt_corr_q3) / smt_corr_quality_den :
     0.0

// Candle Validation
smt_candle_L =
     f_clamp(
         close_loc * 0.18 +
         body_frac * 0.12 +
         f_clamp(lower_wick / math.max(bar_range, syminfo.mintick), 0.0, 1.0) * 0.18 +
         f_clamp(body_atr / math.max(disp_atr, 0.0001), 0.0, 1.0) * 0.14 +
         (bull_engulf ? 0.14 : 0.0) +
         ((pin_bull or hammer) ? 0.12 : 0.0) +
         (is_displacement and close > open ? 0.12 : 0.0),
         0.0,
         1.0)

smt_candle_S =
     f_clamp(
         (1.0 - close_loc) * 0.18 +
         body_frac * 0.12 +
         f_clamp(upper_wick / math.max(bar_range, syminfo.mintick), 0.0, 1.0) * 0.18 +
         f_clamp(body_atr / math.max(disp_atr, 0.0001), 0.0, 1.0) * 0.14 +
         (bear_engulf ? 0.14 : 0.0) +
         ((pin_bear or shooting_star) ? 0.12 : 0.0) +
         (is_displacement and close < open ? 0.12 : 0.0),
         0.0,
         1.0)

// Liquidity Validation
smt_sweep_ctx_L =
     f_clamp(
         (sweep_low ? 0.55 : 0.0) +
         sweep_low_eff * 0.25 +
         (stop_hunt_low ? 0.20 : 0.0),
         0.0,
         1.0)

smt_sweep_ctx_S =
     f_clamp(
         (sweep_high ? 0.55 : 0.0) +
         sweep_high_eff * 0.25 +
         (stop_hunt_high ? 0.20 : 0.0),
         0.0,
         1.0)

smt_liq_ctx_L =
     f_clamp(
         rest_liq_low * 0.25 +
         smt_sweep_ctx_L * 0.30 +
         (equal_lows ? 0.10 : 0.0) +
         (int_equal_lows ? 0.08 : 0.0) +
         (ext_equal_lows ? 0.12 : 0.0) +
         external_low_prox * 0.10 +
         (inducement_long ? 0.15 : 0.0),
         0.0,
         1.0)

smt_liq_ctx_S =
     f_clamp(
         rest_liq_high * 0.25 +
         smt_sweep_ctx_S * 0.30 +
         (equal_highs ? 0.10 : 0.0) +
         (int_equal_highs ? 0.08 : 0.0) +
         (ext_equal_highs ? 0.12 : 0.0) +
         external_high_prox * 0.10 +
         (inducement_short ? 0.15 : 0.0),
         0.0,
         1.0)

smt_stop_ctx_L = stop_hunt_low ? 1.0 : 0.0
smt_stop_ctx_S = stop_hunt_high ? 1.0 : 0.0

// Structure Context
smt_struct_ctx_L =
     f_clamp(
         (mss_up ? 0.35 : 0.0) +
         (choch_up ? 0.25 : 0.0) +
         (bos_up ? 0.15 : 0.0) +
         (trend_dir >= 0 ? 0.10 : 0.0) +
         (int_bias >= 0 ? 0.05 : 0.0) +
         (ext_bias >= 0 ? 0.05 : 0.0) +
         break_quality_live * 0.05,
         0.0,
         1.0)

smt_struct_ctx_S =
     f_clamp(
         (mss_dn ? 0.35 : 0.0) +
         (choch_dn ? 0.25 : 0.0) +
         (bos_dn ? 0.15 : 0.0) +
         (trend_dir <= 0 ? 0.10 : 0.0) +
         (int_bias <= 0 ? 0.05 : 0.0) +
         (ext_bias <= 0 ? 0.05 : 0.0) +
         break_quality_live * 0.05,
         0.0,
         1.0)

// FVG / OB Context
smt_fvg_ctx_L =
     f_clamp(
         fvg_long_conf * 0.45 +
         (in_bull_fvg ? 0.25 : 0.0) +
         (new_bull_fvg ? 0.15 : 0.0) +
         (bullFVG_active ? 0.15 : 0.0),
         0.0,
         1.0)

smt_fvg_ctx_S =
     f_clamp(
         fvg_short_conf * 0.45 +
         (in_bear_fvg ? 0.25 : 0.0) +
         (new_bear_fvg ? 0.15 : 0.0) +
         (bearFVG_active ? 0.15 : 0.0),
         0.0,
         1.0)

smt_ob_ctx_L =
     f_clamp(
         ob_long_conf * 0.55 +
         (in_bull_ob ? 0.25 : 0.0) +
         ob_long_fresh * 0.20,
         0.0,
         1.0)

smt_ob_ctx_S =
     f_clamp(
         ob_short_conf * 0.55 +
         (in_bear_ob ? 0.25 : 0.0) +
         ob_short_fresh * 0.20,
         0.0,
         1.0)

// Trend / HTF / Crypto Context
smt_trend_ctx_L =
     f_clamp(
         (local_bull ? zpf_slope_norm : 0.0) +
         (kalman_bull ? 0.25 : 0.0) +
         (close > ema50 ? 0.15 : 0.0) +
         (close > ema200 ? 0.10 : 0.0) +
         (vwap_valid and close > vwap_val ? 0.15 : 0.0),
         0.0,
         1.0)

smt_trend_ctx_S =
     f_clamp(
         (local_bear ? 1.0 - zpf_slope_norm : 0.0) +
         (kalman_bear ? 0.25 : 0.0) +
         (close < ema50 ? 0.15 : 0.0) +
         (close < ema200 ? 0.10 : 0.0) +
         (vwap_valid and close < vwap_val ? 0.15 : 0.0),
         0.0,
         1.0)

smt_htf_ctx_L =
     f_clamp(
         (htf_bull_ctx ? 0.50 : htf_align == 0 ? 0.25 : 0.0) +
         (htf_in_discount ? 0.30 : 0.0) +
         (htf_long_ok ? 0.20 : 0.0),
         0.0,
         1.0)

smt_htf_ctx_S =
     f_clamp(
         (htf_bear_ctx ? 0.50 : htf_align == 0 ? 0.25 : 0.0) +
         (htf_in_premium ? 0.30 : 0.0) +
         (htf_short_ok ? 0.20 : 0.0),
         0.0,
         1.0)

smt_crypto_ctx_L =
     use_crypto_ctx ?
     f_clamp(0.50 + crypto_ctx_score * 0.50, 0.0, 1.0) :
     0.50

smt_crypto_ctx_S =
     use_crypto_ctx ?
     f_clamp(0.50 - crypto_ctx_score * 0.50, 0.0, 1.0) :
     0.50

// Premium / Discount / Internal / External Alignment
smt_pd_ctx_L =
     f_clamp(
         (in_discount ? 0.50 : 0.0) +
         (in_ote_long ? 0.30 : 0.0) +
         (htf_in_discount ? 0.20 : 0.0),
         0.0,
         1.0)

smt_pd_ctx_S =
     f_clamp(
         (in_premium ? 0.50 : 0.0) +
         (in_ote_short ? 0.30 : 0.0) +
         (htf_in_premium ? 0.20 : 0.0),
         0.0,
         1.0)

smt_internal_ctx_L =
     f_clamp(
         (int_equal_lows ? 0.30 : 0.0) +
         (int_bias >= 0 ? 0.25 : 0.0) +
         (not na(c_pl_age) and c_pl_age <= int_piv_lb * 3 ? 0.25 : 0.0) +
         (sweep_low ? 0.20 : 0.0),
         0.0,
         1.0)

smt_internal_ctx_S =
     f_clamp(
         (int_equal_highs ? 0.30 : 0.0) +
         (int_bias <= 0 ? 0.25 : 0.0) +
         (not na(c_ph_age) and c_ph_age <= int_piv_lb * 3 ? 0.25 : 0.0) +
         (sweep_high ? 0.20 : 0.0),
         0.0,
         1.0)

smt_external_ctx_L =
     f_clamp(
         external_low_prox * 0.35 +
         (ext_equal_lows ? 0.25 : 0.0) +
         (ext_bias >= 0 ? 0.20 : 0.0) +
         (sweep_low ? 0.20 : 0.0),
         0.0,
         1.0)

smt_external_ctx_S =
     f_clamp(
         external_high_prox * 0.35 +
         (ext_equal_highs ? 0.25 : 0.0) +
         (ext_bias <= 0 ? 0.20 : 0.0) +
         (sweep_high ? 0.20 : 0.0),
         0.0,
         1.0)

// Regime-Aware SMT Weighting Context
smt_regime_mult =
     is_ranging ? 1.12 :
     is_transition ? 1.04 :
     is_trending ? 0.88 :
     1.0

smt_regime_mult :=
     f_clamp(
         smt_regime_mult +
         (math.max(smt_sweep_ctx_L, smt_sweep_ctx_S) > 0.50 ? 0.06 : 0.0) -
         (market_entropy > entropy_max ? 0.08 : 0.0),
         0.75,
         1.20)

smt_enabled_core = use_smt and (not smt_crypto_only or smt_crypto_chart)

[
     smt_r1_bull,
     smt_r1_bear,
     smt_r1_bull_type_score,
     smt_r1_bear_type_score,
     smt_r1_bull_type_id_f,
     smt_r1_bear_type_id_f
] = f_smt_eval_ref(
     smt_enabled_core,
     smt_corr_q1,
     smt_ref1_inverse,
     c_lp,
     c_pp,
     c_lh,
     c_phh,
     c_pl_age,
     c_ph_age,
     r1_lp,
     r1_pp,
     r1_lh,
     r1_phh,
     r1_pl_age,
     r1_ph_age,
     r1_sweep_low_f,
     r1_sweep_high_f,
     r1_eq_low_f,
     r1_eq_high_f,
     r1_fvg_bull_f,
     r1_fvg_bear_f,
     r1_ob_bull_f,
     r1_ob_bear_f,
     smt_liq_ctx_L,
     smt_liq_ctx_S,
     smt_sweep_ctx_L,
     smt_sweep_ctx_S,
     smt_stop_ctx_L,
     smt_stop_ctx_S,
     smt_struct_ctx_L,
     smt_struct_ctx_S,
     smt_fvg_ctx_L,
     smt_fvg_ctx_S,
     smt_ob_ctx_L,
     smt_ob_ctx_S,
     smt_trend_ctx_L,
     smt_trend_ctx_S,
     smt_htf_ctx_L,
     smt_htf_ctx_S,
     smt_crypto_ctx_L,
     smt_crypto_ctx_S,
     smt_candle_L,
     smt_candle_S,
     smt_pd_ctx_L,
     smt_pd_ctx_S,
     smt_internal_ctx_L,
     smt_internal_ctx_S,
     smt_external_ctx_L,
     smt_external_ctx_S,
     smt_max_age,
     smt_decay_rate,
     smt_entry_window,
     smt_regime_mult)

[
     smt_r2_bull,
     smt_r2_bear,
     smt_r2_bull_type_score,
     smt_r2_bear_type_score,
     smt_r2_bull_type_id_f,
     smt_r2_bear_type_id_f
] = f_smt_eval_ref(
     smt_enabled_core,
     smt_corr_q2,
     smt_ref2_inverse,
     c_lp,
     c_pp,
     c_lh,
     c_phh,
     c_pl_age,
     c_ph_age,
     r2_lp,
     r2_pp,
     r2_lh,
     r2_phh,
     r2_pl_age,
     r2_ph_age,
     r2_sweep_low_f,
     r2_sweep_high_f,
     r2_eq_low_f,
     r2_eq_high_f,
     r2_fvg_bull_f,
     r2_fvg_bear_f,
     r2_ob_bull_f,
     r2_ob_bear_f,
     smt_liq_ctx_L,
     smt_liq_ctx_S,
     smt_sweep_ctx_L,
     smt_sweep_ctx_S,
     smt_stop_ctx_L,
     smt_stop_ctx_S,
     smt_struct_ctx_L,
     smt_struct_ctx_S,
     smt_fvg_ctx_L,
     smt_fvg_ctx_S,
     smt_ob_ctx_L,
     smt_ob_ctx_S,
     smt_trend_ctx_L,
     smt_trend_ctx_S,
     smt_htf_ctx_L,
     smt_htf_ctx_S,
     smt_crypto_ctx_L,
     smt_crypto_ctx_S,
     smt_candle_L,
     smt_candle_S,
     smt_pd_ctx_L,
     smt_pd_ctx_S,
     smt_internal_ctx_L,
     smt_internal_ctx_S,
     smt_external_ctx_L,
     smt_external_ctx_S,
     smt_max_age,
     smt_decay_rate,
     smt_entry_window,
     smt_regime_mult)

[
     smt_r3_bull,
     smt_r3_bear,
     smt_r3_bull_type_score,
     smt_r3_bear_type_score,
     smt_r3_bull_type_id_f,
     smt_r3_bear_type_id_f
] = f_smt_eval_ref(
     smt_enabled_core,
     smt_corr_q3,
     smt_ref3_inverse,
     c_lp,
     c_pp,
     c_lh,
     c_phh,
     c_pl_age,
     c_ph_age,
     r3_lp,
     r3_pp,
     r3_lh,
     r3_phh,
     r3_pl_age,
     r3_ph_age,
     r3_sweep_low_f,
     r3_sweep_high_f,
     r3_eq_low_f,
     r3_eq_high_f,
     r3_fvg_bull_f,
     r3_fvg_bear_f,
     r3_ob_bull_f,
     r3_ob_bear_f,
     smt_liq_ctx_L,
     smt_liq_ctx_S,
     smt_sweep_ctx_L,
     smt_sweep_ctx_S,
     smt_stop_ctx_L,
     smt_stop_ctx_S,
     smt_struct_ctx_L,
     smt_struct_ctx_S,
     smt_fvg_ctx_L,
     smt_fvg_ctx_S,
     smt_ob_ctx_L,
     smt_ob_ctx_S,
     smt_trend_ctx_L,
     smt_trend_ctx_S,
     smt_htf_ctx_L,
     smt_htf_ctx_S,
     smt_crypto_ctx_L,
     smt_crypto_ctx_S,
     smt_candle_L,
     smt_candle_S,
     smt_pd_ctx_L,
     smt_pd_ctx_S,
     smt_internal_ctx_L,
     smt_internal_ctx_S,
     smt_external_ctx_L,
     smt_external_ctx_S,
     smt_max_age,
     smt_decay_rate,
     smt_entry_window,
     smt_regime_mult)

smt_refs =
     (smt_corr_q1 > 0 ? 1.0 : 0.0) +
     (smt_corr_q2 > 0 ? 1.0 : 0.0) +
     (smt_corr_q3 > 0 ? 1.0 : 0.0)

smt_now_L =
     smt_refs > 0 ?
     (smt_r1_bull + smt_r2_bull + smt_r3_bull) / smt_refs :
     0.0

smt_now_S =
     smt_refs > 0 ?
     (smt_r1_bear + smt_r2_bear + smt_r3_bear) / smt_refs :
     0.0

smt_best_L = math.max(smt_r1_bull, math.max(smt_r2_bull, smt_r3_bull))
smt_best_S = math.max(smt_r1_bear, math.max(smt_r2_bear, smt_r3_bear))

smt_bull_type_id =
     smt_r1_bull >= smt_r2_bull and smt_r1_bull >= smt_r3_bull ? int(smt_r1_bull_type_id_f) :
     smt_r2_bull >= smt_r1_bull and smt_r2_bull >= smt_r3_bull ? int(smt_r2_bull_type_id_f) :
     int(smt_r3_bull_type_id_f)

smt_bear_type_id =
     smt_r1_bear >= smt_r2_bear and smt_r1_bear >= smt_r3_bear ? int(smt_r1_bear_type_id_f) :
     smt_r2_bear >= smt_r1_bear and smt_r2_bear >= smt_r3_bear ? int(smt_r2_bear_type_id_f) :
     int(smt_r3_bear_type_id_f)

smt_bull_ref =
     smt_r1_bull >= smt_r2_bull and smt_r1_bull >= smt_r3_bull ? smt_ref1 :
     smt_r2_bull >= smt_r1_bull and smt_r2_bull >= smt_r3_bull ? smt_ref2 :
     smt_ref3

smt_bear_ref =
     smt_r1_bear >= smt_r2_bear and smt_r1_bear >= smt_r3_bear ? smt_ref1 :
     smt_r2_bear >= smt_r1_bear and smt_r2_bear >= smt_r3_bear ? smt_ref2 :
     smt_ref3

smt_primary_L = f_smt_type_name(smt_bull_type_id)
smt_primary_S = f_smt_type_name(smt_bear_type_id)

// Lifecycle / Merge Engine
var array<SMTEvent> smt_events = array.new<SMTEvent>()

smt_origin_L = not na(c_lp) ? c_lp : low
smt_origin_S = not na(c_lh) ? c_lh : high

smt_bull_event =
     smt_enabled_core and
     barstate.isconfirmed and
     smt_now_L >= smt_min_score and
     smt_now_L > smt_now_S + 0.05 and
     smt_bull_type_id > 0 and
     nz(smt_now_L[1], 0.0) < smt_min_score

smt_bear_event =
     smt_enabled_core and
     barstate.isconfirmed and
     smt_now_S >= smt_min_score and
     smt_now_S > smt_now_L + 0.05 and
     smt_bear_type_id > 0 and
     nz(smt_now_S[1], 0.0) < smt_min_score

if smt_bull_event
    merged = false

    if array.size(smt_events) > 0
        for i = 0 to array.size(smt_events) - 1
            ev = array.get(smt_events, i)
            samePool =
                 ev.dir == 1 and
                 bar_index - ev.born <= smt_merge_bars and
                 math.abs(ev.origin - smt_origin_L) <= atr_val * smt_merge_atr

            if samePool
                ev.quality := f_clamp(math.max(ev.quality, smt_now_L) + math.min(ev.quality, smt_now_L) * 0.25, 0.0, 1.0)
                ev.corrQ := math.max(ev.corrQ, smt_corr_quality)
                ev.liqQ := math.max(ev.liqQ, smt_liq_ctx_L)
                ev.kind := smt_primary_L
                ev.ref := smt_bull_ref

                if smt_show_events and not na(ev.lb)
                    label.set_text(
                         ev.lb,
                         "Bull iSMT Merge\n" +
                         ev.kind + "\n" +
                         f_smt_conf_label(ev.quality) + " · " +
                         str.tostring(ev.quality * 100.0, "#") + "%")

                array.set(smt_events, i, ev)
                merged := true
                break

    if not merged
        lb =
             smt_show_events ?
             label.new(
                 bar_index,
                 low - atr_val * 0.35,
                 "Bull iSMT\n" +
                 smt_primary_L + "\n" +
                 f_smt_conf_label(smt_now_L) + " · " +
                 str.tostring(smt_now_L * 100.0, "#") + "%",
                 xloc=xloc.bar_index,
                 yloc=yloc.price,
                 style=label.style_label_up,
                 color=color.new(bull_col, 0),
                 textcolor=text_col,
                 size=size.tiny) :
             na

        array.push(
             smt_events,
             SMTEvent.new(
                 1,
                 smt_origin_L,
                 smt_now_L,
                 smt_corr_quality,
                 smt_liq_ctx_L,
                 bar_index,
                 0,
                 smt_primary_L,
                 smt_bull_ref,
                 lb))

if smt_bear_event
    merged = false

    if array.size(smt_events) > 0
        for i = 0 to array.size(smt_events) - 1
            ev = array.get(smt_events, i)
            samePool =
                 ev.dir == -1 and
                 bar_index - ev.born <= smt_merge_bars and
                 math.abs(ev.origin - smt_origin_S) <= atr_val * smt_merge_atr

            if samePool
                ev.quality := f_clamp(math.max(ev.quality, smt_now_S) + math.min(ev.quality, smt_now_S) * 0.25, 0.0, 1.0)
                ev.corrQ := math.max(ev.corrQ, smt_corr_quality)
                ev.liqQ := math.max(ev.liqQ, smt_liq_ctx_S)
                ev.kind := smt_primary_S
                ev.ref := smt_bear_ref

                if smt_show_events and not na(ev.lb)
                    label.set_text(
                         ev.lb,
                         "Bear iSMT Merge\n" +
                         ev.kind + "\n" +
                         f_smt_conf_label(ev.quality) + " · " +
                         str.tostring(ev.quality * 100.0, "#") + "%")

                array.set(smt_events, i, ev)
                merged := true
                break

    if not merged
        lb =
             smt_show_events ?
             label.new(
                 bar_index,
                 high + atr_val * 0.35,
                 "Bear iSMT\n" +
                 smt_primary_S + "\n" +
                 f_smt_conf_label(smt_now_S) + " · " +
                 str.tostring(smt_now_S * 100.0, "#") + "%",
                 xloc=xloc.bar_index,
                 yloc=yloc.price,
                 style=label.style_label_down,
                 color=color.new(bear_col, 0),
                 textcolor=text_col,
                 size=size.tiny) :
             na

        array.push(
             smt_events,
             SMTEvent.new(
                 -1,
                 smt_origin_S,
                 smt_now_S,
                 smt_corr_quality,
                 smt_liq_ctx_S,
                 bar_index,
                 0,
                 smt_primary_S,
                 smt_bear_ref,
                 lb))

while array.size(smt_events) > smt_event_cap
    oldEv = array.shift(smt_events)
    f_delete_label(oldEv.lb)

float smt_life_L = 0.0
float smt_life_S = 0.0
float smt_fail_to_bull = 0.0
float smt_fail_to_bear = 0.0

ei = array.size(smt_events) - 1
while ei >= 0
    ev = array.get(smt_events, ei)
    age = bar_index - ev.born
    qLive = f_clamp(ev.quality * math.pow(smt_decay_rate, age), 0.0, 1.0)

    if ev.state == 0 and age > 0
        ev.state := 1

    if ev.dir == 1
        confirmed = mss_up or choch_up or bull_engulf or close > high[1]
        triggered = high >= ev.origin + atr_val * 0.75
        mitigated = high >= ev.origin + atr_val * 2.0 and age > 1
        broken =
             close < ev.origin - atr_val * smt_failure_atr or
             strong_break_dn or
             (smt_now_S > smt_now_L + 0.35 and age <= smt_entry_window)

        if broken
            ev.state := 5
            smt_fail_to_bear := math.max(smt_fail_to_bear, qLive)
        else
            if ev.state < 2 and confirmed
                ev.state := 2
            if ev.state < 3 and triggered
                ev.state := 3
            if ev.state < 4 and mitigated
                ev.state := 4

            stFactor =
                 ev.state == 0 ? 0.55 :
                 ev.state == 1 ? 0.65 :
                 ev.state == 2 ? 1.00 :
                 ev.state == 3 ? 0.82 :
                 ev.state == 4 ? 0.35 :
                 0.0

            smt_life_L := math.max(smt_life_L, qLive * stFactor)

    if ev.dir == -1
        confirmed = mss_dn or choch_dn or bear_engulf or close < low[1]
        triggered = low <= ev.origin - atr_val * 0.75
        mitigated = low <= ev.origin - atr_val * 2.0 and age > 1
        broken =
             close > ev.origin + atr_val * smt_failure_atr or
             strong_break_up or
             (smt_now_L > smt_now_S + 0.35 and age <= smt_entry_window)

        if broken
            ev.state := 5
            smt_fail_to_bull := math.max(smt_fail_to_bull, qLive)
        else
            if ev.state < 2 and confirmed
                ev.state := 2
            if ev.state < 3 and triggered
                ev.state := 3
            if ev.state < 4 and mitigated
                ev.state := 4

            stFactor =
                 ev.state == 0 ? 0.55 :
                 ev.state == 1 ? 0.65 :
                 ev.state == 2 ? 1.00 :
                 ev.state == 3 ? 0.82 :
                 ev.state == 4 ? 0.35 :
                 0.0

            smt_life_S := math.max(smt_life_S, qLive * stFactor)

    if smt_show_events and not na(ev.lb)
        label.set_text(
             ev.lb,
             (ev.dir == 1 ? "Bull iSMT\n" : "Bear iSMT\n") +
             ev.kind + "\n" +
             f_smt_state_name(ev.state) + " · " +
             str.tostring(qLive * 100.0, "#") + "%")

        label.set_color(
             ev.lb,
             ev.state == 5 ? color.new(color.gray, 0) :
             ev.dir == 1 ? color.new(bull_col, 0) :
             color.new(bear_col, 0))

    expired =
         age > smt_event_max_age or
         qLive < 0.04 or
         ev.state == 5 and age > smt_entry_window

    if expired
        f_delete_label(ev.lb)
        array.remove(smt_events, ei)
    else
        array.set(smt_events, ei, ev)

    ei -= 1

smt_bull_score =
     use_smt ?
     f_clamp(
         math.max(smt_now_L, smt_life_L) +
         smt_fail_to_bull * 0.25,
         0.0,
         1.0) :
     0.0

smt_bear_score =
     use_smt ?
     f_clamp(
         math.max(smt_now_S, smt_life_S) +
         smt_fail_to_bear * 0.25,
         0.0,
         1.0) :
     0.0

smt_conf_L_str = f_smt_conf_label(smt_bull_score)
smt_conf_S_str = f_smt_conf_label(smt_bear_score)

//──────────────────────────────────────────────────────────────────────
// STATE VECTOR
//──────────────────────────────────────────────────────────────────────
struct_pulse = (bos_up or choch_up) ? 1.0 : (bos_dn or choch_dn) ? -1.0 : 0.0
struct_mom = ta.ema(struct_pulse, 10)
struct_mom_L = f_clamp(math.max(struct_mom, 0.0), 0.0, 1.0)
struct_mom_S = f_clamp(math.max(-struct_mom, 0.0), 0.0, 1.0)

ev_struct_L = f_clamp(((strong_break_up ? 1.0 : weak_bos_up ? 0.55 : trend_dir == 1 ? 0.35 : 0.0) * (0.55 + 0.45 * break_quality_live)) + struct_mom_L * 0.15, 0.0, 1.0)
ev_struct_S = f_clamp(((strong_break_dn ? 1.0 : weak_bos_dn ? 0.55 : trend_dir == -1 ? 0.35 : 0.0) * (0.55 + 0.45 * break_quality_live)) + struct_mom_S * 0.15, 0.0, 1.0)

ev_liq_L = (sweep_low or spring) ? f_clamp(0.40 + sweep_low_eff * 0.25 + rest_liq_low * 0.20 + (spring ? 0.10 : 0.0) + (stop_hunt_low ? 0.10 : 0.0) + (inducement_long ? 0.10 : 0.0), 0.0, 1.0) : 0.0
ev_liq_S = (sweep_high or upthrust) ? f_clamp(0.40 + sweep_high_eff * 0.25 + rest_liq_high * 0.20 + (upthrust ? 0.10 : 0.0) + (stop_hunt_high ? 0.10 : 0.0) + (inducement_short ? 0.10 : 0.0), 0.0, 1.0) : 0.0

ev_ob_L = ob_long_conf
ev_ob_S = ob_short_conf
ev_fvg_L = fvg_long_conf
ev_fvg_S = fvg_short_conf

ev_zone_L = f_clamp((in_discount ? 0.40 : 0.0) + (in_ote_long ? 0.30 : 0.0) + (htf_in_discount ? 0.20 : 0.0) + (vwap_dev_z < -1.25 ? 0.10 : 0.0), 0.0, 1.0)
ev_zone_S = f_clamp((in_premium ? 0.40 : 0.0) + (in_ote_short ? 0.30 : 0.0) + (htf_in_premium ? 0.20 : 0.0) + (vwap_dev_z > 1.25 ? 0.10 : 0.0), 0.0, 1.0)

ev_dna_L = dna_bull
ev_dna_S = dna_bear
ev_kin_L = kin_long
ev_kin_S = kin_short

ev_delta_L = f_clamp((aggression > 0 ? f_clamp(aggression, 0.0, 1.0) * 0.40 : 0.0) + (absorption_buy ? 0.25 : 0.0) + (sos ? 0.15 : 0.0) + (selling_climax ? 0.20 : 0.0), 0.0, 1.0)
ev_delta_S = f_clamp((aggression < 0 ? f_clamp(-aggression, 0.0, 1.0) * 0.40 : 0.0) + (absorption_sell ? 0.25 : 0.0) + (sow ? 0.15 : 0.0) + (buying_climax ? 0.20 : 0.0), 0.0, 1.0)

// Signal Sequences
ev_seq_L = f_clamp(seq_bull_bias + (dir_flip_bull ? 0.15 : 0.0), 0.0, 1.0)
ev_seq_S = f_clamp(seq_bear_bias + (dir_flip_bear ? 0.15 : 0.0), 0.0, 1.0)

ev_trend_L = f_clamp((local_bull ? zpf_slope_norm : 0.0) + (vwap_valid and close > vwap_val ? 0.12 : 0.0) + (use_kalman_signal_filter and kalman_bull ? 0.15 : 0.0), 0.0, 1.0)
ev_trend_S = f_clamp((local_bear ? 1.0 - zpf_slope_norm : 0.0) + (vwap_valid and close < vwap_val ? 0.12 : 0.0) + (use_kalman_signal_filter and kalman_bear ? 0.15 : 0.0), 0.0, 1.0)

ev_mtf_L = f_clamp((int_bias > 0 ? 0.22 : 0.0) + (trend_dir == 1 ? 0.26 : 0.0) + (ext_bias > 0 ? 0.22 : 0.0) + (htf1_bias > 0 ? 0.15 : 0.0) + (htf2_bias > 0 ? 0.15 : 0.0), 0.0, 1.0)
ev_mtf_S = f_clamp((int_bias < 0 ? 0.22 : 0.0) + (trend_dir == -1 ? 0.26 : 0.0) + (ext_bias < 0 ? 0.22 : 0.0) + (htf1_bias < 0 ? 0.15 : 0.0) + (htf2_bias < 0 ? 0.15 : 0.0), 0.0, 1.0)

ev_smt_L = smt_bull_score
ev_smt_S = smt_bear_score

vp_L = use_volume_profile and not na(vp_poc) ? f_clamp((close > vp_poc ? 0.40 : 0.0) + vp_acceptance * 0.30 + (vwap_valid and close > vwap_val ? 0.20 : 0.0) + (vp_dist_atr < 1.0 ? 0.10 : 0.0), 0.0, 1.0) : 0.0
vp_S = use_volume_profile and not na(vp_poc) ? f_clamp((close < vp_poc ? 0.40 : 0.0) + vp_acceptance * 0.30 + (vwap_valid and close < vwap_val ? 0.20 : 0.0) + (vp_dist_atr < 1.0 ? 0.10 : 0.0), 0.0, 1.0) : 0.0
ev_profile_L = vp_L
ev_profile_S = vp_S

//──────────────────────────────────────────────────────────────────────
// ADAPTIVE WEIGHTS
//──────────────────────────────────────────────────────────────────────
tc = trend_conf
bw0 = 0.12 + 0.10 * tc
bw1 = 0.20 - 0.10 * tc
bw2 = 0.15 - 0.05 * tc
bw3 = 0.10 - 0.02 * tc
bw4 = 0.12 - 0.06 * tc
bw5 = 0.10
bw6 = 0.08 + 0.07 * tc
bw7 = 0.08
bw8 = 0.03 + 0.03 * tc
bw9 = 0.06 - 0.03 * tc
bw10 = 0.08
bw11 =
     use_smt ?
     f_clamp(
         0.035 +
         (is_ranging ? 0.055 : 0.0) +
         (is_transition ? 0.030 : 0.0) +
         math.max(ev_liq_L, ev_liq_S) * 0.045 +
         smt_corr_quality * 0.030 -
         trend_conf * 0.030,
         0.010,
         0.150) :
     0.0

bw12 = use_volume_profile ? 0.06 : 0.0

feat0 = ev_struct_L - ev_struct_S
feat1 = ev_liq_L - ev_liq_S
feat2 = ev_ob_L - ev_ob_S
feat3 = ev_fvg_L - ev_fvg_S
feat4 = ev_zone_L - ev_zone_S
feat5 = ev_dna_L - ev_dna_S
feat6 = ev_kin_L - ev_kin_S
feat7 = ev_delta_L - ev_delta_S
feat8 = ev_seq_L - ev_seq_S
feat9 = ev_trend_L - ev_trend_S
feat10 = ev_mtf_L - ev_mtf_S
feat11 = ev_smt_L - ev_smt_S
feat12 = ev_profile_L - ev_profile_S

ic0 = f_ic(feat0, ic_horizon, ic_len)
ic1 = f_ic(feat1, ic_horizon, ic_len)
ic2 = f_ic(feat2, ic_horizon, ic_len)
ic3 = f_ic(feat3, ic_horizon, ic_len)
ic4 = f_ic(feat4, ic_horizon, ic_len)
ic5 = f_ic(feat5, ic_horizon, ic_len)
ic6 = f_ic(feat6, ic_horizon, ic_len)
ic7 = f_ic(feat7, ic_horizon, ic_len)
ic8 = f_ic(feat8, ic_horizon, ic_len)
ic9 = f_ic(feat9, ic_horizon, ic_len)
ic10 = f_ic(feat10, ic_horizon, ic_len)
ic11 = f_ic(feat11, ic_horizon, ic_len)
ic12 = f_ic(feat12, ic_horizon, ic_len)

f_ic_factor(_ic) =>
    use_adaptive_weights ? f_clamp(1.0 + _ic * ic_strength, 0.65, 1.35) : 1.0

rw0 = bw0 * f_feature_factor(0) * f_ic_factor(ic0)
rw1 = bw1 * f_feature_factor(1) * f_ic_factor(ic1)
rw2 = bw2 * f_feature_factor(2) * f_ic_factor(ic2)
rw3 = bw3 * f_feature_factor(3) * f_ic_factor(ic3)
rw4 = bw4 * f_feature_factor(4) * f_ic_factor(ic4)
rw5 = bw5 * f_feature_factor(5) * f_ic_factor(ic5)
rw6 = bw6 * f_feature_factor(6) * f_ic_factor(ic6)
rw7 = bw7 * f_feature_factor(7) * f_ic_factor(ic7)
rw8 = bw8 * f_feature_factor(8) * f_ic_factor(ic8)
rw9 = bw9 * f_feature_factor(9) * f_ic_factor(ic9)
rw10 = bw10 * f_feature_factor(10) * f_ic_factor(ic10)
rw11 = bw11 * f_feature_factor(11) * f_ic_factor(ic11)
rw12 = bw12 * f_feature_factor(12) * f_ic_factor(ic12)

w_sum = rw0 + rw1 + rw2 + rw3 + rw4 + rw5 + rw6 + rw7 + rw8 + rw9 + rw10 + rw11 + rw12
w0 = rw0 / w_sum
w1 = rw1 / w_sum
w2 = rw2 / w_sum
w3 = rw3 / w_sum
w4 = rw4 / w_sum
w5 = rw5 / w_sum
w6 = rw6 / w_sum
w7 = rw7 / w_sum
w8 = rw8 / w_sum
w9 = rw9 / w_sum
w10 = rw10 / w_sum
w11 = rw11 / w_sum
w12 = rw12 / w_sum

base_L = w0*ev_struct_L + w1*ev_liq_L + w2*ev_ob_L + w3*ev_fvg_L + w4*ev_zone_L + w5*ev_dna_L + w6*ev_kin_L + w7*ev_delta_L + w8*ev_seq_L + w9*ev_trend_L + w10*ev_mtf_L + w11*ev_smt_L + w12*ev_profile_L
base_S = w0*ev_struct_S + w1*ev_liq_S + w2*ev_ob_S + w3*ev_fvg_S + w4*ev_zone_S + w5*ev_dna_S + w6*ev_kin_S + w7*ev_delta_S + w8*ev_seq_S + w9*ev_trend_S + w10*ev_mtf_S + w11*ev_smt_S + w12*ev_profile_S

inter_L = 0.0
inter_L += ev_liq_L * ev_ob_L * 0.14
inter_L += ev_liq_L * ev_struct_L * 0.14
inter_L += ev_ob_L * ev_fvg_L * 0.10
inter_L += ev_struct_L * ev_mtf_L * 0.10
inter_L += ev_smt_L * ev_liq_L * 0.09
inter_L += ev_delta_L * ev_struct_L * 0.06
inter_L += ev_dna_L * ev_kin_L * 0.06
inter_L += (ifvg_bull ? 1.0 : 0.0) * ev_struct_L * 0.05
inter_L += (bpr_bull ? 1.0 : 0.0) * ev_zone_L * 0.04

inter_S = 0.0
inter_S += ev_liq_S * ev_ob_S * 0.14
inter_S += ev_liq_S * ev_struct_S * 0.14
inter_S += ev_ob_S * ev_fvg_S * 0.10
inter_S += ev_struct_S * ev_mtf_S * 0.10
inter_S += ev_smt_S * ev_liq_S * 0.09
inter_S += ev_delta_S * ev_struct_S * 0.06
inter_S += ev_dna_S * ev_kin_S * 0.06
inter_S += (ifvg_bear ? 1.0 : 0.0) * ev_struct_S * 0.05
inter_S += (bpr_bear ? 1.0 : 0.0) * ev_zone_S * 0.04

pen_L = 0.0
pen_L += use_htf and htf_bear_ctx ? 0.25 : 0.0
pen_L += htf_in_premium ? 0.08 : 0.0
pen_L += is_compression ? 0.08 : 0.0
pen_L += use_kalman_signal_filter and kalman_bear and not sweep_low ? 0.08 : 0.0
pen_L += ob_long_conf > 0 and ob_long_fresh < 0.20 ? 0.07 : 0.0
pen_L += vwap_dev_z > 2.0 and not sweep_low ? 0.07 : 0.0
pen_L += effort_result > 0 and dir_now == -1 ? 0.04 : 0.0
pen_L += ev_smt_S > 0.5 ? 0.08 : 0.0

pen_S = 0.0
pen_S += use_htf and htf_bull_ctx ? 0.25 : 0.0
pen_S += htf_in_discount ? 0.08 : 0.0
pen_S += is_compression ? 0.08 : 0.0
pen_S += use_kalman_signal_filter and kalman_bull and not sweep_high ? 0.08 : 0.0
pen_S += ob_short_conf > 0 and ob_short_fresh < 0.20 ? 0.07 : 0.0
pen_S += vwap_dev_z < -2.0 and not sweep_high ? 0.07 : 0.0
pen_S += effort_result > 0 and dir_now == 1 ? 0.04 : 0.0
pen_S += ev_smt_L > 0.5 ? 0.08 : 0.0

crypto_bonus_L = use_crypto_ctx ? math.max(crypto_ctx_score, 0.0) * 0.08 : 0.0
crypto_bonus_S = use_crypto_ctx ? math.max(-crypto_ctx_score, 0.0) * 0.08 : 0.0

raw_L = base_L + inter_L + crypto_bonus_L - pen_L
raw_S = base_S + inter_S + crypto_bonus_S - pen_S

cal_gain = 5.4 + trend_conf * 1.2
prob_L_raw = f_squash((raw_L - 0.45) * cal_gain)
prob_S_raw = f_squash((raw_S - 0.45) * cal_gain)

//──────────────────────────────────────────────────────────────────────
// SETUP CLASSIFICATION / META LEARNING
//──────────────────────────────────────────────────────────────────────
string setup_L = ""
if smt_bull_score > 0 and sweep_low and mss_up
    setup_L := "SMT Turtle Soup Long"
else if pin_bull and sweep_low and in_bull_ob and mss_up
    setup_L := "Institutional Long"
else if sweep_low and bull_engulf and (bos_up or choch_up) and bullFVG_active
    setup_L := "Turtle Soup Long"
else if sweep_low and in_bull_ob and choch_up and ev_dna_L > 0.6
    setup_L := "OB Reversal Long"
else if bull_breaker and mss_up
    setup_L := "Breaker Long"
else if spring and selling_climax
    setup_L := "Wyckoff Spring"
else if is_compression[1] and strong_break_up
    setup_L := "Compression Breakout Long"
else if in_discount and sweep_low and mss_up and in_bull_ob
    setup_L := "Premium/Discount Long"
else if hammer and equal_lows and sweep_low and mss_up
    setup_L := "High-Probability Reversal Long"
else if strong_break_up and bullFVG_active and in_bull_ob
    setup_L := "FVG Continuation Long"
else if bpr_bull and ev_zone_L > 0.5 and ev_struct_L > 0.4
    setup_L := "BPR Rebalance Long"
else if in_bull_ob and in_bull_fvg and ev_mtf_L > 0.6
    setup_L := "Nested OB/FVG Long"

string setup_S = ""
if smt_bear_score > 0 and sweep_high and mss_dn
    setup_S := "SMT Turtle Soup Short"
else if pin_bear and sweep_high and in_bear_ob and mss_dn
    setup_S := "Institutional Short"
else if sweep_high and bear_engulf and (bos_dn or choch_dn) and bearFVG_active
    setup_S := "Turtle Soup Short"
else if sweep_high and in_bear_ob and choch_dn and ev_dna_S > 0.6
    setup_S := "OB Reversal Short"
else if bear_breaker and mss_dn
    setup_S := "Breaker Short"
else if upthrust and buying_climax
    setup_S := "Wyckoff Upthrust"
else if is_compression[1] and strong_break_dn
    setup_S := "Compression Breakout Short"
else if in_premium and sweep_high and mss_dn and in_bear_ob
    setup_S := "Premium/Discount Short"
else if shooting_star and equal_highs and sweep_high and mss_dn
    setup_S := "High-Probability Reversal Short"
else if strong_break_dn and bearFVG_active and in_bear_ob
    setup_S := "FVG Continuation Short"
else if bpr_bear and ev_zone_S > 0.5 and ev_struct_S > 0.4
    setup_S := "BPR Rebalance Short"
else if in_bear_ob and in_bear_fvg and ev_mtf_S > 0.6
    setup_S := "Nested OB/FVG Short"

setup_L_name = setup_L == "" ? "Confluence Long" : setup_L
setup_S_name = setup_S == "" ? "Confluence Short" : setup_S

perf_factor_L = f_setup_factor(setup_L_name)
perf_factor_S = f_setup_factor(setup_S_name)

prob_L_meta = f_clamp(prob_L_raw * perf_factor_L, 0.01, 0.99)
prob_S_meta = f_clamp(prob_S_raw * perf_factor_S, 0.01, 0.99)

prob_L_cal = f_calibrate(prob_L_meta)
prob_S_cal = f_calibrate(prob_S_meta)

prob_L_smooth = ta.ema(prob_L_cal, prob_smooth_len)
prob_S_smooth = ta.ema(prob_S_cal, prob_smooth_len)

prob_L = f_clamp(use_prob_smoothing and prob_smooth_len > 1 ? prob_L_smooth : prob_L_cal, 0.01, 0.99)
prob_S = f_clamp(use_prob_smoothing and prob_smooth_len > 1 ? prob_S_smooth : prob_S_cal, 0.01, 0.99)

//──────────────────────────────────────────────────────────────────────
// CONTRIBUTORS / UNCERTAINTY / EXPECTANCY
//──────────────────────────────────────────────────────────────────────
contributors_L = 0
contributors_L += ev_struct_L > 0.35 ? 1 : 0
contributors_L += ev_liq_L > 0.35 ? 1 : 0
contributors_L += ev_ob_L > 0.25 ? 1 : 0
contributors_L += ev_fvg_L > 0.25 ? 1 : 0
contributors_L += ev_zone_L > 0.35 ? 1 : 0
contributors_L += ev_dna_L > 0.45 ? 1 : 0
contributors_L += ev_kin_L > 0.35 ? 1 : 0
contributors_L += ev_delta_L > 0.35 ? 1 : 0
contributors_L += ev_seq_L > 0.35 ? 1 : 0
contributors_L += ev_trend_L > 0.35 ? 1 : 0
contributors_L += ev_mtf_L > 0.45 ? 1 : 0
contributors_L += ev_smt_L > 0.25 ? 1 : 0
contributors_L += ev_profile_L > 0.35 ? 1 : 0

contributors_S = 0
contributors_S += ev_struct_S > 0.35 ? 1 : 0
contributors_S += ev_liq_S > 0.35 ? 1 : 0
contributors_S += ev_ob_S > 0.25 ? 1 : 0
contributors_S += ev_fvg_S > 0.25 ? 1 : 0
contributors_S += ev_zone_S > 0.35 ? 1 : 0
contributors_S += ev_dna_S > 0.45 ? 1 : 0
contributors_S += ev_kin_S > 0.35 ? 1 : 0
contributors_S += ev_delta_S > 0.35 ? 1 : 0
contributors_S += ev_seq_S > 0.35 ? 1 : 0
contributors_S += ev_trend_S > 0.35 ? 1 : 0
contributors_S += ev_mtf_S > 0.45 ? 1 : 0
contributors_S += ev_smt_S > 0.25 ? 1 : 0
contributors_S += ev_profile_S > 0.35 ? 1 : 0

chosen_contrib = prob_L >= prob_S ? contributors_L : contributors_S
thin_evidence = chosen_contrib < min_contributors
ambiguity = 1.0 - math.abs(prob_L - prob_S)
uncertainty = f_clamp(0.38 * ambiguity + 0.28 * ret_entropy + 0.15 * (is_transition ? 1.0 : 0.0) + 0.12 * (thin_evidence ? 1.0 : 0.0) + 0.07 * math.max(vol_cluster, 0.0), 0.0, 1.0)

catalyst_L = math.max(math.max(ev_struct_L, ev_liq_L), math.max(ev_ob_L, ev_fvg_L))
catalyst_S = math.max(math.max(ev_struct_S, ev_liq_S), math.max(ev_ob_S, ev_fvg_S))

base_rr = tp_mult / sl_mult
tp3_rr_reference = base_rr * 1.50

target_room_L = not na(htf1_hi) and htf1_hi > close and atr_val > 0 ? (htf1_hi - close) / math.max(atr_val * tp_mult, syminfo.mintick) : 1.0
target_room_S = not na(htf1_lo) and htf1_lo < close and atr_val > 0 ? (close - htf1_lo) / math.max(atr_val * tp_mult, syminfo.mintick) : 1.0

rr_quality_L = f_clamp(0.75 + 0.20 * f_clamp(target_room_L, 0.0, 1.5) + 0.15 * catalyst_L - 0.10 * uncertainty, 0.50, 1.30)
rr_quality_S = f_clamp(0.75 + 0.20 * f_clamp(target_room_S, 0.0, 1.5) + 0.15 * catalyst_S - 0.10 * uncertainty, 0.50, 1.30)

expected_rr_L = tp3_rr_reference * rr_quality_L
expected_rr_S = tp3_rr_reference * rr_quality_S

expected_R_L = prob_L * expected_rr_L - (1.0 - prob_L) - fee_slippage_R
expected_R_S = prob_S * expected_rr_S - (1.0 - prob_S) - fee_slippage_R

signal_confidence_L = prob_L * (1.0 - uncertainty) * f_clamp((expected_R_L + 1.0) / 2.0, 0.0, 1.0)
signal_confidence_S = prob_S * (1.0 - uncertainty) * f_clamp((expected_R_S + 1.0) / 2.0, 0.0, 1.0)

//──────────────────────────────────────────────────────────────────────
// VIRTUAL TRADE STATE
//──────────────────────────────────────────────────────────────────────
var float entry_price = na
var float sl_price = na
var float tp_price = na
var float tp1_price = na
var float tp2_price = na
var float tp3_price = na
var int pos_dir = 0
var int entry_bar = na
var string open_setup = ""
var float open_prob = na
var float open_r_win = na
var float open_expR = na
var int last_sig_bar = -10000

var float open_f0 = na
var float open_f1 = na
var float open_f2 = na
var float open_f3 = na
var float open_f4 = na
var float open_f5 = na
var float open_f6 = na
var float open_f7 = na
var float open_f8 = na
var float open_f9 = na
var float open_f10 = na
var float open_f11 = na
var float open_f12 = na

var int wins = 0
var int losses = 0
var float r_sum = 0.0
var int trades = 0

equity_ma = ta.ema(r_sum, equity_guard_ma_len)
equity_guard_bad = use_equity_guard and trades >= equity_guard_min_trades and r_sum < equity_ma

oracle_fail_L = f_clamp(uncertainty * 0.38 + market_entropy * 0.25 + (thin_evidence ? 0.15 : 0.0) + (equity_guard_bad ? 0.10 : 0.0) + (use_crypto_ctx and crypto_ctx_score < -0.35 ? 0.10 : 0.0) + (expected_R_L < 0 ? 0.10 : 0.0), 0.0, 1.0)
oracle_fail_S = f_clamp(uncertainty * 0.38 + market_entropy * 0.25 + (thin_evidence ? 0.15 : 0.0) + (equity_guard_bad ? 0.10 : 0.0) + (use_crypto_ctx and crypto_ctx_score > 0.35 ? 0.10 : 0.0) + (expected_R_S < 0 ? 0.10 : 0.0), 0.0, 1.0)

//──────────────────────────────────────────────────────────────────────
// GATES / EXECUTION TIMING / SIGNAL CLUSTERING
//──────────────────────────────────────────────────────────────────────
prof_thresh_raw = exec_profile == "Aggressive" ? prob_threshold - 0.07 : exec_profile == "Conservative" ? prob_threshold + 0.07 : prob_threshold
prof_unc_raw = exec_profile == "Aggressive" ? unc_max + 0.10 : exec_profile == "Conservative" ? unc_max - 0.10 : unc_max
prof_thresh = f_clamp(prof_thresh_raw + (is_transition ? 0.03 : 0.0) + (is_compression ? 0.02 : 0.0) - (is_trending and is_expansion ? 0.01 : 0.0), 0.40, 0.98)
prof_unc = f_clamp(prof_unc_raw, 0.05, 0.95)

rvol_ok = not use_rvol_gate or not volume_available or rvol >= rvol_cut
atr_ok = (atr_val / close * 100.0) >= min_atr_pct and (atr_val / close * 100.0) <= max_atr_pct
cooldown_ok = (bar_index - last_sig_bar) >= cooldown
flat_ok = pos_dir == 0

entropy_ok_L = not entropy_standby or catalyst_L >= 0.75
entropy_ok_S = not entropy_standby or catalyst_S >= 0.75
oracle_ok_L = not use_oracle_filter or oracle_fail_L <= oracle_fail_max
oracle_ok_S = not use_oracle_filter or oracle_fail_S <= oracle_fail_max

bar_quality_L = body_frac >= 0.08 or is_displacement or sweep_low or lower_wick > body
bar_quality_S = body_frac >= 0.08 or is_displacement or sweep_high or upper_wick > body

expectancy_ok_L = not use_expectancy_gate or (expected_R_L >= min_expected_R and expected_R_L - expected_R_S >= min_expected_edge_R)
expectancy_ok_S = not use_expectancy_gate or (expected_R_S >= min_expected_R and expected_R_S - expected_R_L >= min_expected_edge_R)

base_gate = rvol_ok and atr_ok and warmup_ok and barstate.isconfirmed and flat_ok

ready_long = prob_L >= prof_thresh and uncertainty <= prof_unc and htf_long_ok and crypto_long_ok and contributors_L >= min_contributors and entropy_ok_L and oracle_ok_L and bar_quality_L and expectancy_ok_L and prob_L - prob_S >= prob_edge and signal_confidence_L > signal_confidence_S
ready_short = prob_S >= prof_thresh and uncertainty <= prof_unc and htf_short_ok and crypto_short_ok and contributors_S >= min_contributors and entropy_ok_S and oracle_ok_S and bar_quality_S and expectancy_ok_S and prob_S - prob_L >= prob_edge and signal_confidence_S > signal_confidence_L

var float last_f0 = na
var float last_f1 = na
var float last_f2 = na
var float last_f3 = na
var float last_f4 = na
var float last_f5 = na
var float last_f6 = na
var float last_f7 = na
var float last_f8 = na
var float last_f9 = na
var float last_f10 = na
var float last_f11 = na
var float last_f12 = na
var int last_sig_dir = 0
var int last_sim_bar = -10000

sim_L = f_cos13(ev_struct_L, ev_liq_L, ev_ob_L, ev_fvg_L, ev_zone_L, ev_dna_L, ev_kin_L, ev_delta_L, ev_seq_L, ev_trend_L, ev_mtf_L, ev_smt_L, ev_profile_L, nz(last_f0), nz(last_f1), nz(last_f2), nz(last_f3), nz(last_f4), nz(last_f5), nz(last_f6), nz(last_f7), nz(last_f8), nz(last_f9), nz(last_f10), nz(last_f11), nz(last_f12))
sim_S = f_cos13(ev_struct_S, ev_liq_S, ev_ob_S, ev_fvg_S, ev_zone_S, ev_dna_S, ev_kin_S, ev_delta_S, ev_seq_S, ev_trend_S, ev_mtf_S, ev_smt_S, ev_profile_S, nz(last_f0), nz(last_f1), nz(last_f2), nz(last_f3), nz(last_f4), nz(last_f5), nz(last_f6), nz(last_f7), nz(last_f8), nz(last_f9), nz(last_f10), nz(last_f11), nz(last_f12))

sim_ok_L = not use_similarity_cooldown or last_sig_dir != 1 or (bar_index - last_sim_bar) >= similar_cooldown or sim_L < similarity_threshold
sim_ok_S = not use_similarity_cooldown or last_sig_dir != -1 or (bar_index - last_sim_bar) >= similar_cooldown or sim_S < similarity_threshold

ready_long_core = ready_long and base_gate and cooldown_ok and sim_ok_L
ready_short_core = ready_short and base_gate and cooldown_ok and sim_ok_S

micro_highest_val = ta.highest(high, micro_bos_len)
micro_lowest_val = ta.lowest(low, micro_bos_len)
micro_bos_L = close > micro_highest_val[1] and close > open
micro_bos_S = close < micro_lowest_val[1] and close < open

trigger_L = (close > open and close_loc >= trigger_close_loc and body_frac >= 0.10) or bull_engulf or (mss_up and close > open)
trigger_S = (close < open and close_loc <= 1.0 - trigger_close_loc and body_frac >= 0.10) or bear_engulf or (mss_dn and close < open)

retest_L = in_bull_ob or in_bull_fvg or sweep_low or (vwap_valid and low <= vwap_val and close > vwap_val) or low <= ema20
retest_S = in_bear_ob or in_bear_fvg or sweep_high or (vwap_valid and high >= vwap_val and close < vwap_val) or high >= ema20

var int pend_dir = 0
var int pend_bar = na
var bool pend_pullback = false
var string pend_setup = ""
var float pend_expR = na

bool long_signal = false
bool short_signal = false
bool long_from_pending = false
bool short_from_pending = false

if exec_timing == "Immediate"
    long_signal := ready_long_core and (not ready_short_core or expected_R_L >= expected_R_S)
    short_signal := ready_short_core and (not ready_long_core or expected_R_S > expected_R_L)

if exec_timing == "Trigger Candle"
    long_signal := ready_long_core and trigger_L and (not (ready_short_core and trigger_S) or expected_R_L >= expected_R_S)
    short_signal := ready_short_core and trigger_S and (not (ready_long_core and trigger_L) or expected_R_S > expected_R_L)

if exec_timing == "Retest + Micro BOS"
    if ready_long_core or ready_short_core
        if ready_long_core and (not ready_short_core or expected_R_L >= expected_R_S)
            pend_dir := 1
            pend_bar := bar_index
            pend_pullback := retest_L
            pend_setup := setup_L_name
            pend_expR := expected_R_L
        else if ready_short_core
            pend_dir := -1
            pend_bar := bar_index
            pend_pullback := retest_S
            pend_setup := setup_S_name
            pend_expR := expected_R_S

    if pend_dir == 1
        pend_pullback := pend_pullback or retest_L
        age = bar_index - pend_bar
        valid = age <= pending_max_bars and base_gate and cooldown_ok and sim_ok_L and prob_L >= prof_thresh - 0.03 and expected_R_L >= min_expected_R * 0.50
        if age >= 1 and valid and pend_pullback and (trigger_L or micro_bos_L) and not (ready_short_core and expected_R_S > expected_R_L)
            long_signal := true
            long_from_pending := true
        if age > pending_max_bars or ready_short_core
            if not long_signal
                pend_dir := 0
                pend_setup := ""
                pend_pullback := false

    if pend_dir == -1
        pend_pullback := pend_pullback or retest_S
        age = bar_index - pend_bar
        valid = age <= pending_max_bars and base_gate and cooldown_ok and sim_ok_S and prob_S >= prof_thresh - 0.03 and expected_R_S >= min_expected_R * 0.50
        if age >= 1 and valid and pend_pullback and (trigger_S or micro_bos_S) and not (ready_long_core and expected_R_L > expected_R_S)
            short_signal := true
            short_from_pending := true
        if age > pending_max_bars or ready_short_core
            if not short_signal
                pend_dir := 0
                pend_setup := ""
                pend_pullback := false

if long_signal and short_signal
    if expected_R_L >= expected_R_S
        short_signal := false
    else
        long_signal := false

sig_setup_L_name = long_from_pending and pend_setup != "" ? pend_setup : setup_L_name
sig_setup_S_name = short_from_pending and pend_setup != "" ? pend_setup : setup_S_name

if long_signal or short_signal
    pend_dir := 0
    pend_setup := ""
    pend_pullback := false

entry_style = exec_timing == "Immediate" ? "Immediate" : exec_timing == "Trigger Candle" ? "Trigger Candle" : "Retest + Micro BOS"

//──────────────────────────────────────────────────────────────────────
// ENTRY / RISK / VIRTUAL OUTCOME
//──────────────────────────────────────────────────────────────────────
if long_signal
    entry_price := close
    atr_sl = close - risk_atr * sl_mult
    float struct_sl = na
    if sl_model == "Structure Hybrid"
        struct_sl := in_bull_ob and not na(ob_long_bot) ? ob_long_bot - risk_atr * 0.15 : not na(protected_low) ? protected_low - risk_atr * 0.15 : na
    candidate_sl = atr_sl
    if sl_model == "Structure Hybrid" and not na(struct_sl)
        risk_struct = close - struct_sl
        max_risk = risk_atr * sl_mult * 1.60
        min_risk = risk_atr * 0.35
        if risk_struct > min_risk and risk_struct <= max_risk
            candidate_sl := struct_sl
    sl_price := candidate_sl
    risk_pts = math.max(entry_price - sl_price, syminfo.mintick)
    tp1_price := entry_price + risk_pts * base_rr * 0.50
    tp2_price := entry_price + risk_pts * base_rr
    tp3_candidate = entry_price + risk_pts * base_rr * 1.50
    if use_liquidity_targets and not na(htf1_hi) and htf1_hi > tp2_price and htf1_hi < tp3_candidate
        tp3_price := htf1_hi
    else
        tp3_price := tp3_candidate
    tp_price := tp3_price
    open_r_win := (tp_price - entry_price) / risk_pts
    pos_dir := 1
    entry_bar := bar_index
    open_setup := sig_setup_L_name
    open_prob := prob_L
    open_expR := expected_R_L
    last_sig_bar := bar_index

    open_f0 := ev_struct_L
    open_f1 := ev_liq_L
    open_f2 := ev_ob_L
    open_f3 := ev_fvg_L
    open_f4 := ev_zone_L
    open_f5 := ev_dna_L
    open_f6 := ev_kin_L
    open_f7 := ev_delta_L
    open_f8 := ev_seq_L
    open_f9 := ev_trend_L
    open_f10 := ev_mtf_L
    open_f11 := ev_smt_L
    open_f12 := ev_profile_L

    last_f0 := ev_struct_L
    last_f1 := ev_liq_L
    last_f2 := ev_ob_L
    last_f3 := ev_fvg_L
    last_f4 := ev_zone_L
    last_f5 := ev_dna_L
    last_f6 := ev_kin_L
    last_f7 := ev_delta_L
    last_f8 := ev_seq_L
    last_f9 := ev_trend_L
    last_f10 := ev_mtf_L
    last_f11 := ev_smt_L
    last_f12 := ev_profile_L
    last_sig_dir := 1
    last_sim_bar := bar_index

if short_signal
    entry_price := close
    atr_sl = close + risk_atr * sl_mult
    float struct_sl = na
    if sl_model == "Structure Hybrid"
        struct_sl := in_bear_ob and not na(ob_short_top) ? ob_short_top + risk_atr * 0.15 : not na(protected_high) ? protected_high + risk_atr * 0.15 : na
    candidate_sl = atr_sl
    if sl_model == "Structure Hybrid" and not na(struct_sl)
        risk_struct = struct_sl - close
        max_risk = risk_atr * sl_mult * 1.60
        min_risk = risk_atr * 0.35
        if risk_struct > min_risk and risk_struct <= max_risk
            candidate_sl := struct_sl
    sl_price := candidate_sl
    risk_pts = math.max(sl_price - entry_price, syminfo.mintick)
    tp1_price := entry_price - risk_pts * base_rr * 0.50
    tp2_price := entry_price - risk_pts * base_rr
    tp3_candidate = entry_price - risk_pts * base_rr * 1.50
    if use_liquidity_targets and not na(htf1_lo) and htf1_lo < tp2_price and htf1_lo > tp3_candidate
        tp3_price := htf1_lo
    else
        tp3_price := tp3_candidate
    tp_price := tp3_price
    open_r_win := (entry_price - tp_price) / risk_pts
    pos_dir := -1
    entry_bar := bar_index
    open_setup := sig_setup_S_name
    open_prob := prob_S
    open_expR := expected_R_S
    last_sig_bar := bar_index

    open_f0 := ev_struct_S
    open_f1 := ev_liq_S
    open_f2 := ev_ob_S
    open_f3 := ev_fvg_S
    open_f4 := ev_zone_S
    open_f5 := ev_dna_S
    open_f6 := ev_kin_S
    open_f7 := ev_delta_S
    open_f8 := ev_seq_S
    open_f9 := ev_trend_S
    open_f10 := ev_mtf_S
    open_f11 := ev_smt_S
    open_f12 := ev_profile_S

    last_f0 := ev_struct_S
    last_f1 := ev_liq_S
    last_f2 := ev_ob_S
    last_f3 := ev_fvg_S
    last_f4 := ev_zone_S
    last_f5 := ev_dna_S
    last_f6 := ev_kin_S
    last_f7 := ev_delta_S
    last_f8 := ev_seq_S
    last_f9 := ev_trend_S
    last_f10 := ev_mtf_S
    last_f11 := ev_smt_S
    last_f12 := ev_profile_S
    last_sig_dir := -1
    last_sim_bar := bar_index

bool close_trade = false
bool trade_win = false
float trade_r = na

if pos_dir == 1 and bar_index > entry_bar
    sl_hit = low <= sl_price
    tp_hit = high >= tp_price
    if sl_hit and tp_hit
        close_trade := true
        trade_win := not conservative_resolver
        trade_r := conservative_resolver ? -1.0 : open_r_win
    else if sl_hit
        close_trade := true
        trade_win := false
        trade_r := -1.0
    else if tp_hit
        close_trade := true
        trade_win := true
        trade_r := open_r_win

if pos_dir == -1 and bar_index > entry_bar
    sl_hit = high >= sl_price
    tp_hit = low <= tp_price
    if sl_hit and tp_hit
        close_trade := true
        trade_win := not conservative_resolver
        trade_r := conservative_resolver ? -1.0 : open_r_win
    else if sl_hit
        close_trade := true
        trade_win := false
        trade_r := -1.0
    else if tp_hit
        close_trade := true
        trade_win := true
        trade_r := open_r_win

if close_trade
    wins := wins + (trade_win ? 1 : 0)
    losses := losses + (trade_win ? 0 : 1)
    trades := trades + 1
    r_sum := r_sum + trade_r

    f_record_setup(open_setup, trade_win, trade_r)
    f_update_cal(open_prob, trade_win)

    f_update_feature(0, open_f0, trade_win, trade_r)
    f_update_feature(1, open_f1, trade_win, trade_r)
    f_update_feature(2, open_f2, trade_win, trade_r)
    f_update_feature(3, open_f3, trade_win, trade_r)
    f_update_feature(4, open_f4, trade_win, trade_r)
    f_update_feature(5, open_f5, trade_win, trade_r)
    f_update_feature(6, open_f6, trade_win, trade_r)
    f_update_feature(7, open_f7, trade_win, trade_r)
    f_update_feature(8, open_f8, trade_win, trade_r)
    f_update_feature(9, open_f9, trade_win, trade_r)
    f_update_feature(10, open_f10, trade_win, trade_r)
    f_update_feature(11, open_f11, trade_win, trade_r)
    f_update_feature(12, open_f12, trade_win, trade_r)

    pos_dir := 0
    entry_price := na
    sl_price := na
    tp_price := na
    tp1_price := na
    tp2_price := na
    tp3_price := na
    entry_bar := na
    open_setup := ""
    open_prob := na
    open_r_win := na
    open_expR := na

hit_rate = trades > 0 ? wins / math.max(trades, 1) * 100.0 : 0.0
expectancy = trades > 0 ? r_sum / trades : 0.0

//──────────────────────────────────────────────────────────────────────
// VISUALS
//──────────────────────────────────────────────────────────────────────
plot(zpf_slow, "ZPF Slow", color=zpf_slope > 0 ? bull_col : bear_col, linewidth=1)
plot(zpf_fast, "ZPF Fast", color=color.rgb(255, 180, 40), linewidth=1)
plot(ema20, "EMA 20", color=color.rgb(252, 211, 77), linewidth=1)
plot(ema50, "EMA 50", color=color.rgb(96, 165, 250), linewidth=1)
plot(ema200, "EMA 200", color=color.rgb(216, 180, 254), linewidth=1)
plot(kalman, "Adaptive Kalman", color=info_col, linewidth=1)
plot(use_volume_profile ? vp_poc : na, "Rolling VP POC", color=color.new(color.white, 35), linewidth=1)

if show_struct and (bos_up or bos_dn or choch_up or choch_dn)
    isUp = bos_up or choch_up
    isCh = choch_up or choch_dn
    txtStruct = isCh ? "CHoCH" : "BOS"
    yStruct = isUp ? low - atr_val * 0.15 : high + atr_val * 0.15
    lbStyle = isUp ? label.style_label_up : label.style_label_down
    colStruct = isUp ? bull_col : bear_col
    label.new(bar_index, yStruct, txtStruct, xloc=xloc.bar_index, yloc=yloc.price, style=lbStyle, color=colStruct, textcolor=text_col, size=size.tiny)

plotshape(show_struct and sweep_low, "Low Sweep", shape.xcross, location.belowbar, color.rgb(8, 145, 178), size=size.tiny)
plotshape(show_struct and sweep_high, "High Sweep", shape.xcross, location.abovebar, color.rgb(192, 38, 211), size=size.tiny)
plotshape(
     show_struct and smt_bull_event,
     "Institutional Bull SMT",
     shape.circle,
     location.belowbar,
     color.new(info_col, 0),
     size=size.tiny,
     text="iSMT")

plotshape(
     show_struct and smt_bear_event,
     "Institutional Bear SMT",
     shape.circle,
     location.abovebar,
     color.new(color.orange, 0),
     size=size.tiny,
     text="iSMT")

plotshape(show_sig and long_signal, "Bullish Signal", shape.triangleup, location.belowbar, bull_col, size=size.small)
plotshape(show_sig and short_signal, "Bearish Signal", shape.triangledown, location.abovebar, bear_col, size=size.small)

if show_tag and long_signal
    txt = f_clean_setup(sig_setup_L_name) + "\nP " + str.tostring(prob_L, "#.00") + " · EV " + str.tostring(expected_R_L, "#.00") + "R · U " + str.tostring(uncertainty, "#.00") + "\n" + entry_style + "\nTP " + str.tostring(tp_price, format.mintick) + " · SL " + str.tostring(sl_price, format.mintick)
    label.new(bar_index, low - atr_val * 0.45, txt, xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_up, color=bull_col, textcolor=text_col, size=size.tiny)

if show_tag and short_signal
    txt = f_clean_setup(sig_setup_S_name) + "\nP " + str.tostring(prob_S, "#.00") + " · EV " + str.tostring(expected_R_S, "#.00") + "R · U " + str.tostring(uncertainty, "#.00") + "\n" + entry_style + "\nTP " + str.tostring(tp_price, format.mintick) + " · SL " + str.tostring(sl_price, format.mintick)
    label.new(bar_index, high + atr_val * 0.45, txt, xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_down, color=bear_col, textcolor=text_col, size=size.tiny)

// TP/SL Grid
var line rg_entry = na
var line rg_sl = na
var line rg_tp1 = na
var line rg_tp2 = na
var line rg_tp3 = na
var label rg_entry_lb = na
var label rg_sl_lb = na
var label rg_tp1_lb = na
var label rg_tp2_lb = na
var label rg_tp3_lb = na
var bool rg_live = false

if long_signal or short_signal
    f_delete_line(rg_entry)
    f_delete_line(rg_sl)
    f_delete_line(rg_tp1)
    f_delete_line(rg_tp2)
    f_delete_line(rg_tp3)
    f_delete_label(rg_entry_lb)
    f_delete_label(rg_sl_lb)
    f_delete_label(rg_tp1_lb)
    f_delete_label(rg_tp2_lb)
    f_delete_label(rg_tp3_lb)

    if show_tpsl
        endX = bar_index + 1
        rg_entry := line.new(bar_index, entry_price, endX, entry_price, xloc=xloc.bar_index, color=color.white, width=1)
        rg_sl := line.new(bar_index, sl_price, endX, sl_price, xloc=xloc.bar_index, color=bear_col, width=1, style=line.style_dashed)
        rg_tp1 := line.new(bar_index, tp1_price, endX, tp1_price, xloc=xloc.bar_index, color=color.new(bull_col, 0), width=1)
        rg_tp2 := line.new(bar_index, tp2_price, endX, tp2_price, xloc=xloc.bar_index, color=color.new(bull_col, 10), width=1)
        rg_tp3 := line.new(bar_index, tp3_price, endX, tp3_price, xloc=xloc.bar_index, color=color.new(bull_col, 20), width=1)
        rg_entry_lb := label.new(endX, entry_price, "ENTRY", xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=color.rgb(15,23,42), textcolor=text_col, size=size.tiny)
        rg_sl_lb := label.new(endX, sl_price, "SL", xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=bear_col, textcolor=text_col, size=size.tiny)
        rg_tp1_lb := label.new(endX, tp1_price, "TP1", xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=bull_col, textcolor=text_col, size=size.tiny)
        rg_tp2_lb := label.new(endX, tp2_price, "TP2", xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=bull_col, textcolor=text_col, size=size.tiny)
        rg_tp3_lb := label.new(endX, tp3_price, "TP3", xloc=xloc.bar_index, yloc=yloc.price, style=label.style_label_left, color=bull_col, textcolor=text_col, size=size.tiny)
        rg_live := true

if show_tpsl and rg_live
    endX = close_trade ? bar_index : bar_index + 1
    if not na(rg_entry)
        line.set_x2(rg_entry, endX)
        label.set_x(rg_entry_lb, endX)
    if not na(rg_sl)
        line.set_x2(rg_sl, endX)
        label.set_x(rg_sl_lb, endX)
    if not na(rg_tp1)
        line.set_x2(rg_tp1, endX)
        label.set_x(rg_tp1_lb, endX)
    if not na(rg_tp2)
        line.set_x2(rg_tp2, endX)
        label.set_x(rg_tp2_lb, endX)
    if not na(rg_tp3)
        line.set_x2(rg_tp3, endX)
        label.set_x(rg_tp3_lb, endX)
    if close_trade
        rg_live := false

//──────────────────────────────────────────────────────────────────────
// DASHBOARDS
//──────────────────────────────────────────────────────────────────────
dash_position = f_table_pos(dash_pos_opt)
attr_position = f_table_pos(attr_pos_opt)

var table dash = table.new(dash_position, 2, 23, bgcolor=dash_bg, border_width=1, border_color=color.rgb(30, 41, 59), frame_color=color.rgb(51, 65, 85), frame_width=1)
var table attr = table.new(attr_position, 3, 15, bgcolor=dash_bg, border_width=1, border_color=color.rgb(30, 41, 59), frame_color=color.rgb(51, 65, 85), frame_width=1)
var table risk_dash = table.new(position.bottom_left, 2, 8, bgcolor=dash_bg, border_width=1, border_color=color.rgb(30, 41, 59), frame_color=color.rgb(51, 65, 85), frame_width=1)

if show_dash and barstate.islast
    dash_side_long = prob_L >= prob_S
    dash_setup = dash_side_long ? setup_L_name : setup_S_name
    dash_prob = dash_side_long ? prob_L : prob_S
    dash_exp = dash_side_long ? expected_R_L : expected_R_S

    f_cell(dash, 0, 0, SCRIPT_TITLE, dash_header_bg, text_col)
    f_cell(dash, 1, 0, "STATE", dash_header_bg, text_col)

    f_cell(dash, 0, 1, "Regime Type", dash_bg, color.silver)
    f_cell(dash, 1, 1, regime_str, dash_bg, is_trending ? bull_col : is_ranging ? warn_col : text_col)

    f_cell(dash, 0, 2, "Trend Confidence", dash_bg, color.silver)
    f_cell(dash, 1, 2, str.tostring(trend_conf * 100, "#") + "%", dash_bg, trend_conf >= 0.55 ? bull_col : warn_col)

    f_cell(dash, 0, 3, "Entropy State", dash_bg, color.silver)
    f_cell(dash, 1, 3, str.tostring(market_entropy, "#.00") + (entropy_standby ? " STBY" : ""), dash_bg, entropy_standby ? bear_col : bull_col)

    f_cell(dash, 0, 4, "HTF Matrix Alignment", dash_bg, color.silver)
    f_cell(dash, 1, 4, str.tostring(htf_align) + (htf_in_discount ? " DISC" : htf_in_premium ? " PREM" : ""), dash_bg, htf_align > 0 ? bull_col : htf_align < 0 ? bear_col : text_col)

    f_cell(dash, 0, 5, "Crypto Global Index", dash_bg, color.silver)
    f_cell(dash, 1, 5, str.tostring(crypto_ctx_score, "#.00"), dash_bg, crypto_ctx_score > 0.25 ? bull_col : crypto_ctx_score < -0.25 ? bear_col : warn_col)

    f_cell(dash, 0, 6, "Structure Bias [I/C/E]", dash_bg, color.silver)
    f_cell(dash, 1, 6, "I: " + str.tostring(int_bias) + " | C: " + str.tostring(trend_dir) + " | E: " + str.tostring(ext_bias), dash_bg, ev_mtf_L > ev_mtf_S ? bull_col : ev_mtf_S > ev_mtf_L ? bear_col : text_col)

    f_cell(dash, 0, 7, "Institutional SMT State", dash_bg, color.silver)
    f_cell(dash, 1, 7, str.tostring(ev_smt_L, "#.02") + " " + smt_conf_L_str + " / " + str.tostring(ev_smt_S, "#.02") + " " + smt_conf_S_str, dash_bg, ev_smt_L > ev_smt_S ? bull_col : ev_smt_S > ev_smt_L ? bear_col : text_col)

    f_cell(dash, 0, 8, "Posterior Prob L/S", dash_bg, color.silver)
    f_cell(dash, 1, 8, str.tostring(prob_L, "#.00") + " / " + str.tostring(prob_S, "#.00"), dash_bg, math.max(prob_L, prob_S) >= prof_thresh ? bull_col : warn_col)

    f_cell(dash, 0, 9, "Bayesian Expected R L/S", dash_bg, color.silver)
    f_cell(dash, 1, 9, str.tostring(expected_R_L, "#.00") + " / " + str.tostring(expected_R_S, "#.00"), dash_bg, math.max(expected_R_L, expected_R_S) >= min_expected_R ? bull_col : bear_col)

    f_cell(dash, 0, 10, "Ambiguity / Entropy", dash_bg, color.silver)
    f_cell(dash, 1, 10, str.tostring(uncertainty, "#.02"), dash_bg, uncertainty <= prof_unc ? bull_col : bear_col)

    f_cell(dash, 0, 11, "Oracle Success Gate", dash_bg, color.silver)
    f_cell(dash, 1, 11, str.tostring(oracle_fail_L, "#.02") + " / " + str.tostring(oracle_fail_S, "#.02"), dash_bg, math.min(oracle_fail_L, oracle_fail_S) <= oracle_fail_max ? bull_col : bear_col)

    f_cell(dash, 0, 12, "Evidence Contributors", dash_bg, color.silver)
    f_cell(dash, 1, 12, str.tostring(contributors_L) + " / " + str.tostring(contributors_S), dash_bg, chosen_contrib >= min_contributors ? bull_col : bear_col)

    f_cell(dash, 0, 13, "Order Block Weight", dash_bg, color.silver)
    f_cell(dash, 1, 13, str.tostring(ob_long_conf, "#.02") + " / " + str.tostring(ob_short_conf, "#.02"), dash_bg, text_col)

    f_cell(dash, 0, 14, "Imbalance (FVG) Strength", dash_bg, color.silver)
    f_cell(dash, 1, 14, str.tostring(fvg_long_conf, "#.02") + " / " + str.tostring(fvg_short_conf, "#.02"), dash_bg, text_col)

    f_cell(dash, 0, 15, "VP POC Acceptance", dash_bg, color.silver)
    f_cell(dash, 1, 15, "POC: " + (na(vp_poc) ? "N/A" : str.tostring(vp_poc, format.mintick)) + " | Acc: " + str.tostring(vp_acceptance, "#.02"), dash_bg, info_col)

    f_cell(dash, 0, 16, "RVOL / ATR % Vector", dash_bg, color.silver)
    f_cell(dash, 1, 16, str.tostring(rvol, "#.02") + " / " + str.tostring(atr_val / close * 100.0, "#.02") + "%", dash_bg, rvol_ok and atr_ok ? bull_col : bear_col)

    f_cell(dash, 0, 17, "CVD Momentum Delta", dash_bg, color.silver)
    f_cell(dash, 1, 17, str.tostring(roll_delta, "#") + " / " + str.tostring(cum_delta_bias, "#"), dash_bg, cum_delta_bias > 0 ? bull_col : bear_col)

    f_cell(dash, 0, 18, "Structural Catalyst Setup", dash_bg, color.silver)
    f_cell(dash, 1, 18, f_clean_setup(dash_setup), dash_bg, info_col)

    f_cell(dash, 0, 19, "Posterior Target Edge", dash_bg, color.silver)
    f_cell(dash, 1, 19, str.tostring(dash_prob, "#.00") + " | EV: " + str.tostring(dash_exp, "#.02") + " R", dash_bg, dash_exp >= 0 ? bull_col : bear_col)

    f_cell(dash, 0, 20, "Engine Core Gating", dash_bg, color.silver)
    gate_txt = (warmup_ok ? "WARM" : "CALIBRATING") + " | " + (rvol_ok ? "RVOL" : "LOW-VOL") + " | " + (atr_ok ? "ATR" : "COMPRESSED") + (entropy_standby ? " | ENT-STBY" : "")
    f_cell(dash, 1, 20, gate_txt, dash_bg, base_gate and not entropy_standby ? bull_col : warn_col)

    f_cell(dash, 0, 21, "Pending Setup Trigger", dash_bg, color.silver)
    f_cell(dash, 1, 21, pend_dir == 1 ? "BULLISH" : pend_dir == -1 ? "BEARISH" : "IDLE", dash_bg, pend_dir == 1 ? bull_col : pend_dir == -1 ? bear_col : text_col)

    f_cell(dash, 0, 22, "Virtual Risk State", dash_bg, color.silver)
    f_cell(dash, 1, 22, pos_dir == 1 ? "LONG" : pos_dir == -1 ? "SHORT" : "FLAT", dash_bg, pos_dir == 1 ? bull_col : pos_dir == -1 ? bear_col : text_col)

    //──────────────────────────────────────────────────────────────────────
    // RISK & EXPECTANCY TELEMETRY
    //──────────────────────────────────────────────────────────────────────
    f_cell(risk_dash, 0, 0, "EXPECTANCY & RISK OPTIMIZER ENGINE", dash_header_bg, text_col)
    f_cell(risk_dash, 1, 0, "SYSTEM METRIC STATE", dash_header_bg, text_col)

    f_cell(risk_dash, 0, 1, "Optimal Risk Alloc Per Trade", dash_bg, color.silver)
    f_cell(risk_dash, 1, 1, str.tostring(riskPct, "#.02") + "%", dash_bg, info_col)

    f_cell(risk_dash, 0, 2, "Cumulative Virtual Returns", dash_bg, color.silver)
    f_cell(risk_dash, 1, 2, str.tostring(r_sum, "+#.02;-#.02") + " R", dash_bg, r_sum >= 0 ? bull_col : bear_col)

    f_cell(risk_dash, 0, 3, "Optimized Win Rate", dash_bg, color.silver)
    f_cell(risk_dash, 1, 3, str.tostring(hit_rate, "#.0") + "%", dash_bg, hit_rate >= 50.0 ? bull_col : bear_col)

    f_cell(risk_dash, 0, 4, "Mathematical Expectancy", dash_bg, color.silver)
    f_cell(risk_dash, 1, 4, str.tostring(expectancy, "#.02") + " R / Trade", dash_bg, expectancy >= 0 ? bull_col : bear_col)

    f_cell(risk_dash, 0, 5, "Expected Edge L / S", dash_bg, color.silver)
    f_cell(risk_dash, 1, 5, str.tostring(expected_R_L, "#.02") + " / " + str.tostring(expected_R_S, "#.02"), dash_bg, math.max(expected_R_L, expected_R_S) >= min_expected_R ? bull_col : bear_col)

    f_cell(risk_dash, 0, 6, "Failure-Risk Oracle Vector", dash_bg, color.silver)
    f_cell(risk_dash, 1, 6, str.tostring(oracle_fail_L, "#.02") + " / " + str.tostring(oracle_fail_S, "#.02"), dash_bg, math.min(oracle_fail_L, oracle_fail_S) <= oracle_fail_max ? bull_col : bear_col)

    f_cell(risk_dash, 0, 7, "Virtual Equity Guard State", dash_bg, color.silver)
    f_cell(risk_dash, 1, 7, equity_guard_bad ? "⚠️ RECOVERY DELAY" : "🛡️ ACTIVE", dash_bg, equity_guard_bad ? bear_col : bull_col)

if show_attr and barstate.islast
    bull_side = prob_L >= prob_S

    f_cell(attr, 0, 0, bull_side ? "BULL FEATURES CONFLUENCE" : "BEAR FEATURES CONFLUENCE", dash_header_bg, text_col)
    f_cell(attr, 1, 0, "SCORE", dash_header_bg, text_col)
    f_cell(attr, 2, 0, "WEIGHT", dash_header_bg, text_col)

    scores = array.new_float(0)
    weights = array.new_float(0)

    array.push(scores, bull_side ? ev_struct_L : ev_struct_S)
    array.push(scores, bull_side ? ev_liq_L : ev_liq_S)
    array.push(scores, bull_side ? ev_ob_L : ev_ob_S)
    array.push(scores, bull_side ? ev_fvg_L : ev_fvg_S)
    array.push(scores, bull_side ? ev_zone_L : ev_zone_S)
    array.push(scores, bull_side ? ev_dna_L : ev_dna_S)
    array.push(scores, bull_side ? ev_kin_L : ev_kin_S)
    array.push(scores, bull_side ? ev_delta_L : ev_delta_S)
    array.push(scores, bull_side ? ev_seq_L : ev_seq_S)
    array.push(scores, bull_side ? ev_trend_L : ev_trend_S)
    array.push(scores, bull_side ? ev_mtf_L : ev_mtf_S)
    array.push(scores, bull_side ? ev_smt_L : ev_smt_S)
    array.push(scores, bull_side ? ev_profile_L : ev_profile_S)

    array.push(weights, w0)
    array.push(weights, w1)
    array.push(weights, w2)
    array.push(weights, w3)
    array.push(weights, w4)
    array.push(weights, w5)
    array.push(weights, w6)
    array.push(weights, w7)
    array.push(weights, w8)
    array.push(weights, w9)
    array.push(weights, w10)
    array.push(weights, w11)
    array.push(weights, w12)

    for i = 0 to 12
        f_cell(attr, 0, i + 1, f_feat_name(i), dash_bg, color.silver)
        f_cell(attr, 1, i + 1, str.tostring(array.get(scores, i), "#.00"), dash_bg, text_col)
        f_cell(attr, 2, i + 1, str.tostring(array.get(weights, i), "#.000"), dash_bg, text_col)

    raw_show = bull_side ? raw_L : raw_S
    prob_show = bull_side ? prob_L : prob_S
    f_cell(attr, 0, 14, "RAW → PROB", dash_bg, color.silver)
    f_cell(attr, 1, 14, str.tostring(raw_show, "#.00"), dash_bg, info_col)
    f_cell(attr, 2, 14, str.tostring(prob_show, "#.00"), dash_bg, info_col)

//──────────────────────────────────────────────────────────────────────
// ALERTS
//──────────────────────────────────────────────────────────────────────
alertcondition(long_signal, "AICE PRO Bullish Signal", "AICE PRO bullish signal")
alertcondition(short_signal, "AICE PRO Bearish Signal", "AICE PRO bearish signal")

if long_signal
    alert(
         SCRIPT_TITLE + " BULLISH\n" +
         "Setup: " + f_clean_setup(sig_setup_L_name) + "\n" +
         "Style: " + entry_style + "\n" +
         "Prob: " + str.tostring(prob_L, "#.00") + "\n" +
         "Expected R: " + str.tostring(expected_R_L, "#.00") + "\n" +
         "Oracle Risk: " + str.tostring(oracle_fail_L, "#.00") + "\n" +
         "Entry: " + str.tostring(entry_price, format.mintick) + "\n" +
         "SL: " + str.tostring(sl_price, format.mintick) + "\n" +
         "TP1: " + str.tostring(tp1_price, format.mintick) + "\n" +
         "TP2: " + str.tostring(tp2_price, format.mintick) + "\n" +
         "TP3: " + str.tostring(tp3_price, format.mintick),
         alert.freq_once_per_bar_close)

if short_signal
    alert(
         SCRIPT_TITLE + " BEARISH\n" +
         "Setup: " + f_clean_setup(sig_setup_S_name) + "\n")
