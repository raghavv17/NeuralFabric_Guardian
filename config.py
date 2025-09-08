"""
Configuration settings for NeuralFabric Guardian
"""
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask settings
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # System settings
    TELEMETRY_UPDATE_INTERVAL = int(os.environ.get('TELEMETRY_UPDATE_INTERVAL', 3))  # seconds
    MAX_ALERTS = int(os.environ.get('MAX_ALERTS', 50))
    MAX_ROUTING_DECISIONS = int(os.environ.get('MAX_ROUTING_DECISIONS', 100))
    
    # Default topology settings
    DEFAULT_NUM_GPUS = int(os.environ.get('DEFAULT_NUM_GPUS', 8))
    DEFAULT_NUM_SWITCHES = int(os.environ.get('DEFAULT_NUM_SWITCHES', 4))
    DEFAULT_INTERCONNECTS = os.environ.get('DEFAULT_INTERCONNECTS', 'PCIe,NVLink,UALink').split(',')
    
    # Health scoring thresholds
    HEALTH_REROUTE_THRESHOLD = float(os.environ.get('HEALTH_REROUTE_THRESHOLD', 0.6))
    CRITICAL_HEALTH_THRESHOLD = float(os.environ.get('CRITICAL_HEALTH_THRESHOLD', 0.3))
    
    # Anomaly detection settings
    ANOMALY_CONTAMINATION = float(os.environ.get('ANOMALY_CONTAMINATION', 0.1))
    ANOMALY_WINDOW_SIZE = int(os.environ.get('ANOMALY_WINDOW_SIZE', 50))
    
    # Forecasting settings
    FORECAST_WINDOW_SIZE = int(os.environ.get('FORECAST_WINDOW_SIZE', 50))
    DEFAULT_FORECAST_HORIZON = int(os.environ.get('DEFAULT_FORECAST_HORIZON', 10))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # More restrictive settings for production
    TELEMETRY_UPDATE_INTERVAL = 5  # Slower updates
    MAX_ALERTS = 100
    MAX_ROUTING_DECISIONS = 500

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Faster updates for testing
    TELEMETRY_UPDATE_INTERVAL = 1
    MAX_ALERTS = 10
    MAX_ROUTING_DECISIONS = 20

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])