#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import subprocess as sb
import sys
import tempfile
import warnings
from multiprocessing import Pool

import gffutils
import gffutils.gffwriter as gffwriter
from Bio import SeqIO
from Bio.Alphabet import generic_dna
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

#======================================================================================================================

GT_GFF3 = 'gt gff3 -sort -tidy %s'

GT_GFF3_R = 'gt gff3 -retainids -sort -tidy %s'

BEDTOOLS_GET_FASTA = 'bedtools getfasta -fi %s -bed %s -fo %s'

GFFREAD_W = 'gffread -W -g %s -w %s -y %s %s'

GFFREAD_M = 'gffread -F -M -C -K -Q -Z --force-exons -o %s %s'

GFFREAD_M_S = 'gffread -M -Y -Q -K -F -o %s %s'

EXONERATE = 'exonerate --model coding2genome --bestn 1 --refine region --showtargetgff yes --query %s --target %s'

PASA_VAL = 'pasa_gff3_validator.pl %s'

BEDTOOLS_SORT = 'bedtools sort -i %s'

BEDTOOLS_MERGE = 'bedtools merge -d -100 -s -o count,distinct -c 9,9'

GT_GFF3_INTRON = 'gt gff3 -sort -addintrons -tidy %s'

BEDTOOLS_INTERSECT = 'bedtools intersect -v -a %s -b %s'

GT_RETAINID = 'gt gff3 -sort -tidy -addintrons -retainids %s'

GT_GFF3TOGTF = 'gt gff3_to_gtf %s'

BEDTOOLS_GETFASTA =  'bedtools getfasta -fi %s -bed %s -fo %s -name -split'

CAT = 'cat %s'

#======================================================================================================================

gene_count = 0
exon_cds_count = 0
chrold = ""
cds_lorean = "LoReAn.CDS."
exons_lorean = "LoReAn.exons."
other_lorean = "LoReAn.other."
cds_count_lorean = 0



def longest(gff_file, fasta, proc, wd, verbose):
    outputFilenameLeft = tempfile.NamedTemporaryFile(delete=False, dir=wd, prefix="longest.")
    gff_out = gffwriter.GFFWriter(outputFilenameLeft.name)

    gt_com = GT_GFF3_INTRON % gff_file
    gff_file_outfile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(gff_file_out, "w")
    errorFilefile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=gff_file_outfile, stderr=errorFilefile, shell=True)
    gt_call.communicate()

    gt_com = GT_GFF3TOGTF % gff_file_outfile.name
    gtf_file_outfile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(gtf_file_out, "w")
    errorFilefile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=gtf_file_outfile, stderr=errorFilefile, shell=True)
    gt_call.communicate()


    db1 = gffutils.create_db(gff_file_outfile.name, ':memory:', merge_strategy='create_unique', keep_order=True)


    fasta_file_outfile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(fasta_file_out, "w")
    errorFilefile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    com = 'cufflinks_gtf_genome_to_cdna_fasta.pl %s %s' % (gtf_file_outfile.name, fasta)
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=fasta_file_outfile, stderr=errorFilefile, shell=True)
    call.communicate()

    gff_file_outfile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(gff_file_out_u, "w")
    errorFilefile = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    com = 'cufflinks_gtf_to_alignment_gff3.pl %s' % gtf_file_outfile.name
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=gff_file_outfile, stderr=errorFilefile, shell=True)
    call.communicate()

    gff_file_outfile_1 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(gff_file_out, "w")
    errorFilefile_1 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    com = 'TransDecoder.LongOrfs -m 10 -t %s' % fasta_file_outfile.name
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=gff_file_outfile_1, stderr=errorFilefile_1, cwd=wd, shell=True)
    call.communicate()

    gff_file_outfile_2 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".out") #open(gff_file_out, "w")
    errorFilefile_2 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.", suffix=".err") #open(errorFile, "w")
    wd_fasta = fasta_file_outfile.name
    com = 'TransDecoder.Predict --single_best_orf --cpu %s --retain_long_orfs 10 -t %s' % (proc, wd_fasta)
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=gff_file_outfile_2, stderr=errorFilefile_2, cwd=wd, shell=True)
    call.communicate()

    gff_file_outfile_3 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.") #open(outputFilename, "w")
    errorFilefile_3 = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=wd, prefix="longest.") #open(errorFile, "w")
    transdecoder = tempfile.NamedTemporaryFile(delete=False)

    com = 'cdna_alignment_orf_to_genome_orf.pl %s %s %s' % (wd_fasta + '.transdecoder.gff3', gff_file_outfile.name, wd_fasta)

    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=gff_file_outfile_3, stderr=errorFilefile_3, cwd=wd, shell=True)
    call.communicate()


    listErr = []
    err_file = open(errorFilefile.name, "r")
    for line in err_file:
        if line.startswith("Warning"):
            listErr.append(("mRNA" + line.split("::")[1]).split(".")[0])
    listErrUniq = list(set(listErr))

    for evm in listErrUniq:
        for i in db1.children(evm, featuretype='CDS', order_by='start'):
            gff_out.write_rec(i)
        gff_out.write_rec(db1[evm])
        for i in db1.parents(evm, featuretype='gene', order_by='start'):
            gff_out.write_rec(i)
        for i in db1.children(evm, featuretype='exon', order_by='start'):
            gff_out.write_rec(i)

    gff_files = [outputFilenameLeft.name, gff_file_outfile.name]
    outputFilenameFinal = wd + 'finalAnnotation.Transdecoder.gff3'



    with open(outputFilenameFinal, 'wb') as wfd:
        for f in gff_files:
            with open(f, 'rb') as fd:
                shutil.copyfileobj(fd, wfd, 1024 * 1024 * 10)

    return outputFilenameFinal


