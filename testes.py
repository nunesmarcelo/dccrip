# import sys
# with open(sys.argv[1], 'r') if len(sys.argv) > 1 else sys.stdin as f:
#     leitura = f.readline()
#     while leitura:
#         print(leitura)
#         leitura = f.readline()

lista = {}
lista['129'] = {"custo" :  10 , 'prox' : '130'}
lista['1229'] = {"custo" :  120 , 'prox' : '1130'}

for value in lista:
    print(value)
