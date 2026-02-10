"""
Claude Code Usage Tracker - API Server
チームの利用状況を収集・保存・提供するバックエンドAPI
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json
import os

# ==============================================================================
# Models
# ==============================================================================

class EventPayload(BaseModel):
    event_type: str
    timestamp: str
    user_id: str
    team_id: str
    project: Optional[str] = ""
    session_id: Optional[str] = ""
    tool_name: Optional[str] = None
    categories: Optional[Dict[str, bool]] = None
    success: Optional[bool] = None
    output_length: Optional[int] = None
    prompt_length: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class DashboardStats(BaseModel):
    skill_count: int
    subagent_count: int
    mcp_count: int
    message_count: int
    session_count: int
    command_count: int
    active_users: int
    total_users: int
    skill_change: float
    subagent_change: float
    mcp_change: float
    message_change: float
    session_change: float
    period_start: str
    period_end: str


class UserStats(BaseModel):
    user_id: str
    display_name: str
    skill_count: int
    subagent_count: int
    mcp_count: int
    command_count: int
    message_count: int
    total_count: int
    last_active: str


# ==============================================================================
# Storage (本番ではFirestore/PostgreSQLに置き換え)
# ==============================================================================

events_store: List[Dict] = []
API_KEY = os.environ.get("USAGE_TRACKER_API_KEY", "")


# ==============================================================================
# FastAPI App
# ==============================================================================

app = FastAPI(
    title="Claude Code Usage Tracker API",
    description="チームのClaude Code利用状況を収集・分析するAPI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Auth
# ==============================================================================

async def verify_api_key(authorization: Optional[str] = Header(None)):
    """APIキー認証"""
    if not API_KEY:
        return True  # 認証なしモード
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    if authorization[7:] != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/")
async def root():
    return {"status": "ok", "service": "Claude Code Usage Tracker API"}


@app.get("/health")
async def health():
    return {"status": "healthy", "events_count": len(events_store)}


@app.post("/api/events")
async def receive_event(payload: EventPayload, _: bool = Depends(verify_api_key)):
    """イベントを受信して保存"""
    event = payload.dict()
    event["received_at"] = datetime.now(timezone.utc).isoformat()
    events_store.append(event)
    
    # メモリ制限
    if len(events_store) > 50000:
        events_store.pop(0)
    
    return {"status": "ok", "event_id": len(events_store)}


@app.get("/api/stats", response_model=DashboardStats)
async def get_stats(
    team_id: str = "default-team",
    days: int = 1,
    _: bool = Depends(verify_api_key)
):
    """ダッシュボード用の統計を取得"""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    prev_period_start = period_start - timedelta(days=days)
    
    def parse_ts(ts_str):
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    
    current_events = [
        e for e in events_store
        if e.get("team_id") == team_id
        and parse_ts(e["timestamp"]) >= period_start
    ]
    
    prev_events = [
        e for e in events_store
        if e.get("team_id") == team_id
        and prev_period_start <= parse_ts(e["timestamp"]) < period_start
    ]
    
    def count_category(events, category):
        return sum(1 for e in events if e.get("categories", {}).get(category, False))
    
    def count_event_type(events, event_type):
        return sum(1 for e in events if e.get("event_type") == event_type)
    
    # 現在期間
    skill_count = count_category(current_events, "skill")
    subagent_count = count_event_type(current_events, "SubagentStop")
    mcp_count = count_category(current_events, "mcp")
    message_count = count_event_type(current_events, "UserPromptSubmit")
    session_count = count_event_type(current_events, "SessionStart")
    command_count = count_category(current_events, "command")
    
    # 前期間
    prev_skill = count_category(prev_events, "skill")
    prev_subagent = count_event_type(prev_events, "SubagentStop")
    prev_mcp = count_category(prev_events, "mcp")
    prev_message = count_event_type(prev_events, "UserPromptSubmit")
    prev_session = count_event_type(prev_events, "SessionStart")
    
    def calc_change(current, prev):
        if prev == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - prev) / prev * 100, 1)
    
    active_users = len(set(e.get("user_id") for e in current_events))
    total_users = len(set(e.get("user_id") for e in events_store if e.get("team_id") == team_id))
    
    return DashboardStats(
        skill_count=skill_count,
        subagent_count=subagent_count,
        mcp_count=mcp_count,
        message_count=message_count,
        session_count=session_count,
        command_count=command_count,
        active_users=active_users,
        total_users=total_users,
        skill_change=calc_change(skill_count, prev_skill),
        subagent_change=calc_change(subagent_count, prev_subagent),
        mcp_change=calc_change(mcp_count, prev_mcp),
        message_change=calc_change(message_count, prev_message),
        session_change=calc_change(session_count, prev_session),
        period_start=period_start.isoformat(),
        period_end=now.isoformat(),
    )


@app.get("/api/users", response_model=List[UserStats])
async def get_user_stats(
    team_id: str = "default-team",
    days: int = 1,
    limit: int = 20,
    _: bool = Depends(verify_api_key)
):
    """ユーザー別の統計を取得"""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    
    filtered_events = [
        e for e in events_store
        if e.get("team_id") == team_id
        and datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) >= period_start
    ]
    
    user_stats: Dict[str, Dict] = defaultdict(lambda: {
        "skill_count": 0, "subagent_count": 0, "mcp_count": 0,
        "command_count": 0, "message_count": 0, "total_count": 0, "last_active": ""
    })
    
    for e in filtered_events:
        user_id = e.get("user_id", "unknown")
        stats = user_stats[user_id]
        stats["total_count"] += 1
        
        categories = e.get("categories", {})
        if categories.get("skill"):
            stats["skill_count"] += 1
        if categories.get("mcp"):
            stats["mcp_count"] += 1
        if categories.get("command"):
            stats["command_count"] += 1
        
        if e.get("event_type") == "SubagentStop":
            stats["subagent_count"] += 1
        if e.get("event_type") == "UserPromptSubmit":
            stats["message_count"] += 1
        
        ts = e.get("timestamp", "")
        if ts > stats["last_active"]:
            stats["last_active"] = ts
    
    result = []
    for user_id, stats in user_stats.items():
        display_name = user_id.split("@")[0] if "@" in user_id else user_id
        result.append(UserStats(user_id=user_id, display_name=display_name, **stats))
    
    result.sort(key=lambda x: x.total_count, reverse=True)
    return result[:limit]


@app.get("/api/tools")
async def get_tool_stats(
    team_id: str = "default-team",
    days: int = 1,
    _: bool = Depends(verify_api_key)
):
    """ツール別の利用統計を取得"""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    
    filtered_events = [
        e for e in events_store
        if e.get("team_id") == team_id
        and e.get("event_type") in ["PostToolUse", "PreToolUse"]
        and datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) >= period_start
    ]
    
    tool_counts: Dict[str, int] = defaultdict(int)
    for e in filtered_events:
        tool_counts[e.get("tool_name", "unknown")] += 1
    
    sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "tools": [{"name": name, "count": count} for name, count in sorted_tools],
        "total": sum(tool_counts.values()),
    }


@app.get("/api/timeline")
async def get_timeline(
    team_id: str = "default-team",
    days: int = 7,
    _: bool = Depends(verify_api_key)
):
    """時系列データを取得"""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    
    filtered_events = [
        e for e in events_store
        if e.get("team_id") == team_id
        and datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) >= period_start
    ]
    
    daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "messages": 0, "tools": 0, "sessions": 0
    })
    
    for e in filtered_events:
        date = e.get("timestamp", "")[:10]
        event_type = e.get("event_type", "")
        
        if event_type == "UserPromptSubmit":
            daily_counts[date]["messages"] += 1
        elif event_type in ["PostToolUse", "PreToolUse"]:
            daily_counts[date]["tools"] += 1
        elif event_type == "SessionStart":
            daily_counts[date]["sessions"] += 1
    
    timeline = [{"date": date, **counts} for date, counts in sorted(daily_counts.items())]
    return {"timeline": timeline}


# ==============================================================================
# Run
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
