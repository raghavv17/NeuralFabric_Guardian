import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fabric import FabricManager
import networkx as nx

class TestTopology(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.fabric = FabricManager()
    
    def test_topology_creation(self):
        """Test basic topology creation"""
        self.fabric.create_fabric_topology(
            num_gpus=4, 
            num_switches=2, 
            interconnect_types=['PCIe', 'NVLink']
        )
        
        # Check nodes were created
        self.assertEqual(len(self.fabric.topology.nodes()), 6)  # 4 GPUs + 2 switches
        
        # Check GPU nodes
        gpu_nodes = [n for n in self.fabric.topology.nodes() if 'GPU_' in n]
        self.assertEqual(len(gpu_nodes), 4)
        
        # Check switch nodes
        switch_nodes = [n for n in self.fabric.topology.nodes() if 'SW_' in n]
        self.assertEqual(len(switch_nodes), 2)
    
    def test_topology_edges(self):
        """Test topology edge creation"""
        self.fabric.create_fabric_topology(
            num_gpus=2, 
            num_switches=1, 
            interconnect_types=['NVLink']
        )
        
        # Should have edges connecting GPUs to switches
        self.assertGreater(len(self.fabric.topology.edges()), 0)
        
        # Check edge attributes
        for edge in self.fabric.topology.edges(data=True):
            self.assertIn('link_id', edge[2])
            self.assertIn('type', edge[2])
            self.assertIn('bandwidth_gbps', edge[2])
            self.assertIn('base_latency_us', edge[2])
    
    def test_job_management(self):
        """Test job creation and management"""
        self.fabric.create_fabric_topology(
            num_gpus=4, 
            num_switches=2, 
            interconnect_types=['PCIe']
        )
        
        # Check jobs were created
        self.assertGreater(len(self.fabric.jobs), 0)
        
        # Check job attributes
        for job_id, job in self.fabric.jobs.items():
            self.assertIn('source', job)
            self.assertIn('destination', job)
            self.assertIn('route', job)
            self.assertIn('type', job)
    
    def test_health_update(self):
        """Test link health score updates"""
        self.fabric.create_fabric_topology(
            num_gpus=2, 
            num_switches=1, 
            interconnect_types=['NVLink']
        )
        
        links = self.fabric.get_all_links()
        if links:
            test_link = links[0]
            
            # Update health score
            self.fabric.update_link_health(test_link, 0.5)
            
            # Check if update was successful
            self.assertEqual(self.fabric.link_health[test_link], 0.5)
    
    def test_link_utilization(self):
        """Test link utilization management"""
        self.fabric.create_fabric_topology(
            num_gpus=2, 
            num_switches=1, 
            interconnect_types=['PCIe']
        )
        
        links = self.fabric.get_all_links()
        if links:
            test_link = links[0]
            
            # Set utilization
            self.fabric.set_link_utilization(test_link, 0.8)
            
            # Get utilization
            util = self.fabric.get_link_utilization(test_link)
            self.assertEqual(util, 0.8)
    
    def test_topology_json_export(self):
        """Test topology JSON export"""
        self.fabric.create_fabric_topology(
            num_gpus=2, 
            num_switches=1, 
            interconnect_types=['NVLink']
        )
        
        topology_json = self.fabric.get_topology_json()
        
        # Check JSON structure
        self.assertIn('nodes', topology_json)
        self.assertIn('edges', topology_json)
        self.assertIn('jobs', topology_json)
        
        # Check nodes
        self.assertEqual(len(topology_json['nodes']), 3)  # 2 GPUs + 1 switch
        
        # Check edges exist
        self.assertGreater(len(topology_json['edges']), 0)
    
    def test_job_rerouting(self):
        """Test job rerouting functionality"""
        self.fabric.create_fabric_topology(
            num_gpus=4, 
            num_switches=2, 
            interconnect_types=['PCIe']
        )
        
        if self.fabric.jobs:
            job_id = list(self.fabric.jobs.keys())[0]
            original_route = self.fabric.jobs[job_id]['route'].copy()
            new_route = ['GPU_0', 'SW_0', 'GPU_1']  # Simple test route
            
            success = self.fabric.reroute_job(job_id, new_route)
            self.assertTrue(success)
            self.assertEqual(self.fabric.jobs[job_id]['route'], new_route)
    
    def test_link_degradation(self):
        """Test link degradation functionality"""
        self.fabric.create_fabric_topology(
            num_gpus=2, 
            num_switches=1, 
            interconnect_types=['NVLink']
        )
        
        links = self.fabric.get_all_links()
        if links:
            test_link = links[0]
            
            # Get original latency
            original_latency = None
            for edge in self.fabric.topology.edges(data=True):
                if edge[2].get('link_id') == test_link:
                    original_latency = edge[2]['base_latency_us']
                    break
            
            # Degrade link
            self.fabric.degrade_link(test_link, 0.5)
            
            # Check if latency increased
            new_latency = None
            for edge in self.fabric.topology.edges(data=True):
                if edge[2].get('link_id') == test_link:
                    new_latency = edge[2]['base_latency_us']
                    break
            
            if original_latency and new_latency:
                self.assertGreater(new_latency, original_latency)

if __name__ == '__main__':
    unittest.main()