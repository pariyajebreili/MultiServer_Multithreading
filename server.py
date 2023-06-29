import socket
import concurrent.futures


PORT = 5050
ADDR = ("localhost", PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"


def handle_client(client_socket, client_addr):
    print(f"[NEW THREAD] Handling {client_addr}.")

    # Receive messages from the client
    connected = True
    while connected:
        msg = client_socket.recv(1024).decode(FORMAT)
        if msg == DISCONNECT_MESSAGE:
            connected = False
        else:
            print(f"[{client_addr}] {msg}")

    # Close the client connection
    client_socket.close()
    print(f"[DISCONNECTED] {client_addr} disconnected.")


def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()

    # Create a thread pool of 5 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Keep accepting client connections
        while True:
            # Wait for a client to connect
            client_socket, client_addr = server.accept()
            print(f"[NEW CONNECTION] {client_addr} connected.")

            # Submit the client connection to a free thread
            executor.submit(handle_client, client_socket, client_addr)


if __name__ == '__main__':
    print(f"[STARTING] Server is starting on {ADDR}.")
    start()