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

    gr.HTML("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                padding: 30px; 
                border-radius: 12px; 
                border: 1px solid #334155; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                text-align: center;
                margin-bottom: 20px;">
        <h1 style="color: #60a5fa; font-family: 'Outfit', sans-serif; font-size: 32px; letter-spacing: 0.1em; margin: 0; text-shadow: 0 0 20px rgba(96,165,250,0.4);">
            🏁 JENKINSOPS
        </h1>
        <p style="color: #94a3b8; font-family: 'Inter', sans-serif; font-size: 14px; margin-top: 10px; text-transform: uppercase; letter-spacing: 0.2em;">
            Strategic CI/CD Incident Simulation
        </p>
    </div>
    """)

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
