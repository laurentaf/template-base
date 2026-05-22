import os
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
try:
    from .config import settings
except ImportError:
    import config as settings # Fallback for flat structure

def setup_observability(project_name=None):
    """
    Configures OpenTelemetry to send traces to Phoenix.
    """
    project_name = project_name or settings.PROJECT_NAME
    endpoint = f"{settings.PHOENIX_URL}/v1/traces"
    
    resource = Resource(attributes={
        "service.name": project_name
    })
    
    tracer_provider = trace_sdk.TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=endpoint)
    span_processor = BatchSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    trace_api.set_tracer_provider(tracer_provider)
    
    # Auto-instrument LangChain / LangGraph
    LangChainInstrumentor().instrument()
    
    print(f"✅ Observability Active! Project: {project_name}")
    print(f"🔗 Dashboard: {settings.PHOENIX_URL}")

if __name__ == "__main__":
    setup_observability()
