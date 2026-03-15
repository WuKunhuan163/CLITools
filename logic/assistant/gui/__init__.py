"""Shared agent GUI infrastructure.

Contains the protocol-driven rendering engine, HTML template,
and the live agent server used by --agent, --ask, --plan
symmetric commands across all tools.

Files:
    engine.js      - Block rendering engine (browser-side)
    live.html      - Standard agent HTML template
    server.py      - AgentServer: HTTP + SSE server for agent sessions
    round_store.py - RoundStore: per-round token/file tracking
    key_manager.py - Tkinter key management GUI
"""
