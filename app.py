import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect('scheduler.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, task TEXT, deadline TEXT, 
                  completed INTEGER, reminder_sent INTEGER)''')
    conn.commit()
    conn.close()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_db() 

# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "phone" not in st.session_state:
    st.session_state.phone = ""
if "editing_task_id" not in st.session_state:
    st.session_state.editing_task_id = None

# ---------------- PAGE 1: LOGIN & REGISTRATION ----------------
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("📅 Task Scheduler")
        st.markdown("Please log in or create an account to continue.")
        
        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Create Account"])
        
        with tab_login:
            with st.form(key="login_form"):
                login_user = st.text_input("Username")
                login_pass = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Login")
                
                if submit_login:
                    if login_user and login_pass:
                        conn = sqlite3.connect('scheduler.db')
                        c = conn.cursor()
                        c.execute("SELECT id, phone FROM users WHERE username=? AND password=?", 
                                  (login_user, hash_pw(login_pass)))
                        user = c.fetchone()
                        conn.close()

                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user[0] 
                            st.session_state.phone = user[1]   
                            st.session_state.username = login_user
                            st.rerun()
                        else:
                            st.error("Invalid username or password ❌")
                    else:
                        st.warning("Please enter both username and password.")
                        
        with tab_register:
            with st.form(key="register_form"):
                reg_user = st.text_input("New Username")
                reg_pass = st.text_input("New Password", type="password")
                reg_phone = st.text_input("WhatsApp Number (include country code, e.g., +91938...)")
                submit_reg = st.form_submit_button("Register")
                
                if submit_reg:
                    if reg_user and reg_pass and reg_phone:
                        if not reg_phone.startswith("+"):
                            st.error("Please include the country code starting with '+' (e.g., +91)")
                        else:
                            conn = sqlite3.connect('scheduler.db')
                            c = conn.cursor()
                            try:
                                c.execute("INSERT INTO users (username, password, phone) VALUES (?, ?, ?)", 
                                          (reg_user, hash_pw(reg_pass), reg_phone))
                                conn.commit()
                                st.success("Account created! You can now log in using the tab above. ✅")
                            except sqlite3.IntegrityError:
                                st.error("Username already exists. Please choose another. ❌")
                            finally:
                                conn.close()
                    else:
                        st.warning("Please fill out all fields.")

# ---------------- PAGE 2: MAIN TASK MANAGER ----------------
else:
    st.sidebar.markdown(f"### 👤 User: **{st.session_state.username}**")
    st.sidebar.caption(f"📱 {st.session_state.phone}") 
    if st.sidebar.button("Logout", type="primary"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = ""
        st.session_state.phone = ""
        st.session_state.editing_task_id = None
        st.rerun()

    st.title("📅 Task Scheduler Dashboard")
    
    conn = sqlite3.connect('scheduler.db')
    c = conn.cursor()

    # ADD TASK
    st.markdown("---")
    st.header("➕ Add New Task")
    
    with st.form(key="add_task_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            task_input = st.text_input("Enter your task")
        with col2:
            deadline = st.date_input("Select Deadline")
        
        if st.form_submit_button("Add Task"):
            if task_input.strip() != "":
                c.execute("INSERT INTO tasks (user_id, task, deadline, completed, reminder_sent) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.user_id, task_input, str(deadline), 0, 0))
                conn.commit()
                st.success("Task added successfully ✅")
                st.rerun()
            else:
                st.warning("Please enter a task ⚠️")

    # FETCH TASKS
    c.execute("SELECT * FROM tasks WHERE user_id=?", (st.session_state.user_id,))
    db_tasks = c.fetchall() 

    # TASK SUMMARY
    st.markdown("---")
    total = len(db_tasks)
    completed = sum(1 for t in db_tasks if t[4] == 1)
    pending = total - completed
    
    colA, colB, colC = st.columns(3)
    colA.metric("Total Tasks", total)
    colB.metric("Completed", completed)
    colC.metric("Pending", pending)

    # SHOW TASKS
    st.markdown("---")
    st.header("📋 Your Tasks")

    if total == 0:
        st.info("No tasks added yet. Start by adding one above!")
    else:
        for task in db_tasks:
            t_id, _, t_desc, t_deadline, t_completed, _ = task
                
            if st.session_state.editing_task_id == t_id:
                with st.container(border=True):
                    st.subheader("✏️ Edit Task")
                    new_desc = st.text_input("Task Description", value=t_desc, key=f"desc_{t_id}")
                    date_obj = datetime.strptime(t_deadline, "%Y-%m-%d").date()
                    new_deadline = st.date_input("Deadline", value=date_obj, key=f"date_{t_id}")
                    
                    sub_col1, sub_col2 = st.columns([1, 5])
                    with sub_col1:
                        if st.button("💾 Save", key=f"save_{t_id}"):
                            c.execute("UPDATE tasks SET task=?, deadline=? WHERE id=?", 
                                      (new_desc, str(new_deadline), t_id))
                            conn.commit()
                            st.session_state.editing_task_id = None
                            st.rerun()
                    with sub_col2:
                        if st.button("❌ Cancel", key=f"cancel_{t_id}"):
                            st.session_state.editing_task_id = None
                            st.rerun()
            else:
                col1, col2, col3, col4 = st.columns([4, 1.5, 1.5, 1.5])
                with col1:
                    if t_completed == 0:
                        st.markdown(f"<div style='background-color:#fff3cd;padding:10px;border-radius:5px;margin-bottom:5px'>📝 <b>{t_desc}</b></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background-color:#d4edda;padding:10px;border-radius:5px;margin-bottom:5px;color:grey'>~~{t_desc}~~ ✅</div>", unsafe_allow_html=True)
                    st.caption(f"Deadline: {t_deadline}")
                
                with col2:
                    if t_completed == 0:
                        if st.button("✔ Complete", key=f"complete_{t_id}"):
                            c.execute("UPDATE tasks SET completed=1 WHERE id=?", (t_id,))
                            conn.commit()
                            st.rerun()
                
                with col3:
                    if st.button("✏️ Edit", key=f"editbtn_{t_id}"):
                        st.session_state.editing_task_id = t_id
                        st.rerun()
                        
                with col4:
                    if st.button("🗑️ Delete", key=f"delete_{t_id}"):
                        c.execute("DELETE FROM tasks WHERE id=?", (t_id,))
                        conn.commit()
                        st.rerun()
    conn.close()