import unittest
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from anomaly import AnomalyDetector

class TestAnomalyDetection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = AnomalyDetector()
        
        # Normal telemetry data
        self.normal_telemetry = {
            'link_id': 'test-link-1',
            'timestamp': time.time(),
            'latency': 2.0,
            'ber': 1e-10,
            'utilization': 0.3,
            'temperature': 45.0,
            'crc_errors': 5.0
        }
        
        # Anomalous telemetry data
        self.anomalous_telemetry = {
            'link_id': 'test-link-1',
            'timestamp': time.time(),
            'latency': 150.0,  # Very high latency
            'ber': 5e-8,       # High bit error rate
            'utilization': 0.98, # Very high utilization
            'temperature': 95.0,  # High temperature
            'crc_errors': 500.0   # High CRC errors
        }
    
    def test_baseline_update(self):
        """Test baseline statistics updating"""
        # Update baselines with normal data
        self.detector.update_baselines(self.normal_telemetry)
        
        # Check if baselines were created
        self.assertIn('latency', self.detector.baselines)
        self.assertIn('ber', self.detector.baselines)
        self.assertIn('utilization', self.detector.baselines)
        self.assertIn('temperature', self.detector.baselines)
        self.assertIn('crc_errors', self.detector.baselines)
        
        # Check baseline values exist
        self.assertTrue(len(self.detector.baselines['latency']['values']) > 0)
    
    def test_feature_extraction(self):
        """Test feature extraction from telemetry"""
        features = self.detector.extract_features(self.normal_telemetry)
        
        # Should return a list of numerical features
        self.assertIsInstance(features, list)
        self.assertTrue(len(features) > 5)  # Should have multiple features
        
        # All features should be numerical
        for feature in features:
            self.assertIsInstance(feature, (int, float))
    
    def test_zscore_anomaly_detection(self):
        """Test Z-score based anomaly detection"""
        # Train with normal data
        for _ in range(10):
            self.detector.update_baselines(self.normal_telemetry)
        
        # Test normal data (should not be anomaly)
        normal_anomaly = self.detector._detect_zscore_anomaly(self.normal_telemetry)
        self.assertFalse(normal_anomaly)
        
        # Test anomalous data (should be anomaly)
        anomalous_anomaly = self.detector._detect_zscore_anomaly(self.anomalous_telemetry)
        self.assertTrue(anomalous_anomaly)
    
    def test_rule_based_detection(self):
        """Test rule-based anomaly detection"""
        # Normal data should not trigger rules
        normal_rule_anomaly = self.detector._detect_rule_based_anomaly(self.normal_telemetry)
        self.assertFalse(normal_rule_anomaly)
        
        # Anomalous data should trigger rules
        anomalous_rule_anomaly = self.detector._detect_rule_based_anomaly(self.anomalous_telemetry)
        self.assertTrue(anomalous_rule_anomaly)
    
    def test_anomaly_score(self):
        """Test anomaly score calculation"""
        # Train detector with some data
        for _ in range(25):
            self.detector.detect_anomaly(self.normal_telemetry)
        
        # Get anomaly score for normal data
        normal_score = self.detector.get_anomaly_score(self.normal_telemetry)
        self.assertIsInstance(normal_score, float)
        self.assertGreaterEqual(normal_score, 0.0)
        self.assertLessEqual(normal_score, 1.0)
        
        # Get anomaly score for anomalous data
        anomalous_score = self.detector.get_anomaly_score(self.anomalous_telemetry)
        self.assertIsInstance(anomalous_score, float)
        self.assertGreaterEqual(anomalous_score, 0.0)
        self.assertLessEqual(anomalous_score, 1.0)
        
        # Anomalous data should have higher score
        self.assertGreater(anomalous_score, normal_score)
    
    def test_anomaly_explanation(self):
        """Test anomaly explanation generation"""
        # Train detector
        for _ in range(10):
            self.detector.update_baselines(self.normal_telemetry)
        
        # Get explanation for anomalous data
        explanation = self.detector.get_anomaly_explanation(self.anomalous_telemetry)
        
        # Check explanation structure
        self.assertIn('anomaly_detected', explanation)
        self.assertIn('severity', explanation)
        self.assertIn('explanations', explanation)
        self.assertIn('anomaly_score', explanation)
        self.assertIn('timestamp', explanation)
        
        # Should detect anomaly
        self.assertTrue(explanation['anomaly_detected'])
        
        # Should have explanations
        self.assertGreater(len(explanation['explanations']), 0)
        
        # Check explanation details
        for exp in explanation['explanations']:
            self.assertIn('metric', exp)
            self.assertIn('current_value', exp)
            self.assertIn('z_score', exp)
    
    def test_isolation_forest_training(self):
        """Test Isolation Forest model training"""
        # Feed enough data to trigger training
        for i in range(25):
            telemetry = self.normal_telemetry.copy()
            telemetry['timestamp'] = time.time() + i
            self.detector.detect_anomaly(telemetry)
        
        # Should be fitted after enough data
        self.assertTrue(self.detector.is_fitted)
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with missing fields
        incomplete_telemetry = {
            'link_id': 'test-link-2',
            'timestamp': time.time(),
            'latency': 2.0
            # Missing other fields
        }
        
        # Should not crash
        try:
            is_anomaly = self.detector.detect_anomaly(incomplete_telemetry)
            self.assertIsInstance(is_anomaly, bool)
        except Exception as e:
            self.fail(f"Anomaly detection crashed with incomplete data: {e}")
        
        # Test with extreme values
        extreme_telemetry = {
            'link_id': 'test-link-3',
            'timestamp': time.time(),
            'latency': float('inf'),
            'ber': 0.0,
            'utilization': 1.5,  # > 100%
            'temperature': -100.0,
            'crc_errors': -5.0   # Negative errors
        }
        
        # Should not crash
        try:
            is_anomaly = self.detector.detect_anomaly(extreme_telemetry)
            self.assertIsInstance(is_anomaly, bool)
        except Exception as e:
            self.fail(f"Anomaly detection crashed with extreme values: {e}")
    
    def test_temporal_patterns(self):
        """Test detection of temporal patterns"""
        # Create gradually degrading pattern
        base_latency = 2.0
        
        for i in range(20):
            telemetry = self.normal_telemetry.copy()
            telemetry['timestamp'] = time.time() + i
            telemetry['latency'] = base_latency + (i * 0.5)  # Gradually increasing
            
            is_anomaly = self.detector.detect_anomaly(telemetry)
            
            # Later iterations should be more likely to be anomalies
            if i > 15:  # Last few should be anomalies due to high latency
                self.assertTrue(is_anomaly, f"Expected anomaly at iteration {i}")

if __name__ == '__main__':
    unittest.main()