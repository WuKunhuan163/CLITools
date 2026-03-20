# Gemini 3.1 Pro (Preview)

**Vendor:** Google  
**Model Key:** `gemini-3.1-pro`  
**API Model ID:** `gemini-3.1-pro-preview`  
**Directory:** `gemini_3_1_pro`  
**Status:** Inactive — Paid-only preview. No free tier available.  

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

- **Free tier:** No
- **Input:** 2.0 USD/1M tokens
- **Output:** 12.0 USD/1M tokens

## Rate Limits

### paid_tier1
- **rpm:** 1000
- **tpm:** 2000000
- **rpd:** 10000
- Paid only. Most advanced.

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-3.1-pro` (canonical identifier)
- **Directory:** `gemini_3_1_pro` = `model_key_to_dir("gemini-3.1-pro")`
- **API ID:** `gemini-3.1-pro-preview` (what the vendor API expects)
