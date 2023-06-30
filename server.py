import socket
import queue
import logging
import concurrent.futures
import time

# Server configuration
SERVER_ADDRESS = ('localhost', 8000)
MAX_QUEUE_SIZE = 10
QUEUE_WAIT_TIME = 1

# Message configuration
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '!DISCONNECT'

# Set up logging
logging.basicConfig(level=logging.INFO)

def handle_client(client_socket, client_addr, q, overflow_list):
    #client_socket.settimeout(3)  # Set the timeout to 3 seconds

    logging.info(f"[NEW THREAD] Handling {client_addr}.")

    # Add the client to the queue or the overflow list
    try:
        q.put(client_socket, block=True, timeout=QUEUE_WAIT_TIME)
        logging.info(f"[QUEUEING] {client_addr} queued.")
    except queue.Full:
        # The queue is full, send the client to the overflow list
        overflow_list.append(client_socket)
        logging.warning(f"[QUEUE FULL] {client_addr} sent to overflow list.")

    # Receive messages from the client
    connected = True
    while connected:
        try:
            msg = client_socket.recv(1024).decode(FORMAT)
        except socket.timeout:
            # The client took too long to send a message
            logging.warning(f"[TIMEOUT] {client_addr} took too long to send a message.")
            break
        except ConnectionResetError:
            # Connection was reset by the client
            logging.warning(f"[CONNECTION RESET] {client_addr} connection was reset.")
            break

        if len(msg) == 0:
            # Connection was closed by the client
            logging.info(f"[CONNECTION CLOSED] {client_addr} connection was closed.")
            break

        if msg == DISCONNECT_MESSAGE:
            connected = False
            # Disconnect from the client
            client_socket.close()
            logging.info(f"[DISCONNECTED] {client_addr} disconnected.")
        else:
            logging.info(f"[{client_addr}] {msg}")

    # Remove the client from the queue or the overflow list
    try:
        q.get_nowait()
        logging.info(f"[DEQUEUEING] {client_addr} dequeued.")
    except queue.Empty:
        if client_socket in overflow_list:
            overflow_list.remove(client_socket)
            logging.info(f"[DEQUEUEING] {client_addr} dequeued from overflow list.")
        else:
            pass

def handle_overflow_list(q, overflow_list):
    while True:
        # Check if the queue has capacity
        if not q.full():
            # Move clients from the overflow list to the queue
            while len(overflow_list) > 0:
                client_socket = overflow_list.pop(0)
                q.put(client_socket, block=True, timeout=QUEUE_WAIT_TIME)
                logging.info(f"[QUEUEING] Client from overflow list queued.")
        # Wait for a certain amount of time before checking the queue again
        time.sleep(5)

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(SERVER_ADDRESS)
    server.listen()

    # Create a thread pool of 5 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        q = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        overflow_list = []
        executor.submit(handle_overflow_list, q, overflow_list)

        # Keep accepting client connections
        while True:
            # Wait for a client to connect
            try:
                client_socket, client_addr = server.accept()
            except KeyboardInterrupt:
                # Server was interrupted by the user
                logging.info("[SERVER INTERRUPTED] Server was interrupted by the user.")
                break
            except socket.timeout:
                # Timeout waiting for client connection
                continue
            except Exception as e:
                logging.error(f"[ERROR] {e}")
                continue

            logging.info(f"[NEW CONNECTION] {client_addr} connected.")

            # Submit the client connection to a free thread
            executor.submit(handle_client, client_socket, client_addr, q, overflow_list)

            # Print the current queue
            #logging.info(f"[QUEUE] Current queue: {q.queue}")

    # Remove the clients from the queue and the overflow list when done
    try:
        while True:
            client_socket = q.get_nowait()
            logging.info(f"[DEQUEUEING] Client dequeued.")
    except queue.Empty:
        pass
    try:
        while True:
            client_socket = overflow_list.pop(0)
            logging.info(f"[DEQUEUEING] Client dequeued from overflow list.")
    except IndexError:
        pass

    # Close the server socket
    server.close()

if __name__ == '__main__':
    start()