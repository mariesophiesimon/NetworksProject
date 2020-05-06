import struct

class BTCPSocket:
    def __init__(self, window, timeout):
        self._window = window
        self._timeout = timeout
   
    # Return the Internet checksum of data
    @staticmethod
    def in_cksum(data):
        #checksum from Marie's code of week 2
        sum = 0
        for x in range(0, len(data), 2):#from 0 to length of data in steps of 2
            if(x+1 <= len(data)-1):
                word = data[x] + (data[x+1] << 8)
            else:#in case it is not an even number we append a byte of 0s
                word = data[x] + (bytes(1) << 8)
            sum += word
        while(sum >> 16) > 0:
            sum = (sum & 0xFFFF) + (sum >> 16)
        checksum = (~sum & 0xFFFF)
        return checksum

    #creates a dummy packet first to calculate the checksum and then creates the real packet to be sent
    def create_packet(self, sqn, ack, flags, wind, datal, cksum, data):
        #sequence number
        #acknowledgement number
        #flags
        #window size
        #data length
        #checksum
        #data
        header = struct.pack("!HHbbHH",
                            sqn,
                            ack,
                            flags,
                            wind,
                            datal,
                            cksum)
        header += data
        checksum = BTCPSocket.in_cksum(header)
        header = struct.pack("!HHbbHH",
                             sqn,
                             ack,
                             flags,
                             wind,
                             datal,
                             checksum)
        header += data
        return header