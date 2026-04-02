from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI


class ProviderUnavailableError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, model: str, *, repo_root: Path, timeout_seconds: int) -> None:
        self.model = model
        self.repo_root = repo_root
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY")) or bool(shutil.which("codex"))

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        openai_error: Exception | None = None
        if os.getenv("OPENAI_API_KEY"):
            try:
                return self._complete_openai(system_prompt, user_prompt)
            except Exception as exc:  # pragma: no cover - network/auth failures
                openai_error = exc

        if shutil.which("codex"):
            try:
                return self._complete_codex(system_prompt, user_prompt)
            except Exception as exc:  # pragma: no cover - depends on local CLI state
                message = "Codex CLI fallback failed."
                if openai_error is not None:
                    message = f"OpenAI failed ({openai_error}). Codex CLI fallback failed ({exc})."
                raise ProviderUnavailableError(message) from exc

        if openai_error is not None:
            raise ProviderUnavailableError(
                f"OpenAI completion failed ({openai_error}) and Codex CLI is not available."
            ) from openai_error
        raise ProviderUnavailableError("OPENAI_API_KEY is not set and Codex CLI is not available.")

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> str:
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return response.output_text.strip()

    def _complete_codex(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"System instructions:\n{system_prompt}\n\nUser request:\n{user_prompt}\n"
        with tempfile.TemporaryDirectory(prefix="harness-codex-") as temp_dir:
            output_path = Path(temp_dir) / "last_message.txt"
            command = [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--color",
                "never",
                "-C",
                str(self.repo_root),
                "-s",
                "read-only",
                "-o",
                str(output_path),
                prompt,
            ]
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip() or "unknown Codex CLI error"
                raise ProviderUnavailableError(stderr)
            if not output_path.exists():
                raise ProviderUnavailableError(
                    "Codex CLI completed without writing an output message."
                )
            return output_path.read_text().strip()
