#!C:\anaconda
import sys, os, re
import time
import threading, thread
from Bio import SeqIO
from StringIO import StringIO
#import MySQLdb
import string
import mlpy
import sklearn.preprocessing
import random
import math
import csv
import numpy as np
import array as ar
import configargparse
import subprocess
import shutil
import glob
import h5py
from itertools import islice
from collections import OrderedDict
import psutil
import multiprocessing



global oper
#oper="linux"
oper="windows"

## linux version
if (oper is "linux"):
        config_file = os.path.join(os.path.sep, os.path.dirname(os.path.realpath('__file__')), 'amp.config')

## linux version
if (oper is "windows"):
        config_file = os.path.join(os.path.sep, os.path.dirname(os.path.realpath('__file__')), 'ampW.config')



parser = configargparse.ArgParser(description='ampbalance: A program designed to balance amplicons from a specific reference sequence post sequencing on ONT minIONs but prebasecalling. Developed by Matt Loose @mattloose or matt.loose@nottingham.ac.uk for help!',default_config_files=[config_file])
parser.add('-fasta', '--reference_fasta_file', type=str, dest='fasta', required=True, default=None, help="The fasta format file for the reference sequence for your organism.")
#parser.add('-ids', '--reference_id_pos', nargs = '*', dest='ids',required=True, help = 'A list of start and stop positions for each amplicon from the reference genome - should be space separated with fasta_name:start-stop.\n e.g.\n EM_079517:27-1938 EM_078517:1927-3828 EM_078517:3823-5718 EM_078517:5759-7633 EM_078517:7601-10007 EM_078517:9550-10921 EM_078517:10944-12354 EM_078517:12354-14252 EM_078517:14253-15680 EM_078517:15691-17087 EM_078517:16632-18553\n ')
parser.add('-ids', '--reference_amplicon_positions', type=str, required=True, default=None, help="A file containing a list of amplicon positions defined for the reference sequence. 1 amplicon per line in the format fasta_sequence_name:start-stop e.g EM_079517:27-1938", dest='ids')
parser.add('-w', '--watch-dir', type=str, required=True, default=None, help="The path to the folder containing the downloads directory with fast5 reads to analyse - e.g. C:\data\minion\downloads (for windows).", dest='watchdir')
parser.add('-o', '--output-dir', type=str, required=True, default="prefiltered", help="The path to the destination folder for the preprocessed reads" , dest="targetpath")
parser.add('-d', '--depth',type=int, required=True, default=None, help = 'The desired coverage depth for each amplicon. Note this is unlikely to be achieved for each amplicon and should probably be an overestimate of the minimum coverage required.', dest='depth')
parser.add('-procs', '--proc_num', type=int, dest='procs',required=True, help = 'The number of processors to run this on.')
parser.add('-l', '--length',type=int, required=True, default=2000, help = 'The approximate average length of the amplicons - e.g. 2000', dest='length')
parser.add('-t', '--template_model',type=str, required=True, help = 'The appropriate template model file to use', dest='temp_model')
parser.add('-c', '--complement_model',type=str, required=True, help = 'The appropriate complement model file to use', dest='comp_model')
parser.add('-m', '--model_length',type=int, required=True, help = 'The word size of the mode file - e.g 5,6 or 7', dest='model_length')
parser.add('-v', '--verbose-true', action='store_true', help="Print detailed messages while processing files.", default=False, dest='verbose')
parser.add('-s', '--speed-mode', action='store_true', help="This will selectively run smaller time warps but attempt to return the same data.", default=False, dest='speedmode')

args = parser.parse_args()


###########################################################
#def memory_usage_psutil():
#    process = psutil.Process(os.getpid())
#    pc = round(process.memory_percent(),2)
#    print "Mem Used %s: " % (str(pc))

###########################################################
def make_hdf5_object_attr_hash(hdf5object, fields):
	att_hash=dict()
	for field in fields:
		if (field in hdf5object.attrs.keys() ):
			#print "filed: ",field (args.ref_fasta is not None), hdf5object.attrs[field]
			att_hash[field]=hdf5object.attrs[field]
	return att_hash

