# Gemini 3.1 Flash-Lite (Preview)

**Vendor:** Google  
**Model Key:** `gemini-3.1-flash-lite`  
**API Model ID:** `gemini-3.1-flash-lite-preview`  
**Directory:** `gemini_3_1_flash_lite`  

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
- **Input:** 0.25 USD/1M tokens
- **Output:** 1.5 USD/1M tokens

## Rate Limits

### free
- **rpm:** 30
- **tpm:** 1000000
- **rpd:** 1500
- Free tier preview

### paid_tier1
- **rpm:** 4000
- **tpm:** 4000000
- **rpd:** 14400
- Paid Tier 1 preview

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-3.1-flash-lite` (canonical identifier)
- **Directory:** `gemini_3_1_flash_lite` = `model_key_to_dir("gemini-3.1-flash-lite")`
- **API ID:** `gemini-3.1-flash-lite-preview` (what the vendor API expects)
