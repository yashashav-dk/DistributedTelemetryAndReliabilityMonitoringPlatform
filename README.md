<p align="center">
  <img src="assets/logo.svg" alt="Distributed Telemetry & Reliability Monitoring Platform" width="800"/>
</p>

<p align="center">
  <strong>A portfolio-grade distributed monitoring platform demonstrating SRE/observability skills.</strong><br>
  Runs 12 simulated edge nodes with Prometheus, Grafana, and Alertmanager, all orchestrated via Docker Compose.
</p>

---

## Architecture

```mermaid
flowchart TB
    subgraph INJECT["&nbsp;&nbsp;Failure Injection CLI&nbsp;&nbsp;"]
        direction LR
        FI["inject_failure.py\n--node N --failure MODE"]
    end

    subgraph DOCKER["&nbsp;&nbsp;Docker Compose Network &nbsp;·&nbsp; 16 Services&nbsp;&nbsp;"]
        direction TB

        subgraph EDGE["&nbsp;&nbsp;Edge Node Fleet &nbsp;·&nbsp; FastAPI + prometheus_client&nbsp;&nbsp;"]
            direction LR
            N1["Node 1\n:8001"]
            N2["Node 2\n:8002"]
            N3["Node 3\n:8003"]
            N4["Node 4\n:8004"]
            N5["Node 5\n:8005"]
            N6["Node 6\n:8006"]
            N7["Node 7\n:8007"]
            N8["Node 8\n:8008"]
            N9["Node 9\n:8009"]
            N10["Node 10\n:8010"]
            N11["Node 11\n:8011"]
            N12["Node 12\n:8012"]
        end

        subgraph OBSERVE["&nbsp;&nbsp;Observability Stack&nbsp;&nbsp;"]
            direction LR
            PROM["Prometheus\n:9090\n\nscrape: 1s\neval: 1s\n7 alert rules"]
            AM["Alertmanager\n:9093\n\ngroup_wait: 0s\nroute by severity"]
            GRAF["Grafana\n:3000\n\n4-row dashboard\nauto-provisioned"]
        end
    end

    subgraph METRICS["&nbsp;&nbsp;Exposed Metrics per Node&nbsp;&nbsp;"]
        direction LR
        M1["cpu_usage\nmemory_usage"]
        M2["request_latency\nrequests_total"]
        M3["reliability_score\nerror_budget"]
    end

    FI -- "POST /inject\ncpu_spike · memory_leak\nlatency_spike · error_burst\nnode_crash" --> EDGE

    N1 & N2 & N3 & N4 & N5 & N6 & N7 & N8 & N9 & N10 & N11 & N12 -- "/metrics" --> PROM

    PROM -- "PromQL\nqueries" --> GRAF
    PROM -- "alerts\n< 2s latency" --> AM

    EDGE -.- METRICS

    style DOCKER fill:#0d1117,stroke:#30363d,stroke-width:2px,color:#c9d1d9
    style EDGE fill:#161b22,stroke:#00d2ff,stroke-width:1.5px,color:#c9d1d9
    style OBSERVE fill:#161b22,stroke:#7b2ff7,stroke-width:1.5px,color:#c9d1d9
    style INJECT fill:#1a1226,stroke:#f97583,stroke-width:1.5px,stroke-dasharray:5 5,color:#c9d1d9
    style METRICS fill:#1a1226,stroke:#3fb950,stroke-width:1px,stroke-dasharray:3 3,color:#8b949e

    style N1 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N2 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N3 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N4 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N5 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N6 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N7 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N8 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N9 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N10 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N11 fill:#21262d,stroke:#00ff88,color:#c9d1d9
    style N12 fill:#21262d,stroke:#00ff88,color:#c9d1d9

    style PROM fill:#2a1a0a,stroke:#e6522c,stroke-width:2px,color:#f0883e
    style AM fill:#2a1a0a,stroke:#e6522c,stroke-width:1.5px,color:#f0883e
    style GRAF fill:#1a1a0a,stroke:#f46800,stroke-width:2px,color:#f0883e
    style FI fill:#21262d,stroke:#f97583,stroke-width:1.5px,color:#f97583

    style M1 fill:#0d1117,stroke:#3fb950,stroke-width:1px,color:#3fb950
    style M2 fill:#0d1117,stroke:#3fb950,stroke-width:1px,color:#3fb950
    style M3 fill:#0d1117,stroke:#3fb950,stroke-width:1px,color:#3fb950

    linkStyle 0 stroke:#f97583,stroke-width:1.5px
    linkStyle 1,2,3,4,5,6,7,8,9,10,11,12 stroke:#00d2ff,stroke-width:1px
    linkStyle 13 stroke:#7b2ff7,stroke-width:2px
    linkStyle 14 stroke:#e6522c,stroke-width:2px
    linkStyle 15 stroke:#3fb950,stroke-width:1px,stroke-dasharray:3
```

