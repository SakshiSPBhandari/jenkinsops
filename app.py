import sys
import types
if "audioop" not in sys.modules:
    sys.modules["audioop"] = types.ModuleType("audioop")

import gradio as gr
from environment.env import JenkinsOpsEnv
from environment.models import Action

env = JenkinsOpsEnv()


def format_observation(obs, info):
    diff = info.get("difficulty", "easy")
    is_easy = diff == "easy"
    
    phase = info.get("phase", "observe")
    phase_icons = {"observe": "🔍 OBSERVE", "diagnose": "🧠 DIAGNOSE", "fix": "🛠️ FIX"}
    phase_display = phase_icons.get(phase, phase.upper())
    
    observed = "✅" if info.get("observed") else "⬜"
    # Show N/A for diagnose in easy mode if not yet diagnosed
    diagnosed = "✅" if info.get("diagnosed") else ("N/A" if is_easy else "⬜")
    
    fix_unlocked = info.get("observed") and (is_easy or info.get("diagnosed"))

    ctx = obs.context_data if obs.context_data else {}
    ctx_lines = "\n".join(f"  `{k}`: `{v}`" for k, v in ctx.items()) if ctx else "  *No context data available*"

    return f"""
### 🚨 Active Pipeline Incident
| Field | Value |
|---|---|
| **Pipeline** | `{obs.pipeline_name}` |
| **Environment** | `{obs.environment}` |
| **Failed Stage** | `{obs.failed_stage}` (Stage {obs.stage_number}/7) |
| **Difficulty** | `{diff.capitalize()}` |
| **Attempts Remaining** | `{obs.attempts_remaining}/{info.get('max_attempts', 8)}` |

### 💻 Error Log
```
{obs.error_message}
```

### 📊 Structured Context Data
{ctx_lines}

### 🗺️ Current Phase: **{phase_display}**
| Observe | Diagnose | Fix |
|:---:|:---:|:---:|
| {observed} | {diagnosed} | {"🔓 Unlocked" if fix_unlocked else "🔒 Locked"} |

**Previous Actions:** `{', '.join(obs.previous_actions) if obs.previous_actions else 'None yet'}`
"""


def generate_history_html(history_logs):
    if not history_logs:
        return "<i>No actions taken yet.</i>"
    rows = ""
    for i, log in enumerate(history_logs, 1):
        score = log.get("score", 0)
        if score == 1.0:
            color, icon = "#22c55e", "✅"
        elif score > 0:
            color, icon = "#f59e0b", "👍"
        elif score == 0:
            color, icon = "#64748b", "➖"
        else:
            color, icon = "#ef4444", "❌"
        msg = log.get("message", "")
        msg_display = (msg[:85] + "...") if len(msg) > 85 else msg
        rows += (
            f"<tr>"
            f"<td style='padding:4px 10px;'><b>#{i}</b></td>"
            f"<td style='padding:4px 10px;font-family:monospace;font-size:12px;'>{log.get('fix', '')}</td>"
            f"<td style='padding:4px 10px;color:{color};font-weight:bold;'>{icon} {score:+.2f}</td>"
            f"<td style='padding:4px 10px;color:#94a3b8;font-size:11px;'>{msg_display}</td>"
            f"</tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;'>"
        "<tr style='background:#1e293b;color:#94a3b8;'>"
        "<th style='padding:4px 10px;'>Step</th>"
        "<th style='padding:4px 10px;'>Action</th>"
        "<th style='padding:4px 10px;'>Reward</th>"
        "<th style='padding:4px 10px;'>Feedback</th>"
        "</tr>"
        f"{rows}</table>"
    )


def reset_scenario(difficulty):
    obs = env.reset(difficulty=difficulty)
    info = {
        "difficulty": difficulty,
        "attempt": 0,
        "phase": "observe",
        "observed": False,
        "diagnosed": False,
        "max_attempts": env.max_attempts
    }
    return (
        format_observation(obs, info),
        generate_history_html([]),
        [],
        gr.update(choices=obs.available_actions, value=None)
    )


