"""
코리아골드익스체인지 금 시세 시각화 대시보드
----------------------------------------------
필요 패키지:
    pip install matplotlib seaborn pandas scipy numpy

실행:
    python gold_price_visualize.py
"""

import glob
import os
import warnings
import matplotlib
matplotlib.use("Agg")   # GUI 없이 파일로 바로 저장
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")
matplotlib.rcParams["axes.unicode_minus"] = False

# ── 한글 폰트 설정 ────────────────────────────────────────────────────────────
def _set_korean_font():
    prefer = [
        "Malgun Gothic", "맑은 고딕",
        "NanumGothic", "NanumBarunGothic",
        "AppleGothic", "Gulim",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in prefer:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            return name
    # 폴백: 첫 번째 TTF 로 설정
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    return "DejaVu Sans"

FONT_NAME = _set_korean_font()


# ── 데이터 로드 ───────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    """저장된 최신 CSV를 읽거나, 없으면 API 에서 새로 가져옵니다."""
    files = sorted(glob.glob("gold_price_1year_*.csv"))
    if files:
        path = files[-1]
        print(f"CSV 로드: {path}")
        df = pd.read_csv(path, encoding="utf-8-sig")
    else:
        print("CSV 없음 — API 에서 데이터를 가져옵니다...")
        from gold_price_crawler import fetch_gold_price_1year
        df = fetch_gold_price_1year()

    # 열 이름 영어 매핑 (한글 인코딩 문제 우회)
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if "고시" in c or "일시" in c or "date" in lc:
            col_map[c] = "date"
        elif "순금" in c and "살" in c:
            col_map[c] = "buy_pure"
        elif "순금" in c and "팔" in c:
            col_map[c] = "sell_pure"
        elif "18k" in c.lower() and "팔" in c:
            col_map[c] = "sell_18k"
        elif "14k" in c.lower() and "팔" in c:
            col_map[c] = "sell_14k"
        elif "은" in c and "살" in c:
            col_map[c] = "buy_silver"
        elif "은" in c and "팔" in c:
            col_map[c] = "sell_silver"
        # 컬럼명이 영어인 경우
        elif c == "s_pure":
            col_map[c] = "buy_pure"
        elif c == "p_pure":
            col_map[c] = "sell_pure"
        elif c == "s_18k":
            col_map[c] = "buy_18k"
        elif c in ("p_18k", "18k_팔때(원/3.75g)") or ("18k" in c.lower() and "팔" in c):
            col_map[c] = "sell_18k"
        elif c == "s_14k":
            col_map[c] = "buy_14k"
        elif c in ("p_14k", "14k_팔때(원/3.75g)") or ("14k" in c.lower() and "팔" in c):
            col_map[c] = "sell_14k"
        elif c == "s_silver":
            col_map[c] = "buy_silver"
        elif c == "p_silver":
            col_map[c] = "sell_silver"
        elif c == "s_white":
            col_map[c] = "buy_white"
        elif c == "p_white":
            col_map[c] = "sell_white"

    df.rename(columns=col_map, inplace=True)

    # 첫 번째 컬럼이 date 로 매핑 안 됐을 경우 보정
    if "date" not in df.columns:
        df.rename(columns={df.columns[0]: "date"}, inplace=True)

    # 날짜 파싱
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 숫자 컬럼 확인
    num_cols = [c for c in df.columns if c != "date"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 순금 살때 컬럼 없으면 대체 생성
    if "buy_pure" not in df.columns:
        # API 원본 컬럼 탐색 (순금 살때)
        for c in df.columns:
            raw = c.lower()
            if "pure" in raw or "순금" in raw:
                df["buy_pure"] = df[c]
                break

    # 일별 마지막 고시가 기준으로 집계
    df["day"] = df["date"].dt.date
    print(f"  총 {len(df):,}건 로드 완료 ({df['date'].min().date()} ~ {df['date'].max().date()})")
    return df


def daily_close(df: pd.DataFrame, col: str) -> pd.Series:
    """일별 마지막 고시가 (종가 대용)"""
    return df.groupby("day")[col].last()


def daily_ohlc(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """일별 OHLC"""
    g = df.groupby("day")[col]
    return pd.DataFrame({
        "open":  g.first(),
        "high":  g.max(),
        "low":   g.min(),
        "close": g.last(),
    })


# ── 색상 팔레트 ───────────────────────────────────────────────────────────────
GOLD      = "#FFD700"
GOLD_DARK = "#B8860B"
GOLD2     = "#FFA500"
SILVER    = "#C0C0C0"
BG        = "#0F0F1A"
BG2       = "#1A1A2E"
PANEL     = "#16213E"
TEXT      = "#E8E8F0"
SUBTEXT   = "#9090A8"
GREEN     = "#00D4AA"
RED       = "#FF4C6A"
BLUE      = "#4C9CFF"
PURPLE    = "#A855F7"


def apply_dark_style(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=SUBTEXT, labelsize=9)
    ax.xaxis.label.set_color(SUBTEXT)
    ax.yaxis.label.set_color(SUBTEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2A2A3E")
    if title:
        ax.set_title(title, color=TEXT, fontsize=11, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=SUBTEXT, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=9)
    ax.grid(True, color="#2A2A3E", linewidth=0.5, linestyle="--", alpha=0.7)


def fmt_won(x, _):
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{x/1_000:.0f}K"
    return str(int(x))


# ════════════════════════════════════════════════════════════════════════════
#  차트 1: 메인 라인 차트 + 이동평균
# ════════════════════════════════════════════════════════════════════════════
def plot_main_line(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    close = daily_close(df, col)
    idx = pd.to_datetime(close.index)

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    ax.fill_between(idx, close.values, alpha=0.12, color=GOLD)
    ax.plot(idx, close.values, color=GOLD, linewidth=1.5, label="순금 살 때")
    ax.plot(idx, ma20.values, color=GOLD2, linewidth=1.2, linestyle="--",
            label="20일 이동평균", alpha=0.9)
    ax.plot(idx, ma60.values, color=RED, linewidth=1.2, linestyle="-.",
            label="60일 이동평균", alpha=0.9)

    # 최고/최저 표시
    hi_i = close.idxmax()
    lo_i = close.idxmin()
    ax.annotate(f"최고 {close.max():,.0f}",
                xy=(pd.to_datetime(hi_i), close.max()),
                xytext=(10, 12), textcoords="offset points",
                color=GREEN, fontsize=8,
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=0.8))
    ax.annotate(f"최저 {close.min():,.0f}",
                xy=(pd.to_datetime(lo_i), close.min()),
                xytext=(10, -18), textcoords="offset points",
                color=RED, fontsize=8,
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.8))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_won))
    ax.legend(loc="upper left", fontsize=8, facecolor=BG2, labelcolor=TEXT,
              edgecolor="#2A2A3E")
    apply_dark_style(ax, "순금 시세 추이 (살 때, 원/3.75g)", ylabel="원/3.75g")


# ════════════════════════════════════════════════════════════════════════════
#  차트 2: 캔들스틱 (마지막 3개월)
# ════════════════════════════════════════════════════════════════════════════
def plot_candlestick(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    cutoff = df["date"].max() - pd.Timedelta(days=90)
    sub = df[df["date"] >= cutoff]
    ohlc = daily_ohlc(sub, col)
    if ohlc.empty:
        return

    dates = pd.to_datetime(ohlc.index)
    x = np.arange(len(dates))

    up_mask   = ohlc["close"] >= ohlc["open"]
    down_mask = ~up_mask

    # 몸통
    for i, (_, row) in enumerate(ohlc.iterrows()):
        color = GREEN if row["close"] >= row["open"] else RED
        body_lo = min(row["open"], row["close"])
        body_hi = max(row["open"], row["close"])
        ax.bar(x[i], body_hi - body_lo, bottom=body_lo,
               color=color, width=0.6, alpha=0.85)
        ax.vlines(x[i], row["low"], row["high"], color=color, linewidth=0.8)

    # X축 레이블
    step = max(1, len(dates) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(
        [d.strftime("%m/%d") for d in dates[::step]],
        rotation=30, ha="right", fontsize=8
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_won))
    apply_dark_style(ax, "캔들스틱 (최근 3개월, 일별 OHLC)", ylabel="원/3.75g")


# ════════════════════════════════════════════════════════════════════════════
#  차트 3: 월별 평균 바 차트
# ════════════════════════════════════════════════════════════════════════════
def plot_monthly_bar(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    df2 = df.copy()
    df2["ym"] = df2["date"].dt.to_period("M")
    monthly = df2.groupby("ym")[col].mean()
    labels  = [str(p) for p in monthly.index]
    vals    = monthly.values

    colors = [GOLD if v >= np.median(vals) else GOLD_DARK for v in vals]
    bars = ax.bar(range(len(labels)), vals, color=colors, width=0.65, alpha=0.9,
                  edgecolor="#2A2A3E", linewidth=0.5)

    # 값 레이블
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2000,
                f"{v/1000:.0f}K", ha="center", va="bottom",
                color=TEXT, fontsize=7, fontweight="bold")

    # 평균선
    ax.axhline(np.mean(vals), color=BLUE, linewidth=1.2, linestyle="--", alpha=0.8,
               label=f"연간 평균  {np.mean(vals):,.0f}")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_won))
    ax.legend(fontsize=8, facecolor=BG2, labelcolor=TEXT, edgecolor="#2A2A3E")
    apply_dark_style(ax, "월별 평균 금 시세", ylabel="원/3.75g")


