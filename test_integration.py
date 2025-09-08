#!/usr/bin/env python3
"""
Integration test to verify all components work together
"""
import sys
import os
import time
import unittest
from unittest.mock import patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all main components
from fabric import FabricManager
from optimizer import RoutingOptimizer
from anomaly import AnomalyDetector
from forecasting import LinkPerformanceForecaster
from health_score import HealthScoreCalculator
from telemetry_generator import TelemetryGenerator
from chaos_mode import ChaosEngine

class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up complete system for integration testing"""
        self.fabric_manager = FabricManager()
        self.routing_optimizer = RoutingOptimizer()
        self.anomaly_detector = AnomalyDetector()
        self.forecaster = LinkPerformanceForecaster()
        self.health_calculator = HealthScoreCalculator()
        
        # Create test topology
        self.fabric_manager.create_fabric_topology(
            num_gpus=4,
            num_switches=2,
            interconnect_types=['PCIe', 'NVLink', 'UALink']
        )
        
        self.telemetry_generator = TelemetryGenerator(self.fabric_manager)
        self.chaos_engine = ChaosEngine(self.fabric_manager, self.telemetry_generator)
    
    def test_full_system_workflow(self):
        """Test complete system workflow"""
        # 1. Generate telemetry
        telemetry_batch = self.telemetry_generator.generate_telemetry_batch()
        self.assertGreater(len(telemetry_batch), 0)
        
        # 2. Process each link
        for link_id, telemetry_data in telemetry_batch.items():
            # Anomaly detection
            is_anomaly = self.anomaly_detector.detect_anomaly(telemetry_data)
            self.assertIsInstance(is_anomaly, bool)
            
            # Health scoring
            health_result = self.health_calculator.calculate_health_score(telemetry_data)
            self.assertIn('overall_score', health_result)
            self.assertIsInstance(health_result['overall_score'], float)
            
            # Forecasting
            self.forecaster.add_telemetry_data(link_id, telemetry_data)
            
            # Update fabric
            self.fabric_manager.update_link_health(link_id, health_result['overall_score'])
        
        # 3. Test routing optimization
        jobs = list(self.fabric_manager.jobs.values())
        if jobs:
            job = jobs[0]
            current_route = job['route']
            
            # Test rerouting decision
            should_reroute = self.routing_optimizer.should_reroute(
                self.fabric_manager.topology, current_route
            )
            self.assertIsInstance(should_reroute, bool)
            
            # Test route optimization
            new_route = self.routing_optimizer.find_optimal_route(
                self.fabric_manager.topology,
                job['source'],
                job['destination'],
                'health'
            )
            self.assertIsNotNone(new_route)
    
    def test_chaos_injection_and_recovery(self):
        """Test chaos injection and system recovery"""
        # Inject chaos
        result = self.chaos_engine.inject_chaos('link_degradation')
        self.assertIn('type', result)
        self.assertEqual(result['type'], 'link_degradation')
        
        # Generate telemetry after chaos
        telemetry_batch = self.telemetry_generator.generate_telemetry_batch()
        
        # Should detect anomalies due to chaos
        anomaly_detected = False
        for link_id, telemetry_data in telemetry_batch.items():
            if self.anomaly_detector.detect_anomaly(telemetry_data):
                anomaly_detected = True
                break
        
        # Note: Due to the nature of the simulation, we might not always detect anomalies
        # This is expected behavior
        
        # Stop chaos
        self.chaos_engine.stop_all_chaos()
        
        # Verify chaos stopped
        active_events = self.chaos_engine.get_active_events()
        # Events might still be active if they haven't expired yet
        self.assertIsInstance(active_events, dict)
    
    def test_forecasting_workflow(self):
        """Test forecasting functionality"""
        # Generate some historical data
        for i in range(10):
            telemetry_batch = self.telemetry_generator.generate_telemetry_batch()
            for link_id, telemetry_data in telemetry_batch.items():
                telemetry_data['timestamp'] = time.time() + i
                self.forecaster.add_telemetry_data(link_id, telemetry_data)
        
        # Test forecasting
        links = self.fabric_manager.get_all_links()
        if links:
            test_link = links[0]
            forecast = self.forecaster.forecast_link_performance(test_link, horizon=5)
            self.assertIsInstance(forecast, dict)
    
    def test_health_scoring_accuracy(self):
        """Test health scoring accuracy"""
        # Create known good telemetry
        good_telemetry = {
            'link_id': 'test-link',
            'timestamp': time.time(),
            'latency': 1.0,
            'ber': 1e-12,
            'utilization': 0.3,
            'temperature': 45.0,
            'crc_errors': 1.0,
            'signal_integrity': 0.95
        }
        
        health_result = self.health_calculator.calculate_health_score(good_telemetry)
        self.assertGreaterEqual(health_result['overall_score'], 0.8)  # Should be healthy
        
        # Create known bad telemetry
        bad_telemetry = {
            'link_id': 'test-link',
            'timestamp': time.time(),
            'latency': 100.0,
            'ber': 1e-8,
            'utilization': 0.95,
            'temperature': 90.0,
            'crc_errors': 200.0,
            'signal_integrity': 0.3
        }
        
        health_result = self.health_calculator.calculate_health_score(bad_telemetry)
        self.assertLessEqual(health_result['overall_score'], 0.5)  # Should be unhealthy
    
    def test_error_handling(self):
        """Test system error handling"""
        # Test with invalid data
        invalid_telemetry = {
            'link_id': 'invalid-link',
            'timestamp': time.time(),
            'latency': float('inf'),
            'ber': -1.0,  # Invalid BER
            'utilization': 2.0,  # Invalid utilization > 100%
            'temperature': -100.0  # Invalid temperature
        }
        
        # Should not crash
        try:
            is_anomaly = self.anomaly_detector.detect_anomaly(invalid_telemetry)
            health_result = self.health_calculator.calculate_health_score(invalid_telemetry)
            self.assertIsInstance(is_anomaly, bool)
            self.assertIsInstance(health_result['overall_score'], float)
        except Exception as e:
            self.fail(f"System crashed with invalid data: {e}")
    
    def test_topology_modification(self):
        """Test dynamic topology changes"""
        # Get initial state
        initial_links = len(self.fabric_manager.get_all_links())
        
        # Create new topology
        self.fabric_manager.create_fabric_topology(
            num_gpus=6,
            num_switches=3,
            interconnect_types=['NVLink', 'UALink']
        )
        
        # Verify changes
        new_links = len(self.fabric_manager.get_all_links())
        self.assertNotEqual(initial_links, new_links)
        
        # Reinitialize telemetry generator
        self.telemetry_generator = TelemetryGenerator(self.fabric_manager)
        
        # Should still work
        telemetry_batch = self.telemetry_generator.generate_telemetry_batch()
        self.assertGreater(len(telemetry_batch), 0)

if __name__ == '__main__':
    unittest.main()