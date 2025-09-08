from flask import Blueprint, jsonify, request, current_app
import time
import json

telemetry_bp = Blueprint('telemetry', __name__)

@telemetry_bp.route('/telemetry/current')
def get_current_telemetry():
    """Get current telemetry data for all links"""
    try:
        current_telemetry = current_app.config.get('current_telemetry', {})
        
        if not current_telemetry:
            return jsonify({
                'message': 'No telemetry data available',
                'total_links': 0,
                'telemetry': {}
            })
        
        return jsonify({
            'timestamp': time.time(),
            'total_links': len(current_telemetry),
            'telemetry': current_telemetry
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/link/<link_id>')
def get_link_telemetry(link_id):
    """Get current telemetry for a specific link"""
    try:
        current_telemetry = current_app.config.get('current_telemetry', {})
        
        if link_id not in current_telemetry:
            return jsonify({'error': f'No telemetry data found for link {link_id}'}), 404
        
        telemetry_data = current_telemetry[link_id]
        
        # Add health score calculation
        health_calculator = current_app.config.get('health_calculator')
        if health_calculator:
            health_result = health_calculator.calculate_health_score(telemetry_data)
            telemetry_data['health_details'] = health_result
        
        # Add anomaly information
        anomaly_detector = current_app.config.get('anomaly_detector')
        if anomaly_detector:
            anomaly_score = anomaly_detector.get_anomaly_score(telemetry_data)
            anomaly_explanation = anomaly_detector.get_anomaly_explanation(telemetry_data)
            telemetry_data['anomaly_score'] = anomaly_score
            telemetry_data['anomaly_details'] = anomaly_explanation
        
        return jsonify({
            'link_id': link_id,
            'timestamp': time.time(),
            'data': telemetry_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/alerts')
def get_alerts():
    """Get current alerts"""
    try:
        alerts = current_app.config.get('alerts', [])
        
        # Filter alerts based on query parameters
        time_window = request.args.get('time_window', '300')  # Default 5 minutes
        severity = request.args.get('severity')
        
        try:
            time_window = int(time_window)
        except ValueError:
            time_window = 300
        
        current_time = time.time()
        filtered_alerts = []
        
        for alert in alerts:
            # Time filter
            if time_window > 0 and (current_time - alert.get('timestamp', 0)) > time_window:
                continue
            
            # Severity filter
            if severity and alert.get('severity') != severity:
                continue
            
            filtered_alerts.append(alert)
        
        # Sort by timestamp (most recent first)
        filtered_alerts.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Calculate alert statistics
        alert_stats = {'critical': 0, 'warning': 0, 'info': 0}
        for alert in filtered_alerts:
            alert_severity = alert.get('severity', 'info')
            alert_stats[alert_severity] = alert_stats.get(alert_severity, 0) + 1
        
        return jsonify({
            'total_alerts': len(filtered_alerts),
            'time_window_seconds': time_window,
            'alert_statistics': alert_stats,
            'alerts': filtered_alerts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/health')
def get_health_data():
    """Get health scores for all links"""
    try:
        current_telemetry = current_app.config.get('current_telemetry', {})
        health_calculator = current_app.config.get('health_calculator')
        
        if not current_telemetry:
            return jsonify({
                'message': 'No telemetry data available',
                'total_links': 0,
                'health_data': {}
            })
        
        health_data = {}
        detailed_health = {}
        
        for link_id, telemetry in current_telemetry.items():
            health_indicator = telemetry.get('health_indicator', 1.0)
            health_data[link_id] = health_indicator
            
            # Get detailed health information if calculator available
            if health_calculator:
                try:
                    health_result = health_calculator.calculate_health_score(telemetry)
                    detailed_health[link_id] = health_result
                except Exception as e:
                    print(f"Error calculating health for {link_id}: {e}")
                    detailed_health[link_id] = {
                        'overall_score': health_indicator,
                        'health_category': 'Unknown',
                        'error': str(e)
                    }
        
        # Calculate fleet-wide health statistics
        if health_calculator:
            try:
                fleet_summary = health_calculator.get_fleet_health_summary()
            except Exception as e:
                fleet_summary = {'error': str(e)}
        else:
            # Basic fleet summary without health calculator
            health_values = list(health_data.values())
            if health_values:
                avg_health = sum(health_values) / len(health_values)
                min_health = min(health_values)
                max_health = max(health_values)
            else:
                avg_health = min_health = max_health = 0
            
            fleet_summary = {
                'total_links': len(health_values),
                'average_health': round(avg_health, 3),
                'min_health': round(min_health, 3),
                'max_health': round(max_health, 3)
            }
        
        return jsonify({
            'timestamp': time.time(),
            'fleet_summary': fleet_summary,
            'health_scores': health_data,
            'detailed_health': detailed_health
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/forecast/<link_id>')
def get_link_forecast(link_id):
    """Get forecast for a specific link"""
    try:
        forecaster = current_app.config.get('forecaster')
        if not forecaster:
            return jsonify({'error': 'Forecaster not initialized'}), 500
        
        horizon = request.args.get('horizon', 10)
        try:
            horizon = int(horizon)
            if horizon < 1 or horizon > 50:
                horizon = 10
        except ValueError:
            horizon = 10
        
        forecast = forecaster.forecast_link_performance(link_id, horizon)
        
        return jsonify({
            'link_id': link_id,
            'forecast_horizon': horizon,
            'timestamp': time.time(),
            'forecast': forecast
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/forecast/fleet')
def get_fleet_forecast():
    """Get fleet-wide forecast summary"""
    try:
        forecaster = current_app.config.get('forecaster')
        if not forecaster:
            return jsonify({'error': 'Forecaster not initialized'}), 500
        
        fleet_summary = forecaster.get_fleet_forecast_summary()
        
        return jsonify({
            'timestamp': time.time(),
            'fleet_forecast': fleet_summary
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/chaos/inject', methods=['POST'])
def inject_chaos():
    """Inject chaos events for testing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        chaos_type = data.get('type')
        if not chaos_type:
            return jsonify({'status': 'error', 'message': 'Chaos type not specified'}), 400
        
        chaos_engine = current_app.config.get('chaos_engine')
        if not chaos_engine:
            return jsonify({'status': 'error', 'message': 'Chaos engine not initialized'}), 500
        
        valid_chaos_types = [
            'link_degradation', 'sudden_failure', 'intermittent_issues',
            'congestion_storm', 'thermal_event', 'cascade_failure'
        ]
        
        if chaos_type not in valid_chaos_types:
            return jsonify({
                'status': 'error', 
                'message': f'Invalid chaos type. Valid types: {valid_chaos_types}'
            }), 400
        
        result = chaos_engine.inject_chaos(chaos_type)
        
        return jsonify({
            'status': 'success',
            'message': f"Injected {chaos_type} chaos event",
            'details': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@telemetry_bp.route('/telemetry/chaos/active')
def get_active_chaos():
    """Get active chaos events"""
    try:
        chaos_engine = current_app.config.get('chaos_engine')
        if not chaos_engine:
            return jsonify({'active_events': {}, 'total_events': 0})
        
        active_events = chaos_engine.get_active_events()
        return jsonify({
            'timestamp': time.time(),
            'total_events': len(active_events),
            'active_events': active_events
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@telemetry_bp.route('/telemetry/chaos/stop', methods=['POST'])
def stop_chaos():
    """Stop all chaos events"""
    try:
        chaos_engine = current_app.config.get('chaos_engine')
        if not chaos_engine:
            return jsonify({'status': 'error', 'message': 'Chaos engine not initialized'}), 500
        
        result = chaos_engine.stop_all_chaos()
        return jsonify({'status': 'success', 'message': result['message']})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@telemetry_bp.route('/telemetry/statistics')
def get_telemetry_statistics():
    """Get telemetry statistics and trends"""
    try:
        current_telemetry = current_app.config.get('current_telemetry', {})
        
        if not current_telemetry:
            return jsonify({
                'message': 'No telemetry data available',
                'statistics': {}
            })
        
        # Calculate statistics
        latencies = []
        utilizations = []
        temperatures = []
        ber_values = []
        health_scores = []
        
        for telemetry in current_telemetry.values():
            latencies.append(telemetry.get('latency', 0))
            utilizations.append(telemetry.get('utilization', 0))
            temperatures.append(telemetry.get('temperature', 0))
            ber_values.append(telemetry.get('ber', 0))
            health_scores.append(telemetry.get('health_indicator', 1.0))
        
        import numpy as np
        
        statistics = {
            'latency': {
                'mean': round(np.mean(latencies), 3),
                'std': round(np.std(latencies), 3),
                'min': round(np.min(latencies), 3),
                'max': round(np.max(latencies), 3),
                'p95': round(np.percentile(latencies, 95), 3) if latencies else 0
            },
            'utilization': {
                'mean': round(np.mean(utilizations), 3),
                'std': round(np.std(utilizations), 3),
                'min': round(np.min(utilizations), 3),
                'max': round(np.max(utilizations), 3),
                'p95': round(np.percentile(utilizations, 95), 3) if utilizations else 0
            },
            'temperature': {
                'mean': round(np.mean(temperatures), 3),
                'std': round(np.std(temperatures), 3),
                'min': round(np.min(temperatures), 3),
                'max': round(np.max(temperatures), 3),
                'p95': round(np.percentile(temperatures, 95), 3) if temperatures else 0
            },
            'health': {
                'mean': round(np.mean(health_scores), 3),
                'std': round(np.std(health_scores), 3),
                'min': round(np.min(health_scores), 3),
                'max': round(np.max(health_scores), 3)
            }
        }
        
        return jsonify({
            'timestamp': time.time(),
            'total_links': len(current_telemetry),
            'statistics': statistics
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500