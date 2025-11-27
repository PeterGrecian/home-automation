#!/bin/bash
w=2
c=3
while true; do
  for i in 106 70 69 102; do
    printf "%3s " $i
    ping -w $w -c $c 192.168.4.$i 2>&1 | grep "packet loss" | grep --invert-match " 0% packet loss"
    #echo
  done
done

