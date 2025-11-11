import sounddevice as sd
import numpy as np
import os
import customtkinter as ctk

# === INITIAL CONFIG ===
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
GAIN = 1.0
SMOOTHING = 0.05

smooth_buffer = np.zeros(BLOCK_SIZE)
waveform_data = np.zeros(BLOCK_SIZE)
stream = None

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

    grid_color = "#2A2A2A"
    for x in range(0, w, 50):
        canvas.create_line(x, 0, x, h, fill=grid_color, width=1, tags="grid")
    for y in range(0, h, 25):
        canvas.create_line(0, y, w, y, fill=grid_color, width=1, tags="grid")
    canvas.create_line(0, h/2, w, h/2, fill="#444", width=1, tags="grid")

    if waveform_data is not None and len(waveform_data) > 0:
        step = max(1, len(waveform_data) // w)
        for i in range(0, len(waveform_data) - step, step):
            x0 = i / len(waveform_data) * w
            y0 = h / 2 - waveform_data[i] * h / 2
            x1 = (i + step) / len(waveform_data) * w
            y1 = h / 2 - waveform_data[i + step] * h / 2
            canvas.create_line(x0, y0, x1, y1, fill="#00D5D2", width=1, tags="wave")

    root.after(30, update_visualizer)

# === GUI ===
ctk.set_appearance_mode("dark")

root = ctk.CTk()
icon_path = os.path.join(os.getcwd(), "liv-mic.ico")
root.iconbitmap(icon_path)
root.title("Live Mic Visualizer")
root.geometry("420x420")  # 👈 narrower window width
root.resizable(False, False)

canvas = ctk.CTkCanvas(root, bg="#1E1E1E", height=130, highlightthickness=0)
canvas.pack(fill="x", padx=15, pady=10)

# === CONTROL PANEL ===
control_frame = ctk.CTkFrame(root, fg_color="#252526", corner_radius=10)
control_frame.pack(pady=8, padx=15, fill="x")

def add_slider(parent, label, from_, to, val, command):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(side="left", expand=True, fill="both", padx=6)
    ctk.CTkLabel(frame, text=label, anchor="center", width=70).pack(pady=(8, 5))
    slider = ctk.CTkSlider(frame, from_=from_, to=to, orientation="vertical",
                           command=command, width=16, height=130, number_of_steps=100)
    slider.set(val)
    slider.pack(pady=(0, 10))
    return slider

gain_slider = add_slider(control_frame, "Gain", 0.1, 5.0, GAIN, update_gain)
smooth_slider = add_slider(control_frame, "Smooth", 0.01, 0.5, SMOOTHING, update_smoothing)
sr_slider = add_slider(control_frame, "Rate", 8000, 96000, SAMPLE_RATE, update_sample_rate)
bs_slider = add_slider(control_frame, "Size", 128, 4096, BLOCK_SIZE, update_block_size)

stop_button = ctk.CTkButton(root, text="Stop Stream", fg_color="#1F6AA5",
                            hover_color="#257EC4", width=120,
                            command=lambda: (stream.stop(), root.destroy()))
stop_button.pack(pady=12)

# === START ===
start_stream()
update_visualizer()
root.mainloop()

if stream:
    stream.stop()
    stream.close()
