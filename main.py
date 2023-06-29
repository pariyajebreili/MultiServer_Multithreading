import socket
import threading
import random
import time

NUM_STUDENTS = 10
NUM_PROFESSORS = 3
COUNSELING_TIME = 10


class Professor:
    def __init__(self, id):
        self.id = id
        self.available = True
        self.lock = threading.Lock()

    def __repr__(self):
        return f"Professor {self.id}"


class Student:
    def __init__(self, id, counseling_times):
        self.id = id
        self.counseling_times = counseling_times
        self.finished_practice = False
        self.professor = None
        self.sessions = []

    def __repr__(self):
        return f"Student {self.id}"


class Session:
    def __init__(self, professor, duration):
        self.professor = professor
        self.duration = duration

    def __repr__(self):
        return f"Session with {self.professor} ({self.duration:.2f} seconds)"


def professor_thread(professor, waiting_room):
    # Create a socket for the professor thread
    professor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    professor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a local address and port
    professor_socket.bind(('localhost', 0))
    professor_port = professor_socket.getsockname()[1]
    print(f"{professor} listening on port {professor_port}")

    # Register the professor with the waiting room
    waiting_room_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    waiting_room_socket.connect(('localhost', 9999))
    professor_info = f"{professor.id}:{professor_port}"
    waiting_room_socket.send(professor_info.encode())
    waiting_room_socket.close()

    # Listen for connections from students
    professor_socket.listen()
    while True:
        student_socket, student_addr = professor_socket.accept()
        print(f"{professor} received a connection from {student_addr}")

        # Receive the student's ID and port
        student_info = student_socket.recv(1024).decode()
        student_id, student_port = student_info.split(':')
        student_port = int(student_port)
        student = Student(student_id, 2)

        # Connect to the student's socket
        student_socket.close()
        student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        student_socket.connect(('localhost', student_port))

        # Wait for the student to enter the waiting room
        message = student_socket.recv(1024).decode()
        if message != "enter":
            print(f"{professor} received unexpected message from {student}: {message}")
            student_socket.close()
            continue

        # Send a message to the waiting room that the professor is available
        professor.available = True
        waiting_room_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        waiting_room_socket.connect(('localhost', 9999))
        waiting_room_socket.send("available".encode())
        waiting_room_socket.close()

        # Wait for the student to be ready for counseling
        message = student_socket.recv(1024).decode()
        if message != "ready":
            print(f"{professor} received unexpected message from {student}: {message}")
            student_socket.close()
            continue

        # Start the counseling session
        start_time = time.monotonic()
        print(f"{professor} is counseling {student}")
        time.sleep(COUNSELING_TIME)
        end_time = time.monotonic()
        duration = end_time - start_time
        student.sessions.append(Session(professor, duration))
        print(f"{professor} finished counseling {student} ({duration:.2f} seconds)")
        professor.available = True
        student_socket.close()


def student_thread(student, waiting_room, professors):
    # Create a socket for the student thread
    student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    student_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a local address and port
    student_socket.bind(('localhost', 0))
    student_port = student_socket.getsockname()[1]
    print(f"{student} listening on port {student_port}")

    waiting_room_socket = None

    try:
        # Connect to a professor
        professor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        professor_socket.connect(('localhost', 8888))
        print(f"{student} connected to professor")

        # Send the student's ID and port to the professor
        student_info = f"{student.id}:{student_port}"
        professor_socket.send(student_info.encode())

        # Accept a connection from the waiting room
        student_socket.listen()
        waiting_room_socket, waiting_room_addr = student_socket.accept()
        print(f"{student} entered waiting room")

        # Wait for a professor tobe available
        while True:
            # Check if there are any available professors
            available_professors = [p for p in professors if p.available]
            if not available_professors:
                # If there are no available professors, wait for a random amount of time before checking again
                wait_time = random.randint(1, 5)
                print(f"{student} is waiting for {wait_time} seconds")
                time.sleep(wait_time)
                continue

            # Choose a random available professor
            professor = random.choice(available_professors)

            # Connect to the professor's socket
            professor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            professor_socket.connect(('localhost', professor.port))

            # Send a message to the professor that the student is ready
            professor_socket.send("ready".encode())

            # Wait for the professor to accept the connection
            message = professor_socket.recv(1024).decode()
            if message != "accept":
                print(f"{student} received unexpected message from {professor}: {message}")
                professor_socket.close()
                continue

            # Start the counseling session
            student.professor = professor
            professor.available = False
            session = Session(professor, COUNSELING_TIME)
            student.sessions.append(session)
            print(f"{student} started a counseling session with {professor}")

            # Connect to the student's socket and send a message that the professor has accepted the connection
            student_socket.close()
            student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            student_socket.connect(('localhost', student_port))
            student_socket.send("accept".encode())

            # Wait for the counseling session to finish
            time.sleep(COUNSELING_TIME)

            # End the counseling session
            professor_socket.close()
            professor.available = True
            print(f"{student} finished counseling session with {professor}")
    finally:
        if waiting_room_socket:
            waiting_room_socket.close()
        student_socket.close()


def waiting_room_thread(waiting_room, professors):
    # Create a socket for the waiting room thread
    waiting_room_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    waiting_room_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a local address and port
    waiting_room_socket.bind(('localhost', 9999))
    print("Waiting room is open")

    # Listen for connections from professors and students
    waiting_room_socket.listen()
    while True:
        client_socket, client_addr = waiting_room_socket.accept()
        print(f"Waiting room received a connection from {client_addr}")

        # Receive the client's information
        client_info = client_socket.recv(1024).decode()
        client_id, client_port = client_info.split(':')
        client_port = int(client_port)

        # Register the client with the waiting room
        if isinstance(client_id, int) and client_id < NUM_STUDENTS:
            # If the client is a student, add them to the waiting room
            student = Student(client_id, 2)
            waiting_room.append(student)
            print(f"{student} entered the waiting room")

            # Connect to the student's socket and send a message that they can enter the waiting room
            student_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            student_socket.connect(('localhost', client_port))
            student_socket.send("enter".encode())
            student_socket.close()
        elif isinstance(client_id, int) and client_id < NUM_STUDENTS + NUM_PROFESSORS:
            # If the client is a professor, add them to the list of professors
            professor = Professor(client_id - NUM_STUDENTS)
            professor.port = client_port
            professors.append(professor)
            print(f"{professor} entered the waiting room")
        else:
            print(f"Received unexpected client ID: {client_id}")

        client_socket.close()
def main():
    waiting_room = []
    professors = []

    # Start the waiting room thread
    waiting_room_thread_obj = threading.Thread(target=waiting_room_thread, args=(waiting_room, professors))
    waiting_room_thread_obj.start()

    # Start the professor threads
    professor_threads = []
    for i in range(NUM_PROFESSORS):
        professor = Professor(i)
        professor_thread_obj = threading.Thread(target=professor_thread, args=(professor, waiting_room))
        professor_threads.append(professor_thread_obj)
        professor_thread_obj.start()

    # Start the student threads
    student_threads = []
    for i in range(NUM_STUDENTS):
        student = Student(i, 2)
        student_thread_obj = threading.Thread(target=student_thread, args=(student, waiting_room, professors))
        student_threads.append(student_thread_obj)
        student_thread_obj.start()

    # Wait for all threads to finish
    for thread in professor_threads + student_threads:
        thread.join()
    waiting_room_thread_obj.join()


if __name__ == '__main__':
    main()