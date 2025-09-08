import random
import time
from typing import Dict, List, Any

class ChaosEngine:
    """Chaos engineering tools for testing system resilience"""
    
    def __init__(self, fabric_manager, telemetry_generator):
        self.fabric_manager = fabric_manager
        self.telemetry_generator = telemetry_generator
        self.active_chaos_events = {}
    
    def inject_chaos(self, chaos_type: str) -> Dict[str, Any]:
        """Inject various types of chaos events"""
        chaos_methods = {
            'link_degradation': self._inject_link_degradation,
            'sudden_failure': self._inject_sudden_failure,
            'intermittent_issues': self._inject_intermittent_issues,
            'congestion_storm': self._inject_congestion_storm,
            'thermal_event': self._inject_thermal_event,
            'cascade_failure': self._inject_cascade_failure
        }
        
        if chaos_type not in chaos_methods:
            return {'error': f'Unknown chaos type: {chaos_type}'}
        
        return chaos_methods[chaos_type]()
    
    def _inject_link_degradation(self) -> Dict[str, Any]:
        """Gradually degrade a random link's performance"""
        all_links = self.fabric_manager.get_all_links()
        if not all_links:
            return {'error': 'No links available for degradation'}
        
        target_link = random.choice(all_links)
        severity = random.uniform(0.3, 0.7)  # 30-70% degradation
        duration = random.randint(120, 300)   # 2-5 minutes
        
        # Apply degradation to fabric
        self.fabric_manager.degrade_link(target_link, 1.0 - severity)
        
        # Apply to telemetry generator
        self.telemetry_generator.inject_degradation_event(
            target_link, severity, duration
        )
        
        self.active_chaos_events[target_link] = {
            'type': 'degradation',
            'severity': severity,
            'start_time': time.time(),
            'duration': duration
        }
        
        return {
            'type': 'link_degradation',
            'target': target_link,
            'severity': f'{severity*100:.1f}%',
            'duration': f'{duration}s',
            'description': f'Degraded {target_link} by {severity*100:.1f}% for {duration} seconds'
        }
    
    def _inject_sudden_failure(self) -> Dict[str, Any]:
        """Suddenly fail a random link completely"""
        all_links = self.fabric_manager.get_all_links()
        if not all_links:
            return {'error': 'No links available for failure'}
        
        target_link = random.choice(all_links)
        duration = random.randint(60, 180)  # 1-3 minutes
        
        # Complete failure
        self.fabric_manager.degrade_link(target_link, 0.0)
        self.telemetry_generator.inject_degradation_event(
            target_link, 0.9, duration
        )
        
        self.active_chaos_events[target_link] = {
            'type': 'failure',
            'start_time': time.time(),
            'duration': duration
        }
        
        return {
            'type': 'sudden_failure',
            'target': target_link,
            'duration': f'{duration}s',
            'description': f'Complete failure of {target_link} for {duration} seconds'
        }
    
    def _inject_intermittent_issues(self) -> Dict[str, Any]:
        """Create intermittent connectivity issues"""
        all_links = self.fabric_manager.get_all_links()
        if not all_links:
            return {'error': 'No links available'}
        
        target_links = random.sample(all_links, min(3, len(all_links)))
        affected_links = []
        
        for link in target_links:
            # Random intermittent degradation
            severity = random.uniform(0.2, 0.5)
            duration = random.randint(30, 90)
            
            self.telemetry_generator.inject_degradation_event(
                link, severity, duration
            )
            
            affected_links.append({
                'link': link,
                'severity': f'{severity*100:.1f}%'
            })
            
            self.active_chaos_events[f'{link}_intermittent'] = {
                'type': 'intermittent',
                'severity': severity,
                'start_time': time.time(),
                'duration': duration
            }
        
        return {
            'type': 'intermittent_issues',
            'affected_links': affected_links,
            'description': f'Intermittent issues on {len(affected_links)} links'
        }
    
    def _inject_congestion_storm(self) -> Dict[str, Any]:
        """Create a sudden spike in traffic causing congestion"""
        all_links = self.fabric_manager.get_all_links()
        if not all_links:
            return {'error': 'No links available'}
        
        # Affect 20-50% of links
        num_affected = max(1, int(len(all_links) * random.uniform(0.2, 0.5)))
        target_links = random.sample(all_links, num_affected)
        
        affected_links = []
        for link in target_links:
            # Increase utilization dramatically
            current_util = self.fabric_manager.get_link_utilization(link)
            new_util = min(0.95, current_util + random.uniform(0.3, 0.6))
            
            self.fabric_manager.set_link_utilization(link, new_util)
            self.telemetry_generator.inject_congestion_event(
                link, new_util - current_util, 180
            )
            
            affected_links.append({
                'link': link,
                'utilization_increase': f'{(new_util - current_util)*100:.1f}%'
            })
        
        return {
            'type': 'congestion_storm',
            'affected_links': affected_links,
            'description': f'Traffic spike affecting {len(affected_links)} links'
        }
    
    def _inject_thermal_event(self) -> Dict[str, Any]:
        """Simulate thermal issues affecting performance"""
        all_links = self.fabric_manager.get_all_links()
        if not all_links:
            return {'error': 'No links available'}
        
        # Choose links that might be physically close (same switch connections)
        target_link = random.choice(all_links)
        
        # Thermal events cause moderate degradation
        severity = random.uniform(0.3, 0.6)
        duration = random.randint(300, 600)  # 5-10 minutes (longer for thermal)
        
        self.fabric_manager.degrade_link(target_link, 1.0 - severity)
        self.telemetry_generator.inject_degradation_event(
            target_link, severity, duration
        )
        
        # Also affect nearby links slightly
        nearby_links = self._find_nearby_links(target_link)
        for nearby_link in nearby_links[:2]:  # Affect up to 2 nearby links
            minor_severity = severity * 0.5
            self.telemetry_generator.inject_degradation_event(
                nearby_link, minor_severity, duration * 0.7
            )
        
        return {
            'type': 'thermal_event',
            'primary_target': target_link,
            'affected_nearby': len(nearby_links),
            'severity': f'{severity*100:.1f}%',
            'duration': f'{duration}s',
            'description': f'Thermal event affecting {target_link} and {len(nearby_links)} nearby links'
        }
    
    def _inject_cascade_failure(self) -> Dict[str, Any]:
        """Simulate a cascading failure scenario"""
        all_links = self.fabric_manager.get_all_links()
        if len(all_links) < 3:
            return {'error': 'Need at least 3 links for cascade failure'}
        
        # Start with one critical failure
        initial_target = random.choice(all_links)
        self.fabric_manager.degrade_link(initial_target, 0.1)  # 90% degradation
        
        # This will cause rerouting, potentially overloading other links
        cascade_targets = []
        remaining_links = [l for l in all_links if l != initial_target]
        
        # Gradually affect other links due to increased load
        for i in range(min(3, len(remaining_links))):
            target = random.choice(remaining_links)
            remaining_links.remove(target)
            
            # Progressive degradation
            delay = i * 30  # 30-second intervals
            severity = 0.4 + (i * 0.1)  # Increasing severity
            
            # In a real implementation, you'd schedule these with delays
            self.fabric_manager.degrade_link(target, 1.0 - severity)
            cascade_targets.append({
                'link': target,
                'delay': f'{delay}s',
                'severity': f'{severity*100:.1f}%'
            })
        
        return {
            'type': 'cascade_failure',
            'initial_failure': initial_target,
            'cascade_targets': cascade_targets,
            'description': f'Cascade failure starting with {initial_target}, affecting {len(cascade_targets)} additional links'
        }
    
    def _find_nearby_links(self, target_link: str) -> List[str]:
        """Find links that might be physically nearby (same nodes)"""
        if '-' not in target_link:
            return []
        
        # Parse target link to find connected nodes
        parts = target_link.split('-', 1)
        node1, node2 = parts[0], parts[1]
        
        # Find other links connected to the same nodes
        nearby_links = []
        all_links = self.fabric_manager.get_all_links()
        
        for link in all_links:
            if link == target_link:
                continue
            
            if '-' in link:
                link_parts = link.split('-', 1)
                link_node1, link_node2 = link_parts[0], link_parts[1]
                
                # Same nodes involved = nearby
                if (link_node1 in [node1, node2]) or (link_node2 in [node1, node2]):
                    nearby_links.append(link)
        
        return nearby_links
    
    def get_active_events(self) -> Dict[str, Any]:
        """Get currently active chaos events"""
        current_time = time.time()
        active_events = {}
        
        for event_id, event_data in self.active_chaos_events.items():
            elapsed_time = current_time - event_data['start_time']
            remaining_time = event_data['duration'] - elapsed_time
            
            if remaining_time > 0:
                active_events[event_id] = {
                    **event_data,
                    'elapsed': elapsed_time,
                    'remaining': remaining_time
                }
        
        # Clean up expired events
        self.active_chaos_events = active_events
        
        return active_events
    
    def stop_all_chaos(self):
        """Stop all active chaos events"""
        self.active_chaos_events.clear()
        
        # Reset all links to healthy state
        for link_id in self.fabric_manager.get_all_links():
            self.fabric_manager.update_link_health(link_id, 1.0)
        
        return {'message': 'All chaos events stopped, links reset to healthy state'}