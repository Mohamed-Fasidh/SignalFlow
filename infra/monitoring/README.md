# Monitoring integration

The starter exposes health endpoints but does not pretend to include production telemetry. Recommended next integration:

- Instrument FastAPI and SQLAlchemy with OpenTelemetry.
- Export traces/metrics to an OpenTelemetry Collector.
- Use Prometheus + Grafana or a managed observability provider.
- Add alerts for 5xx rate, p95 latency, database pool saturation, queue age, worker failures and CRM provider errors.
- Use structured logs with request/correlation IDs and PII redaction.