def genename_last(gff_filename, prefix, verbose, wd, dict_ref_name, step):

    global prefix_name
    prefix_name = prefix
    out = tempfile.NamedTemporaryFile(delete=False, mode="w", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, mode="w")
    gt_com = GT_GFF3 % gff_filename
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=out, stderr=err, shell=True)
    gt_call.communicate()

    db1 = gffutils.create_db(out.name, ':memory:', merge_strategy='create_unique', keep_order=True, transform=transform_name)
    gene_count = 0
    list_mrna = [mRNA.attributes["ID"][0] for mRNA in db1.features_of_type('mRNA')]
    out_gff = tempfile.NamedTemporaryFile(delete=False, prefix="gffread", suffix=".gff3", dir=wd)
    gff_out = gffwriter.GFFWriter(out_gff.name)
    gene_name = []
    for evm in list_mrna:
        for i in db1.children(evm, featuretype='CDS', order_by='start'):
            if i.chrom in dict_ref_name:
                i.chrom = dict_ref_name[i.chrom]
            gff_out.write_rec(i)
        i = db1[evm]
        if i.chrom in dict_ref_name:
            i.chrom = dict_ref_name[i.chrom]
        gff_out.write_rec(i)
        for i in db1.parents(evm, featuretype='gene', order_by='start'):
            if i.chrom in dict_ref_name:
                i.chrom = dict_ref_name[i.chrom]
            id_gene = i.attributes['ID'][0]
            if not id_gene in gene_name:
                gff_out.write_rec(i)
                gene_name.append(id_gene)
        for i in db1.children(evm, featuretype='exon', order_by='start'):
            if i.chrom in dict_ref_name:
                i.chrom = dict_ref_name[i.chrom]
            gff_out.write_rec(i)
    gff_out.close()
    if "pasa" in step:
        out_name = os.path.join(wd, "Final.evm.update.gff3")
        with open(out_name, "w") as fh:
            gt_com = GT_RETAINID % out_gff.name
            if verbose:
                sys.stderr.write('Executing: %s\n\n' % gt_com)
            gt_call = subprocess.Popen(gt_com, stdout=fh, stderr=err, shell=True)
            gt_call.communicate()
    if "lorean" in step:
        out_name = os.path.join(wd, "Final.LoReAn.update.gff3")
        with open(out_name, "w") as fh:
            gt_com = GT_RETAINID % out_gff.name
            if verbose:
                sys.stderr.write('Executing: %s\n\n' % gt_com)
            gt_call = subprocess.Popen(gt_com, stdout=fh, stderr=err, shell=True)
            gt_call.communicate()
    if verbose:
        print(out_name)
    return out_name