# ════════════════════════════════════════════════════════════════════════════
#  차트 4: 가격 분포 히스토그램 + KDE
# ════════════════════════════════════════════════════════════════════════════
def plot_distribution(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    data = df[col].dropna()
    ax2  = ax.twinx()

    # 히스토그램
    n, bins, patches = ax.hist(data, bins=40, color=GOLD, alpha=0.55,
                               edgecolor="#2A2A3E", linewidth=0.4)
    # KDE
    kde_x = np.linspace(data.min(), data.max(), 300)
    kde   = stats.gaussian_kde(data)
    ax2.plot(kde_x, kde(kde_x), color=RED, linewidth=2, label="KDE 밀도")
    ax2.set_ylabel("밀도", color=SUBTEXT, fontsize=9)
    ax2.tick_params(colors=SUBTEXT, labelsize=8)

    # 통계선
    for val, label, color in [
        (data.mean(),   "평균", BLUE),
        (data.median(), "중앙값", GREEN),
    ]:
        ax.axvline(val, color=color, linewidth=1.5, linestyle="--", alpha=0.9)
        ax.text(val, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] > 0 else 1,
                f"{label}\n{val:,.0f}", ha="center", fontsize=7,
                color=color, fontweight="bold")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_won))
    apply_dark_style(ax, "순금 시세 분포", xlabel="원/3.75g", ylabel="빈도")


