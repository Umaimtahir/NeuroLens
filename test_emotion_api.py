"""
Test script to verify emotion logging works correctly
"""
import requests
import random

BASE_URL = "http://127.0.0.1:8000"

def test_guest_emotion_logging():
    """Test emotion logging as guest user"""
    
    # 1. Login as guest
    print("1. Logging in as guest...")
    response = requests.post(f"{BASE_URL}/api/auth/guest")
    assert response.status_code == 200
    
    data = response.json()
    token = data["token"]
    print(f"   ✅ Guest token: {token[:20]}...")
    
    # 2. Analyze frame (without actual frame, should use fallback)
    print("\n2. Sending emotion analysis request...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/analyze/frame", headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        emotion_data = response.json()
        print(f"   ✅ Emotion detected: {emotion_data['emotion']}")
        print(f"   ✅ Intensity: {emotion_data['intensity']}")
    else:
        print(f"   ❌ Error: {response.text}")
        return False
    
    # 3. Check if saved (admin endpoint)
    print("\n3. Checking saved emotions...")
    admin_headers = {"x-api-key": "neurolens-admin-key-2025"}
    response = requests.get(f"{BASE_URL}/api/admin/emotion-logs?limit=5", headers=admin_headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Total logs in database: {data['total']}")
        if data['logs']:
            latest = data['logs'][0]
            print(f"   Latest: {latest['username']} - {latest['emotion']} ({latest['intensity']})")
        return data['total'] > 0
    else:
        print(f"   ❌ Failed to fetch logs: {response.text}")
        return False

def test_registered_user_emotion():
    """Test with actual registered user"""
    print("\n" + "="*50)
    print("Testing with registered user 'umaim'...")
    print("="*50)
    
    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "umaim",
        "password": "Umaim123"  # Replace with actual password
    })
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return False
    
    data = response.json()
    token = data["token"]
    print(f"✅ Logged in as: {data['user']['name']}")
    
    # Send multiple emotion captures
    print("\nSending 3 emotion captures...")
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(3):
        response = requests.post(f"{BASE_URL}/api/analyze/frame", headers=headers)
        if response.status_code == 200:
            emotion = response.json()
            print(f"   {i+1}. {emotion['emotion']} - {emotion['intensity']}")
        else:
            print(f"   {i+1}. ❌ Failed: {response.text}")
    
    # Check history
    print("\nFetching emotion history...")
    response = requests.get(f"{BASE_URL}/api/emotions/history", headers=headers)
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ User has {len(history)} emotion records")
        return len(history) > 0
    else:
        print(f"❌ Failed: {response.text}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("NeuroLens Emotion Logging Test")
    print("="*50)
    
    # Test 1: Guest user
    success1 = test_guest_emotion_logging()
    
    # Test 2: Registered user (optional, comment out if password unknown)
    # success2 = test_registered_user_emotion()
    
    print("\n" + "="*50)
    print("RESULTS:")
    print("="*50)
    print(f"Guest emotion logging: {'✅ PASS' if success1 else '❌ FAIL'}")
    # print(f"User emotion logging: {'✅ PASS' if success2 else '❌ FAIL'}")
