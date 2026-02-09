import sqlite3
import json


def check_database():
    conn = sqlite3.connect('service_platform.db')
    c = conn.cursor()

    # Check total service requests
    c.execute('SELECT COUNT(*) FROM service_requests')
    total_requests = c.fetchone()[0]
    print(f"Total service requests: {total_requests}")

    # Check recent service requests
    c.execute('SELECT * FROM service_requests ORDER BY created_at DESC LIMIT 5')
    rows = c.fetchall()
    print("\nRecent service requests:")
    for row in rows:
        print(
            f"ID: {row[0]}, Customer: {row[1]}, Category: {row[3]}, Status: {row[6]}, Created: {row[10]}")

    # Check if there are any unassigned requests (service_provider_id is NULL)
    c.execute(
        'SELECT COUNT(*) FROM service_requests WHERE service_provider_id IS NULL')
    unassigned = c.fetchone()[0]
    print(f"\nUnassigned service requests: {unassigned}")

    # Check provider customer requests endpoint data
    c.execute('SELECT sr.* FROM service_requests sr WHERE sr.status = ? ORDER BY sr.created_at DESC', ('scheduled',))
    customer_requests = c.fetchall()
    print(
        f"\nAvailable customer requests (scheduled status): {len(customer_requests)}")
    for req in customer_requests[:3]:  # Show first 3
        print(
            f"ID: {req[0]}, Category: {req[3]}, Description: {req[4]}, Location: {req[5]}, Date: {req[7]}, Time: {req[8]}")

    conn.close()


if __name__ == "__main__":
    check_database()
