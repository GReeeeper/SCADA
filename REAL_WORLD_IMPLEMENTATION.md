# Real-World Implementation Guide

Transitioning this Proof-of-Concept (PoC) to a real Industrial Control System (ICS) environment requires addressing physical integration, reliability, and safety.

## 1. Physical Deployment

In a real factory, you wouldn't run this on the same machine as the PLC. You would place a dedicated hardware device between the **HMI/Engineering Workstation** and the **PLC**.

**Hardware Options:**
*   **Industrial PC (IPC)**: A ruggedized computer (fanless, DIN-rail mountable) running Linux.
*   **Raspberry Pi (for testing)**: Often used in non-critical pilots, but generally not rugged enough for factory floors.
*   **Managed Switch**: Some advanced switches support containerized apps, allowing you to run this C code directly on the network hardware.

## 2. Network Integration (Transparent Proxy)

In our lab, we manually connected the client to port 502 (Firewall). In real life, you don't want to reconfigure every HMI. You use **Transparent Proxying**.

You would configure `iptables` or `nftables` on the Firewall device to intercept traffic destined for the PLC's IP address.

```bash
# Example: Redirect traffic meant for PLC (192.168.1.50) port 502 to local Firewall process
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -A PREROUTING -p tcp --dport 502 -d 192.168.1.50 -j REDIRECT --to-port 502
```

The C code would need slight modification to use `SO_ORIGINAL_DST` to know where to forward the packet after inspection.

## 3. Reliability & "Fail-Open" Design

**Safety is paramount.** If your firewall crashes, the factory must not stop.

*   **Hardware Bypass (Fail-Open)**: Use a Network Interface Card (NIC) with a hardware bypass relay. If the device loses power, the relay closes and physically connects the Input port to the Output port, allowing traffic to flow uninspected (but keeping the process alive).
*   **Watchdog Timers**: A hardware watchdog should reboot the firewall device immediately if the OS freezes.

## 4. Performance (Latency)

*   **Real-time requirement**: SCADA networks often expect responses in milliseconds.
*   **Optimization**:
    *   Our C code is already fast, but `printf` to console is slow. In production, we would log to a file asynchronously or use a high-performance logging library (like Syslog or ZeroMQ) to send alerts to a SIEM.
    *   Use `O3` compiler optimization: `gcc -O3 firewall.c -o firewall`.

## 5. Deployment Checklist

1.  **Baseline Traffic**: Use Wireshark to record normal traffic for a week. Ensure your firewall doesn't block legitimate maintenance commands.
2.  **Alert-Only Mode**: Run the firewall in a mode where it *logs* blocked packets but doesn't actually drop them. Review logs for false positives.
3.  **Physical Security**: Lock the firewall device in the control cabinet. An attacker with physical access can bypass it.
