#!/usr/bin/env python3
"""
Startup script for NeuralFabric Guardian
"""
import os
import sys
import argparse
from config import get_config

def main():
    parser = argparse.ArgumentParser(description='NeuralFabric Guardian - AI-Driven GPU Interconnect Health Monitor')
    parser.add_argument('--env', choices=['development', 'production', 'testing'], 
                       default='development', help='Environment to run in')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set environment
    os.environ['FLASK_ENV'] = args.env
    
    # Get configuration
    config_class = get_config()
    
    # Ensure backend folder is in sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
    
    # Import and create app
    from app import app, initialize_system
    
    # Configure app
    app.config.from_object(config_class)
    if args.debug:
        app.config['DEBUG'] = True
    
    # Initialize system
    print("Initializing NeuralFabric Guardian...")
    initialize_system()
    
    print(f"Starting server on {args.host}:{args.port} in {args.env} mode...")
    print(f"Dashboard available at: http://{args.host}:{args.port}")
    print(f"API documentation available at: http://{args.host}:{args.port}/api")
    
    # Start the app
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=app.config.get('DEBUG', False),
            threaded=True
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
