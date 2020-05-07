import socket
from btcp.lossy_layer import LossyLayer
from btcp.btcp_socket import BTCPSocket
from btcp.constants import *
import random
from queue import Queue, Empty

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
        self._sq = 0#last sequence number sent
        self._recv = 0#last sequence number received
        self._lastack = 0#last acknowledgement number received
        self._clientwindow = 0
        self._padding = bytearray(bytes(1008))
        self._message = bytearray(bytes(0))

    # Wait for the client to initiate a three-way handshake
    def accept(self):
        segment = self._queue.get()
        self._recv = int.from_bytes(segment[:2], "big")
        self._sq = random.randint(0, 65535)
        packet = BTCPSocket.create_packet(self, self._sq, self._recv + 1, 3, self._window, 0, 0, self._padding)
        LossyLayer.send_segment(self._lossy_layer, packet)
        self._lastack = self._recv +1
        segment = self._queue.get()
        x = int.from_bytes(segment[:2], "big")
        y = int.from_bytes(segment[2:4], "big")
        self._clientwindow = int.from_bytes(segment[5:6], "big")
        if self._lastack == x and self._sq + 1 == y:
            self._lastack = y
            self._recv = x
        #a client has successfully connected

    # Send any incoming data to the application layer
    def recv(self):
        #so I guess in here we need to check for the FIN flag to close the connection
        try:
            segment = self._queue.get()
            sq = int.from_bytes(segment[:2], "big")
            self._lastack = int.from_bytes(segment[2:4], "big")
            flags = int.from_bytes(segment[4:5], "big")
            if flags >= 4:  # so if FIN flag is set (maybe also other flags)
                self._sq += 1
                packet = BTCPSocket.create_packet(self, self._sq, sq + 1, 5, self._window, 0, 0,self._padding)
                LossyLayer.send_segment(self._lossy_layer, packet)
                return False
            else:  # every normal packet that does not finish the connection
                length = int.from_bytes(segment[6:8], "big")
                self._message += segment[10:(10+length)]
                self._sq += 1
                packet = BTCPSocket.create_packet(self, self._sq, sq +1, flags, self._window, 0, 0, self._padding)
                LossyLayer.send_segment(self._lossy_layer, packet)
                return True
        except Empty:
            pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, addr):
        # received the clients request and sends its response back
        self._queue.put(segment)