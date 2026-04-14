import sqlite3
from database_utils import get_connection

def wipe_test_data():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Delete all bookings (clears the schedule)
        cursor.execute("DELETE FROM bookings")
        
        # 2. Delete all vehicles (clears the fleet)
        cursor.execute("DELETE FROM vehicles")
        
        # 3. Delete all drivers (clears the driver roster)
        cursor.execute("DELETE FROM drivers")
        
        # 4. Delete all users EXCEPT the Admin (keeps your login intact)
        cursor.execute("DELETE FROM users WHERE role != 'ADMIN'")
        
        conn.commit()
        print("✅ SUCCESS: All phony test data has been permanently deleted.")
        print("✅ STRUCTURE SAFE: Database architecture and Admin account are intact.")
        print("🚀 DriveElite is now a clean slate and ready for real users!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        conn.rollback()

if __name__ == "__main__":
    wipe_test_data()
