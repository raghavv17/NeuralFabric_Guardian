import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.seasonal import seasonal_decompose
    STATSMODELS_AVAILABLE = True
except ImportError:
    print("Warning: statsmodels not available. ARIMA forecasting will be disabled.")
    STATSMODELS_AVAILABLE = False

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    print("Warning: TensorFlow not available. LSTM forecasting will be disabled.")
    TENSORFLOW_AVAILABLE = False

class LinkPerformanceForecaster:
    """Forecasts link performance degradation and congestion patterns"""
    
    def __init__(self, window_size: int = 50, forecast_horizon: int = 10):
        self.window_size = window_size
        self.forecast_horizon = forecast_horizon
        
        # Data storage
        self.link_data = {}  # link_id -> deque of telemetry data
        self.models = {}     # link_id -> trained models
        
        # Model configurations
        self.arima_orders = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2)]
        self.lstm_config = {
            'lookback': 20,
            'neurons': [50, 25],
            'dropout': 0.2,
            'batch_size': 16,
            'epochs': 50
        }
    
    def add_telemetry_data(self, link_id: str, telemetry: Dict[str, Any]):
        """Add new telemetry data point for a link"""
        if link_id not in self.link_data:
            self.link_data[link_id] = deque(maxlen=self.window_size * 2)
        
        # Extract key metrics for forecasting
        try:
            data_point = {
                'timestamp': telemetry.get('timestamp', 0),
                'latency': float(telemetry.get('latency', 0)),
                'utilization': float(telemetry.get('utilization', 0)),
                'ber': float(telemetry.get('ber', 0)),
                'temperature': float(telemetry.get('temperature', 25)),
                'crc_errors': float(telemetry.get('crc_errors', 0)),
                'health_indicator': float(telemetry.get('health_indicator', 1.0))
            }
            
            # Validate data ranges
            data_point['utilization'] = max(0.0, min(1.0, data_point['utilization']))
            data_point['temperature'] = max(-50, min(150, data_point['temperature']))
            data_point['latency'] = max(0, data_point['latency'])
            data_point['ber'] = max(0, data_point['ber'])
            data_point['crc_errors'] = max(0, data_point['crc_errors'])
            data_point['health_indicator'] = max(0.0, min(1.0, data_point['health_indicator']))
            
            self.link_data[link_id].append(data_point)
            
            # Retrain model if we have enough data
            if len(self.link_data[link_id]) >= self.window_size:
                self._update_model(link_id)
                
        except Exception as e:
            print(f"Error adding telemetry data for {link_id}: {e}")
    
    def forecast_link_performance(self, link_id: str, 
                                horizon: Optional[int] = None) -> Dict[str, Any]:
        """
        Forecast performance metrics for a specific link
        
        Args:
            link_id: Link identifier
            horizon: Forecast horizon (timesteps), defaults to self.forecast_horizon
            
        Returns:
            Dictionary with forecasted metrics and confidence intervals
        """
        if horizon is None:
            horizon = self.forecast_horizon
            
        if link_id not in self.link_data or len(self.link_data[link_id]) < 10:
            return {
                'error': f'Insufficient data for forecasting (need at least 10 points, have {len(self.link_data.get(link_id, []))})'
            }
        
        try:
            data = list(self.link_data[link_id])
            df = pd.DataFrame(data)
            
            forecasts = {}
            
            # Forecast each metric
            metrics = ['latency', 'utilization', 'ber', 'temperature', 'crc_errors', 'health_indicator']
            
            for metric in metrics:
                if metric in df.columns:
                    series = df[metric].dropna().values
                    
                    if len(series) < 5:
                        continue
                    
                    # Try different forecasting methods
                    arima_forecast = self._arima_forecast(series, horizon) if STATSMODELS_AVAILABLE else None
                    simple_forecast = self._simple_trend_forecast(series, horizon)
                    
                    if TENSORFLOW_AVAILABLE and len(series) > 30:
                        lstm_forecast = self._lstm_forecast(series, horizon)
                    else:
                        lstm_forecast = None
                    
                    # Combine forecasts or use best available
                    forecasts[metric] = self._combine_forecasts(
                        arima_forecast, simple_forecast, lstm_forecast
                    )
            
            # Detect potential issues in forecasts
            alerts = self._analyze_forecasts(forecasts)
            
            return {
                'link_id': link_id,
                'forecast_horizon': horizon,
                'forecasts': forecasts,
                'alerts': alerts,
                'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns and len(df) > 0 else None,
                'confidence': self._calculate_forecast_confidence(link_id),
                'data_points_used': len(data)
            }
            
        except Exception as e:
            return {'error': f'Forecasting failed: {str(e)}'}
    
    def _arima_forecast(self, series: np.ndarray, horizon: int) -> Optional[Dict[str, Any]]:
        """Forecast using ARIMA model"""
        if not STATSMODELS_AVAILABLE or len(series) < 20:
            return None
        
        try:
            # Remove any NaN or infinite values
            series = series[~(np.isnan(series) | np.isinf(series))]
            if len(series) < 10:
                return None
            
            # Try different ARIMA orders and select best based on AIC
            best_aic = float('inf')
            best_model = None
            
            for order in self.arima_orders:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = ARIMA(series, order=order)
                        fitted_model = model.fit(disp=0)
                        
                        if fitted_model.aic < best_aic and not np.isnan(fitted_model.aic):
                            best_aic = fitted_model.aic
                            best_model = fitted_model
                except:
                    continue
            
            if best_model is None:
                return None
            
            # Generate forecast
            forecast_result = best_model.forecast(steps=horizon)
            conf_int = best_model.get_forecast(steps=horizon).conf_int()
            
            return {
                'method': 'ARIMA',
                'values': forecast_result.tolist(),
                'lower_bound': conf_int.iloc[:, 0].tolist(),
                'upper_bound': conf_int.iloc[:, 1].tolist(),
                'aic': best_aic
            }
            
        except Exception as e:
            print(f"ARIMA forecasting error: {e}")
            return None
    
    def _simple_trend_forecast(self, series: np.ndarray, horizon: int) -> Dict[str, Any]:
        """Simple trend-based forecasting"""
        if len(series) < 3:
            # Not enough data, return flat forecast
            last_value = series[-1] if len(series) > 0 else 0
            return {
                'method': 'constant',
                'values': [float(last_value)] * horizon,
                'trend': 0,
                'confidence': 'low'
            }
        
        # Calculate trend using linear regression
        x = np.arange(len(series))
        y = series
        
        # Remove NaN/inf values
        valid_idx = ~(np.isnan(y) | np.isinf(y))
        x, y = x[valid_idx], y[valid_idx]
        
        if len(x) < 2:
            last_value = series[-1] if len(series) > 0 else 0
            return {
                'method': 'constant',
                'values': [float(last_value)] * horizon,
                'trend': 0,
                'confidence': 'low'
            }
        
        try:
            # Linear regression
            A = np.vstack([x, np.ones(len(x))]).T
            slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
            
            # Generate forecast
            future_x = np.arange(len(series), len(series) + horizon)
            forecast_values = slope * future_x + intercept
            
            # Calculate simple confidence bounds based on recent variance
            recent_values = series[-min(10, len(series)):]
            variance = np.var(recent_values) if len(recent_values) > 1 else 0
            std_dev = np.sqrt(variance)
            
            # Calculate R-squared
            r_squared = self._calculate_r_squared(x, y, slope, intercept)
            
            return {
                'method': 'linear_trend',
                'values': [float(v) for v in forecast_values],
                'lower_bound': [float(v - 1.96 * std_dev) for v in forecast_values],
                'upper_bound': [float(v + 1.96 * std_dev) for v in forecast_values],
                'trend': float(slope),
                'r_squared': float(r_squared),
                'confidence': 'medium' if r_squared > 0.5 else 'low'
            }
            
        except Exception as e:
            print(f"Simple trend forecasting error: {e}")
            last_value = series[-1] if len(series) > 0 else 0
            return {
                'method': 'constant',
                'values': [float(last_value)] * horizon,
                'trend': 0,
                'confidence': 'low',
                'error': str(e)
            }
    
    def _lstm_forecast(self, series: np.ndarray, horizon: int) -> Optional[Dict[str, Any]]:
        """LSTM-based forecasting"""
        if not TENSORFLOW_AVAILABLE or len(series) < 30:
            return None
        
        try:
            # Prepare data for LSTM
            lookback = min(self.lstm_config['lookback'], len(series) - 5)
            
            if lookback < 3:
                return None
            
            X, y = [], []
            for i in range(lookback, len(series)):
                X.append(series[i-lookback:i])
                y.append(series[i])
            
            if len(X) < 10:  # Need minimum data for training
                return None
            
            X, y = np.array(X), np.array(y)
            
            # Handle any remaining NaN/inf values
            if np.any(np.isnan(X)) or np.any(np.isinf(X)) or np.any(np.isnan(y)) or np.any(np.isinf(y)):
                return None
            
            X = X.reshape(X.shape[0], X.shape[1], 1)
            
            # Build LSTM model
            model = Sequential([
                LSTM(self.lstm_config['neurons'][0], 
                     return_sequences=True, 
                     input_shape=(lookback, 1)),
                Dropout(self.lstm_config['dropout']),
                LSTM(self.lstm_config['neurons'][1]),
                Dropout(self.lstm_config['dropout']),
                Dense(1)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            
            # Train model (suppress output)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(X, y, 
                         epochs=min(20, self.lstm_config['epochs']), 
                         batch_size=self.lstm_config['batch_size'],
                         verbose=0)
            
            # Generate forecasts
            forecast_values = []
            current_input = series[-lookback:].reshape(1, lookback, 1)
            
            for _ in range(horizon):
                next_pred = model.predict(current_input, verbose=0)[0, 0]
                
                # Ensure prediction is reasonable
                if np.isnan(next_pred) or np.isinf(next_pred):
                    break
                    
                forecast_values.append(float(next_pred))
                
                # Update input for next prediction
                current_input = np.roll(current_input, -1, axis=1)
                current_input[0, -1, 0] = next_pred
            
            if len(forecast_values) == horizon:
                return {
                    'method': 'LSTM',
                    'values': forecast_values,
                    'model_summary': f'LSTM({self.lstm_config["neurons"][0]}, {self.lstm_config["neurons"][1]})',
                    'confidence': 'high'
                }
            
        except Exception as e:
            print(f"LSTM forecasting error: {e}")
        
        return None
    
    def _combine_forecasts(self, arima_result: Optional[Dict], 
                          simple_result: Dict, 
                          lstm_result: Optional[Dict]) -> Dict[str, Any]:
        """Combine multiple forecasts for better accuracy"""
        # Start with simple forecast as baseline
        combined = {
            'primary_forecast': simple_result['values'],
            'methods_used': [simple_result['method']],
            'confidence': simple_result.get('confidence', 'low')
        }
        
        if simple_result.get('r_squared', 0) > 0.7:
            combined['confidence'] = 'medium'
        
        # Add bounds if available
        if 'lower_bound' in simple_result:
            combined['lower_bound'] = simple_result['lower_bound']
            combined['upper_bound'] = simple_result['upper_bound']
        
        # If ARIMA is available and good quality, blend it in
        if arima_result and arima_result.get('aic', float('inf')) < 1000:
            combined['methods_used'].append('ARIMA')
            combined['confidence'] = 'medium'
            
            # Weighted average (70% simple, 30% ARIMA)
            simple_values = np.array(simple_result['values'])
            arima_values = np.array(arima_result['values'])
            
            if len(simple_values) == len(arima_values):
                combined['primary_forecast'] = (0.7 * simple_values + 0.3 * arima_values).tolist()
            
            # Use ARIMA bounds if available
            if 'lower_bound' in arima_result:
                combined['lower_bound'] = arima_result['lower_bound']
                combined['upper_bound'] = arima_result['upper_bound']
        
        # If LSTM is available, give it higher weight for longer forecasts
        if lstm_result:
            combined['methods_used'].append('LSTM')
            combined['confidence'] = 'high'
            
            # For longer horizons, give more weight to LSTM
            weight_lstm = min(0.4, len(combined['primary_forecast']) * 0.05)
            weight_other = 1 - weight_lstm
            
            current_values = np.array(combined['primary_forecast'])
            lstm_values = np.array(lstm_result['values'])
            
            if len(current_values) == len(lstm_values):
                combined['primary_forecast'] = (weight_other * current_values + 
                                              weight_lstm * lstm_values).tolist()
        
        return combined
    
    def _analyze_forecasts(self, forecasts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze forecasts for potential issues"""
        alerts = []
        
        try:
            # Check latency forecast
            if 'latency' in forecasts and 'primary_forecast' in forecasts['latency']:
                latency_forecast = forecasts['latency']['primary_forecast']
                if any(lat > 50 for lat in latency_forecast):  # > 50μs
                    max_latency = max(latency_forecast)
                    time_to_issue = next((i for i, lat in enumerate(latency_forecast) if lat > 50), len(latency_forecast))
                    alerts.append({
                        'type': 'performance_degradation',
                        'metric': 'latency',
                        'severity': 'high',
                        'message': f"High latency predicted (max: {max_latency:.2f}μs)",
                        'time_to_issue': time_to_issue
                    })
            
            # Check utilization forecast
            if 'utilization' in forecasts and 'primary_forecast' in forecasts['utilization']:
                util_forecast = forecasts['utilization']['primary_forecast']
                if any(util > 0.9 for util in util_forecast):
                    max_util = max(util_forecast)
                    time_to_issue = next((i for i, util in enumerate(util_forecast) if util > 0.9), len(util_forecast))
                    alerts.append({
                        'type': 'congestion_warning',
                        'metric': 'utilization',
                        'severity': 'medium',
                        'message': f"High utilization predicted (max: {max_util:.1%})",
                        'time_to_issue': time_to_issue
                    })
            
            # Check health indicator forecast
            if 'health_indicator' in forecasts and 'primary_forecast' in forecasts['health_indicator']:
                health_forecast = forecasts['health_indicator']['primary_forecast']
                if any(health < 0.5 for health in health_forecast):
                    min_health = min(health_forecast)
                    time_to_issue = next((i for i, health in enumerate(health_forecast) if health < 0.5), len(health_forecast))
                    alerts.append({
                        'type': 'health_degradation',
                        'metric': 'health_indicator',
                        'severity': 'critical',
                        'message': f"Link health degradation predicted (min: {min_health:.2f})",
                        'time_to_issue': time_to_issue
                    })
            
        except Exception as e:
            print(f"Error analyzing forecasts: {e}")
        
        return alerts
    
    def _calculate_r_squared(self, x: np.ndarray, y: np.ndarray, 
                           slope: float, intercept: float) -> float:
        """Calculate R-squared for linear regression"""
        try:
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            
            if ss_tot == 0:
                return 1.0 if ss_res == 0 else 0.0
            
            return 1 - (ss_res / ss_tot)
        except:
            return 0.0
    
    def _calculate_forecast_confidence(self, link_id: str) -> str:
        """Calculate overall confidence in forecasts for a link"""
        if link_id not in self.link_data:
            return 'none'
        
        data_points = len(self.link_data[link_id])
        
        if data_points < 10:
            return 'low'
        elif data_points < 30:
            return 'medium'
        else:
            return 'high'
    
    def _update_model(self, link_id: str):
        """Update forecasting model for a link (placeholder for periodic retraining)"""
        # In a production system, you might periodically retrain models here
        # For now, we rely on online forecasting
        pass
    
    def get_fleet_forecast_summary(self) -> Dict[str, Any]:
        """Get fleet-wide forecast summary"""
        total_links = len(self.link_data)
        if total_links == 0:
            return {'total_links': 0, 'alerts': [], 'links_with_data': 0}
        
        all_alerts = []
        links_with_issues = 0
        links_with_data = 0
        
        for link_id in self.link_data.keys():
            if len(self.link_data[link_id]) >= 10:
                links_with_data += 1
                
                forecast_result = self.forecast_link_performance(link_id, 5)  # 5-step lookahead
                
                if 'alerts' in forecast_result and forecast_result['alerts']:
                    for alert in forecast_result['alerts']:
                        alert['link_id'] = link_id
                    all_alerts.extend(forecast_result['alerts'])
                    links_with_issues += 1
        
        # Categorize alerts by severity
        alert_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for alert in all_alerts:
            severity = alert.get('severity', 'low')
            alert_counts[severity] = alert_counts.get(severity, 0) + 1
        
        return {
            'total_links': total_links,
            'links_with_data': links_with_data,
            'links_with_predicted_issues': links_with_issues,
            'alert_summary': alert_counts,
            'upcoming_alerts': sorted(all_alerts, key=lambda x: x.get('time_to_issue', 0))[:10]
        }