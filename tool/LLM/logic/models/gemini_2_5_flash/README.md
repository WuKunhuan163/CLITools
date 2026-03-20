# Gemini 2.5 Flash

**Vendor:** Google  
**Model Key:** `gemini-2.5-flash`  
**Directory:** `gemini_2_5_flash`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | True |
| System Prompt | True |
| Max Context Tokens | 1048576 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** Yes
- **Input:** 0.3 USD/1M tokens
- **Output:** 2.5 USD/1M tokens

## Rate Limits

### free
- **rpm:** 10
- **tpm:** 250000
- **rpd:** 250
- Free tier: no billing required. Dec 2025 quota reduction.

### paid_tier1
- **rpm:** 2000
- **tpm:** 4000000
- **rpd:** 10000
- Paid Tier 1 with billing enabled

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-2.5-flash` (canonical identifier)
- **Directory:** `gemini_2_5_flash` = `model_key_to_dir("gemini-2.5-flash")`
