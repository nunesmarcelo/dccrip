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

        #inputs from terminal
        self.myAddress = sys.argv[1]
        self.period      = sys.argv[2]
        self.port = 55151

        self.input = open(sys.argv[3], 'r') if len(sys.argv) > 3 else None
        
        # IP : Weight | IP : NextStep
        self.routingWeightTable = {}
        self.routingNextStepTable = {}
        self.routingWeightTable[self.myAddress] = 0
        self.routingNextStepTable[self.myAddress] = self.myAddress

        # IP : Weight
        self.neighborsTable = {}

        try:
            self.con = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
            self.con.bind((self.myAddress, self.port)) # bind instance
        except socket.error as err:
            print("Socket error:" , err)
            sys.exit(0)
    
    def execution(self):
        try:
            startListen = threading.Thread(target = self.listenUpdates)
            startListen.start()
            
            startInput = threading.Thread(target = self.listenInputs)
            startInput.start()

            self.startSend = threading.Timer( float(self.period) ,  self.sendUpdates) # Timer
            self.startSend.start()

            startListen.join()
            startInput.join()
            self.startSend.join()
            
        except KeyboardInterrupt:
            print("\n")
            self.con.close()
            if self.input != None:
                self.input.close()
            os._exit(1)
            

    def listenUpdates(self):
        while True:
            try:
                data, addr = self.con.recvfrom(1024) # buffer size is 1024 bytes
            except KeyboardInterrupt:
                raise KeyboardInterrupt

            data = json.loads( bytes.decode( data) )
            if(data['type'] == 'update'):
                distances = data['distances']
                
                for address in distances:
                    print(distances , "         source: " , data['source'])
                    #If is my neighbor but i don't know him
                    if((address not in self.neighborsTable and distances[address] == 0)): 
                        continue 
                    
                    # If old weight greater than new weight -> swap
                    if ((address not in self.routingWeightTable.keys()) or int(self.routingWeightTable[address])  > int(distances[address]) + int(self.neighborsTable[data['source']])):
                        self.routingWeightTable[address] = int(distances[address]) + int(self.neighborsTable[data['source']])
                        self.routingNextStepTable[address] = data['source']
      
    def listenInputs(self):
        try:
            readCount = self.input.readline() if self.input != None else input() #input() if has no file open, or readline() else.
            while readCount:
                print(readCount)
                if readCount.split(' ')[0] == 'add':
                    if len(readCount.split(' ')) <= 2:
                        print("Input failure. Correct pattern:")
                        print("add <ip> <weight>")
                    else:
                        self.routingWeightTable[readCount.split(' ')[1] ] = readCount.split(' ')[2]
                        self.routingNextStepTable[readCount.split(' ')[1] ] = readCount.split(' ')[1]
                        self.neighborsTable[readCount.split(' ')[1]] = readCount.split(' ')[2]
                        self.sendUpdates()
       
                if readCount.split(' ')[0] == 'print':
                    self.imprimirTabelas()

                readCount = self.input.readline() if self.input != None else input()
        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def sendUpdates(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
            for key in self.neighborsTable:

                # Make a dict of type -> 'ip' : 'cost' 
                distances = self.routingWeightTable.copy()
                if key in distances.keys():
                    del distances[key]

                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': key,
                    'distances': distances
                }
                sock.sendto(str.encode( json.dumps( message ) ), (key, self.port))
            
            self.startSend = threading.Timer( float(self.period) , self.sendUpdates)
            self.startSend.start()
        except:
            print('veio aqui embaixo')
            os._exit(0)

    def imprimirTabelas(self):
        #threading.Timer(7 , self.imprimirTabelas).start()
        try:
            print("-"*40)
            print("**** VIZINHOS ----- ")
            for k in self.neighborsTable:
                print(k , "---> " , self.neighborsTable[k])

            print('**** PESOS ----')
            for k in self.routingWeightTable:
                print(k , ' ---> ' , self.routingWeightTable[k]) 

            print('**** NEXT -----')
            for k in self.routingNextStepTable:
                print(k , ' ---> ' , self.routingNextStepTable[k])
            print("-"*40)
        except:
            print("ERROOO")
    
        

if __name__ == "__main__":
    try:
        route = DCCRIP()
        route.execution()
    except KeyboardInterrupt:
        os._exit(0)

# logging: http://zeldani.blogspot.com/2012/08/python-usando-o-modulo-threading.html
