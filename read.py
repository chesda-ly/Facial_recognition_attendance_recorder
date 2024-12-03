import cv2
import sqlite3

#--------------------------------------------------------------------------------

# Load the cascade
faceDetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml');
cam = cv2.VideoCapture(0);

# Function to insert or update data in database
def insertOrUpdate(Id, Name, age):
    conn = sqlite3.connect("sqlite.db")
    cmd = "SELECT * FROM students  WHERE Id="+str(Id);
    cursor = conn.execute(cmd);
    isRecordExist = 0;

    for row in cursor:
        isRecordExist = 1;
    
    if isRecordExist == 1:
        conn.execute("UPDATE students SET Name =? WHERE Id =?", (Name, Id))
        conn.execute("UPDATE students SET age =? WHERE Id =?", (age, Id))

    else:
        conn.execute("INSERT INTO students(Id, Name, age) VALUES(?, ?, ?)", (Id, Name, age))
    
    conn.commit()
    conn.close()