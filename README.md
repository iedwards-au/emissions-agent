# Scope3 Inventory Agent

An AI-powered agent for evaluating advertising inventory carbon emissions, built with Claude + Streamlit.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
SCOPE3_API_KEY=your-scope3-key
```

## Deploying to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. In **Advanced settings → Secrets**, add:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SCOPE3_API_KEY = "your-scope3-key"
```

4. Deploy — you'll get a public URL in ~2 minutes.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit web UI |
| `agent.py` | Agentic loop (Claude + tool calling) |
| `tools.py` | Tool definitions + Scope3 API calls |
| `prompts.py` | System prompt + prompt templates |
| `pdf_report.py` | Branded PDF report generator |