######################################################
def process_model_file(model_file):
	model_kmers = dict()
	with open(model_file, 'rb') as csv_file:
		reader = csv.reader(csv_file, delimiter="\t")
    		d = list(reader)
		#print d
		for r in range(1, len(d)):
			#print r, d[r]
			kmer = d[r][0]
			mean = d[r][1]
			#print r, kmer, mean
			model_kmers[kmer]=mean
	return 	model_kmers

######################################################
def get_amplicons():
    print "Groking amplicons"
    if (args.verbose is True):
        print "ids is of type", type(amplicons)
    for sequence in amplicons:
        if (args.verbose is True):
            print sequence
        start = int(float(sequence.split(':', 1 )[1].split('-',1)[0]))
        stop = int(float(sequence.split(':', 1 )[1].split('-',1)[1]))
        if (args.verbose is True):
            print start
            print stop
        REVERSE_stop = seqlengths['EM_079517']-start
        REVERSE_start = seqlengths['EM_079517']-stop
        if (args.verbose is True):
            print REVERSE_stop
            print REVERSE_start

######################################################
def get_seq_len(ref_fasta):
	seqlens=dict()
	for record in SeqIO.parse(ref_fasta, 'fasta'):
		seq=record.seq
		seqlens[record.id]=len(seq)
	return seqlens
#######################################################################
def raw_squiggle_search2(squiggle,hashthang):
    result=[]
    #print args.speedmode
    for ref in hashthang:
        try:
            if (args.speedmode is True):
            #    memory_usage_psutil()
                queryarray = sklearn.preprocessing.scale(np.array(squiggle),axis=0,with_mean=True,with_std=True,copy=True)
                dist, cost, path = mlpy.dtw_subsequence(queryarray[0:500],hashthang[ref]['Fprime'])
                dist1, cost1, path1 = mlpy.dtw_subsequence(queryarray[-500:],hashthang[ref]['Fprime'])
                result.append((dist+dist1,ref,"F",path[1][0],path1[1][-1],path[0][0],path1[0][-1]))
                dist, cost, path = mlpy.dtw_subsequence(queryarray[0:500],hashthang[ref]['Rprime'])
                dist1, cost1, path1 = mlpy.dtw_subsequence(queryarray[-500:],hashthang[ref]['Rprime'])
                result.append((dist+dist1,ref,"R",(len(hashthang[ref]['Rprime'])-path1[1][-1]),(len(hashthang[ref]['Rprime'])-path[1][0]),path[0][0],path1[0][-1]))
            else:
                queryarray = sklearn.preprocessing.scale(np.array(squiggle),axis=0,with_mean=True,with_std=True,copy=True)
                dist, cost, path = mlpy.dtw_subsequence(queryarray,hashthang[ref]['Fprime'])
                #if (args.verbose is True):
                #    memory_usage_psutil()
                result.append((dist,ref,"F",path[1][0],path[1][-1],path[0][0],path[0][-1]))
                dist, cost, path = mlpy.dtw_subsequence(queryarray,hashthang[ref]['Rprime'])
                result.append((dist,ref,"R",(len(hashthang[ref]['Rprime'])-path[1][-1]),(len(hashthang[ref]['Rprime'])-path[1][0]),path[0][0],path[0][-1]))
                #if (args.verbose is True):
                #    memory_usage_psutil()
        except Exception,err:
            print "Warp Fail"
	return sorted(result,key=lambda result: result[0])[0][1],sorted(result,key=lambda result: result[0])[0][0],sorted(result,key=lambda result: result[0])[0][2],sorted(result,key=lambda result: result[0])[0][3],sorted(result,key=lambda result: result[0])[0][4],sorted(result,key=lambda result: result[0])[0][5],sorted(result,key=lambda result: result[0])[0][6]


