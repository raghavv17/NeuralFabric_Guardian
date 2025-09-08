#!/usr/bin/env python3
"""
Deployment helper for NeuralFabric Guardian
"""
import os
import sys
import subprocess
import argparse

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask', 'flask-cors', 'networkx', 'numpy', 'pandas', 'scikit-learn'
    ]
    
    optional_packages = [
        ('statsmodels', 'ARIMA forecasting'),
        ('tensorflow', 'LSTM forecasting')
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            missing_required.append(package)
            print(f"✗ {package} (REQUIRED)")
    
    for package, feature in optional_packages:
        try:
            __import__(package)
            print(f"✓ {package} ({feature})")
        except ImportError:
            missing_optional.append((package, feature))
            print(f"✗ {package} ({feature}) - OPTIONAL")
    
    return missing_required, missing_optional

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    return True

def run_tests():
    """Run the test suite"""
    print("Running tests...")
    try:
        # Run individual test files
        test_files = [
            'test_topology.py',
            'test_anomaly.py', 
            'test_routing.py',
            'test_integration.py'
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Running {test_file}...")
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✓ {test_file} passed")
                else:
                    print(f"✗ {test_file} failed:")
                    print(result.stderr)
            else:
                print(f"⚠ {test_file} not found")
        
        return True
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def create_directories():
    """Create required directories"""
    directories = [
        'routes',
        'static/js',
        'static/css',
        'logs',
        'data'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created/verified directory: {directory}")

def main():
    parser = argparse.ArgumentParser(description='NeuralFabric Guardian Deployment Helper')
    parser.add_argument('--check-deps', action='store_true', 
                       help='Check dependencies')
    parser.add_argument('--install-deps', action='store_true',
                       help='Install dependencies')
    parser.add_argument('--run-tests', action='store_true',
                       help='Run test suite')
    parser.add_argument('--setup', action='store_true',
                       help='Complete setup (directories + dependencies)')
    parser.add_argument('--deploy', action='store_true',
                       help='Full deployment (setup + tests + start)')
    
    args = parser.parse_args()
    
    if args.check_deps or args.setup or args.deploy:
        print("=== Checking Dependencies ===")
        missing_required, missing_optional = check_dependencies()
        
        if missing_required:
            print(f"\nMissing required packages: {missing_required}")
            if args.setup or args.deploy:
                if not install_dependencies():
                    sys.exit(1)
            else:
                print("Run with --install-deps to install them")
                sys.exit(1)
    
    if args.install_deps:
        install_dependencies()
    
    if args.setup or args.deploy:
        print("\n=== Creating Directories ===")
        create_directories()
    
    if args.run_tests or args.deploy:
        print("\n=== Running Tests ===")
        if not run_tests():
            print("Some tests failed. Check the output above.")
            if args.deploy:
                response = input("Continue with deployment anyway? (y/N): ")
                if response.lower() != 'y':
                    sys.exit(1)
    
    if args.deploy:
        print("\n=== Starting Application ===")
        print("Use: python run.py --env production")
        print("Or:  python app.py")
        
    if not any(vars(args).values()):
        parser.print_help()

if __name__ == '__main__':
    main()