#!/usr/bin/python3

#   TP 2 - Redes - DDCNET
#   Marcelo Nunes da Silva
#   Wanderson Sena
import sys
import socket
import threading
import json
import os
import logging

logging.basicConfig(filename="output.log" , level=logging.DEBUG , format='%(levelname)s: line: %(lineno)d , Nó {} diz: -> %(message)s '.format(sys.argv[1]))

class DCCRIP:
    def __init__(self):

        if (len(sys.argv) < 3):
            print("Input failure. Correct pattern:\t./router.py <ADDR> <PERIOD> [STARTUP]")
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

            self.sendUpdates() # Timer

            startListen.join()
            startInput.join()
            
        except KeyboardInterrupt:
            print("\n")
            self.con.close()
            if self.input != None:
                self.input.close()
            os._exit(1)
            

    def listenUpdates(self):
        while True:
            #Receive data
            try:
                data, addr = self.con.recvfrom(1024) # buffer size is 1024 bytes
            except KeyboardInterrupt:
                raise KeyboardInterrupt

            data = json.loads( bytes.decode( data) )

            # If type = update -> update routingWeightTable and routingNextStepTable
            if(data['type'] == 'update'):
                distances = data['distances']
                
                for address in distances:
                    #print(address, distances[address] , type(distances[address]))

                    if(data['source'] not in self.neighborsTable):
                        break

                    # If old weight greater than new weight -> swap
                    if ((address not in self.routingWeightTable.keys()) or int(self.routingWeightTable[address]) > int(distances[address]) + int(self.neighborsTable[data['source']])):
                        self.routingWeightTable[address] = int(distances[address]) + int(self.neighborsTable[data['source']])
                        self.routingNextStepTable[address] = data['source']

                        logging.debug('Endereço atualizado: {} - antigo: {} - peso: {}'.format(address , int(self.routingWeightTable[address]) , int(distances[address]) + int(self.neighborsTable[data['source']])))

            # If type = table -> send self routingWeightTable and routingNexStepTable for who requested
            if(data['type'] == 'trace' or data['type'] == 'table'):
                sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket

                print("trace vindoo" , self.myAddress , data['destination'])
                
                # If this node is the destination
                if(data['destination'] == self.myAddress):    
                    # Create a data message to return
                    message = {
                        'type':'data',
                        'source': self.myAddress,
                        'destination' : data['source']
                    }

                    #The type of return is the table of this node
                    if(data['type'] == 'table'):
                        message.update({ 'payload' : [ (ip,self.routingNextStepTable[ip],self.routingWeightTable[ip]) for ip in self.routingWeightTable ] })
                    
                    #The type of return is a list of addresses
                    if(data['type'] == 'trace'):
                        message.update({'payload' : data['hops']})
                        message['payload'].append(self.myAddress)
                else:
                    # If this is not the destination, just pass the package (updating it if is trace package)
                    message = data
                    if(message['type'] == 'trace'):
                        message['hops'].append(self.myAddress)
                    
                #print("message: " , message , ' - next: ' , self.routingNextStepTable[ message['destination'] ])
                sock.sendto(str.encode ( json.dumps( message ) ) , ( self.routingNextStepTable[ message['destination'] ] , self.port) )
            
            if(data['type'] == 'data'):
                if(data['destination'] == self.myAddress):
                    for itemData in data['payload']:
                        print(itemData) 
                else:
                    sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket
                    sock.sendto( str.encode(json.dumps(data)) , (self.routingNextStepTable[data['destination']] , self.port) )

                

      
    def listenInputs(self):
        try:
            readCount = self.input.readline() if self.input != None else input() #input() if has no file open, or readline() else.
            while readCount:
                # ADD Neighbor
                if readCount.split(' ')[0] == 'add':
                    if len(readCount.split(' ')) <= 2:
                        print("Input failure. Correct pattern:")
                        print("add <ip> <weight>")
                    else:
                        self.routingWeightTable[readCount.split(' ')[1] ] = readCount.split(' ')[2]
                        self.routingNextStepTable[readCount.split(' ')[1] ] = readCount.split(' ')[1]
                        self.neighborsTable[readCount.split(' ')[1]] = readCount.split(' ')[2]
                        self.sendUpdates(repetir=False)

                # Table and Trace
                if readCount.split(' ')[0] == 'table' or readCount.split(' ')[0] == 'trace':
                    readType = readCount.split(' ')[0]
                    destination = readCount.split(' ')[1] # the ip that will give the table or trace route
                    if (len(readCount.split(' ')) <= 1):
                        print('Input failure. Correct pattern:')
                        print("table <ip>") if readType == 'table' else print("trace <ip>")
                    else:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
                        message = {
                            'type'  : readType,
                            'source': self.myAddress ,  
                            'destination': destination
                        }
                        
                        if readType == 'trace':
                            message.update({ 'hops' : [self.myAddress] })

                        sock.sendto(str.encode ( json.dumps( message ) ) , ( self.routingNextStepTable[destination], self.port) )

                if readCount.split(' ')[0] == 'print':
                    self.imprimirTabelas()

                readCount = self.input.readline() if self.input != None else input()
        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def sendUpdates(self , repetir = True):
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

            if (repetir):
                startSend = threading.Timer( float(self.period), self.sendUpdates)
                startSend.start()

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
