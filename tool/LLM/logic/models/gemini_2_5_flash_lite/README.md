# Gemini 2.5 Flash-Lite

**Vendor:** Google  
**Model Key:** `gemini-2.5-flash-lite`  
**Directory:** `gemini_2_5_flash_lite`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | False |
| System Prompt | True |
| Max Context Tokens | 1048576 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** Yes
- **Input:** 0.1 USD/1M tokens
- **Output:** 0.4 USD/1M tokens

## Rate Limits

### free
- **rpm:** 30
- **tpm:** 1000000
- **rpd:** 1500
- Free tier: no billing required

### paid_tier1
- **rpm:** 4000
- **tpm:** 4000000
- **rpd:** 14400
- Paid Tier 1

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-2.5-flash-lite` (canonical identifier)
- **Directory:** `gemini_2_5_flash_lite` = `model_key_to_dir("gemini-2.5-flash-lite")`
