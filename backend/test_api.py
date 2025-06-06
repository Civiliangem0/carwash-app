#!/usr/bin/env python3
"""
Script to test the API endpoints.
"""
import os
import sys
import argparse
import json
import requests
from dotenv import load_dotenv

class ApiTester:
    """Class for testing the API endpoints."""
    
    def __init__(self, base_url):
        """Initialize the API tester."""
        self.base_url = base_url.rstrip('/')
        self.token = None
    
    def register(self, username, password):
        """Register a new user."""
        print(f"Registering user: {username}")
        
        url = f"{self.base_url}/auth/register"
        data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 201:
                print("Registration successful")
                return True
            else:
                print(f"Registration failed: {response.status_code}")
                print(response.json().get('msg', 'Unknown error'))
                return False
                
        except Exception as e:
            print(f"Error during registration: {str(e)}")
            return False
    
    def login(self, username, password):
        """Login and get JWT token."""
        print(f"Logging in as: {username}")
        
        url = f"{self.base_url}/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                print("Login successful")
                print(f"Token: {self.token[:20]}...")
                return True
            else:
                print(f"Login failed: {response.status_code}")
                print(response.json().get('msg', 'Unknown error'))
                return False
                
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False
    
    def get_stations(self):
        """Get station statuses."""
        print("Getting station statuses")
        
        if not self.token:
            print("Error: Not authenticated")
            return False
        
        url = f"{self.base_url}/stations"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                stations = response.json()
                print(f"Retrieved {len(stations)} stations:")
                for station in stations:
                    print(f"  Bay {station['id']}: {station['status']}")
                return True
            else:
                print(f"Failed to get stations: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Error getting stations: {str(e)}")
            return False
    
    def health_check(self):
        """Perform a health check."""
        print("Performing health check")
        
        url = f"{self.base_url}/health"
        
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("Health check successful:")
                print(f"  Status: {data.get('status')}")
                print(f"  Uptime: {data.get('uptime')} seconds")
                print(f"  Version: {data.get('version')}")
                return True
            else:
                print(f"Health check failed: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Error during health check: {str(e)}")
            return False
    
    def get_stations_guest(self):
        """Get station statuses as guest (no authentication)."""
        print("Getting station statuses as guest")
        
        url = f"{self.base_url}/guest/stations"
        
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                stations = response.json()
                print(f"Retrieved {len(stations)} stations as guest:")
                for station in stations:
                    print(f"  Bay {station['id']}: {station['status']}")
                return True
            else:
                print(f"Failed to get stations as guest: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Error getting stations as guest: {str(e)}")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the API endpoints")
    parser.add_argument("--url", default="http://localhost:5000/api", help="Base URL of the API")
    parser.add_argument("--username", default="testuser", help="Username for registration/login")
    parser.add_argument("--password", default="password123", help="Password for registration/login")
    parser.add_argument("--register", action="store_true", help="Register a new user")
    parser.add_argument("--login", action="store_true", help="Login and get JWT token")
    parser.add_argument("--stations", action="store_true", help="Get station statuses")
    parser.add_argument("--guest", action="store_true", help="Get station statuses as guest")
    parser.add_argument("--health", action="store_true", help="Perform a health check")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Load environment variables
    load_dotenv()
    
    # Create API tester
    tester = ApiTester(args.url)
    
    # Run tests
    success = True
    
    if args.all or args.register:
        if not tester.register(args.username, args.password):
            success = False
        print()
    
    if args.all or args.login:
        if not tester.login(args.username, args.password):
            success = False
        print()
    
    if args.all or args.stations:
        if not tester.get_stations():
            success = False
        print()
    
    if args.all or args.guest:
        if not tester.get_stations_guest():
            success = False
        print()
    
    if args.all or args.health:
        if not tester.health_check():
            success = False
        print()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
