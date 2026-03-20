# GLM-4.7-Flash

**Vendor:** Zhipu AI  
**Model Key:** `glm-4.7-flash`  
**Directory:** `glm_4_7_flash`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | True |
| Max Context Tokens | 128000 |
| Max Output Tokens | 8192 |

## Cost

- **Free tier:** Yes

## Rate Limits

### free
- **rpm:** 10
- **tpm:** 100000
- **max_concurrency:** 1
- **context_threshold_tokens:** 8000
- **over_threshold_concurrency_pct:** 1
- Free reasoning model: stricter RPM, concurrency=1

### paid
- **rpm:** 100
- **tpm:** 5000000
- **max_concurrency:** 50
- **context_threshold_tokens:** None
- **over_threshold_concurrency_pct:** None
- Paid tier standard

## Logo

- **Source:** [Zhipu AI / ChatGLM icon](https://lobehub.com/icons/zhipu)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `glm-4.7-flash` (canonical identifier)
- **Directory:** `glm_4_7_flash` = `model_key_to_dir("glm-4.7-flash")`