## Quick Start

```bash
# Start all 16 services
docker compose up --build -d

# Open Grafana dashboard (no login required)
open http://localhost:3000

# View Prometheus targets
open http://localhost:9090/targets

# View Alertmanager
open http://localhost:9093
```

## Metrics

Each edge node exposes the following Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `node_cpu_usage_percent` | Gauge | Simulated CPU usage (10-85% with drift) |
| `node_memory_usage_percent` | Gauge | Simulated memory usage (20-75% with drift) |
| `node_request_latency_seconds` | Histogram | Request latency (log-normal distribution) |
| `node_requests_total` | Counter | Total requests (labeled `status=success/error`) |
| `node_uptime_seconds` | Gauge | Time since node start |
| `node_error_rate` | Gauge | Current error rate (0-1) |
| `reliability_score` | Gauge | Weighted composite SRE metric |
| `error_budget_remaining` | Gauge | Error budget remaining (99.9% SLO target) |

## Alerting

Prometheus evaluates alert rules every 1s with `for: 0s` for sub-2-second detection:

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighCPUUsage | CPU > 90% | warning |
| HighMemoryUsage | Memory > 85% | warning |
| HighErrorRate | Error rate > 5% | critical |
| HighLatency | p95 latency > 1s | warning |
| NodeDown | Target unreachable | critical |
| LowReliabilityScore | Score < 0.95 | warning |
| ErrorBudgetBurn | Budget < 50% | critical |

## Failure Injection

Use the injection script to test alerting and dashboard responsiveness:

```bash
# Spike CPU on node 3 for 30 seconds
python scripts/inject_failure.py --node 3 --failure cpu_spike --duration 30

# Simulate memory leak on node 7
python scripts/inject_failure.py --node 7 --failure memory_leak --duration 60

# Inject latency spike across all nodes
python scripts/inject_failure.py --node all --failure latency_spike --duration 20

# Trigger error burst on node 5
python scripts/inject_failure.py --node 5 --failure error_burst --duration 30

# Crash node 10
python scripts/inject_failure.py --node 10 --failure node_crash --duration 45
```

### Failure Modes

| Mode | Effect |
|------|--------|
| `cpu_spike` | CPU jumps to 95-100% |
| `memory_leak` | Memory climbs steadily to 95%+ |
| `latency_spike` | Latency increases 10x |
| `error_burst` | Error rate jumps to 20-50% |
| `node_crash` | Node returns 503 on all endpoints |

## Grafana Dashboard

The pre-provisioned dashboard includes four rows:

1. **Overview** - Active nodes, reliability score, error budget, platform health gauge
2. **Resource Utilization** - CPU and memory time series for all 12 nodes
3. **Request Metrics** - Request rate, p50/p95/p99 latency, error rate per node
4. **SRE Metrics** - Reliability score, error budget consumption, active alerts

## Project Structure

```
├── docker-compose.yml              # Orchestrates all 16 services
├── edge-node/
│   ├── Dockerfile                  # Python 3.11 slim image
│   ├── requirements.txt            # FastAPI + prometheus-client
│   └── simulator.py                # Edge node simulator
├── prometheus/
│   ├── prometheus.yml              # Scrape config (1s interval)
│   └── rules/
│       └── alerts.yml              # 7 alert rules
├── alertmanager/
│   └── alertmanager.yml            # Alert routing config
├── grafana/
│   └── provisioning/
│       ├── dashboards/
│       │   ├── dashboards.yml      # Dashboard provider
│       │   └── telemetry.json      # Pre-built dashboard
│       └── datasources/
│           └── datasource.yml      # Prometheus datasource
└── scripts/
    └── inject_failure.py           # Failure injection CLI
```

## Teardown

```bash
docker compose down
```
