# =============================================================================
# demo_data.py - SQL 失敗時のフォールバック用デモデータ生成
# =============================================================================

import pandas as pd
from datetime import datetime, timedelta
import random


def _seed():
    random.seed(42)


def demo_kpi_overview():
    return {
        "MSG_COUNT":   3085, "SESS_COUNT": 584, "ACTIVE_USERS": 8,
        "SKILL_COUNT": 56,   "MCP_COUNT":  720, "LIMIT_HITS":  23,
        "PREV_MSG":    2900, "PREV_SESS":  550, "PREV_USERS":   7,
        "PREV_SKILL":  45,   "PREV_MCP":   600, "TOTAL_USERS":  10,
    }


def demo_timeline(days: int) -> pd.DataFrame:
    _seed()
    dates = pd.date_range(end=datetime.today(), periods=min(days, 30), freq="D")
    return pd.DataFrame({
        "EVENT_DATE":  dates,
        "MESSAGES":    [random.randint(60, 180)  for _ in dates],
        "TOOLS":       [random.randint(200, 700)  for _ in dates],
        "SESSIONS":    [random.randint(10, 40)    for _ in dates],
        "LIMIT_HITS":  [random.randint(0, 4)      for _ in dates],
    })


def demo_heatmap() -> pd.DataFrame:
    _seed()
    rows = []
    for dow in range(7):
        for h in range(24):
            cnt = random.randint(0, 55) if 8 <= h <= 22 else random.randint(0, 8)
            rows.append({"DOW": dow, "HOUR_OF_DAY": h, "EVENT_COUNT": cnt})
    return pd.DataFrame(rows)


def demo_users() -> pd.DataFrame:
    _seed()
    names = [
        "te.haginoya", "a.tanaka", "k.suzuki", "m.yamamoto",
        "r.kobayashi", "y.ito", "h.watanabe", "s.nakamura",
    ]
    rows = []
    for u in names:
        rows.append({
            "USER_ID":        u + "@example.com",
            "DISPLAY_NAME":   u,
            "SKILL_COUNT":    random.randint(0, 30),
            "SUBAGENT_COUNT": random.randint(0, 60),
            "MCP_COUNT":      random.randint(0, 120),
            "COMMAND_COUNT":  random.randint(0, 25),
            "MESSAGE_COUNT":  random.randint(40, 280),
            "SESSION_COUNT":  random.randint(5, 50),
            "LIMIT_HITS":     random.randint(0, 6),
            "TOTAL_COUNT":    random.randint(200, 1200),
            "LAST_ACTIVE":    datetime.now() - timedelta(hours=random.randint(1, 96)),
            "FIRST_ACTIVE":   (datetime.now() - timedelta(days=random.randint(3, 60))).date(),
        })
    return pd.DataFrame(rows)


def demo_user_timeline(days: int) -> pd.DataFrame:
    return demo_timeline(days)


def demo_user_top_tools() -> pd.DataFrame:
    _seed()
    tools = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "Task"]
    return pd.DataFrame({
        "TOOL_NAME": tools,
        "CNT":       [random.randint(10, 200) for _ in tools],
    }).sort_values("CNT", ascending=False)


def demo_tools() -> pd.DataFrame:
    _seed()
    tools = [
        "Bash", "Read", "Write", "Edit", "Glob", "Grep",
        "WebFetch", "Task", "TodoWrite", "NotebookEdit", "WebSearch",
    ]
    rows = []
    for t in tools:
        cnt  = random.randint(40, 900)
        succ = random.randint(int(cnt * 0.65), cnt)
        rows.append({
            "TOOL_NAME":     t,
            "TOTAL_COUNT":   cnt,
            "SUCCESS_COUNT": succ,
            "SUCCESS_RATE":  round(succ / cnt * 100, 1),
        })
    return pd.DataFrame(rows).sort_values("TOTAL_COUNT", ascending=False)


def demo_tool_trend(days: int) -> pd.DataFrame:
    _seed()
    top_tools = ["Bash", "Read", "Write", "Edit", "Glob"]
    dates = pd.date_range(end=datetime.today(), periods=min(days, 30), freq="D")
    rows = []
    for t in top_tools:
        for d in dates:
            rows.append({"EVENT_DATE": d, "TOOL_NAME": t, "CNT": random.randint(5, 120)})
    return pd.DataFrame(rows)


def demo_session_kpi() -> pd.DataFrame:
    return pd.DataFrame({
        "TOTAL_SESSIONS":    [151],
        "AVG_DURATION_MIN":  [18.5],
        "LIMIT_STOPPED":     [23],
        "NORMAL_STOPPED":    [120],
        "ACTIVE_USERS_SESS": [8],
    })


def demo_stop_reason() -> pd.DataFrame:
    return pd.DataFrame({
        "STOP_REASON":   ["normal", "usage_limit", "unknown"],
        "SESSION_COUNT": [120, 23, 8],
    })


def demo_limit_by_hour() -> pd.DataFrame:
    _seed()
    hours = list(range(24))
    hits  = [random.randint(0, 9) if 9 <= h <= 22 else random.randint(0, 2) for h in hours]
    return pd.DataFrame({"HOUR_OF_DAY": hours, "LIMIT_HITS": hits})


def demo_projects() -> pd.DataFrame:
    _seed()
    projs = [
        "claude-usage-tracker", "webapp-refactor", "data-pipeline",
        "api-service", "ml-experiment", "(no project)",
    ]
    rows = []
    for p in projs:
        ec = random.randint(80, 2500)
        rows.append({
            "PROJECT_NAME": p,
            "EVENT_COUNT":  ec,
            "USER_COUNT":   random.randint(1, 6),
            "MSG_COUNT":    random.randint(20, 250),
            "SKILL_COUNT":  random.randint(0, 25),
            "MCP_COUNT":    random.randint(0, 60),
        })
    return pd.DataFrame(rows).sort_values("EVENT_COUNT", ascending=False)


def demo_monthly() -> pd.DataFrame:
    _seed()
    months = pd.date_range(end=datetime.today().replace(day=1), periods=6, freq="MS")
    return pd.DataFrame({
        "MONTH":        months,
        "ACTIVE_USERS": [random.randint(2, 10)    for _ in months],
        "SESSIONS":     [random.randint(40, 200)  for _ in months],
        "MESSAGES":     [random.randint(400, 2000) for _ in months],
    })


def demo_feature_adoption() -> pd.DataFrame:
    return pd.DataFrame({
        "TOTAL_USERS":    [10],
        "SKILL_USERS":    [4],
        "MCP_USERS":      [6],
        "SUBAGENT_USERS": [3],
        "COMMAND_USERS":  [7],
    })
