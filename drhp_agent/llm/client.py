"""LLM client with Anthropic Claude API support.

Tasks 3.1-3.5: LLM provider abstraction, API integration, retry logic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    api_key: str | None = None
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.0
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 120.0

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key to LLMConfig."
            )


class LLMClient:
    """Client for interacting with LLM APIs."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.client = anthropic.Anthropic(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a completion request to the LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The LLM response text

        Raises:
            anthropic.APIError: On API errors after retries exhausted
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        prompt_len = len(system_prompt) + len(user_prompt)
        logger.debug("LLM request: model=%s prompt_len=%d temperature=%s", self.config.model, prompt_len, temp)

        last_error = None
        for attempt in range(self.config.max_retries):
            t0 = time.time()
            try:
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=tokens,
                    temperature=temp,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                elapsed = time.time() - t0
                result_text = response.content[0].text
                logger.debug("LLM response: len=%d time=%.1fs", len(result_text), elapsed)
                return result_text

            except anthropic.RateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2**attempt)
                    logger.warning("Rate limited, retrying in %.1fs (attempt %d/%d)",
                                   delay, attempt + 1, self.config.max_retries)
                    time.sleep(delay)
                continue

            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    last_error = e
                    if attempt < self.config.max_retries - 1:
                        delay = self.config.retry_delay * (2**attempt)
                        logger.warning("API error %d, retrying in %.1fs (attempt %d/%d)",
                                       e.status_code, delay, attempt + 1, self.config.max_retries)
                        time.sleep(delay)
                    continue
                logger.error("API error: %s", e)
                raise

        logger.error("All %d retries exhausted: %s", self.config.max_retries, last_error)
        raise last_error  # type: ignore

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a completion request and parse JSON response.

        Args:
            system_prompt: System instructions (should request JSON output)
            user_prompt: User message
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Parsed JSON as dict

        Raises:
            ValueError: If response is not valid JSON
        """
        response_text = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return self._parse_json(response_text)

    def _parse_json(self, text: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling common formats.

        Handles:
        - Raw JSON
        - JSON wrapped in ```json ... ``` code blocks
        - JSON wrapped in ``` ... ``` code blocks
        """
        text = text.strip()

        # Try to extract JSON from code blocks
        json_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        matches = re.findall(json_block_pattern, text)
        if matches:
            text = matches[0].strip()

        # Try to parse
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from LLM response: {e}")

    def extract_facts(self, document_content: str, filename: str) -> dict[str, Any]:
        """Extract facts from a document using the extraction prompt.

        Args:
            document_content: Full text content of the document
            filename: Name of the file being processed

        Returns:
            Extracted facts in FACT_SCHEMA format
        """
        from drhp_agent.prompts import (
            EXTRACTION_SYSTEM_PROMPT,
            EXTRACTION_USER_PROMPT,
            FACT_SCHEMA,
        )

        system = EXTRACTION_SYSTEM_PROMPT.format(schema=FACT_SCHEMA)
        user = EXTRACTION_USER_PROMPT.format(
            filename=filename,
            content=document_content,
        )

        return self.complete_json(system, user, max_tokens=8192)

    def fill_slot(
        self,
        slot_id: str,
        slot_type: str,
        slot_hint: str | None,
        slot_context: str | None,
        facts_json: str,
    ) -> dict[str, Any]:
        """Fill a template slot using extracted facts.

        Args:
            slot_id: ID of the slot to fill
            slot_type: Type of value expected (amount, date, text, etc.)
            slot_hint: Hint about what the slot represents
            slot_context: Surrounding template text
            facts_json: JSON string of available facts

        Returns:
            Slot fill result in SlotFillResult format
        """
        from drhp_agent.prompts import (
            SLOT_FILL_SYSTEM_PROMPT,
            SLOT_FILL_USER_PROMPT,
        )

        user = SLOT_FILL_USER_PROMPT.format(
            slot_id=slot_id,
            slot_type=slot_type,
            slot_hint=slot_hint or "No hint provided",
            slot_context=slot_context or "No context provided",
            facts_json=facts_json,
        )

        return self.complete_json(SLOT_FILL_SYSTEM_PROMPT, user)

    def validate_facts(self, facts_json: str) -> dict[str, Any]:
        """Validate extracted facts for consistency.

        Args:
            facts_json: JSON string of all extracted facts

        Returns:
            Validation result with issues list
        """
        from drhp_agent.prompts import (
            VALIDATION_SYSTEM_PROMPT,
            VALIDATION_USER_PROMPT,
        )

        user = VALIDATION_USER_PROMPT.format(facts_json=facts_json)
        return self.complete_json(VALIDATION_SYSTEM_PROMPT, user)

    def generate_section(
        self,
        company_name: str,
        filled_slots_json: str,
        source_files: list[str],
    ) -> str:
        """Generate a DRHP section from filled slots.

        Args:
            company_name: Name of the company
            filled_slots_json: JSON string of filled slots
            source_files: List of source document names

        Returns:
            Generated section markdown
        """
        from drhp_agent.prompts import (
            SECTION_GENERATE_SYSTEM_PROMPT,
            SECTION_GENERATE_USER_PROMPT,
        )

        user = SECTION_GENERATE_USER_PROMPT.format(
            company_name=company_name,
            filled_slots_json=filled_slots_json,
            source_files=", ".join(source_files),
        )

        return self.complete(SECTION_GENERATE_SYSTEM_PROMPT, user, max_tokens=8192)

    def elaborate_section(
        self,
        block_id: str,
        hint: str,
        template_context: str,
        facts_json: str,
    ) -> dict[str, Any]:
        """Generate elaborate prose for a template block.

        All facts are passed to the LLM which does semantic matching
        based on the hint to generate relevant content.

        Args:
            block_id: ID of the elaboration block
            hint: Instructions for what to elaborate on
            template_context: Surrounding template text for tone matching
            facts_json: JSON string of all facts

        Returns:
            Elaboration result with generated markdown and sources
        """
        from drhp_agent.prompts import (
            ELABORATION_SYSTEM_PROMPT,
            ELABORATION_USER_PROMPT,
        )

        user = ELABORATION_USER_PROMPT.format(
            block_id=block_id,
            hint=hint or "Generate detailed content",
            template_context=template_context or "No context provided",
            facts_json=facts_json,
        )

        return self.complete_json(ELABORATION_SYSTEM_PROMPT, user, max_tokens=8192)
