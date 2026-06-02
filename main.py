import os
import sys
import ctypes
import json
import time
import threading
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from http.client import HTTPSConnection
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
MESSAGES_FILE = "messages.txt"

# Ensure .env file exists
if not os.path.exists(ENV_FILE):
    open(ENV_FILE, "w").close()

load_dotenv(ENV_FILE)

# Setup CustomTkinter Theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def get_timestamp():
    return "[" + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "]"

class FruitSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fruit Sender - Auto Messenger")
        self.root.geometry("700x750")
        self.root.resizable(False, False)
        self.running = False

        # Load values from .env if they exist
        self.var_user_id = ctk.StringVar(value=os.getenv("USER_ID", ""))
        self.var_token = ctk.StringVar(value=os.getenv("TOKEN", ""))
        self.var_channel_url = ctk.StringVar(value=os.getenv("CHANNEL_URL", ""))
        self.var_channel_id = ctk.StringVar(value=os.getenv("CHANNEL_ID", ""))
        self.var_delay = ctk.StringVar(value=os.getenv("DELAY", "20"))

        self.build_ui()

    def build_ui(self):
        # Main Frame with padding
        main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(main_frame, text="🍎 Fruit Sender", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(10, 15))

        # Form Inputs
        ctk.CTkLabel(main_frame, text="User ID:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkEntry(main_frame, textvariable=self.var_user_id, width=400, placeholder_text="1234567890").grid(row=1, column=1, padx=20, pady=5)

        ctk.CTkLabel(main_frame, text="Discord Token:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkEntry(main_frame, textvariable=self.var_token, width=400, show="*", placeholder_text="Your Discord Token").grid(row=2, column=1, padx=20, pady=5)

        ctk.CTkLabel(main_frame, text="Channel URL:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkEntry(main_frame, textvariable=self.var_channel_url, width=400, placeholder_text="https://discord.com/channels/...").grid(row=3, column=1, padx=20, pady=5)

        ctk.CTkLabel(main_frame, text="Channel ID:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkEntry(main_frame, textvariable=self.var_channel_id, width=400, placeholder_text="Channel ID to send to").grid(row=4, column=1, padx=20, pady=5)

        ctk.CTkLabel(main_frame, text="Delay (seconds):", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkEntry(main_frame, textvariable=self.var_delay, width=150, placeholder_text="e.g., 20").grid(row=5, column=1, sticky="w", padx=20, pady=5)

        # Messages Area
        msg_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        msg_frame.grid(row=6, column=0, columnspan=2, pady=10, padx=20, sticky="w")
        
        ctk.CTkLabel(msg_frame, text="Messages (one per line). Tip: Custom emojis format: <:name:id>", font=ctk.CTkFont(size=12, slant="italic")).pack(anchor="w")
        self.msg_area = ctk.CTkTextbox(msg_frame, width=620, height=120, corner_radius=8)
        self.msg_area.pack()
        
        # Pre-load messages
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                self.msg_area.insert("0.0", f.read())

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)

        self.btn_start = ctk.CTkButton(btn_frame, text="Start Sending", width=150, fg_color="#28a745", hover_color="#218838", command=self.start)
        self.btn_start.pack(side="left", padx=10)

        self.btn_stop = ctk.CTkButton(btn_frame, text="Stop", width=150, fg_color="#dc3545", hover_color="#c82333", state="disabled", command=self.stop)
        self.btn_stop.pack(side="left", padx=10)

        # Output Log area
        ctk.CTkLabel(main_frame, text="Output Logs:", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, sticky="w", padx=20, pady=(5, 0))
        self.log_area = ctk.CTkTextbox(main_frame, width=620, height=150, corner_radius=8, state="disabled", fg_color="#1e1e1e", text_color="#d1d1d1")
        self.log_area.grid(row=9, column=0, columnspan=2, padx=20, pady=5)
        
        self.log_area.tag_config("SUCCESS", foreground="#28a745")
        self.log_area.tag_config("ERROR", foreground="#dc3545")

    def log(self, text):
        tag = None
        if "SUCCESS" in text:
            tag = "SUCCESS"
        elif "ERROR" in text or "FAILED" in text:
            tag = "ERROR"

        self.log_area.configure(state="normal")
        if tag:
            self.log_area.insert("end", text + "\n", tag)
        else:
            self.log_area.insert("end", text + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def start(self):
        user_id = self.var_user_id.get().strip()
        token = self.var_token.get().strip()
        channel_url = self.var_channel_url.get().strip()
        channel_id = self.var_channel_id.get().strip()
        delay = self.var_delay.get().strip()

        if not all([user_id, token, channel_url, channel_id, delay]):
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        try:
            delay_int = int(delay)
        except ValueError:
            messagebox.showerror("Error", "Delay must be a valid number.")
            return

        # Save messages to file
        msgs = self.msg_area.get("0.0", "end").strip()
        if not msgs:
            messagebox.showerror("Error", "Messages cannot be empty.")
            return

        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            f.write(msgs)

        # Save back to .env
        set_key(ENV_FILE, "USER_ID", user_id)
        set_key(ENV_FILE, "TOKEN", token)
        set_key(ENV_FILE, "CHANNEL_URL", channel_url)
        set_key(ENV_FILE, "CHANNEL_ID", channel_id)
        set_key(ENV_FILE, "DELAY", delay)

        # Update UI state
        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log(f"{get_timestamp()} Started sender bot...")

        # Run messaging loop in a separate thread to keep GUI responsive
        self.thread = threading.Thread(target=self.run_sender, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.log(f"{get_timestamp()} Stopping bot...")

    def run_sender(self):
        header_data = {
            "content-type": "application/json",
            "user-id": self.var_user_id.get().strip(),
            "authorization": self.var_token.get().strip(),
            "host": "discordapp.com",
            "referrer": self.var_channel_url.get().strip()
        }

        channel_id = self.var_channel_id.get().strip()
        delay = int(self.var_delay.get().strip())

        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as file:
                messages = file.read().splitlines()
        except FileNotFoundError:
            self.log(f"{get_timestamp()} ERROR: {MESSAGES_FILE} not found. Please create it.")
            self.root.after(0, self.stop)
            return

        if not messages:
            self.log(f"{get_timestamp()} ERROR: {MESSAGES_FILE} is empty.")
            self.root.after(0, self.stop)
            return

        while self.running:
            for message in messages:
                if not self.running:
                    break
                
                message_data = json.dumps({"content": message})
                conn = HTTPSConnection("discordapp.com", 443)
                try:
                    conn.request("POST", f"/api/v6/channels/{channel_id}/messages", message_data, header_data)
                    resp = conn.getresponse()
                    if 199 < resp.status < 300:
                        self.log(f"{get_timestamp()} SUCCESS: Sent '{message}'")
                    else:
                        self.log(f"{get_timestamp()} FAILED ({resp.status}): {resp.read().decode('utf-8', errors='ignore')}")
                except Exception as e:
                    self.log(f"{get_timestamp()} ERROR: {e}")
                finally:
                    conn.close()

                # Sleep incrementally so the thread can be interrupted gracefully
                for _ in range(delay):
                    if not self.running:
                        break
                    time.sleep(1)

            if self.running:
                self.log(f"{get_timestamp()} Reached the end of message list. Restarting loop...")

        self.log(f"{get_timestamp()} Process stopped.")

if __name__ == "__main__":
    mutex_name = "FruitSender_SingleInstance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(0, "Aplikasi Fruit Sender sudah berjalan di latar belakang atau sedang dibuka!", "Peringatan", 0x40000 | 0x30)
        sys.exit(0)

    root = ctk.CTk()
    app = FruitSenderGUI(root)
    root.mainloop()