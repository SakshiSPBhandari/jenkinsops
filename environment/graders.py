# environment/graders.py

from environment.models import Reward


def grade_action(
    scenario: dict,
    action_fix: str,
    previous_actions: list,
    observed: bool,
    diagnosed: bool
) -> Reward:
    """
    Prerequisite State Machine Grader.

    Actions are evaluated based on the agent's current phase:
      Phase 0 — Not yet observed → only observe-tier actions progress
      Phase 1 — Observed, not yet diagnosed → diagnose-tier unlocked
      Phase 2 — Observed + Diagnosed → fix-tier unlocked

    Reward tiers:
      +0.2  Correct observe-tier action (new)
      +0.3  Correct diagnose-tier action (new)
      +0.5  Correct fix after full observe+diagnose trajectory
      +1.0  Correct fix (always episode-ending, trajectory bonus in info)
      -0.2  Wrong or irrelevant action
      -0.1  First repeat of any action
      -0.3  Second+ repeat (loop)
      -0.5  Fix attempted before root cause confirmed (prerequisite gate)
      done=True with -0.5 if same action repeated 3+ times
    """
    tiers = scenario.get("action_tiers", {})
    observe_actions  = tiers.get("observe", [])
    diagnose_actions = tiers.get("diagnose", [])
    fix_actions      = tiers.get("fix", [])
    difficulty       = scenario.get("difficulty", "medium")

    # ── 1. Prerequisite Gate — Fix blocked without prior observation+diagnosis ──
    if action_fix in fix_actions:
        if not observed:
            return Reward(
                score=0.01,  # Zero-floor for penalties
                message="🚫 Prerequisite not met: You cannot apply a fix before observing the failure. "
                        "Start by inspecting logs, headers, or system state.",
                is_done=False
            )
        # Easy tasks: observation alone is sufficient to unlock fix
        # Medium: observation AND diagnosis required
        # Hard: 2+ observations AND 2+ diagnoses required (4-6 steps total)
        if difficulty == "hard":
            required_obs = 2
            required_diag = 2
            current_obs_count = len([a for a in previous_actions if a in observe_actions])
            current_diag_count = len([a for a in previous_actions if a in diagnose_actions])
            
            if current_obs_count < required_obs:
                return Reward(
                    score=0.01,
                    message=f"⚠️ Insufficient evidence. Hard tasks require multiple observations ({current_obs_count}/{required_obs}).",
                    is_done=False
                )
            if current_diag_count < required_diag:
                return Reward(
                    score=0.01,
                    message=f"⚠️ Incomplete diagnosis. Hard tasks require multi-signal confirmation ({current_diag_count}/{required_diag}).",
                    is_done=False
                )
        elif difficulty == "medium":
            # Bridge if no diagnose tier exists
            if not diagnosed and tiers.get("diagnose", []):
                return Reward(
                    score=0.01,
                    message="🚫 Prerequisite not met: You need to diagnose the root cause before applying a fix.",
                    is_done=False
                )
        
        # Prerequisites met — apply fix
        # Bridging if diagnostic tier is empty
        diag_met = diagnosed or not tiers.get("diagnose", [])
        final_score = 0.99 if (observed and diag_met) else 0.8
        
        return Reward(
            score=final_score,
            message=f"✅ Root cause resolved! {scenario.get('resolution', '')}",
            is_done=True,
            trajectory_bonus=(observed and diag_met)
        )

    # ── 2. Consecutive Repetition & Loop Detection ──
    if previous_actions:
        if action_fix == previous_actions[-1]:
            return Reward(
                score=0.01, # Zero-floor for penalties
                message=f"🔴 FATAL: Consecutive repetition '{action_fix}'. Episode terminated.",
                is_done=True
            )

    repeat_count = previous_actions.count(action_fix)
    if repeat_count >= 2:
        return Reward(
            score=0.01,
            message=f"🔴 Loop Detection: '{action_fix}' repeated {repeat_count + 1} times. Terminating episode.",
            is_done=True
        )
    if repeat_count == 1:
        return Reward(
            score=0.01,
            message=f"⚠️ Already tried '{action_fix}'. Explore a different direction.",
            is_done=False
        )

    # ── 3. Observe Tier ──
    if action_fix in observe_actions:
        return Reward(
            score=0.1,  # Reduced but positive for progress
            message="🔍 Good — you've gathered system state. This narrows the failure scope.",
            is_done=False
        )

    # ── 4. Diagnose Tier ──
    if action_fix in diagnose_actions:
        if not observed:
            return Reward(
                score=0.01,
                message="⚠️ Attempting diagnosis before observation. Try inspecting state first.",
                is_done=False
            )
        return Reward(
            score=0.1,  # Positive for milestone
            message="🧠 Root cause identified! Apply the fix when ready.",
            is_done=False
        )

    # ── 5. Explicitly listed irrelevant action ──
    if action_fix in scenario.get("irrelevant_actions", []):
        return Reward(
            score=0.01,
            message=f"❌ Unrelated to this failure. Hint: {scenario.get('hint', '')}",
            is_done=False
        )

    # ── 6. Domain-relevant but not a named action (exploration signal) ──
    if difficulty != "easy":
        domain_keywords = {
            "git":      ["git", "branch", "token", "github", "repo"],
            "docker":   ["docker", "build", "image", "container", "buildx"],
            "ecs":      ["ecs", "task", "service", "fargate", "ecr"],
            "infra":    ["tf", "terraform", "lock", "iam", "policy"],
            "npm":      ["npm", "node", "package", "peer", "jest"],
            "security": ["sonar", "checkmarx", "scan", "token", "auth"],
            "auth":     ["token", "secret", "rotate", "credential"],
            "k8s":      ["k8s", "kubectl", "manifest", "pod"],
        }
        keywords = domain_keywords.get(scenario.get("category", ""), [])
        if any(kw in action_fix.lower() for kw in keywords):
            return Reward(
                score=0.05,  # Small positive for safe domain exploration
                message=f"➕ Right domain. Hint: {scenario.get('hint', '')}",
                is_done=False
            )

    # ── 7. Completely wrong action ──
    return Reward(
        score=0.01,
        message=f"❌ Unrelated to this failure. Hint: {scenario.get('hint', '')}",
        is_done=False
    )