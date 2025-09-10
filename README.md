# 🚀 Neural Fabric Guardian

This project provides an **AI-powered telemetry monitoring, anomaly detection, health scoring, forecasting, and routing optimization system** for GPU interconnect networks. It includes both a **Flask-based backend** and a **frontend dashboard** for visualization.

---

## 📦 Installation Guide

### 1. Clone the Repository

```bash
git clone <repo-url>
cd <repo-name>
```

### 2. Create and Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Configuration

Update `config.py` with necessary parameters like API keys, ports, and settings.

### 5. Run the Application

```bash
python run.py
```

The backend will start on `http://localhost:5000` by default.

---

## 🛠️ Project Setup

* **Backend (Flask API)**: Handles telemetry ingestion, anomaly detection, health scoring, forecasting, and routing optimization.
* **Frontend (Static Dashboard)**: Provides visualizations of telemetry, topology, and alerts.
* **Data**: Sample topologies (`CSV`, `JSON`) for testing.
* **Tests**: Unit and integration tests for core components.

---

## ⚙️ Working

1. **Telemetry Collection**: Simulated or real telemetry ingested via `/telemetry` APIs.
2. **Anomaly Detection**: Isolation Forest + Z-score based methods identify anomalies.
3. **Health Scoring**: Links evaluated using weighted scoring system.
4. **Forecasting**: ARIMA and LSTM models predict performance degradation.
5. **Routing Optimization**: Routes recalculated dynamically based on health and performance.
6. **Visualization**: Dashboard shows network health, forecasts, and alerts.

---

## ✨ Features

* 🔍 **Real-time telemetry monitoring**
* 🤖 **AI-powered anomaly detection**
* 📊 **Link health scoring with recommendations**
* ⏳ **Forecasting of congestion & degradation**
* 🛤️ **Dynamic routing optimization**
* ⚡ **Chaos testing for resilience**
* 🌐 **Frontend dashboard for visualization**

---

## 🖥️ Tech Stack

* **Backend**: Python, Flask
* **AI/ML**: Scikit-learn, TensorFlow, Statsmodels, NumPy, Pandas
* **Frontend**: HTML, CSS, JavaScript (Charts.js, D3.js)
* **Visualization**: Custom topology viewer & charts
* **Testing**: Pytest

---

## 📂 Project Structure

```
backend/
  models/         # AI/ML models (anomaly, forecasting, health)
  routes/         # Flask API routes (routing, telemetry, topology)
  services/       # Fabric & optimizer logic
  utils/          # Telemetry generators, chaos mode
  app.py          # Flask app setup

frontend/
  static/
    css/          # Stylesheets
    js/           # Charts, topology visualizations
  index.html      # Dashboard

data/
  sample_topology.csv
  sample_topology.json

tests/            # Unit & integration tests
config.py         # Configuration
requirements.txt  # Dependencies
run.py            # Entry point
deploy.py         # Deployment script
```

---

## 🧪 Running Tests

```bash
pytest tests/
```

---

## 🚀 Future Improvements

* Support for distributed deployment
* Real telemetry ingestion (from hardware agents)
* Advanced ML models (transformers for time series)
* Role-based access control for APIs

---

## 👨‍💻 Contributors

* **Raghav Tandon**
* **Saumitra**
* **Lakshay Garg**