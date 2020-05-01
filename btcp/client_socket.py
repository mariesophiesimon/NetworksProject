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
#ACK, SYN, FIN      7

# bTCP client socket
# A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close
class BTCPClientSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)
        self._queue = Queue()
        self._state = 0
        self._sq = 0#last squence number sent
        self._lastack = 0#last ackowledgenumber received

    # Perform a three-way handshake to establish a connection
    def connect(self):
        x = random.randint(0, 65535)
        #creating the BTCP segment with random x
        header = BTCPSocket.create_header(self, x, 0, 1, self._window, 0, 0)
        LossyLayer.send_segment(self._lossy_layer, header)
        self._state = 1
        response = False
        i = 0
        #need to receive x+1 and y
        while not response and i <= NUMBER_OF_TRIES:
            while(self._timeout > 0):#waits for a response
                segment = self._queue.get()
                response = True
                self._sq = int.from_bytes(segment[:2], "big")
                self._lastack = int.from_bytes(segment[2:4], "big")
                if self._lastack == x+1:
                    header = BTCPSocket.create_header(self, self._lastack, self._sq +1, 1, self._window, 0, 0)
                    LossyLayer.send_segment(self._lossy_layer, header)
                    self._state = 2  # because from client side the handshake is done now
                    print("CLient state 2")
            if not response:
                LossyLayer.send_segment(self._lossy_layer, header)#if no response comes within the given time it tries again
                i += 1

    # Send data originating from the application in a reliable way to the server
    def send(self, data):
        pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()

    # Perform a handshake to terminate a connection
    def disconnect(self):
        header =BTCPSocket.create_header(self, self._lastack, self._sq +1, 4, self._window, 0, 0)
        LossyLayer.send_segment(self._lossy_layer, header)
        #some state
        response = False
        i = 0
        while not response and i <= NUMBER_OF_TRIES:
            while(self._timeout > 0):#waits for a response
                segment = self._queue.get()
                response = True
                flags = int.from_bytes(segment[4:5], "big")
                if flags == 5:#if the ACK and FIN flag are set
                    self.close(self)
            if not response:
                LossyLayer.send_segment(self._lossy_layer, header)#tries sending again in case of no response
                i += 1
        self.close(self)#in case it never receives anything it still closes the connection

    # Called by the lossy layer from another thread whenever a segment arrives.
    def lossy_layer_input(self, segment, addr):
        self._queue.put(segment)
