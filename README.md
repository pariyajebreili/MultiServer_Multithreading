# MultiServer_Multithreading
# Brief summary of this project
This project use threading library to create servers.if the number of clients exceeds maximum main queue size then we put those client into overflow queue and clients which are in the overflow queue checks every 3 seconds if the main queue has free space.
This project use sempaphore to avoid race condition.
This project use socket for communication.

# Installation
1.
```bash
git clone https://github.com/pariyajebreili/
```
2.
```bash
python server.py
```
3.
```bash
python client.py
```
    