def transform_name(f):
    global gene_count
    global chrold
    global exon_cds_count
    chrold = ""
    if f.featuretype == 'gene':
        f.source = "LoReAn"
        if chrold == "" or f.chrom in chrold:
            chrold = f.chrom
            gene_count += 10
            fatureattgene = str(prefix_name) + '_' + str(chrold) + '_G_' + str(gene_count)
            f.attributes['Name'] = fatureattgene
        else:
            chrold = f.chrom
            gene_count = 0
            gene_count += 10
            fatureattgene = str(prefix_name) + '_' + str(chrold) + '_G_' + str(gene_count)
            f.attributes['Name'] = fatureattgene
        for field in f.attributes:
            if "ID" in field:
                id = f.attributes["ID"]
            elif "Name" in field:
                name = f.attributes["Name"]
        f.attributes = ""
        gene = {}
        gene["ID"] = id
        gene["Name"] = name
        f.attributes = gene

    elif f.featuretype == 'mRNA':
        f.source = "LoReAn"
        for field in f.attributes:
            if "ID" in field:
                id = f.attributes["ID"]
            elif "Parent" in field:
                parent = f.attributes["Parent"]
        f.attributes = ""
        mRNA = {}
        mRNA["ID"] = id
        mRNA["Parent"] = parent
        f.attributes = mRNA
    else:
        f.source = "LoReAn"
        exon_cds_count += 1
        for field in f.attributes:
            if "Parent" in field:
                parent = f.attributes["Parent"]
        f.attributes = ""
        code = {}
        code["Parent"] = parent
        code["ID"] = "LoReAn-" + str(exon_cds_count)
        f.attributes = code
    return f


def exonerate(ref, gff_file, proc, wd, verbose):

    ##THIS removes the warning. the check of the longest protein was giving a warining. if Biopython change, this could be a problem

    warnings.filterwarnings("ignore")


    exon_file_out = gff_file + ".exons.fasta"
    prot_file_out = gff_file + ".prot.fasta"
    errorFile = gff_file + ".gffread_err.log"
    logFile = exon_file_out + "gffread_log.log"
    com = GFFREAD_W % (ref, exon_file_out, prot_file_out, gff_file)
    fasta_file_outfile = open(logFile, "w")
    errorFilefile = open(errorFile, "w")
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=fasta_file_outfile, cwd=wd, stderr=errorFilefile, shell=True)
    call.communicate()
    fasta_file_outfile.close()
    errorFilefile.close()
    list_complete = []
    dict_incomplete = {}
    dict_fasta_prot = {}
    longest_prot = []
    list_total = []
    list_single_exons = []
    list_incomplete = []
    for record in SeqIO.parse(prot_file_out, "fasta"):
        list_total.append(record.id)
        if record.seq.startswith("M"):
            list_complete.append(record.id)
        else:
            list_incomplete.append(record.id)
            dict_incomplete[record.id] = record.id
    for record in SeqIO.parse(exon_file_out, "fasta"):
        list_fields = record.description.split(' ')
        for elem in list_fields:
            if elem.startswith('exons'):
                exon_number = elem.split(",")
                if (len(exon_number)) > 0:
                    list_single_exons.append(record.id)
                    if record.id in dict_incomplete:
                        newrecord = record.reverse_complement()
                        input_seq = str(record.seq)
                        startP = re.compile('ATG')
                        nuc = input_seq.replace('\n', '')
                        longest = (0,)
                        for m in startP.finditer(nuc):
                            if len(Seq(nuc)[m.start():].translate(to_stop=True)) > longest[0]:
                                pro = Seq(nuc)[m.start():].translate(to_stop=True)
                                longest = [len(pro), nuc[m.start():m.start() + len(pro) * 3 + 3]]
                                if len(longest) == 2:
                                    record.seq = Seq(longest[1])
                                    dict_fasta_prot[record.id] = record
                                else:
                                    dict_fasta_prot[record.id] = record
                        input_seq = str(newrecord.seq)
                        startP = re.compile('ATG')
                        nuc = input_seq.replace('\n', '')
                        longest = (0,)
                        for m in startP.finditer(nuc):
                            if len(Seq(nuc)[m.start():].translate(to_stop=True)) > longest[0]:
                                pro = Seq(nuc)[m.start():].translate(to_stop=True)
                                longest = [len(pro), nuc[m.start():m.start() + len(pro) * 3 + 3]]
                                if len(longest) == 2:
                                    if record.id in dict_fasta_prot:
                                        if (len((dict_fasta_prot[record.id]).seq)) < (len(longest[1])):
                                            record.seq = Seq(longest[1])
                                            dict_fasta_prot[record.id] = record
                                    elif len(longest) == 2:
                                        record.seq = Seq(longest[1])
                                        dict_fasta_prot[record.id] = record
                                    else:
                                        dict_fasta_prot[record.id] = record

    for mod in dict_fasta_prot:
        longest_prot.append(dict_fasta_prot[mod])
    prot_file_out_mod = prot_file_out + ".mod.fasta"
    SeqIO.write(longest_prot, prot_file_out_mod, "fasta")

    pool = Pool(processes=int(proc))
    list_get_seq= []
    list_short = []
    record_dict = SeqIO.to_dict(SeqIO.parse(exon_file_out, "fasta"))
    for key in dict_fasta_prot:
        if key in record_dict:
            list_short.append(key)
            output_filename_prot = os.path.join(wd, key + '.prot.fasta')
            SeqIO.write(dict_fasta_prot[key], output_filename_prot, "fasta")
            list_fields = record_dict[key].description.split(' ')
            for elem in list_fields:
                output_filename = wd + key + '.genome.fasta'
                bedFile = wd + key + '.genome.bed'
                if (elem.startswith('loc') and elem.endswith('+')) or (elem.startswith('loc') and elem.endswith('-')):
                    coordsList = elem.split('|', -2)
                    chrN = coordsList[0].split(':')
                    coord = coordsList[1].split('-')
                    locus = '\t'.join([chrN[1], coord[0], coord[1]])
                    locus = locus + '\n'
                    bedhandler = open(bedFile, 'w')
                    bedhandler.write(locus)
                    bedhandler.close()
                    data = [ref, bedFile, output_filename, output_filename_prot, verbose, wd]
                    list_get_seq.append(data)

    results_get = pool.map(get_fasta, list_get_seq, chunksize=1)
    results = pool.map(runExonerate, results_get, chunksize=1)


    db1 = gffutils.create_db(gff_file, ':memory:', merge_strategy='create_unique', keep_order=True)
    list_gene_complete = []
    list_gene_incomplete = []
    for mRNA in list_complete:
        for mRNA_ok in db1.parents(mRNA, featuretype='gene', order_by='start'):
            list_gene_complete.append(mRNA_ok.attributes["ID"][0])
    for mRNA in list_incomplete:
        for mRNA_ok in db1.parents(mRNA, featuretype='gene', order_by='start'):
            list_gene_incomplete.append(mRNA_ok.attributes["ID"][0])
    list_gene_complete = sorted(list(set(list_gene_complete)))
    list_gene_incomplete = sorted(list(set(list_gene_incomplete)))
    list_gene_ok_uniq = sorted(list(set(list_gene_complete) - set(list_gene_incomplete)))

    output_filename_gff = os.path.join(wd , 'exonerate_step1.gff3')
    gff_out = gffwriter.GFFWriter(output_filename_gff)
    for evm in list_gene_ok_uniq:
        gff_out.write_rec(db1[evm])
        for i in db1.children(evm):
            gff_out.write_rec(i)

    exonerate_files = results + [output_filename_gff]
    gff_out.close()
    orintedFIleN = os.path.join(wd, 'exonerate_step2_oldnames.gff3')
    with open(orintedFIleN, 'wb') as wfd:
        for f in exonerate_files:
            with open(f, 'rb') as fd:
                shutil.copyfileobj(fd, wfd, 1024 * 1024 * 10)
    outfile_gff = tempfile.NamedTemporaryFile(delete=False, prefix="exonerate_step3.", suffix=".gff3", dir=wd)
    log = tempfile.NamedTemporaryFile(delete=False, prefix="exonerate_step3.", suffix=".log", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, prefix="exonerate_step3.", suffix=".err", dir=wd)
    cmd = GFFREAD_M_S % (outfile_gff.name, orintedFIleN)
    gffread = subprocess.Popen(cmd, cwd=wd, shell=True, stdout=log, stderr=err)
    gffread.communicate()
    db_gffread = gffutils.create_db(outfile_gff.name, ':memory:', merge_strategy='create_unique', keep_order=True,
                                    transform=transform_func)

    outfile_out = tempfile.NamedTemporaryFile(delete=False, prefix="exonerate_step4.final.", suffix=".gff3", dir=wd)
    gff_out_s = gffwriter.GFFWriter(outfile_out.name)

    for gene in db_gffread.features_of_type("gene"):
        for i in db_gffread.children(gene, order_by='start'):
            gff_out_s.write_rec(i)
        gff_out_s.write_rec(db_gffread[gene])
    return outfile_out.name


