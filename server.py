import socket
import logging
import concurrent.futures
from queue import Queue
import time
import threading 

# Server configuration
SERVER_ADDRESS = ('localhost', 8000)
MAX_CONNECTIONS = 5
MAX_QUEUE_SIZE = 5
OVERFLOW_QUEUE_SIZE = 50
IDLE_TIMEOUT = 3  # Define the idle timeout in seconds
OVERFLOW_CHECK_INTERVAL = 3  # Define the overflow check interval in seconds

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(SERVER_ADDRESS)
server_socket.listen(MAX_CONNECTIONS)
logging.info(f"[LISTENING] Server is listening on {SERVER_ADDRESS}.")

# Set up a queue to hold incoming clients
client_queue = Queue(maxsize=MAX_QUEUE_SIZE)

# Set up an overflow queue to hold clients when the main queue is full
overflow_queue = Queue(maxsize=OVERFLOW_QUEUE_SIZE)

# Set up semaphore objects to control access to the queues
client_queue_semaphore = threading.Semaphore(1)
overflow_queue_semaphore = threading.Semaphore(1)


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
                msg = client_socket.recv(1024).decode()
            except socket.timeout:
                # The client is idle, disconnect it
                #logging.error(f"[IDLE TIMEOUT] {client_addr} disconnected.")
                connected = False
                break

            if len(msg) == 0:
                # Connection was closed by the client
                logging.info(f"[CONNECTION CLOSED] {client_addr} connection was closed.")
                break

            if msg == "!DISCONNECT":
                connected = False
                # Disconnect from the client
                client_socket.close()
                logging.info(f"[DISCONNECTED] {client_addr} disconnected.")

                # Remove the client from the queue if it is still waiting
                with client_queue_semaphore:
                    if client_socket in client_queue.queue:
                        client_queue.queue.remove(client_socket)
                        logging.info(f"[REMOVING FROM QUEUE] {client_addr} removed from queue.")
                    elif client_socket in overflow_queue.queue:
                        overflow_queue.queue.remove(client_socket)
                        logging.info(f"[REMOVING FROM OVERFLOW QUEUE] {client_addr} removed from overflow queue.")
            else:
                logging.info(f"[{client_addr}] {msg}")

        # Remove the client from the queue
        with client_queue_semaphore:
            try:
                client_queue.get_nowait()
                logging.info(f"[DEQUEUEING] {client_addr} dequeued.")
            except:
                pass

        # Check if there is space in the main queue
        if not client_queue.full():
            # Add the client to the main queue
            with client_queue_semaphore:
                try:
                    client_queue.put(client_socket, block=True, timeout=1.0)
                    logging.info(f"[QUEUEING] {client_addr} queued.")
                except:
                    pass
        else:
            # Add the client to the overflow queue
            with overflow_queue_semaphore:
                try:
                    overflow_queue.put(client_socket, block=True, timeout=1.0)
                    logging.info(f"[OVERFLOW QUEUEING] {client_addr} queued in overflow queue.")
                except :
                    # The overflow queue is also full, reject the client
                    client_socket.send("Sorry, the server is busy. Please try again later.".encode())
                    client_socket.close()

def overflow_queue_worker():
    """
    This function checks the overflow queue and moves clients from the overflow queue
    to the main queue if there is space available.
    """
    while True:
        time.sleep(OVERFLOW_CHECK_INTERVAL)
        with client_queue_semaphore:
            with overflow_queue_semaphore:
                while not client_queue.full() and not overflow_queue.empty():
                    client_socket = overflow_queue.get()
                    client_queue.put(client_socket)
                    logging.info(f"[OVERFLOW DEQUEUEING] {client_socket.getpeername()} dequeued from overflow queue and queued in main queue.")


# Start the overflow queue worker thread
overflow_queue_thread = threading.Thread(target=overflow_queue_worker)
overflow_queue_thread.start()

# Set up a thread pool to handle clients
executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS)
while True:
    # Accept clients
    client_socket, client_addr = server_socket.accept()

    # Submit the client to the thread pool
    executor.submit(handle_client, client_socket, client_addr)