# ════════════════════════════════════════════════════════════════════════════
#  차트 5: 금 종류별 가격 비교 라인
# ════════════════════════════════════════════════════════════════════════════
def plot_multi_gold(df: pd.DataFrame, ax: plt.Axes):
    mapping = {
        "buy_pure":  ("순금 살때",  GOLD,   2.0),
        "sell_pure": ("순금 팔때",  GOLD2,  1.4),
        "sell_18k":  ("18K 팔때",  PURPLE, 1.4),
        "sell_14k":  ("14K 팔때",  BLUE,   1.4),
    }
    found = False
    for col, (label, color, lw) in mapping.items():
        if col not in df.columns:
            continue
        close = daily_close(df, col)
        idx   = pd.to_datetime(close.index)
        ax.plot(idx, close.values, color=color, linewidth=lw, label=label, alpha=0.9)
        found = True

    if not found:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_won))
    ax.legend(loc="upper left", fontsize=8, facecolor=BG2, labelcolor=TEXT,
              edgecolor="#2A2A3E")
    apply_dark_style(ax, "금 종류별 시세 비교", ylabel="원/3.75g")


# ════════════════════════════════════════════════════════════════════════════
#  차트 6: 전일 대비 변화율 (%)
# ════════════════════════════════════════════════════════════════════════════
def plot_daily_change(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    close  = daily_close(df, col)
    pct    = close.pct_change() * 100
    idx    = pd.to_datetime(pct.index)
    vals   = pct.values

    colors = [GREEN if v >= 0 else RED for v in vals]
    ax.bar(idx, vals, color=colors, width=0.8, alpha=0.8)
    ax.axhline(0, color=SUBTEXT, linewidth=0.8)

    # ±2% 경계선
    ax.axhline(2,  color=GREEN, linewidth=0.7, linestyle="--", alpha=0.5)
    ax.axhline(-2, color=RED,   linewidth=0.7, linestyle="--", alpha=0.5)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    apply_dark_style(ax, "일별 등락률 (%)", ylabel="%")


# ════════════════════════════════════════════════════════════════════════════
#  차트 7: 20일 변동성 (표준편차 롤링)
# ════════════════════════════════════════════════════════════════════════════
def plot_volatility(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    close = daily_close(df, col)
    pct   = close.pct_change() * 100
    vol20 = pct.rolling(20).std()
    idx   = pd.to_datetime(vol20.index)

    ax.fill_between(idx, vol20.values, alpha=0.35, color=PURPLE)
    ax.plot(idx, vol20.values, color=PURPLE, linewidth=1.5)
    ax.axhline(vol20.mean(), color=BLUE, linewidth=1, linestyle="--", alpha=0.8,
               label=f"평균 변동성 {vol20.mean():.2f}%")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.legend(fontsize=8, facecolor=BG2, labelcolor=TEXT, edgecolor="#2A2A3E")
    apply_dark_style(ax, "20일 롤링 변동성", ylabel="%")


# ════════════════════════════════════════════════════════════════════════════
#  차트 8: 상관관계 히트맵
# ════════════════════════════════════════════════════════════════════════════
def plot_heatmap(df: pd.DataFrame, ax: plt.Axes):
    cols = [c for c in ["buy_pure", "sell_pure", "sell_18k", "sell_14k",
                         "buy_silver", "sell_silver", "buy_white", "sell_white",
                         "buy_18k", "buy_14k"]
            if c in df.columns]
    if len(cols) < 2:
        ax.text(0.5, 0.5, "컬럼 부족", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    label_map = {
        "buy_pure":   "순금살때", "sell_pure":  "순금팔때",
        "sell_18k":   "18K팔때",  "sell_14k":   "14K팔때",
        "buy_silver": "은살때",   "sell_silver":"은팔때",
        "buy_white":  "백금살때", "sell_white": "백금팔때",
        "buy_18k":    "18K살때",  "buy_14k":    "14K살때",
    }

    sub = df[cols].dropna()
    corr = sub.corr()
    corr.index   = [label_map.get(c, c) for c in corr.index]
    corr.columns = [label_map.get(c, c) for c in corr.columns]

    cmap = sns.diverging_palette(10, 145, as_cmap=True)
    sns.heatmap(corr, ax=ax, cmap=cmap, vmin=-1, vmax=1,
                annot=True, fmt=".2f", annot_kws={"size": 8},
                linewidths=0.5, linecolor="#0F0F1A",
                cbar_kws={"shrink": 0.8})
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=SUBTEXT, labelsize=8)
    ax.set_title("가격 지표 상관관계", color=TEXT, fontsize=11,
                 fontweight="bold", pad=10)


# ════════════════════════════════════════════════════════════════════════════
#  차트 9: 누적 수익률
# ════════════════════════════════════════════════════════════════════════════
def plot_cumulative_return(df: pd.DataFrame, ax: plt.Axes):
    col = "buy_pure"
    if col not in df.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color=TEXT)
        return

    close  = daily_close(df, col)
    cumret = (close / close.iloc[0] - 1) * 100
    idx    = pd.to_datetime(cumret.index)

    pos_mask = cumret.values >= 0
    ax.fill_between(idx, cumret.values, where=pos_mask,  alpha=0.25, color=GREEN)
    ax.fill_between(idx, cumret.values, where=~pos_mask, alpha=0.25, color=RED)
    ax.plot(idx, cumret.values, color=GOLD, linewidth=1.8)
    ax.axhline(0, color=SUBTEXT, linewidth=0.8)

    final = cumret.iloc[-1]
    color = GREEN if final >= 0 else RED
    ax.text(0.98, 0.05, f"기간 수익률\n{final:+.1f}%",
            transform=ax.transAxes, ha="right", va="bottom",
            color=color, fontsize=10, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=BG2, alpha=0.8,
                      edgecolor=color))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    apply_dark_style(ax, "누적 수익률 (기간 대비 %)", ylabel="%")


