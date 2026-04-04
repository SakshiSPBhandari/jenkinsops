# environment/models.py

from pydantic import BaseModel
from typing import List, Optional

class Observation(BaseModel):
    """What the agent SEES — the Jenkins failure details"""
    category: str               # e.g. "git", "docker", "ecs"
    pipeline_name: str          # e.g. "payment-service-build"
    environment: str            # e.g. "UAT", "PreProd", "Prod"
    failed_stage: str           # e.g. "checkmarx", "git-checkout"
    error_message: str          # e.g. "Project not found in Checkmarx"
    stage_number: int           # e.g. 3 (out of 7)
    previous_actions: List[str] # what fixes agent already tried
    attempt_number: int         # how many attempts so far
    attempts_remaining: int     # how many attempts left before failure
    difficulty: str             # e.g. "easy", "medium", "hard"
    phase: str                  # current phase: "observe", "diagnose", or "fix"
    available_actions: List[str]# dynamically filtered list of valid context actions
    action_metadata: dict = {}  # Map of action names to their tiers (observe, diagnose, fix)
    last_reward_message: str = "" # Feedback from the grader about the last step
    context_data: dict = {}     # rich structured signal: headers, status codes, metrics

class Action(BaseModel):
    """What the agent DOES — the fix it chooses"""
    fix: str                    # e.g. "retry_scan", "correct_branch_name"
    reasoning: Optional[str] = None    # why the agent chose this fix

class Reward(BaseModel):
    """How well the agent DID — the score"""
    score: float                        # -0.5 to 1.0
    message: str                        # feedback message
    is_done: bool                       # True = episode over
    trajectory_bonus: bool = False      # True = agent completed full observe→diagnose→fix path