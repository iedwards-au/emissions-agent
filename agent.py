# The agentic loop. Sends messages to Claude → executes tool calls → feeds results back → loops until Claude reaches end_turn.
import os
import json
import anthropic
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT, BRIEF_CLARIFICATION_PROMPT
from tools import TOOL_DEFINITIONS, execute_tool
from pdf_report import generate_pdf

load_dotenv()

# ── Support both .env (local) and Streamlit secrets (cloud) ──────────────────
def _get_secret(key: str) -> str | None:
    """Get a secret from Streamlit secrets (cloud) or os.environ (local)."""
    try:
        import streamlit as st
        return st.secrets.get(key) or os.getenv(key)
    except Exception:
        return os.getenv(key)


def _make_client():
    api_key = _get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


# ── Brief clarification check ─────────────────────────────────────────────────

def check_brief_clarity(brief: str) -> str | None:
    """
    Returns None if brief is clear enough to proceed.
    Returns a clarifying question string if more info is needed.
    """
    client = _make_client()
    prompt = BRIEF_CLARIFICATION_PROMPT.format(brief=brief)
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.content[0].text.strip()
    if result.startswith("CLARIFY:"):
        return result.replace("CLARIFY:", "").strip()
    return None


# ── Agentic loop ──────────────────────────────────────────────────────────────

def run_agent(user_message: str, conversation_history: list = None) -> dict:
    """
    Run the Scope3 agent for one user turn.
    Returns: {
        "response": str,
        "pdf_path": str | None,
        "tool_calls": list,
        "conversation": list
    }
    """
    if conversation_history is None:
        conversation_history = []

    client = _make_client()
    conversation_history.append({"role": "user", "content": user_message})

    tool_calls_log = []
    pdf_path = None
    final_response = ""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=conversation_history
        )

        assistant_content = response.content
        stop_reason = response.stop_reason

        if stop_reason == "end_turn":
            for block in assistant_content:
                if block.type == "text":
                    final_response = block.text
            conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })
            break

        elif stop_reason == "tool_use":
            conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })

            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    print(f"  [agent] calling tool: {tool_name}")
                    tool_calls_log.append({"tool": tool_name, "input": tool_input})

                    result_json = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_json
                    })

            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
        else:
            break

    return {
        "response": final_response,
        "pdf_path": pdf_path,
        "tool_calls": tool_calls_log,
        "conversation": conversation_history
    }


# ── CLI interface ─────────────────────────────────────────────────────────────

def main():
    print("\n🌿 Scope3 Inventory Agent")
    print("=" * 50)

    conversation = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        print("\nAgent thinking...\n")
        result = run_agent(user_input, conversation)
        conversation = result["conversation"]

        print(f"Agent: {result['response']}\n")

        if result["tool_calls"]:
            print(f"  [Tools used: {', '.join(c['tool'] for c in result['tool_calls'])}]")

        print()


if __name__ == "__main__":
    main()
