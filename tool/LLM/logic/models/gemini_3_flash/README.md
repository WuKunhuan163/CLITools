# Gemini 3 Flash (Preview)

**Vendor:** Google  
**Model Key:** `gemini-3-flash`  
**API Model ID:** `gemini-3-flash-preview`  
**Directory:** `gemini_3_flash`  

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
- **Input:** 0.5 USD/1M tokens
- **Output:** 3.0 USD/1M tokens

## Rate Limits

### free
- **rpm:** 10
- **tpm:** 500000
- **rpd:** 1500
- Free tier preview

### paid_tier1
- **rpm:** 2000
- **tpm:** 4000000
- **rpd:** 10000
- Paid Tier 1 preview

## Logo

- **Source:** [Google Gemini sparkle icon](https://lobehub.com/icons/gemini)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `gemini-3-flash` (canonical identifier)
- **Directory:** `gemini_3_flash` = `model_key_to_dir("gemini-3-flash")`
- **API ID:** `gemini-3-flash-preview` (what the vendor API expects)
