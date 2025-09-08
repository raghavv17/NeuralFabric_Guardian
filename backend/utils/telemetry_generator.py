import random
import time
import numpy as np
from typing import Dict, Any, List
import math

class TelemetryGenerator:
    """Generates realistic telemetry data for GPU interconnect links"""
    
    def __init__(self, fabric_manager):
        self.fabric_manager = fabric_manager
        
        # Base parameters for different interconnect types
        self.base_params = {
            'NVLink': {
                'latency': {'base': 1.0, 'variance': 0.2, 'unit': 'microseconds'},
                'ber': {'base': 1e-11, 'variance': 5e-12, 'unit': 'errors/bit'},
                'temperature': {'base': 45, 'variance': 8, 'unit': 'celsius'},
                'bandwidth_utilization': {'base': 0.3, 'variance': 0.2},
            },
            'UALink': {
                'latency': {'base': 2.0, 'variance': 0.4, 'unit': 'microseconds'},
                'ber': {'base': 5e-11, 'variance': 2e-11, 'unit': 'errors/bit'},
                'temperature': {'base': 50, 'variance': 10, 'unit': 'celsius'},
                'bandwidth_utilization': {'base': 0.4, 'variance': 0.25},
            },
            'PCIe': {
                'latency': {'base': 5.0, 'variance': 1.0, 'unit': 'microseconds'},
                'ber': {'base': 1e-10, 'variance': 5e-11, 'unit': 'errors/bit'},
                'temperature': {'base': 55, 'variance': 12, 'unit': 'celsius'},
                'bandwidth_utilization': {'base': 0.5, 'variance': 0.3},
            }
        }
        
        # Simulation state
        self.time_step = 0
        self.link_states = {}  # Per-link simulation state
        self.degradation_events = {}  # Active degradation events
        
        # Time-based patterns
        self.daily_pattern = True  # Simulate daily usage patterns
        self.workload_spikes = True  # Simulate periodic workload spikes
        
    def initialize_link_state(self, link_id: str, interconnect_type: str):
        """Initialize simulation state for a link"""
        if link_id not in self.link_states:
            base = self.base_params.get(interconnect_type, self.base_params['PCIe'])
            
            self.link_states[link_id] = {
                'interconnect_type': interconnect_type,
                'base_latency': base['latency']['base'],
                'base_ber': base['ber']['base'],
                'base_temperature': base['temperature']['base'],
                'base_utilization': base['bandwidth_utilization']['base'],
                'current_health': 1.0,
                'trend_offset': random.uniform(-0.1, 0.1),  # Long-term drift
                'noise_seed': random.randint(0, 10000),
                'last_spike': 0,
                'congestion_level': 0.0
            }
    
    def generate_telemetry_batch(self) -> Dict[str, Dict[str, Any]]:
        """Generate telemetry data for all links"""
        self.time_step += 1
        current_time = time.time()
        telemetry_batch = {}
        
        all_links = self.fabric_manager.get_all_links()
        
        for link_id in all_links:
            # Get interconnect type from topology
            interconnect_type = self._get_link_type(link_id)
            
            # Initialize if needed
            self.initialize_link_state(link_id, interconnect_type)
            
            # Generate telemetry for this link
            telemetry_batch[link_id] = self._generate_link_telemetry(link_id, current_time)
        
        return telemetry_batch
    
    def _get_link_type(self, link_id: str) -> str:
        """Get interconnect type for a link from topology"""
        topology = self.fabric_manager.topology
        
        # Parse link_id to find the edge
        if '-' in link_id:
            parts = link_id.split('-', 1)
            node1, node2 = parts[0], parts[1]
            
            if topology.has_edge(node1, node2):
                return topology[node1][node2].get('type', 'PCIe')
        
        return 'PCIe'  # Default fallback
    
    def _generate_link_telemetry(self, link_id: str, timestamp: float) -> Dict[str, Any]:
        """Generate realistic telemetry data for a single link"""
        state = self.link_states[link_id]
        interconnect_type = state['interconnect_type']
        
        # Time-based modulation factors
        time_factor = self._calculate_time_factor(timestamp)
        workload_factor = self._calculate_workload_factor(timestamp, link_id)
        degradation_factor = self._calculate_degradation_factor(link_id, timestamp)
        
        # Base values with time and workload modulation
        base_utilization = state['base_utilization'] * time_factor * workload_factor
        base_utilization = max(0.05, min(0.95, base_utilization))  # Clamp to reasonable range
        
        # Generate correlated metrics
        utilization = base_utilization + random.gauss(0, 0.05)
        utilization = max(0.0, min(1.0, utilization))
        
        # Latency increases with utilization and degradation
        latency_multiplier = 1.0 + (utilization * 2.0) + (degradation_factor * 3.0)
        latency = state['base_latency'] * latency_multiplier
        latency += random.gauss(0, latency * 0.1)  # Add noise
        latency = max(0.1, latency)
        
        # BER increases with temperature and degradation
        temperature = state['base_temperature'] + random.gauss(0, 5)
        temperature += (utilization * 15)  # Higher utilization = higher temp
        temperature += (degradation_factor * 20)  # Degraded links run hotter
        temperature = max(10, min(100, temperature))
        
        temp_factor = 1.0 + ((temperature - 25) * 0.01)  # BER increases with temp
        ber = state['base_ber'] * temp_factor * (1.0 + degradation_factor * 10)
        ber += random.gauss(0, ber * 0.2)  # Add noise
        ber = max(1e-15, ber)
        
        # CRC errors correlate with BER and utilization
        base_crc_rate = 5.0  # errors per second at baseline
        crc_multiplier = (ber / state['base_ber']) * (1.0 + utilization)
        crc_errors = base_crc_rate * crc_multiplier * (1.0 + degradation_factor * 5)
        crc_errors += random.gauss(0, crc_errors * 0.3)
        crc_errors = max(0, crc_errors)
        
        # Add realistic noise and spikes
        if random.random() < 0.05:  # 5% chance of temporary spike
            spike_factor = random.uniform(1.5, 3.0)
            latency *= spike_factor
            crc_errors *= spike_factor
        
        # Update link state
        state['congestion_level'] = utilization
        
        telemetry = {
            'link_id': link_id,
            'timestamp': timestamp,
            'interconnect_type': interconnect_type,
            'latency': round(latency, 3),
            'ber': ber,
            'utilization': round(utilization, 3),
            'temperature': round(temperature, 1),
            'crc_errors': round(crc_errors, 1),
            'bandwidth_gbps': self._calculate_effective_bandwidth(link_id, utilization),
            'signal_integrity': self._calculate_signal_integrity(ber, temperature),
            'health_indicator': 1.0 - degradation_factor
        }
        
        return telemetry
    
    def _calculate_time_factor(self, timestamp: float) -> float:
        """Calculate time-based modulation factor (daily patterns)"""
        if not self.daily_pattern:
            return 1.0
        
        # Simulate daily usage pattern (higher activity during work hours)
        hour_of_day = (timestamp % 86400) / 3600  # Hours since midnight
        
        # Peak activity between 9 AM - 6 PM
        if 9 <= hour_of_day <= 18:
            return random.uniform(0.8, 1.5)  # Higher activity
        elif 6 <= hour_of_day <= 9 or 18 <= hour_of_day <= 22:
            return random.uniform(0.6, 1.2)  # Medium activity
        else:
            return random.uniform(0.2, 0.8)   # Lower activity (night)
    
    def _calculate_workload_factor(self, timestamp: float, link_id: str) -> float:
        """Calculate workload-based modulation factor"""
        if not self.workload_spikes:
            return 1.0
        
        state = self.link_states[link_id]
        
        # Periodic spikes every 5-15 minutes
        spike_period = 300 + (hash(link_id) % 600)  # 5-15 minutes
        time_in_cycle = timestamp % spike_period
        
        # Spike probability increases near the end of cycle
        spike_probability = (time_in_cycle / spike_period) * 0.3
        
        if random.random() < spike_probability:
            state['last_spike'] = timestamp
            return random.uniform(1.5, 2.5)  # Workload spike
        elif timestamp - state['last_spike'] < 60:  # Recent spike aftereffects
            return random.uniform(1.2, 1.8)
        else:
            return random.uniform(0.7, 1.3)  # Normal variation
    
    def _calculate_degradation_factor(self, link_id: str, timestamp: float) -> float:
        """Calculate degradation factor for a link"""
        base_degradation = 0.0
        
        # Check for active degradation events
        if link_id in self.degradation_events:
            event = self.degradation_events[link_id]
            if timestamp < event['end_time']:
                base_degradation = event['severity']
            else:
                # Event expired, remove it
                del self.degradation_events[link_id]
        
        # Add gradual wear over time (very slow)
        age_factor = self.time_step * 0.0001  # Gradual degradation
        
        # Add random fluctuations
        noise = random.gauss(0, 0.02)
        
        total_degradation = base_degradation + age_factor + noise
        return max(0.0, min(0.8, total_degradation))  # Cap at 80% degradation
    
    def _calculate_effective_bandwidth(self, link_id: str, utilization: float) -> float:
        """Calculate effective bandwidth considering utilization"""
        # Get nominal bandwidth from topology
        topology = self.fabric_manager.topology
        nominal_bandwidth = 100  # Default GB/s
        
        if '-' in link_id:
            parts = link_id.split('-', 1)
            node1, node2 = parts[0], parts[1]
            
            if topology.has_edge(node1, node2):
                nominal_bandwidth = topology[node1][node2].get('bandwidth_gbps', 100)
        
        # Effective bandwidth decreases with high utilization due to overhead
        efficiency = 1.0 - (utilization ** 2 * 0.1)  # Quadratic efficiency loss
        return round(nominal_bandwidth * utilization * efficiency, 1)
    
    def _calculate_signal_integrity(self, ber: float, temperature: float) -> float:
        """Calculate signal integrity metric"""
        # Signal integrity decreases with BER and temperature
        ber_factor = max(0.1, 1.0 - (math.log10(abs(ber) + 1e-15) + 10) / 5)
        temp_factor = max(0.1, 1.0 - ((temperature - 25) / 75))
        
        return round(min(ber_factor, temp_factor), 3)
    
    def inject_degradation_event(self, link_id: str, severity: float = 0.5, 
                                duration: float = 300):
        """Inject a degradation event for testing"""
        self.degradation_events[link_id] = {
            'severity': severity,
            'start_time': time.time(),
            'end_time': time.time() + duration,
            'type': 'injected'
        }
    
    def inject_congestion_event(self, link_id: str, utilization_boost: float = 0.3,
                               duration: float = 180):
        """Inject a congestion event"""
        if link_id in self.link_states:
            original_util = self.link_states[link_id]['base_utilization']
            self.link_states[link_id]['base_utilization'] = min(0.95, original_util + utilization_boost)
            
            # Schedule restoration
            def restore_utilization():
                if link_id in self.link_states:
                    self.link_states[link_id]['base_utilization'] = original_util
            
            # In a real implementation, you'd use a timer here
            # For now, we'll let the degradation naturally decay
    
    def get_link_statistics(self, link_id: str) -> Dict[str, Any]:
        """Get statistics for a specific link"""
        if link_id not in self.link_states:
            return {}
        
        state = self.link_states[link_id]
        active_events = []
        
        if link_id in self.degradation_events:
            event = self.degradation_events[link_id]
            remaining_time = event['end_time'] - time.time()
            if remaining_time > 0:
                active_events.append({
                    'type': 'degradation',
                    'severity': event['severity'],
                    'remaining_seconds': round(remaining_time, 1)
                })
        
        return {
            'interconnect_type': state['interconnect_type'],
            'current_health': round(state['current_health'], 3),
            'congestion_level': round(state['congestion_level'], 3),
            'active_events': active_events,
            'time_step': self.time_step
        }