#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "./lo-addresses.sh [-add OR -del]"
    exit 1
fi

NUM_ADDR=16

if [[ $1 == "-add" ]]; then
    echo "Adicionando enderecos..."
    for i in $(seq 1 $NUM_ADDR); 
    do 
        echo "> Adicionando endereco 127.0.1.$i" 
        ip addr add 127.0.1.$i/32 dev lo
    done
    echo "Enderecos adicionados!"
elif [[ $1 == "-del" ]]; then
    echo "Removendo enderecos..."
    for i in $(seq 1 $NUM_ADDR); 
    do 
        echo "> Removendo endereco 127.0.1.$i" 
        ip addr del 127.0.1.$i/32 dev lo
    done
    echo "Enderecos removidos!"
else
    echo "./lo-addresses.sh [-add OR -del]"
    exit 1
fi