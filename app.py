import sounddevice as sd
import numpy as np
import os, sys
import customtkinter as ctk
from PIL import Image, ImageTk

# === INITIAL CONFIG ===
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
GAIN = 1.0
SMOOTHING = 0.05

smooth_buffer = np.zeros(BLOCK_SIZE)
waveform_data = np.zeros(BLOCK_SIZE)
stream = None
selected_device_index = None
stream_status = None

# === AUDIO EFFECT ===
def clean_effect(indata):
    global smooth_buffer, GAIN, SMOOTHING, waveform_data
    dry = indata[:, 0]
    smoothed = dry * (1 - SMOOTHING) + smooth_buffer * SMOOTHING
    smooth_buffer[:] = smoothed
    output = np.clip(smoothed * GAIN, -1.0, 1.0)
    waveform_data = output.copy()
    return output

def audio_callback(indata, outdata, frames, time, status):
    if status:
        print("Audio status:", status)
    outdata[:] = clean_effect(indata).reshape(-1, 1)

# === STREAM MANAGEMENT ===
def start_stream(device_index=None):
    global stream, selected_device_index, stream_status, smooth_buffer

    if stream:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        stream = None

    if device_index is None:
        # fallback to first input device
        for idx, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                device_index = idx
                break

    selected_device_index = device_index

    try:
        dev_info = sd.query_devices(selected_device_index, 'input')
        channels = dev_info['max_input_channels']
        if channels < 1:
            raise RuntimeError("Selected device has no input channels.")

        smooth_buffer = np.zeros(BLOCK_SIZE)
        stream_status = f"{dev_info['name']}"

        stream = sd.Stream(
            device=(selected_device_index, None),
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=BLOCK_SIZE,
            dtype='float32',
            callback=audio_callback
        )
        stream.start()
    except Exception as e:
        stream_status = f"{e}"

def restart_stream():
    start_stream(selected_device_index)

# === GUI CALLBACKS ===
def update_gain(val):
    global GAIN
    GAIN = float(val)

def update_smoothing(val):
    global SMOOTHING
    SMOOTHING = float(val)

def update_sample_rate(val):
    global SAMPLE_RATE
    SAMPLE_RATE = int(float(val))
    restart_stream()

def update_block_size(val):
    global BLOCK_SIZE
    BLOCK_SIZE = int(float(val))
    restart_stream()

# === VISUALIZER ===
def update_visualizer():
    canvas.delete("wave")
    canvas.delete("grid")
    canvas.delete("status")

    h = canvas.winfo_height()
    w = canvas.winfo_width()

    # Grid
    for x in range(0, w, 50):
        canvas.create_line(x, 0, x, h, fill="#252525", width=1, tags="grid")
    for y in range(0, h, 25):
        canvas.create_line(0, y, w, y, fill="#252525", width=1, tags="grid")
    canvas.create_line(0, h/2, w, h/2, fill="#444", width=1, tags="grid")

    # Waveform
    if waveform_data is not None and len(waveform_data) > 0:
        smooth_window = 6
        smoothed = np.convolve(waveform_data, np.ones(smooth_window)/smooth_window, mode='same')
        step = max(1, len(smoothed) // w)
        for i in range(0, len(smoothed)-step, step):
            x0 = i / len(smoothed) * w
            y0 = h/2 - smoothed[i]*h/2
            x1 = (i+step)/len(smoothed)*w
            y1 = h/2 - smoothed[i+step]*h/2

            amp = abs(smoothed[i])
            if amp < 0.7:
                color = "#00FFFF"
                width = 1
            elif amp < 0.9:
                color = "#00FF88"
                width = 1.5
            else:
                color = "#FF4444"
                width = 2

            canvas.create_line(x0, y0, x1, y1, fill=color, width=width, tags="wave")

        rms = np.sqrt(np.mean(smoothed**2))
        rms_h = rms * h / 2
        canvas.create_line(0, h/2 - rms_h, w, h/2 - rms_h, fill="#888", width=1, dash=(2,4), tags="wave")
        canvas.create_line(0, h/2 + rms_h, w, h/2 + rms_h, fill="#888", width=1, dash=(2,4), tags="wave")

    canvas.create_text(
        w/2, h - 5,              #
        text=stream_status,
        fill="#FFFFFF",
        font=("Arial", 7, "normal"),
        anchor="s",           
        tags="status"
    )

    root.after(33, update_visualizer)

def set_window_icon(window, icon_path):
    if os.path.exists(icon_path):
        img = Image.open(icon_path)
        photo = ImageTk.PhotoImage(img)
        try:
            window.iconphoto(False, photo)
            window._icon_ref = photo
        except:
            pass

def update_device(name):
    global selected_device_index
    # Extract index from the name string
    idx = int(name.split('(')[-1].strip(')'))
    selected_device_index = idx
    restart_stream()

# === DEVICE SELECTION ===
# All input devices with at least 1 channel
input_devices = [d for d in sd.query_devices() if d['max_input_channels'] > 0]
device_names = [f"{d['name']} ({i})" for i, d in enumerate(input_devices)]
selected_device_index = None


# === GUI ===
ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.title("Live Mic Visualizer")
# Windows-only
if os.name == "nt":
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe
        base_path = sys._MEIPASS
    else:
        # Running as normal Python script
        base_path = os.getcwd()
        
    icon_path = os.path.join(base_path, "liv-mic.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

root.geometry("420x420")

canvas = ctk.CTkCanvas(root, bg="#1E1E1E", height=130, highlightthickness=0)
canvas.pack(fill="x", padx=15, pady=10)

# Controls
control_frame = ctk.CTkFrame(root, fg_color="#252526", corner_radius=10)
control_frame.pack(padx=15, pady=8, fill="x")

def add_slider(parent, label, from_, to, val, command):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(side="left", expand=True, fill="both", padx=6)
    ctk.CTkLabel(frame, text=label, anchor="center", width=70).pack(pady=(8,5))
    slider = ctk.CTkSlider(frame, from_=from_, to=to, orientation="vertical",
                           command=command, width=16, height=130, number_of_steps=100)
    slider.set(val)
    slider.pack(pady=(0,10))
    return slider

gain_slider = add_slider(control_frame, "Gain", 0.1, 5.0, GAIN, update_gain)
smooth_slider = add_slider(control_frame, "Smooth", 0.01, 0.5, SMOOTHING, update_smoothing)
sr_slider = add_slider(control_frame, "Rate", 8000, 96000, SAMPLE_RATE, update_sample_rate)
bs_slider = add_slider(control_frame, "Size", 128, 4096, BLOCK_SIZE, update_block_size)

# Device dropdown
device_var = ctk.StringVar(value="Select more input")

def truncate_text(text, max_chars=25):
    return text if len(text) <= max_chars else text[:max_chars-3] + "..."

# Update device selection and truncate display if too long
def update_device_truncate(value):
    device_var.set(truncate_text(value))
    update_device(value)

device_menu = ctk.CTkOptionMenu(
    root,
    values=device_names,
    variable=device_var,
    command=update_device_truncate,
    width=220,   # fixed width
    anchor="w"   # left-align text
)
device_menu.pack(pady=10)


# === START ===

update_visualizer()
root.mainloop()

if stream:
    stream.stop()
    stream.close()
