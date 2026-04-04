# environment/env.py

import random
from environment.models import Observation, Action, Reward
from environment.scenarios import SCENARIOS, get_contextual_actions
from environment.graders import grade_action


class JenkinsOpsEnv:
    """
    JenkinsOps — Jenkins Pipeline Failure Resolution Environment.

    Implements a prerequisite state machine:
      Phase 0: Must observe (inspect logs, check state)
      Phase 1: Must diagnose (identify root cause)
      Phase 2: Fix unlocked — apply solution

    Easy tasks require Phase 0 → Fix (1 diagnostic step minimum).
    Medium/Hard require Phase 0 → Phase 1 → Fix (2+ steps minimum).
    Hard tasks have 5–6 total required actions before fix is valid.
    """

    MAX_ATTEMPTS = {"easy": 3, "medium": 5, "hard": 8}

    def __init__(self):
        self.current_scenario = None
        self.previous_actions = []
        self.observed = False       # Phase 0 cleared
        self.diagnosed = False      # Phase 1 cleared
        self.attempt_number = 0
        self.max_attempts = 8
        self.done = False           # New persistent state

    def reset(self, difficulty: str = None) -> Observation:
        """Start a new episode with a fresh scenario."""
        pool = [s for s in SCENARIOS if s["difficulty"] == difficulty] \
               if difficulty else SCENARIOS

        self.current_scenario = random.choice(pool)
        self.previous_actions = []
        self.observed = False
        self.diagnosed = False
        self.attempt_number = 0
        self.done = False           # Reset on new episode
        self.max_attempts = self.MAX_ATTEMPTS.get(difficulty or "hard", 8)

        avail = get_contextual_actions(self.current_scenario)

        return Observation(
            category=self.current_scenario["category"],
            pipeline_name=self.current_scenario["pipeline_name"],
            environment=self.current_scenario["environment"],
            failed_stage=self.current_scenario["failed_stage"],
            error_message=self.current_scenario["error_message"],
            stage_number=self.current_scenario["stage_number"],
            previous_actions=[],
            attempt_number=0,
            attempts_remaining=self.max_attempts,
            difficulty=self.current_scenario.get("difficulty", "easy"),
            phase="observe",
            available_actions=avail,
            context_data=self.current_scenario.get("context_data", {})
        )

    def step(self, action: Action):
        """Agent submits an action — graded via prerequisite state machine."""
        
        # Avoid stepping after completion
        if self.done:
             # Just return current state if already finished
             reward = Reward(score=0.0, message="Episode already finished.", is_done=True)
             avail = get_contextual_actions(self.current_scenario)
             return self._get_obs(avail), reward, True, self._get_info(reward)

        self.attempt_number += 1

        reward = grade_action(
            scenario=self.current_scenario,
            action_fix=action.fix,
            previous_actions=self.previous_actions,
            observed=self.observed,
            diagnosed=self.diagnosed
        )

        # Advance phase state based on action tier
        tiers = self.current_scenario.get("action_tiers", {})
        if reward.score > 0:
            if action.fix in tiers.get("observe", []):
                self.observed = True
            if action.fix in tiers.get("diagnose", []):
                self.diagnosed = True

        # Phase-Gap Bridge: Automatically diagnose if tier is empty
        if self.observed and not tiers.get("diagnose", []):
            self.diagnosed = True

        self.previous_actions.append(action.fix)

        # Mark as done if success (0.8+) or grader says so
        if reward.score >= 0.8 or reward.is_done:
            self.done = True
            reward.is_done = True 

        # Force done if max attempts exhausted WITHOUT a success
        if self.attempt_number >= self.max_attempts and not self.done:
            self.done = True
            reward.is_done = True
            reward.message += (
                f" | ❌ Out of attempts. Fail. "
                f"Required: observe→{self.current_scenario['action_tiers'].get('observe',[])} "
                f"diagnose→{self.current_scenario['action_tiers'].get('diagnose',[])} "
                f"fix→{self.current_scenario['action_tiers'].get('fix',[])}"
            )

        avail = get_contextual_actions(self.current_scenario)
        self.last_message = reward.message # Store for the next observation
        observation = self._get_obs(avail)
        info = self._get_info(reward)

        return observation, reward, self.done, info

    def _get_obs(self, avail) -> Observation:
        # Calculate diagnostic count for Hard tasks
        tiers = self.current_scenario.get("action_tiers", {})
        diagnose_list = tiers.get("diagnose", [])
        diag_count = len(set([a for a in self.previous_actions if a in diagnose_list]))
        
        # Difficulty-aware phase transition
        difficulty = self.current_scenario["difficulty"]
        if self.observed and self.diagnosed:
            # Match graders.py: Hard requires 2 diag signals
            if difficulty == "hard" and diag_count < 2:
                phase = "diagnose"
            else:
                phase = "fix"
        elif self.observed:
            phase = "diagnose"
        else:
            phase = "observe"

        return Observation(
            category=self.current_scenario["category"],
            pipeline_name=self.current_scenario["pipeline_name"],
            environment=self.current_scenario["environment"],
            failed_stage=self.current_scenario["failed_stage"],
            error_message=self.current_scenario["error_message"],
            stage_number=self.current_scenario["stage_number"],
            previous_actions=self.previous_actions,
            attempt_number=self.attempt_number,
            attempts_remaining=max(0, self.max_attempts - self.attempt_number),
            difficulty=difficulty,
            phase=phase,
            available_actions=avail,
            action_metadata={
                a: next((t for t, actions in self.current_scenario.get("action_tiers", {}).items() if a in actions), "other") 
                for a in avail
            },
            last_reward_message=getattr(self, "last_message", ""),
            context_data=self.current_scenario.get("context_data", {})
        )

    def _get_info(self, reward) -> dict:
        return {
            "scenario_id": self.current_scenario["id"],
            "difficulty": self.current_scenario["difficulty"],
            "variant_group": self.current_scenario.get("variant_group"),
            "attempt": self.attempt_number,
            "phase": "fix" if (self.observed and self.diagnosed) else ("diagnose" if self.observed else "observe"),
            "observed": self.observed,
            "diagnosed": self.diagnosed,
            "trajectory_bonus": reward.trajectory_bonus,
            "success": self.done and reward.score >= 0.8
        }

    def state(self) -> dict:
        return {
            "current_scenario": self.current_scenario,
            "previous_actions": self.previous_actions,
            "observed": self.observed,
            "diagnosed": self.diagnosed,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts
        }