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
        # self.routingWeightTable = {}
        # self.routingNextStepTable = {}
        # self.routingWeightTable[self.myAddress] = 0
        # self.routingNextStepTable[self.myAddress] = self.myAddress

        self.routingTable = {}
        self.routingTable[self.myAddress] = { 'weight' : 0 , 'next' : self.myAddress}

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

            # If type = update -> update the routingTable
            if(data['type'] == 'update'):
                distances = data['distances']
                
                for address in distances:
                    #print(address, distances[address] , type(distances[address]))

                    #If sender not is my neighbor , i don't can receive his package.
                    if(data['source'] not in self.neighborsTable):
                        break

                    # If old weight greater than new weight -> swap
                    # If ip not in routingTable, add 
                    if ((address not in self.routingTable) or 
                        int(self.routingTable[address]['weight']) > (int(distances[address]) + int(self.neighborsTable[data['source']])) ):
                        self.routingTable[address] = {}
                        self.routingTable[address]['weight'] = int(distances[address]) + int(self.neighborsTable[data['source']])
                        self.routingTable[address]['next'] = data['source']

                        logging.debug('Endereço atualizado: {} - antigo: {} - peso: {}'.format(address , int(self.routingTable[address]['weight']) , int(distances[address]) + int(self.neighborsTable[data['source']])))

                # Delete the ips that are in the old routingTable, but are not on the distances received.
                for old in self.routingTable.copy():
                    if self.routingTable[old]['next'] == data['source'] and old not in distances:
                        del self.routingTable[old]

                # If this message is to del our connection, delete this neighbor for the neighborTable
                if distances == {} and data['source'] in self.neighborsTable:
                    del self.neighborsTable[data['source']]

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
                        message.update({ 'payload' : [ (ip,self.routingTable[ip]['next'],self.routingTable[ip]['weight']) for ip in self.routingTable ] })
                    
                    #The type of return is a list of addresses
                    if(data['type'] == 'trace'):
                        message.update({'payload' : data['hops']})
                        message['payload'].append(self.myAddress)
                else:
                    # If this is not the destination, just pass the package (updating it if is trace package)
                    message = data
                    if(message['type'] == 'trace'):
                        message['hops'].append(self.myAddress)
                    
                #print("message: " , message , ' - next: ' , self.routingTable[ message['destination'] ])
                sock.sendto(str.encode ( json.dumps( message ) ) , ( self.routingTable[ message['destination'] ]['next'] , self.port) )
            
            if(data['type'] == 'data'):
                if(data['destination'] == self.myAddress):
                    print(data['payload'])
                else:
                    sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket
                    sock.sendto( str.encode(json.dumps(data)) , (self.routingTable[data['destination']]['next'] , self.port) )

                

      
    def listenInputs(self):
        try:
             while True:
                readCommand = self.input.readline() if self.input != None else input() #input() if has no file open, or readline() else.

                if(readCommand == 'quit'):
                    os._exit(0)

                # Add Neighbor
                if readCommand.split(' ')[0] == 'add':
                    if len(readCommand.split(' ')) <= 2:
                        print("Input failure. Correct pattern:\t add <ip> <weight>")
                    else:
                        self.routingTable[readCommand.split(' ')[1] ] = {}
                        self.routingTable[readCommand.split(' ')[1] ]['weight'] = readCommand.split(' ')[2]
                        self.routingTable[readCommand.split(' ')[1] ]['next'] = readCommand.split(' ')[1]
                        self.neighborsTable[readCommand.split(' ')[1]] = readCommand.split(' ')[2]
                        self.sendUpdates(repeat=False)
                
                if readCommand.split(' ')[0] == 'del':
                    if len( readCommand.split(' ')) <= 1:
                        print('Input failure. Correct pattern:\t del <ip>')
                    else:
                        ip = readCommand.split(' ')[1]
                        if ip in self.neighborsTable: # Remove the ip from neighborhood if it is neighbor
                            del self.neighborsTable[ip]

                            # if ip in self.routingWeightTable: # Remove the ip from Weights if there exists 
                            #     del self.routingWeightTable[ip]
                            # if ip in self.routingNextStepTable: # Remove the ip from nextsteps if there exists
                            #     del self.routingNextStepTable[ip]

                            # if ip in self.routingTable.values():
                            #     del self.routingTable[ip]

                            for old in self.routingTable.copy():
                                if ip == self.routingTable[old]['next']:
                                    del self.routingTable[old]

                            self.sendUpdates(repeat=False , ipExcluded=ip) # Send the news from the others.
                        else:
                            print('Ip not found on the neighborhood')

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

                        sock.sendto(str.encode ( json.dumps( message ) ) , ( self.routingTable[destination]['next'], self.port) )

                if readCommand.split(' ')[0] == 'print':
                    self.imprimirTabelas()

        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def sendUpdates(self , repeat = True , ipExcluded = None):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
            for key in self.neighborsTable:

                # Make a dict of type -> 'ip' : 'cost'  
                distances = self.routingTable.copy()

                #Split Horizon
                # if key in distances: # 1º don't send for x information to go to x
                #     del distances[key]
                # for nextStep in self.routingTable: # 2º don't send for x information that uses x as next step
                #     if key == self.routingNextStepTable[nextStep] and nextStep in distances:
                #         del distances[nextStep]
                # if key in distances or key in distances.values():
                #     del distances[key]
                
                for old in distances.copy():
                    if key == old or key == distances[old]['next']:
                        del distances[old]

                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': key,
                    'distances': { ip : distances[ip]['weight'] for ip in distances}
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
            for k in self.routingTable:
                print(k , ' ---> ' , self.routingTable[k]['weight'] , ' ---> ' , self.routingTable[k]['next']) 
            print("-"*40)
        except Exception as e:
            print(e)
    
        

if __name__ == "__main__":
    try:
        route = DCCRIP()
        route.execution()
    except KeyboardInterrupt:
        os._exit(0)

# logging: http://zeldani.blogspot.com/2012/08/python-usando-o-modulo-threading.html
