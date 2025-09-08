import numpy as np
from typing import Dict, Any, List
import time
import math

class HealthScoreCalculator:
    """Calculates comprehensive health scores for GPU interconnect links"""
    
    def __init__(self):
        # Weight factors for different metrics (should sum to 1.0)
        self.metric_weights = {
            'latency': 0.25,
            'ber': 0.20,
            'utilization': 0.15,
            'temperature': 0.15,
            'crc_errors': 0.15,
            'signal_integrity': 0.10
        }
        
        # Threshold ranges for scoring (lower is better for most metrics)
        self.thresholds = {
            'latency': {  # microseconds
                'excellent': 2.0,
                'good': 5.0,
                'fair': 15.0,
                'poor': 50.0
            },
            'ber': {  # bit error rate
                'excellent': 1e-12,
                'good': 1e-10,
                'fair': 1e-9,
                'poor': 1e-8
            },
            'utilization': {  # 0-1 range, but optimal is around 0.7
                'excellent': 0.7,
                'good': 0.8,
                'fair': 0.9,
                'poor': 0.95
            },
            'temperature': {  # celsius
                'excellent': 50,
                'good': 65,
                'fair': 80,
                'poor': 90
            },
            'crc_errors': {  # errors per second
                'excellent': 1.0,
                'good': 5.0,
                'fair': 20.0,
                'poor': 100.0
            },
            'signal_integrity': {  # 0-1 range, higher is better
                'excellent': 0.9,
                'good': 0.8,
                'fair': 0.6,
                'poor': 0.4
            }
        }
        
        # Historical data for trend analysis
        self.history = {}  # link_id -> list of (timestamp, health_score)
        self.max_history = 100  # Keep last 100 measurements
    
    def calculate_health_score(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive health score from telemetry data
        
        Args:
            telemetry_data: Dictionary containing telemetry metrics
            
        Returns:
            Dictionary with health score and component breakdowns
        """
        link_id = telemetry_data.get('link_id', 'unknown')
        
        # Calculate individual metric scores
        metric_scores = {}
        
        # Latency score (lower is better)
        latency = telemetry_data.get('latency', 0)
        metric_scores['latency'] = self._score_latency(latency)
        
        # BER score (lower is better)
        ber = telemetry_data.get('ber', 0)
        metric_scores['ber'] = self._score_ber(ber)
        
        # Utilization score (optimal around 70%)
        utilization = telemetry_data.get('utilization', 0)
        metric_scores['utilization'] = self._score_utilization(utilization)
        
        # Temperature score (lower is better)
        temperature = telemetry_data.get('temperature', 25)
        metric_scores['temperature'] = self._score_temperature(temperature)
        
        # CRC errors score (lower is better)
        crc_errors = telemetry_data.get('crc_errors', 0)
        metric_scores['crc_errors'] = self._score_crc_errors(crc_errors)
        
        # Signal integrity score (higher is better)
        signal_integrity = telemetry_data.get('signal_integrity', 1.0)
        metric_scores['signal_integrity'] = self._score_signal_integrity(signal_integrity)
        
        # Calculate weighted overall score
        overall_score = sum(
            score * self.metric_weights.get(metric, 0.1)
            for metric, score in metric_scores.items()
        )
        
        # Apply trend analysis
        trend_factor = self._calculate_trend_factor(link_id, overall_score)
        adjusted_score = overall_score * trend_factor
        
        # Clamp to [0, 1] range
        adjusted_score = max(0.0, min(1.0, adjusted_score))
        
        # Store in history
        self._update_history(link_id, adjusted_score)
        
        # Determine health category
        health_category = self._categorize_health(adjusted_score)
        
        return {
            'link_id': link_id,
            'overall_score': round(adjusted_score, 3),
            'health_category': health_category,
            'metric_scores': {k: round(v, 3) for k, v in metric_scores.items()},
            'trend_factor': round(trend_factor, 3),
            'timestamp': telemetry_data.get('timestamp', time.time()),
            'recommendations': self._generate_recommendations(metric_scores, telemetry_data)
        }
    
    def _score_latency(self, latency: float) -> float:
        """Score latency metric (0-1, where 1 is excellent)"""
        thresholds = self.thresholds['latency']
        
        if latency <= thresholds['excellent']:
            return 1.0
        elif latency <= thresholds['good']:
            return 0.8 + 0.2 * (thresholds['good'] - latency) / (thresholds['good'] - thresholds['excellent'])
        elif latency <= thresholds['fair']:
            return 0.6 + 0.2 * (thresholds['fair'] - latency) / (thresholds['fair'] - thresholds['good'])
        elif latency <= thresholds['poor']:
            return 0.3 + 0.3 * (thresholds['poor'] - latency) / (thresholds['poor'] - thresholds['fair'])
        else:
            # Beyond poor threshold, exponential decay
            return max(0.1, 0.3 * math.exp(-(latency - thresholds['poor']) / thresholds['poor']))
    
    def _score_ber(self, ber: float) -> float:
        """Score bit error rate (0-1, where 1 is excellent)"""
        if ber <= 0:
            return 1.0
        
        thresholds = self.thresholds['ber']
        
        if ber <= thresholds['excellent']:
            return 1.0
        elif ber <= thresholds['good']:
            ratio = math.log10(ber / thresholds['excellent']) / math.log10(thresholds['good'] / thresholds['excellent'])
            return 1.0 - 0.2 * ratio
        elif ber <= thresholds['fair']:
            ratio = math.log10(ber / thresholds['good']) / math.log10(thresholds['fair'] / thresholds['good'])
            return 0.8 - 0.2 * ratio
        elif ber <= thresholds['poor']:
            ratio = math.log10(ber / thresholds['fair']) / math.log10(thresholds['poor'] / thresholds['fair'])
            return 0.6 - 0.3 * ratio
        else:
            # Beyond poor threshold
            return max(0.1, 0.3 * math.exp(-math.log10(ber / thresholds['poor'])))
    
    def _score_utilization(self, utilization: float) -> float:
        """Score utilization (optimal around 70%, very high utilization is bad)"""
        if utilization <= 0:
            return 0.5  # Unused link
        
        optimal = 0.7
        if utilization <= optimal:
            # Linear increase from 0 to optimal
            return 0.5 + 0.5 * (utilization / optimal)
        else:
            # Decrease as utilization gets too high
            thresholds = self.thresholds['utilization']
            if utilization <= thresholds['good']:
                return 1.0 - 0.2 * (utilization - optimal) / (thresholds['good'] - optimal)
            elif utilization <= thresholds['fair']:
                return 0.8 - 0.2 * (utilization - thresholds['good']) / (thresholds['fair'] - thresholds['good'])
            elif utilization <= thresholds['poor']:
                return 0.6 - 0.3 * (utilization - thresholds['fair']) / (thresholds['poor'] - thresholds['fair'])
            else:
                return max(0.1, 0.3 * (1.0 - utilization) / (1.0 - thresholds['poor']))
    
    def _score_temperature(self, temperature: float) -> float:
        """Score temperature (lower is better)"""
        thresholds = self.thresholds['temperature']
        
        if temperature <= thresholds['excellent']:
            return 1.0
        elif temperature <= thresholds['good']:
            return 0.8 + 0.2 * (thresholds['good'] - temperature) / (thresholds['good'] - thresholds['excellent'])
        elif temperature <= thresholds['fair']:
            return 0.6 + 0.2 * (thresholds['fair'] - temperature) / (thresholds['fair'] - thresholds['good'])
        elif temperature <= thresholds['poor']:
            return 0.3 + 0.3 * (thresholds['poor'] - temperature) / (thresholds['poor'] - thresholds['fair'])
        else:
            return max(0.1, 0.3 * math.exp(-(temperature - thresholds['poor']) / 20))
    
    def _score_crc_errors(self, crc_errors: float) -> float:
        """Score CRC errors (lower is better)"""
        thresholds = self.thresholds['crc_errors']
        
        if crc_errors <= thresholds['excellent']:
            return 1.0
        elif crc_errors <= thresholds['good']:
            return 0.8 + 0.2 * (thresholds['good'] - crc_errors) / (thresholds['good'] - thresholds['excellent'])
        elif crc_errors <= thresholds['fair']:
            return 0.6 + 0.2 * (thresholds['fair'] - crc_errors) / (thresholds['fair'] - thresholds['good'])
        elif crc_errors <= thresholds['poor']:
            return 0.3 + 0.3 * (thresholds['poor'] - crc_errors) / (thresholds['poor'] - thresholds['fair'])
        else:
            return max(0.1, 0.3 * math.exp(-crc_errors / thresholds['poor']))
    
    def _score_signal_integrity(self, signal_integrity: float) -> float:
        """Score signal integrity (higher is better)"""
        thresholds = self.thresholds['signal_integrity']
        
        if signal_integrity >= thresholds['excellent']:
            return 1.0
        elif signal_integrity >= thresholds['good']:
            return 0.8 + 0.2 * (signal_integrity - thresholds['good']) / (thresholds['excellent'] - thresholds['good'])
        elif signal_integrity >= thresholds['fair']:
            return 0.6 + 0.2 * (signal_integrity - thresholds['fair']) / (thresholds['good'] - thresholds['fair'])
        elif signal_integrity >= thresholds['poor']:
            return 0.3 + 0.3 * (signal_integrity - thresholds['poor']) / (thresholds['fair'] - thresholds['poor'])
        else:
            return max(0.1, 0.3 * signal_integrity / thresholds['poor'])
    
    def _calculate_trend_factor(self, link_id: str, current_score: float) -> float:
        """Calculate trend factor based on historical performance"""
        if link_id not in self.history or len(self.history[link_id]) < 3:
            return 1.0  # No trend data available
        
        recent_scores = [score for _, score in self.history[link_id][-10:]]  # Last 10 measurements
        
        if len(recent_scores) < 3:
            return 1.0
        
        # Calculate trend (slope)
        x = list(range(len(recent_scores)))
        y = recent_scores
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Linear regression slope
        if n * sum_x2 - sum_x ** 2 != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        else:
            slope = 0
        
        # Convert slope to trend factor
        if slope > 0:
            # Improving trend
            trend_factor = min(1.1, 1.0 + slope * 2)
        else:
            # Degrading trend
            trend_factor = max(0.9, 1.0 + slope * 2)
        
        return trend_factor
    
    def _update_history(self, link_id: str, health_score: float):
        """Update historical health scores for a link"""
        if link_id not in self.history:
            self.history[link_id] = []
        
        self.history[link_id].append((time.time(), health_score))
        
        # Keep only recent history
        if len(self.history[link_id]) > self.max_history:
            self.history[link_id].pop(0)
    
    def _categorize_health(self, score: float) -> str:
        """Categorize health score into human-readable categories"""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.5:
            return "Fair"
        elif score >= 0.3:
            return "Poor"
        else:
            return "Critical"
    
    def _generate_recommendations(self, metric_scores: Dict[str, float], 
                                telemetry_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on scores"""
        recommendations = []
        
        # Check each metric for issues
        if metric_scores.get('latency', 1.0) < 0.6:
            latency = telemetry_data.get('latency', 0)
            recommendations.append(f"High latency detected ({latency:.2f}μs). Consider reducing traffic load or checking for congestion.")
        
        if metric_scores.get('ber', 1.0) < 0.6:
            recommendations.append("High bit error rate detected. Check signal integrity and cable connections.")
        
        if metric_scores.get('utilization', 1.0) < 0.6:
            utilization = telemetry_data.get('utilization', 0)
            if utilization > 0.9:
                recommendations.append(f"Link overutilized ({utilization:.1%}). Consider load balancing or traffic shaping.")
            elif utilization < 0.1:
                recommendations.append("Link underutilized. May indicate connectivity issues or misconfiguration.")
        
        if metric_scores.get('temperature', 1.0) < 0.6:
            temp = telemetry_data.get('temperature', 0)
            recommendations.append(f"High temperature detected ({temp:.1f}°C). Check cooling systems and airflow.")
        
        if metric_scores.get('crc_errors', 1.0) < 0.6:
            crc = telemetry_data.get('crc_errors', 0)
            recommendations.append(f"High CRC error rate ({crc:.1f}/sec). Indicates data integrity issues.")
        
        if metric_scores.get('signal_integrity', 1.0) < 0.6:
            recommendations.append("Poor signal integrity. Check physical connections and cable quality.")
        
        # Overall recommendations
        overall_score = sum(metric_scores.values()) / len(metric_scores)
        if overall_score < 0.5:
            recommendations.append("Link requires immediate attention. Consider taking offline for maintenance.")
        elif overall_score < 0.7:
            recommendations.append("Schedule preventive maintenance during next maintenance window.")
        
        return recommendations
    
    def get_fleet_health_summary(self) -> Dict[str, Any]:
        """Get summary health statistics across all monitored links"""
        if not self.history:
            return {'total_links': 0, 'health_distribution': {}}
        
        latest_scores = {}
        for link_id, history_data in self.history.items():
            if history_data:
                latest_scores[link_id] = history_data[-1][1]  # Get latest score
        
        if not latest_scores:
            return {'total_links': 0, 'health_distribution': {}}
        
        # Calculate distribution
        categories = {'Excellent': 0, 'Good': 0, 'Fair': 0, 'Poor': 0, 'Critical': 0}
        for score in latest_scores.values():
            category = self._categorize_health(score)
            categories[category] += 1
        
        # Calculate statistics
        scores = list(latest_scores.values())
        avg_score = np.mean(scores)
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        return {
            'total_links': len(latest_scores),
            'health_distribution': categories,
            'average_health': round(avg_score, 3),
            'min_health': round(min_score, 3),
            'max_health': round(max_score, 3),
            'healthy_percentage': round((categories['Excellent'] + categories['Good']) / len(latest_scores) * 100, 1)
        }