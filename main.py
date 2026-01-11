import speech_recognition as sr
import pyttsx3
import webbrowser
import os
import subprocess
import pywhatkit
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import time

assistant_name = "jerry"

# Thread-safe speech engine
speech_lock = threading.Lock()
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)

# Task queue and executor for multi-tasking
task_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=5)
active_tasks = []

def speak(text):
    """Thread-safe speech function"""
    with speech_lock:
        engine.say(text)
        engine.runAndWait()

recognizer = sr.Recognizer()
mic = sr.Microphone()
recognizer.pause_threshold = 0.6

with mic as source:
    print("Calibrating microphone for ambient noise...")
    recognizer.adjust_for_ambient_noise(source, duration=1)
    print("Calibration complete!")

def listen():
    with mic as source:
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            command = recognizer.recognize_google(audio)
            command = command.lower()
            print(f"You said: {command}")
            return command
        except sr.UnknownValueError:
            print("Sorry, I did not understand.")
            return ""
        except sr.RequestError:
            print("Check your internet connection.")
            return ""
        except sr.WaitTimeoutError:
            print("Listening timed out.")
            return ""

def open_app(name):
    """Open application in background thread"""
    if "notepad" in name:
        speak("Opening Notepad")
        threading.Thread(target=lambda: os.system("notepad"), daemon=True).start()
    elif "calculator" in name:
        speak("Opening Calculator")
        threading.Thread(target=lambda: subprocess.Popen(r"C:\Windows\System32\calc.exe"), daemon=True).start()
    elif "chrome" in name:
        speak("Opening Chrome")
        threading.Thread(target=lambda: subprocess.Popen(r"C:\Program Files\Google\Chrome\Application\chrome.exe"), daemon=True).start()
    elif "edge" in name or "microsoft edge" in name:
        speak("Opening Microsoft Edge")
        threading.Thread(target=lambda: subprocess.Popen(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), daemon=True).start()
    else:
        speak(f"I cannot open {name}")


    


def close_app(name):
    """Close application in background thread"""
    if "notepad" in name:
        speak("Closing Notepad")
        threading.Thread(target=lambda: os.system("taskkill /f /im notepad.exe"), daemon=True).start()
    elif "calculator" in name:
        speak("Closing Calculator")
        threading.Thread(target=lambda: os.system('taskkill /f /fi "windowtitle eq Calculator"'), daemon=True).start()
        speak("If Calculator did not close, please close it manually.")
    elif "chrome" in name:
        speak("Closing Chrome")
        threading.Thread(target=lambda: os.system("taskkill /f /im chrome.exe"), daemon=True).start()
    elif "edge" in name or "microsoft edge" in name:
        speak("Closing Microsoft Edge")
        threading.Thread(target=lambda: os.system("taskkill /f /im msedge.exe"), daemon=True).start()
        speak("If Microsoft Edge did not close, please close it manually.")
    else:
        speak(f"I cannot close {name}")

def search_in_chrome(query):
    """Search in Chrome asynchronously"""
    speak(f"Searching for {query}")
    threading.Thread(target=lambda: webbrowser.open(f"https://www.google.com/search?q={query}"), daemon=True).start()

def play_song(query):
    """Play song asynchronously"""
    speak(f"Playing {query}")
    def _play():
        try:
            pywhatkit.playonyt(query)
        except Exception as e:
            print("Error playing song:", e)
            speak("Sorry, I couldn't play the song.")
    threading.Thread(target=_play, daemon=True).start()

def send_whatsapp_message(number, message):
    """Send WhatsApp message asynchronously"""
    def _send():
        try:
            speak(f"Sending WhatsApp message to {number}")
            pywhatkit.sendwhatmsg_instantly(number, message, wait_time=10, tab_close=True)
            speak("Message sent successfully")
        except Exception as e:
            print("Error sending WhatsApp message:", e)
            speak("Sorry, I could not send the WhatsApp message.")
    threading.Thread(target=_send, daemon=True).start()

def execute_task(command):
    """Execute a single task based on command"""
    print(f"[TASK] Executing: {command}")
    
    if "close" in command:
        close_app(command)
    elif "open" in command:
        open_app(command)
    elif "search" in command:
        query_index = command.find("search")
        if query_index != -1:
            query = command[query_index + len("search"):].strip()
            search_in_chrome(query)
        else:
            speak("Please say the search query after search.")
    elif "play" in command:
        query_index = command.find("play")
        if query_index != -1:
            query = command[query_index + len("play"):].strip()
            if query:
                play_song(query)
            else:
                speak("Please say the song name after play.")
        else:
            speak("Please say the song name after play.")
    elif "whatsapp" in command or "send message" in command:
        try:
            speak("Please say the phone number including country code.")
            number = listen()
            number = number.replace(" ", "")
            if not number.startswith("+"):
                speak("Please include the country code, like plus nine one for India.")
                return

            speak("What message should I send?")
            message = listen()

            if message:
                send_whatsapp_message(number, message)
            else:
                speak("Message was empty, I did not send anything.")
        except Exception as e:
            print("Error in WhatsApp command:", e)
            speak("Something went wrong while sending WhatsApp message.")
    else:
        speak("I cannot do that yet.")

def task_worker():
    """Background worker that processes tasks from the queue"""
    while True:
        try:
            command = task_queue.get(timeout=1)
            if command == "STOP_WORKER":
                break
            execute_task(command)
            task_queue.task_done()
        except queue.Empty:
            continue

def process_command(command):
    """Add command to task queue for parallel processing"""
    task_queue.put(command)
    speak("Task added to queue")

def main():
    """Main function with multi-tasking support"""
    # Start background task worker
    worker_thread = threading.Thread(target=task_worker, daemon=True)
    worker_thread.start()
    
    speak("Multi-tasking Voice Assistant is ready. Say 'Jerry let's go' to start.")
    continuous_mode = False
    
    while True:
        # Wait for activation
        listening = False
        while not listening:
            command = listen()
            if "jerry let's go" in command:
                speak("I am ready! You can give me multiple tasks.")
                listening = True
                continuous_mode = True
        
        # Listen for commands in continuous mode
        command = listen()
        if not command:
            if continuous_mode:
                continue
            else:
                speak("No command detected. Waiting for activation again.")
                continue
        
        # Handle special commands
        if "stop listening" in command or "pause" in command:
            speak("Pausing. Say Jerry let's go to resume.")
            continuous_mode = False
            continue
        elif "goodbye" in command or "exit" in command or "quit" in command:
            speak("Goodbye!")
            task_queue.put("STOP_WORKER")
            break
        elif "queue" in command or "show tasks" in command:
            queue_size = task_queue.qsize()
            speak(f"There are {queue_size} tasks in the queue.")
            continue
        
        # Execute task immediately (blocking mode)
        if "now" in command or "immediately" in command:
            execute_task(command)
        # Add to queue (non-blocking, multi-tasking mode)
        else:
            process_command(command)
        
        # In continuous mode, keep listening
        if not continuous_mode:
            speak("Waiting for activation...")

if __name__ == "__main__":
    main()
