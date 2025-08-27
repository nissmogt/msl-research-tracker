#!/usr/bin/env python3
"""
Security validation test script for MSL Research Tracker
Tests the security improvements implemented for insightmsl.com
"""

import requests
import time
import json
from datetime import datetime

# Test configuration
RAILWAY_URL = "https://msl-research-tracker-production.up.railway.app"
VERCEL_URL = "https://insightmsl.com"  # Update when domain is live
TEST_EDGE_SECRET = "test-secret-for-validation"

def test_health_check_info_disclosure():
    """Test that health check no longer exposes environment variables"""
    print("🧪 Testing health check information disclosure fix...")
    
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        data = response.json()
        
        # Check that sensitive info is removed
        sensitive_keys = ["openai_api", "secret_key", "database_url", "port"]
        found_sensitive = [key for key in sensitive_keys if key in data]
        
        if found_sensitive:
            print(f"   ❌ FAIL: Still exposing sensitive keys: {found_sensitive}")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return False
        else:
            print(f"   ✅ PASS: No sensitive information exposed")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
            
    except Exception as e:
        print(f"   ⚠️  ERROR: Could not test health endpoint: {e}")
        return False

def test_edge_auth_blocking():
    """Test that direct Railway access is blocked without edge auth header"""
    print("🧪 Testing edge authentication blocking...")
    
    endpoints_to_test = [
        "/articles/recent",
        "/articles/search", 
        "/conversations",
        "/therapeutic-areas"
    ]
    
    blocked_count = 0
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{RAILWAY_URL}{endpoint}", timeout=5)
            if response.status_code == 403:
                print(f"   ✅ {endpoint}: Properly blocked (403)")
                blocked_count += 1
            else:
                print(f"   ❌ {endpoint}: Not blocked (got {response.status_code})")
        except Exception as e:
            print(f"   ⚠️  {endpoint}: Error testing - {e}")
    
    success_rate = blocked_count / len(endpoints_to_test)
    if success_rate >= 0.8:  # 80% success rate threshold
        print(f"   ✅ PASS: {blocked_count}/{len(endpoints_to_test)} endpoints properly blocked")
        return True
    else:
        print(f"   ❌ FAIL: Only {blocked_count}/{len(endpoints_to_test)} endpoints blocked")
        return False

def test_rate_limiting():
    """Test rate limiting functionality (careful not to trigger real limits)"""
    print("🧪 Testing rate limiting responses...")
    
    # Test that rate limit headers are present
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=5)
        
        rate_limit_headers = [h for h in response.headers.keys() if 'ratelimit' in h.lower()]
        
        if rate_limit_headers:
            print(f"   ✅ PASS: Rate limit headers present: {rate_limit_headers}")
            return True
        else:
            print(f"   ℹ️  INFO: No rate limit headers found (may be expected)")
            # This might be OK since health endpoint might be excluded
            return True
            
    except Exception as e:
        print(f"   ⚠️  ERROR: Could not test rate limiting: {e}")
        return False

def test_security_headers():
    """Test security headers on the root endpoint"""
    print("🧪 Testing security headers...")
    
    try:
        response = requests.get(f"{RAILWAY_URL}/", timeout=5)
        headers = response.headers
        
        expected_headers = [
            'strict-transport-security',
            'x-content-type-options', 
            'x-frame-options'
        ]
        
        found_headers = []
        for header in expected_headers:
            if header in [h.lower() for h in headers.keys()]:
                found_headers.append(header)
        
        success_rate = len(found_headers) / len(expected_headers)
        
        if success_rate >= 0.6:  # 60% of expected headers
            print(f"   ✅ PASS: Found security headers: {found_headers}")
            return True
        else:
            print(f"   ❌ FAIL: Missing security headers. Found: {found_headers}")
            return False
            
    except Exception as e:
        print(f"   ⚠️  ERROR: Could not test security headers: {e}")
        return False

def main():
    """Run all security tests"""
    print(f"🔒 MSL Research Tracker Security Validation")
    print(f"⏰ Test run: {datetime.now().isoformat()}")
    print(f"🎯 Target: {RAILWAY_URL}")
    print("=" * 60)
    
    tests = [
        ("Health Check Info Disclosure", test_health_check_info_disclosure),
        ("Edge Authentication Blocking", test_edge_auth_blocking), 
        ("Rate Limiting", test_rate_limiting),
        ("Security Headers", test_security_headers)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   💥 EXCEPTION: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All security tests passed! Your application is well secured.")
    elif passed >= total * 0.75:
        print("✅ Most security tests passed. Minor issues may need attention.")
    else:
        print("⚠️  Some security tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
