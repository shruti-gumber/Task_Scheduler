import sqlite3
import schedule
import time
from datetime import datetime
from twilio.rest import Client
from streamlit import secrets 

# Load Twilio credentials
try:
    account_sid = secrets["TWILIO_ACCOUNT_SID"]
    auth_token = secrets["TWILIO_AUTH_TOKEN"]
    twilio_whatsapp_number = "whatsapp:+14155238886"
    client = Client(account_sid, auth_token)
except KeyError:
    print("❌ Error: Could not find Twilio credentials in .streamlit/secrets.toml")
    exit()

def send_daily_reminders():
    print(f"[{datetime.now()}] 🔄 Checking for due tasks...")
    today_str = str(datetime.now().date())
    
    conn = sqlite3.connect('scheduler.db')
    c = conn.cursor()
    
    # We use a SQL JOIN to combine data from the tasks table and users table
    c.execute('''
        SELECT tasks.id, tasks.task, users.phone 
        FROM tasks 
        JOIN users ON tasks.user_id = users.id 
        WHERE tasks.completed = 0 AND tasks.deadline <= ? AND tasks.reminder_sent = 0
    ''', (today_str,))
    
    pending_tasks = c.fetchall()
    
    if not pending_tasks:
        print("✅ No pending messages to send.")
    
    for task_data in pending_tasks:
        t_id = task_data[0]
        t_desc = task_data[1]
        user_phone = task_data[2]
        user_whatsapp = f"whatsapp:{user_phone}"
        
        try:
            message_body = f"⏰ Automated Reminder: Your task '{t_desc}' is pending today!"
            client.messages.create(
                from_=twilio_whatsapp_number,
                body=message_body,
                to=user_whatsapp
            )
            print(f"✅ Sent reminder to {user_phone} for task: '{t_desc}'")
            
            # Update database so we don't spam them tomorrow
            c.execute("UPDATE tasks SET reminder_sent=1 WHERE id=?", (t_id,))
            conn.commit()
            
        except Exception as e:
            print(f"❌ Failed to send to {user_phone}. Error: {e}")

    conn.close()

# ---------------- THE SCHEDULER LOOP ----------------
print("🚀 Starting Background WhatsApp Bot...")

# 1. Run it once immediately when you start the script to test it:
send_daily_reminders()

# 2. Then set it to run every morning at 9:00 AM automatically
schedule.every().day.at("09:00").do(send_daily_reminders)

# 3. Keep the script running forever
while True:
    schedule.run_pending()
    time.sleep(60)