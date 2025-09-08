import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from collections import deque
from typing import Dict, List, Any, Optional
import time

class AnomalyDetector:
    """AI-powered anomaly detection for GPU interconnect telemetry"""
    
    def __init__(self, contamination=0.1, window_size=50):
        self.contamination = contamination
        self.window_size = window_size
        
        # Models for different metrics
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # Historical data storage
        self.historical_data = deque(maxlen=1000)
        self.link_histories = {}  # Per-link historical data
        
        # Z-score thresholds for quick detection
        self.z_score_thresholds = {
            'latency': 3.0,
            'ber': 2.5,
            'utilization': 2.0,
            'temperature': 2.5,
            'crc_errors': 2.0
        }
        
        # Baseline statistics
        self.baselines = {}
    
    def update_baselines(self, telemetry_data: Dict[str, Any]):
        """Update baseline statistics for each metric"""
        for metric in ['latency', 'ber', 'utilization', 'temperature', 'crc_errors']:
            if metric in telemetry_data:
                value = telemetry_data[metric]
                
                if metric not in self.baselines:
                    self.baselines[metric] = {
                        'values': deque(maxlen=100),
                        'mean': 0,
                        'std': 1
                    }
                
                self.baselines[metric]['values'].append(value)
                
                # Update mean and std
                values = list(self.baselines[metric]['values'])
                if len(values) > 5:
                    self.baselines[metric]['mean'] = np.mean(values)
                    self.baselines[metric]['std'] = max(np.std(values), 0.001)  # Avoid division by zero
    
    def extract_features(self, telemetry_data: Dict[str, Any]) -> List[float]:
        """Extract feature vector from telemetry data"""
        features = []
        
        # Basic metrics
        features.append(telemetry_data.get('latency', 0))
        features.append(telemetry_data.get('ber', 0))
        features.append(telemetry_data.get('utilization', 0))
        features.append(telemetry_data.get('temperature', 0))
        features.append(telemetry_data.get('crc_errors', 0))
        
        # Derived features
        features.append(telemetry_data.get('latency', 0) * telemetry_data.get('utilization', 0))  # Latency under load
        features.append(telemetry_data.get('ber', 0) / max(telemetry_data.get('utilization', 0.001), 0.001))  # BER efficiency
        features.append(telemetry_data.get('temperature', 0) - 20)  # Temperature deviation from room temp
        
        # Rate of change (if we have historical data)
        timestamp = telemetry_data.get('timestamp', time.time())
        if hasattr(self, 'last_telemetry') and self.last_telemetry:
            time_diff = max(timestamp - self.last_telemetry.get('timestamp', 0), 0.1)
            
            latency_rate = (telemetry_data.get('latency', 0) - self.last_telemetry.get('latency', 0)) / time_diff
            utilization_rate = (telemetry_data.get('utilization', 0) - self.last_telemetry.get('utilization', 0)) / time_diff
            
            features.append(latency_rate)
            features.append(utilization_rate)
        else:
            features.extend([0, 0])  # No rate information available
        
        self.last_telemetry = telemetry_data
        return features
    
    def detect_anomaly(self, telemetry_data: Dict[str, Any]) -> bool:
        """
        Detect anomalies in telemetry data using multiple methods
        
        Args:
            telemetry_data: Dictionary containing telemetry metrics
            
        Returns:
            True if anomaly detected, False otherwise
        """
        # Update baselines
        self.update_baselines(telemetry_data)
        
        # Method 1: Z-score based detection (fast)
        z_score_anomaly = self._detect_zscore_anomaly(telemetry_data)
        
        # Method 2: Isolation Forest (more sophisticated)
        isolation_anomaly = self._detect_isolation_anomaly(telemetry_data)
        
        # Method 3: Rule-based detection
        rule_based_anomaly = self._detect_rule_based_anomaly(telemetry_data)
        
        # Combine results (anomaly if any method detects it)
        return z_score_anomaly or isolation_anomaly or rule_based_anomaly
    
    def _detect_zscore_anomaly(self, telemetry_data: Dict[str, Any]) -> bool:
        """Detect anomalies using Z-score thresholds"""
        for metric, threshold in self.z_score_thresholds.items():
            if metric in telemetry_data and metric in self.baselines:
                value = telemetry_data[metric]
                baseline = self.baselines[metric]
                
                if len(baseline['values']) > 5:
                    z_score = abs(value - baseline['mean']) / baseline['std']
                    if z_score > threshold:
                        return True
        
        return False
    
    def _detect_isolation_anomaly(self, telemetry_data: Dict[str, Any]) -> bool:
        """Detect anomalies using Isolation Forest"""
        features = self.extract_features(telemetry_data)
        self.historical_data.append(features)
        
        # Need enough data to train
        if len(self.historical_data) < 20:
            return False
        
        # Retrain periodically or if not fitted
        if not self.is_fitted or len(self.historical_data) % 100 == 0:
            try:
                X = np.array(list(self.historical_data))
                X_scaled = self.scaler.fit_transform(X)
                self.isolation_forest.fit(X_scaled)
                self.is_fitted = True
            except Exception as e:
                print(f"Error training Isolation Forest: {e}")
                return False
        
        # Predict anomaly
        if self.is_fitted:
            try:
                X_current = np.array(features).reshape(1, -1)
                X_scaled = self.scaler.transform(X_current)
                prediction = self.isolation_forest.predict(X_scaled)
                return prediction[0] == -1  # -1 indicates anomaly
            except Exception as e:
                print(f"Error in anomaly prediction: {e}")
                return False
        
        return False
    
    def _detect_rule_based_anomaly(self, telemetry_data: Dict[str, Any]) -> bool:
        """Detect anomalies using domain-specific rules"""
        
        # Rule 1: Excessive latency
        latency = telemetry_data.get('latency', 0)
        if latency > 100:  # > 100 microseconds is concerning
            return True
        
        # Rule 2: High bit error rate
        ber = telemetry_data.get('ber', 0)
        if ber > 1e-9:  # BER threshold
            return True
        
        # Rule 3: Overutilization
        utilization = telemetry_data.get('utilization', 0)
        if utilization > 0.95:  # > 95% utilization
            return True
        
        # Rule 4: Temperature issues
        temperature = telemetry_data.get('temperature', 0)
        if temperature > 85 or temperature < 10:  # Outside normal range
            return True
        
        # Rule 5: Excessive CRC errors
        crc_errors = telemetry_data.get('crc_errors', 0)
        if crc_errors > 100:  # Too many errors per second
            return True
        
        # Rule 6: Inconsistent performance (high latency with low utilization)
        if latency > 50 and utilization < 0.1:
            return True
        
        return False
    
    def get_anomaly_score(self, telemetry_data: Dict[str, Any]) -> float:
        """Get continuous anomaly score (0.0 = normal, 1.0 = highly anomalous)"""
        if not self.is_fitted:
            return 0.0
        
        try:
            features = self.extract_features(telemetry_data)
            X_current = np.array(features).reshape(1, -1)
            X_scaled = self.scaler.transform(X_current)
            
            # Get anomaly score from Isolation Forest
            score = self.isolation_forest.decision_function(X_current)[0]
            
            # Normalize score to 0-1 range (approximately)
            # Isolation Forest returns negative values for anomalies
            normalized_score = max(0, min(1, (0.5 - score) * 2))
            
            return normalized_score
            
        except Exception as e:
            print(f"Error calculating anomaly score: {e}")
            return 0.0
    
    def get_anomaly_explanation(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide explanation for detected anomalies"""
        explanations = []
        severity = "normal"
        
        # Check each metric against its baseline
        for metric in ['latency', 'ber', 'utilization', 'temperature', 'crc_errors']:
            if metric in telemetry_data and metric in self.baselines:
                value = telemetry_data[metric]
                baseline = self.baselines[metric]
                
                if len(baseline['values']) > 5:
                    z_score = abs(value - baseline['mean']) / baseline['std']
                    
                    if z_score > self.z_score_thresholds[metric]:
                        explanations.append({
                            'metric': metric,
                            'current_value': round(value, 4),
                            'baseline_mean': round(baseline['mean'], 4),
                            'z_score': round(z_score, 2),
                            'deviation': 'high' if value > baseline['mean'] else 'low'
                        })
                        
                        if z_score > 4:
                            severity = "critical"
                        elif z_score > 3 and severity != "critical":
                            severity = "high"
                        elif severity == "normal":
                            severity = "medium"
        
        return {
            'anomaly_detected': len(explanations) > 0,
            'severity': severity,
            'explanations': explanations,
            'anomaly_score': self.get_anomaly_score(telemetry_data),
            'timestamp': time.time()
        }