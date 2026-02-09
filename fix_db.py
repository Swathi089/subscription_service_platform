import sqlite3

conn = sqlite3.connect("service_platform.db")
c = conn.cursor()

try:
    c.execute("ALTER TABLE payments ADD COLUMN razorpay_order_id TEXT;")
    print("✅ Column 'razorpay_order_id' added successfully.")
except Exception as e:
    print("⚠️ Error or column already exists:", e)

conn.commit()
conn.close()
