import glob
import hashlib
import os
import re
import shutil
import sqlite3
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from detect import getProfile
from read import insertOrUpdate
from train import get_image_with_id

#--------------------------------------------------------------------------------

# Set up the recognizer and the face detector
recognizer = cv2.face.LBPHFaceRecognizer_create()
face_detect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Create users table if it doesn't exist
def create_users_table():
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (username TEXT PRIMARY KEY,
                       password TEXT NOT NULL)''')
    conn.commit()
    conn.close()
    
# Create students table if it doesn't exist
def create_students_table():
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS students
                      (id TEXT PRIMARY KEY,
                       name TEXT NOT NULL,
                       age INTEGER)''')
    conn.commit()
    conn.close()

# Hash the password in SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login function
def login():
    username = username_entry.get()
    password = password_entry.get()

    # Check if all fields are filled
    if not username or not password:
        messagebox.showerror("Error", "Please fill all fields")
        return

    # Connect to the database and check if the user exists
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    # Check if the password is correct or the credentials are for the admin
    if result and result[0] == hash_password(password) or (username == 'admin' and password == '12345'):
        login_window.destroy()
        show_main_window()
    # Show an error message if the credentials are invalid
    else:
        messagebox.showerror("Error", "Invalid email address or password")

def register_user():
    username = username_entry.get()
    password = password_entry.get()
    
    # Check if the username and password match the required patterns for AUPP faculty (EX: j.doe@aupp.edu.kh)
    username_pattern = r'^[a-z]\.[a-z]+@aupp\.edu\.kh$'
    password_pattern = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$'
        
    # Check if all fields are filled
    if not username or not password:
        messagebox.showerror("Error", "Please fill all fields")
        return

    # Check if the username and password match the required patterns
    if not re.match(username_pattern, username):
        messagebox.showerror("Error", "Invalid address. Must be a valid AUPP faculty email address.")
        return

    if not re.match(password_pattern, password):
        messagebox.showerror("Error", "Invalid password. Must be at least 8 characters long, with at least one letter and one number.")
        return

    # Connect to the database and insert the user
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (username, hash_password(password)))
        conn.commit()
        messagebox.showinfo("Success", "User registered successfully")
    # Only one user can have the same username(email address)
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists")
    finally:
        conn.close()
        
# Show the password if the checkbox is checked
def toggle_password_visibility():
    if show_password_var.get():
        password_entry.config(show="")
    else:
        password_entry.config(show="*")
        
# Focus on the next widget when the "Enter" key is pressed
def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return "break"

# Close the current window and show the login window
def go_back():
    root.destroy()
    show_login_window()

