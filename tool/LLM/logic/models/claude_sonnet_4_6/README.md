# Claude Sonnet 4.6

**Vendor:** Anthropic  
**Model Key:** `claude-sonnet-4.6`  
**API Model ID:** `claude-sonnet-4-6-20260101`  
**Directory:** `claude_sonnet_4_6`  
**Status:** Inactive — Paid model. Configure Anthropic API key to unlock.  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | True |
| System Prompt | True |
| Max Context Tokens | 200000 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** No
- **Input:** 3.0 USD/1M tokens
- **Output:** 15.0 USD/1M tokens

## Rate Limits

### tier1
- **rpm:** 50
- **tpm:** 40000
- **rpd:** 1000
- Tier 1: $5 credit purchase required

### tier2
- **rpm:** 1000
- **tpm:** 80000
- Tier 2: $40 cumulative spend

### tier3
- **rpm:** 2000
- **tpm:** 160000
- Tier 3: $200 cumulative spend

### tier4
- **rpm:** 4000
- **tpm:** 400000
- Tier 4: $400 cumulative spend

## Logo

- **Source:** [Anthropic Claude mark](https://lobehub.com/icons/claude)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `claude-sonnet-4.6` (canonical identifier)
- **Directory:** `claude_sonnet_4_6` = `model_key_to_dir("claude-sonnet-4.6")`
- **API ID:** `claude-sonnet-4-6-20260101` (what the vendor API expects)
