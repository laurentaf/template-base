from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

try:
    from .config import settings
except ImportError:
    settings = None  # type: ignore[assignment]


def setup_observability(project_name=None):
    try:
        from .config import settings as _settings

        project_name = project_name or _settings.PROJECT_NAME
        endpoint = f"{_settings.PHOENIX_URL}/v1/traces"
    except Exception:
        project_name = project_name or "ltade"
        endpoint = "http://localhost:6006/v1/traces"

    try:
        resource = Resource(attributes={"service.name": project_name})
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint)
        span_processor = BatchSpanProcessor(span_exporter)
        tracer_provider.add_span_processor(span_processor)
        trace_api.set_tracer_provider(tracer_provider)
        LangChainInstrumentor().instrument()
        print(f"Observability Active! Project: {project_name}")
    except Exception:
        print(f"Observability skipped — Phoenix not available at {endpoint}")


def get_tracer(project_name: str = "ltade"):
    return trace_api.get_tracer(project_name)


if __name__ == "__main__":
    setup_observability()
