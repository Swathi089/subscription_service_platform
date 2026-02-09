import sqlite3

conn = sqlite3.connect("service_platform.db")
c = conn.cursor()

# Get all table names
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
print("Tables in database:", [table[0] for table in tables])

# Check payments table schema if it exists
if 'payments' in [table[0] for table in tables]:
    c.execute("PRAGMA table_info(payments);")
    columns = c.fetchall()
    print("Payments table columns:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
else:
    print("Payments table does not exist")

conn.close()
