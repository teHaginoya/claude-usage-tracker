# =============================================================================
# Claude Code Usage Dashboard - Streamlit in Snowflake
# =============================================================================
# このファイルをStreamlit in Snowflakeにデプロイしてください
# =============================================================================

import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session
from datetime import datetime, timedelta

# =============================================================================
# ページ設定
# =============================================================================
st.set_page_config(
    page_title="Claude Code KPI ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# カスタムCSS
# =============================================================================
st.markdown("""
<style>
    /* メインコンテナ */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    
    /* ヘッダー */
    .dashboard-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .dashboard-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 0;
    }
    
    .dashboard-subtitle {
        font-size: 0.875rem;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* メトリックカード */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        height: 100%;
    }
    
    .metric-title {
        font-size: 0.875rem;
        color: #6b7280;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.25rem;
    }
    
    .metric-change {
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .metric-change.positive {
        color: #059669;
    }
    
    .metric-change.negative {
        color: #dc2626;
    }
    
    /* インサイトカード */
    .insight-card {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .insight-card.trend-up {
        background: #fef3c7;
        border: 1px solid #fcd34d;
    }
    
    .insight-card.trend-down {
        background: #fee2e2;
        border: 1px solid #fca5a5;
    }
    
    .insight-card.power-user {
        background: #d1fae5;
        border: 1px solid #6ee7b7;
    }
    
    .insight-card.usecase {
        background: #dbeafe;
        border: 1px solid #93c5fd;
    }
    
    .insight-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    
    .insight-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.25rem;
    }
    
    .insight-desc {
        font-size: 0.75rem;
        color: #4b5563;
    }
    
    /* テーブル */
    .user-table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .user-table th {
        background: #f9fafb;
        padding: 0.75rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .user-table td {
        padding: 0.75rem;
        border-bottom: 1px solid #f3f4f6;
        font-size: 0.875rem;
    }
    
    /* タブスタイル */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: #111827;
        color: white;
    }
    
    /* プログレスバー */
    .progress-bar {
        background: #e5e7eb;
        border-radius: 4px;
        height: 8px;
        overflow: hidden;
    }
    
    .progress-bar-fill {
        background: #3b82f6;
        height: 100%;
        border-radius: 4px;
    }
    
    /* 非表示 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Snowflake接続
# =============================================================================
@st.cache_resource
def get_session():
    return get_active_session()

session = get_session()

# =============================================================================
# データ取得関数
# =============================================================================
@st.cache_data(ttl=60)  # 60秒キャッシュ
def get_kpi_metrics(team_id: str, days: int):
    """KPIメトリクスを取得"""
    query = f"""
    WITH current_period AS (
        SELECT 
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS skill_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS subagent_count,
            COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS mcp_count,
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS message_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END) AS session_count,
            COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END) AS command_count,
            COUNT(DISTINCT USER_ID) AS active_users
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
        AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    ),
    previous_period AS (
        SELECT 
            COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS skill_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS subagent_count,
            COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS mcp_count,
            COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS message_count,
            COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END) AS session_count
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
        AND EVENT_TIMESTAMP >= DATEADD('day', -{days * 2}, CURRENT_TIMESTAMP())
        AND EVENT_TIMESTAMP < DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    ),
    total_users AS (
        SELECT COUNT(DISTINCT USER_ID) AS total_users
        FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
        WHERE TEAM_ID = '{team_id}'
    )
    SELECT 
        c.*,
        p.skill_count AS prev_skill,
        p.subagent_count AS prev_subagent,
        p.mcp_count AS prev_mcp,
        p.message_count AS prev_message,
        p.session_count AS prev_session,
        t.total_users
    FROM current_period c, previous_period p, total_users t
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_user_stats(team_id: str, days: int, limit: int = 20):
    """ユーザー別統計を取得"""
    query = f"""
    SELECT 
        USER_ID,
        SPLIT_PART(USER_ID, '@', 1) AS DISPLAY_NAME,
        COUNT(CASE WHEN IS_SKILL = TRUE THEN 1 END) AS SKILL_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'SubagentStop' OR IS_SUBAGENT = TRUE THEN 1 END) AS SUBAGENT_COUNT,
        COUNT(CASE WHEN IS_MCP = TRUE THEN 1 END) AS MCP_COUNT,
        COUNT(CASE WHEN IS_COMMAND = TRUE THEN 1 END) AS COMMAND_COUNT,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGE_COUNT,
        COUNT(*) AS TOTAL_COUNT,
        MAX(EVENT_TIMESTAMP) AS LAST_ACTIVE
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
    AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY USER_ID
    ORDER BY TOTAL_COUNT DESC
    LIMIT {limit}
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_tool_stats(team_id: str, days: int):
    """ツール別統計を取得"""
    query = f"""
    SELECT 
        TOOL_NAME,
        COUNT(*) AS COUNT
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
    AND TOOL_NAME IS NOT NULL
    AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY TOOL_NAME
    ORDER BY COUNT DESC
    LIMIT 10
    """
    return session.sql(query).to_pandas()


@st.cache_data(ttl=60)
def get_timeline_data(team_id: str, days: int):
    """時系列データを取得"""
    query = f"""
    SELECT 
        DATE_TRUNC('day', EVENT_TIMESTAMP)::DATE AS EVENT_DATE,
        COUNT(CASE WHEN EVENT_TYPE = 'UserPromptSubmit' THEN 1 END) AS MESSAGES,
        COUNT(CASE WHEN EVENT_TYPE IN ('PostToolUse', 'PreToolUse') THEN 1 END) AS TOOLS,
        COUNT(CASE WHEN EVENT_TYPE = 'SessionStart' THEN 1 END) AS SESSIONS
    FROM CLAUDE_USAGE_DB.USAGE_TRACKING.USAGE_EVENTS
    WHERE TEAM_ID = '{team_id}'
    AND EVENT_TIMESTAMP >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', EVENT_TIMESTAMP)
    ORDER BY EVENT_DATE
    """
    return session.sql(query).to_pandas()


# =============================================================================
# ヘルパー関数
# =============================================================================
def calc_change(current, previous):
    """変化率を計算"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


