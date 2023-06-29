import socket
import time


PORT = 5050
SERVERS = 5
ADDR = ("localhost", PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"


def connect():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(SERVERS):
        try:
            client.connect(("localhost", PORT+i))
            return client
        except ConnectionRefusedError:
            # Server is busy, try the next server
            continue
    # All servers are busy, raise an exception
    raise ConnectionRefusedError("All servers are busy")


def send(client, msg):
    message = msg.encode(FORMAT)
    client.send(message)


def start():
    # Connect to up to 20 servers
    for i in range(20):
        answer = input('Would you like to connect (yes/no)? ')
        if answer.lower() != 'yes':
            break

        connection = None
        while connection is None:
            try:
                connection = connect()
            except ConnectionRefusedError:
                # All servers are busy, wait and try again
                time.sleep(1)

        while True:
            msg = input("Message (q for quit): ")

            if msg == 'q':
                break

            send(connection, msg)

        send(connection, DISCONNECT_MESSAGE)
        time.sleep(1)
        print('Disconnected')


if __name__ == '__main__':
    start()