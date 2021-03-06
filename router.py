#!/usr/bin/python3

#   TP 2 - Redes - DDCNET
#   Marcelo Nunes da Silva
#   Wanderson Sena

# Commands:
# add <ip> <weight>
# del <ip>
# table <ip>
# trace <ip>
# quit
# Extra command(to debug) : print

import sys
import socket
import threading
import json
import os
import logging
import copy # To make a deep copy of dicts

#Log for hidden debug
if len(sys.argv) >= 2:
    logging.basicConfig(filename="output.log" , level=logging.DEBUG , format='%(levelname)s:linha: %(lineno)d,{} -operação: -> %(message)s '.format(sys.argv[1]))

class DCCRIP:
    def __init__(self):

        if (len(sys.argv) < 3): # The min lenght of input is 3 ( program, addr and period are required)
            print("Input failure. Correct pattern:\t./router.py <ADDR> <PERIOD> [STARTUP]")
            os._exit(0)

        #inputs from terminal start
        self.myAddress = sys.argv[1] # address to identify this node
        self.period      = float(sys.argv[2]) # period for send and check updates
        self.port = 55151 # port to bind
        try:
            self.input = open(sys.argv[3], 'r') if len(sys.argv) > 3 else None # If argv[3] exists, uses as input inside line command
        except FileNotFoundError:
            print("File ", sys.argv[3] ," not found! " )
            os._exit(1)
        # Create the routing table of this node, and add myself inside it
        self.routingTable = {}
        # Weight -> cost of move in this edge
        # Next -> List of bests nodes to go towards the desired node
        # Timeout -> time marker to remove itens when 4*period reset
        # Index of Next ->  Integer to control the index of 'next' field, and know what is the next node to go, to balance the load.
        self.routingTable[self.myAddress] = { 'weight' : 0 , 'next' : [self.myAddress] , 'timeout' : [4*self.period] , 'indexOfNext' : 0}

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
            startListen = threading.Thread(target = self.listenMessages) # Receive updates for neighbors
            startListen.start()
            
            startInput = threading.Thread(target = self.listenInputs) # Receive the inputs of user
            startInput.start()

            self.sendUpdates() #  Send Updates at every 'period' seconds (timer to repeat inside the function)

            self.checkAndUpdatePeriods() # At every period, we update the timeouts, and clean the outdated nodes

            startListen.join()
            startInput.join()
            
        except KeyboardInterrupt:
            print("\n")
            self.con.close()
            if self.input != None:
                self.input.close()
            os._exit(1)
            

    def listenMessages(self):
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

                    #If sender not is my neighbor , i can not receive this package.
                    if(data['source'] not in self.neighborsTable):
                        break

                    # If old weight greater than new weight -> swap
                    # If ip not in routingTable, add 
                    if ((address not in self.routingTable) or 
                        int(self.routingTable[address]['weight']) > (int(distances[address]) + int(self.neighborsTable[data['source']])) ):
                        
                        self.routingTable[address] = {}
                        self.routingTable[address]['weight'] = int(distances[address]) + int(self.neighborsTable[data['source']])
                        self.routingTable[address]['next'] = [data['source']]
                        self.routingTable[address]['indexOfNext'] = 0
                        self.routingTable[address]['timeout'] = [4*self.period]

                        logging.debug('Endereço atualizado: {} - antigo: {} - peso: {}'.format(address , int(self.routingTable[address]['weight']) , int(distances[address]) + int(self.neighborsTable[data['source']])))

                    # If there is a different node of this that has the same cost , we have to balance the load
                    if (int(self.routingTable[address]['weight']) == (int(distances[address]) + int(self.neighborsTable[data['source']])) and
                        data['source'] not in self.routingTable[address]['next']):
                        
                        self.routingTable[address]['next'].append(data['source'])
                        self.routingTable[address]['timeout'].append( 4*self.period )

                # Delete the ips that are in the old routingTable, but are not on the distances received.
                # Make 4*period(full) the 'timeout' otherwise.
                for old in self.routingTable.copy():
                    if data['source'] in self.routingTable[old]['next']:
                        if old not in distances:
                            if len(self.routingTable[old]['next']) == 1:
                                #if it is unique route in the table, remove it
                                del self.routingTable[old]
                            else:
                                #if have more then one, remove just that index from next and timeout
                                self.routingTable[old]['next'].remove(data['source'])
                                del self.routingTable[old]['timeout'][ self.routingTable[old]['next'].index(data['source']) ]
                                self.routingTable[old]['indexOfNext'] = (self.routingTable[old]['indexOfNext'] + 1) % len(self.routingTable[old]['next'])
                        else:
                            self.routingTable[old]['timeout'][ self.routingTable[old]['next'].index(data['source']) ] = 4*self.period

                # If this message is to del our connection, delete this neighbor for the neighborTable
                if distances == {} and data['source'] in self.neighborsTable:
                    del self.neighborsTable[data['source']]

            # If type = table or trace -> send the routingTable or the trace for who requested
            if(data['type'] == 'trace' or data['type'] == 'table'):
                sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket

                logging.debug("trace - passou em : {} sentido ao nó: {}".format(self.myAddress ,data['destination']))
                
                # If this node is the destination
                if(data['destination'] == self.myAddress):    
                    # Create a data message to return
                    message = {
                        'type':'data',
                        'source': self.myAddress,
                        'destination' : data['source']
                    }

                    # Payload is the table of this node, if type is table
                    if(data['type'] == 'table'):
                        message.update({ 'payload' : [ (ip,self.routingTable[ip]['next'],self.routingTable[ip]['weight']) for ip in self.routingTable ] })
                    
                    # Payload is the trace generated, if type is trace
                    if(data['type'] == 'trace'):
                        # If i don't know this neighbor yet, i can not ask trace for him.
                        if message['destination'] not in self.routingTable:
                            message['payload'] = "Unable to communicate with this node."
                        else:
                            message.update({'payload' : data['hops']})
                            message['payload'].append(self.myAddress)
                else:
                    message = data
                    # Catch connections that not exists
                    if message['destination'] not in self.routingTable:
                        message['source'] = self.myAddress
                        message['destination'] = data['source']
                        message['payload'] = "Unable to communicate with this node."
                    # If this node is not the destination, just pass the package (updating it if is a 'trace' package)
                    else:
                        if(message['type'] == 'trace'):
                            message['hops'].append(self.myAddress)
                    
                sock.sendto(
                    # message
                    str.encode ( json.dumps( message ) ) , 
                    # send for routing[ destination ][ next ][ choice the next loking at indexofnext ]
                    ( self.routingTable[ message['destination'] ]['next'][ self.routingTable[ message['destination'] ]['indexOfNext'] ] ,
                    self.port) 
                )
                #update the index of next (used for balance the load)
                self.routingTable[ message['destination'] ]['indexOfNext'] = (self.routingTable[ message['destination'] ]['indexOfNext'] + 1) % len(self.routingTable[ message['destination'] ]['next'])
            
            
            if(data['type'] == 'data'):
                if(data['destination'] == self.myAddress):
                    print(data['payload'])
                else:
                    sock = socket.socket(socket.AF_INET , socket.SOCK_DGRAM) # UDP socket

                    # send for routing[ destination ][ next ][ choice the next loking at indexofnext ]
                    sock.sendto( str.encode(json.dumps(data)) , (self.routingTable[ data['destination'] ]['next'][ self.routingTable[ data['destination'] ]['indexOfNext'] ] , self.port) )
                    #update the index of next (used for balance the load)
                    self.routingTable[ data['destination'] ]['indexOfNext'] = (self.routingTable[ data['destination'] ]['indexOfNext'] + 1) % len(self.routingTable[ data['destination'] ]['next'])
            

    def listenInputs(self):
        try:
             while True:
                readCommand = self.input.readline() if self.input != None else input() #input() if has no file open, or readline() otherwise.
                
                # Exit to the program
                if(readCommand == 'quit'):
                    os._exit(0)

                # If the file input is over, listen user commands
                if(readCommand == '' and self.input != None):
                    self.input = None
                    continue

                # Add Neighbor
                if readCommand.split(' ')[0] == 'add':
                    if len(readCommand.split(' ')) <= 2:
                        print("Input failure. Correct pattern:\t add <ip> <weight>")
                    else:
                        if readCommand.split(' ')[1] == self.myAddress:
                            continue
                        self.routingTable[readCommand.split(' ')[1] ] = {}
                        self.routingTable[readCommand.split(' ')[1] ]['weight'] = readCommand.split(' ')[2]
                        self.routingTable[readCommand.split(' ')[1] ]['next'] = [ readCommand.split(' ')[1] ]
                        self.routingTable[readCommand.split(' ')[1] ]['timeout'] = [4*self.period]
                        self.routingTable[readCommand.split(' ')[1] ]['indexOfNext'] = 0
                        self.neighborsTable[readCommand.split(' ')[1] ] = readCommand.split(' ')[2]
                        self.sendUpdates(repeat=False)
                
                # Del Neighbor
                if readCommand.split(' ')[0] == 'del':
                    if len( readCommand.split(' ')) <= 1:
                        print('Input failure. Correct pattern:\t del <ip>')
                    else:
                        ip = readCommand.split(' ')[1]
                        if ip in self.neighborsTable: # Remove the ip from neighborhood if it is neighbor
                            del self.neighborsTable[ip]

                            for old in self.routingTable.copy():
                                if ip in self.routingTable[old]['next']:
                                    if len(self.routingTable[old]['next']) == 1:
                                        #if it is unique route in the table, remove it
                                        del self.routingTable[old]
                                    else:
                                        #if have more then one, remove just that index
                                        index = self.routingTable[old]['next'].index(ip) 
                                        del self.routingTable[old]['next'][index]
                                        del self.routingTable[old]['timeout'][index]
                                        self.routingTable[old]['indexOfNext'] = (self.routingTable[old]['indexOfNext'] + 1) % len(self.routingTable[old]['next'])
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
                        
                        if destination not in self.routingTable:
                            print("Ip not found on the neighborhood")
                        else:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
                            message = {
                                'type'  : readType,
                                'source': self.myAddress ,  
                                'destination': destination
                            }
                            
                            # If the command is trace, start the list of trace 
                            if readType == 'trace':
                                message.update({ 'hops' : [self.myAddress] })

                            #send the request to the next on the routing table
                            sock.sendto(str.encode ( json.dumps( message ) ) , ( self.routingTable[destination]['next'][ self.routingTable[destination]['indexOfNext'] ], self.port) )
                            
                            #update the index of next (used for balance the load)
                            self.routingTable[destination]['indexOfNext'] = (self.routingTable[destination]['indexOfNext'] + 1) % len(self.routingTable[destination]['next'])
                
                # Extra command: print
                if readCommand.split(' ')[0] == 'print':
                    self.printTables()

        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def sendUpdates(self , repeat = True , ipExcluded = None):
        try:
            # UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

            #Send update for each neighbor
            for key in self.neighborsTable.copy():

                # Make a copy of routingTable 
                distances = copy.deepcopy( self.routingTable )

                #Applying Split Horizon
                for old in distances.copy():
                    if key == old:
                        del distances[old]
                    else:
                        if key in distances[old]['next']:
                            if len(self.routingTable[old]['next']) == 1: # if have not other pointing, remove this node
                                #if it is unique route in the table, remove it
                                del distances[old]
                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': key,
                    'distances': { ip : distances[ip]['weight'] for ip in distances}
                }

                if key in self.routingTable:
                    sock.sendto(str.encode( json.dumps( message ) ), ( self.routingTable[key]['next'][self.routingTable[key]['indexOfNext']], self.port))
                    
            if (ipExcluded != None): # Used for inform ip that the connection is over (hey, my side canceled the connection)
                message = { 
                    'type'  : 'update',
                    'source': self.myAddress ,  
                    'destination': ipExcluded,
                    'distances': {}
                }
                sock.sendto(str.encode( json.dumps( message ) ), (ipExcluded, self.port))

            if (repeat): # send updates every 'period' seconds
                startSend = threading.Timer( self.period, self.sendUpdates)
                startSend.start()

        except KeyboardInterrupt:
            raise KeyboardInterrupt

    def checkAndUpdatePeriods(self):
        # Look at every line in routing table
        for ip in self.routingTable.copy():
            # Don't remove my ip
            if ip == self.myAddress : continue 
            
            # How we have a list of possible next's (balance load), we have a time for each
            for time in self.routingTable[ip]['timeout']: 
                if int(time) <= 0: # if a time of next is over, remove it
                    if len(self.routingTable[ip]['next']) == 1:
                        del self.routingTable[ip]
                    else:
                        index = self.routingTable[ip]['timeout'].index(time)
                        del self.routingTable[ip]['timeout'][index]
                        del self.routingTable[ip]['next'][index]
                        self.routingTable[ip]['indexOfNext'] = (self.routingTable[ip]['indexOfNext'] + 1 ) % len(self.routingTable[ip]['next'])
                else:
                    # Decrease the timeout of next
                    self.routingTable[ip]['timeout'][ self.routingTable[ip]['timeout'].index(time) ] -= self.period
            

        # Check and decrease again 'period' seconds
        checkAgain = threading.Timer( self.period, self.checkAndUpdatePeriods)
        checkAgain.start()

    # Extra command, for a better debug 
    def printTables(self):
        try:
            print("-"*20)
            print("**** Neighbors **** ")
            for k in self.neighborsTable:
                print(k , "-> " , self.neighborsTable[k].strip('\n'))

            print('**** Weights ****')
            for k in self.routingTable:
               print("{}----{}----{}----{}".replace('\n',' ').replace('\t',' ').replace(' ','').format(k,str( self.routingTable[k]['weight'] ).replace('\n' ,''),self.routingTable[k]['next'],self.routingTable[k]['timeout']))
            print("-"*20)
        except Exception as e:
            print(e)
    
        

if __name__ == "__main__":
    try:
        route = DCCRIP()
        route.execution()
    except KeyboardInterrupt:
        os._exit(0)