def transform_func(x):

    if 'locus' in x.featuretype:
        x.featuretype = "gene"
        #x.attributes['ID'] = x.attributes['locus']
        x.source = "LoReAn"
        return x
    elif 'mRNA' in x.featuretype:
        x.attributes['Parent'] = x.attributes['locus']
        x.source = "LoReAn"
        return x
    else:
        x.source = "LoReAn"
        return x

def get_fasta(list_data):
    err = tempfile.NamedTemporaryFile(delete=True)
    log = tempfile.NamedTemporaryFile(delete=True)

    com = BEDTOOLS_GET_FASTA % (list_data[0], list_data[1], list_data[2])
    if list_data[4]:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, cwd = list_data[5], shell=True, stderr=err, stdout=log)
    call.communicate()
    os.remove(list_data[1])
    combList = [list_data[3], list_data[2], list_data[4], list_data[5]]
    return combList

def runExonerate(commandList):
    outputFilenameProt = commandList[0]
    outputFilename = commandList[1]
    protGff = outputFilenameProt + ".exonOut"
    errorFile = outputFilenameProt + ".exonerate_err.log"
    protGff_outfile = open(protGff, "w")
    errorFilefile = open(errorFile, "w")
    com = EXONERATE % (outputFilenameProt, outputFilename)
    if commandList[2]:
        sys.stderr.write('Executing: %s\n\n' % com)
    call = subprocess.Popen(com, stdout=protGff_outfile, cwd = commandList[3], stderr=errorFilefile, shell=True)
    call.communicate()
    fileGff = open(protGff, "r")
    protGff3 = protGff + ".gff3"
    fileFinalGff = open(protGff3, "w")
    gff = fileGff.readlines()
    for line in gff:
        if "exonerate:" in line:
            splitLine = line.split("\t")
            # sys.stdout.write (splitLine)
            if (len(splitLine)) > 8:
                chNr = splitLine[0].split(":")
                start = chNr[1].split("-")[0]
                elm = splitLine[8].split(";")
                if "gene" in splitLine[2]:
                    nameGene = elm[1].split(" ")
                    geneList = [chNr[0], "LoReAn", splitLine[2], str(int(splitLine[3]) + int(start)),
                                str(int(splitLine[4]) + int(start)), '.', splitLine[6], splitLine[7],
                                "ID=" + nameGene[2]]
                    mRNAList = [chNr[0], "LoReAn", 'mRNA', str(int(splitLine[3]) + int(start)),
                                str(int(splitLine[4]) + int(start)), '.', splitLine[6], splitLine[7],
                                "ID=" + nameGene[2] + ".mRNA;Parent=" + nameGene[2]]
                    fileFinalGff.write(('\t'.join(geneList)) + "\n")
                    fileFinalGff.write(('\t'.join(mRNAList)) + "\n")
                if "cds" in splitLine[2]:
                    cdsList = [chNr[0], "LoReAn", "CDS", str(int(splitLine[3]) + int(start)),
                               str(int(splitLine[4]) + int(start)), splitLine[5], splitLine[6], splitLine[7],
                               "Parent=" + nameGene[2] + ".mRNA"]
                    fileFinalGff.write(('\t'.join(cdsList)) + "\n")
                if "exon" in splitLine[2]:
                    exonList = [chNr[0], "LoReAn", splitLine[2], str(int(splitLine[3]) + int(start)),
                                str(int(splitLine[4]) + int(start)), splitLine[5], splitLine[6], splitLine[7],
                                "Parent=" + nameGene[2] + ".mRNA"]
                    fileFinalGff.write(('\t'.join(exonList)) + "\n")
    fileFinalGff.close()
    if os.stat(errorFile).st_size == 0:
        os.remove(errorFile)
        os.remove(protGff)
    os.remove(outputFilenameProt)
    os.remove(outputFilename)

    return protGff3

