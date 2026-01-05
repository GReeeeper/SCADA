from pymodbus.client import ModbusTcpClient
import time

def test_firewall():
    # Connect to the Firewall (Port 502), NOT the PLC directly
    client = ModbusTcpClient('localhost', port=502)
    
    print("[-] Connecting to Firewall on port 502...")
    if not client.connect():
        print("[!] Failed to connect. Is the firewall running (with sudo)?")
        return

    # Test 1: Safe Command (Write Coil 0x02)
    print("\n[+] Test 1: Sending SAFE command (Write Coil 0x02)...")
    try:
        # write_coil(address, value, slave=1)
        resp = client.write_coil(2, True, slave=1)
        if not resp.isError():
            print("    [SUCCESS] Response received (Command Allowed).")
        else:
            print("    [FAIL] Error response.")
    except Exception as e:
        print(f"    [FAIL] Exception: {e}")

    # Test 2: Unsafe Command (Write Coil 0x01)
    print("\n[+] Test 2: Sending UNSAFE command (Write Coil 0x01)...")
    try:
        resp = client.write_coil(1, True, slave=1)
        if not resp.isError():
            print("    [FAIL] Command was ALLOWED (Should be blocked!)")
        else:
            print("    [SUCCESS] Error/No Response (Command Blocked).")
    except Exception as e:
        print(f"    [SUCCESS] Request failed/dropped as expected: {e}")

    client.close()

if __name__ == "__main__":
    test_firewall()
