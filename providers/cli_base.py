"""Base class for CLI-based model providers."""

import asyncio
import logging
import time
from abc import abstractmethod

from .base import ModelProvider
from .shared import ModelResponse
from .shared.cli_output import CliError, CliNotFoundError, CliOutput, CliTimeoutError

logger = logging.getLogger(__name__)


class CliProvider(ModelProvider):
    """Abstract base class for model providers that execute CLI commands.

    This provider wraps subprocess execution with timeout protection, signal handling,
    and full response collection (no streaming).

    Subclasses must implement:
    - get_provider_type()
    - _build_args() to construct CLI arguments from request params
    - _parse_response() to convert CLI output to ModelResponse
    - generate_content() to orchestrate the flow
    """

    def __init__(self, cli_path: str = "gemini", timeout_s: int = 30, **kwargs):
        """Initialize CLI provider.

        Args:
            cli_path: Path to the CLI binary (default: "gemini")
            timeout_s: Subprocess timeout in seconds (default: 30)
            **kwargs: Additional arguments passed to ModelProvider
        """
        # Extract api_key from kwargs or use a placeholder for CLI providers
        api_key = kwargs.pop("api_key", "cli-provider")
        super().__init__(api_key=api_key, **kwargs)

        self.cli_path = cli_path
        self.timeout_s = timeout_s

    async def _run_cli(self, args: list[str]) -> CliOutput:
        """Execute CLI command with subprocess and timeout protection.

        Collects full stdout/stderr and returns result or raises error.

        Args:
            args: List of command arguments (e.g., ["gemini", "generate", "--model", "..."])

        Returns:
            CliOutput with stdout, stderr, exit code, and duration

        Raises:
            CliTimeoutError: If command exceeds timeout
            CliNotFoundError: If CLI binary not found
            CliError: For other subprocess errors
        """
        if not args:
            raise CliError("No arguments provided to _run_cli")

        command_str = " ".join(str(arg) for arg in args)
        logger.debug(f"Executing CLI: {command_str}")

        start_time = time.time()

        try:
            # Execute subprocess asynchronously
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_s,
                )
            except TimeoutError:
                # Terminate process on timeout
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except TimeoutError:
                    # Force kill if termination hangs
                    logger.warning(f"CLI command did not terminate gracefully, killing: {command_str}")
                    process.kill()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2.0)
                    except TimeoutError:
                        logger.error(f"Failed to kill CLI process: {command_str}")

                duration_ms = (time.time() - start_time) * 1000
                raise CliTimeoutError(
                    f"CLI command exceeded {self.timeout_s}s timeout: {command_str}"
                ) from None

            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            duration_ms = (time.time() - start_time) * 1000

            # Log result
            if process.returncode == 0:
                logger.debug(f"CLI success ({duration_ms:.0f}ms): {command_str}")
            else:
                logger.warning(
                    f"CLI exit code {process.returncode} ({duration_ms:.0f}ms): {command_str}"
                )
                if stderr:
                    logger.debug(f"CLI stderr: {stderr[:200]}")

            return CliOutput(
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode,
                command=command_str,
                duration_ms=duration_ms,
            )

        except FileNotFoundError as e:
            duration_ms = (time.time() - start_time) * 1000
            raise CliNotFoundError(f"CLI binary not found: {args[0]}") from e
        except asyncio.CancelledError:
            # Cancellation must propagate so the caller (or asyncio.wait_for) can
            # complete its cancellation handshake. Suppressing it here led to
            # coroutines hanging after a tool timeout.
            raise
        except (CliTimeoutError, CliNotFoundError):
            # Re-raise our own exceptions unchanged
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            raise CliError(f"CLI execution failed: {e}") from e

    @abstractmethod
    def _parse_response(self, output: CliOutput) -> ModelResponse:
        """Parse CLI output into ModelResponse.

        Subclasses must implement to handle provider-specific response formats.

        Args:
            output: CliOutput from _run_cli

        Returns:
            ModelResponse with content, usage, metadata

        Raises:
            CliError: If parsing fails
        """

    @abstractmethod
    def _build_args(self, prompt: str, model: str, temperature: float, **kwargs) -> list[str]:
        """Build CLI arguments from request parameters.

        Subclasses must implement to map request params to CLI flags.

        Args:
            prompt: User prompt
            model: Model name
            temperature: Temperature parameter
            **kwargs: Additional parameters

        Returns:
            List of command arguments ready for subprocess.exec()
        """

    def classify_error(self, error: Exception) -> str:
        """Classify error type for fallback decisions.

        Categorizes CLI errors into types that determine whether to try
        the next provider in the fallback chain:
        - "not_found": CLI binary missing from PATH
        - "timeout": CLI command exceeded time limit
        - "invalid_output": CLI output invalid (JSON parse failure, etc.)
        - "unknown": Other CLI errors

        Args:
            error: Exception to classify

        Returns:
            Classification string: "not_found", "timeout", "invalid_output", or "unknown"
        """
        if isinstance(error, CliNotFoundError):
            return "not_found"
        elif isinstance(error, CliTimeoutError):
            return "timeout"
        elif isinstance(error, CliError) and "JSON" in str(error):
            return "invalid_output"
        else:
            return "unknown"

    def should_fallback(self, error: Exception) -> bool:
        """Determine if error warrants fallback to next provider.

        CLI errors typically indicate the provider is unavailable or failed
        in a way that a different provider might handle better. All CliError
        subclasses trigger fallback rather than retrying the same provider.

        Args:
            error: Exception from CLI execution

        Returns:
            True if fallback should be attempted, False if error is fatal
        """
        # All CLI errors should trigger fallback, not retry
        return isinstance(error, (CliError, CliTimeoutError, CliNotFoundError))

    def close(self) -> None:
        """Clean up resources (no-op for CLI providers)."""
        pass