def genename_evm(gff_filename, verbose, wd, dict_ref_name, upgrade):

    match = {}
    for name in dict_ref_name:
        match[dict_ref_name[name]] = name
    if upgrade != "":
        out = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=".gff3", dir=wd)
        #with open() as fho:
        with open(gff_filename, "r") as fh:
            for line in fh:
                elements = line.split("\t")
                if match[elements[0]]:
                    elements[0] = match[elements[0]]
                    out.write("\t".join(elements))
        gff_filename = out.name


    gene_evm = "evm.TU."
    mRNA_evm = "evm.model."
    out = tempfile.NamedTemporaryFile(delete=False, mode="w", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, mode="w")
    gt_com = GT_GFF3 % gff_filename
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=out, stderr=err, shell=True)
    gt_call.communicate()

    db1 = gffutils.create_db(out.name, ':memory:', merge_strategy='create_unique', keep_order=True)
    list_gene = [gene.attributes["ID"][0] for gene in db1.features_of_type('gene')]
    list_chr = [chr.chrom for chr in db1.features_of_type('gene')]
    chr_count_gene = {}
    chr_count_mRNA = {}

    chrs = list(set(list_chr))
    for elm in chrs:
        chr_count_gene[elm] = 0
        chr_count_mRNA[elm] = 0

    out_gff = tempfile.NamedTemporaryFile(delete=False, prefix="gffread_parse", suffix=".gff3", dir=wd)
    gff_out = gffwriter.GFFWriter(out_gff.name)
    for evm in list_gene:
        exon_count = 0
        cds_count = 0
        gene_chr = db1[evm].chrom
        gene = db1[evm]
        count_gene = chr_count_gene[gene_chr] + 1
        chr_count_gene[gene_chr] = count_gene
        id_new_gene = gene_evm + gene_chr + "." + str(count_gene)
        gene.attributes["ID"][0] = id_new_gene
        gff_out.write_rec(gene)
        for i in db1.children(evm, featuretype='mRNA', order_by='start'):
            mRNA = i
            mRNA_old = i.attributes["ID"][0]
            count_mRNA = chr_count_mRNA[gene_chr] + 1
            chr_count_mRNA[gene_chr] = count_mRNA
            id_new_mRNA = mRNA_evm + gene_chr + "." + str(count_mRNA)
            mRNA.attributes["Parent"][0] = id_new_gene
            mRNA.attributes["ID"][0] = id_new_mRNA
            gff_out.write_rec(mRNA)
            for e in db1.children(mRNA_old, featuretype='exon', order_by='start'):
                exon_count += 1
                exon = e
                exon.attributes["Parent"][0] = mRNA.attributes["ID"][0]
                exon.attributes["ID"] = id_new_mRNA + ".exon" + str(exon_count)
                gff_out.write_rec(exon)
            for c in db1.children(mRNA_old, featuretype='CDS', order_by='start'):
                cds_count += 1
                cds = c
                cds.attributes["Parent"] = mRNA.attributes["ID"][0].split(",")[0]
                cds.attributes["ID"] = "cds." + str(cds_count) + "." + id_new_mRNA
                gff_out.write_rec(cds)
    gff_out.close()

    out = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="new_name_update.", suffix= ".gff3", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, mode="w", dir=wd)
    gt_com = GT_GFF3_R % out_gff.name
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=out, stderr=err, shell=True)
    gt_call.communicate()
    if verbose:
        print(out.name)
    return out.name

