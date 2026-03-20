# Gemini 2.5 Pro

**Vendor:** Google  
**Model Key:** `gemini-2.5-pro`  
**Directory:** `gemini_2_5_pro`  
**Status:** Inactive — Free tier quota very limited (5 RPM, 50 RPD). Persistent 429 errors. Enable billing for reliable access.  

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
- **Input:** 1.25 USD/1M tokens
- **Output:** 10.0 USD/1M tokens

## Rate Limits

### free
- **rpm:** 5
- **tpm:** 250000
- **rpd:** 25
- Free tier: very limited quota. Dec 2025 quota reduction.

### paid_tier1
- **rpm:** 1000
- **tpm:** 2000000
- **rpd:** 10000
- Paid Tier 1

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-2.5-pro` (canonical identifier)
- **Directory:** `gemini_2_5_pro` = `model_key_to_dir("gemini-2.5-pro")`
