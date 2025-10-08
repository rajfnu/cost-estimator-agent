"""
FastAPI application for cost estimation API.

Provides REST endpoints for cost estimation, validation, and analysis
with comprehensive error handling and documentation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..graph import CostEstimatorGraph, estimate_application_costs
from ..schemas import ApplicationSpecification, CostEstimationRequest
from ..graph.state import CostEstimationState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Multi-Agent Cost Estimator API",
    description="Intelligent cost estimation system for multi-agent AI applications",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global estimator instance
estimator = CostEstimatorGraph()


# Pydantic models for API requests/responses
class EstimationResponse(BaseModel):
    """Response model for cost estimation."""
    estimation_id: str
    total_monthly_cost: float
    confidence_score: float
    processing_time_seconds: float
    cost_breakdown: List[Dict[str, Any]]
    optimization_suggestions: List[Dict[str, Any]]
    scenarios: Optional[List[Dict[str, Any]]] = None
    executive_summary: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    """Response model for specification validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    """Response model for scenario comparison."""
    scenarios: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    supported_providers: Dict[str, List[str]]


# Helper functions
def _convert_decimal_to_float(obj: Any) -> Any:
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimal_to_float(v) for v in obj]
    return obj


def _state_to_response(state: CostEstimationState) -> EstimationResponse:
    """Convert CostEstimationState to API response."""
    cost_breakdown = []
    for cb in state.cost_breakdowns:
        cost_breakdown.append({
            "component": cb.component,
            "category": cb.category,
            "monthly_cost": float(cb.monthly_cost),
            "usage_estimate": {
                "component": cb.usage_estimate.component,
                "usage_amount": cb.usage_estimate.usage_amount,
                "usage_unit": cb.usage_estimate.usage_unit,
                "confidence_level": cb.usage_estimate.confidence_level
            },
            "pricing_data": {
                "service": cb.pricing_data.service,
                "provider": cb.pricing_data.provider,
                "unit_cost": float(cb.pricing_data.unit_cost),
                "unit_type": cb.pricing_data.unit_type,
                "confidence_level": cb.pricing_data.confidence_level
            },
            "notes": cb.notes
        })

    optimization_suggestions = []
    for opt in state.optimization_suggestions:
        optimization_suggestions.append({
            "title": opt.title,
            "description": opt.description,
            "category": opt.category,
            "potential_savings": float(opt.potential_savings),
            "effort_level": opt.effort_level,
            "implementation_time": opt.implementation_time,
            "trade_offs": opt.trade_offs,
            "confidence": opt.confidence
        })

    return EstimationResponse(
        estimation_id=state.estimation_id or "unknown",
        total_monthly_cost=float(state.total_monthly_cost or 0),
        confidence_score=state.get_confidence_score(),
        processing_time_seconds=state.processing_time_seconds or 0.0,
        cost_breakdown=cost_breakdown,
        optimization_suggestions=optimization_suggestions,
        executive_summary=state.executive_summary,
        warnings=state.warnings,
        errors=state.errors
    )


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
        supported_providers=estimator.get_supported_providers()
    )


@app.post("/estimate", response_model=EstimationResponse)
async def estimate_costs(
    request: CostEstimationRequest,
    background_tasks: BackgroundTasks
):
    """
    Estimate costs for a multi-agent AI application.

    Analyzes the provided specification and returns comprehensive
    cost estimates with optimization recommendations.
    """
    try:
        logger.info(f"Starting cost estimation for: {request.specification.application.name}")

        # Convert specification to dict for processing
        spec_dict = request.specification.dict()

        # Run estimation
        if request.scenario_analysis:
            scenarios_result = await estimator.estimate_costs_with_scenarios(spec_dict)
            state = scenarios_result.get("base")

            # Add scenario data to response
            response = _state_to_response(state)
            response.scenarios = []

            for scenario_name, scenario_state in scenarios_result.items():
                if scenario_name != "base":
                    response.scenarios.append({
                        "name": scenario_name,
                        "total_cost": float(scenario_state.total_monthly_cost or 0),
                        "confidence": scenario_state.get_confidence_score()
                    })

        else:
            state = await estimator.estimate_costs(spec_dict, request.estimation_options)
            response = _state_to_response(state)

        logger.info(f"Estimation completed: ${response.total_monthly_cost:.2f}/month")
        return response

    except Exception as e:
        logger.error(f"Estimation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Estimation failed: {str(e)}")