def step_scenario(fix, history_logs):
    # Guard: no action selected
    if fix is None or fix == "" or fix == "(click Start to load actions)":
        return (
            "⚠️ Please **select an action** from the dropdown before clicking Apply Fix.",
            generate_history_html(history_logs),
            history_logs,
            gr.update()
        )
    # Guard: no active scenario
    if not getattr(env, "current_scenario", None):
        return (
            "⚠️ No active scenario. Click **Start / Reset Scenario** first.",
            generate_history_html(history_logs),
            history_logs,
            gr.update()
        )

    action = Action(fix=fix)
    obs, reward, done, info = env.step(action)

    history_logs = list(history_logs)
    history_logs.append({"fix": fix, "score": reward.score, "message": reward.message})

    obs_md = format_observation(obs, info)

    if done:
        status_banner = "## ✅ SUCCESS: Pipeline Restored!" if (reward.score >= 0.8) else "## ❌ FAILED: Pipeline Broken!"
        obs_md = f"# {status_banner}\n\n" + obs_md
        
        if (reward.score >= 0.8):
            bonus = " 🌟 *Full trajectory bonus — you solved it through reasoning!*" if reward.trajectory_bonus else ""
            obs_md += f"\n\n> ### 🏆 INCIDENT RESOLVED!\n> Pipeline is back online.{bonus}"
        else:
            obs_md += f"\n\n> ### ⚠️ Episode Over\n> {reward.message}"

    return (
        obs_md,
        generate_history_html(history_logs),
        history_logs,
        gr.update(choices=obs.available_actions, value=None if not done else fix)
    )


# ── GRADIO UI ──
css = ".gradio-container { max-width: 1200px; margin: auto; }"

with gr.Blocks(title="JenkinsOps — DevOps RL Environment", theme=gr.themes.Monochrome(), css=css) as app:
    history_state = gr.State([])

    gr.Image("data:image/jpeg;base64,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", show_label=False, interactive=False, height=180, container=False)
    gr.Markdown("""
# 🦊 JenkinsOps — OpenEnv Hackathon
**Real-world CI/CD pipeline failure simulator.**  
Your agent must observe, diagnose, and resolve production Jenkins incidents through structured reasoning.
""")

    with gr.Row():
        with gr.Column(scale=1, min_width=280):
            gr.Markdown("## ⚙️ Control")
            difficulty_dd = gr.Dropdown(
                choices=["easy", "medium", "hard"], value="easy",
                label="Task Difficulty"
            )
            start_btn = gr.Button("🚀 Start / Reset Scenario", variant="primary", size="lg")

            gr.Markdown("---")
            gr.Markdown("## 🔧 Execute Action")
            fix_dd = gr.Dropdown(
                choices=["(click Start to load actions)"],
                label="Select Contextual Action"
            )
            submit_btn = gr.Button("▶ Apply Action", variant="secondary", size="lg")

            gr.Markdown("---")
            gr.Markdown("""**Reward Guide**
- `+1.00` — Root cause fixed ✅
- `+1.00` — Perfect Trajectory ✨
- `+0.80` — Base Success ✅
- `+0.10` — Milestone (Obs/Diag) 🔍🧠
- ` 0.00` — Penalty/Incorrect/Loop 🚫""")

        with gr.Column(scale=2):
            gr.Markdown("## 📟 Incident Terminal")
            terminal = gr.Markdown("Click **Start Scenario** to initialize the environment...")

            gr.Markdown("---")
            gr.Markdown("## 📊 Action History")
            history_out = gr.HTML("<i>No actions taken yet.</i>")

    start_btn.click(
        fn=reset_scenario,
        inputs=[difficulty_dd],
        outputs=[terminal, history_out, history_state, fix_dd]
    )
    submit_btn.click(
        fn=step_scenario,
        inputs=[fix_dd, history_state],
        outputs=[terminal, history_out, history_state, fix_dd]
    )

if __name__ == "__main__":
    app.launch()