def genename_lorean(gff_filename, verbose, wd):


    outfile_gff = tempfile.NamedTemporaryFile(delete=False, prefix="genename_lorean.1.", suffix=".gff3", dir=wd)
    log = tempfile.NamedTemporaryFile(delete=False, prefix="genename_lorean.1.", suffix=".log", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, prefix="genename_lorean.1.", suffix=".err", dir=wd)
    cmd = GFFREAD_M % (outfile_gff.name, gff_filename)

    if verbose:
        sys.stderr.write('Executing: %s\n\n' % cmd)
    gffread = subprocess.Popen(cmd, cwd=wd, shell=True, stdout=log, stderr=err)
    gffread.communicate()
    out_final = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix = "genename_lorean.2.", suffix=".gff3", dir=wd)
    log = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genename_lorean.2.", suffix=".log", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genename_lorean.2.", dir=wd, suffix=".last.gt_gff3.err")
    gt_com = 'gt gff3 -retainids -sort -force -tidy -o %s %s' % (out_final.name, outfile_gff.name)
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=log, stderr=err, shell=True)
    gt_call.communicate()
    path_out = os.path.join(wd, "genename_lorean.3.gff3")
    with open(out_final.name, "r") as fh, open(path_out, "w") as fhd:
        count = 0
        for line_f in fh:
            line = line_f.rstrip()
            fields = line.split("\t")
            if len(fields) == 9:
                if fields[2] == "locus":
                    attributes = fields[8].split(";")
                    for elemt in attributes:
                        if elemt.startswith("ID"):
                            fields[8] = elemt
                            fields[2] = "gene"
                            fields[1] = "LoReAn"
                elif fields[2] == "mRNA":
                    new_attrib = []
                    attributes = fields[8].split(";")
                    for elemt in attributes:
                        if elemt.startswith("ID"):
                            new_attrib.append(elemt)
                        elif elemt.startswith("locus"):
                            parent = "Parent=" + elemt.split("=")[-1]
                            new_attrib.append(parent)
                    fields[8] = ";".join(new_attrib)
                else:
                    count += 1
                    fields[8] = fields[8] + ";ID=" + fields[2] + "." + str(count)
            line_o = "\t". join(fields) + "\n"
            if not line_o.startswith("###"):
                fhd.write(line_o)
    out_1 = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genename_lorean.4.", suffix=".gff3", dir=wd)
    log = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genename_lorean.4.", suffix=".log", dir=wd)
    err = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genename_lorean.4.", dir=wd, suffix=".last.gt_gff3.err")
    gt_com = 'gt gff3 -retainids -sort -force -tidy -o %s %s' % (out_1.name, path_out)
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % gt_com)
    gt_call = subprocess.Popen(gt_com, stdout=log, stderr=err, shell=True)
    gt_call.communicate()
    return out_1.name