@app.post("/validate", response_model=ValidationResponse)
async def validate_specification(specification: ApplicationSpecification):
    """
    Validate an application specification.

    Checks the specification for errors and provides suggestions
    for improvement without running the full cost estimation.
    """
    try:
        # Convert to dict and validate
        spec_dict = specification.dict()
        validation_result = estimator.validate_specification(spec_dict)

        return ValidationResponse(
            valid=validation_result["valid"],
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", []),
            suggestions=validation_result.get("suggestions", [])
        )

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")


@app.post("/compare", response_model=ComparisonResponse)
async def compare_scenarios(
    scenarios: Dict[str, ApplicationSpecification],
    background_tasks: BackgroundTasks
):
    """
    Compare costs across multiple application scenarios.

    Analyzes multiple specifications and provides a comparative
    analysis of costs and recommendations.
    """
    try:
        logger.info(f"Comparing {len(scenarios)} scenarios")

        results = {}
        total_costs = []

        # Process each scenario
        for name, spec in scenarios.items():
            spec_dict = spec.dict()
            state = await estimator.estimate_costs(spec_dict)

            if state.total_monthly_cost:
                results[name] = {
                    "monthly_cost": float(state.total_monthly_cost),
                    "confidence_score": state.get_confidence_score(),
                    "cost_breakdown": _convert_decimal_to_float([
                        {
                            "component": cb.component,
                            "category": cb.category,
                            "monthly_cost": float(cb.monthly_cost)
                        }
                        for cb in state.cost_breakdowns
                    ]),
                    "optimization_suggestions": len(state.optimization_suggestions),
                    "potential_savings": float(state.get_total_potential_savings())
                }
                total_costs.append(float(state.total_monthly_cost))

        # Generate summary
        summary = {
            "total_scenarios": len(scenarios),
            "cost_range": {
                "min": min(total_costs) if total_costs else 0,
                "max": max(total_costs) if total_costs else 0,
                "avg": sum(total_costs) / len(total_costs) if total_costs else 0
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

        return ComparisonResponse(scenarios=results, summary=summary)

    except Exception as e:
        logger.error(f"Comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/providers")
async def get_supported_providers():
    """Get list of supported cloud and AI service providers."""
    return estimator.get_supported_providers()


@app.get("/templates")
async def get_templates():
    """Get available application specification templates."""
    return {
        "basic": {
            "name": "Basic Multi-Agent Application",
            "description": "Simple multi-agent application with standard components",
            "use_cases": ["General purpose", "Proof of concept", "Small scale deployment"]
        },
        "sales_coach": {
            "name": "Sales Coaching Platform",
            "description": "AI-powered sales coaching with CRM integration",
            "use_cases": ["Sales enablement", "Training platforms", "Performance optimization"]
        },
        "support_bot": {
            "name": "Customer Support System",
            "description": "Intelligent customer support with knowledge base",
            "use_cases": ["Customer service", "Help desk automation", "FAQ systems"]
        },
        "content_generator": {
            "name": "Content Generation Pipeline",
            "description": "Multi-agent content creation and review system",
            "use_cases": ["Marketing automation", "Content production", "Document generation"]
        }
    }


@app.get("/estimation/{estimation_id}")
async def get_estimation(estimation_id: str):
    """Retrieve a previous estimation by ID."""
    # This would integrate with a database to retrieve historical estimations
    # For now, return a placeholder response
    raise HTTPException(status_code=404, detail="Estimation history not yet implemented")


# WebSocket endpoint for streaming updates (optional)
@app.websocket("/ws/estimate")
async def websocket_estimate(websocket):
    """WebSocket endpoint for real-time estimation updates."""
    await websocket.accept()
    # Implementation for streaming estimation progress
    # This would use the streaming capabilities of the graph
    await websocket.send_text("Streaming estimation not yet implemented")
    await websocket.close()


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle value errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": f"Invalid input: {str(exc)}"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Cost Estimator API starting up...")
    # Initialize any required services here


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Cost Estimator API shutting down...")
    # Cleanup any resources here


# Development server
def run_dev_server():
    """Run development server."""
    uvicorn.run(
        "cost_estimator.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_dev_server()