######################################################
def process_ref_fasta_raw(ref_fasta,model_kmer_means):
    print "processing the reference fasta."
    kmer_len=args.model_length
    kmer_means=dict()
    for record in SeqIO.parse(ref_fasta, 'fasta'):
        kmer_means[record.id]=dict()
        kmer_means[record.id]["F"]=list()
        kmer_means[record.id]["R"]=list()
        kmer_means[record.id]["Fprime"]=list()
        kmer_means[record.id]["Rprime"]=list()
        if (args.verbose is True):
            print "ID", record.id
            print "length", len(record.seq)
            print "FORWARD STRAND"
        seq = record.seq
        for x in range(len(seq)+1-kmer_len):
            kmer = str(seq[x:x+kmer_len])
            kmer_means[record.id]["F"].append(float(model_kmer_means[kmer]))
        if (args.verbose is True):
            print "REVERSE STRAND"
        seq = revcomp = record.seq.reverse_complement()
        for x in range(len(seq)+1-kmer_len):
            kmer = str(seq[x:x+kmer_len])
            kmer_means[record.id]["R"].append(float(model_kmer_means[kmer]))
        kmer_means[record.id]["Fprime"]=sklearn.preprocessing.scale(kmer_means[record.id]["F"], axis=0, with_mean=True, with_std=True, copy=True)
        kmer_means[record.id]["Rprime"]=sklearn.preprocessing.scale(kmer_means[record.id]["R"], axis=0, with_mean=True, with_std=True, copy=True)
    return kmer_means
