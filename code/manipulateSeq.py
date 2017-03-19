#!/usr/bin/env python3
from Bio import pairwise2
from Bio import SeqIO
import sys
from sys import argv
import numpy as np
import os
from Bio.Seq import reverse_complement
from multiprocessing import Pool
import itertools
from Bio.SeqUtils import GC
import os.path as op
import ctypes as ct
import timeit as ti
import math
from Bio import SeqIO
import ssw_lib
from Bio.Seq import reverse_complement




def to_int(seq, lEle, dEle2Int):
    """
    translate a sequence into numbers
    @param  seq   a sequence
    """
    num_decl = len(seq) * ct.c_int8
    num = num_decl()
    for i,ele in enumerate(seq):
        try:
            n = dEle2Int[ele]
        except KeyError:
            n = dEle2Int[lEle[-1]]
        finally:
            num[i] = n
    return num

def align_one(ssw, qProfile, rNum, nRLen, nOpen, nExt, nFlag, nMaskLen):
    """
    align one pair of sequences
    @param  qProfile   query profile
    @param  rNum   number array for reference
    @param  nRLen   length of reference sequence
    @param  nFlag   alignment flag
    @param  nMaskLen   mask length
    """
    res = ssw.ssw_align(qProfile, rNum, ct.c_int32(nRLen), nOpen, nExt, nFlag, 0, 0, int(nMaskLen))

    nScore = res.contents.nScore
    nScore2 = res.contents.nScore2
    nRefBeg = res.contents.nRefBeg
    nRefEnd = res.contents.nRefEnd
    nQryBeg = res.contents.nQryBeg
    nQryEnd = res.contents.nQryEnd
    nRefEnd2 = res.contents.nRefEnd2
    lCigar = [res.contents.sCigar[idx] for idx in range(res.contents.nCigarLen)]
    nCigarLen = res.contents.nCigarLen
    ssw.align_destroy(res)

    return (nScore, nScore2, nRefBeg, nRefEnd, nQryBeg, nQryEnd, nRefEnd2, nCigarLen, lCigar)

def align_call(record, adapter):
    lEle = []
    dRc = {} 
    dEle2Int = {}
    dInt2Ele = {}
    nMatch = 2
    nMismatch = 1
    nOpen = 1
    nExt = -2
    nFlag = 0
    #if not args.sMatrix:
    lEle = ['A', 'C', 'G', 'T', 'N']
    for i,ele in enumerate(lEle):
        dEle2Int[ele] = i
        dEle2Int[ele.lower()] = i
        dInt2Ele[i] = ele
    nEleNum = len(lEle)
    lScore = [0 for i in range(nEleNum**2)]
    for i in range(nEleNum-1):
        for j in range(nEleNum-1):
            if lEle[i] == lEle[j]:
                lScore[i*nEleNum+j] = nMatch
            else:
                lScore[i*nEleNum+j] = -nMismatch
    mat = (len(lScore) * ct.c_int8) ()
    mat[:] = lScore
    
    ssw = ssw_lib.CSsw("./")
    sQSeq = record.seq
    sQId = record.id
    if len(sQSeq) > 30:
        nMaskLen = len(sQSeq) / 2
    else:
        nMaskLen = 15
    outputAlign = []
    qNum = to_int(sQSeq, lEle, dEle2Int)
    qProfile = ssw.ssw_init(qNum, ct.c_int32(len(sQSeq)), mat, len(lEle), 2)
    sQRcSeq = reverse_complement(sQSeq)
    qRcNum = to_int(sQRcSeq, lEle, dEle2Int)
    qRcProfile = ssw.ssw_init(qRcNum, ct.c_int32(len(sQSeq)), mat, len(lEle), 2)
    sRSeq = adapter.seq
    sRId = adapter.id
    rNum = to_int(sRSeq, lEle, dEle2Int)
    res = align_one(ssw, qProfile, rNum, len(sRSeq), nOpen, nExt, nFlag, nMaskLen)
    resRc = None
    resRc = align_one(ssw, qRcProfile, rNum, len(sRSeq), nOpen, nExt, nFlag, nMaskLen)
    strand = 0
    if res[0] == resRc[0]:
        next
    if res[0] > resRc[0]:
        resPrint = res
        strand = 0
        outputAlign = [sRId , sQId, strand, resPrint[0]]
    elif res[0] < resRc[0]:
        resPrint = resRc
        strand = 1
        outputAlign = [sRId , sQId, strand, resPrint[0]]
    ssw.init_destroy(qProfile)
    ssw.init_destroy(qRcProfile)
    return outputAlign

