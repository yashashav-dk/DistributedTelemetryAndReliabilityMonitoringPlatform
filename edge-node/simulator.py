"""Edge Node Simulator - Generates realistic telemetry metrics for monitoring."""

import math
import os
import random
import threading
import time

from fastapi import FastAPI, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

NODE_ID = os.environ.get("NODE_ID", "1")
registry = CollectorRegistry()

# --- Prometheus Metrics ---
cpu_gauge = Gauge(
    "node_cpu_usage_percent", "Simulated CPU usage",
    ["node_id"], registry=registry,
)
memory_gauge = Gauge(
    "node_memory_usage_percent", "Simulated memory usage",
    ["node_id"], registry=registry,
)
latency_histogram = Histogram(
    "node_request_latency_seconds", "Request latency",
    ["node_id"], registry=registry,
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
requests_total = Counter(
    "node_requests_total", "Total requests processed",
    ["node_id", "status"], registry=registry,
)
uptime_gauge = Gauge(
    "node_uptime_seconds", "Time since node start",
    ["node_id"], registry=registry,
)
error_rate_gauge = Gauge(
    "node_error_rate", "Current error rate 0-1",
    ["node_id"], registry=registry,
)
reliability_gauge = Gauge(
    "reliability_score", "Weighted composite SRE reliability score",
    ["node_id"], registry=registry,
)
error_budget_gauge = Gauge(
    "error_budget_remaining", "Error budget remaining (target 99.9% SLO)",
    ["node_id"], registry=registry,
)

# --- Simulation State ---
start_time = time.time()
seed = int(NODE_ID) * 42
rng = random.Random(seed)

state = {
    "cpu": 40.0,
    "memory": 45.0,
    "error_rate": 0.001,
    "latency_mult": 1.0,
    "total_requests": 0,
    "total_errors": 0,
    "crashed": False,
}

# Active failure injections: {mode: expiry_time}
active_failures: dict[str, float] = {}
failure_lock = threading.Lock()


def update_metrics():
    """Background loop that updates all metrics every 0.5s with realistic patterns."""
    tick = 0
    while True:
        now = time.time()
        elapsed = now - start_time

        # Clear expired failures
        with failure_lock:
            expired = [k for k, v in active_failures.items() if now > v]
            for k in expired:
                del active_failures[k]
            current_failures = dict(active_failures)

        if state["crashed"] and "node_crash" not in current_failures:
            state["crashed"] = False

        if state["crashed"]:
            time.sleep(0.5)
            continue

        # --- CPU simulation ---
        base_cpu = 35 + 20 * math.sin(elapsed / 60) + 10 * math.sin(elapsed / 17)
        noise = rng.gauss(0, 3)
        cpu = max(5, min(95, base_cpu + noise))
        if "cpu_spike" in current_failures:
            cpu = rng.uniform(93, 100)
        state["cpu"] = cpu
        cpu_gauge.labels(node_id=NODE_ID).set(round(cpu, 2))

        # --- Memory simulation ---
        drift = rng.gauss(0, 0.5)
        state["memory"] = max(15, min(90, state["memory"] + drift))
        mem = state["memory"]
        if "memory_leak" in current_failures:
            state["memory"] = min(98, state["memory"] + 0.5)
            mem = state["memory"]
        memory_gauge.labels(node_id=NODE_ID).set(round(mem, 2))

        # --- Latency simulation (log-normal) ---
        base_latency = rng.lognormvariate(-3.5, 0.8)
        latency_mult = 10.0 if "latency_spike" in current_failures else 1.0
        latency = base_latency * latency_mult
        latency_histogram.labels(node_id=NODE_ID).observe(latency)

        # --- Request & error simulation ---
        batch = rng.randint(5, 20)
        error_rate = 0.001 + 0.002 * math.sin(elapsed / 120)
        if "error_burst" in current_failures:
            error_rate = rng.uniform(0.20, 0.50)
        errors_in_batch = sum(1 for _ in range(batch) if rng.random() < error_rate)
        successes = batch - errors_in_batch

        requests_total.labels(node_id=NODE_ID, status="success").inc(successes)
        requests_total.labels(node_id=NODE_ID, status="error").inc(errors_in_batch)
        state["total_requests"] += batch
        state["total_errors"] += errors_in_batch

        # --- Derived metrics ---
        current_error_rate = (
            state["total_errors"] / state["total_requests"]
            if state["total_requests"] > 0
            else 0
        )
        error_rate_gauge.labels(node_id=NODE_ID).set(round(error_rate, 6))

        uptime = elapsed
        uptime_gauge.labels(node_id=NODE_ID).set(round(uptime, 1))

        # Reliability score: weighted composite
        cpu_score = max(0, 1 - (cpu / 100))
        latency_score = max(0, 1 - min(latency, 5) / 5)
        error_score = max(0, 1 - error_rate * 10)
        reliability = 0.3 * cpu_score + 0.3 * latency_score + 0.4 * error_score
        reliability_gauge.labels(node_id=NODE_ID).set(round(reliability, 4))

        # Error budget (99.9% SLO)
        slo_target = 0.999
        if state["total_requests"] > 0:
            actual_success_rate = 1 - current_error_rate
            budget_consumed = max(0, (slo_target - actual_success_rate) / (1 - slo_target))
            budget_remaining = max(0, 1 - budget_consumed)
        else:
            budget_remaining = 1.0
        error_budget_gauge.labels(node_id=NODE_ID).set(round(budget_remaining, 4))

        tick += 1
        time.sleep(0.5)


# Start background metrics thread
metrics_thread = threading.Thread(target=update_metrics, daemon=True)
metrics_thread.start()

app = FastAPI(title=f"Edge Node {NODE_ID}")


@app.get("/health")
def health():
    if state["crashed"]:
        return Response(status_code=503, content="node crashed")
    return {"status": "healthy", "node_id": NODE_ID}


@app.get("/metrics")
def metrics():
    if state["crashed"]:
        return Response(status_code=503, content="node crashed")
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/inject")
def inject_failure(mode: str, duration: int = 30):
    """Inject a failure mode into this node.

    Supported modes: cpu_spike, memory_leak, latency_spike, error_burst, node_crash
    """
    valid_modes = {"cpu_spike", "memory_leak", "latency_spike", "error_burst", "node_crash"}
    if mode not in valid_modes:
        return {"error": f"Unknown mode '{mode}'. Valid: {sorted(valid_modes)}"}

    expiry = time.time() + duration
    with failure_lock:
        active_failures[mode] = expiry

    if mode == "node_crash":
        state["crashed"] = True

    return {
        "status": "injected",
        "node_id": NODE_ID,
        "mode": mode,
        "duration_seconds": duration,
    }
