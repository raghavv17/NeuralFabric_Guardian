from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import sys
import threading
import time
from datetime import datetime
import random


# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules (corrected paths - they're in the same directory)
from services.fabric import FabricManager
from services.optimizer import RoutingOptimizer
from models.anomaly import AnomalyDetector
from models.forecasting import LinkPerformanceForecaster
from models.health_score import HealthScoreCalculator
from utils.telemetry_generator import TelemetryGenerator
from utils.chaos_mode import ChaosEngine

# Import routes
from routes.topology import topology_bp
from routes.telemetry import telemetry_bp
from routes.routing import routing_bp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static")
)

CORS(app)

# Global instances
fabric_manager = FabricManager()
routing_optimizer = RoutingOptimizer()
anomaly_detector = AnomalyDetector()
forecaster = LinkPerformanceForecaster()
health_calculator = HealthScoreCalculator()
telemetry_generator = None
chaos_engine = None

# System state
system_running = False
telemetry_thread = None
alerts = []
routing_decisions = []
current_telemetry = {}


def initialize_system():
    """Initialize the system with default topology"""
    global telemetry_generator, chaos_engine
    
    try:
        # Create default topology
        fabric_manager.create_fabric_topology(
            num_gpus=8,
            num_switches=4,
            interconnect_types=['PCIe', 'NVLink', 'UALink']
        )
        
        # Initialize telemetry generator
        telemetry_generator = TelemetryGenerator(fabric_manager)
        
        # Initialize chaos engine
        chaos_engine = ChaosEngine(fabric_manager, telemetry_generator)
        
        print("System initialized successfully")
        
    except Exception as e:
        print(f"Error initializing system: {e}")

