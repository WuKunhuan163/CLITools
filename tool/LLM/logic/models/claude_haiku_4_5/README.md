# Claude Haiku 4.5

**Vendor:** Anthropic  
**Model Key:** `claude-haiku-4.5`  
**API Model ID:** `claude-haiku-4-5-20260101`  
**Directory:** `claude_haiku_4_5`  
**Status:** Inactive — Paid model. Configure Anthropic API key to unlock.  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | False |
| System Prompt | True |
| Max Context Tokens | 200000 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** No
- **Input:** 1.0 USD/1M tokens
- **Output:** 5.0 USD/1M tokens

## Rate Limits

### tier1
- **rpm:** 50
- **tpm:** 50000
- **rpd:** 1000
- Tier 1: $5 credit purchase required

### tier2
- **rpm:** 1000
- **tpm:** 100000
- Tier 2: $40 cumulative spend

## Logo

- **Source:** [Anthropic Claude mark](https://lobehub.com/icons/claude)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `claude-haiku-4.5` (canonical identifier)
- **Directory:** `claude_haiku_4_5` = `model_key_to_dir("claude-haiku-4.5")`
- **API ID:** `claude-haiku-4-5-20260101` (what the vendor API expects)
