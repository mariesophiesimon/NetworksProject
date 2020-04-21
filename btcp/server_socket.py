import socket
from btcp.lossy_layer import LossyLayer
from btcp.btcp_socket import BTCPSocket
from btcp.constants import *
import random
from queue import Queue

#flags[0] = ACK     1
#flags[1] = SYN     2
#flags[2] = FIN     4
#ACK, SYN           3
#ACK, FIN           5
#SYN, FIN           6
#ACK, SYN, FIN      8

# The bTCP server socket
# A server application makes use of the services provided by bTCP by calling accept, recv, and close
class BTCPServerSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)
        self._queue = Queue()
        self._state = 0
        self._sq = 0
        self._lastack = 0

    # Wait for the client to initiate a three-way handshake
    def accept(self):
        segment = self._queue.get()
        x = int.from_bytes(segment[:2], "big")
        y = random.randint(0, 65535)
        header = BTCPSocket.create_header(self, y, x + 1, 3, self._window, 0, 0)
        LossyLayer.send_segment(self._lossy_layer, header)
        self._lastack = x+1
        self._sq = y
        segment = self._queue.get()
        x = int.from_bytes(segment[:2], "big")
        y = int.from_bytes(segment[2:4], "big")
        if self._lastack == x and self._sq+1 == y:
            self._state = 2
            print("Server state 2")
        #a client has successfully connected

    # Send any incoming data to the application layer
    def recv(self):
        pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, addr):
        # received the clients request and sends its response back
        self._queue.put(segment)