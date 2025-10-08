"""
Command-line interface for the Cost Estimator Agent.

Provides an intuitive CLI for cost estimation, scenario analysis,
and report generation.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.json import JSON
from rich.markdown import Markdown

from .graph import CostEstimatorGraph, estimate_application_costs
from .schemas import ApplicationSpecification

# Initialize CLI app and console
app = typer.Typer(
    name="cost-estimator",
    help="Intelligent cost estimation for multi-agent AI applications",
    rich_markup_mode="rich"
)
console = Console()


@app.command()
def estimate(
    input_file: Path = typer.Argument(
        ...,
        help="Path to JSON specification file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: stdout)"
    ),
    format: str = typer.Option(
        "markdown",
        "--format", "-f",
        help="Output format: markdown, json, table"
    ),
    scenario_analysis: bool = typer.Option(
        True,
        "--scenarios/--no-scenarios",
        help="Include scenario analysis"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Verbose output with detailed logs"
    )
):
    """
    Estimate costs for a multi-agent AI application.

    Analyzes the provided specification and generates comprehensive
    cost estimates with optimization recommendations.
    """
    console.print("🤖 [bold blue]AI Multi-Agent Cost Estimator[/bold blue]")
    console.print()

    try:
        # Load specification
        with console.status("[bold green]Loading specification..."):
            with open(input_file, 'r') as f:
                spec_data = json.load(f)

        app_name = spec_data.get('application', {}).get('name', 'Unknown Application')
        console.print(f"📊 Analyzing: [bold]{app_name}[/bold]")
        console.print()

        # Run estimation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Estimating costs...", total=None)

            # Run the estimation
            result = asyncio.run(_run_estimation(spec_data, scenario_analysis, progress, task))

        # Display results
        if result.has_errors():
            console.print("❌ [red]Estimation completed with errors:[/red]")
            for error in result.errors:
                console.print(f"  • {error}")
            console.print()

        if result.total_monthly_cost:
            _display_results(result, format, output, scenario_analysis)
        else:
            console.print("❌ [red]Failed to generate cost estimate[/red]")
            sys.exit(1)

    except FileNotFoundError:
        console.print(f"❌ [red]File not found: {input_file}[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"❌ [red]Invalid JSON: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [red]Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command()
def validate(
    input_file: Path = typer.Argument(
        ...,
        help="Path to JSON specification file",
        exists=True,
        file_okay=True,
        dir_okay=False
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Attempt to fix validation issues automatically"
    )
):
    """
    Validate an application specification without running cost estimation.

    Checks the specification for errors, missing fields, and provides
    suggestions for improvement.
    """
    console.print("🔍 [bold blue]Specification Validator[/bold blue]")
    console.print()

    try:
        # Load and validate specification
        with open(input_file, 'r') as f:
            spec_data = json.load(f)

        # Simple validation without requiring API keys
        try:
            spec = ApplicationSpecification(**spec_data)
            validation_result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}
        except Exception as e:
            validation_result = {"valid": False, "errors": [str(e)], "warnings": [], "suggestions": []}

        if validation_result["valid"]:
            console.print("✅ [green]Specification is valid![/green]")

            if validation_result.get("warnings"):
                console.print("\n⚠️  [yellow]Warnings:[/yellow]")
                for warning in validation_result["warnings"]:
                    console.print(f"  • {warning}")

            if validation_result.get("suggestions"):
                console.print("\n💡 [blue]Suggestions:[/blue]")
                for suggestion in validation_result["suggestions"]:
                    console.print(f"  • {suggestion}")

        else:
            console.print("❌ [red]Specification has errors:[/red]")
            for error in validation_result.get("errors", []):
                console.print(f"  • {error}")

            if fix:
                console.print("\n🔧 [yellow]Auto-fix is not yet implemented[/yellow]")

    except Exception as e:
        console.print(f"❌ [red]Validation failed: {e}[/red]")
        sys.exit(1)


@app.command()
def compare(
    scenario_dir: Path = typer.Argument(
        ...,
        help="Directory containing scenario JSON files",
        exists=True,
        file_okay=False,
        dir_okay=True
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: stdout)"
    ),
    format: str = typer.Option(
        "table",
        "--format", "-f",
        help="Output format: table, json, markdown"
    )
):
    """
    Compare costs across multiple scenarios.

    Analyzes all JSON files in the specified directory and provides
    a comparative analysis of costs and recommendations.
    """
    console.print("📊 [bold blue]Scenario Comparison[/bold blue]")
    console.print()

    try:
        # Find all JSON files
        json_files = list(scenario_dir.glob("*.json"))
        if not json_files:
            console.print(f"❌ [red]No JSON files found in {scenario_dir}[/red]")
            sys.exit(1)

        console.print(f"Found {len(json_files)} scenarios to compare")
        console.print()

        # Run estimations for all scenarios
        results = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for json_file in json_files:
                task = progress.add_task(f"Analyzing {json_file.name}...", total=None)

                with open(json_file, 'r') as f:
                    spec_data = json.load(f)

                result = asyncio.run(_run_estimation(spec_data, False, progress, task))
                results[json_file.stem] = result
                progress.remove_task(task)

        # Display comparison
        _display_comparison(results, format, output)

    except Exception as e:
        console.print(f"❌ [red]Comparison failed: {e}[/red]")
        sys.exit(1)


@app.command()
def init(
    name: str = typer.Argument(..., help="Application name"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: {name}_spec.json)"
    ),
    template: str = typer.Option(
        "basic",
        "--template", "-t",
        help="Template type: basic, sales_coach, support_bot"
    )
):
    """
    Initialize a new application specification from a template.

    Creates a basic specification file that can be customized for your
    specific multi-agent AI application.
    """
    console.print("🚀 [bold blue]Initialize Application Specification[/bold blue]")
    console.print()

    output_file = output_file or Path(f"{name.lower().replace(' ', '_')}_spec.json")

    try:
        spec = _create_template_spec(name, template)

        with open(output_file, 'w') as f:
            json.dump(spec, f, indent=2)

        console.print(f"✅ [green]Created specification: {output_file}[/green]")
        console.print(f"📝 [blue]Edit the file to customize your application[/blue]")
        console.print(f"🔍 [blue]Run 'cost-estimator validate {output_file}' to check your changes[/blue]")

    except Exception as e:
        console.print(f"❌ [red]Failed to create specification: {e}[/red]")
        sys.exit(1)


@app.command()
def providers():
    """
    List supported cloud and AI service providers.

    Shows all supported providers for LLMs, cloud infrastructure,
    and vector databases.
    """
    console.print("🌐 [bold blue]Supported Providers[/bold blue]")
    console.print()

    estimator = CostEstimatorGraph()
    providers = estimator.get_supported_providers()

    for category, provider_list in providers.items():
        table = Table(title=category.replace('_', ' ').title())
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")

        for provider in provider_list:
            table.add_row(provider, "✅ Supported")

        console.print(table)
        console.print()


async def _run_estimation(spec_data: Dict[str, Any], scenario_analysis: bool, progress, task) -> Any:
    """Run cost estimation with progress updates."""
    if scenario_analysis:
        estimator = CostEstimatorGraph()
        scenarios = await estimator.estimate_costs_with_scenarios(spec_data)
        return scenarios.get("base")
    else:
        return await estimate_application_costs(spec_data)


def _display_results(result, format: str, output: Optional[Path], scenario_analysis: bool):
    """Display estimation results in the specified format."""
    if format == "json":
        output_data = {
            "total_monthly_cost": float(result.total_monthly_cost),
            "confidence_score": result.get_confidence_score(),
            "cost_breakdown": [
                {
                    "component": cb.component,
                    "category": cb.category,
                    "monthly_cost": float(cb.monthly_cost),
                    "notes": cb.notes
                }
                for cb in result.cost_breakdowns
            ],
            "optimization_suggestions": [
                {
                    "title": opt.title,
                    "description": opt.description,
                    "potential_savings": float(opt.potential_savings),
                    "effort_level": opt.effort_level
                }
                for opt in result.optimization_suggestions
            ]
        }

        if output:
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
        else:
            console.print(JSON.from_data(output_data))

    elif format == "table":
        _display_table_results(result)

    else:  # markdown
        _display_markdown_results(result, output)


def _display_table_results(result):
    """Display results in table format."""
    # Main cost summary
    summary_table = Table(title="💰 Cost Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Monthly Cost", f"${result.total_monthly_cost:.2f}")
    summary_table.add_row("Confidence Score", f"{result.get_confidence_score():.1%}")
    summary_table.add_row("Potential Savings", f"${result.get_total_potential_savings():.2f}")

    console.print(summary_table)
    console.print()

    # Cost breakdown
    breakdown_table = Table(title="📊 Cost Breakdown")
    breakdown_table.add_column("Component", style="cyan")
    breakdown_table.add_column("Category", style="blue")
    breakdown_table.add_column("Monthly Cost", style="green")

    for cb in result.cost_breakdowns:
        breakdown_table.add_row(
            cb.component,
            cb.category,
            f"${cb.monthly_cost:.2f}"
        )

    console.print(breakdown_table)
    console.print()

    # Optimization suggestions
    if result.optimization_suggestions:
        opt_table = Table(title="💡 Optimization Opportunities")
        opt_table.add_column("Suggestion", style="cyan")
        opt_table.add_column("Savings", style="green")
        opt_table.add_column("Effort", style="yellow")

        for opt in result.optimization_suggestions:
            opt_table.add_row(
                opt.title,
                f"${opt.potential_savings:.2f}",
                opt.effort_level
            )

        console.print(opt_table)


def _display_markdown_results(result, output: Optional[Path]):
    """Display results in markdown format."""
    if result.detailed_report:
        content = result.detailed_report
    else:
        # Generate basic markdown
        content = f"""# Cost Estimation Report

