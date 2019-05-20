#!/usr/bin/python3

#   TP 2 - Redes - DDCNET
#   Marcelo Nunes da Silva
#   Wanderson Sena
import sys
import socket
import threading
import json
import signal
import time
import os

class DCCRIP:
    def __init__(self):

        if (len(sys.argv)< 3):
            print("input failure. Correct pattern:")
            print("\t./router.py <address> <period> <startup (optional)>")
            os._exit(0)

        #Leituras stdin
        self.myAddress = sys.argv[1]
        self.period      = sys.argv[2]
        self.port = 55151

        self.input = open(sys.argv[3], 'r') if len(sys.argv) > 3 else None
        
        # Target , Cost , NextStep , TimeOut
        self.rountingTable = {}
        self.rountingTable[self.myAddress] = { 'Cost' : 0 ,'NextStep' : self.myAddress , 'TimeOut' : -1}

        # Neighbor , Cost
        self.neighborsTable = {}

        try:
            self.con = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Internet # UDP
            self.con.bind((self.myAddress, self.port))
        except socket.error as err:
            print("Socket error:" , err)
            sys.exit(0)
    
    def execution(self):
        try:
            startListen = threading.Thread(target = self.startListen)
            startListen.start()
            
            startInput = threading.Thread(target = self.meetNeighbors)
            startInput.start()

            startListen.join()
            startInput.join()
            
        except KeyboardInterrupt:
            print("\n")
            self.con.close()
            if self.input != None:
                self.input.close()
            os._exit(1)
            

  
    def startListen(self):
        while True:
            try:
                print("lendo")
                data, addr = self.con.recvfrom(1024) # buffer size is 1024 bytes
                print("lido")
            except KeyboardInterrupt:
                raise KeyboardInterrupt

            print("Update received")
            data = json.loads( bytes.decode( data) )

            if(data['type'] == 'update'):
                distances = data['distances']
                for address in distances:
                    # If old cost greater than new cost -> swap
                    if ((address not in self.rountingTable.keys()) or self.rountingTable[address]['Cost']  > distances[address]['Cost'] + self.neighborsTable[address]['Cost']):
                        self.rountingTable[address]['Cost'] = distances[address]['Cost'] + self.neighborsTable[address]['Cost']
                        self.rountingTable[address]['Target'] = address
      
    def meetNeighbors(self):
        try:
            print('meet Neighbors')
            self.addToNeighborTable(self.myAddress, 0)
            readCount = self.input.readline() if self.input != None else input()
            while readCount:
                if readCount.split(' ')[0] == 'add':
                    if len(readCount.split(' ')) <= 2:
                        print("Input failure. Correct pattern:")
                        print("add <address> <cost>")
                    else:
                        self.addToNeighborTable(readCount.split(' ')[1] , readCount.split(' ')[2] )
                                
                if readCount.split(' ')[0] == 'print':
                    self.imprimirTabelas()

                readCount = self.input.readline() if self.input != None else input()
        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def addToNeighborTable( self, address , cost ):
        self.neighborsTable[address] = {'Cost' : cost }

    def sendUpdate(self):
        sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP

        for key in self.neighborsTable.copy():
            print("Send Update")
            if key == self.myAddress: continue

            # Make a copy of neighbor dict and del the target address before send
            distances = self.rountingTable
            del distances[key] 

            message = { 
                'type'  : 'update',
                'source': self.myAddress ,  
                'destination': key,
                'distances': distances
            }
            sock.sendto(str.encode( json.dumps( message ) ), (key, self.port))
            print("Update Sended")
        #self.sendUpdateTimer.start()

    def imprimirTabelas(self):
        #threading.Timer(7 , self.imprimirTabelas).start()
        print("-"*40)
        print("Tabela de vizinhos: " , self.neighborsTable)
        print("Tabela de roteamento (GERAL)" , self.rountingTable)
        print("-"*40)
    
        

if __name__ == "__main__":
    try:
        route = DCCRIP()
        route.execution()
    except Exception as e:
        print("Na main: " + e)
        sys.exit(0)

# logging: http://zeldani.blogspot.com/2012/08/python-usando-o-modulo-threading.html