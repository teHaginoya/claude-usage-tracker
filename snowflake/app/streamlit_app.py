# =============================================================================
# 03_streamlit_app.py - メインエントリポイント
# =============================================================================
# Streamlit in Snowflake へデプロイ時は、同じステージに以下を配置してください:
#   helpers.py / queries.py / demo_data.py
#   tab_overview.py / tab_users.py / tab_tools.py
#   tab_sessions.py / tab_projects.py / tab_adoption.py
# =============================================================================

import streamlit as st

# ── ページ設定（最初に呼ぶ必要あり） ─────────────────────────────
st.set_page_config(
    page_title="Claude Code Usage Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    /* ===== カラーパレット（プレミアムライト） ===== */
    :root {
        /* サーフェス */
        --bg-base:       #f0f4f8;
        --bg-surface:    #e8edf5;
        --bg-elevated:   #edf1f7;
        --bg-card:       #ffffff;
        --bg-card-hover: #fafbff;
        --bg-highlight:  #f5f8ff;

        /* ボーダー */
        --border:        #dde3ed;
        --border-light:  #edf1f7;
        --border-accent: rgba(245,158,11,0.4);

        /* テキスト */
        --text-primary:  #0f172a;
        --text-secondary:#475569;
        --text-muted:    #94a3b8;

        /* アクセントカラー */
        --accent-amber:  #f59e0b;
        --accent-teal:   #0d9488;
        --accent-blue:   #3b82f6;
        --accent-rose:   #e11d48;
        --accent-violet: #7c3aed;
        --accent-green:  #16a34a;
        --positive:      #16a34a;
        --negative:      #e11d48;

        /* フォント */
        --mono-font: 'DM Mono', 'Courier New', monospace;
        --body-font: 'Inter', 'Noto Sans JP', 'Hiragino Sans', sans-serif;

        /* シェイプ */
        --radius-sm: 6px;
        --radius:    10px;
        --radius-lg: 12px;

        /* シャドウ */
        --shadow-sm: 0 1px 2px rgba(15,23,42,0.04), 0 1px 4px rgba(15,23,42,0.06);
        --shadow:    0 2px 8px rgba(15,23,42,0.07), 0 1px 3px rgba(15,23,42,0.05);
        --shadow-md: 0 4px 16px rgba(15,23,42,0.10), 0 2px 6px rgba(15,23,42,0.06);
    }

    /* ===== グローバル ===== */
    html, body, [class*="css"] {
        font-family: var(--body-font);
        background-color: var(--bg-base);
        color: var(--text-primary);
    }

    .stApp {
        background-color: var(--bg-base) !important;
    }

    .main .block-container {
        padding: 1.25rem 2rem 2.5rem;
        max-width: 1680px;
        background-color: var(--bg-base);
    }

    /* ===== 非表示 ===== */
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; }

    /* ===== ヘッダーエリア ===== */
    /* Streamlit カラムの中でロゴを縦中央揃え */
    [data-testid="column"]:first-child > div:first-child {
        display: flex;
        align-items: center;
        min-height: 52px;
    }

    /* 期間ボタンも縦中央揃え */
    [data-testid="column"]:last-child > div:first-child {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-end !important;
        min-height: 52px;
    }

    /* ラジオグループのラベル非表示残骸対策 */
    [data-testid="column"]:last-child .stRadio > div:first-child:not(:has(label)) {
        display: none !important;
    }

    /* フィルタのSiSカードコンテナを透明化（白いボックスを除去） */
    .element-container:has(.stRadio),
    .stRadio {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    .dash-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .dash-logo-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        box-shadow: 0 2px 8px rgba(245,158,11,0.3), 0 1px 2px rgba(245,158,11,0.2);
        flex-shrink: 0;
    }

    .dash-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        line-height: 1.2;
        margin: 0;
    }

    .dash-subtitle {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin: 0.1rem 0 0;
        font-weight: 400;
    }

    /* ===== セクションヘッダー ===== */
    .section-header {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #64748b;
        margin: 1.75rem 0 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.55rem;
    }

    .section-header::before {
        content: '';
        width: 3px;
        height: 13px;
        background: linear-gradient(180deg, var(--accent-amber) 0%, #d97706 100%);
        border-radius: 2px;
        flex-shrink: 0;
    }

    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    .section-sub {
        font-size: 0.62rem;
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: var(--text-muted);
        opacity: 0.75;
    }

    /* ===== KPIカード ===== */
    @keyframes kpiIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.15rem 1.3rem 1rem;
        position: relative;
        overflow: hidden;
        transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;
        height: 100%;
        flex: 1;
        min-height: 12rem;
        animation: kpiIn 0.35s ease both;
        box-shadow: var(--shadow-sm);
    }

    /* アクセントカラー ラインを上部に */
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--accent-color, var(--accent-teal));
    }

    /* 背景に極薄グロー */
    .kpi-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 50%;
        background: radial-gradient(ellipse at 15% 0%, var(--glow-color, transparent) 0%, transparent 75%);
        pointer-events: none;
    }

    .kpi-card:hover {
        box-shadow: var(--shadow-md);
        border-color: var(--border-light);
        transform: translateY(-2px);
    }

    .kpi-label {
        font-size: 0.67rem;
        font-weight: 600;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 0.55rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .kpi-label .badge {
        font-size: 0.56rem;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-weight: 700;
        background: var(--bg-elevated);
        color: var(--text-muted);
        letter-spacing: 0.06em;
        border: 1px solid var(--border);
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        font-family: var(--mono-font);
        color: var(--text-primary);
        line-height: 1.1;
        letter-spacing: -0.04em;
        margin-bottom: 0.4rem;
    }

    .kpi-change {
        font-size: 0.7rem;
        font-family: var(--mono-font);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.3rem;
        flex-wrap: wrap;
    }

    .kpi-change .period {
        color: var(--text-muted);
        font-weight: 400;
        font-size: 0.65rem;
    }

    .kpi-change.pos { color: var(--positive); }
    .kpi-change.neg { color: var(--negative); }
    .kpi-change.neu { color: var(--text-muted); }

    .kpi-sparkbar {
        display: flex;
        gap: 2px;
        margin-top: 0.65rem;
        align-items: flex-end;
        height: 22px;
    }

    .kpi-sparkbar span {
        flex: 1;
        background: var(--accent-color, var(--accent-teal));
        opacity: 0.5;
        border-radius: 2px 2px 0 0;
        min-height: 3px;
        transition: opacity 0.2s;
    }

    .kpi-card:hover .kpi-sparkbar span { opacity: 0.75; }

    /* ===== プログレスバー ===== */
    .progress-track {
        background: var(--border);
        border-radius: 99px;
        height: 5px;
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .progress-fill {
        height: 100%;
        border-radius: 99px;
        background: linear-gradient(90deg, var(--accent-teal), var(--accent-blue));
        transition: width 0.8s cubic-bezier(0.4,0,0.2,1);
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.65rem;
        font-family: var(--mono-font);
        color: var(--text-muted);
        margin-top: 0.3rem;
    }

    /* ===== 利用制限バッジ ===== */
    .limit-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        margin-top: 0.45rem;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        padding: 0.2rem 0.55rem;
        border-radius: 5px;
        background: rgba(225,29,72,0.08);
        color: var(--negative);
        border: 1px solid rgba(225,29,72,0.2);
    }

    /* ===== インサイトカード ===== */
    .insight-row {
        display: flex;
        gap: 0.75rem;
        flex-wrap: nowrap;
    }

    .insight-card {
        flex: 1;
        min-width: 0;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.1rem;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.2s, transform 0.2s;
    }

    .insight-card:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow);
    }

    .insight-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
    }

    .insight-card.trend-up::before   { background: var(--accent-amber); }
    .insight-card.trend-down::before { background: var(--negative); }
    .insight-card.power-user::before { background: var(--accent-green); }
    .insight-card.usecase::before    { background: var(--accent-blue); }
    .insight-card.neutral::before    { background: var(--accent-violet); }

    .insight-tag {
        font-size: 0.58rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }
    .trend-up   .insight-tag { color: var(--accent-amber); }
    .trend-down .insight-tag { color: var(--negative); }
    .power-user .insight-tag { color: var(--accent-green); }
    .usecase    .insight-tag { color: var(--accent-blue); }
    .neutral    .insight-tag { color: var(--accent-violet); }

    .insight-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }

    .insight-desc {
        font-size: 0.7rem;
        color: var(--text-secondary);
        line-height: 1.55;
    }

    /* ===== テーブル ===== */
    .rank-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }

    .rank-table th {
        font-size: 0.62rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        padding: 0.65rem 0.85rem;
        border-bottom: 1px solid var(--border);
        background: var(--bg-elevated);
        white-space: nowrap;
    }

    .rank-table th:first-child { border-radius: var(--radius) 0 0 0; }
    .rank-table th:last-child  { border-radius: 0 var(--radius) 0 0; }

    .rank-table td {
        padding: 0.7rem 0.85rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.81rem;
        color: var(--text-secondary);
        background: var(--bg-card);
        transition: background 0.12s;
    }

    .rank-table tr:hover td { background: var(--bg-highlight); }
    .rank-table tr:last-child td { border-bottom: none; }

    .rank-icon { font-size: 1rem; line-height: 1; }

    .user-name {
        font-weight: 600;
        color: var(--text-primary);
        font-size: 0.83rem;
    }

    .user-time {
        font-size: 0.62rem;
        color: var(--text-muted);
        font-family: var(--mono-font);
        margin-top: 0.15rem;
    }

    .num-cell {
        font-family: var(--mono-font);
        font-size: 0.8rem;
        text-align: right;
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }

    .num-cell.highlight {
        color: var(--accent-amber);
        font-weight: 600;
    }

    .tag-pill {
        display: inline-block;
        font-size: 0.56rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        padding: 0.13rem 0.42rem;
        border-radius: 4px;
        text-transform: uppercase;
    }

    .tag-skill    { background: rgba(13,148,136,0.1);  color: var(--accent-teal);   border: 1px solid rgba(13,148,136,0.2); }
    .tag-mcp      { background: rgba(124,58,237,0.1);  color: var(--accent-violet); border: 1px solid rgba(124,58,237,0.2); }
    .tag-subagent { background: rgba(22,163,74,0.1);   color: var(--accent-green);  border: 1px solid rgba(22,163,74,0.2); }
    .tag-command  { background: rgba(59,130,246,0.1);  color: var(--accent-blue);   border: 1px solid rgba(59,130,246,0.2); }

    /* ===== ユーザー詳細パネル ===== */
    .detail-panel {
        background: var(--bg-highlight);
        border: 1px solid var(--border);
        border-left: 3px solid var(--accent-amber);
        border-radius: var(--radius);
        padding: 1.1rem 1.4rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
    }

    /* ===== チャートコンテナ ===== */
    .chart-wrap {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem 1.25rem 0.75rem;
        box-shadow: var(--shadow-sm);
    }

    .chart-title {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 0.85rem;
    }

    /* ===== タブ ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.15rem;
        background: transparent;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0;
        margin-bottom: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0;
        padding: 0.55rem 1.1rem;
        font-size: 0.8rem;
        color: var(--text-muted);
        border: none;
        font-family: var(--body-font);
        font-weight: 500;
        transition: color 0.15s;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-secondary);
        background: var(--bg-elevated);
    }

    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-bottom: 1px solid var(--bg-card) !important;
        font-weight: 600 !important;
    }

    /* ===== ラジオボタン（期間選択：セグメントコントロール） ===== */
    [data-testid="column"]:last-child .stRadio {
        display: flex;
        justify-content: flex-end;
    }

    /* ボタン群をひとつの横バーに */
    .stRadio > div {
        display: inline-flex !important;
        flex-direction: row !important;
        gap: 0 !important;
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 3px !important;
        box-shadow: inset 0 1px 2px rgba(15,23,42,0.05) !important;
    }

    /* 各オプション */
    .stRadio label {
        background: transparent !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.28rem 0.88rem !important;
        font-size: 0.72rem !important;
        font-family: var(--mono-font) !important;
        color: var(--text-muted) !important;
        cursor: pointer;
        transition: background 0.15s, color 0.15s, box-shadow 0.15s;
        display: flex !important;
        align-items: center !important;
        gap: 0 !important;
        box-shadow: none !important;
        white-space: nowrap;
    }

    /* ラジオのネイティブUI要素を非表示 */
    .stRadio label > div:first-child,
    .stRadio label > span:first-child,
    .stRadio label input[type="radio"],
    .stRadio label svg {
        display: none !important;
    }

    .stRadio label p {
        margin: 0 !important;
        font-size: 0.72rem !important;
        font-family: var(--mono-font) !important;
        line-height: 1 !important;
        color: inherit !important;
    }

    /* 選択中 */
    .stRadio label:has(input:checked) {
        background: var(--accent-amber) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 1px 3px rgba(245,158,11,0.45) !important;
    }

    /* ホバー（未選択） */
    .stRadio label:not(:has(input:checked)):hover {
        background: var(--bg-card) !important;
        color: var(--text-secondary) !important;
    }

    /* ===== Streamlit 要素の上書き ===== */
    .stDataFrame, [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        overflow: hidden;
        background: var(--bg-card) !important;
    }

    .stAlert {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: var(--radius-sm) !important;
    }

    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: var(--radius-sm) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stSelectbox > div > div:focus-within {
        border-color: var(--border-accent) !important;
        box-shadow: 0 0 0 3px rgba(245,158,11,0.12) !important;
    }

    /* ドロップダウンリスト */
    [data-baseweb="popover"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-md) !important;
    }

    [data-baseweb="option"] {
        background: var(--bg-card) !important;
        color: var(--text-secondary) !important;
    }

    [data-baseweb="option"]:hover {
        background: var(--bg-highlight) !important;
        color: var(--text-primary) !important;
    }

    /* ===== Plotly チャートの背景を透過 ===== */
    .js-plotly-plot .plotly { background: transparent !important; }
    .js-plotly-plot .plotly .main-svg { background: transparent !important; }

    /* ===== 全体的な余白調整 ===== */
    [data-testid="stVerticalBlock"] { gap: 0.75rem; }
    [data-testid="column"] > div:first-child { padding-top: 0 !important; }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-base); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #c0ccda; }

    /* ===== KPIカード行の高さを揃える（6列ブロックのみ対象） ===== */
    /* :has() で6列のKPIカード行だけを狙い打ち。ヘッダー行(2列)には影響しない */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) {
        align-items: stretch !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) > [data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) > [data-testid="column"] > [data-testid="stVerticalBlock"] {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) > [data-testid="column"] > [data-testid="stVerticalBlock"] > .element-container {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) > [data-testid="column"] > [data-testid="stVerticalBlock"] > .element-container .stMarkdown,
    [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)) > [data-testid="column"] > [data-testid="stVerticalBlock"] > .element-container .stMarkdown > div {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* ===== chart-wrap / Plotlyチャートの表示修正 ===== */
    /* st.markdown('<div class="chart-wrap">') は Streamlit 内で自動クローズされ空div になる → 非表示 */
    .chart-wrap:empty {
        display: none !important;
    }
    /* Plotly チャートコンポーネントにカードスタイルを適用 */
    [data-testid="stPlotlyChart"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 0.85rem 0.85rem 0.25rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 0 !important;
    }
    /* Plotly チャート下の余分な余白を除去 */
    .element-container:has([data-testid="stPlotlyChart"]) {
        margin-bottom: 0 !important;
    }

</style>
""", unsafe_allow_html=True)

# ── タブモジュールを読み込む ──────────────────────────────────────
from tab_overview  import render_overview
from tab_users     import render_users
from tab_tools     import render_tools
from tab_sessions  import render_sessions
from tab_projects  import render_projects
from tab_adoption  import render_adoption

# =============================================================================
# メイン
# =============================================================================

def main():
    if "selected_user" not in st.session_state:
        st.session_state.selected_user = None

    # ── ヘッダー ──────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([3, 2])

    with hdr_l:
        st.markdown("""
        <div class="dash-logo">
            <div class="dash-logo-icon">⬡</div>
            <div>
                <p class="dash-title">Claude Code Usage Dashboard</p>
                <p class="dash-subtitle">チーム全体の利用状況をリアルタイムで把握</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with hdr_r:
        period_options = {"1D": 1, "7D": 7, "30D": 30, "90D": 90, "All": 365}
        selected_period = st.radio(
            "期間",
            options=list(period_options.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )
        days = period_options[selected_period]

    team_id = "default-team"

    # ── 6タブ ─────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "概要", "ユーザー", "ツール", "セッション", "プロジェクト", "普及",
    ])

    with tab1: render_overview(team_id, days)
    with tab2: render_users(team_id, days)
    with tab3: render_tools(team_id, days)
    with tab4: render_sessions(team_id, days)
    with tab5: render_projects(team_id, days)
    with tab6: render_adoption(team_id, days)


# =============================================================================
if __name__ == "__main__":
    main()
