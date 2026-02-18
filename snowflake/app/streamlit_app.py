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
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    /* ===== ベーステーマ ===== */
    :root {
        --bg-primary:    #0a0e1a;
        --bg-secondary:  #111827;
        --bg-card:       #141c2e;
        --bg-card-hover: #1a2540;
        --border:        #1f2d4a;
        --border-light:  #263351;
        --text-primary:  #e8edf5;
        --text-secondary:#8899b8;
        --text-muted:    #4a5c7a;
        --accent-amber:  #f59e0b;
        --accent-teal:   #14b8a6;
        --accent-blue:   #3b82f6;
        --accent-rose:   #f43f5e;
        --accent-violet: #8b5cf6;
        --accent-green:  #22c55e;
        --positive:      #10b981;
        --negative:      #f43f5e;
        --mono-font: 'DM Mono', 'Courier New', monospace;
        --body-font: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    }

    /* ===== グローバル ===== */
    html, body, [class*="css"] {
        font-family: var(--body-font);
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }

    .main .block-container {
        padding: 1.5rem 2rem 2rem;
        max-width: 1600px;
        background-color: var(--bg-primary);
    }

    /* ===== 非表示 ===== */
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; }

    /* ===== ヘッダー ===== */
    .dash-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .dash-logo-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--accent-amber) 0%, #e07b04 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        box-shadow: 0 0 16px rgba(245, 158, 11, 0.3);
    }

    .dash-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        line-height: 1.2;
        margin: 0;
    }

    .dash-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin: 0.15rem 0 0;
        font-weight: 400;
    }

    /* ===== セクションヘッダー ===== */
    .section-header {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin: 1.75rem 0 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    /* ===== KPIカード ===== */
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.1rem 1.25rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s, transform 0.2s;
        height: 100%;
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: var(--accent-color, var(--accent-teal));
        opacity: 0.8;
    }

    .kpi-card:hover {
        border-color: var(--border-light);
        transform: translateY(-1px);
    }

    .kpi-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    .kpi-label .badge {
        font-size: 0.6rem;
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-weight: 700;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        font-family: var(--mono-font);
        color: var(--text-primary);
        line-height: 1.1;
        letter-spacing: -0.03em;
        margin-bottom: 0.4rem;
    }

    .kpi-change {
        font-size: 0.72rem;
        font-family: var(--mono-font);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .kpi-change.pos { color: var(--positive); }
    .kpi-change.neg { color: var(--negative); }
    .kpi-change.neu { color: var(--text-muted); }

    .kpi-sparkbar {
        display: flex;
        gap: 2px;
        margin-top: 0.6rem;
        align-items: flex-end;
        height: 20px;
    }

    .kpi-sparkbar span {
        flex: 1;
        background: var(--accent-color, var(--accent-teal));
        opacity: 0.5;
        border-radius: 2px 2px 0 0;
        min-height: 3px;
    }

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
        transition: width 1s ease;
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.68rem;
        font-family: var(--mono-font);
        color: var(--text-muted);
        margin-top: 0.3rem;
    }

    /* ===== 利用制限バッジ ===== */
    .limit-badge {
        display: inline-block;
        margin-top: 0.5rem;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: rgba(244, 63, 94, 0.15);
        color: var(--negative);
        border: 1px solid rgba(244, 63, 94, 0.3);
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
        border-radius: 10px;
        padding: 1rem 1.1rem;
        position: relative;
        overflow: hidden;
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
        font-size: 0.6rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .trend-up   .insight-tag { color: var(--accent-amber); }
    .trend-down .insight-tag { color: var(--negative); }
    .power-user .insight-tag { color: var(--accent-green); }
    .usecase    .insight-tag { color: var(--accent-blue); }
    .neutral    .insight-tag { color: var(--accent-violet); }

    .insight-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }

    .insight-desc {
        font-size: 0.72rem;
        color: var(--text-secondary);
        line-height: 1.5;
    }

    /* ===== テーブル ===== */
    .rank-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }

    .rank-table th {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        padding: 0.6rem 0.75rem;
        border-bottom: 1px solid var(--border);
        background: var(--bg-card);
        white-space: nowrap;
    }

    .rank-table th:first-child { border-radius: 8px 0 0 0; }
    .rank-table th:last-child  { border-radius: 0 8px 0 0; }

    .rank-table td {
        padding: 0.7rem 0.75rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.82rem;
        color: var(--text-primary);
        background: var(--bg-card);
    }

    .rank-table tr:hover td { background: var(--bg-card-hover); }
    .rank-table tr:last-child td { border-bottom: none; }

    .rank-icon { font-size: 1rem; line-height: 1; }

    .user-name { font-weight: 600; color: var(--text-primary); }

    .user-time {
        font-size: 0.65rem;
        color: var(--text-muted);
        font-family: var(--mono-font);
    }

    .num-cell {
        font-family: var(--mono-font);
        font-size: 0.82rem;
        text-align: right;
        color: var(--text-secondary);
    }

    .num-cell.highlight { color: var(--accent-amber); font-weight: 600; }

    .tag-pill {
        display: inline-block;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        text-transform: uppercase;
    }

    .tag-skill    { background: rgba(20,184,166,0.15);  color: var(--accent-teal); }
    .tag-mcp      { background: rgba(139,92,246,0.15);  color: var(--accent-violet); }
    .tag-subagent { background: rgba(34,197,94,0.15);   color: var(--accent-green); }
    .tag-command  { background: rgba(59,130,246,0.15);  color: var(--accent-blue); }

    /* ===== ユーザー詳細パネル ===== */
    .detail-panel {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-left: 3px solid var(--accent-amber);
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }

    /* ===== チャートコンテナ ===== */
    .chart-wrap {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.25rem;
    }

    .chart-title {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 1rem;
    }

    /* ===== タブ ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        background: transparent;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px 6px 0 0;
        padding: 0.5rem 1rem;
        font-size: 0.8rem;
        color: var(--text-muted);
        border: none;
        font-family: var(--body-font);
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: var(--bg-card);
        color: var(--text-primary) !important;
        border: 1px solid var(--border);
        border-bottom: 1px solid var(--bg-card);
    }

    /* ===== ラジオボタン（期間選択） ===== */
    .stRadio > div {
        display: flex;
        gap: 0.25rem;
        flex-direction: row !important;
    }

    .stRadio label {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        padding: 0.3rem 0.9rem !important;
        font-size: 0.75rem !important;
        font-family: var(--mono-font) !important;
        color: var(--text-secondary) !important;
        cursor: pointer;
        transition: all 0.15s;
        display: flex !important;
        align-items: center !important;
        gap: 0 !important;
    }

    /* ラジオの丸インジケーターを非表示 */
    .stRadio label > div:first-child,
    .stRadio label > span:first-child,
    .stRadio label input[type="radio"],
    .stRadio label svg {
        display: none !important;
    }

    /* ラベルテキストの余白をリセット */
    .stRadio label p {
        margin: 0 !important;
        font-size: 0.75rem !important;
        font-family: var(--mono-font) !important;
        line-height: 1 !important;
    }

    .stRadio label:has(input:checked) {
        background: var(--accent-amber) !important;
        color: #0a0e1a !important;
        border-color: var(--accent-amber) !important;
        font-weight: 700 !important;
    }

    .stRadio label:not(:has(input:checked)):hover {
        border-color: var(--border-light) !important;
        color: var(--text-primary) !important;
    }

    /* ===== Streamlit 要素の上書き ===== */
    .stDataFrame, [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden;
        background: var(--bg-card) !important;
    }

    .stAlert {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: 8px !important;
    }

    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 6px !important;
    }

    /* ===== ヘッダー下の余白をタイトに ===== */
    [data-testid="column"] > div:first-child { padding-top: 0 !important; }

    /* ===== Plotly チャートの白背景を除去 ===== */
    .js-plotly-plot .plotly { background: transparent !important; }

    /* ===== 全体的な余白調整 ===== */
    [data-testid="stVerticalBlock"] { gap: 0.75rem; }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

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
                <p class="dash-subtitle">チーム全体の利用状況を一目で把握</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with hdr_r:
        # 右寄せラッパー
        st.markdown(
            '<div style="display:flex;justify-content:flex-end;align-items:center;'
            'padding-top:0.25rem">',
            unsafe_allow_html=True,
        )
        period_options = {"1D": 1, "7D": 7, "30D": 30, "90D": 90, "All": 365}
        selected_period = st.radio(
            "期間",
            options=list(period_options.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)
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