# ════════════════════════════════════════════════════════════════════════════
#  메인 대시보드 조립
# ════════════════════════════════════════════════════════════════════════════
def build_dashboard(df: pd.DataFrame):
    fig = plt.figure(figsize=(22, 26), facecolor=BG)
    fig.patch.set_facecolor(BG)

    # 타이틀
    fig.text(0.5, 0.985, "🏅 코리아골드익스체인지 금 시세 대시보드",
             ha="center", va="top", color=GOLD, fontsize=18, fontweight="bold",
             fontfamily=FONT_NAME)

    period = f"{df['date'].min().strftime('%Y.%m.%d')}  →  {df['date'].max().strftime('%Y.%m.%d')}"
    fig.text(0.5, 0.975, f"기간: {period}  |  총 {len(df):,}건",
             ha="center", va="top", color=SUBTEXT, fontsize=10,
             fontfamily=FONT_NAME)

    # ── KPI 카드 행 ────────────────────────────────────────────────────────
    col = "buy_pure"
    if col in df.columns:
        close  = daily_close(df, col)
        latest = close.iloc[-1]
        prev   = close.iloc[-2] if len(close) > 1 else latest
        diff   = latest - prev
        pct    = diff / prev * 100
        hi52   = close.max()
        lo52   = close.min()
        avg52  = close.mean()

        kpis = [
            ("현재가",       f"{latest:,.0f} 원",   f"{diff:+,.0f} ({pct:+.2f}%)",
             GREEN if diff >= 0 else RED),
            ("52주 최고",    f"{hi52:,.0f} 원",      "", GOLD),
            ("52주 최저",    f"{lo52:,.0f} 원",      "", BLUE),
            ("연간 평균",    f"{avg52:,.0f} 원",      "", PURPLE),
        ]

        for i, (label, value, sub, color) in enumerate(kpis):
            ax_kpi = fig.add_axes([0.03 + i * 0.245, 0.935, 0.22, 0.038])
            ax_kpi.set_facecolor(PANEL)
            ax_kpi.set_xlim(0, 1); ax_kpi.set_ylim(0, 1)
            ax_kpi.axis("off")
            for spine in ax_kpi.spines.values():
                spine.set_edgecolor(color)
                spine.set_linewidth(1.5)
                spine.set_visible(True)
            ax_kpi.text(0.5, 0.85, label,  ha="center", va="top",
                        color=SUBTEXT, fontsize=9,  fontfamily=FONT_NAME)
            ax_kpi.text(0.5, 0.42, value,  ha="center", va="center",
                        color=color,   fontsize=13, fontweight="bold",
                        fontfamily=FONT_NAME)
            if sub:
                ax_kpi.text(0.5, 0.05, sub, ha="center", va="bottom",
                            color=GREEN if "+" in sub else RED,
                            fontsize=8, fontfamily=FONT_NAME)

    # ── 그리드 레이아웃 ────────────────────────────────────────────────────
    gs = fig.add_gridspec(5, 2, left=0.06, right=0.97,
                           top=0.925, bottom=0.04,
                           hspace=0.42, wspace=0.28)

    axes = [
        fig.add_subplot(gs[0, :]),   # 0: 메인 라인 (전체 너비)
        fig.add_subplot(gs[1, 0]),   # 1: 캔들스틱
        fig.add_subplot(gs[1, 1]),   # 2: 월별 평균
        fig.add_subplot(gs[2, 0]),   # 3: 분포
        fig.add_subplot(gs[2, 1]),   # 4: 금 종류 비교
        fig.add_subplot(gs[3, 0]),   # 5: 일별 등락률
        fig.add_subplot(gs[3, 1]),   # 6: 변동성
        fig.add_subplot(gs[4, 0]),   # 7: 상관관계 히트맵
        fig.add_subplot(gs[4, 1]),   # 8: 누적 수익률
    ]

    plot_main_line(df,        axes[0])
    plot_candlestick(df,      axes[1])
    plot_monthly_bar(df,      axes[2])
    plot_distribution(df,     axes[3])
    plot_multi_gold(df,       axes[4])
    plot_daily_change(df,     axes[5])
    plot_volatility(df,       axes[6])
    plot_heatmap(df,          axes[7])
    plot_cumulative_return(df, axes[8])

    # 푸터
    fig.text(0.5, 0.01, "Data Source: koreagoldx.co.kr  |  단위: 원/3.75g(돈)",
             ha="center", va="bottom", color=SUBTEXT, fontsize=8)

    plt.savefig("gold_dashboard.png", dpi=150, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    print("대시보드 저장 완료: gold_dashboard.png")


# ── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  코리아골드익스체인지 금 시세 시각화 대시보드")
    print("=" * 55)

    df = load_data()
    build_dashboard(df)
