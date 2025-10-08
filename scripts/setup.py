#!/usr/bin/env python3
"""
Setup script for the Cost Estimator Agent.

This script helps users set up the development environment, configure
API keys, and validate the installation.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="Setup script for Cost Estimator Agent")


def check_python_version() -> bool:
    """Check if Python version is 3.11 or higher."""
    if sys.version_info < (3, 11):
        console.print(f"❌ [red]Python 3.11+ required. You have {sys.version}[/red]")
        return False
    console.print(f"✅ [green]Python {sys.version_info.major}.{sys.version_info.minor}[/green]")
    return True


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_dependencies() -> bool:
    """Install Python dependencies."""
    console.print("📦 [blue]Installing dependencies...[/blue]")

    try:
        # Try pip install first
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], capture_output=True, text=True)

        if result.returncode == 0:
            console.print("✅ [green]Dependencies installed successfully[/green]")
            return True
        else:
            console.print(f"❌ [red]Failed to install dependencies: {result.stderr}[/red]")
            return False

    except Exception as e:
        console.print(f"❌ [red]Error installing dependencies: {e}[/red]")
        return False


def create_env_file(api_keys: Dict[str, str]) -> bool:
    """Create .env file with user-provided API keys."""
    env_path = Path(".env")

    if env_path.exists():
        if not Confirm.ask("📄 .env file already exists. Overwrite?"):
            return True

    try:
        with open(env_path, "w") as f:
            f.write("# Cost Estimator Agent Configuration\n\n")
            f.write("# Core Application Settings\n")
            f.write("APP_NAME=\"Cost Estimator Agent\"\n")
            f.write("DEBUG=true\n")
            f.write("LOG_LEVEL=INFO\n\n")

            f.write("# LLM Provider API Keys\n")
            if api_keys.get("openai"):
                f.write(f"OPENAI_API_KEY={api_keys['openai']}\n")
            if api_keys.get("anthropic"):
                f.write(f"ANTHROPIC_API_KEY={api_keys['anthropic']}\n")
            if api_keys.get("azure_openai"):
                f.write(f"AZURE_OPENAI_API_KEY={api_keys['azure_openai']}\n")
                f.write("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com\n")
            f.write("\n")

            f.write("# Cloud Provider Credentials (Optional)\n")
            if api_keys.get("aws_access_key"):
                f.write(f"AWS_ACCESS_KEY_ID={api_keys['aws_access_key']}\n")
                f.write("AWS_SECRET_ACCESS_KEY=your_aws_secret_key\n")
            if api_keys.get("azure_subscription"):
                f.write(f"AZURE_SUBSCRIPTION_ID={api_keys['azure_subscription']}\n")
            if api_keys.get("gcp_project"):
                f.write(f"GCP_PROJECT_ID={api_keys['gcp_project']}\n")
            f.write("\n")

            f.write("# Feature Flags\n")
            f.write("ENABLE_LIVE_PRICING=false\n")
            f.write("FALLBACK_TO_CACHED_PRICING=true\n")
            f.write("ENABLE_OPTIMIZATION_SUGGESTIONS=true\n")
            f.write("ENABLE_SCENARIO_ANALYSIS=true\n\n")

            f.write("# Security (Generate a secure secret key for production)\n")
            f.write("SECRET_KEY=your-secret-key-change-this-in-production\n")

        console.print("✅ [green].env file created successfully[/green]")
        return True

    except Exception as e:
        console.print(f"❌ [red]Failed to create .env file: {e}[/red]")
        return False


def collect_api_keys() -> Dict[str, str]:
    """Collect API keys from user."""
    console.print("\n🔑 [blue]API Key Configuration[/blue]")
    console.print("Enter your API keys (press Enter to skip optional keys):\n")

    api_keys = {}

    # Required LLM API keys
    console.print("[bold]At least one LLM API key is required:[/bold]")

    openai_key = Prompt.ask("OpenAI API Key", default="", show_default=False)
    if openai_key:
        api_keys["openai"] = openai_key

    anthropic_key = Prompt.ask("Anthropic API Key", default="", show_default=False)
    if anthropic_key:
        api_keys["anthropic"] = anthropic_key

    azure_key = Prompt.ask("Azure OpenAI API Key", default="", show_default=False)
    if azure_key:
        api_keys["azure_openai"] = azure_key

    if not any([openai_key, anthropic_key, azure_key]):
        console.print("⚠️  [yellow]Warning: No LLM API keys provided. You'll need to add them later.[/yellow]")

    # Optional cloud provider keys
    console.print("\n[bold]Optional cloud provider credentials:[/bold]")

    if Confirm.ask("Configure AWS credentials?", default=False):
        aws_key = Prompt.ask("AWS Access Key ID", default="", show_default=False)
        if aws_key:
            api_keys["aws_access_key"] = aws_key

    if Confirm.ask("Configure Azure credentials?", default=False):
        azure_sub = Prompt.ask("Azure Subscription ID", default="", show_default=False)
        if azure_sub:
            api_keys["azure_subscription"] = azure_sub

    if Confirm.ask("Configure GCP credentials?", default=False):
        gcp_project = Prompt.ask("GCP Project ID", default="", show_default=False)
        if gcp_project:
            api_keys["gcp_project"] = gcp_project

    return api_keys


def test_installation() -> bool:
    """Test that the installation works correctly."""
    console.print("\n🧪 [blue]Testing installation...[/blue]")

    try:
        # Test importing the main module
        import cost_estimator
        console.print("✅ [green]Module import successful[/green]")

        # Test CLI command
        result = subprocess.run([
            sys.executable, "-m", "cost_estimator.cli", "--help"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            console.print("✅ [green]CLI command working[/green]")
        else:
            console.print("❌ [red]CLI command failed[/red]")
            return False

        # Test example validation
        example_path = Path("examples/minimal_example.json")
        if example_path.exists():
            result = subprocess.run([
                sys.executable, "-m", "cost_estimator.cli", "validate", str(example_path)
            ], capture_output=True, text=True)

            if result.returncode == 0:
                console.print("✅ [green]Example validation successful[/green]")
            else:
                console.print("⚠️  [yellow]Example validation failed (this is OK if API keys aren't configured)[/yellow]")

        return True

    except Exception as e:
        console.print(f"❌ [red]Installation test failed: {e}[/red]")
        return False


def show_next_steps():
    """Show next steps after successful setup."""
    console.print("\n🎉 [green bold]Setup completed successfully![/green bold]\n")

    panel_content = """
