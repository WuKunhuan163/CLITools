# DeepSeek V3.2 Chat

**Vendor:** DeepSeek  
**Model Key:** `deepseek-chat`  
**Directory:** `deepseek_chat`  
**Status:** Inactive — Paid model. Configure DeepSeek API key to unlock.  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | False |
| System Prompt | True |
| Max Context Tokens | 128000 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** No
- **Input:** 0.28 USD/1M tokens
- **Output:** 0.42 USD/1M tokens

## Rate Limits

### default
- **rpm:** 60
- **tpm:** 500000
- Prepaid balance required. Rates vary by account level.

## Logo

- **Source:** [DeepSeek brand icon](https://lobehub.com/icons/deepseek)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `deepseek-chat` (canonical identifier)
- **Directory:** `deepseek_chat` = `model_key_to_dir("deepseek-chat")`
