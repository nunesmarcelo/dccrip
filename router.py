#   TP 2 - Redes - DDCNET
#   Marcelo Nunes da Silva
#   Wanderson Sena
import sys
import socket
import threading
import json

#!/usr/bin/python3
class DCCRIP:
    def __init__(self):
        #Leituras stdin
        self.myAddress = sys.argv[1]
        self.period      = sys.argv[2]
        self.port = 55151
        if(len(sys.argv) > 3):
            self.input = open(sys.argv[3], 'r')
        else:
            self.input = sys.stdin
        
        # Target , Cost , NextStep , TimeOut
        self.rountingTable = {}
        self.rountingTable[self.myAddress] = { 'Cost' : 0 , 'NextStep' : self.myAddress , 'TimeOut' : -1}

        # Neighbor , Cost
        self.neighborsTable = {}

  
    def startListen(self):
        sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP
        sock.bind((self.myAddress, self.port))

        while True:
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            data = data.loads(data)

            if(data['type'] == 'update'):
                distances = data['distances']
                for address in distances:
                    # If old cost greater than new cost -> swap
                    if ((address not in self.rountingTable.keys()) or self.rountingTable[address]['Cost']  > distances[address]['Cost'] + self.neighborsTable[address]['Cost']):
                        self.rountingTable[address]['Cost'] = distances[address]['Cost'] + self.neighborsTable[address]['Cost']
                        self.rountingTable[address]['Target'] = address
                        

    def meetNeighbors(self):
        self.addToNeighborTable(self.myAddress, 0)
        readCount = self.input.readline()
        while readCount:
            if readCount.split(' ')[0] == 'add':
                self.addToNeighborTable(readCount.split(' ')[1] , readCount.split(' ')[2] )

        readCount = self.input.readline()

    def addToNeighborTable( self, address , cost ):
        self.neighborsTable[address] = {'Cost' : cost }

    def sendUpdate(self):
        sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP

        for key in self.neighborsTable:

            # Make a copy of neighbor dict and del the target address before send
            distances = self.neighborsTable
            del distances[key] 

            message = { 
                'type'  : 'update',
                'source': self.myAddress ,  
                'destination': key,
                'distances': distances
            }
            sock.sendto(message, (key, self.port))

    def execution(self):
        listen = threading.Thread(target = self.startListen)
        listen.start()

        self.meetNeighbors()

        timer = threading.Timer(self.period, self.sendUpdate())
        timer.start()
        

if __name__ == "__main__":
    route = DCCRIP()
    route.execution()

# logging: http://zeldani.blogspot.com/2012/08/python-usando-o-modulo-threading.html