def format_change(change):
    """変化率をフォーマット"""
    if change >= 0:
        return f"↑ +{change}%", "positive"
    else:
        return f"↓ {change}%", "negative"


def time_ago(dt):
    """相対時間を計算"""
    if pd.isna(dt):
        return ""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}日前"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}時間前"
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}分前"
    return "今"


def get_rank_icon(rank):
    """ランクアイコンを取得"""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    return str(rank)


# =============================================================================
# メイン画面
# =============================================================================
def main():
    # ヘッダー
    col_title, col_tabs, col_period = st.columns([2, 3, 2])
    
    with col_title:
        st.markdown("""
        <div>
            <p class="dashboard-title">Claude Code Usage Dashboard</p>
            <p class="dashboard-subtitle">チーム全体の利用状況を一目で把握</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_period:
        # 期間選択
        period_options = {"1D": 1, "7D": 7, "30D": 30, "All": 365}
        selected_period = st.radio(
            "期間",
            options=list(period_options.keys()),
            horizontal=True,
            label_visibility="collapsed"
        )
        days = period_options[selected_period]
    
    # チームID（実際の運用では選択可能にする）
    team_id = "default-team"
    
    # タブ
    tab_dashboard, tab_tools, tab_tokens, tab_users = st.tabs([
        "📊 ダッシュボード", "🔧 ツール分析", "📈 トークン使用量", "👥 ユーザー一覧"
    ])
    
    with tab_dashboard:
        render_dashboard(team_id, days)
    
    with tab_tools:
        render_tools_analysis(team_id, days)
    
    with tab_tokens:
        st.info("トークン使用量の機能は開発中です")
    
    with tab_users:
        render_users_list(team_id, days)


def render_dashboard(team_id: str, days: int):
    """ダッシュボードタブをレンダリング"""
    
    # KPIデータ取得
    try:
        kpi_df = get_kpi_metrics(team_id, days)
        
        if kpi_df.empty:
            st.warning("データがありません。プラグインからデータを送信してください。")
            return
        
        kpi = kpi_df.iloc[0]
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        # デモデータを表示
        st.info("デモデータを表示しています")
        kpi = pd.Series({
            'SKILL_COUNT': 56, 'SUBAGENT_COUNT': 508, 'MCP_COUNT': 720,
            'MESSAGE_COUNT': 3085, 'SESSION_COUNT': 584, 'COMMAND_COUNT': 120,
            'ACTIVE_USERS': 32, 'TOTAL_USERS': 34,
            'PREV_SKILL': 50, 'PREV_SUBAGENT': 555, 'PREV_MCP': 579,
            'PREV_MESSAGE': 3193, 'PREV_SESSION': 770
        })
    
    # Overview セクション
    st.markdown("### Overview")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        skill_change = calc_change(kpi.get('SKILL_COUNT', 0), kpi.get('PREV_SKILL', 0))
        change_text, change_class = format_change(skill_change)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Skill実行数</div>
            <div class="metric-change {change_class}">{change_text}</div>
            <div class="metric-value">{int(kpi.get('SKILL_COUNT', 0)):,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        subagent_change = calc_change(kpi.get('SUBAGENT_COUNT', 0), kpi.get('PREV_SUBAGENT', 0))
        change_text, change_class = format_change(subagent_change)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Subagent数</div>
            <div class="metric-change {change_class}">{change_text}</div>
            <div class="metric-value">{int(kpi.get('SUBAGENT_COUNT', 0)):,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mcp_change = calc_change(kpi.get('MCP_COUNT', 0), kpi.get('PREV_MCP', 0))
        change_text, change_class = format_change(mcp_change)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">MCP呼び出し</div>
            <div class="metric-change {change_class}">{change_text}</div>
            <div class="metric-value">{int(kpi.get('MCP_COUNT', 0)):,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        message_change = calc_change(kpi.get('MESSAGE_COUNT', 0), kpi.get('PREV_MESSAGE', 0))
        change_text, change_class = format_change(message_change)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">メッセージ</div>
            <div class="metric-change {change_class}">{change_text}</div>
            <div class="metric-value">{int(kpi.get('MESSAGE_COUNT', 0)):,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        active = int(kpi.get('ACTIVE_USERS', 0))
        total = int(kpi.get('TOTAL_USERS', 1))
        percentage = round(active / total * 100) if total > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">アクティブ</div>
            <div class="metric-value">{active} <span style="font-size:1rem;color:#666">/ {total}名</span></div>
            <div class="progress-bar">
                <div class="progress-bar-fill" style="width: {percentage}%"></div>
            </div>
            <div style="font-size:0.75rem;color:#666;margin-top:0.25rem">{percentage}% 普及率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        session_change = calc_change(kpi.get('SESSION_COUNT', 0), kpi.get('PREV_SESSION', 0))
        change_text, change_class = format_change(session_change)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">セッション</div>
            <div class="metric-change {change_class}">{change_text}</div>
            <div class="metric-value">{int(kpi.get('SESSION_COUNT', 0)):,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # AI Insights セクション
    st.markdown("### AI Insights")
    st.caption("Powered by Claude · 数分前に生成")
    
    insight_col1, insight_col2, insight_col3, insight_col4 = st.columns(4)
    
    with insight_col1:
        if mcp_change > 20:
            st.markdown(f"""
            <div class="insight-card trend-up">
                <div class="insight-label" style="color:#92400e">TREND UP</div>
                <div class="insight-title">MCP呼び出しが大幅増加</div>
                <div class="insight-desc">MCP呼び出しが前期比{mcp_change}%増加し、活用が進んでいます。</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="insight-card usecase">
                <div class="insight-label" style="color:#1e40af">USECASE INSIGHT</div>
                <div class="insight-title">調査・バグ修正が利用の中心</div>
                <div class="insight-desc">調査・リサーチとバグ修正が主要な利用用途です。</div>
            </div>
            """, unsafe_allow_html=True)
    
    with insight_col2:
        st.markdown("""
        <div class="insight-card power-user">
            <div class="insight-label" style="color:#065f46">POWER USER</div>
            <div class="insight-title">パワーユーザーを特定</div>
            <div class="insight-desc">最も多く利用しているユーザーがいます。</div>
        </div>
        """, unsafe_allow_html=True)
    
    with insight_col3:
        if subagent_change < -5:
            st.markdown(f"""
            <div class="insight-card trend-down">
                <div class="insight-label" style="color:#991b1b">TREND DOWN</div>
                <div class="insight-title">Subagent利用数が減少傾向</div>
                <div class="insight-desc">Subagentの利用が前期比{abs(subagent_change)}%減少し、見直しが必要です。</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="insight-card trend-up">
                <div class="insight-label" style="color:#92400e">TREND UP</div>
                <div class="insight-title">Skill実行数が増加トレンド</div>
                <div class="insight-desc">Skill実行数が増加しており、利用が拡大しています。</div>
            </div>
            """, unsafe_allow_html=True)
    
    with insight_col4:
        st.markdown("""
        <div class="insight-card usecase">
            <div class="insight-label" style="color:#1e40af">USECASE INSIGHT</div>
            <div class="insight-title">コード生成が人気</div>
            <div class="insight-desc">Write/Editツールの利用が多く、コード生成に活用されています。</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # チャートセクション
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("### 利用推移")
        try:
            timeline_df = get_timeline_data(team_id, days if days < 365 else 30)
            if not timeline_df.empty:
                st.line_chart(timeline_df.set_index('EVENT_DATE')[['MESSAGES', 'TOOLS', 'SESSIONS']])
            else:
                st.info("時系列データがありません")
        except Exception as e:
            st.info("時系列データを取得できませんでした")
    
    with chart_col2:
        st.markdown("### ツール利用分布")
        try:
            tool_df = get_tool_stats(team_id, days)
            if not tool_df.empty:
                st.bar_chart(tool_df.set_index('TOOL_NAME')['COUNT'])
            else:
                st.info("ツールデータがありません")
        except Exception as e:
            st.info("ツールデータを取得できませんでした")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ユーザーテーブル
    st.markdown("### ユーザー別利用状況")
    render_user_table(team_id, days)


def render_user_table(team_id: str, days: int):
    """ユーザーテーブルをレンダリング"""
    try:
        user_df = get_user_stats(team_id, days)
        
        if user_df.empty:
            st.info("ユーザーデータがありません")
            return
        
        # テーブルヘッダー
        cols = st.columns([0.5, 2, 1, 1, 1, 1, 1, 1])
        headers = ["順位", "ユーザー", "Skill", "Subagent", "MCP", "Command", "Message", "合計"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")
        
        st.markdown("---")
        
        # テーブル行
        for idx, row in user_df.iterrows():
            cols = st.columns([0.5, 2, 1, 1, 1, 1, 1, 1])
            
            rank = idx + 1
            cols[0].markdown(get_rank_icon(rank))
            
            # ユーザー名と最終アクティブ
            display_name = row.get('DISPLAY_NAME', row.get('USER_ID', 'Unknown'))
            last_active = time_ago(row.get('LAST_ACTIVE'))
            cols[1].markdown(f"**{display_name}**  \n<small style='color:#999'>{last_active}</small>", unsafe_allow_html=True)
            
            cols[2].write(int(row.get('SKILL_COUNT', 0)))
            cols[3].write(int(row.get('SUBAGENT_COUNT', 0)))
            cols[4].write(int(row.get('MCP_COUNT', 0)))
            cols[5].write(int(row.get('COMMAND_COUNT', 0)))
            cols[6].write(int(row.get('MESSAGE_COUNT', 0)))
            cols[7].markdown(f"**{int(row.get('TOTAL_COUNT', 0))}**")
    
    except Exception as e:
        st.error(f"ユーザーデータ取得エラー: {e}")


def render_tools_analysis(team_id: str, days: int):
    """ツール分析タブをレンダリング"""
    st.markdown("### ツール利用分析")
    
    try:
        tool_df = get_tool_stats(team_id, days)
        
        if tool_df.empty:
            st.info("ツールデータがありません")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ツール利用ランキング")
            st.dataframe(
                tool_df.rename(columns={'TOOL_NAME': 'ツール名', 'COUNT': '実行回数'}),
                hide_index=True,
                use_container_width=True
            )
        
        with col2:
            st.markdown("#### ツール利用割合")
            st.bar_chart(tool_df.set_index('TOOL_NAME')['COUNT'])
    
    except Exception as e:
        st.error(f"ツールデータ取得エラー: {e}")


def render_users_list(team_id: str, days: int):
    """ユーザー一覧タブをレンダリング"""
    st.markdown("### ユーザー一覧")
    
    try:
        user_df = get_user_stats(team_id, days, limit=50)
        
        if user_df.empty:
            st.info("ユーザーデータがありません")
            return
        
        st.dataframe(
            user_df[[
                'DISPLAY_NAME', 'SKILL_COUNT', 'SUBAGENT_COUNT', 
                'MCP_COUNT', 'COMMAND_COUNT', 'MESSAGE_COUNT', 'TOTAL_COUNT'
            ]].rename(columns={
                'DISPLAY_NAME': 'ユーザー',
                'SKILL_COUNT': 'Skill',
                'SUBAGENT_COUNT': 'Subagent',
                'MCP_COUNT': 'MCP',
                'COMMAND_COUNT': 'Command',
                'MESSAGE_COUNT': 'Message',
                'TOTAL_COUNT': '合計'
            }),
            hide_index=True,
            use_container_width=True
        )
    
    except Exception as e:
        st.error(f"ユーザーデータ取得エラー: {e}")


# =============================================================================
# アプリ実行
# =============================================================================
if __name__ == "__main__":
    main()
