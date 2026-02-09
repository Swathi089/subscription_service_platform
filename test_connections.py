#!/usr/bin/env python3
"""
Test script to verify frontend-backend-database connections
"""
import sqlite3
import urllib.request
import json
import sys
import os


def test_database_connection():
    """Test database connection and data"""
    print("Testing database connection...")
    try:
        conn = sqlite3.connect('service_platform.db')
        c = conn.cursor()

        # Check tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print(f"✓ Database connected. Tables: {[t[0] for t in tables]}")

        # Check services count
        c.execute("SELECT COUNT(*) FROM services")
        services_count = c.fetchone()[0]
        print(f"✓ Services in database: {services_count}")

        # Check users count
        c.execute("SELECT COUNT(*) FROM users")
        users_count = c.fetchone()[0]
        print(f"✓ Users in database: {users_count}")

        conn.close()
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_backend_api():
    """Test backend API endpoints"""
    print("\nTesting backend API...")
    base_url = "http://127.0.0.1:5000"

    try:
        # Test services endpoint
        req = urllib.request.Request(f"{base_url}/api/services")
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode())
                print(f"✓ Services API working. Returned {len(data)} services")
            else:
                print(f"✗ Services API failed: {response.getcode()}")
                return False

        # Test categories endpoint
        req = urllib.request.Request(f"{base_url}/api/categories")
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode())
                print(
                    f"✓ Categories API working. Returned {len(data)} categories")
            else:
                print(f"✗ Categories API failed: {response.getcode()}")
                return False

        return True
    except urllib.error.URLError as e:
        print(f"✗ Backend API not accessible: {e}")
        print("   Make sure Flask app is running with: python app.py")
        return False
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False


def test_frontend_connection():
    """Test if frontend can connect to backend"""
    print("\nTesting frontend-backend connection...")

    # Check if app.js has correct API URL
    try:
        with open('static/js/app.js', 'r') as f:
            content = f.read()
            if 'http://127.0.0.1:5000/api' in content:
                print("✓ Frontend API URL configured correctly")
            else:
                print("✗ Frontend API URL not found or incorrect")
                return False
    except FileNotFoundError:
        print("✗ app.js file not found")
        return False

    # Check if templates include the JS file
    try:
        with open('templates/index.html', 'r') as f:
            content = f.read()
            if 'static/js/app.js' in content:
                print("✓ Frontend templates include app.js")
            else:
                print("✗ Frontend templates don't include app.js")
                return False
    except FileNotFoundError:
        print("✗ index.html template not found")
        return False

    return True


def main():
    print("🔗 Testing Frontend-Backend-Database Connections\n")

    all_passed = True

    # Test database
    if not test_database_connection():
        all_passed = False

    # Test backend
    if not test_backend_api():
        all_passed = False

    # Test frontend
    if not test_frontend_connection():
        all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("✅ All connections are working properly!")
        print("\nYour application is ready:")
        print("- Database: Connected and populated")
        print("- Backend: Running on http://127.0.0.1:5000")
        print("- Frontend: Connected to backend API")
        print("\nYou can now open http://127.0.0.1:5000 in your browser")
        print("\n🎉 Frontend, Backend, and Database are successfully connected!")
    else:
        print("❌ Some connections have issues. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
