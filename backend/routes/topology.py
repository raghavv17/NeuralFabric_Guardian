
import json



# topology.py — robust /topology/init handler (replace existing)

from flask import Blueprint, request, jsonify, current_app
import importlib, time, threading, traceback

topology_bp = Blueprint('topology', __name__)

@topology_bp.route('/topology/init', methods=['POST'])
def initialize_topology():
    try:
        data = request.get_json() or {}
        num_gpus = data.get('num_gpus', 8)
        num_switches = data.get('num_switches', 4)
        interconnect_types = data.get('interconnect_types', ['PCIe', 'NVLink', 'UALink'])

        # basic validation (optional)
        if not (2 <= num_gpus <= 64):
            return jsonify({'status': 'error', 'message': 'num_gpus must be between 2 and 64'}), 400
        if not (1 <= num_switches <= 32):
            return jsonify({'status': 'error', 'message': 'num_switches must be between 1 and 32'}), 400

        # Import main app module to access module-level globals
        main_app = importlib.import_module('app')

        # Safely check or create commonly-used globals on the app module
        # so we don't fail if the attribute was never defined.
        if not hasattr(main_app, '_current_telemetry'):
            main_app._current_telemetry = {}
        if not hasattr(main_app, 'alerts'):
            # prefer a list/deque depending on your app; list is safe default
            main_app.alerts = []
        if not hasattr(main_app, 'routing_decisions'):
            main_app.routing_decisions = []
        if not hasattr(main_app, 'system_running'):
            main_app.system_running = False

        # remember running state to decide whether to restart later
        was_running = bool(getattr(main_app, 'system_running', False))

        # if telemetry is running, pause it to avoid racing with reinit
        if was_running:
            main_app.system_running = False
            # give background thread a moment to exit or pause
            time.sleep(0.4)

        # Acquire or create fabric_manager from current_app or app module
        fabric_manager = current_app.config.get('fabric_manager') or getattr(main_app, 'fabric_manager', None)
        if not fabric_manager:
            # If the project exposes a factory or creator, call it; otherwise error
            return jsonify({'status': 'error', 'message': 'Fabric manager not initialized'}), 500

        # Recreate the fabric topology (use the API your fabric_manager exposes)
        # Many fabric managers offer something like create_fabric_topology(...) or load_default_topology()
        if hasattr(fabric_manager, 'create_fabric_topology'):
            fabric_manager.create_fabric_topology(num_gpus, num_switches, interconnect_types)
        elif hasattr(fabric_manager, 'init_default_topology'):
            fabric_manager.init_default_topology()
        else:
            # fallback: try to reset nodes/edges if that API exists
            if hasattr(fabric_manager, 'reset'):
                fabric_manager.reset()
            # else continue — topology endpoint may still return something

        # Reinitialize TelemetryGenerator and ChaosEngine with safe import fallbacks
        telemetry_generator = None
        chaos_engine = None
        try:
            # adjust module path according to your project structure
            from utils.telemetry_generator import TelemetryGenerator
            from utils.chaos_mode import ChaosEngine
            telemetry_generator = TelemetryGenerator(fabric_manager)
            chaos_engine = ChaosEngine(fabric_manager, telemetry_generator)
        except Exception:
            try:
                from telemetry_generator import TelemetryGenerator
                from chaos_mode import ChaosEngine
                telemetry_generator = TelemetryGenerator(fabric_manager)
                chaos_engine = ChaosEngine(fabric_manager, telemetry_generator)
            except Exception:
                # Could not import; continue but warn
                traceback.print_exc()
                telemetry_generator = None
                chaos_engine = None

        # Update flask current_app config and main_app module globals so other parts see new instances
        if telemetry_generator:
            current_app.config['telemetry_generator'] = telemetry_generator
            setattr(main_app, 'telemetry_generator', telemetry_generator)
        if chaos_engine:
            current_app.config['chaos_engine'] = chaos_engine
            setattr(main_app, 'chaos_engine', chaos_engine)

        current_app.config['fabric_manager'] = fabric_manager
        setattr(main_app, 'fabric_manager', fabric_manager)

        # Clear alerts/decisions/telemetry so UI shows a fresh state
        main_app.alerts.clear() if hasattr(main_app.alerts, 'clear') else main_app.alerts.__init__()
        main_app.routing_decisions.clear() if hasattr(main_app.routing_decisions, 'clear') else main_app.routing_decisions.__init__()
        if isinstance(main_app._current_telemetry, dict):
            main_app._current_telemetry.clear()
        else:
            main_app._current_telemetry = {}

        current_app.config['alerts'] = main_app.alerts
        current_app.config['routing_decisions'] = main_app.routing_decisions
        current_app.config['_current_telemetry'] = main_app._current_telemetry

        # If telemetry was running before, restart it now (only if telemetry_worker exists)
        if was_running:
            main_app.system_running = True
            if hasattr(main_app, 'telemetry_worker') and callable(getattr(main_app, 'telemetry_worker')):
                # spawn as daemon so it won't block shutdown
                t = threading.Thread(target=main_app.telemetry_worker, daemon=True)
                t.start()

        # Return a summary for the frontend to use
        total_links = 0
        try:
            if hasattr(fabric_manager, 'get_all_links'):
                total_links = len(fabric_manager.get_all_links())
        except Exception:
            total_links = 0

        return jsonify({
            'status': 'success',
            'message': 'Topology initialized',
            'details': {
                'num_gpus': num_gpus,
                'num_switches': num_switches,
                'interconnect_types': interconnect_types,
                'total_links': total_links
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@topology_bp.route('/topology')
def get_topology():
    """Get current fabric topology"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
            
        topology_data = fabric_manager.get_topology_json()
        
        # Add health information to edges
        current_telemetry = current_app.config.get('current_telemetry', {})
        for edge in topology_data.get('edges', []):
            link_id = edge.get('id') or edge.get('data', {}).get('link_id')
            if link_id and link_id in current_telemetry:
                telemetry = current_telemetry[link_id]
                edge['data']['current_health'] = telemetry.get('health_indicator', 1.0)
                edge['data']['current_latency'] = telemetry.get('latency', 0)
                edge['data']['current_utilization'] = telemetry.get('utilization', 0)
                edge['data']['current_temperature'] = telemetry.get('temperature', 25)
        
        return jsonify(topology_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# topology.py — replace existing /topology/init handler with this


@topology_bp.route('/topology/links')
def get_all_links():
    """Get all links in the topology"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
        
        links = fabric_manager.get_all_links()
        
        # Add detailed information for each link
        link_details = {}
        current_telemetry = current_app.config.get('current_telemetry', {})
        
        for link_id in links:
            link_info = {'link_id': link_id}
            
            # Get topology information
            topology = fabric_manager.topology
            if '-' in link_id:
                parts = link_id.split('-', 1)
                node1, node2 = parts[0], parts[1]
                
                if topology.has_edge(node1, node2):
                    edge_data = topology[node1][node2]
                    link_info.update({
                        'type': edge_data.get('type', 'Unknown'),
                        'bandwidth_gbps': edge_data.get('bandwidth_gbps', 0),
                        'base_latency_us': edge_data.get('base_latency_us', 0),
                        'nodes': [node1, node2]
                    })
            
            # Add current telemetry if available
            if link_id in current_telemetry:
                telemetry = current_telemetry[link_id]
                link_info.update({
                    'current_latency': telemetry.get('latency', 0),
                    'current_utilization': telemetry.get('utilization', 0),
                    'current_temperature': telemetry.get('temperature', 0),
                    'health_indicator': telemetry.get('health_indicator', 1.0),
                    'last_updated': telemetry.get('timestamp', 0)
                })
            
            link_details[link_id] = link_info
        
        return jsonify({
            'total_links': len(links),
            'links': link_details
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@topology_bp.route('/topology/jobs')
def get_topology_jobs():
    """Get all jobs in the topology"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
        
        jobs = list(fabric_manager.jobs.values())
        
        # Add route metrics for each job
        routing_optimizer = current_app.config.get('routing_optimizer')
        if routing_optimizer:
            for job in jobs:
                if 'route' in job and job['route']:
                    metrics = routing_optimizer.calculate_route_metrics(
                        fabric_manager.topology, job['route']
                    )
                    job['route_metrics'] = metrics
        
        return jsonify({
            'total_jobs': len(jobs),
            'jobs': jobs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@topology_bp.route('/topology/stats')
def get_topology_stats():
    """Get topology statistics"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
        
        topology = fabric_manager.topology
        
        # Count different node types
        gpu_nodes = [n for n in topology.nodes() if fabric_manager.node_types.get(n) == 'GPU']
        switch_nodes = [n for n in topology.nodes() if fabric_manager.node_types.get(n) == 'Switch']
        
        # Count different link types
        link_types = {}
        for edge in topology.edges(data=True):
            link_type = edge[2].get('type', 'Unknown')
            link_types[link_type] = link_types.get(link_type, 0) + 1
        
        # Health statistics
        current_telemetry = current_app.config.get('current_telemetry', {})
        health_stats = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0, 'critical': 0}
        
        for telemetry in current_telemetry.values():
            health = telemetry.get('health_indicator', 1.0)
            if health >= 0.9:
                health_stats['excellent'] += 1
            elif health >= 0.7:
                health_stats['good'] += 1
            elif health >= 0.5:
                health_stats['fair'] += 1
            elif health >= 0.3:
                health_stats['poor'] += 1
            else:
                health_stats['critical'] += 1
        
        return jsonify({
            'nodes': {
                'total': topology.number_of_nodes(),
                'gpus': len(gpu_nodes),
                'switches': len(switch_nodes)
            },
            'links': {
                'total': topology.number_of_edges(),
                'by_type': link_types
            },
            'health_distribution': health_stats,
            'jobs': {
                'total': len(fabric_manager.jobs),
                'active': len([j for j in fabric_manager.jobs.values() if j.get('route')])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@topology_bp.route('/topology/export')
def export_topology():
    """Export topology configuration"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
        
        topology_data = fabric_manager.get_topology_json()
        
        # Add metadata
        export_data = {
            'metadata': {
                'export_timestamp': request.args.get('timestamp', 'now'),
                'system_name': 'NeuralFabric Guardian',
                'version': '1.0'
            },
            'topology': topology_data
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@topology_bp.route('/topology/load', methods=['POST'])
def load_topology():
    """Load topology from JSON data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # This would require implementing a load function in FabricManager
        # For now, return not implemented
        return jsonify({
            'status': 'error', 
            'message': 'Load topology functionality not yet implemented'
        }), 501
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500