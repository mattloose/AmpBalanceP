# AmpBalanceP
AmpBalance Parallel

Very simple little program to try and split up amplicons.

This should work on the default version of python as registered on an ONT PC. It does require the mlpy library to be installed:

pip install mlpy-3.5.0-cp27-none-win_amd64.whl

After that you should just be able to run:

python ampbalance_v2P.py -w /path/to/reads -o /path/to/outfolder -d 50 -p 8

Note that the full options are available with -h

Many options are now encoded in the ampW.config file for simplicity. 

usage: ampbalance_v2P.py [-h] -fasta FASTA -ids IDS -w WATCHDIR -o TARGETPATH
                         -d DEPTH -procs PROCS -l LENGTH [-v]

