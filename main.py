import threading
import time
import queue


WAITING_ROOM_CAPACITY = 20
COUNSELING_TIMES = 4
PROFESSORS_COUNT = 4
STUDENTS_COUNT = 30
WAITING_TIME = 5  # in seconds
COUNSELING_TIME = 10  # in seconds


class Professor:
    def __init__(self, name):
        self.name = name
        self.available = True  # whether the professor is available for counseling

    def __repr__(self):
        return f"Professor {self.name}"


class Student:
    def __init__(self, name):
        self.name = name
        self.counseling_times = COUNSELING_TIMES  # the number of times the student needs to be counseled
        self.finished_practice = False  # whether the student is finished practicing

    def __repr__(self):
        return f"Student {self.name}"


class WaitingRoom:
    def __init__(self):
        self.queue = queue.Queue(maxsize=WAITING_ROOM_CAPACITY)
        self.lock = threading.Lock()

    def add_student(self, student):
        with self.lock:
            if self.queue.full():
                return False  # the waiting room is full
            else:
                self.queue.put(student)
                return True

    def remove_student(self):
        with self.lock:
            if not self.queue.empty():
                student = self.queue.get()
                return student
            else:
                return None  # the waiting room is empty


def professor_thread(professor, waiting_room):
    while True:
        # Check if there are students in the waiting room
        student = waiting_room.remove_student()
        if student is not None:
            print(f"{professor} is counseling {student}")
            time.sleep(COUNSELING_TIME)
            student.counseling_times -= 1
            if student.counseling_times == 0:
                student.finished_practice = True
            else:
                print(f"{student} goes back to practice")
                time.sleep(WAITING_TIME)
                waiting_room.add_student(student)
        else:
            professor.available = True
            print(f"{professor} is waiting for a student")


def student_thread(student, waiting_room, professors):
    while True:
        # Try to enter the waiting room
        entered = waiting_room.add_student(student)
        if entered:
            print(f"{student} entered the waiting room")
            break  # student entered the waiting room
        else:
            print(f"{student} went back to the library")
            time.sleep(WAITING_TIME)

    while not student.finished_practice:
        # Check if there is an available professor
        professor = None
        for p in professors:
            if p.available:
                professor = p
                break
        if professor is not None:
            professor.available = False
            print(f"{professor} is counseling {student}")
            time.sleep(COUNSELING_TIME)
            student.counseling_times -= 1
            if student.counseling_times == 0:
                student.finished_practice = True
            else:
                print(f"{student} goes back to practice")
                time.sleep(WAITING_TIME)
                waiting_room.add_student(student)
        else:
            print(f"{student} is waiting for a professor")
            time.sleep(WAITING_TIME)


if __name__ == "__main__":
    # Create professors and waiting room
    professors = [Professor(i) for i in range(PROFESSORS_COUNT)]
    waiting_room = WaitingRoom()

    # Create and start student threads
    students = [Student(i) for i in range(STUDENTS_COUNT)]
    student_threads = []
    for student in students:
        t = threading.Thread(target=student_thread, args=(student, waiting_room, professors))
        student_threads.append(t)
        t.start()

    # Create and start professor threads
    professor_threads = []
    for professor in professors:
        t = threading.Thread(target=professor_thread, args=(professor, waiting_room))
        professor_threads.append(t)
        t.start()

    # Wait for all student threads to finish
    for t in student_threads:
        t.join()

    # Wait for all professor threads to finish
    for t in professor_threads:
        t.join()