## Summary
- **Total Monthly Cost**: ${result.total_monthly_cost:.2f}
- **Confidence Score**: {result.get_confidence_score():.1%}

## Cost Breakdown
"""
        for cb in result.cost_breakdowns:
            content += f"- **{cb.component}** ({cb.category}): ${cb.monthly_cost:.2f}\n"

        if result.optimization_suggestions:
            content += "\n## Optimization Opportunities\n"
            for opt in result.optimization_suggestions:
                content += f"- **{opt.title}**: ${opt.potential_savings:.2f} savings\n"

    if output:
        with open(output, 'w') as f:
            f.write(content)
        console.print(f"📄 [green]Report saved to {output}[/green]")
    else:
        console.print(Markdown(content))


def _display_comparison(results: Dict[str, Any], format: str, output: Optional[Path]):
    """Display scenario comparison results."""
    if format == "table":
        table = Table(title="📊 Scenario Comparison")
        table.add_column("Scenario", style="cyan")
        table.add_column("Monthly Cost", style="green")
        table.add_column("Confidence", style="blue")

        for name, result in results.items():
            if result.total_monthly_cost:
                table.add_row(
                    name,
                    f"${result.total_monthly_cost:.2f}",
                    f"{result.get_confidence_score():.1%}"
                )

        console.print(table)

    elif format == "json":
        comparison_data = {}
        for name, result in results.items():
            if result.total_monthly_cost:
                comparison_data[name] = {
                    "monthly_cost": float(result.total_monthly_cost),
                    "confidence": result.get_confidence_score()
                }

        if output:
            with open(output, 'w') as f:
                json.dump(comparison_data, f, indent=2)
        else:
            console.print(JSON.from_data(comparison_data))


def _create_template_spec(name: str, template: str) -> Dict[str, Any]:
    """Create a template specification."""
    base_spec = {
        "application": {
            "name": name,
            "description": f"Multi-agent AI application: {name}",
            "complexity": "medium",
            "expected_users": 1000,
            "usage_patterns": {
                "sessions_per_user_month": 10,
                "avg_session_duration_minutes": 15,
                "peak_concurrency_ratio": 0.1
            }
        },
        "agents": [
            {
                "name": "PrimaryAgent",
                "role": "primary",
                "llm_config": {
                    "name": "gpt-4-turbo",
                    "provider": "openai",
                    "deployment_mode": "api"
                },
                "tools": [],
                "complexity": "medium",
                "interaction_frequency": "on_demand"
            }
        ],
        "infrastructure": {
            "deployment_type": "cloud",
            "cloud_provider": "aws",
            "region": "us-east-1",
            "scaling_strategy": "auto",
            "availability_requirement": 99.9
        },
        "data_requirements": {
            "vector_stores": [],
            "document_processing_monthly": 1000
        }
    }

    if template == "sales_coach":
        base_spec["application"]["description"] = "AI-powered sales coaching platform"
        base_spec["agents"][0]["name"] = "SalesCoachAgent"
        base_spec["agents"][0]["role"] = "sales_coach"
        base_spec["agents"][0]["tools"] = [
            {"name": "crm_integration", "type": "api", "usage_frequency": "frequent"}
        ]

    elif template == "support_bot":
        base_spec["application"]["description"] = "Intelligent customer support system"
        base_spec["agents"][0]["name"] = "SupportAgent"
        base_spec["agents"][0]["role"] = "customer_support"
        base_spec["data_requirements"]["vector_stores"] = [
            {
                "provider": "pinecone",
                "deployment_mode": "managed",
                "estimated_vectors": 100000,
                "vector_dimensions": 1536
            }
        ]

    return base_spec


def main():
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n❌ [red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()