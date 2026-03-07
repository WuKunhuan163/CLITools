# USERINPUT Logic — Technical Reference

## queue.py

Queue file: `tool/USERINPUT/logic/queue.json`
Format: `{"prompts": ["prompt1", "prompt2", ...]}`

Functions:
- Read queued prompts
- Add prompts to queue
- Pop next prompt (FIFO)

No system prompts or feedback directives are stored — only plain text user prompts.

## Gotchas

1. **queue.json location**: In `logic/` directory (code), not `data/`. This is intentional as the queue is transient.
2. **Blocking command**: USERINPUT itself is blocking. Do not background it.
