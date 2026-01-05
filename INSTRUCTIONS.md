# Modbus DPI Firewall: User Manual

Welcome to the **Modbus Deep Packet Inspection (DPI) Firewall** project. This lab mimics a critical infrastructure setup where a firewall protects a PLC (Programmable Logic Controller) from malicious commands.

---

## 1. Project Overview

There are three main components:
1.  **The Factory (Simulation)**: `plc_sim.py`
    - Runs a Modbus TCP server on `localhost:5020`.
    - Simulates a PLC controlling a physical process (like a turbine).
    
2.  **The Firewall (DPI)**: `firewall.c` (Compiled to `./firewall`)
    - Runs on `localhost:502` (Standard Modbus Port).
    - Acts as a proxy. It receives traffic, inspects it, and forwards safe packets to the Factory (5020).
    - **Rule**: BLOCKS any "Write Coil" command to Address `0x01` (Simulating a "Shutdown" command).

3.  **The Attacker (Test)**: `test_attack.py`
    - Connects to the Firewall to test if rules are working.

---

## 2. Setup & Installation

### Prerequisites
- Linux Environment (Arch Linux recommended)
- Python 3.x
- GCC Compiler

### Installation
1.  Install Python dependencies:
    ```bash
    pip install pymodbus
    ```

2.  Compile the Firewall:
    ```bash
    gcc firewall.c -o firewall
    ```

---

## 3. Running the Lab (HMI Dashboard)

You will need **3 separate terminal windows** to see the interaction clearly.

### Terminal 1: Start the Factory (Simulator)
This simulates the physical plant (Pressure/Temp sensors).
```bash
python plc_sim.py
```

### Terminal 2: Start the Firewall
This protects the factory from illegal commands.
```bash
sudo ./firewall
```

### Terminal 3: Start the HMI
This is the Operator's Dashboard.
```bash
python hmi_gui.py
```

### 4. How to Use
*   **Monitor**: Watch the **Pressure** and **Temperature** gauges on the dashboard move in real-time.
*   **Normal Op**: Click **"NORMAL CYCLING"** to send a safe command.
    *   Result: `COMMAND ACCEPTED`.
*   **Attack**: Click **"EMERGENCY OVERRIDE"** (The Red Button) to simulate an attack.
    *   Result: `PLC REJECTED COMMAND` (Blocked by Firewall).


---

## 4. Expected Results

When you run the test script in Terminal 3, observe the output in **Terminal 2 (Firewall)**.

1.  **Safe Command** (Write Coil `0x02`):
    - **Firewall**: `[+] Forwarded ... bytes to PLC`
    - **Test Script**: `[SUCCESS] Response received.`

2.  **Unsafe Command** (Write Coil `0x01`):
    - **Firewall**: `[BLOCKED] Illegal Shutdown Command detected!`
    - **Test Script**: `[SUCCESS] Request failed/dropped as expected.`

This confirms that your DPI Firewall is successfully inspecting Modbus packets and enforcing security rules!
