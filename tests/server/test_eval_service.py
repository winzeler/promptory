"""Tests for the eval service (promptfoo config generation and run execution)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from server.db.queries import eval_runs as eval_queries
from server.services.eval_service import generate_promptfoo_config, run_evaluation

from tests.conftest import PROMPT_ID


# ---------------------------------------------------------------------------
# generate_promptfoo_config tests
# ---------------------------------------------------------------------------


class TestGeneratePromptfooConfig:
    def test_basic_config(self):
        config = generate_promptfoo_config("Hello {{ name }}", ["gemini-2.0-flash"])
        assert config["prompts"] == ["Hello {{ name }}"]
        assert config["providers"] == ["google:gemini-2.0-flash"]
        assert "tests" not in config

    def test_multiple_providers(self):
        config = generate_promptfoo_config(
            "Hello", ["gemini-2.0-flash", "gpt-4o", "claude-sonnet-4-5-20250929"]
        )
        assert "google:gemini-2.0-flash" in config["providers"]
        assert "openai:gpt-4o" in config["providers"]
        assert "anthropic:claude-sonnet-4-5-20250929" in config["providers"]

    def test_unknown_provider_passthrough(self):
        config = generate_promptfoo_config("Hello", ["custom-model-v1"])
        assert config["providers"] == ["custom-model-v1"]

    def test_with_variables(self):
        config = generate_promptfoo_config(
            "Hello {{ name }}", ["gemini-2.0-flash"],
            variables={"name": "Alice"},
        )
        assert "tests" in config
        assert config["tests"][0]["vars"] == {"name": "Alice"}

    def test_with_assertions(self):
        eval_config = {
            "assertions": [
                {"type": "contains", "value": "hello"},
                {"type": "llm-rubric", "value": "Is polite", "threshold": 0.8},
            ]
        }
        config = generate_promptfoo_config(
            "Hello", ["gemini-2.0-flash"],
            eval_config=eval_config,
        )
        assert "tests" in config
        asserts = config["tests"][0]["assert"]
        assert len(asserts) == 2
        assert asserts[0] == {"type": "contains", "value": "hello"}
        assert asserts[1] == {"type": "llm-rubric", "value": "Is polite", "threshold": 0.8}

    def test_with_variables_and_assertions(self):
        config = generate_promptfoo_config(
            "Hello {{ name }}", ["gemini-2.0-flash"],
            eval_config={"assertions": [{"type": "contains", "value": "greeting"}]},
            variables={"name": "Bob"},
        )
        test_case = config["tests"][0]
        assert "vars" in test_case
        assert "assert" in test_case

    def test_no_eval_config(self):
        config = generate_promptfoo_config("Hello", ["gemini-2.0-flash"], eval_config=None)
        assert "tests" not in config

    def test_google_provider_variants(self):
        for model in ["gemini-2.0-flash", "google-model", "Gemini-Pro"]:
            config = generate_promptfoo_config("test", [model])
            assert config["providers"][0].startswith("google:")

    def test_openai_provider_variants(self):
        for model in ["gpt-4o", "openai-custom", "GPT-3.5-turbo"]:
            config = generate_promptfoo_config("test", [model])
            assert config["providers"][0].startswith("openai:")

    def test_anthropic_provider_variants(self):
        for model in ["claude-sonnet-4-5-20250929", "anthropic-model", "Claude-3-haiku"]:
            config = generate_promptfoo_config("test", [model])
            assert config["providers"][0].startswith("anthropic:")


# ---------------------------------------------------------------------------
# run_evaluation tests
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    @pytest.mark.asyncio
    async def test_promptfoo_not_installed(self, db):
        """When promptfoo is not found, the run should be marked failed."""
        run_id = await eval_queries.create_eval_run(
            db, PROMPT_ID, prompt_version="1.0",
            provider="promptfoo", model="gemini-2.0-flash", triggered_by="test",
        )

        with patch("server.services.eval_service.shutil.which", return_value=None):
            result = await run_evaluation(db, run_id, "Hello", "gemini-2.0-flash")

        assert result["status"] == "failed"
        assert "not found" in result["error"]

        # Verify DB was updated
        run = await eval_queries.get_eval_run(db, run_id)
        assert run["status"] == "failed"
        assert "not found" in run["error_message"]

    @pytest.mark.asyncio
    async def test_successful_run(self, db):
        """Mock a successful promptfoo execution."""
        run_id = await eval_queries.create_eval_run(
            db, PROMPT_ID, prompt_version="1.0",
            provider="promptfoo", model="gemini-2.0-flash", triggered_by="test",
        )

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"OK", b"")
        mock_proc.returncode = 0

        with patch("server.services.eval_service.shutil.which", return_value="/usr/bin/promptfoo"), \
             patch("server.services.eval_service.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("server.services.eval_service.asyncio.wait_for", return_value=(b"OK", b"")), \
             patch("server.services.eval_service.Path") as mock_path_cls:
            # Mock the temp directory paths
            mock_config_path = mock_path_cls.return_value.__truediv__.return_value
            mock_output_path = mock_path_cls.return_value.__truediv__.return_value
            mock_output_path.exists.return_value = True
            mock_output_path.read_text.return_value = '{"results": [{"score": 1.0}]}'

            result = await run_evaluation(db, run_id, "Hello", "gemini-2.0-flash")

        assert result["status"] == "completed"
        assert "duration_ms" in result

        run = await eval_queries.get_eval_run(db, run_id)
        assert run["status"] == "completed"

    @pytest.mark.asyncio
    async def test_eval_run_lifecycle(self, db):
        """Test the full CRUD lifecycle for eval runs."""
        # Create
        run_id = await eval_queries.create_eval_run(
            db, PROMPT_ID, prompt_version="1.0",
            provider="promptfoo", model="gemini-2.0-flash", triggered_by="test",
        )
        run = await eval_queries.get_eval_run(db, run_id)
        assert run is not None
        assert run["status"] == "pending"

        # Update
        await eval_queries.update_eval_run(
            db, run_id, status="completed",
            results='{"score": 0.95}',
            duration_ms=1500,
            cost_usd=0.002,
        )
        run = await eval_queries.get_eval_run(db, run_id)
        assert run["status"] == "completed"
        assert run["duration_ms"] == 1500

        # List
        runs = await eval_queries.list_eval_runs(db, PROMPT_ID)
        assert len(runs) >= 1
        assert any(r["id"] == run_id for r in runs)

        # Delete
        await eval_queries.delete_eval_run(db, run_id)
        run = await eval_queries.get_eval_run(db, run_id)
        assert run is None