def filterLongReads(fastqFilename, min_length, max_length, wd, a):
    '''Filters out reads longer than length provided'''
    finalSeq= []
    if a:
        outFilename = wd + fastqFilename + '.longreads.filtered.fasta'
    else:
        outFilename = fastqFilename + '.longreads.filtered.fasta'

    if os.path.isfile(outFilename):
            print(('Filtered FASTQ existed already: ' +
                outFilename + ' --- skipping\n'))
            return outFilename, 0

    if fastqFilename.endswith('fastq') or fastqFilename.endswith('fq'):
        record_dict = SeqIO.to_dict(SeqIO.parse(fastqFilename, "fastq"))
    elif fastqFilename.endswith('fasta') or fastqFilename.endswith('fa'):
        record_dict = SeqIO.to_dict(SeqIO.parse(fastqFilename, "fasta"))
        #print (fastqFilename)
    outFile = open(outFilename, 'w')
    filter_count = 0
    gcvalue = []
    for key in record_dict:
        #print (key)
        gc = int(GC(record_dict[key].seq))
        gcvalue.append(gc)
    meanV = int(np.mean(gcvalue))
    stdV = int(np.std(gcvalue))
    for key in record_dict:
        if int(GC(record_dict[key].seq)) < (meanV + 3*stdV) or int(GC(record_dict[key].seq)) > (meanV - 3*stdV):
            if len(str(record_dict[key].seq)) > int(min_length) and len(str(record_dict[key].seq)) < int(max_length):
                record_dict[key].id = str(filter_count)
                finalSeq.append(record_dict[key])
                filter_count += 1    
    SeqIO.write(finalSeq, outFilename, "fasta")
    return (outFilename, filter_count)

def findOrientation(fastqFilename, min_length, max_length, wd, fastaAdapt):
    '''Filters out reads longer than length provided'''
    outFilename = wd + fastqFilename + '.longreads.filtered.oriented.fasta'
    seqDict = {}
    scoreDict = {}
    listScore=[]
    listSeqGood = []
    listAdapter = []
    finalSeq = []
    listSeqAdap = []
    finalDNA = []
    if os.path.isfile(outFilename):
            print(('Filtered FASTQ existed already: ' +
                outFilename + ' --- skipping\n'))
            return outFilename, 0
    for adpt in SeqIO.parse(fastaAdapt, "fasta"):
        listAdapter.append(adpt.id)
        listSeqAdap.append(adpt)
    if fastqFilename.endswith('fastq') or fastqFilename.endswith('fq'):
        record_dict = SeqIO.to_dict(SeqIO.parse(fastqFilename, "fastq"))
    elif fastqFilename.endswith('fasta') or fastqFilename.endswith('fa'):
        record_dict = SeqIO.to_dict(SeqIO.parse(fastqFilename, "fasta"))
    else:
        print("can not recognize file type")
    outFile = open(outFilename, 'w')
    filter_count = 0
    gcvalue = []
    allData = len(record_dict)
    for key in record_dict:
        gc = int(GC(record_dict[key].seq))
        gcvalue.append(gc)
    meanV = int(np.mean(gcvalue))
    stdV = int(np.std(gcvalue))
    for key in record_dict:
        if int(GC(record_dict[key].seq)) < (meanV + stdV) or int(GC(record_dict[key].seq)) > (meanV - stdV):
            if len(str(record_dict[key].seq)) > int(min_length) and len(str(record_dict[key].seq)) < int(max_length):
                record_dict[key].id = str(filter_count)
                filter_count += 1
                for adpter in listSeqAdap:
                    alingRes = align_call(record_dict[key], adpter)
                    if len(alingRes) == 0:
                        next
                    else:
                        seqDict[record_dict[key].id] = [record_dict[key], alingRes[2]]
                        scoreDict[record_dict[key].id] =  alingRes[3]
    for key in scoreDict:
        listScore.append(float(scoreDict[key]))
    a = np.array(listScore)
    mean = np.mean(a)
    stderrS = np.std(a)
    valueOptimal = mean - stderrS
    filter_count = 0
    for key in scoreDict:
        if scoreDict[key]  > valueOptimal and seqDict[key][1] == 0:
            filter_count += 1
            finalSeq.append(seqDict[key][0])
        elif scoreDict[key]  > valueOptimal and seqDict[key][1] == 1:
            filter_count += 1
            sequenze = reverse_complement(seqDict[key][0].seq)
            seqDict[key][0].seq = sequenze
            finalSeq.append(seqDict[key][0])
    outFile.close()
    SeqIO.write(finalSeq, outFilename, "fasta")
    lost = allData - filter_count 
    return (outFilename, filter_count, lost)

if __name__ == '__main__':
    
    fastaSeq = argv[1]
    min_length = argv[2]
    max_length = argv[3]
    wd = argv[4]
    fastaAdapt= argv[5]
    #threads = argv[6]
    
    #filterLongReads(fastaSeq, min_length, max_length, wd, a = True)
    findOrientation(fastaSeq, min_length, max_length, wd, fastaAdapt)
