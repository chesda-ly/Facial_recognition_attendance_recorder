import cv2
import sqlite3

#--------------------------------------------------------------------------------

# Load the cascade
faceDetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml');
cam = cv2.VideoCapture(0)

recognizer = cv2.face.LBPHFaceRecognizer_create()

# Function to get profile from database
def getProfile(id):
    conn = sqlite3.connect("sqlite.db")
    cursor = conn.execute(f"SELECT * FROM students WHERE Id=?", (id,))
    profile = None

    for row in cursor:
        profile = row
    conn.close()
    
    return profile