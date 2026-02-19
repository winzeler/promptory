"""PromptPex integration — auto-generate test cases from prompt body using LLMs."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# System prompt for the LLM that generates test cases
_TEST_GEN_SYSTEM = """You are a prompt testing expert. Given a prompt template, generate test cases that evaluate its quality.

For each test case, produce:
1. A set of input variables to fill the template
2. Assertions to validate the output quality

Output a JSON array of test cases in this format:
[
  {
    "description": "Brief description of what this test validates",
    "vars": {"variable_name": "value", ...},
    "assertions": [
      {"type": "contains", "value": "expected substring"},
      {"type": "llm-rubric", "value": "Quality criterion description", "threshold": 0.8}
    ]
  }
]

Generate 3-5 diverse test cases covering:
- Happy path with typical inputs
- Edge cases (empty inputs, long inputs, special characters)
- Quality checks (tone, relevance, completeness)

Only output valid JSON, no markdown fences or explanation."""


def generate_test_prompt(prompt_body: str, prompt_name: str | None = None) -> str:
    """Build the user message for the test generation LLM call."""
    context = f"Prompt name: {prompt_name}\n\n" if prompt_name else ""
    return f"""{context}Prompt template to test:
---
{prompt_body}
---

Generate test cases for this prompt template."""


def parse_generated_tests(llm_output: str) -> list[dict]:
    """Parse LLM output into structured test cases.

    Handles common LLM output quirks (markdown fences, extra text).
    """
    text = llm_output.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        tests = json.loads(text)
        if isinstance(tests, list):
            return _validate_tests(tests)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            tests = json.loads(text[start : end + 1])
            if isinstance(tests, list):
                return _validate_tests(tests)
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse LLM test generation output")
    return []


def _validate_tests(tests: list) -> list[dict]:
    """Validate and normalize test case structure."""
    valid = []
    for test in tests:
        if not isinstance(test, dict):
            continue
        normalized = {
            "description": test.get("description", "Test case"),
            "vars": test.get("vars", {}),
            "assertions": [],
        }
        for assertion in test.get("assertions", []):
            if isinstance(assertion, dict) and "type" in assertion and "value" in assertion:
                a = {"type": assertion["type"], "value": assertion["value"]}
                if "threshold" in assertion:
                    a["threshold"] = assertion["threshold"]
                normalized["assertions"].append(a)
        valid.append(normalized)
    return valid


def tests_to_eval_config(tests: list[dict]) -> dict:
    """Convert generated test cases to promptfoo eval config format."""
    test_cases = []
    for test in tests:
        case: dict = {}
        if test.get("vars"):
            case["vars"] = test["vars"]
        if test.get("assertions"):
            case["assert"] = test["assertions"]
        if test.get("description"):
            case["description"] = test["description"]
        if case:
            test_cases.append(case)
    return {"tests": test_cases}


async def generate_tests_with_llm(
    prompt_body: str,
    prompt_name: str | None = None,
    model: str = "gemini-2.0-flash",
) -> list[dict]:
    """Generate test cases using an LLM.

    Uses Google Generative AI if available, otherwise returns a helpful error.
    This is the main entry point for the PromptPex integration.
    """
    user_message = generate_test_prompt(prompt_body, prompt_name)

    try:
        import google.generativeai as genai

        gen_model = genai.GenerativeModel(model)
        response = gen_model.generate_content(
            [
                {"role": "user", "parts": [_TEST_GEN_SYSTEM + "\n\n" + user_message]},
            ]
        )
        return parse_generated_tests(response.text)
    except ImportError:
        logger.info("google-generativeai not installed, using fallback test generation")
    except Exception as e:
        logger.warning("LLM test generation failed: %s", e)

    # Fallback: generate basic test cases from template analysis
    return _generate_fallback_tests(prompt_body)


def _generate_fallback_tests(prompt_body: str) -> list[dict]:
    """Generate basic test cases by analyzing the template for variables."""
    import re

    # Extract Jinja2 variables
    variables = set(re.findall(r"\{\{\s*(\w+)\s*(?:\|[^}]*)?\}\}", prompt_body))

    if not variables:
        return [
            {
                "description": "Basic output check",
                "vars": {},
                "assertions": [
                    {"type": "llm-rubric", "value": "Output should be coherent and relevant", "threshold": 0.7}
                ],
            }
        ]

    # Generate test cases with sample values
    sample_vars = {v: f"test_{v}" for v in variables}
    return [
        {
            "description": "Happy path with sample variables",
            "vars": sample_vars,
            "assertions": [
                {"type": "contains", "value": next(iter(sample_vars.values()))},
                {"type": "llm-rubric", "value": "Output should be coherent and relevant", "threshold": 0.7},
            ],
        },
        {
            "description": "Empty variables",
            "vars": {v: "" for v in variables},
            "assertions": [
                {"type": "llm-rubric", "value": "Output should handle empty inputs gracefully", "threshold": 0.5},
            ],
        },
    ]