def transform_cds(x):
    global cds_count_lorean
    cds_count_lorean += 1
    if 'locus' in x.featuretype:
        x.featuretype = "gene"
        #x.attributes['ID'] = x.attributes['locus']
        x.attributes = {'ID': x.attributes['ID'], 'Name': x.attributes['transcripts'][0].split("_")[0]}
        x.source = "LoReAn"
        return x
    elif 'mRNA' in x.featuretype:
        x.source = "LoReAn"
        x.attributes['Parent'] = x.attributes['locus']
        x.attributes = {'ID': x.attributes['ID'], 'Parent': x.attributes['Parent']}
        return x
    elif 'CDS' in x.featuretype:
        x.attributes = {'ID': cds_lorean + str(cds_count_lorean), 'Parent': x.attributes['Parent']}
        x.source = "LoReAn"
        return x
    elif 'exon' in x.featuretype:
        x.attributes = {'ID': exons_lorean + str(cds_count_lorean), 'Parent': x.attributes['Parent']}
        x.source = "LoReAn"
        return x
    else:
        print(x.attributes )
        x.attributes = {'ID': other_lorean + str(cds_count_lorean), 'Parent': x.attributes['Parent']}
        x.source = "LoReAn"
        return x

def add_removed_evm(pasa, exon, wd):
    """
    here the clusters of sequence from the same locus are prepared
    """

    db_evm = gffutils.create_db(pasa, ':memory:', merge_strategy='create_unique', keep_order=True)
    ids_evm = [gene.attributes["ID"][0] for gene in db_evm.features_of_type("mRNA")]

    db_gmap = gffutils.create_db(exon, ':memory:', merge_strategy='create_unique', keep_order=True)
    ids_gmap_full = [gene.attributes["ID"][0] for gene in db_gmap.features_of_type("gene")]
    ids_gmap = [gene.attributes["ID"][0].split("_")[0] for gene in db_gmap.features_of_type("mRNA")]


    uniq_evm = [evm for evm in ids_evm if evm not in ids_gmap]
    uniq_gene = [gene.attributes["ID"][0] for mrna in uniq_evm for gene in db_evm.parents(mrna)]
    uniq = list(set(uniq_gene))


    outfile = tempfile.NamedTemporaryFile(delete=False, prefix="additional.", suffix=".gff3", dir=wd)
    gff_out_s = gffwriter.GFFWriter(outfile.name)

    for name in uniq:
        for i in db_evm.children(name, order_by='start'):
            gff_out_s.write_rec(i)
        gff_out_s.write_rec(db_evm[name])
    for name in ids_gmap_full:
        for i in db_gmap.children(name, order_by='start'):
            gff_out_s.write_rec(i)
        gff_out_s.write_rec(db_gmap[name])
    gff_out_s.close()

    return outfile.name




#final_evm="/home/lfaino/lfainoData/lorean/LoReAn_Example/Crispa/LoReAn_crispa/run/exonerate/exonerate_step4.final.4e4aoxwb.gff3"
#genome = "/home/lfaino/lfainoData/lorean/LoReAn_Example/Crispa/LoReAn_crispa/run/split/scaffold3.fasta.masked.rename.fasta"


def pep_seq(myFasta, final_evm):
    fasta = {}
    db = gffutils.create_db(final_evm, ':memory:', merge_strategy="create_unique", keep_order=True)
    gff_file = final_evm + ".gff3"
    gff_out = gffwriter.GFFWriter(gff_file)
    for t in db.features_of_type('mRNA', order_by='start'):
        position = []
        seq_combined = ''
        j = 0
        for i in db.children(t, featuretype='CDS', order_by='start'):
            j += 1
            if j == 1:
                pphase = i[7]
            seq = i.sequence(myFasta, use_strand=False)
            seq_combined += seq
            position = position + [i.start,i.stop]
        seq_combined = SeqRecord(Seq(seq_combined, generic_dna))
        #print(t.attributes["ID"][0])
        #print(seq_combined.seq)
        if t.strand == '-':
            pphase = i[7]
            seq_combined = seq_combined.reverse_complement()
        if pphase == "0" or pphase == ".":
            seq_transl = seq_combined.translate()
        elif pphase == "1":
            seq_transl = seq_combined[1:].translate()
        elif pphase == "2":
            seq_transl = seq_combined[2:].translate()
        seq_transl.description = position
        seq_transl.id = t.id
        position = sorted(position)
        t.start = position[0]
        t.stop = position[-1]
        fasta[str(seq_transl.seq)] = [seq_transl, t]
    count = 0
    for key in fasta:
        for i in db.parents(fasta[key][1], featuretype='gene', order_by='start'):
            gff_out.write_rec(i)
            i.start = fasta[key][1].start
            i.stop = fasta[key][1].stop
        gff_out.write_rec(fasta[key][1])
        for i in db.children(fasta[key][1], featuretype='CDS', order_by='start'):
            gff_out.write_rec(i)
        for i in db.children(fasta[key][1], featuretype='CDS', order_by='start'):
            count += 1
            i.featuretype="exon"
            if "ID" in i.attributes:
                i.attributes["ID"][0] = i.attributes["ID"][0] + "-" + str(count)
            else:
                i.attributes["ID"] = ["exon" + "-" + str(count)]
            gff_out.write_rec(i)
    return (gff_file)

