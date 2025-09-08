from flask import Blueprint, jsonify, request, current_app
import time

routing_bp = Blueprint('routing', __name__)

@routing_bp.route('/routing/decisions')
def get_routing_decisions():
    """Get recent routing decisions"""
    try:
        routing_decisions = current_app.config.get('routing_decisions', [])
        
        # Filter decisions based on query parameters
        limit = request.args.get('limit', 100)
        time_window = request.args.get('time_window')  # seconds
        
        try:
            limit = int(limit)
            if limit < 1 or limit > 1000:
                limit = 100
        except ValueError:
            limit = 100
        
        filtered_decisions = routing_decisions.copy()
        
        # Time filter
        if time_window:
            try:
                time_window = int(time_window)
                current_time = time.time()
                filtered_decisions = [
                    decision for decision in filtered_decisions
                    if (current_time - decision.get('timestamp', 0)) <= time_window
                ]
            except ValueError:
                pass
        
        # Sort by timestamp (most recent first)
        filtered_decisions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Apply limit
        filtered_decisions = filtered_decisions[:limit]
        
        return jsonify({
            'total_decisions': len(filtered_decisions),
            'routing_decisions': filtered_decisions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/optimize', methods=['POST'])
def optimize_route():
    """Find optimal route between two nodes"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        source = data.get('source')
        destination = data.get('destination')
        optimize_for = data.get('optimize_for', 'health')
        
        if not source or not destination:
            return jsonify({'error': 'Source and destination must be specified'}), 400
        
        valid_optimizations = ['health', 'latency', 'energy', 'balanced']
        if optimize_for not in valid_optimizations:
            return jsonify({
                'error': f'Invalid optimization type. Valid options: {valid_optimizations}'
            }), 400
        
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        if not fabric_manager or not routing_optimizer:
            return jsonify({'error': 'Routing components not initialized'}), 500
        
        # Check if nodes exist
        if not fabric_manager.topology.has_node(source):
            return jsonify({'error': f'Source node {source} not found'}), 404
        
        if not fabric_manager.topology.has_node(destination):
            return jsonify({'error': f'Destination node {destination} not found'}), 404
        
        # Find optimal route
        optimal_route = routing_optimizer.find_optimal_route(
            fabric_manager.topology, source, destination, optimize_for
        )
        
        if not optimal_route:
            return jsonify({
                'error': f'No route found from {source} to {destination}'
            }), 404
        
        # Calculate route metrics
        route_metrics = routing_optimizer.calculate_route_metrics(
            fabric_manager.topology, optimal_route
        )
        
        # Find alternative routes
        alternatives = routing_optimizer.find_alternative_routes(
            fabric_manager.topology, source, destination, k=3
        )
        
        return jsonify({
            'source': source,
            'destination': destination,
            'optimization_type': optimize_for,
            'optimal_route': optimal_route,
            'route_metrics': route_metrics,
            'alternative_routes': alternatives[:3],  # Top 3 alternatives
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/job/<job_id>/reroute', methods=['POST'])
def reroute_job(job_id):
    """Reroute a specific job"""
    try:
        data = request.get_json() or {}
        force_reroute = data.get('force', False)
        optimize_for = data.get('optimize_for', 'health')
        
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        if not fabric_manager or not routing_optimizer:
            return jsonify({'error': 'Routing components not initialized'}), 500
        
        # Check if job exists
        if job_id not in fabric_manager.jobs:
            return jsonify({'error': f'Job {job_id} not found'}), 404
        
        job = fabric_manager.jobs[job_id]
        current_route = job['route']
        
        # Check if rerouting is needed (unless forced)
        if not force_reroute:
            should_reroute = routing_optimizer.should_reroute(
                fabric_manager.topology, current_route, threshold=0.6
            )
            if not should_reroute:
                return jsonify({
                    'job_id': job_id,
                    'message': 'Current route is healthy, rerouting not needed',
                    'current_route': current_route,
                    'rerouted': False
                })
        
        # Find new optimal route
        new_route = routing_optimizer.find_optimal_route(
            fabric_manager.topology,
            job['source'],
            job['destination'],
            optimize_for
        )
        
        if not new_route:
            return jsonify({
                'error': f'No alternative route found for job {job_id}'
            }), 404
        
        if new_route == current_route and not force_reroute:
            return jsonify({
                'job_id': job_id,
                'message': 'Current route is already optimal',
                'current_route': current_route,
                'rerouted': False
            })
        
        # Execute rerouting
        success = fabric_manager.reroute_job(job_id, new_route)
        
        if not success:
            return jsonify({'error': f'Failed to reroute job {job_id}'}), 500
        
        # Calculate metrics for both routes
        old_metrics = routing_optimizer.calculate_route_metrics(
            fabric_manager.topology, current_route
        )
        new_metrics = routing_optimizer.calculate_route_metrics(
            fabric_manager.topology, new_route
        )
        
        # Log the decision
        routing_decisions = current_app.config.get('routing_decisions', [])
        decision = {
            'timestamp': time.time(),
            'job_id': job_id,
            'old_route': current_route,
            'new_route': new_route,
            'reason': f'Manual reroute (optimize_for: {optimize_for})',
            'old_metrics': old_metrics,
            'new_metrics': new_metrics,
            'forced': force_reroute
        }
        routing_decisions.append(decision)
        
        return jsonify({
            'job_id': job_id,
            'message': 'Job successfully rerouted',
            'old_route': current_route,
            'new_route': new_route,
            'old_metrics': old_metrics,
            'new_metrics': new_metrics,
            'rerouted': True,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/alternatives/<source>/<destination>')
def get_alternative_routes(source, destination):
    """Get alternative routes between two nodes"""
    try:
        k = request.args.get('k', 3)
        try:
            k = int(k)
            if k < 1 or k > 10:
                k = 3
        except ValueError:
            k = 3
        
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        if not fabric_manager or not routing_optimizer:
            return jsonify({'error': 'Routing components not initialized'}), 500
        
        # Check if nodes exist
        if not fabric_manager.topology.has_node(source):
            return jsonify({'error': f'Source node {source} not found'}), 404
        
        if not fabric_manager.topology.has_node(destination):
            return jsonify({'error': f'Destination node {destination} not found'}), 404
        
        # Find alternative routes
        alternatives = routing_optimizer.find_alternative_routes(
            fabric_manager.topology, source, destination, k=k
        )
        
        return jsonify({
            'source': source,
            'destination': destination,
            'requested_alternatives': k,
            'found_alternatives': len(alternatives),
            'routes': alternatives,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/analyze', methods=['POST'])
def analyze_route():
    """Analyze a specific route for performance and health"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        route = data.get('route')
        if not route or not isinstance(route, list) or len(route) < 2:
            return jsonify({'error': 'Valid route must be provided as list of nodes'}), 400
        
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        if not fabric_manager or not routing_optimizer:
            return jsonify({'error': 'Routing components not initialized'}), 500
        
        # Validate route nodes exist
        for node in route:
            if not fabric_manager.topology.has_node(node):
                return jsonify({'error': f'Node {node} not found in topology'}), 404
        
        # Validate route connectivity
        for i in range(len(route) - 1):
            if not fabric_manager.topology.has_edge(route[i], route[i + 1]):
                return jsonify({
                    'error': f'No connection between {route[i]} and {route[i + 1]}'
                }), 400
        
        # Calculate route metrics
        metrics = routing_optimizer.calculate_route_metrics(fabric_manager.topology, route)
        
        # Check if rerouting is recommended
        should_reroute = routing_optimizer.should_reroute(
            fabric_manager.topology, route, threshold=0.6
        )
        
        # Get affected jobs
        affected_jobs = []
        for job_id, job in fabric_manager.jobs.items():
            if job.get('route') == route:
                affected_jobs.append({
                    'job_id': job_id,
                    'type': job.get('type'),
                    'priority': job.get('priority')
                })
        
        # Analyze individual links
        link_analysis = []
        for i in range(len(route) - 1):
            node1, node2 = route[i], route[i + 1]
            edge_data = fabric_manager.topology[node1][node2]
            link_id = edge_data.get('link_id', f'{node1}-{node2}')
            
            # Get current telemetry if available
            current_telemetry = current_app.config.get('current_telemetry', {})
            link_telemetry = current_telemetry.get(link_id, {})
            
            link_info = {
                'link_id': link_id,
                'nodes': [node1, node2],
                'type': edge_data.get('type'),
                'health_score': edge_data.get('health_score', 1.0),
                'base_latency': edge_data.get('base_latency_us', 0),
                'bandwidth': edge_data.get('bandwidth_gbps', 0),
                'current_utilization': link_telemetry.get('utilization', 0),
                'current_latency': link_telemetry.get('latency', 0),
                'current_temperature': link_telemetry.get('temperature', 0)
            }
            link_analysis.append(link_info)
        
        return jsonify({
            'route': route,
            'metrics': metrics,
            'should_reroute': should_reroute,
            'affected_jobs': affected_jobs,
            'link_analysis': link_analysis,
            'recommendations': {
                'reroute_recommended': should_reroute,
                'bottleneck_links': [
                    link for link in link_analysis 
                    if link.get('health_score', 1.0) < 0.5
                ],
                'high_utilization_links': [
                    link for link in link_analysis 
                    if link.get('current_utilization', 0) > 0.8
                ]
            },
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/jobs')
def get_routing_jobs():
    """Get all jobs and their routing information"""
    try:
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        if not fabric_manager:
            return jsonify({'error': 'Fabric manager not initialized'}), 500
        
        jobs_info = []
        
        for job_id, job in fabric_manager.jobs.items():
            job_info = job.copy()
            
            # Calculate route metrics if optimizer available
            if routing_optimizer and job.get('route'):
                try:
                    route_metrics = routing_optimizer.calculate_route_metrics(
                        fabric_manager.topology, job['route']
                    )
                    job_info['route_metrics'] = route_metrics
                    
                    # Check if rerouting is recommended
                    should_reroute = routing_optimizer.should_reroute(
                        fabric_manager.topology, job['route'], threshold=0.6
                    )
                    job_info['reroute_recommended'] = should_reroute
                except Exception as e:
                    job_info['route_error'] = str(e)
            
            jobs_info.append(job_info)
        
        return jsonify({
            'total_jobs': len(jobs_info),
            'jobs': jobs_info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routing_bp.route('/routing/statistics')
def get_routing_statistics():
    """Get routing performance statistics"""
    try:
        routing_decisions = current_app.config.get('routing_decisions', [])
        fabric_manager = current_app.config.get('fabric_manager')
        routing_optimizer = current_app.config.get('routing_optimizer')
        
        # Basic statistics
        stats = {
            'total_rerouting_decisions': len(routing_decisions),
            'recent_decisions': len([
                d for d in routing_decisions 
                if time.time() - d.get('timestamp', 0) < 3600  # Last hour
            ])
        }
        
        # Job statistics
        if fabric_manager:
            total_jobs = len(fabric_manager.jobs)
            healthy_routes = 0
            
            if routing_optimizer:
                for job in fabric_manager.jobs.values():
                    if job.get('route'):
                        should_reroute = routing_optimizer.should_reroute(
                            fabric_manager.topology, job['route'], threshold=0.6
                        )
                        if not should_reroute:
                            healthy_routes += 1
            
            stats.update({
                'total_jobs': total_jobs,
                'healthy_routes': healthy_routes,
                'routes_needing_attention': total_jobs - healthy_routes
            })
        
        # Decision analysis
        if routing_decisions:
            recent_decisions = [
                d for d in routing_decisions 
                if time.time() - d.get('timestamp', 0) < 86400  # Last 24 hours
            ]
            
            reasons = {}
            for decision in recent_decisions:
                reason = decision.get('reason', 'Unknown')
                # Simplify reason for grouping
                if 'health degraded' in reason:
                    reason_key = 'Health Degradation'
                elif 'Manual reroute' in reason:
                    reason_key = 'Manual Override'
                else:
                    reason_key = 'Other'
                
                reasons[reason_key] = reasons.get(reason_key, 0) + 1
            
            stats['rerouting_reasons'] = reasons
        
        return jsonify({
            'timestamp': time.time(),
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500