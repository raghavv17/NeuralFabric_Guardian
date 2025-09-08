# 🧠 NeuralFabric Guardian
> AI-Driven GPU Interconnect Health & Orchestration Control Plane  
Built for Nebula Hackathon 2025 🚀

---

## 🌟 What is this?
Modern AI/ML clusters rely on **GPU interconnect fabrics** (NVLink, PCIe, UALink).  
These links can degrade, congest, or fail — killing training jobs.  

**NeuralFabric Guardian** is a control plane that:
- Simulates a GPU interconnect fabric
- Continuously monitors link telemetry (latency, BER, temperature, utilization)
- Detects anomalies in real time (Z-score + IsolationForest + rule-based)
- Forecasts failures (ARIMA / LSTM)
- Computes link health scores
- Dynamically reroutes jobs using a health-aware optimizer
- Injects **chaos events** (failures, congestion storms, cascades)
- Visualizes everything in a **live interactive dashboard**

---

## 🏗️ Architecture

```text
Telemetry Generator → Anomaly Detector → Health Scorer → Forecaster
        │                      │                │
        └──────→ Fabric Manager + Routing Optimizer ──────→ Job Rerouting
                                                        │
                                            Chaos Engine (failures/stress)
                                                        │
                                                 Flask API Server
                                                        │
                                               Frontend Dashboard
