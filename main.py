# main.py — FastAPI server (OpenEnv REST API for HuggingFace Space)

import sys
import types
if "audioop" not in sys.modules:
    sys.modules["audioop"] = types.ModuleType("audioop")

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from environment.env import JenkinsOpsEnv
from environment.models import Action

app = FastAPI(
    title="JenkinsOps",
    description=(
        "Phase-driven RL environment where an AI agent debugs real Jenkins CI/CD failures "
        "through structured multi-step reasoning. OBSERVE → DIAGNOSE → FIX."
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

env = JenkinsOpsEnv()


@app.get("/")
def root():
    return {
        "name": "JenkinsOps",
        "version": "2.0.0",
        "description": "Phase-driven DevOps RL environment. OBSERVE → DIAGNOSE → FIX.",
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/health"]
    }

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/reset")
def reset(difficulty: str = Query(default=None, description="easy | medium | hard")):
    """Start a new episode. Returns the initial observation."""
    obs = env.reset(difficulty=difficulty)
    return obs.dict()


@app.post("/step")
def step(action: Action):
    """Submit an action. Returns observation, reward, done flag, and info."""
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.dict(),
        "reward": reward.dict(),
        "done": done,
        "info": info
    }


@app.get("/state")
def state():
    """Return raw environment internal state for debugging."""
    return env.state()


@app.get("/tasks")
def tasks():
    """Return all available task difficulties with step requirements."""
    return {
        "tasks": [
            {
                "id": "easy",
                "name": "Basic Pipeline Failure",
                "difficulty": "easy",
                "steps": "2–3",
                "max_attempts": 3,
                "description": "Direct error→fix mapping. One observe step unlocks the fix.",
                "example_path": "inspect → correct_branch_name"
            },
            {
                "id": "medium",
                "name": "Deployment Failure",
                "difficulty": "medium",
                "steps": "3–4",
                "max_attempts": 5,
                "description": "Requires observe + diagnose before fix is gated open.",
                "example_path": "inspect_task_definition → compare_environment_account_ids → correct_task_definition"
            },
            {
                "id": "hard",
                "name": "Cascading Multi-Signal Failure",
                "difficulty": "hard",
                "steps": "4–6",
                "max_attempts": 8,
                "description": "Multi-service failures, shared root causes, ambiguous signals. context_data is critical.",
                "example_path": "observe1 → observe2 → diagnose1 → diagnose2 → diagnose3 → fix"
            }
        ]
    }

import gradio as gr
from app import app as ui_app

app = gr.mount_gradio_app(app, ui_app, path="/ui")