#######################################################################
def process_hdf5((filename,kmerhashT,kmerhashC,amplicons,ampstartdict,ampenddict,procampres)):
        readprediction=dict()
        if (args.verbose is True):
            print filename
        hdf = h5py.File(filename, 'r')
        for read in hdf['Analyses']['EventDetection_000']['Reads']:
            events = hdf['Analyses']['EventDetection_000']['Reads'][read]['Events'][()]
            event_collection=list()
            time_collection=list()
            for event in events:
                event_collection.append(float(event['mean']))
                time_collection.append(event['start'])
            #print event_collection
            #print time_collection
            read_id_fields = ['duration','hairpin_found','hairpin_event_index','read_number','scaling_used','start_mux','start_time',]
            read_info_hash =  make_hdf5_object_attr_hash(hdf['Analyses/EventDetection_000/Reads/'+read],read_id_fields)
            if read_info_hash['hairpin_found']==1:
                procampres["HF"] += 1
                template_time = time_collection[read_info_hash['hairpin_event_index']]-time_collection[0]
                complement_time = time_collection[len(time_collection)-1]-time_collection[read_info_hash['hairpin_event_index']]
                ratiotempcomp = float(complement_time)/float(template_time)
                if (args.verbose is True):
                    print "!!! Hairpin Found !!!"
                    print "Template Length:", len(event_collection[0:read_info_hash['hairpin_event_index']])
                    print "Complement Length:", len(event_collection[read_info_hash['hairpin_event_index']:len(event_collection)])
            #        print "Template Time", template_time
            #        print "Complement Time", complement_time
                if (len(event_collection[0:read_info_hash['hairpin_event_index']]) > (5 * args.length)) or (len(event_collection[read_info_hash['hairpin_event_index']:len(event_collection)]) > (5*args.length)):
                    procampres["BF"] += 1
                    if (args.verbose is True):
                        print "******** WARNING THIS READ WOULD CRASH WINDOWS ********"
                        print "Skipped", filename
                    break
                #try:
                (seqmatchnameT,distanceT,frT,rsT,reT,qsT,qeT) = raw_squiggle_search2(event_collection[0:read_info_hash['hairpin_event_index']],kmerhashT)
                if (args.verbose is True):
                    print "Warp 1 Complete"
                #except Exception,err:
                #    print "A time warp failed:", err
                #try:
                (seqmatchnameC,distanceC,frC,rsC,reC,qsC,qeC) = raw_squiggle_search2(event_collection[read_info_hash['hairpin_event_index']:len(event_collection)],kmerhashC)
                if (args.verbose is True):
                    print "Warp 2 Complete"
                #except Exception,err:
                #    print "A time warp failed:", err
                if (seqmatchnameC==seqmatchnameT and frT != frC and reC >= rsT and rsC <= reT):
                    if (args.verbose is True):
                        print "Good Candidate"
                    if (rsT < rsC):
                        start = rsT
                    else:
                        start = rsC
                    if (reT > reC):
                        end = reT
                    else:
                        end = reC
                    for amplicon in amplicons:
                        ampstart = int(float(amplicon.split(':', 1 )[1].split('-',1)[0]))
                        ampstop = int(float(amplicon.split(':', 1 )[1].split('-',1)[1]))
                    if (args.verbose is True):
                        print start,end
                    amplicon, value = min(ampstartdict.items(), key=lambda (_, v): abs(v - start))
                    if (args.verbose is True):
                        print amplicon, value
                    key2, value2 = min(ampenddict.items(), key=lambda (_, v): abs(v - end))
                    if (args.verbose is True):
                        print key2, value2
                    if amplicon == key2:
                        if 1.3 < ratiotempcomp < 1.7:
                            procampres[amplicon] += 1
                            if (amplicon not in readprediction):
                                readprediction[amplicon]=dict()
                            if (0 not in readprediction[amplicon]):
                                readprediction[amplicon][0]=dict()
                            if (filename not in readprediction[amplicon][0]):
                                readprediction[amplicon][0][filename]=dict()
                            readprediction[amplicon][0][filename]["name"]=filename
                            readprediction[amplicon][0][filename]["matchdistance"]=distanceT
                        elif 1 < ratiotempcomp < 1.7:
                            procampres[amplicon] += 1
                            if (amplicon not in readprediction):
                                readprediction[amplicon]=dict()
                            if (1 not in readprediction[amplicon]):
                                readprediction[amplicon][1]=dict()
                            if (filename not in readprediction[amplicon][1]):
                                readprediction[amplicon][1][filename]=dict()
                            readprediction[amplicon][1][filename]["name"]=filename
                            readprediction[amplicon][1][filename]["matchdistance"]=distanceT
                        else:
                            if (amplicon not in readprediction):
                                readprediction[amplicon]=dict()
                            if (2 not in readprediction[amplicon]):
                                readprediction[amplicon][2]=dict()
                            if (filename not in readprediction[amplicon][2]):
                                readprediction[amplicon][2][filename]=dict()
                            readprediction[amplicon][2][filename]["name"]=filename
                            readprediction[amplicon][2][filename]["matchdistance"]=distanceT
                    else:
                        if 1 < ratiotempcomp < 1.7:
                            procampres[amplicon] += 1
                            if (amplicon not in readprediction):
                                readprediction[amplicon]=dict()
                            if (3 not in readprediction[amplicon]):
                                readprediction[amplicon][3]=dict()
                            if (filename not in readprediction[amplicon][3]):
                                readprediction[amplicon][3][filename]=dict()
                            readprediction[amplicon][3][filename]["name"]=filename
                            readprediction[amplicon][3][filename]["matchdistance"]=distanceT
                        else:
                            procampres[amplicon] += 1
                            if (amplicon not in readprediction):
                                readprediction[amplicon]=dict()
                            if (4 not in readprediction[amplicon]):
                                readprediction[amplicon][4]=dict()
                            if (filename not in readprediction[amplicon][4]):
                                readprediction[amplicon][4][filename]=dict()
                            readprediction[amplicon][4][filename]["name"]=filename
                            readprediction[amplicon][4][filename]["matchdistance"]=distanceT
                else:
                    if (args.verbose is True):
                        print "Template and Complement don't overlap sufficiently"
                    procampres["DO"] += 1
                    if (args.verbose is True):
                        print "Template",frT,rsT,reT
                        print "Complement",frC,rsC,reC
            else:
                procampres["NH"] += 1
                if (args.verbose is True):
                    print "!!! Hairpin Not Found !!!"
        hdf.close()
        procampres["TF"]-=1
        if (args.verbose is True):
            print procampres,
            print filename+" done"
        else:
            print procampres
        return readprediction

######################

