"""
API Key Management and Authentication for Cost Estimator Agent.

Handles intelligent API key detection, user prompting, and mode selection
for optimal user experience.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from enum import Enum

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .config import get_config

console = Console()


class OperationMode(str, Enum):
    """Available operation modes for the cost estimator."""
    FULL = "full"           # All API keys available
    PARTIAL = "partial"     # Some API keys available
    MOCK = "mock"          # No API keys, using mock data
    INTERACTIVE = "interactive"  # Ask user for keys


class APIKeyStatus:
    """Manages API key status and user interaction."""

    def __init__(self):
        self.config = get_config()
        self._detected_keys = self._detect_available_keys()
        self._operation_mode = self._determine_operation_mode()

    def _detect_available_keys(self) -> Dict[str, bool]:
        """Detect which API keys are available."""
        return {
            "openai": bool(self.config.llm.openai_api_key),
            "anthropic": bool(self.config.llm.anthropic_api_key),
            "azure_openai": bool(self.config.llm.azure_openai_api_key),
            "aws": bool(self.config.cloud.aws_access_key_id),
            "azure": bool(self.config.cloud.azure_subscription_id),
            "gcp": bool(self.config.cloud.gcp_project_id),
        }

    def _determine_operation_mode(self) -> OperationMode:
        """Determine the appropriate operation mode."""
        llm_keys = ["openai", "anthropic", "azure_openai"]
        available_llm_keys = [k for k in llm_keys if self._detected_keys[k]]

        if len(available_llm_keys) >= 2:
            return OperationMode.FULL
        elif len(available_llm_keys) >= 1:
            return OperationMode.PARTIAL
        else:
            return OperationMode.MOCK

    @property
    def operation_mode(self) -> OperationMode:
        """Get the current operation mode."""
        return self._operation_mode

    @property
    def has_llm_keys(self) -> bool:
        """Check if any LLM API keys are available."""
        llm_keys = ["openai", "anthropic", "azure_openai"]
        return any(self._detected_keys[k] for k in llm_keys)

    def get_missing_keys(self) -> List[str]:
        """Get list of missing API keys."""
        return [key for key, available in self._detected_keys.items() if not available]

    def get_available_keys(self) -> List[str]:
        """Get list of available API keys."""
        return [key for key, available in self._detected_keys.items() if available]

    def display_status(self, show_recommendations: bool = True) -> None:
        """Display current API key status to user."""

        # Create status table
        table = Table(title="🔑 API Key Status", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        table.add_column("Impact", style="dim")

        key_info = {
            "openai": ("OpenAI", "LLM operations, intelligent analysis"),
            "anthropic": ("Anthropic", "LLM operations, intelligent analysis"),
            "azure_openai": ("Azure OpenAI", "LLM operations, intelligent analysis"),
            "aws": ("AWS", "Live infrastructure pricing"),
            "azure": ("Azure", "Live infrastructure pricing"),
            "gcp": ("Google Cloud", "Live infrastructure pricing"),
        }

        for key, (provider, impact) in key_info.items():
            if self._detected_keys[key]:
                status = "✅ Available"
                style = "green"
            else:
                status = "❌ Missing"
                style = "red"

            table.add_row(provider, f"[{style}]{status}[/{style}]", impact)

        console.print(table)
        console.print()

        # Show operation mode
        mode_info = {
            OperationMode.FULL: ("🚀 Full Mode", "green", "All features available with live data"),
            OperationMode.PARTIAL: ("⚡ Partial Mode", "yellow", "Core features with some limitations"),
            OperationMode.MOCK: ("🧪 Mock Mode", "blue", "Basic functionality with simulated data"),
        }

        mode_name, color, description = mode_info[self._operation_mode]
        console.print(Panel(
            f"[bold {color}]{mode_name}[/bold {color}]\n{description}",
            title="Current Operation Mode"
        ))
        console.print()

        if show_recommendations and self._operation_mode != OperationMode.FULL:
            self._show_recommendations()

    def _show_recommendations(self) -> None:
        """Show recommendations for improving functionality."""
        missing = self.get_missing_keys()

        if not self.has_llm_keys:
            console.print("💡 [bold yellow]Recommendation[/bold yellow]: Add at least one LLM API key for intelligent analysis:")
            console.print("   • OpenAI: Set OPENAI_API_KEY environment variable")
            console.print("   • Anthropic: Set ANTHROPIC_API_KEY environment variable")
            console.print("   • Azure OpenAI: Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
            console.print()

        cloud_keys = [k for k in missing if k in ["aws", "azure", "gcp"]]
        if cloud_keys:
            console.print("💡 [bold blue]Optional[/bold blue]: Add cloud provider keys for live pricing:")
            for key in cloud_keys:
                if key == "aws":
                    console.print("   • AWS: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
                elif key == "azure":
                    console.print("   • Azure: Set AZURE_SUBSCRIPTION_ID and related credentials")
                elif key == "gcp":
                    console.print("   • GCP: Set GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT_ID")
            console.print()

    def prompt_for_keys(self, interactive: bool = True) -> bool:
        """Prompt user to provide missing API keys."""
        if not interactive:
            return False

        console.print("🔧 [bold]API Key Setup[/bold]")
        console.print()

        # Check if user wants to provide keys
        if self._operation_mode == OperationMode.MOCK:
            msg = "No LLM API keys detected. Would you like to provide them for full functionality?"
        else:
            msg = "Some API keys are missing. Would you like to provide additional keys?"

        if not Confirm.ask(msg):
            console.print("Continuing in current mode...")
            return False

        # Prompt for missing LLM keys first (most important)
        self._prompt_for_llm_keys()

        # Optionally prompt for cloud provider keys
        if Confirm.ask("Would you like to add cloud provider keys for live pricing?", default=False):
            self._prompt_for_cloud_keys()

        # Update status
        self._detected_keys = self._detect_available_keys()
        self._operation_mode = self._determine_operation_mode()

        console.print("✅ API key setup complete!")
        console.print()
        self.display_status(show_recommendations=False)

        return True

    def _prompt_for_llm_keys(self) -> None:
        """Prompt for LLM API keys."""
        console.print("🤖 [bold]LLM Provider Setup[/bold]")

        if not self._detected_keys["openai"]:
            openai_key = Prompt.ask("OpenAI API Key (or press Enter to skip)", default="", show_default=False)
            if openai_key.strip():
                os.environ["OPENAI_API_KEY"] = openai_key.strip()
                console.print("✅ OpenAI API key set")

        if not self._detected_keys["anthropic"]:
            anthropic_key = Prompt.ask("Anthropic API Key (or press Enter to skip)", default="", show_default=False)
            if anthropic_key.strip():
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key.strip()
                console.print("✅ Anthropic API key set")

        console.print()

    def _prompt_for_cloud_keys(self) -> None:
        """Prompt for cloud provider keys."""
        console.print("☁️  [bold]Cloud Provider Setup[/bold]")
        console.print("Note: These are optional for live pricing data")

        if not self._detected_keys["aws"]:
            if Confirm.ask("Configure AWS credentials?", default=False):
                aws_key = Prompt.ask("AWS Access Key ID", default="", show_default=False)
                aws_secret = Prompt.ask("AWS Secret Access Key", default="", show_default=False, password=True)
                if aws_key.strip() and aws_secret.strip():
                    os.environ["AWS_ACCESS_KEY_ID"] = aws_key.strip()
                    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret.strip()
                    console.print("✅ AWS credentials set")

        console.print()

    def should_use_mock_mode(self) -> bool:
        """Determine if mock mode should be used."""
        return self._operation_mode == OperationMode.MOCK

    def get_confidence_adjustment(self) -> float:
        """Get confidence score adjustment based on available keys."""
        if self._operation_mode == OperationMode.FULL:
            return 1.0
        elif self._operation_mode == OperationMode.PARTIAL:
            return 0.85
        else:  # MOCK
            return 0.7


def check_api_keys(interactive: bool = True, force_check: bool = False) -> APIKeyStatus:
    """
    Check API key status and optionally prompt user for missing keys.

    Args:
        interactive: Whether to prompt user for missing keys
        force_check: Whether to always show status (even if keys are available)

    Returns:
        APIKeyStatus object with current status
    """
    status = APIKeyStatus()

    # Always show status if requested or if in mock mode
    if force_check or status.operation_mode == OperationMode.MOCK:
        status.display_status()

    # Prompt for keys if in mock mode and interactive
    if interactive and status.operation_mode == OperationMode.MOCK:
        status.prompt_for_keys()

    return status


def ensure_minimum_keys(operation: str = "cost estimation") -> APIKeyStatus:
    """
    Ensure minimum required keys for an operation.

    Args:
        operation: Description of the operation being performed

    Returns:
        APIKeyStatus object
    """
    status = check_api_keys(interactive=True)

    if status.operation_mode == OperationMode.MOCK:
        console.print(f"⚠️  [yellow]Running {operation} in mock mode with simulated data[/yellow]")
        console.print("For production usage, please configure API keys using the setup above.")
        console.print()

    return status