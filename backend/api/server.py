import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows consoles default to cp1252, which crashes on the emoji used in
# log prints — force UTF-8 output instead.
for stream in (sys.stdout, sys.stderr):
    if stream and hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agents.orchestrator import AgentOrchestrator
from llm_client import mistral_chat
import progress

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = AgentOrchestrator()

# ================= PIPELINE =================
# Sync (def) endpoints run in FastAPI's threadpool, so the long
# pipeline doesn't block the event loop and /progress stays live.
@app.post("/run-agent")
def run_agent(body: dict):
    try:
        structured_input = {
            "query": body.get("query"),
            "agent1": body.get("agent1", {}),
            "agent2": body.get("agent2", {}),
            "agent3": body.get("agent3", {}),
            "agent4": body.get("agent4", {})
        }

        result = orchestrator.run_pipeline(structured_input)

        return {
            "status": "success",
            "pipeline_output": result
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# ================= PROGRESS =================
@app.get("/progress")
def get_progress():
    return progress.get()

# ================= APPLY STRATEGY =================
# Saves a dashboard-approved recommendation into Agent 5's memory,
# so it becomes part of the learning context on future runs.
@app.post("/apply-strategy")
def apply_strategy(body: dict):
    try:
        from datetime import datetime
        from agents.agent3.memory_agent import save_memory

        save_memory({
            "timestamp": datetime.utcnow().isoformat(),
            "applied_strategy": str(body.get("strategy", ""))[:1000],
            "source": "dashboard_apply_button"
        })
        return {"status": "saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ================= CHAT =================
@app.post("/chat")
def chat(body: dict):
    msg = body.get("message", "")

    prompt = f"""
You are an agriculture expert.
User: {msg}
Give short, practical answer.
"""

    try:
        reply = mistral_chat([{"role": "user", "content": prompt}])
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Chat unavailable: {e}"}

# ================= RUN =================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8001, reload=True)