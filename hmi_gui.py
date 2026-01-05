import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Canvas
from pymodbus.client import ModbusTcpClient
import threading
import time
import collections

# Configuration
PLC_IP = "localhost"
PLC_PORT = 502

class ScadaHMI:
    def __init__(self, root):
        self.root = root
        self.root.title("SCADA HMI // REACTOR CONTROL SYSTEM")
        self.root.geometry("800x700")
        self.root.configure(bg="#2b2b2b")
        
        self.client = None
        self.connected = False
        
        # History for Graph (Store last 50 points)
        self.history_len = 60
        self.pressure_data = collections.deque([0]*self.history_len, maxlen=self.history_len)
        self.temp_data = collections.deque([0]*self.history_len, maxlen=self.history_len)
        
        self.setup_ui()
        
        # Connection Thread
        self.connect()
        
        # Polling Thread
        self.running = True
        self.poller = threading.Thread(target=self.poll_plc)
        self.poller.daemon = True
        self.poller.start()

    def setup_ui(self):
        # 1. Header
        header = tk.Label(self.root, text="::: REACTOR CORE MONITOR :::", 
                         font=("Impact", 24), fg="#00ffff", bg="#2b2b2b")
        header.pack(pady=10)
        
        # Connection Status
        self.lbl_status = tk.Label(self.root, text="CONNECTING...", fg="yellow", bg="#2b2b2b", font=("Consolas", 10))
        self.lbl_status.pack()

        # 2. Main Layout (Gauges + Graph)
        frame_top = tk.Frame(self.root, bg="#2b2b2b")
        frame_top.pack(fill=tk.BOTH, expand=True, padx=20)

        # Left: Gauges
        frame_gauges = tk.LabelFrame(frame_top, text="[ SENSORS ]", fg="white", bg="#333", font=("Consolas", 10, "bold"))
        frame_gauges.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pressure
        tk.Label(frame_gauges, text="PRESSURE (PSI)", fg="cyan", bg="#333", font=("Consolas", 10)).pack(pady=5)
        self.lbl_pressure = tk.Label(frame_gauges, text="000", fg="#00ff00", bg="#333", font=("Consolas", 30, "bold"))
        self.lbl_pressure.pack()
        self.prog_pressure = ttk.Progressbar(frame_gauges, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.prog_pressure.pack(pady=5)
        
        # Temp
        tk.Label(frame_gauges, text="TEMP (C)", fg="orange", bg="#333", font=("Consolas", 10)).pack(pady=20)
        self.lbl_temp = tk.Label(frame_gauges, text="000", fg="#00ff00", bg="#333", font=("Consolas", 30, "bold"))
        self.lbl_temp.pack()
        self.prog_temp = ttk.Progressbar(frame_gauges, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.prog_temp.pack(pady=5)

        # Right: Live Graph
        frame_graph = tk.LabelFrame(frame_top, text="[ HISTORICAL TREND ]", fg="white", bg="#333", font=("Consolas", 10, "bold"))
        frame_graph.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = Canvas(frame_graph, bg="black", height=250, width=400, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 3. Controls Frame
        frame_controls = tk.LabelFrame(self.root, text="[ VALVE CONTROLS ]", fg="white", bg="#333", font=("Consolas", 10, "bold"))
        frame_controls.pack(fill=tk.X, padx=20, pady=10)
        
        btn_safe = tk.Button(frame_controls, text="NORMAL CYCLING", bg="#006600", fg="white", 
                            font=("Consolas", 12, "bold"), command=lambda: self.send_command(2, True))
        btn_safe.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        btn_attack = tk.Button(frame_controls, text="EMERGENCY OVERRIDE", bg="#880000", fg="white",
                              font=("Consolas", 12, "bold"), command=lambda: self.send_command(1, True))
        btn_attack.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        # Pump Control
        self.pump_status = True
        self.btn_pump = tk.Button(frame_controls, text="COOLING PUMP: ON", bg="#004400", fg="#00ff00",
                                 font=("Consolas", 12, "bold"), command=self.toggle_pump)
        self.btn_pump.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        # 4. Event Log
        frame_log = tk.LabelFrame(self.root, text="[ EVENT LOG ]", fg="white", bg="#333", font=("Consolas", 10, "bold"))
        frame_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(frame_log, height=8, bg="black", fg="#00ff00", 
                                                  font=("Consolas", 10), state='normal')
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log(self, msg):
        self.log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} > {msg}\n")
        self.log_area.see(tk.END)

    def connect(self):
        try:
            target_port = PLC_PORT
            self.client = ModbusTcpClient(PLC_IP, port=target_port)
            if self.client.connect():
                self.connected = True
                self.lbl_status.config(text=f"SYSTEM ONLINE: {PLC_IP}:{target_port}", fg="#00ff00")
                self.log("Connected to PLC Controller.")
            else:
                self.lbl_status.config(text="CONNECTION FAILED", fg="red")
                self.log("Connection Failed.")
        except Exception as e:
            self.lbl_status.config(text=f"ERROR: {e}", fg="red")

    def draw_graph(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        scan_w = w / self.history_len
        
        # Draw Grids
        self.canvas.create_line(0, h/2, w, h/2, fill="#333", dash=(2, 4))
        
        # Draw Pressure (Cyan)
        points_p = []
        for i, val in enumerate(self.pressure_data):
            x = i * scan_w
            # Scale 0-100 to h-0
            y = h - (val / 100.0 * h)
            points_p.append(x)
            points_p.append(y)
        if len(points_p) > 2:
            self.canvas.create_line(points_p, fill="cyan", width=2, smooth=True)

        # Draw Temp (Orange)
        points_t = []
        for i, val in enumerate(self.temp_data):
            x = i * scan_w
            y = h - (val / 100.0 * h)
            points_t.append(x)
            points_t.append(y)
        if len(points_t) > 2:
            self.canvas.create_line(points_t, fill="orange", width=2, smooth=True)

    def poll_plc(self):
        while self.running:
            if self.connected:
                try:
                    # Read Holding Registers 10 (Pressure) and 11 (Temp)
                    rr = self.client.read_holding_registers(10, 2, slave=1)
                    # Read Coil 3 (Pump Status) - Address 0-3... let's read 5
                    rc = self.client.read_coils(0, 5, slave=1)
                    
                    if not rr.isError() and not rc.isError():
                        pressure = rr.registers[0]
                        temp = rr.registers[1]
                        self.pump_status = rc.bits[3] # Index 3 = Address 3
                        
                        # Add to history
                        self.pressure_data.append(pressure)
                        self.temp_data.append(temp)
                        
                        # Update GUI
                        self.root.after(0, self.update_gui, pressure, temp)
                        
                    else:
                        self.lbl_status.config(text="READ ERROR", fg="orange")
                except Exception as e:
                    self.connected = False
                    self.lbl_status.config(text="DISCONNECTED", fg="red")
                    self.client.connect()
            time.sleep(0.5)

    def update_gui(self, pressure, temp):
        self.prog_pressure['value'] = pressure
        self.lbl_pressure.config(text=str(pressure))
        
        self.prog_temp['value'] = temp
        self.lbl_temp.config(text=str(temp))
        
        self.draw_graph()
        
        # Alerts
        if pressure > 80: self.lbl_pressure.config(fg="red")
        else: self.lbl_pressure.config(fg="#00ff00")
        
        if temp > 100: self.lbl_temp.config(fg="red", text=f"{temp} (CRITICAL)")
        else: self.lbl_temp.config(fg="#00ff00", text=str(temp))
        
        # Update Pump Button specific text if we had a dedicated status label, 
        # but for now we trust the button action updates state on click? 
        # Better: Update button text/color based on self.pump_status
        if self.pump_status:
            self.btn_pump.config(text="COOLING PUMP: ON", bg="#004400", fg="#00ff00")
        else:
            self.btn_pump.config(text="COOLING PUMP: OFF", bg="#440000", fg="white")

    def send_command(self, coil, value):
        if not self.connected:
            messagebox.showerror("Error", "PLC Disconnected")
            return
        threading.Thread(target=self._send_command_bg, args=(coil, value)).start()

    def toggle_pump(self):
        # Toggle current state
        # In Modbus we write the boolean.
        new_val = not self.pump_status
        self.send_command(3, new_val) # Coil 3

    def _send_command_bg(self, coil, value):
        try:
            self.root.after(0, lambda: self.log(f"Sending CMD to Coil {coil}..."))
            resp = self.client.write_coil(coil, value, slave=1)
            
            if resp.isError():
                self.root.after(0, lambda: self.log(f"[!] PLC REJECTED COMMAND (Coil {coil})"))
            else:
                self.root.after(0, lambda: self.log(f"[+] COMMAND ACCEPTED (Coil {coil})"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error: {e}"))

    def on_close(self):
        self.running = False
        if self.client:
            self.client.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScadaHMI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
