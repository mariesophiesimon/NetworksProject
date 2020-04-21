from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
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

# bTCP client socket
# A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close
class BTCPClientSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)
        self._queue = Queue()
        self._state = 0
        self._sq = 0
        self._lastack = 0

    # Perform a three-way handshake to establish a connection
    def connect(self):
        x = random.randint(0, 65535)
        #creating the BTCP segment with random x
        header = BTCPSocket.create_header(self, x, 0, 1, self._window, 0, 0)
        LossyLayer.send_segment(self._lossy_layer, header)
        self._state = 1
        #need to receive x+1 and y
        segment = self._queue.get()
        self._sq = int.from_bytes(segment[:2], "big")
        self._lastack = int.from_bytes(segment[2:4], "big")
        if self._lastack == x+1:
            header = BTCPSocket.create_header(self, self._lastack, self._sq +1, 1, self._window, 0, 0)
            LossyLayer.send_segment(self._lossy_layer, header)
            self._state = 2  # because from client side the handshake is done now
            print("CLient state 2")

    # Send data originating from the application in a reliable way to the server
    def send(self, data):
        pass

    # Perform a handshake to terminate a connection
    def disconnect(self):
        pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()

    # Called by the lossy layer from another thread whenever a segment arrives.
    def lossy_layer_input(self, segment, addr):
        self._queue.put(segment)
