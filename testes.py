#!/usr/bin/python3

import threading

def printit():
  
  print ("Hello, World!")

threading.Timer(5.0, printit).start()