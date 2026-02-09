import sqlite3
from datetime import datetime


def insert_test_request():
    conn = sqlite3.connect('service_platform.db')
    c = conn.cursor()

    # Insert a test customer service request
    c.execute('''INSERT INTO service_requests
                 (customer_id, service_category, service_description, location,
                  scheduled_date, scheduled_time, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (1, 'Cleaning', 'Need deep cleaning for my apartment',
               'Mumbai', '2024-01-15', 'morning', 'scheduled'))

    request_id = c.lastrowid
    conn.commit()
    conn.close()

    print(f"Inserted test customer service request with ID: {request_id}")
    return request_id


if __name__ == "__main__":
    insert_test_request()
