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

logging.basicConfig(filename="output.log" , level=logging.DEBUG , format='%(levelname)s:linha: %(lineno)d,{} -operação: -> %(message)s '.format(sys.argv[1]))

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

            self.sendUpdates() #  Send Updates at every period seconds (timer to repeat inside the function)

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

            #Decode json data
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

                for nextStep in self.routingNextStepTable.copy():
                    #if the nextstep are in my tables, and uses the neighbor, but the table of neighbor don't have this, del from tables.
                    if self.routingNextStepTable[nextStep] == data['source'] and nextStep not in distances:
                        del self.routingWeightTable[nextStep]
                        if nextStep in self.neighborsTable:
                            del self.neighborsTable[nextStep]
                        del self.routingNextStepTable[nextStep]
                        print( nextStep, " deletado na recepção da update - linha 100")

            # If type = table -> send self routingWeightTable and routingNexStepTable for who requested
            if(data['type'] == 'trace' or data['type'] == 'table'):
                sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket

                print("trace:" , self.myAddress , ' para ', data['destination'])
                
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
                    print(data['payload'])
                else:
                    sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket
                    sock.sendto( str.encode(json.dumps(data)) , (self.routingNextStepTable[data['destination']] , self.port) )

                

      
    def listenInputs(self):
        try:
            readCommand = self.input.readline() if self.input != None else input() #input() if has no file open, or readline() else.
            while readCommand:
                # Add Neighbor
                if readCommand.split(' ')[0] == 'add':
                    if len(readCommand.split(' ')) <= 2:
                        print("Input failure. Correct pattern:\t add <ip> <weight>")
                    else:
                        self.routingWeightTable[readCommand.split(' ')[1] ] = readCommand.split(' ')[2]
                        self.routingNextStepTable[readCommand.split(' ')[1] ] = readCommand.split(' ')[1]
                        self.neighborsTable[readCommand.split(' ')[1]] = readCommand.split(' ')[2]
                        self.sendUpdates(repeat=False)
                
                if readCommand.split(' ')[0] == 'del':
                    if len( readCommand.split(' ')) <= 1:
                        print('Input failure. Correct pattern:\t del <ip>')
                    else:
                        ip = readCommand.split(' ')[1]
                        if ip in self.neighborsTable: # Remove the ip from neighborhood if it is neighbor
                            del self.neighborsTable[ip]

                            if ip in self.routingWeightTable: # Remove the ip from Weights if there exists 
                                del self.routingWeightTable[ip]
                            if ip in self.routingNextStepTable: # Remove the ip from nextsteps if there exists
                                del self.routingNextStepTable[ip]
                            self.sendUpdates(repeat=False , ipExcluded=ip) # Send the news from the others.
                        else:
                            print('Ip not found on the tables')

                # Table and Trace
                if readCommand.split(' ')[0] == 'table' or readCommand.split(' ')[0] == 'trace':
                    readType = readCommand.split(' ')[0]
                    destination = readCommand.split(' ')[1] # the ip that will give the table or trace route
                    if (len(readCommand.split(' ')) <= 1):
                        print('Input failure. Correct pattern:' , end='\t')
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

                if readCommand.split(' ')[0] == 'print':
                    self.imprimirTabelas()

                readCommand = self.input.readline() if self.input != None else input()
        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def sendUpdates(self , repeat = True , ipExcluded = None):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
            for key in self.neighborsTable:

                # Make a dict of type -> 'ip' : 'cost'  
                distances = self.routingWeightTable.copy()

                #Split Horizon
                if key in distances: # 1º don't send for x information to go to x
                    del distances[key]
                for nextStep in self.routingNextStepTable: # 2º don't send for x information that uses x as next step
                    if key == self.routingNextStepTable[nextStep] and nextStep in distances:
                        print(key, ' - deletado linha 210, distances')
                        del distances[nextStep]

                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': key,
                    'distances': distances
                }
                sock.sendto(str.encode( json.dumps( message ) ), (key, self.port))

            if (ipExcluded != None): # Used for tell to the ip that the connection is over (connection excluded)
                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': ipExcluded,
                    'distances': {}
                }
                sock.sendto(str.encode( json.dumps( message ) ), (ipExcluded, self.port))

            if (repeat):
                startSend = threading.Timer( float(self.period), self.sendUpdates)
                startSend.start()

        except KeyboardInterrupt:
            raise KeyboardInterrupt

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
