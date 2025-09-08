import networkx as nx
import random
import json
import uuid
from typing import Dict, List, Tuple, Any

class FabricManager:
    """Manages GPU fabric topology and job routing"""
    
    def __init__(self):
        self.topology = nx.Graph()
        self.jobs = {}  # Active jobs
        self.link_health = {}  # Link health scores
        self.node_types = {}  # GPU, Switch, etc.
        
    def create_fabric_topology(self, num_gpus: int, num_switches: int, 
                             interconnect_types: List[str]):
        """Create a realistic GPU fabric topology"""
        self.topology.clear()
        self.jobs.clear()
        self.link_health.clear()
        self.node_types.clear()
        
        # Add GPU nodes
        gpu_nodes = []
        for i in range(num_gpus):
            node_id = f"GPU_{i}"
            gpu_nodes.append(node_id)
            self.topology.add_node(node_id, 
                                 type='GPU',
                                 compute_capability=random.choice([7.5, 8.0, 8.6, 9.0]),
                                 memory_gb=random.choice([16, 24, 32, 48, 80]))
            self.node_types[node_id] = 'GPU'
        
        # Add Switch nodes
        switch_nodes = []
        for i in range(num_switches):
            node_id = f"SW_{i}"
            switch_nodes.append(node_id)
            self.topology.add_node(node_id,
                                 type='Switch',
                                 ports=random.choice([16, 32, 64]))
            self.node_types[node_id] = 'Switch'
        
        # Connect GPUs to switches with different interconnect types
        for gpu in gpu_nodes:
            # Each GPU connects to 1-2 switches
            connected_switches = random.sample(switch_nodes, 
                                             min(random.randint(1, 2), len(switch_nodes)))
            
            for switch in connected_switches:
                interconnect_type = random.choice(interconnect_types)
                link_id = f"{gpu}-{switch}"
                
                # Different interconnect types have different characteristics
                if interconnect_type == 'NVLink':
                    bandwidth = random.choice([300, 400, 600])  # GB/s
                    base_latency = random.uniform(0.5, 1.0)  # μs
                elif interconnect_type == 'UALink':
                    bandwidth = random.choice([200, 400])  # GB/s
                    base_latency = random.uniform(1.0, 2.0)  # μs
                else:  # PCIe
                    bandwidth = random.choice([16, 32, 64])  # GB/s
                    base_latency = random.uniform(2.0, 5.0)  # μs
                
                self.topology.add_edge(gpu, switch,
                                     link_id=link_id,
                                     type=interconnect_type,
                                     bandwidth_gbps=bandwidth,
                                     base_latency_us=base_latency,
                                     utilization=random.uniform(0.1, 0.3),
                                     health_score=1.0)
                
                self.link_health[link_id] = 1.0
        
        # Connect switches to each other
        for i, sw1 in enumerate(switch_nodes):
            for sw2 in switch_nodes[i+1:]:
                if random.random() < 0.7:  # 70% chance of connection
                    interconnect_type = random.choice(['UALink', 'PCIe'])
                    link_id = f"{sw1}-{sw2}"
                    
                    if interconnect_type == 'UALink':
                        bandwidth = random.choice([400, 800])
                        base_latency = random.uniform(0.8, 1.5)
                    else:  # PCIe
                        bandwidth = random.choice([32, 64])
                        base_latency = random.uniform(1.5, 3.0)
                    
                    self.topology.add_edge(sw1, sw2,
                                         link_id=link_id,
                                         type=interconnect_type,
                                         bandwidth_gbps=bandwidth,
                                         base_latency_us=base_latency,
                                         utilization=random.uniform(0.2, 0.5),
                                         health_score=1.0)
                    
                    self.link_health[link_id] = 1.0
        
        # Generate some sample jobs
        self._generate_sample_jobs()
        
    def _generate_sample_jobs(self):
        """Generate sample GPU compute jobs"""
        gpu_nodes = [n for n in self.topology.nodes() if self.node_types[n] == 'GPU']
        
        for i in range(random.randint(3, 8)):
            source = random.choice(gpu_nodes)
            destination = random.choice([n for n in gpu_nodes if n != source])
            
            # Find initial route
            try:
                route = nx.shortest_path(self.topology, source, destination)
                job_id = str(uuid.uuid4())[:8]
                
                self.jobs[job_id] = {
                    'id': job_id,
                    'source': source,
                    'destination': destination,
                    'route': route,
                    'type': random.choice(['training', 'inference', 'data_transfer']),
                    'priority': random.choice(['high', 'medium', 'low']),
                    'bandwidth_required': random.randint(10, 100),  # GB/s
                    'created_at': random.randint(1640995200, 1672531200)  # 2022-2023
                }
            except nx.NetworkXNoPath:
                continue  # Skip if no path exists
    
    def get_topology_json(self) -> Dict[str, Any]:
        """Convert topology to JSON format for frontend"""
        nodes = []
        edges = []
        
        for node in self.topology.nodes(data=True):
            nodes.append({
                'id': node[0],
                'type': node[1].get('type', 'unknown'),
                'data': dict(node[1])
            })
        
        for edge in self.topology.edges(data=True):
            edges.append({
                'source': edge[0],
                'target': edge[1],
                'id': edge[2].get('link_id', f"{edge[0]}-{edge[1]}"),
                'type': edge[2].get('type', 'unknown'),
                'data': dict(edge[2])
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'jobs': list(self.jobs.values())
        }
    
    def get_all_links(self) -> List[str]:
        """Get all link IDs"""
        links = []
        for edge in self.topology.edges(data=True):
            link_id = edge[2].get('link_id', f"{edge[0]}-{edge[1]}")
            links.append(link_id)
        return links
    
    def update_link_health(self, link_id: str, health_score: float):
        """Update health score for a specific link"""
        self.link_health[link_id] = health_score
        
        # Update the edge in the topology
        for edge in self.topology.edges(data=True):
            if edge[2].get('link_id') == link_id:
                edge[2]['health_score'] = health_score
                break
    
    def get_jobs_on_link(self, link_id: str) -> List[Dict[str, Any]]:
        """Get all jobs that use a specific link"""
        affected_jobs = []
        
        # Parse link_id to get nodes
        if '-' in link_id:
            node1, node2 = link_id.split('-', 1)
            
            for job in self.jobs.values():
                route = job['route']
                for i in range(len(route) - 1):
                    if (route[i] == node1 and route[i+1] == node2) or \
                       (route[i] == node2 and route[i+1] == node1):
                        affected_jobs.append(job)
                        break
        
        return affected_jobs
    
    def reroute_job(self, job_id: str, new_route: List[str]):
        """Reroute a specific job"""
        if job_id in self.jobs:
            self.jobs[job_id]['route'] = new_route
            return True
        return False
    
    def degrade_link(self, link_id: str, degradation_factor: float = 0.5):
        """Artificially degrade a link for testing"""
        for edge in self.topology.edges(data=True):
            if edge[2].get('link_id') == link_id:
                # Increase latency and reduce effective bandwidth
                edge[2]['base_latency_us'] *= (2 - degradation_factor)
                edge[2]['utilization'] = min(0.9, edge[2].get('utilization', 0.5) * 1.5)
                break
        
        # Update health score
        self.update_link_health(link_id, degradation_factor)
    
    def get_link_utilization(self, link_id: str) -> float:
        """Get current utilization of a link"""
        for edge in self.topology.edges(data=True):
            if edge[2].get('link_id') == link_id:
                return edge[2].get('utilization', 0.0)
        return 0.0
    
    def set_link_utilization(self, link_id: str, utilization: float):
        """Set utilization for a link"""
        for edge in self.topology.edges(data=True):
            if edge[2].get('link_id') == link_id:
                edge[2]['utilization'] = min(1.0, max(0.0, utilization))
                break