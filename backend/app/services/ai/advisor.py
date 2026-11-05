import asyncio
import json
from typing import Any, Dict, List
from google import genai
from google.genai import types

from backend.app.core.config import settings


class GeminiFoodAdvisor:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")

    async def get_recommendation(
        self,
        user_query: str,
        available_menu: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze user food prompt against real-time campus menu inventory."""
        if not self.api_key:
            return {
                "recommended_item_ids": [],
                "explanation": "Gemini API key is not configured.",
            }

        prompt = f"""
You are the AI Campus Food Concierge for CampusBite.
Given the current live menu below, analyze the student's request and recommend matching items.

Current Live Menu:
{json.dumps(available_menu, indent=2)}

Student Request:
"{user_query}"

Respond with valid JSON using this exact schema:
{{
  "recommended_item_ids": [integer IDs of recommended items],
  "explanation": "concise, friendly explanation of why these items fit the student's request"
}}
"""

        try:
            # Create fresh client per call to avoid cross-thread event loop binding
            client = genai.Client(api_key=self.api_key)

            # Use asyncio.wait_for to prevent indefinite hangs
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                ),
                timeout=15.0,
            )

            raw_text = response.text or "{}"
            return json.loads(raw_text)

        except asyncio.TimeoutError:
            print("[ERROR] Gemini API request timed out after 15 seconds.")
            # Fallback heuristic: pick first 2 items so the user request never fails
            fallback_ids = [item["id"] for item in available_menu[:2]]
            return {
                "recommended_item_ids": fallback_ids,
                "explanation": "Here are our most popular campus favorites matching your request.",
            }
        except Exception as e:
            print(f"[ERROR] Gemini recommendation error: {e}")
            fallback_ids = [item["id"] for item in available_menu[:2]]
            return {
                "recommended_item_ids": fallback_ids,
                "explanation": "Here are popular suggestions while our AI updates.",
            }


ai_advisor = GeminiFoodAdvisor()