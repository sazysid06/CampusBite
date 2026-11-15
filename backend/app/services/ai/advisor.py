import asyncio
import json
import logging
from typing import Any, Dict, List

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from backend.app.core.config import settings


logger = logging.getLogger(__name__)
_REQUEST_TIMEOUT_SECONDS = 15.0
_UNAVAILABLE_EXPLANATION = (
    "AI recommendations are temporarily unavailable. Please try again later."
)


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
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )

            raw_text = response.text or "{}"
            result = json.loads(raw_text)
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("recommended_item_ids"), list)
                or any(
                    type(item_id) is not int
                    for item_id in result["recommended_item_ids"]
                )
                or not isinstance(result.get("explanation"), str)
                or not result["explanation"].strip()
            ):
                raise ValueError("Gemini returned a response with an invalid schema.")
            return result

        except asyncio.TimeoutError:
            logger.warning(
                "Gemini recommendation request timed out after %.1f seconds.",
                _REQUEST_TIMEOUT_SECONDS,
            )
            return {
                "recommended_item_ids": [],
                "explanation": _UNAVAILABLE_EXPLANATION,
            }
        except (genai_errors.APIError, httpx.RequestError) as error:
            logger.warning("Gemini recommendation request failed: %s", error)
            return {
                "recommended_item_ids": [],
                "explanation": _UNAVAILABLE_EXPLANATION,
            }
        except (ValueError, TypeError) as error:
            logger.warning(
                "Gemini returned an invalid recommendation response: %s",
                error,
            )
            return {
                "recommended_item_ids": [],
                "explanation": _UNAVAILABLE_EXPLANATION,
            }


ai_advisor = GeminiFoodAdvisor()