def gff_filter(final_evm, myFasta):
    file_out = final_evm + ".mod.gff3"
    with open(final_evm, "r") as fh, open(file_out, "w") as fhd:
        for line in fh:
            if not line.startswith("#"):
                elm = line.split("\t")
                elm[8] = elm[8].replace("locus", "Parent")
                elm[2] = elm[2].replace("locus", "gene")
                fhd.write("\t".join(elm))
    db = gffutils.create_db(file_out, ':memory:', merge_strategy="create_unique", keep_order=True)

    b = []
    mrna_retain = []
    for t in db.features_of_type('gene', order_by='start'):
        c = 0
        for i in db.children(t, featuretype='mRNA', order_by='start'):
            c += 1
        if c > 1:
            b.append(t)
        else:
            mrna_retain.append(i.attributes["ID"][0])
    mrna_select = []
    for t in b:
        seq_multiple = []
        for a in db.children(t, featuretype='mRNA', order_by='start'):
            seq_combined = ''
            j = 0
            for i in db.children(a, featuretype='CDS', order_by='start'):
                j += 1
                if j == 1:
                    pphase = i[7]
                seq = i.sequence(myFasta, use_strand=False)
                seq_combined += seq
            seq_combined = SeqRecord(Seq(seq_combined, generic_dna))
            if t.strand == '-':
                pphase = i[7]
                seq_combined = seq_combined.reverse_complement()
            if pphase == "0" or pphase == ".":
                seq_transl = seq_combined.translate()
            elif pphase == "1":
                seq_transl = seq_combined[1:].translate()
            elif pphase == "2":
                seq_transl = seq_combined[2:].translate()
            seq_transl.id = a.attributes["ID"][0]
            if seq_multiple:
                seq_multiple_len = len(seq_multiple)
                c = 0
                while seq_multiple_len > c:
                    a1 = str(seq_multiple[c].seq)
                    a2 =      str(seq_transl.seq)
                    if a1.rstrip("*").startswith(a2.rstrip("*")) and len(a1) < len(a2):
                        seq_multiple[c] = seq_transl
                    elif  a2.rstrip("*").startswith(a1.rstrip("*")) and len(a1) < len(a2):
                        seq_multiple[c] = seq_transl
                    else:
                        seq_multiple = seq_multiple + [seq_transl]
                    c+=1
            else:
                seq_multiple = [seq_transl]
        mrna_select = mrna_select + seq_multiple
    mrna_select_name = []
    for seq in mrna_select:
        mrna_select_name.append(seq.id)
    mrna_total = sorted(mrna_retain + mrna_select_name)
    gff_file = final_evm + ".final.gff3"
    gff_out = gffwriter.GFFWriter(gff_file)
    for key in mrna_total:
        for i in db.parents(key, featuretype='gene', order_by='start'):
            gff_out.write_rec(i)
        gff_out.write_rec(db[key])
        for i in db.children(key, featuretype='CDS', order_by='start'):
            gff_out.write_rec(i)
        for i in db.children(key, featuretype='exon', order_by='start'):
            gff_out.write_rec(i)
    return(gff_file)

def remove_redudant(genome, final_evm):
    fasta = pep_seq(genome, final_evm)
    gff_new = fasta + ".gffread.gff3"
    cm = "gffread -M -H -V -g %s -K %s -F -o %s" % (genome, fasta, gff_new)
    gffread = sb.Popen(cm, shell=True, stdout=sb.PIPE, stderr=sb.PIPE)
    gffread.communicate()
    gff_file = gff_filter(gff_new, genome)
    #print(gff_file)
    return (gff_file)

if __name__ == '__main__':
    #strand(*sys.argv[1:])
    #gff_filename = exonerate(*sys.argv[1:])
    #genename_lorean(gff_filename, "True", "./")
    a=remove_redudant(*sys.argv[1:])
    #update2 = exonerate(*sys.argv[1:])
    #genename_evm(*sys.argv[1:])
