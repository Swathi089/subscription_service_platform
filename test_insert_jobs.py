import sqlite3
import datetime


def insert_test_jobs():
    conn = sqlite3.connect('service_platform.db')
    c = conn.cursor()

    # Insert some test service requests with 'scheduled' status (available jobs)
    test_jobs = [
        {
            'customer_id': 1,
            'service_category': 'Cleaning',
            'service_description': 'Deep cleaning of 2BHK apartment',
            'location': 'Mumbai, Maharashtra',
            'scheduled_date': (datetime.datetime.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%d'),
            'scheduled_time': '10:00 AM',
            'status': 'scheduled'
        },
        {
            'customer_id': 1,
            'service_category': 'Plumbing',
            'service_description': 'Fix leaking kitchen faucet',
            'location': 'Delhi, Delhi',
            'scheduled_date': (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'scheduled_time': '2:00 PM',
            'status': 'scheduled'
        },
        {
            'customer_id': 1,
            'service_category': 'Electrical',
            'service_description': 'Install new ceiling fan',
            'location': 'Bangalore, Karnataka',
            'scheduled_date': (datetime.datetime.now() + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'scheduled_time': '11:00 AM',
            'status': 'scheduled'
        },
        {
            'customer_id': 1,
            'service_category': 'Gardening',
            'service_description': 'Monthly garden maintenance',
            'location': 'Pune, Maharashtra',
            'scheduled_date': (datetime.datetime.now() + datetime.timedelta(days=5)).strftime('%Y-%m-%d'),
            'scheduled_time': '9:00 AM',
            'status': 'scheduled'
        },
        {
            'customer_id': 1,
            'service_category': 'AC Service',
            'service_description': 'Annual AC maintenance and cleaning',
            'location': 'Chennai, Tamil Nadu',
            'scheduled_date': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            'scheduled_time': '3:00 PM',
            'status': 'scheduled'
        }
    ]

    for job in test_jobs:
        c.execute('''INSERT INTO service_requests
                     (customer_id, service_category, service_description, location,
                      scheduled_date, scheduled_time, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (job['customer_id'], job['service_category'], job['service_description'],
                   job['location'], job['scheduled_date'], job['scheduled_time'], job['status']))

    conn.commit()
    conn.close()
    print("Test jobs inserted successfully!")


if __name__ == '__main__':
    insert_test_jobs()