[bold cyan]Next Steps:[/bold cyan]

1. [bold]Try the CLI:[/bold]
   cost-estimator estimate --input examples/minimal_example.json

2. [bold]Start the API server:[/bold]
   uvicorn cost_estimator.api:app --reload

3. [bold]Run tests:[/bold]
   pytest tests/

4. [bold]Create your own specification:[/bold]
   cost-estimator init "My AI App" --template basic

5. [bold]Edit .env file to add missing API keys[/bold]

[bold green]Documentation:[/bold green]
- README.md - Architecture and usage guide
- examples/ - Sample application specifications
- docs/ - Additional documentation
"""

    console.print(Panel(panel_content, title="🚀 You're Ready to Go!", border_style="green"))


@app.command()
def install(
    skip_dependencies: bool = typer.Option(False, "--skip-deps", help="Skip dependency installation"),
    skip_api_keys: bool = typer.Option(False, "--skip-keys", help="Skip API key configuration"),
    dev: bool = typer.Option(False, "--dev", help="Install development dependencies")
):
    """Install and configure the Cost Estimator Agent."""
    console.print("🤖 [bold blue]Cost Estimator Agent Setup[/bold blue]\n")

    # Check prerequisites
    if not check_python_version():
        sys.exit(1)

    # Check for Git (optional but recommended)
    if check_command_exists("git"):
        console.print("✅ [green]Git available[/green]")
    else:
        console.print("⚠️  [yellow]Git not found (recommended for development)[/yellow]")

    # Install dependencies
    if not skip_dependencies:
        if not install_dependencies():
            sys.exit(1)

        if dev:
            console.print("📦 [blue]Installing development dependencies...[/blue]")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-e", ".[dev]"
                ], check=True, capture_output=True)
                console.print("✅ [green]Development dependencies installed[/green]")
            except subprocess.CalledProcessError:
                console.print("❌ [red]Failed to install development dependencies[/red]")

    # Configure API keys
    if not skip_api_keys:
        api_keys = collect_api_keys()
        if not create_env_file(api_keys):
            sys.exit(1)

    # Test installation
    if not test_installation():
        console.print("⚠️  [yellow]Installation test failed, but setup may still work[/yellow]")

    show_next_steps()


@app.command()
def validate():
    """Validate the current installation and configuration."""
    console.print("🔍 [bold blue]Validating Installation[/bold blue]\n")

    issues = []

    # Check Python version
    if not check_python_version():
        issues.append("Python 3.11+ required")

    # Check if package is installed
    try:
        import cost_estimator
        console.print("✅ [green]Package installed[/green]")
    except ImportError:
        console.print("❌ [red]Package not installed[/red]")
        issues.append("Run 'python setup.py install' first")

    # Check .env file
    env_path = Path(".env")
    if env_path.exists():
        console.print("✅ [green].env file exists[/green]")

        # Check for API keys
        with open(env_path) as f:
            env_content = f.read()

        if "OPENAI_API_KEY" in env_content or "ANTHROPIC_API_KEY" in env_content:
            console.print("✅ [green]LLM API keys configured[/green]")
        else:
            console.print("⚠️  [yellow]No LLM API keys found in .env[/yellow]")
            issues.append("Add at least one LLM API key to .env")
    else:
        console.print("❌ [red].env file missing[/red]")
        issues.append("Run setup to create .env file")

    # Check examples
    examples_dir = Path("examples")
    if examples_dir.exists() and list(examples_dir.glob("*.json")):
        console.print("✅ [green]Example specifications found[/green]")
    else:
        console.print("⚠️  [yellow]No example specifications found[/yellow]")

    # Summary
    if issues:
        console.print(f"\n❌ [red]{len(issues)} issues found:[/red]")
        for issue in issues:
            console.print(f"  • {issue}")
        sys.exit(1)
    else:
        console.print("\n✅ [green bold]All checks passed![/green bold]")


@app.command()
def update():
    """Update the Cost Estimator Agent to the latest version."""
    console.print("🔄 [blue]Updating Cost Estimator Agent...[/blue]")

    try:
        # Update the package
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "-e", "."
        ], check=True)

        console.print("✅ [green]Update completed successfully[/green]")

        # Test after update
        if test_installation():
            console.print("✅ [green]Update verified[/green]")
        else:
            console.print("⚠️  [yellow]Update completed but tests failed[/yellow]")

    except subprocess.CalledProcessError as e:
        console.print(f"❌ [red]Update failed: {e}[/red]")
        sys.exit(1)


@app.command()
def clean():
    """Clean up build artifacts and cache files."""
    console.print("🧹 [blue]Cleaning up...[/blue]")

    patterns_to_clean = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "build/",
        "dist/",
        "*.egg-info/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".mypy_cache/",
    ]

    import shutil
    import glob

    cleaned_count = 0

    for pattern in patterns_to_clean:
        for path in glob.glob(pattern, recursive=True):
            path_obj = Path(path)
            try:
                if path_obj.is_file():
                    path_obj.unlink()
                    cleaned_count += 1
                elif path_obj.is_dir():
                    shutil.rmtree(path_obj)
                    cleaned_count += 1
            except Exception as e:
                console.print(f"⚠️  [yellow]Could not clean {path}: {e}[/yellow]")

    console.print(f"✅ [green]Cleaned {cleaned_count} items[/green]")


if __name__ == "__main__":
    app()