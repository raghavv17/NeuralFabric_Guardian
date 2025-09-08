import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fabric import FabricManager
from optimizer import RoutingOptimizer
import networkx as nx

class TestRouting(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.fabric = FabricManager()
        self.optimizer = RoutingOptimizer()
        
        # Create test topology
        self.fabric.create_fabric_topology(
            num_gpus=4,
            num_switches=2,
            interconnect_types=['PCIe', 'NVLink', 'UALink']
        )
    
    def test_health_weighted_routing(self):
        """Test health-weighted shortest path routing"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[1]
            
            # Find route optimized for health
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'health'
            )
            
            self.assertIsNotNone(route)
            self.assertEqual(route[0], source)
            self.assertEqual(route[-1], destination)
            self.assertGreaterEqual(len(route), 2)
    
    def test_latency_optimized_routing(self):
        """Test latency-optimized routing"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[-1]
            
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'latency'
            )
            
            self.assertIsNotNone(route)
            self.assertEqual(route[0], source)
            self.assertEqual(route[-1], destination)
    
    def test_energy_optimized_routing(self):
        """Test energy-optimized routing"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[-1]
            
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'energy'
            )
            
            self.assertIsNotNone(route)
            self.assertEqual(route[0], source)
            self.assertEqual(route[-1], destination)
    
    def test_balanced_routing(self):
        """Test balanced optimization routing"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[-1]
            
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'balanced'
            )
            
            self.assertIsNotNone(route)
            self.assertEqual(route[0], source)
            self.assertEqual(route[-1], destination)
    
    def test_route_metrics_calculation(self):
        """Test route metrics calculation"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[1]
            
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'health'
            )
            
            if route:
                metrics = self.optimizer.calculate_route_metrics(
                    self.fabric.topology, route
                )
                
                # Check metrics structure
                self.assertIn('total_latency', metrics)
                self.assertIn('avg_health', metrics)
                self.assertIn('energy_cost', metrics)
                self.assertIn('hops', metrics)
                
                # Check metric values are reasonable
                self.assertGreaterEqual(metrics['total_latency'], 0)
                self.assertGreaterEqual(metrics['avg_health'], 0)
                self.assertLessEqual(metrics['avg_health'], 1)
                self.assertGreaterEqual(metrics['energy_cost'], 0)
                self.assertEqual(metrics['hops'], len(route) - 1)
    
    def test_alternative_routes(self):
        """Test finding alternative routes"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[-1]
            
            alternatives = self.optimizer.find_alternative_routes(
                self.fabric.topology, source, destination, k=3
            )
            
            self.assertIsInstance(alternatives, list)
            self.assertLessEqual(len(alternatives), 3)
            
            # Check each alternative
            for route, metrics in alternatives:
                self.assertIsInstance(route, list)
                self.assertIsInstance(metrics, dict)
                self.assertEqual(route[0], source)
                self.assertEqual(route[-1], destination)
                
                # Check metrics
                self.assertIn('total_latency', metrics)
                self.assertIn('avg_health', metrics)
    
    def test_rerouting_decision(self):
        """Test rerouting decision logic"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[1]
            
            # Find initial route
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'health'
            )
            
            if route:
                # Test with healthy route (should not reroute)
                should_reroute = self.optimizer.should_reroute(
                    self.fabric.topology, route, threshold=0.5
                )
                self.assertIsInstance(should_reroute, bool)
                
                # Degrade some links in the route
                if len(route) > 1:
                    # Find a link in the route to degrade
                    for i in range(len(route) - 1):
                        node1, node2 = route[i], route[i + 1]
                        if self.fabric.topology.has_edge(node1, node2):
                            # Degrade this link
                            edge_data = self.fabric.topology[node1][node2]
                            edge_data['health_score'] = 0.3  # Poor health
                            break
                    
                    # Now should recommend rerouting
                    should_reroute = self.optimizer.should_reroute(
                        self.fabric.topology, route, threshold=0.5
                    )
                    self.assertTrue(should_reroute)
    
    def test_no_path_scenario(self):
        """Test behavior when no path exists"""
        # Create disconnected nodes
        test_topology = nx.Graph()
        test_topology.add_node("GPU_A")
        test_topology.add_node("GPU_B")
        # No edges - nodes are disconnected
        
        route = self.optimizer.find_optimal_route(
            test_topology, "GPU_A", "GPU_B", 'health'
        )
        
        self.assertIsNone(route)
    
    def test_same_source_destination(self):
        """Test routing when source equals destination"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if gpu_nodes:
            source = gpu_nodes[0]
            
            route = self.optimizer.find_optimal_route(
                self.fabric.topology, source, source, 'health'
            )
            
            self.assertEqual(route, [source])
    
    def test_health_penalty_weighting(self):
        """Test that unhealthy links are properly penalized"""
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        
        if len(gpu_nodes) >= 2:
            source = gpu_nodes[0]
            destination = gpu_nodes[1]
            
            # Get initial route
            route1 = self.optimizer.find_optimal_route(
                self.fabric.topology, source, destination, 'health'
            )
            
            if route1 and len(route1) > 1:
                # Severely degrade all links in the current optimal route
                for i in range(len(route1) - 1):
                    node1, node2 = route1[i], route1[i + 1]
                    if self.fabric.topology.has_edge(node1, node2):
                        self.fabric.topology[node1][node2]['health_score'] = 0.1
                
                # Find new route - should avoid the degraded path if alternatives exist
                route2 = self.optimizer.find_optimal_route(
                    self.fabric.topology, source, destination, 'health'
                )
                
                if route2:
                    # Calculate metrics for both routes
                    metrics1 = self.optimizer.calculate_route_metrics(
                        self.fabric.topology, route1
                    )
                    metrics2 = self.optimizer.calculate_route_metrics(
                        self.fabric.topology, route2
                    )
                    
                    # New route should have better health if alternative exists
                    if route1 != route2:
                        self.assertGreater(metrics2['avg_health'], metrics1['avg_health'])
    
    def test_energy_weights(self):
        """Test energy weight calculations"""
        # Test that energy weights are properly configured
        self.assertIn('NVLink', self.optimizer.energy_weights)
        self.assertIn('UALink', self.optimizer.energy_weights)
        self.assertIn('PCIe', self.optimizer.energy_weights)
        
        # NVLink should be most energy efficient
        self.assertLessEqual(
            self.optimizer.energy_weights['NVLink'],
            self.optimizer.energy_weights['PCIe']
        )

if __name__ == '__main__':
    unittest.main()