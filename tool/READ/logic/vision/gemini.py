#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.api_core import exceptions
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_keys = {
            "USER": api_key,
            "FREE": os.getenv("GOOGLE_API_KEY_FREE"),
            "PAID": os.getenv("GOOGLE_API_KEY_PAID")
        }
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        prompt_path = Path(__file__).parent / "prompts.json"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"default": "Please describe the following image:"}

    def analyze_image(self, image_path: Path, mode: str = "general", custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze an image using Google Gemini Vision API.
        Returns a dict with success status and result/error message.
        """
        if not any(self.api_keys.values()):
            return {"success": False, "error": "API keys not set. Please set GOOGLE_API_KEY_FREE or GOOGLE_API_KEY_PAID."}

        if not image_path.exists():
            return {"success": False, "error": f"Image file not found: {image_path}"}

        try:
            img = Image.open(image_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to open image: {e}"}

        prompt_instruction = custom_prompt or self.prompts.get(mode, self.prompts.get("default"))
        
        failed_reasons = []
        for key_type, api_key in self.api_keys.items():
            if not api_key:
                continue
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                response = model.generate_content([prompt_instruction, img], stream=False)
                response.resolve()
                return {"success": True, "result": response.text, "key_type": key_type}
            except exceptions.PermissionDenied:
                failed_reasons.append(f"{key_type}: Permission denied (possibly regional restriction)")
            except exceptions.ResourceExhausted:
                failed_reasons.append(f"{key_type}: Quota exhausted")
            except Exception as e:
                failed_reasons.append(f"{key_type}: {str(e)}")
        
        return {"success": False, "error": "All API keys failed: " + "; ".join(failed_reasons)}

    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity for all configured keys."""
        results = {}
        for key_type, api_key in self.api_keys.items():
            if not api_key:
                continue
            try:
                genai.configure(api_key=api_key)
                models = list(genai.list_models())
                results[key_type] = {"success": True, "message": "Connection successful"}
            except Exception as e:
                results[key_type] = {"success": False, "message": str(e)}
        return results

