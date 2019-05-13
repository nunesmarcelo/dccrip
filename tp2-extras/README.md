# DCCRIP - testes

## Casos de teste

O diretório `tests` contém topologias de testes que você pode utilizar
para testar seu programa. Cada diretório dentro de `tests` contém um conjunto de 
arquivos que podem ser utilizados para definir topologias iniciais. A quantidade 
de arquivos nesses diretórios indicam o número de roteadores nas redes e os 
nomes dos  arquivos indicam os endereços a serem utilizados. Por exemplo, o 
diretório `basic` contém dois arquivos, `127.0.1.1.txt` e `127.0.1.2.txt`, que 
podem construir uma rede com dois roteadores conectados entre si, através dos 
comandos:

```
./router.py 127.0.1.1 5 tests/basic/127.0.1.1.txt
```

```
./router.py 127.0.1.2 5 tests/basic/127.0.1.2.txt
```


## *Script* `lo-addresses.sh`

O *script* `lo-addresses.sh` pode ser utilizado para adicionar ou remover 
endereços na interface de *loopback*. A adição de 16 endereços pode ser feita 
através do comando:
```
sudo ./lo-addresses.sh -add
```

A remoção dos endereços pode ser feita através do comando:
```
sudo ./lo-addresses.sh -del
```

**Observações**: Esse *script* só funciona em máquinas Linux. Além disso, 
note que é necessário dar permissão de superusuário para adicionar ou remover os
endereços.
