/**
 * firewall.c
 * Modbus TCP DPI Firewall
 * 
 * Acts as a proxy between Client (Attacker/HMI) and PLC (Simulator).
 * Listens on Port 502 (Customizable).
 * Forwards to Port 5020 (Simulator).
 * 
 * RULES:
 * - DROP Write Coil (0x05) to Address 0x01
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

#define LISTEN_PORT 502
#define TARGET_IP "127.0.0.1"
#define TARGET_PORT 5020
#define BUFFER_SIZE 1024

// Modbus Constants
#define FUNC_WRITE_COIL 0x05
#define FORBIDDEN_ADDR  0x01

// Function to inspect Modbus packet
// Returns 1 if safe to forward, 0 if blocked
int inspect_packet(unsigned char *buffer, int len) {
    if (len < 10) return 1; // Too short to be a full Write Coil request, forward it (or could drop)

    // Modbus TCP Header:
    // Bytes 0-1: Transaction ID
    // Bytes 2-3: Protocol ID (0 = Modbus)
    // Bytes 4-5: Length
    // Byte 6: Unit ID
    // Byte 7: Function Code (PDU starts here)
    // Bytes 8-9: Data Address (for Write Coil)

    // Check Protocol ID (should be 0)
    if (buffer[2] != 0 || buffer[3] != 0) return 1;

    unsigned char func_code = buffer[7];
    
    if (func_code == FUNC_WRITE_COIL) {
        // Extract Address (Big Endian)
        unsigned int addr = (buffer[8] << 8) | buffer[9];

        if (addr == FORBIDDEN_ADDR) {
            printf("\033[1;31m[BLOCKED] Illegal Shutdown Command detected! (Func: 0x05, Addr: 0x%04X)\033[0m\n", addr);
            return 0; // Drop
        }
    }

    return 1; // Safe
}

void handle_client(int client_sock) {
    int target_sock;
    struct sockaddr_in target_addr;
    unsigned char buffer[BUFFER_SIZE];
    fd_set readfds;
    int max_sd;

    // Connect to the real PLC (Simulator)
    target_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (target_sock < 0) {
        perror("Target socket creation failed");
        close(client_sock);
        return;
    }

    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(TARGET_PORT);
    if (inet_pton(AF_INET, TARGET_IP, &target_addr.sin_addr) <= 0) {
        perror("Invalid address/ Address not supported");
        close(client_sock);
        close(target_sock);
        return;
    }

    if (connect(target_sock, (struct sockaddr *)&target_addr, sizeof(target_addr)) < 0) {
        perror("Connection to PLC Sim failed (is plc_sim.py running?)");
        close(client_sock);
        close(target_sock);
        return;
    }

    printf("[-] Client connected. Tunnel established to PLC.\n");

    while (1) {
        FD_ZERO(&readfds);
        FD_SET(client_sock, &readfds);
        FD_SET(target_sock, &readfds);
        max_sd = (client_sock > target_sock) ? client_sock : target_sock;

        int activity = select(max_sd + 1, &readfds, NULL, NULL, NULL);

        if ((activity < 0)) {
            printf("Select error\n");
            break;
        }

        // If something happened on the Client Socket (Incoming Command)
        if (FD_ISSET(client_sock, &readfds)) {
            int valread = read(client_sock, buffer, BUFFER_SIZE);
            if (valread <= 0) {
                printf("[-] Client disconnected\n");
                break;
            }

            // INSPECT PACKET BEFORE FORWARDING
            if (inspect_packet(buffer, valread)) {
                send(target_sock, buffer, valread, 0);
                printf("[+] Forwarded %d bytes to PLC\n", valread);
            } else {
                printf("[!] Packet Dropped.\n");
                // We do not forward.
                // Optionally send Modbus Exception? For now, we simulate a timeout/drop.
            }
        }

        // If something happened on the Target Socket (PLC Response)
        if (FD_ISSET(target_sock, &readfds)) {
            int valread = read(target_sock, buffer, BUFFER_SIZE);
            if (valread <= 0) {
                printf("[-] PLC closed connection\n");
                break;
            }
            // Forward response back to client (No inspection needed usually)
            send(client_sock, buffer, valread, 0);
        }
    }

    close(client_sock);
    close(target_sock);
}

int main() {
    int server_sock, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    // Create socket file descriptor
    if ((server_sock = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Force attach socket to port 502
    if (setsockopt(server_sock, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(LISTEN_PORT);

    if (bind(server_sock, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Bind failed (Are you running with sudo? Port 502 is privileged)");
        exit(EXIT_FAILURE);
    }

    if (listen(server_sock, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    printf("========================================\n");
    printf(" MODBUS FIREWALL ACTIVE\n");
    printf(" Listening on Port: %d\n", LISTEN_PORT);
    printf(" Forwarding to    : %s:%d\n", TARGET_IP, TARGET_PORT);
    printf("========================================\n");

    while(1) {
        printf("\n[-] Waiting for connection...\n");
        if ((new_socket = accept(server_sock, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
            perror("accept");
            exit(EXIT_FAILURE);
        }
        
        handle_client(new_socket);
    }

    return 0;
}
