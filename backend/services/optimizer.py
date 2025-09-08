import networkx as nx
from typing import Dict, List, Tuple, Optional
import heapq

class RoutingOptimizer:
    """Optimizes routing decisions based on link health and performance metrics"""
    
    def __init__(self):
        self.routing_cache = {}
        self.energy_weights = {
            'NVLink': 1.0,    # Most energy efficient
            'UALink': 1.2,    # Medium efficiency
            'PCIe': 1.5       # Least efficient
        }
    
    def find_optimal_route(self, topology: nx.Graph, source: str, destination: str,
                          optimize_for: str = 'health') -> Optional[List[str]]:
        """
        Find optimal route considering health scores and other factors
        
        Args:
            topology: Network topology graph
            source: Source node
            destination: Destination node
            optimize_for: 'health', 'latency', 'energy', or 'balanced'
        
        Returns:
            List of nodes representing the optimal route, or None if no route exists
        """
        if source == destination:
            return [source]
        
        try:
            if optimize_for == 'health':
                return self._health_weighted_shortest_path(topology, source, destination)
            elif optimize_for == 'latency':
                return self._latency_optimized_path(topology, source, destination)
            elif optimize_for == 'energy':
                return self._energy_optimized_path(topology, source, destination)
            else:  # balanced
                return self._balanced_optimization(topology, source, destination)
                
        except nx.NetworkXNoPath:
            return None
    
    def _health_weighted_shortest_path(self, topology: nx.Graph, source: str, 
                                     destination: str) -> List[str]:
        """Modified Dijkstra's algorithm with health penalty weights"""
        # Create edge weights based on health scores
        def weight_function(u, v, edge_data):
            health_score = edge_data.get('health_score', 1.0)
            base_weight = 1.0
            
            # Penalize unhealthy links heavily
            if health_score < 0.3:
                health_penalty = 10.0  # Very unhealthy
            elif health_score < 0.6:
                health_penalty = 3.0   # Somewhat unhealthy
            else:
                health_penalty = 1.0   # Healthy
            
            # Consider utilization
            utilization = edge_data.get('utilization', 0.0)
            utilization_penalty = 1.0 + (utilization * 2.0)  # Higher utilization = higher cost
            
            return base_weight * health_penalty * utilization_penalty
        
        return nx.shortest_path(topology, source, destination, weight=weight_function)
    
    def _latency_optimized_path(self, topology: nx.Graph, source: str, 
                               destination: str) -> List[str]:
        """Find path with minimum latency"""
        def weight_function(u, v, edge_data):
            base_latency = edge_data.get('base_latency_us', 1.0)
            utilization = edge_data.get('utilization', 0.0)
            
            # Higher utilization increases effective latency
            effective_latency = base_latency * (1.0 + utilization * 2.0)
            
            # Unhealthy links have unpredictable latency
            health_score = edge_data.get('health_score', 1.0)
            if health_score < 0.5:
                effective_latency *= 2.0
            
            return effective_latency
        
        return nx.shortest_path(topology, source, destination, weight=weight_function)
    
    def _energy_optimized_path(self, topology: nx.Graph, source: str, 
                              destination: str) -> List[str]:
        """Find path with minimum energy consumption"""
        def weight_function(u, v, edge_data):
            interconnect_type = edge_data.get('type', 'PCIe')
            base_energy = self.energy_weights.get(interconnect_type, 1.5)
            
            # Higher utilization means more energy consumption
            utilization = edge_data.get('utilization', 0.0)
            energy_factor = 1.0 + (utilization * 1.5)
            
            return base_energy * energy_factor
        
        return nx.shortest_path(topology, source, destination, weight=weight_function)
    
    def _balanced_optimization(self, topology: nx.Graph, source: str, 
                              destination: str) -> List[str]:
        """Find path balancing health, latency, and energy"""
        def weight_function(u, v, edge_data):
            # Health component (0.4 weight)
            health_score = edge_data.get('health_score', 1.0)
            health_cost = (1.0 - health_score) * 4.0
            
            # Latency component (0.4 weight)
            base_latency = edge_data.get('base_latency_us', 1.0)
            utilization = edge_data.get('utilization', 0.0)
            latency_cost = base_latency * (1.0 + utilization) / 10.0
            
            # Energy component (0.2 weight)
            interconnect_type = edge_data.get('type', 'PCIe')
            energy_cost = self.energy_weights.get(interconnect_type, 1.5) / 5.0
            
            return (health_cost * 0.4) + (latency_cost * 0.4) + (energy_cost * 0.2)
        
        return nx.shortest_path(topology, source, destination, weight=weight_function)
    
    def calculate_route_metrics(self, topology: nx.Graph, route: List[str]) -> Dict[str, float]:
        """Calculate comprehensive metrics for a given route"""
        if len(route) < 2:
            return {'total_latency': 0, 'avg_health': 1.0, 'energy_cost': 0, 'hops': 0}
        
        total_latency = 0
        health_scores = []
        energy_cost = 0
        hops = len(route) - 1
        
        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            
            if topology.has_edge(u, v):
                edge_data = topology[u][v]
                
                # Latency calculation
                base_latency = edge_data.get('base_latency_us', 1.0)
                utilization = edge_data.get('utilization', 0.0)
                effective_latency = base_latency * (1.0 + utilization)
                total_latency += effective_latency
                
                # Health tracking
                health_score = edge_data.get('health_score', 1.0)
                health_scores.append(health_score)
                
                # Energy calculation
                interconnect_type = edge_data.get('type', 'PCIe')
                link_energy = self.energy_weights.get(interconnect_type, 1.5)
                energy_cost += link_energy * (1.0 + utilization)
        
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 1.0
        
        return {
            'total_latency': round(total_latency, 2),
            'avg_health': round(avg_health, 3),
            'energy_cost': round(energy_cost, 2),
            'hops': hops,
            'min_health': min(health_scores) if health_scores else 1.0
        }
    
    def find_alternative_routes(self, topology: nx.Graph, source: str, destination: str,
                               k: int = 3) -> List[Tuple[List[str], Dict[str, float]]]:
        """Find k alternative routes with their metrics"""
        routes_with_metrics = []
        
        try:
            # Find multiple paths using different optimization strategies
            strategies = ['health', 'latency', 'energy', 'balanced']
            
            for strategy in strategies:
                if len(routes_with_metrics) >= k:
                    break
                
                route = self.find_optimal_route(topology, source, destination, strategy)
                if route and route not in [r[0] for r in routes_with_metrics]:
                    metrics = self.calculate_route_metrics(topology, route)
                    metrics['strategy'] = strategy
                    routes_with_metrics.append((route, metrics))
            
            # If we still need more routes, try removing edges temporarily
            if len(routes_with_metrics) < k:
                original_topology = topology.copy()
                
                for attempt in range(k - len(routes_with_metrics)):
                    # Remove the most utilized edge temporarily
                    max_util_edge = None
                    max_util = -1
                    
                    for u, v, data in topology.edges(data=True):
                        util = data.get('utilization', 0)
                        if util > max_util:
                            max_util = util
                            max_util_edge = (u, v)
                    
                    if max_util_edge:
                        topology.remove_edge(*max_util_edge)
                        try:
                            route = nx.shortest_path(topology, source, destination)
                            if route not in [r[0] for r in routes_with_metrics]:
                                metrics = self.calculate_route_metrics(original_topology, route)
                                metrics['strategy'] = f'alternative_{attempt + 1}'
                                routes_with_metrics.append((route, metrics))
                        except nx.NetworkXNoPath:
                            pass
                        
                        # Restore the edge
                        edge_data = original_topology[max_util_edge[0]][max_util_edge[1]]
                        topology.add_edge(*max_util_edge, **edge_data)
        
        except Exception as e:
            print(f"Error finding alternative routes: {e}")
        
        # Sort by a combined score (health * efficiency)
        routes_with_metrics.sort(
            key=lambda x: x[1]['avg_health'] / (x[1]['total_latency'] + 1), 
            reverse=True
        )
        
        return routes_with_metrics[:k]
    
    def should_reroute(self, topology: nx.Graph, current_route: List[str], 
                      threshold: float = 0.5) -> bool:
        """Determine if a route should be rerouted based on current conditions"""
        metrics = self.calculate_route_metrics(topology, current_route)
        
        # Reroute if minimum health is below threshold
        if metrics['min_health'] < threshold:
            return True
        
        # Reroute if average health is very low
        if metrics['avg_health'] < 0.4:
            return True
        
        # Check if there's a significantly better alternative
        if len(current_route) >= 2:
            source, destination = current_route[0], current_route[-1]
            alternatives = self.find_alternative_routes(topology, source, destination, 2)
            
            if alternatives:
                best_alternative = alternatives[0][1]
                current_score = metrics['avg_health'] / (metrics['total_latency'] + 1)
                alternative_score = best_alternative['avg_health'] / (best_alternative['total_latency'] + 1)
                
                # Reroute if alternative is significantly better (20% improvement)
                if alternative_score > current_score * 1.2:
                    return True
        
        return False