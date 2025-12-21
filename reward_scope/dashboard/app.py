"""
FastAPI Dashboard Application

Real-time web dashboard for RL training visualization.
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
from pathlib import Path
from typing import Optional
import json

from ..core.collector import DataCollector


app = FastAPI(title="RewardScope Dashboard", version="0.1.0")

# Global state (set by run_dashboard function)
collector: Optional[DataCollector] = None
run_name: str = "unknown"

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files directory
static_dir = templates_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "run_name": run_name,
        }
    )


@app.get("/api/reward-history")
async def get_reward_history(n: int = 100):
    """
    Get recent reward history.
    
    Returns:
        {
            "steps": [int],
            "rewards": [float],
            "episodes": [int]
        }
    """
    if not collector:
        return {"error": "No data collector initialized"}
    
    try:
        # Flush buffer to ensure latest data is available
        collector._flush_step_buffer()
        
        steps = collector.get_recent_steps(n)
        return {
            "steps": [s.step for s in steps],
            "rewards": [s.reward for s in steps],
            "episodes": [s.episode for s in steps],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/component-breakdown")
async def get_component_breakdown(n: int = 100):
    """
    Get reward component breakdown.
    
    Returns:
        {
            "components": [str],
            "values": [float]
        }
    """
    if not collector:
        return {"error": "No data collector initialized"}
    
    try:
        # Flush buffer to ensure latest data is available
        collector._flush_step_buffer()
        
        steps = collector.get_recent_steps(n)
        
        # Aggregate components
        component_sums = {}
        for step in steps:
            for name, value in step.reward_components.items():
                if name not in component_sums:
                    component_sums[name] = 0.0
                component_sums[name] += abs(value)  # Use absolute values for pie chart
        
        return {
            "components": list(component_sums.keys()),
            "values": list(component_sums.values()),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/episode-history")
async def get_episode_history(n: int = 50):
    """
    Get episode-level statistics.
    
    Returns:
        {
            "episodes": [int],
            "total_rewards": [float],
            "lengths": [int],
            "hacking_scores": [float]
        }
    """
    if not collector:
        return {"error": "No data collector initialized"}
    
    try:
        episodes = collector.get_episode_history(n)
        return {
            "episodes": [e.episode for e in episodes],
            "total_rewards": [e.total_reward for e in episodes],
            "lengths": [e.length for e in episodes],
            "hacking_scores": [e.hacking_score for e in episodes],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/alerts")
async def get_alerts():
    """
    Get recent hacking alerts.
    
    Returns:
        {
            "alerts": [
                {
                    "episode": int,
                    "type": str,
                    "severity": float,
                    "description": str
                }
            ]
        }
    """
    if not collector:
        return {"error": "No data collector initialized"}
    
    try:
        episodes = collector.get_episode_history(10)
        alerts = []
        for ep in episodes:
            for flag in ep.hacking_flags:
                alerts.append({
                    "episode": ep.episode,
                    "type": flag,
                    "severity": ep.hacking_score,
                    "description": flag.replace("_", " ").title(),
                })
        
        return {"alerts": alerts}
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for live updates (10Hz).
    
    Sends JSON messages with step updates:
    {
        "type": "step_update",
        "step": int,
        "reward": float,
        "components": {str: float},
        "episode": int
    }
    """
    await websocket.accept()
    
    try:
        last_step = 0
        while True:
            # Check for new data
            if collector:
                try:
                    # Flush buffer to get latest data
                    collector._flush_step_buffer()
                    
                    steps = collector.get_recent_steps(10)
                    if steps and steps[-1].step > last_step:
                        last_step = steps[-1].step
                        
                        # Send update
                        await websocket.send_json({
                            "type": "step_update",
                            "step": last_step,
                            "reward": steps[-1].reward,
                            "components": steps[-1].reward_components,
                            "episode": steps[-1].episode,
                        })
                except Exception as e:
                    # Don't crash on errors, just continue
                    print(f"WebSocket error: {e}")
            
            await asyncio.sleep(0.1)  # 10 Hz updates
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket connection error: {e}")


def run_dashboard(
    data_dir: str,
    run_name_param: str,
    port: int = 8050,
    host: str = "0.0.0.0",
):
    """
    Start the dashboard server.
    
    Args:
        data_dir: Directory containing the SQLite database
        run_name_param: Name of the run to display
        port: Port to run the server on
        host: Host to bind to
    """
    global collector, run_name
    
    run_name = run_name_param
    collector = DataCollector(run_name, data_dir)
    
    print(f"\n🔬 RewardScope Dashboard Starting...")
    print(f"   Run: {run_name}")
    print(f"   URL: http://localhost:{port}")
    print(f"   Data: {data_dir}\n")
    
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")

