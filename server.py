import socket
import logging
import concurrent.futures
import queue
import time
import threading
from colorprints import ColorPrints

# Server configuration
SERVER_ADDRESS = ('localhost', 8000)
MAX_CONNECTIONS = 5
MAX_QUEUE_SIZE = 20
OVERFLOW_QUEUE_SIZE = 20
IDLE_TIMEOUT = 3  # Define the idle timeout in seconds
OVERFLOW_CHECK_INTERVAL = 3  # Define the overflow check interval in seconds

# Message configuration
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '!DISCONNECT'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(SERVER_ADDRESS)
server_socket.listen(MAX_CONNECTIONS)
logging.info(f"[LISTENING] Server is listening on {SERVER_ADDRESS}.")

# Set up a queue to hold incoming clients
client_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

# Set up an overflow queue to hold clients when the main queue is full
overflow_queue = queue.Queue(maxsize=OVERFLOW_QUEUE_SIZE)


def handle_client(client_socket, client_addr):
    logging.info(f"[NEW THREAD] Handling {client_addr}.")

    # Set a timeout on the client socket
    client_socket.settimeout(IDLE_TIMEOUT)

    # Loop to connect 4 times
    for i in range(4):
        # Receive messages from the client
        connected = True
        while connected:
            try:
                msg = client_socket.recv(1024).decode(FORMAT)
            except socket.timeout:
                # The client is idle, disconnect it
                ColorPrints.print_in_red(f"[IDLE TIMEOUT] {client_addr} disconnected.")
                connected = False
                break

            if len(msg) == 0:
                # Connection was closed by the client
                ColorPrints.print_in_cyan(f"[CONNECTION CLOSED] {client_addr} connection was closed.")
                break

            if msg == DISCONNECT_MESSAGE:
                connected = False
                # Disconnect from the client
                client_socket.close()
                ColorPrints.print_in_red(f"[DISCONNECTED] {client_addr} disconnected.")
            else:
                logging.info(f"[{client_addr}] {msg}")

        # Remove the client from the queue
        try:
            client_queue.get_nowait()
            ColorPrints.print_in_yellow(f"[DEQUEUEING] {client_addr} dequeued.")
        except queue.Empty:
            pass

        # Check if there is space in the main queue
        if not client_queue.full():
            # Add the client to the main queue
            try:
                client_queue.put(client_socket, block=True, timeout=1.0)
                ColorPrints.print_in_purple(f"[QUEUEING] {client_addr} queued.")
            except queue.Full:
                pass
        else:
            # Add the client to the overflow queue
            try:
                overflow_queue.put(client_socket, block=True, timeout=1.0)
                logging.info(f"[OVERFLOW QUEUEING] {client_addr} queued in overflow queue.")
            except queue.Full:
                # The overflow queue is also full, reject the client
                client_socket.send("Sorry, the server is busy. Please try again later.".encode(FORMAT))
                client_socket.close()
                logging.warning(f"[OVERFLOW QUEUE FULL] {client_addr} rejected.")

        # Wait for a short time before connecting again
        time.sleep(1)

    logging.info(f"[FINISHED] {client_addr} finished connecting.")


def check_overflow_queue():
    while True:
        # Check if there is space in the main queue
        if not client_queue.full():
            # Move clients from the overflow queue to the main queue
            while not overflow_queue.empty():
                client_socket = overflow_queue.get()
                try:
                    client_queue.put(client_socket, block=True, timeout=1.0)
                    logging.info(f"[OVERFLOW DEQUEUEING] Client dequeued from overflow queue and queued in main queue.")
                except queue.Full:
                    # The main queue is full, put the client back in the overflow queue
                    overflow_queue.put(client_socket)
                    logging.info(f"[OVERFLOW REQUEUEING] Client put back in overflow queue.")
                    break
                
        time.sleep(OVERFLOW_CHECK_INTERVAL)


def start():
    # Create a thread pool of MAX_CONNECTIONS threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
        # Start the overflow queue checker
        overflow_checker = threading.Thread(target=check_overflow_queue)
        overflow_checker.daemon = True
        overflow_checker.start()

        # Accept clients and add them to the queue
        while True:
            try:
                client_socket, client_addr = server_socket.accept()
                logging.info(f"[NEW CONNECTION] {client_addr} connected.")
            except Exception as e:
                logging.error(f"[ERROR] {e}")
                continue

            # Add the client to the queue
            try:
                client_queue.put(client_socket, block=True, timeout=1.0)
                logging.info(f"[QUEUEING] {client_addr} queued.")
            except queue.Full:
                # The main queue is full, add the client to the overflow queue
                try:
                    overflow_queue.put(client_socket, block=True, timeout=1.0)
                    logging.info(f"[OVERFLOW QUEUEING] {client_addr} queued in overflow queue.")
                except queue.Full:
                    # The overflow queue is also full, reject the client
                    client_socket.send("Sorry, the server is busy. Please try again later.".encode(FORMAT))
                    client_socket.close()
                    logging.warning(f"[OVERFLOW QUEUE FULL] {client_addr} rejected.")

            # Submit the client connection to a free thread
            executor.submit(handle_client, client_socket, client_addr)


if __name__ == '__main__':
    start()