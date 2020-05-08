from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
from btcp.constants import *
import random
from queue import Queue, Empty

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
        self._sq = 0#last sequence number sent
        self._recv = 0#last sequence number received
        self._lastack = 0#last ackowledgenumber received
        self._serverwindow = 0
        self._padding = bytearray(bytes(1008))

    # Perform a three-way handshake to establish a connection
    def connect(self):
        self._sq = random.randint(0, 65535)
        #creating the BTCP segment with random x
        packet = BTCPSocket.create_packet(self, self._sq, 0, 1, self._window, 0, 0, self._padding)
        LossyLayer.send_segment(self._lossy_layer, packet)
        self._state = 1
        response = False
        i = 0
        #need to receive x+1 and y
        while not response and i <= NUMBER_OF_TRIES:
            try:
                segment = self._queue.get(timeout=self._timeout)
                response = True
                self._recv = int.from_bytes(segment[:2], "big")
                self._lastack = int.from_bytes(segment[2:4], "big")
                self._serverwindow = int.from_bytes(segment[5:6], "big")
                if self._lastack == self._sq + 1:
                    self._sq += 1
                    header2 = BTCPSocket.create_packet(self, self._sq, self._recv + 1, 1, self._window, 0, 0, self._padding)
                    LossyLayer.send_segment(self._lossy_layer, header2)
                    self._state = 2  # because from client side the handshake is done now
            except Empty:
                i += 1
                LossyLayer.send_segment(self._lossy_layer, packet)
        # because of the threeway handshake one packet
        # does not get acknowledged but the ack number
        # needs to be increased so it works for the
        # sending function with the comparison
        self._lastack += 1


    # Send data originating from the application in a reliable way to the server
    def send(self, data):
        segments, length = self.prepare_data(data)
        startSQ = self._sq
        #create a byte segment of PAYLOAD_SIZE
        for i in range(0, len(segments)):
            if self._serverwindow > 0:
                if i == len(segments)-1:#only for the last segment do we need to change the datalenght
                    datal = length
                else:
                    datal = PAYLOAD_SIZE
                packet = BTCPSocket.create_packet(self, self._sq + 1, self._recv + i, 1, self._window, datal, 0, segments[i])
                LossyLayer.send_segment(self._lossy_layer, packet)
                self._serverwindow -= 1
            try:
                response = self._queue.get(timeout=self._timeout)
                self._serverwindow = int.from_bytes(response[5:6], "big")
                ack = int.from_bytes(response[2:4], "big")
                if ack != self._lastack + 1:#apparently it did not receive the packets in order
                    #it needs to resend from the package on that has not been acknowledged yet
                    i = ack - startSQ
                # somehow have to compare which sequence number he acknowledged so that it is still in order
            except Empty:
                i -= 1 #because the same element needs to try to send again then

    # returns a list of data sections, each containing exactly 1008 bytes
    def prepare_data(self, data):
        data_sections = []
        data_bytearray = bytearray(data, 'utf-8')  # bytearray instead of bytes because we want it to be muteable

        while len(data_bytearray) > PAYLOAD_SIZE:
            data_sections.append(data_bytearray[:PAYLOAD_SIZE])
            data_bytearray = data_bytearray[PAYLOAD_SIZE:]

        # note: len(data_bytearray) <= PAYLOAD_SIZE
        # Possibly add padding to reach the PAYLOAD_SIZE
        padding_size = PAYLOAD_SIZE - len(data_bytearray)
        padding = bytes(padding_size)  # this creates the right amount of 'zero bytes'
        data_bytearray += padding

        data_sections.append(data_bytearray)
        return data_sections, PAYLOAD_SIZE-padding_size



    # Perform a handshake to terminate a connection
    def disconnect(self):
        packet =BTCPSocket.create_packet(self, self._sq + 1, self._recv + 1, 4, self._window, 0, 0, self._padding)
        LossyLayer.send_segment(self._lossy_layer, packet)
        response = False
        i = 0
        while not response and i <= NUMBER_OF_TRIES:
            try:
                segment = self._queue.get(timeout=self._timeout)
                flags = int.from_bytes(segment[4:5], "big")
                if flags == 5:  # if the ACK and FIN flag are set
                    response = True
            except Empty:
                LossyLayer.send_segment(self._lossy_layer, packet)  # tries sending again in case of no response
                i += 1

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()

    # Called by the lossy layer from another thread whenever a segment arrives.
    def lossy_layer_input(self, segment, addr):
        self._queue.put(segment)
