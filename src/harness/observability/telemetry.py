from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from socket import create_connection
from time import perf_counter
from typing import Any
from urllib.parse import quote_plus, urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from harness.config import HarnessConfig
from harness.schemas.run import RunManifest

_TRACE_INITIALIZED = False


class Telemetry:
    def __init__(self, config: HarnessConfig, manifest: RunManifest) -> None:
        self.config = config
        self.manifest = manifest
        self.registry = CollectorRegistry()
        labels = ["run_id", "task_id", "agent_role", "provider", "model", "git_sha", "worktree"]
        self.tool_calls = Counter(
            "tool_calls_total",
            "Total tool calls",
            labelnames=labels,
            registry=self.registry,
        )
        self.agent_turns = Counter(
            "agent_turns_total",
            "Agent phase executions",
            labelnames=labels,
            registry=self.registry,
        )
        self.failed_steps = Counter(
            "failed_steps_total",
            "Failed steps",
            labelnames=labels,
            registry=self.registry,
        )
        self.run_duration = Histogram(
            "run_duration_seconds",
            "Run duration seconds",
            labelnames=labels,
            registry=self.registry,
        )
        self._start = perf_counter()
        self._tracer = self._configure_tracer()

    def _attrs(self, agent_role: str = "system") -> dict[str, str]:
        return {
            "run_id": self.manifest.run_id,
            "task_id": self.manifest.task_id,
            "agent_role": agent_role,
            "provider": self.manifest.provider,
            "model": self.manifest.model,
            "git_sha": self.manifest.git_sha or "unknown",
            "worktree": self.manifest.worktree_path,
        }

    def _configure_tracer(self) -> trace.Tracer:
        global _TRACE_INITIALIZED
        provider = trace.get_tracer_provider()
        endpoint = self.config.observability.otlp_endpoint
        if not _TRACE_INITIALIZED and endpoint and self._endpoint_reachable(endpoint):
            trace_provider = TracerProvider(
                resource=Resource.create({"service.name": self.config.observability.service_name})
            )
            exporter = OTLPSpanExporter(endpoint=endpoint)
            trace_provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(trace_provider)
            provider = trace_provider
            _TRACE_INITIALIZED = True
        return provider.get_tracer(__name__)

    def _endpoint_reachable(self, endpoint: str) -> bool:
        parsed = urlparse(endpoint)
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return False
        try:
            with create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            return False

    @contextmanager
    def span(self, name: str, agent_role: str = "system", **attrs: Any) -> Iterator[None]:
        payload = {**self._attrs(agent_role), **attrs}
        with self._tracer.start_as_current_span(name, attributes=payload):
            yield

    def record_tool_call(self, agent_role: str) -> None:
        self.tool_calls.labels(**self._attrs(agent_role)).inc()

    def record_turn(self, agent_role: str) -> None:
        self.agent_turns.labels(**self._attrs(agent_role)).inc()

    def record_failure(self, agent_role: str) -> None:
        self.failed_steps.labels(**self._attrs(agent_role)).inc()

    def finish(self) -> dict[str, Any]:
        self.run_duration.labels(**self._attrs()).observe(perf_counter() - self._start)
        return {
            "metrics_text": generate_latest(self.registry).decode("utf-8"),
            "links": self.links(),
        }

    def links(self) -> dict[str, str]:
        run_filter = quote_plus(f'{{run_id="{self.manifest.run_id}"}}')
        return {
            "grafana": self.config.observability.grafana_base_url,
            "loki": f"{self.config.observability.grafana_base_url}/explore?left={run_filter}",
            "tempo": self.config.observability.tempo_base_url,
            "prometheus": self.config.observability.prometheus_base_url,
        }