if __name__ == "__main__":
    multiprocessing.freeze_support()
    p = multiprocessing.Pool(args.procs)
    manager = multiprocessing.Manager()
    amplicon_file = open(args.ids, "r")
    amplicons = []
    for line in amplicon_file.readlines():
        amplicons.append(line.rstrip())
    if (args.verbose is True):
        print amplicons
    amplicon_file.close()
    fasta_file = args.fasta
    model_file_template = args.temp_model
    model_file_complement = args.comp_model
    model_kmer_means_template=process_model_file(model_file_template)
    model_kmer_means_complement=process_model_file(model_file_complement)
    kmerhashT = process_ref_fasta_raw(fasta_file,model_kmer_means_template)
    kmerhashC = process_ref_fasta_raw(fasta_file,model_kmer_means_complement)
    seqlengths = get_seq_len(fasta_file)
    get_amplicons()
    #memory_usage_psutil()
    ampdict=[]
    ampstartdict=dict()
    ampenddict=dict()
    counter = 0
    procampres=manager.dict()

    for amplicon in amplicons:
    	counter+=1
    	ampstart = int(float(amplicon.split(':', 1 )[1].split('-',1)[0]))
    	ampstop = int(float(amplicon.split(':', 1 )[1].split('-',1)[1]))
    	ampstartdict[counter]=ampstart
    	ampenddict[counter]=ampstop
    	ampdict.append((counter,ampstart,ampstop))
        procampres[counter]=0

    procampres["DO"]=0
    procampres["HF"]=0
    procampres["NH"]=0
    procampres["BF"]=0


    print "******AMP DICTIONARY*******"
    print type(ampstartdict)
    print ampstartdict
    readprediction=dict()

    print procampres

    print "Now we are going to try and open the raw reads and do the same as we have done above..."
    d=list()
    filenamecounter=0
    for filename in glob.glob(os.path.join(args.watchdir, '*.fast5')):
        filenamecounter+=1
        d.append([filename,kmerhashT,kmerhashC,amplicons,ampstartdict,ampenddict,procampres])
    procdata=tuple(d)

    procampres["TF"]=filenamecounter



    results = p.map(process_hdf5, (procdata),chunksize=1)
    p.close()
    masterreadprediction=dict()
    for element in results:
        for amplicon in element:
            if (amplicon not in masterreadprediction):
                masterreadprediction[amplicon]=dict()
            for quality in element[amplicon]:
                if (quality not in masterreadprediction[amplicon]):
                    masterreadprediction[amplicon][quality]=dict()
                for filename in element[amplicon][quality]:
                    if (filename not in masterreadprediction[amplicon][quality]):
                        masterreadprediction[amplicon][quality][filename]=dict()
                    masterreadprediction[amplicon][quality][filename]["name"]=element[amplicon][quality][filename]["name"]
                    masterreadprediction[amplicon][quality][filename]["matchdistance"]=element[amplicon][quality][filename]["matchdistance"]

    print "Amplicon Read Counts"
    for amplicon in masterreadprediction:
        numberofreads = 0
        for i in range(5):
            try:
                if len(masterreadprediction[amplicon][i].keys()) > 0:
                    numberofreads += len(masterreadprediction[amplicon][i].keys())
            except Exception, err:
                print "",
        print "Amplicon Number:",amplicon,"Reads:",numberofreads


    print "Copying Amplicon Data"
    for amplicon in masterreadprediction:
        print "Amplicon Number",amplicon
    	counter = 0
        for i in range(5):
            try:
                if (len(masterreadprediction[amplicon][i].keys())>0):
                    if (args.verbose is True):
                        print len(masterreadprediction[amplicon][i].keys())
                    if (counter < args.depth):
                        ordered0 = OrderedDict(sorted(masterreadprediction[amplicon][i].iteritems(), key=lambda x: x[1]['matchdistance']))
                        for read in ordered0:
                            if (args.verbose is True):
                                print read, ordered0[read]["matchdistance"]
                            if not os.path.exists(args.targetpath):
                                os.makedirs(args.targetpath)
                            destdir = os.path.join(args.targetpath)
                            if not os.path.exists(destdir):
                                os.makedirs(destdir)
                            try:
                                filetocheck = os.path.split(read)
                                sourcefile = read
                                destfile = os.path.join(destdir,filetocheck[1])
                                if (args.verbose is True):
                                    print "sourcefile is:",sourcefile
                                    print "destfile is:",destfile
                                try:
                                    shutil.copy(sourcefile,destfile)
                                except Exception, err:
                                    print "File Copy Failed",err
                            except Exception, err:
                                print "Weird bug I don't GROK"
                            counter += 1
                            if counter >= args.depth:
                                break
            except Exception, err:
                if (args.verbose is True):
                    print "No reads of class "+str(i)

    exit()