# Check if the ID already exists in the database
def check_id_exists(Id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id=?", (Id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def show_error(message):
    messagebox.showerror("Error", message)
    return

# Check if the inputs are valid
def validate_inputs(Id, Name, age):
    if not Id or not Name or not age:
        show_error("Please fill all fields")
        return False
    
    if not re.match(r'^[A-Z][a-z]+\s[A-Z]+$', Name):
        show_error("Invalid name. Must be in the format 'Firstname LASTNAME'.")
        return False
    
    if not Id.isdigit() or not age.isdigit():
        show_error("ID and Age must be numbers.")
        return False
    
    if int(Id) < 2015000 or int(Id) > 2026000:
        show_error("Invalid ID number.")
        return False
    
    if check_id_exists(Id):
        show_error("ID already exists. Please use a different ID.")
        return False
    
    return True

# Start the face recognition process
def start_face_recognition():
    cam = cv2.VideoCapture(0)
    Id = id_entry.get()
    Name = name_entry.get()
    age = age_entry.get()

    if not validate_inputs(Id, Name, age):
        cam.release()
        return

    # Insert the student into the database
    insertOrUpdate(Id, Name, age)

    ret, img = cam.read()
    if not ret:
        show_error("Failed to capture image")
        cam.release()
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sample_num, no_face_detected_time = 0, None

    while sample_num <= 20:
        ret, img = cam.read()
        if not ret:
            show_error("Failed to capture image")
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detect.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            if no_face_detected_time is None:
                no_face_detected_time = time.time()
                
            elif time.time() - no_face_detected_time >= 5:
                print("No face detected for 5 seconds. Exiting...")
                break
            
        else:
            no_face_detected_time = None
            for (x, y, w, h) in faces:
                sample_num += 1
                cv2.imwrite(f"dataset/{Name}.{Id}.{sample_num}.jpg", gray[y:y + h, x:x + w])
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(img, "REGISTERING...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.waitKey(100)

        cv2.imshow("Registering Face", img)
        cv2.waitKey(1)

    cam.release()
    cv2.destroyAllWindows()

    # Train the recognizer with the new images
    ids, faces = get_image_with_id('dataset')
    recognizer.train(faces, ids)
    recognizer.save('recognizer/trainingdata.yml')
    messagebox.showinfo("Success", "Face registered successfully.")
    id_entry.delete(0, tk.END)
    name_entry.delete(0, tk.END)
    age_entry.delete(0, tk.END)

# Register the face with the selected images
def register_face_with_images():
    warning = messagebox.askyesno("WARNING", "Using image files may lead to a VERY HIGH false positive rate. [Not Advised, if the other method is possible] Do you want to proceed?")
    if not warning:
        return
    
    file_paths = filedialog.askopenfilenames(
        title="Select Images", 
        filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
    )
    
    Id, Name, age = id_entry.get(), name_entry.get(), age_entry.get()

    if not validate_inputs(Id, Name, age):
        return

    insertOrUpdate(Id, Name, age)

    sample_num = 0

    for file_path in file_paths:
        img = cv2.imread(file_path)
        if img is None:
            continue
        
        # Convert the image to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detect.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            sample_num += 1
            cv2.imwrite(f"dataset/{Name}.{Id}.{sample_num}.jpg", gray[y:y + h, x:x + w])
            
        if sample_num >= 21:
            break

    if sample_num == 0:
        show_error("No faces detected in the selected images.")
        
    else:
        # Train the recognizer with the new images
        ids, faces = get_image_with_id('dataset')
        recognizer.train(faces, ids)
        recognizer.save('recognizer/trainingdata.yml')
        messagebox.showinfo("Success", "Faces registered successfully.")

# Record the attendance of a student
def record_attendance(id, name):
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    table_name = 'attendance_' + datetime.now().strftime('%d_%m_%Y')
    
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                        id TEXT,
                        name TEXT,
                        time DATETIME
                    )''')
    
    cursor.execute(f"INSERT INTO {table_name} (id, name, time) VALUES (?, ?, ?)",
                   (id, name, datetime.now().strftime('%H:%M:%S')))
    conn.commit()
    conn.close()
       
# Face recognition loop 
def face_recognition_loop():
    try:
        recognizer.read('recognizer/trainingdata.yml')
    except cv2.error:
        messagebox.showerror("Error", "Training data not found. Please register faces first.")
        return

    cam = cv2.VideoCapture(0)
    recorded_ids = set()
    table_name = 'attendance_' + datetime.now().strftime('%d_%m_%Y')
    
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    # Create a new table for the current date if it doesn't exist
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                        id TEXT,
                        name TEXT,
                        time DATETIME
                    )''')
    conn.commit()
    
    cursor.execute(f"SELECT id FROM {table_name}")
    rows = cursor.fetchall()
    for row in rows:
        recorded_ids.add(row[0])

    try:
        while True:
            ret, img = cam.read()
            if not ret:
                messagebox.showerror("Error", "Failed to capture image")
                break
            # Check if the face is recognized
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_detect.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                id, confidence = recognizer.predict(face)
                if confidence < 70:
                    profile = getProfile(id)
                    if profile:
                        if str(id) not in recorded_ids:
                            record_attendance(id, profile[1])
                            recorded_ids.add(str(id))
                            status = 'Unrecorded'
                        else:
                            status = 'Present'
                    # Display the student's ID, name, age, and status
                    cv2.putText(img, f"ID: {profile[0]}", (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(img, f"Name: {profile[1]}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(img, f"Age: {profile[2]}", (x, y + h + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(img, f"Status: {status}", (x, y + h + 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                else:
                    cv2.putText(img, "Face not recognized", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 2)
            cv2.imshow("Face Recognition", img)
            if cv2.waitKey(10) == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()
        conn.close()

def begin_face_recognition():
    face_recognition_loop()
    
# Reset the databases
def reset_databases():
    # Give warning twice before resetting the databases
    warning = messagebox.askyesno("WARNING", "You are about to DELETE ALL data from the databases. This action cannot be undone. Do you want to proceed?")
    if warning:
        response = messagebox.askyesno("Confirm Reset #2", "Are you sure you want to reset the databases? This action CANNOT be undone.")
    else:
        messagebox.showinfo("Reset Cancelled", "Reset Cancelled.")
        
    # Delete all data from the databases
    if response:
        conn = sqlite3.connect('sqlite.db')
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS students")
        cursor.execute('''CREATE TABLE IF NOT EXISTS students
                          (id TEXT PRIMARY KEY,
                           name TEXT NOT NULL,
                           age INTEGER)''')
        conn.commit()
        conn.close()

        # Delete all images from the dataset folder
        files = glob.glob('dataset/*')
        for f in files:
            os.remove(f)
         
        # Delete all images subfolders from the picture_database folder   
        files = glob.glob('picture_database/*')
        for f in files:
            shutil.rmtree(f)

        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'attendance_%'")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        conn.commit()
        conn.close()

        messagebox.showinfo("Reset Complete", "Databases have been reset successfully.")
        
    else:
        messagebox.showinfo("Reset Cancelled", "Databases have not been reset.")
        
# Login window UI
def show_login_window():
    global login_window, username_entry, password_entry, show_password_var

    login_window = tk.Tk()
    login_window.geometry('1280x720')
    login_window.title('Login or Sign Up')
    
    background = Image.open('logos/login.png')
    background = background.resize((1280, 720))
    background = ImageTk.PhotoImage(background)
    
    background_label = tk.Label(login_window, image=background)
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    background_label.image = background
    
    label = tk.Label(login_window, text="Please Login or Sign Up", font=('Times New Roman', 24), fg='#2F3A6A', bg="white")
    label.place(relx=0.5, rely=0.2, anchor="n")

    username_label = tk.Label(login_window, text="Email Address:", font=('Times New Roman', 16), bg="white", fg='black')
    username_label.place(relx=0.5, rely=(220/720), anchor="n")
    
    username_entry = tk.Entry(login_window)
    username_entry.place(relx=0.5, rely=(220/720)+45/720, anchor="n")
    username_entry.bind("<Return>", focus_next_widget)

    password_label = tk.Label(login_window, text="Password:", font=('Times New Roman', 16), bg="white", fg='black')
    password_label.place(relx=0.5, rely=(220/720)+90/720, anchor="n")
    
    password_entry = tk.Entry(login_window, show="*")
    password_entry.place(relx=0.5, rely=(220/720)+135/720, anchor="n")
    password_entry.bind("<Return>", focus_next_widget)

    show_password_var = tk.BooleanVar()
    show_password_check = tk.Checkbutton(login_window, text="Show Password", font=('Times New Roman', 16), variable=show_password_var, command=toggle_password_visibility, bg="white",)
    show_password_check.place(relx=0.5, rely=(220/720)+180/720, anchor="n")

    login_button = tk.Button(login_window, text="Login", command=login, font=('Times New Roman', 16), bg="white", fg='black')
    login_button.place(relx=0.5, rely=(220/720)+225/720, anchor="n")
    
    sign_up_button = tk.Button(login_window, text="Register", command=register_user, font=('Times New Roman', 16), bg="white", fg='black')
    sign_up_button.place(relx=0.5, rely=(220/720)+270/720, anchor="n")
    
    tk.Label(login_window, text='Or', font=('Times New Roman', 16), fg="black", bg="white").place(relx=0.5, rely=(220/720)+315/720, anchor="n")
    
    start_detection_button = tk.Button(login_window, text="Take Attendance", font=('Times New Roman', 16), command=begin_face_recognition, width=20)
    start_detection_button.place(relx=0.45, rely=(220/720)+360/720, anchor="e")
    
    view_attendance_button = tk.Button(login_window, text="View Attendance", font=('Times New Roman', 16), command=lambda: view_attendance(login_window), width=20)
    view_attendance_button.place(relx=0.55, rely=(220/720)+360/720, anchor="w")
    
    login_window.mainloop()
    
# Main window UI
def show_main_window():
    global root, id_entry, name_entry, age_entry

    root = tk.Tk()
    root.geometry('1280x720')
    root.title('Facial Recognition')

    background = Image.open('logos/main.png')
    background = background.resize((1280, 720))
    background = ImageTk.PhotoImage(background)

    background_label = tk.Label(root, image=background)
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    background_label.image = background

    label = tk.Label(root, text='Welcome to AUPP Facial Attendance Recording System', font=('Times New Roman', 24), fg='#2F3A6A', bg="white")
    label.place(relx=0.5, rely=0.1, anchor="n")

    id_label = tk.Label(root, text="Enter your ID:", font=('Times New Roman', 16), bg="white", fg='black')
    id_label.place(relx=0.5, rely=0.2, anchor="n")

    id_entry = tk.Entry(root, fg='black', bg='white')
    id_entry.place(relx=0.5, rely=0.2+(45/720), anchor="n")
    id_entry.bind("<Return>", focus_next_widget)

    name_label = tk.Label(root, text="Enter your name: (EX: John SMITH)", font=('Times New Roman', 16), bg="white", fg='black')
    name_label.place(relx=0.5, rely=0.2+(90/720), anchor="n")

    name_entry = tk.Entry(root, fg='black', bg='white')
    name_entry.place(relx=0.5, rely=0.2+(135/720), anchor="n")
    name_entry.bind("<Return>", focus_next_widget)

    age_label = tk.Label(root, text="Enter your age:", font=('Times New Roman', 16), bg="white", fg='black')
    age_label.place(relx=0.5, rely=0.2+(180/720), anchor="n")

    age_entry = tk.Entry(root, fg='black', bg='white')
    age_entry.place(relx=0.5, rely=0.2+(225/720), anchor="n")
    age_entry.bind("<Return>", focus_next_widget)

    start_button = tk.Button(root, text="Start Facial Registration", font=('Times New Roman', 16), command=start_face_recognition, width=20)
    start_button.place(relx=0.35, rely=0.2+(270/720), anchor="n")
    
    upload_button = tk.Button(root, text="Upload Images", font=('Times New Roman', 16), command=register_face_with_images, width=20)
    upload_button.place(relx=0.65, rely=0.2+(270/720), anchor="n")
    
    self_label = tk.Label(root, text='Press "ENTER" to start. "q" to quit.', font=('Times New Roman', 16), fg="black", bg="white")
    self_label.place(relx=0.5, rely=0.2+(315/720), anchor="n")
    
    start_detection_button = tk.Button(root, text="Take Attendance", font=('Times New Roman', 16), command=begin_face_recognition, width=20)
    start_detection_button.place(relx=0.5, rely=0.2+(360/720), anchor="n")
    
    view_db_button = tk.Button(root, text="View Database", font=('Times New Roman', 16), command=view_database, width=20)
    view_db_button.place(relx=0.35, rely=0.2+(405/720), anchor="n")
    
    view_attendance_button = tk.Button(root, text="View Attendance", font=('Times New Roman', 16), command=lambda: view_attendance(root), width=20)
    view_attendance_button.place(relx=0.65, rely=0.2+(405/720), anchor="n")
    
    go_back_button = tk.Button(root, text="X", font=('Times New Roman', 16), command=go_back, width=1, bg='RED', fg='RED')
    go_back_button.place(relx=0, rely=0, anchor="nw", x=10, y=10)
    
    reset_button = tk.Button(root, text="Reset Databases", font=('Times New Roman', 16), command=reset_databases, width=20, bg='RED', fg='RED')
    reset_button.place(relx=0.5, rely=0.2+(500/720), anchor="n")

    root.mainloop()
  
# Display the database in a new window  
def view_database():
    db_window = tk.Toplevel(root)
    db_window.title("Students Database")
    db_window.geometry(root.geometry())
    db_window.resizable(True, True)

    tree = ttk.Treeview(db_window)
    tree["columns"] = ("ID", "Name", "Age")
    tree.column("#0", width=0, stretch=tk.NO)
    tree.column("ID", anchor=tk.W, width=100)
    tree.column("Name", anchor=tk.W, width=100)
    tree.column("Age", anchor=tk.W, width=100)

    tree.heading("#0", text="", anchor=tk.W)
    tree.heading("ID", text="ID", anchor=tk.W)
    tree.heading("Name", text="Name", anchor=tk.W)
    tree.heading("Age", text="Age", anchor=tk.W)
    
    tree.pack(expand=True, fill='both')

    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    for row in rows:
        tree.insert("", tk.END, values=row)

    tree.pack()
    conn.close()
    
# Display the attendance records in a new window
def view_attendance(parent_window):
    def load_attendance_records(table_name):
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        for row in tree.get_children():
            tree.delete(row)
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()
    
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'attendance_%'")
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]
    conn.close()
    
    if not table_names:
        messagebox.showinfo("Info", "No attendance records found.")
        return
    
    attendance_window = tk.Toplevel(parent_window)
    attendance_window.title("Attendance Records")
    attendance_window.geometry(parent_window.geometry())
    attendance_window.resizable(True, True)
    
    tree = ttk.Treeview(attendance_window)
    tree["columns"] = ("ID", "Name", "Time")
    tree.column("#0", width=0, stretch=tk.NO)
    tree.column("ID", anchor=tk.W, width=100)
    tree.column("Name", anchor=tk.W, width=100)
    tree.column("Time", anchor=tk.W, width=150)
    
    tree.heading("#0", text="", anchor=tk.W)
    tree.heading("ID", text="ID", anchor=tk.W)
    tree.heading("Name", text="Name", anchor=tk.W)
    tree.heading("Time", text="Time", anchor=tk.W)
    
    selected_table = tk.StringVar()
    selected_table.set(table_names[0])
    
    dropdown = ttk.Combobox(attendance_window, textvariable=selected_table, values=table_names)
    dropdown.pack()
    dropdown.bind("<<ComboboxSelected>>", lambda event: load_attendance_records(selected_table.get()))
    
    tree.pack(expand=True, fill='both')
    
    load_attendance_records(selected_table.get())
    
if __name__ == "__main__":
    create_users_table()
    create_students_table()
    show_login_window()