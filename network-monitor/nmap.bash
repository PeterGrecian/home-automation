#!/bin/bash
LAST="last_output.txt"

function nmp() {
  ofile=$1
   n=$((n+1))
  echo -n "$n  "
  nmap -sn 192.168.4.0/24 |& grep report > $ofile 
  wc -l $ofile
}

n=0
nmp $LAST

while true; do
  rm nmap.out >& /dev/null
  nmp new_output.txt
  diff $LAST new_output.txt | grep report | sed 's/</missing/' | sed 's/>/new    /' | tee -a nmap.out

  mv new_output.txt $LAST
  sleep 6
done

