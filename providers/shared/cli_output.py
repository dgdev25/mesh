"""CLI subprocess output parsing and validation."""

import json
import logging
from dataclasses import dataclass
from typing import Any

__all__ = ["CliOutput", "CliResponseParser", "CliError"]

logger = logging.getLogger(__name__)


class CliError(Exception):
    """Base exception for CLI-related errors."""

    pass


class CliTimeoutError(CliError):
    """Raised when CLI command exceeds timeout."""

    pass


class CliNotFoundError(CliError):
    """Raised when CLI binary is not found."""

    pass


@dataclass
class CliOutput:
    """Standardized representation of subprocess output.

    Attributes:
        stdout: Standard output from the subprocess
        stderr: Standard error output from the subprocess
        exit_code: Process exit code (0 = success)
        command: Full command invoked (for logging)
        duration_ms: Execution time in milliseconds
    """

    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: float

    @property
    def success(self) -> bool:
        """Return True if subprocess exited with code 0."""
        return self.exit_code == 0

    @property
    def raw_output(self) -> str:
        """Return stdout if available, otherwise stderr."""
        return self.stdout if self.stdout else self.stderr

    def __str__(self) -> str:
        """Return human-readable representation."""
        status = "success" if self.success else f"exit_code={self.exit_code}"
        return f"CliOutput({status}, duration_ms={self.duration_ms})"


class CliResponseParser:
    """Parser for CLI subprocess output in various formats.

    Supports JSON parsing, text extraction, and validation of CLI output.
    """

    @staticmethod
    def parse_json(output: str) -> dict[str, Any]:
        """Parse JSON from CLI output.

        Args:
            output: Raw output string expected to contain JSON

        Returns:
            Parsed JSON object

        Raises:
            CliError: If output is not valid JSON
        """
        if not output or not output.strip():
            raise CliError("Empty output cannot be parsed as JSON")

        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise CliError(f"Invalid JSON in CLI output: {e}") from e

    @staticmethod
    def parse_text(output: str) -> str:
        """Extract text from CLI output.

        Strips leading/trailing whitespace and returns the text.

        Args:
            output: Raw output string

        Returns:
            Trimmed text output

        Raises:
            CliError: If output is empty
        """
        if not output or not output.strip():
            raise CliError("Empty output cannot be parsed as text")

        return output.strip()

    @staticmethod
    def validate_output(output: CliOutput, expected_format: str = "json") -> bool:
        """Validate CLI output structure.

        Args:
            output: CliOutput object to validate
            expected_format: Expected format ("json" or "text")

        Returns:
            True if output is valid for the expected format

        Raises:
            CliError: If validation fails
        """
        if not output:
            raise CliError("CliOutput is None")

        if not isinstance(output, CliOutput):
            raise CliError(f"Expected CliOutput, got {type(output).__name__}")

        if expected_format == "json":
            if not output.stdout and not output.stderr:
                raise CliError("No output available for JSON parsing")

            # Try to parse the output as JSON to validate
            try:
                CliResponseParser.parse_json(output.raw_output)
            except CliError as e:
                raise CliError(f"Output is not valid JSON: {e}") from e

        elif expected_format == "text":
            if not output.stdout and not output.stderr:
                raise CliError("No output available for text parsing")

            # Text output just needs to be non-empty
            try:
                CliResponseParser.parse_text(output.raw_output)
            except CliError as e:
                raise CliError(f"Output is empty: {e}") from e

        else:
            raise CliError(f"Unknown output format: {expected_format}")

        return True

    @staticmethod
    def extract_json_field(
        output: CliOutput,
        field_name: str,
        default: Any = None,
    ) -> Any:
        """Extract a specific field from JSON output.

        Args:
            output: CliOutput with JSON content
            field_name: Name of the field to extract
            default: Default value if field is missing (if provided, missing fields return default)

        Returns:
            Field value or default if not found and default was provided

        Raises:
            CliError: If output is not valid JSON or field is missing and no default provided
        """
        try:
            data = CliResponseParser.parse_json(output.raw_output)
            if field_name not in data:
                if default is None:
                    raise CliError(f"Required field '{field_name}' not found in JSON output")
                logger.warning(f"Field '{field_name}' not found in JSON, using default")
                return default
            return data[field_name]
        except CliError as e:
            if default is not None:
                logger.warning(f"Failed to extract field '{field_name}': {e}, using default")
                return default
            raise
