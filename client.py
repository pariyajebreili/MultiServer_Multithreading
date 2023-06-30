import socket
import logging
import concurrent.futures
import time
import queue

# Client configuration
SERVER_ADDRESS = ('localhost', 8000)
NUM_CONNECTIONS = 5
MAX_QUEUE_SIZE = 10
QUEUE_WAIT_TIME = 5  # Define the queue wait time in seconds

# Message configuration
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '!DISCONNECT'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Rest of the code goes here

def handle_client(client_socket):
    # Send a message to the server
    msg = 'Hello, server!'
    client_socket.send(msg.encode(FORMAT))

    # Receive a message from the server
    msg = client_socket.recv(1024).decode(FORMAT)
    logging.info(f"[RECEIVED] {msg}")

    # Disconnect from the server
    msg = DISCONNECT_MESSAGE
    client_socket.send(msg.encode(FORMAT))

    # Remove the client from the queue
    #q.get_nowait()
    client_socket.close()
    logging.info("[DISCONNECTED] Client disconnected.")



def start():
    # Create a thread pool of NUM_CONNECTIONS threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CONNECTIONS) as executor:
        while(True):
            answer = input('Would you like to connect (yes/no)? ')
            if answer.lower() != 'y':
                break
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect(SERVER_ADDRESS)
                logging.info(f"[NEW CONNECTION] Connected to {SERVER_ADDRESS}.")
            except Exception as e:
                logging.error(f"[ERROR] {e}")
                continue

            # Submit the client connection to a free thread
            executor.submit(handle_client, client_socket)
        # Wait for a certain amount of time before connecting to the next server
        time.sleep(1)

if __name__ == '__main__':
    start()