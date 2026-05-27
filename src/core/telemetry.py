import atexit

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

_tracer_provider: trace_sdk.TracerProvider | None = None


def _shutdown_otel():
    global _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:
            pass
        _tracer_provider = None


def setup_observability(project_name=None):
    global _tracer_provider
    try:
        from .config import settings as _settings

        project_name = project_name or _settings.PROJECT_NAME
        endpoint = f"{_settings.PHOENIX_URL}/v1/traces"
    except Exception:
        project_name = project_name or "ltade"
        endpoint = "http://localhost:6006/v1/traces"

    try:
        resource = Resource(attributes={"service.name": project_name})
        _tracer_provider = trace_sdk.TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint)
        span_processor = BatchSpanProcessor(span_exporter)
        _tracer_provider.add_span_processor(span_processor)
        trace_api.set_tracer_provider(_tracer_provider)
        LangChainInstrumentor().instrument()
        atexit.register(_shutdown_otel)
        print(f"Observability Active! Project: {project_name}")
    except Exception:
        print(f"Observability skipped — Phoenix not available at {endpoint}")


def get_tracer(project_name: str = "ltade"):
    return trace_api.get_tracer(project_name)


if __name__ == "__main__":
    setup_observability()
