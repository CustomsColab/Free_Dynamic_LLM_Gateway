# ============================================================================
# PASTE THIS BLOCK INTO ANY APP  (needs freellm.py next to it + `pip install httpx`)
# ============================================================================
# .env / environment:
#   FREELLM_REGISTRY_URL=https://raw.githubusercontent.com/<USER>/<REPO>/main/registry/models.json
#   GROQ_API_KEY=...  GEMINI_API_KEY=...  CEREBRAS_API_KEY=...  OPENROUTER_API_KEY=...   (only those you have)
from typing import Optional
from freellm import FreeLLM, tool

llm = FreeLLM()          # reads registry + keeps today's rate-limit ledger in .freellm_state.json


# ---- 1. plain call: pick the model by TASK, never by name ----------------------------
#  tasks: chat | fast | coding | reasoning | extraction | vision | long_doc | agent
def call_llm(prompt: str, task: str = "chat", system: Optional[str] = None, **kw) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return llm.chat(msgs, task=task, **kw).text        # auto-skips exhausted gateways, fails over


# ---- 2. function calling: decorate any typed Python function with @tool --------------
@tool
def get_gst_rate(hsn_code: str, intra_state: bool = True) -> dict:
    """Look up the GST rate for an HSN/SAC code.

    Args:
        hsn_code: 4 to 8 digit HSN or SAC code
        intra_state: True for CGST+SGST, False for IGST
    """
    return {"hsn_code": hsn_code, "rate_percent": 18, "type": "CGST+SGST" if intra_state else "IGST"}  # <- your real logic


def call_llm_with_tools(prompt: str, tools=(get_gst_rate,), **kw):
    """Model decides which tool to call; the loop executes it and feeds the result back."""
    res = llm.run(prompt, list(tools), task="agent", **kw)   # only tool-capable free models are considered
    return res.text, res.steps, f"{res.gateway}/{res.model_id}"


# ---- 3. optional helpers ---------------------------------------------------------------
def llm_status() -> dict:
    """Per-gateway: rate_limit_exhausted_today yes/no, requests used today, usable models left."""
    return llm.gateway_status()


# ---- usage examples --------------------------------------------------------------------
if __name__ == "__main__":
    print(call_llm("Summarise GST input tax credit in 2 lines", task="fast"))
    print(call_llm('Return JSON {"entities": [...]} for: Acme Ltd paid Rs 5000 to Ravi', task="extraction",
                   response_format={"type": "json_object"}))
    print(call_llm("Write a Python function to validate a GSTIN", task="coding"))
    print(call_llm(open("long_notice.txt").read() + "\n\nSummarise.", task="long_doc") if False else "")
    answer, steps, used = call_llm_with_tools("What is the GST rate for HSN 8517, inter-state?")
    print(answer, steps, used)
    print(llm_status())
