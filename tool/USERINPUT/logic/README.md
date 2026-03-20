# USERINPUT Logic

Decomposed CLI for the USERINPUT feedback tool. Each subcommand has its own module with `cli.py` and `argparse.json`.

## Structure

```
logic/
├── cli.py               ← Root entry point: GUI feedback collection (no-args default)
├── argparse.json         ← Root command schema (for ---help)
├── __init__.py           ← Shared utilities: config, messages, exceptions
├── queue/
│   ├── cli.py            ← --queue subcommand: manage prompt queue
│   ├── store.py          ← Queue storage: FIFO read/write to queue.json
│   └── argparse.json     ← Queue command schema
├── prompt/
│   ├── cli.py            ← --system-prompt subcommand: manage system prompts
│   └── argparse.json     ← Prompt command schema
├── config/
│   ├── cli.py            ← --config subcommand + --enquiry-mode toggle
│   └── argparse.json     ← Config command schema
├── prompts.py            ← Default system prompt templates
├── config.json           ← Runtime configuration (focus_interval, etc.)
├── queue.json            ← Queue data (FIFO prompt storage)
└── translation/          ← i18n translations (zh.json, ar.json)
```

## Command Routing

`main.py` is a thin router. It creates the `UserInputTool` instance, detects the subcommand mode from argv, and dispatches:

| Flag | Module | Entry |
|------|--------|-------|
| (none) | `logic/cli.py` | `run_feedback(tool, args)` |
| `--queue` | `logic/queue/cli.py` | `run_queue(tool, args)` |
| `--system-prompt` | `logic/prompt/cli.py` | `run_prompt(tool, args)` |
| `--config` | `logic/config/cli.py` | `run_config(tool, args)` |
| `--enquiry-mode` | `logic/config/cli.py` | `run_enquiry_mode(tool, args)` |
| `---<eco>` | ToolBase eco dispatch | `tool.handle_command_line()` |
