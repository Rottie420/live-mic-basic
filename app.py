import sounddevice as sd
import numpy as np
import tkinter as tk
from tkinter import ttk

# === INITIAL CONFIG ===
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
GAIN = 1.0
SMOOTHING = 0.05

# Buffers
smooth_buffer = np.zeros(BLOCK_SIZE)
waveform_data = np.zeros(BLOCK_SIZE)
stream = None  # initialized later

# === AUDIO EFFECT ===
def clean_effect(indata):
    global smooth_buffer, GAIN, SMOOTHING, waveform_data
    dry = indata[:, 0]
    smoothed = dry * (1 - SMOOTHING) + smooth_buffer * SMOOTHING
    smooth_buffer[:] = smoothed
    output = np.clip(smoothed * GAIN, -1.0, 1.0)
    waveform_data = output.copy()
    return output.reshape(-1, 1)

def audio_callback(indata, outdata, frames, time, status):
    if status:
        print("Audio status:", status)
    outdata[:] = clean_effect(indata)

# === STREAM MANAGEMENT ===
def start_stream():
    global stream
    if stream:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
    stream = sd.Stream(channels=1,
                       samplerate=SAMPLE_RATE,
                       blocksize=BLOCK_SIZE,
                       dtype='float32',
                       callback=audio_callback)
    stream.start()

def restart_stream():
    start_stream()

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
    global BLOCK_SIZE, smooth_buffer
    BLOCK_SIZE = int(float(val))
    smooth_buffer = np.zeros(BLOCK_SIZE)
    restart_stream()

# === VISUALIZER ===
def update_visualizer():
    canvas.delete("wave")
    canvas.delete("grid")

    h = canvas.winfo_height()
    w = canvas.winfo_width()

    # === Modern Grid ===
    grid_color = "#2A2A2A"
    # Vertical lines (every 50 px)
    for x in range(0, w, 50):
        canvas.create_line(x, 0, x, h, fill=grid_color, width=1, tags="grid")
    # Horizontal lines (every 25 px)
    for y in range(0, h, 25):
        canvas.create_line(0, y, w, y, fill=grid_color, width=1, tags="grid")
    # Center line (0 axis)
    canvas.create_line(0, h/2, w, h/2, fill="#444", width=1, tags="grid")

    # === Waveform ===
    if waveform_data is not None and len(waveform_data) > 0:
        step = max(1, len(waveform_data) // w)
        for i in range(0, len(waveform_data) - step, step):
            x0 = i / len(waveform_data) * w
            y0 = h / 2 - waveform_data[i] * h / 2
            x1 = (i + step) / len(waveform_data) * w
            y1 = h / 2 - waveform_data[i + step] * h / 2
            canvas.create_line(x0, y0, x1, y1, fill="cyan", width=1, tags="wave")

    root.after(30, update_visualizer)

# === GUI ===
root = tk.Tk()
root.title("Live Mic (Basic)")
root.configure(bg="#F0F0F0")
root.resizable(False, False)

canvas = tk.Canvas(root, bg="#1E1E1E", height=150)
canvas.pack(fill="x", padx=20, pady=15)

frame = ttk.Frame(root, padding=20)
frame.pack()

# Gain
ttk.Label(frame, text="Gain").grid(row=0, column=0, padx=10)
gain_slider = ttk.Scale(frame, from_=5.0, to=0.1, orient="vertical", command=update_gain, length=150)
gain_slider.set(GAIN)
gain_slider.grid(row=1, column=0, padx=10)

# Smoothing
ttk.Label(frame, text="Smoothing").grid(row=0, column=1, padx=10)
smooth_slider = ttk.Scale(frame, from_=0.5, to=0.01, orient="vertical", command=update_smoothing, length=150)
smooth_slider.set(SMOOTHING)
smooth_slider.grid(row=1, column=1, padx=10)

# Sample Rate
ttk.Label(frame, text="Sample Rate").grid(row=0, column=2, padx=10)
sr_slider = ttk.Scale(frame, from_=96000, to=8000, orient="vertical", command=update_sample_rate, length=150)
sr_slider.set(SAMPLE_RATE)
sr_slider.grid(row=1, column=2, padx=10)

# Block Size
ttk.Label(frame, text="Block Size").grid(row=0, column=3, padx=10)
bs_slider = ttk.Scale(frame, from_=4096, to=128, orient="vertical", command=update_block_size, length=150)
bs_slider.set(BLOCK_SIZE)
bs_slider.grid(row=1, column=3, padx=10)

# Stop
stop_button = ttk.Button(frame, text="Stop Stream", command=lambda: (stream.stop(), root.destroy()))
stop_button.grid(row=2, column=0, columnspan=4, pady=20)

# === START ===
start_stream()
update_visualizer()
root.mainloop()

if stream:
    stream.stop()
    stream.close()
