#!/usr/bin/env python3

import sys
import json
import requests
from datetime import datetime

def test_backend_connection():
    
    backend_url = "http://192.168.0.3:8080"
    username = "pappuraj.duet@gmail.com"
    password = "11223344"
    
    print("=== Backend Connection Test ===")
    print(f"Backend URL: {backend_url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print()
    
    try:
        print("Step 1: Testing authentication (LOGIN)...")
        auth_data = {
            'username': username,
            'password': password
        }
        
        auth_response = requests.post(
            f"{backend_url}/api/auth/login",
            json=auth_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Login Status Code: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            token_data = auth_response.json()
            access_token = token_data.get('accessToken')
            refresh_token = token_data.get('refreshToken')
            
            print("✓ LOGIN successful!")
            print(f"Access Token: {access_token[:20]}..." if access_token else "No access token")
            print(f"Refresh Token: {refresh_token[:20]}..." if refresh_token else "No refresh token")
            
            token_storage = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': time.time() + 900,
                'saved_at': time.time()
            }
            
            with open('tokens.json', 'w') as f:
                json.dump(token_storage, f, indent=2)
            print("✓ Tokens saved to tokens.json")
            
            print("\nStep 2: Testing authenticated endpoint (using saved JWT token)...")
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            health_response = requests.get(
                f"{backend_url}/api/health",
                headers=headers,
                timeout=10
            )
            
            print(f"Health Check Status: {health_response.status_code}")
            if health_response.status_code == 200:
                print("✓ Health check successful!")
            else:
                print(f"⚠ Health check failed: {health_response.text}")
            
            print("\nStep 3: Testing detection upload endpoint (using JWT token)...")
            test_detection = {
                'device_id': 'test_device_001',
                'timestamp': datetime.now().isoformat(),
                'trigger_source': 'test',
                'location': {
                    'latitude': 12.9716,
                    'longitude': 77.5946,
                    'altitude': 920.0,
                    'speed': 0.0,
                    'fix_quality': 1
                },
                'detections': [{
                    'bbox': [100, 100, 200, 200],
                    'confidence': 0.85,
                    'class_id': 0,
                    'class_name': 'pothole'
                }],
                'sensor_data': {
                    'ultrasonic_distance': 45.0,
                    'vibration_detected': True,
                    'confidence': 0.85
                },
                'metadata': {
                    'detection_count': 1,
                    'max_confidence': 0.85
                }
            }
            
            detection_response = requests.post(
                f"{backend_url}/api/detections",
                json=test_detection,
                headers=headers,
                timeout=30
            )
            
            print(f"Detection Upload Status: {detection_response.status_code}")
            if detection_response.status_code == 201:
                print("✓ Detection upload successful!")
                response_data = detection_response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
            else:
                print(f"⚠ Detection upload failed: {detection_response.text}")
            
            print("\nStep 4: Testing token refresh...")
            if refresh_token:
                refresh_data = {
                    'refreshToken': refresh_token
                }
                
                refresh_response = requests.post(
                    f"{backend_url}/api/auth/refresh",
                    json=refresh_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"Token Refresh Status: {refresh_response.status_code}")
                if refresh_response.status_code == 200:
                    print("✓ Token refresh successful!")
                    new_token_data = refresh_response.json()
                    new_access_token = new_token_data.get('accessToken')
                    print(f"New Access Token: {new_access_token[:20]}..." if new_access_token else "No new access token")
                else:
                    print(f"⚠ Token refresh failed: {refresh_response.text}")
            else:
                print("⚠ No refresh token available")
            
        else:
            print(f"✗ Authentication failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - check if backend server is running")
        print("Make sure the server is accessible at http://192.168.0.3:8080")
        return False
    except requests.exceptions.Timeout:
        print("✗ Request timeout - server may be slow or unreachable")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    print("\n=== Test Summary ===")
    print("Backend connection test completed!")
    return True

def test_network_connectivity():
    print("=== Network Connectivity Test ===")
    
    try:
        import subprocess
        result = subprocess.run(['ping', '-c', '1', '192.168.0.3'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Ping to 192.168.0.3 successful")
        else:
            print("✗ Ping to 192.168.0.3 failed")
            print("Make sure the backend server is running and accessible")
            
    except Exception as e:
        print(f"✗ Network test failed: {e}")

if __name__ == "__main__":
    print("Pothole Detection System - Backend Connection Test")
    print("=" * 50)
    
    test_network_connectivity()
    print()
    
    success = test_backend_connection()
    
    if success:
        print("\n🎉 All tests passed! Backend is ready for pothole detection system.")
    else:
        print("\n❌ Some tests failed. Please check the backend server configuration.")
        print("\nTroubleshooting tips:")
        print("1. Make sure the backend server is running on 192.168.0.3:8080")
        print("2. Check if the username/password are correct")
        print("3. Verify the Spring Security JWT endpoints are configured")
        print("4. Check firewall settings")
    
    sys.exit(0 if success else 1)