def telemetry_worker():
    """Background worker for telemetry generation and processing"""
    global system_running, current_telemetry, alerts, routing_decisions, app
    
    while system_running:
        try:
            if telemetry_generator is None:
                print("Telemetry generator not initialized")
                time.sleep(1)
                continue
                
            # Generate telemetry batch
            telemetry_batch = telemetry_generator.generate_telemetry_batch()
            
            # Process each link's telemetry and add health scores
            processed_telemetry = {}
            
            for link_id, telemetry_data in telemetry_batch.items():
                # Add timestamp if missing
                if 'timestamp' not in telemetry_data:
                    telemetry_data['timestamp'] = time.time()
                
                # Add link_id to telemetry data for health calculator
                telemetry_data['link_id'] = link_id
                
                # Anomaly detection
                is_anomaly = anomaly_detector.detect_anomaly(telemetry_data)
                
                # Calculate health score
                health_result = health_calculator.calculate_health_score(telemetry_data)
                health_score = health_result['overall_score']
                
                # Add health score to telemetry data
                telemetry_data['health_indicator'] = health_score
                telemetry_data['health_category'] = health_result['health_category']
                telemetry_data['is_anomaly'] = is_anomaly
                
                processed_telemetry[link_id] = telemetry_data
                
                # Add forecasting data
                forecaster.add_telemetry_data(link_id, telemetry_data)
                
                if is_anomaly:
                    # Get detailed anomaly explanation
                    anomaly_explanation = anomaly_detector.get_anomaly_explanation(telemetry_data)
                    
                    # Create alert
                    alert = {
                        'timestamp': time.time(),
                        'link_id': link_id,
                        'message': f"Anomaly detected on {link_id}: Latency={telemetry_data.get('latency', 0):.2f}μs, Util={telemetry_data.get('utilization', 0):.2f}%, Health={health_score:.2f}",
                        'severity': 'critical' if health_score < 0.3 else ('warning' if health_score < 0.7 else 'info'),
                        'health_score': health_score,
                        'details': health_result,
                        'anomaly_details': anomaly_explanation
                    }
                    alerts.append(alert)
                    
                    # Keep only last 50 alerts
                    if len(alerts) > 50:
                        alerts.pop(0)
                    
                    print(f"Alert created for {link_id}: {alert['message']}")
                
                # Update fabric health
                fabric_manager.update_link_health(link_id, health_score)
                
                # Check if rerouting is needed
                affected_jobs = fabric_manager.get_jobs_on_link(link_id)
                
                for job in affected_jobs:
                    current_route = job['route']
                    should_reroute = routing_optimizer.should_reroute(
                        fabric_manager.topology, current_route, threshold=0.6
                    )
                    
                    if should_reroute:
                        # Find new route
                        new_route = routing_optimizer.find_optimal_route(
                            fabric_manager.topology, 
                            job['source'], 
                            job['destination'],
                            optimize_for='health'
                        )
                        
                        if new_route and new_route != current_route:
                            # Execute rerouting
                            success = fabric_manager.reroute_job(job['id'], new_route)
                            
                            if success:
                                # Log decision
                                decision = {
                                    'timestamp': time.time(),
                                    'job_id': job['id'],
                                    'old_route': current_route,
                                    'new_route': new_route,
                                    'reason': f"Link {link_id} health degraded to {health_score:.2f}",
                                    'old_metrics': routing_optimizer.calculate_route_metrics(fabric_manager.topology, current_route),
                                    'new_metrics': routing_optimizer.calculate_route_metrics(fabric_manager.topology, new_route)
                                }
                                routing_decisions.append(decision)
                                
                                # Keep only last 100 decisions
                                if len(routing_decisions) > 100:
                                    routing_decisions.pop(0)
            
            # Update global current_telemetry with processed data
            current_telemetry = processed_telemetry
            
            # IMPORTANT: Store in app context for blueprints to access
            with app.app_context():
                app._current_telemetry = processed_telemetry
                app.config['alerts'] = alerts
                app.config['routing_decisions'] = routing_decisions
                app.config['current_telemetry'] = current_telemetry
            
            time.sleep(3)  # Update every 3 seconds
            
        except Exception as e:
            print(f"Error in telemetry worker: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)

# Make global instances available to routes
app.config['fabric_manager'] = fabric_manager
app.config['routing_optimizer'] = routing_optimizer
app.config['anomaly_detector'] = anomaly_detector
app.config['forecaster'] = forecaster
app.config['health_calculator'] = health_calculator
app.config['alerts'] = alerts
app.config['routing_decisions'] = routing_decisions
app.config['current_telemetry'] = current_telemetry

# Store instances in app for blueprint access
app.fabric_manager = fabric_manager
app.routing_optimizer = routing_optimizer
app._current_telemetry = {}

# Register blueprints
app.register_blueprint(topology_bp, url_prefix='/api')
app.register_blueprint(telemetry_bp, url_prefix='/api')
app.register_blueprint(routing_bp, url_prefix='/api')

# Main routes
@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the monitoring system"""
    global system_running, telemetry_thread
    
    try:
        if not system_running:
            system_running = True
            telemetry_thread = threading.Thread(target=telemetry_worker, daemon=True)
            telemetry_thread.start()
            
            return jsonify({'status': 'success', 'message': 'System started'})
        else:
            return jsonify({'status': 'info', 'message': 'System already running'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop the monitoring system"""
    global system_running
    
    try:
        system_running = False
        return jsonify({'status': 'success', 'message': 'System stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/system/status')
def system_status():
    """Get system status"""
    return jsonify({
        'running': system_running,
        'components': {
            'fabric_manager': fabric_manager is not None,
            'telemetry_generator': telemetry_generator is not None,
            'chaos_engine': chaos_engine is not None,
        },
        'statistics': {
            'total_links': len(fabric_manager.get_all_links()) if fabric_manager else 0,
            'active_alerts': len(alerts),
            'routing_decisions': len(routing_decisions)
        }
    })


@app.route('/api/chaos/inject', methods=['POST'])
def inject_chaos():
    """Inject chaos into the system"""
    try:
        data = request.get_json() or {}
        # accept both 'type' and 'chaos_type' keys
        chaos_type = data.get('type') or data.get('chaos_type')

        if not chaos_type:
            return jsonify({'status': 'error', 'message': 'Chaos type is required'})

        if chaos_engine is None:
            return jsonify({'status': 'error', 'message': 'Chaos engine not initialized'})

        # Execute chaos injection
        result = chaos_engine.inject_chaos(chaos_type)

        # If the chaos engine returned an error key -> failure
        if isinstance(result, dict) and result.get('error'):
            return jsonify({
                'status': 'error',
                'message': f'Chaos injection failed: {result.get("error")}',
                'details': result
            }), 400

        # Otherwise assume success and return the result
        return jsonify({
            'status': 'success',
            'message': f'Chaos injection successful: {chaos_type}',
            'details': result
        })

    except Exception as e:
        # Log the exception on server console (helps debugging)
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/topology/health')
def get_topology_health():
    """Get health status for topology visualization"""
    try:
        link_health = {}
        
        # Get current health for each link
        for link_id, telemetry_data in current_telemetry.items():
            health_score = telemetry_data.get('health_indicator', 1.0)
            
            # Categorize health for visualization
            if health_score >= 0.7:
                status = 'healthy'
            elif health_score >= 0.5:
                status = 'warning'
            else:
                status = 'critical'
                
            link_health[link_id] = {
                'score': health_score,
                'status': status,
                'category': telemetry_data.get('health_category', 'excellent')
            }
        
        return jsonify(link_health)
    except Exception as e:
        print(f"Error getting topology health: {e}")
        return jsonify({})

@app.route('/api/kpis')
def get_kpis():
    """Get current system KPIs"""
    try:
        if not current_telemetry:
            # Return default values if no telemetry available
            return jsonify({
                'total_links': 16,
                'healthy_links': 14,
                'health_percentage': 87.5,
                'avg_latency': 6.22,
                'avg_utilization': 0.68,
                'active_alerts': len([a for a in alerts if time.time() - a['timestamp'] < 300])
            })
        
        # Calculate KPIs from current telemetry
        total_links = len(current_telemetry)
        healthy_links = 0
        total_latency = 0
        total_utilization = 0
        
        for telemetry in current_telemetry.values():
            health_indicator = telemetry.get('health_indicator', 1.0)
            if health_indicator > 0.7:
                healthy_links += 1
            total_latency += telemetry.get('latency', 0)
            total_utilization += telemetry.get('utilization', 0)
        
        # Count recent alerts (last 5 minutes)
        current_time = time.time()
        active_alerts_count = len([
            a for a in alerts 
            if (current_time - a['timestamp']) < 300
        ])
        
        avg_latency = total_latency / max(total_links, 1)
        avg_utilization = total_utilization / max(total_links, 1)
        health_percentage = (healthy_links / max(total_links, 1)) * 100
        
        return jsonify({
            'total_links': total_links,
            'healthy_links': healthy_links,
            'health_percentage': round(health_percentage, 1),
            'avg_latency': round(avg_latency, 2),
            'avg_utilization': round(avg_utilization, 3),
            'active_alerts': active_alerts_count
        })
    except Exception as e:
        print(f"Error calculating KPIs: {e}")
        return jsonify({
            'total_links': 0,
            'healthy_links': 0,
            'health_percentage': 0,
            'avg_latency': 0,
            'avg_utilization': 0,
            'active_alerts': 0
        })

# Debug endpoints
@app.route('/api/debug/telemetry')
def debug_telemetry():
    """Debug endpoint to check telemetry data structure"""
    try:
        debug_info = {
            'telemetry_generator_initialized': telemetry_generator is not None,
            'current_telemetry_keys': list(current_telemetry.keys()) if current_telemetry else [],
            'sample_telemetry': {},
            'alerts_count': len(alerts),
            'routing_decisions_count': len(routing_decisions),
            'system_running': system_running
        }
        
        # Get a sample of current telemetry data
        if current_telemetry:
            first_key = list(current_telemetry.keys())[0]
            debug_info['sample_telemetry'] = {
                'link_id': first_key,
                'data': current_telemetry[first_key],
                'data_keys': list(current_telemetry[first_key].keys())
            }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e), 'type': 'debug_endpoint_error'})

@app.route('/api/debug/alerts')
def debug_alerts():
    """Debug alerts specifically"""
    try:
        current_time = time.time()
        return jsonify({
            'total_alerts': len(alerts),
            'recent_alerts': len([a for a in alerts if (current_time - a['timestamp']) < 300]),
            'sample_alerts': alerts[-3:] if alerts else [],
            'system_running': system_running,
            'telemetry_keys': list(current_telemetry.keys()) if current_telemetry else []
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize system
    initialize_system()
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)