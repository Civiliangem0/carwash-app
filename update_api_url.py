#!/usr/bin/env python3
"""
Script to update the API URL in the Flutter app.
"""
import os
import sys
import re
import argparse

def update_api_url(api_url):
    """Update the API URL in the Flutter app's API service."""
    api_service_path = os.path.join('lib', 'services', 'api_service.dart')
    
    if not os.path.exists(api_service_path):
        print(f"Error: {api_service_path} not found")
        return False
    
    # Read the file
    with open(api_service_path, 'r') as f:
        content = f.read()
    
    # Check if we're using the new implementation with platform-specific URLs
    if "if (Platform.isAndroid)" in content:
        # Update both Android and non-Android URLs
        android_pattern = r'baseUrl = \'http://10\.0\.2\.2:5000/api\';'
        android_replacement = f"baseUrl = 'http://10.0.2.2:{api_url.split(':')[1]}';"
        
        other_pattern = r'baseUrl = \'http://localhost:5000/api\';'
        other_replacement = f"baseUrl = '{api_url}';"
        
        if not re.search(android_pattern, content) or not re.search(other_pattern, content):
            print(f"Warning: Could not find exact baseUrl patterns in {api_service_path}")
            print(f"Attempting to update with more generic patterns...")
            
            # Try more generic patterns
            android_pattern = r'baseUrl = \'http://10\.0\.2\.2:[^/]+/api\';'
            other_pattern = r'baseUrl = \'http://localhost:[^/]+/api\';'
            
            if not re.search(android_pattern, content) or not re.search(other_pattern, content):
                print(f"Error: Could not find baseUrl patterns in {api_service_path}")
                return False
        
        updated_content = re.sub(android_pattern, android_replacement, content)
        updated_content = re.sub(other_pattern, other_replacement, updated_content)
    else:
        # Update the old implementation with a single baseUrl
        pattern = r'final String baseUrl = \'[^\']*\';'
        replacement = f"final String baseUrl = '{api_url}';"
        
        if not re.search(pattern, content):
            print(f"Error: Could not find baseUrl pattern in {api_service_path}")
            return False
        
        updated_content = re.sub(pattern, replacement, content)
    
    # Write the updated content
    with open(api_service_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated API URL to: {api_url}")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update the API URL in the Flutter app")
    parser.add_argument("api_url", help="The API URL (e.g., http://192.168.1.100:5000/api)")
    
    args = parser.parse_args()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not update_api_url(args.api_url):
        return 1
    
    print("API URL updated successfully. Run 'flutter pub get' and 'flutter run' to test the app.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
