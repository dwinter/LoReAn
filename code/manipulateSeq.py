#!/usr/bin/env python3
import datetime
import os
import subprocess
import sys
import tempfile

import align as align
import mapping
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqUtils import GC
from simplesam import Reader

#==========================================================================================================
# COMMANDS LIST

BEDTOOLS_SORT = 'bedtools sort -i %s'

BEDTOOLS_MERGE = 'bedtools merge -d 1'

BEDTOOLS_MASK = 'bedtools maskfasta -fi %s -bed %s -fo %s'

AWK = 'awk \'{if ($3 - $2 > %s) print $0} \''

BUILD_TABLE  = 'build_lmer_table -sequence  %s -freq %s'

REPEAT_SCOUT =  'RepeatScout -sequence %s -output %s -freq %s'

GFF3_REPEATS = 'rmOutToGFF3.pl %s > %s'

REPEAT_MASKER = 'RepeatMasker %s -e ncbi -lib %s -gff -pa %s -dir %s -nolow'

REPEAT_MODELER = 'RepeatModeler -LTRStruct -pa %s -database %s'

BUILD_DATABASE = 'BuildDatabase -name %s %s'


#==========================================================================================================


def adapter_find(reference_database, reads, threads, max_intron_length, working_dir, verbose):
    subset_fasta = reads + "subset.10000.fasta"
    with open(subset_fasta, "w") as fh:
        for rec in SeqIO.parse(reads, "fasta"):
            if int(rec.id) < 10000:
                SeqIO.write(rec, fh, "fasta")

    bam = mapping.minimap(reference_database, subset_fasta, threads, max_intron_length, working_dir, verbose)
    #soft_clip_regions = soft_clip(bam)
    fasta_gz = bam + ".fasta"
    cmd = "extractSoftclipped %s | zcat | fastqToFa /dev/stdin %s" % (bam, fasta_gz)
    if verbose:
        sys.stderr.write('Executing: %s\n\n' % cmd)
    extract_clip = subprocess.Popen(cmd, cwd=working_dir, shell=True)
    extract_clip.communicate()

    list_short = []
    list_long = []
    dict_uniq = {}
    with open(fasta_gz, "r") as handle:
        for rec in SeqIO.parse(handle, "fasta"):
            name_seq = str(rec.id)
            name = name_seq.split("_")[0]
            if name in dict_uniq:
                if len(dict_uniq[name].seq) > len(rec.seq):
                    list_long.append(dict_uniq[name])
                    list_short.append(rec)
                else:
                    list_short.append(dict_uniq[name])
                    list_long.append(rec)
            else:
                dict_uniq[name] = rec
    long_file = fasta_gz + ".long.fasta"
    with open(long_file, "w") as fh:
        SeqIO.write(list_long, fh, "fasta")
    short_file = fasta_gz + ".short.fasta"
    with open(short_file, "w") as fh:
        SeqIO.write(list_short, fh, "fasta")
    list_file_clip = [(long_file, "long"),(short_file,"short")]
    for clip_file in list_file_clip:
        kmer_start = 21
        list_kmer = []
        while kmer_start < 120:
            cmd = "jellyfish count -s 10000000 -m %s -o %s.%s.kmer %s" % (kmer_start, kmer_start, clip_file[1], clip_file[0])
            if verbose:
                sys.stderr.write('Executing: %s\n\n' % cmd)
            jelly_count = subprocess.Popen(cmd, cwd=working_dir, shell=True)
            jelly_count.communicate()
            cmd = "jellyfish dump -L 2 -ct %s.%s.kmer | sort -k2n | tail -n 1" % (kmer_start, clip_file[1])
            if verbose:
                sys.stderr.write('Executing: %s\n\n' % cmd)
            jelly_dump = subprocess.Popen(cmd, cwd=working_dir, stdout=subprocess.PIPE, shell=True)
            out_dump = jelly_dump.communicate()[0].decode('utf-8')
            mer = out_dump.split("\t")[0]
            a_count = mer.count("A")
            t_count = mer.count("T")
            if a_count > t_count:
                bias_count = a_count
            else:
                bias_count = t_count
            data_kmer = (kmer_start, mer, GC(mer), (bias_count/kmer_start)*100,  (bias_count/kmer_start)*100 - GC(mer) )
            list_kmer.append(data_kmer)
            kmer_start += 5
        value_adapter = 0
        for i in list_kmer:
            if i[4] > int(value_adapter):
                value_adapter = i[4]
                kmer_done = i[1]

    adapter_file = os.path.join(working_dir, "adapter.fasta")
    if value_adapter > 0:
        with open(adapter_file, "w") as fh:
            record = SeqRecord(Seq(str(kmer_done)), id="adapter")
            SeqIO.write(record, fh, "fasta")
    return adapter_file

def soft_clip(long_sam):

    in_file = open(long_sam, "r")
    in_sam = Reader(in_file)
    soft_clip_file = "test.fasta"
    with open(soft_clip_file, "w") as fh:
        for line in in_sam:
            if "S" in line.cigars[0][1]:
                if line.flag == 0 or line.flag == 16:
                    fh.write(line.rname + "\n")
                    fh.write(line.seq + "\n")

    return soft_clip_file


def filterLongReads(fastq_filename, min_length, max_length, wd, adapter, threads, align_score_value, reference_database, max_intron_length, verbose, stranded):
    """
    Filters out reads longer than length provided and it is used to call the alignment and parse the outputs
    """
    scoring = [3, -6, -5, -2]
    out_filename = wd + fastq_filename.split("/")[-1] + '.long_reads.filtered.fasta'
    filter_count = 0
    if not os.path.isfile(out_filename):
        with open(out_filename, "w") as output_handle:
            if fastq_filename.endswith('fastq') or fastq_filename.endswith('fq'):
                for record in SeqIO.parse(fastq_filename, "fastq"):
                    if len(str(record.seq)) > int(min_length) < int(max_length):
                        record.description = ""
                        record.name = ""
                        record.id = str(filter_count)
                        filter_count += 1
                        SeqIO.write(record, output_handle, "fasta")
            elif fastq_filename.endswith('fasta') or fastq_filename.endswith('fa'):
                for record in SeqIO.parse(fastq_filename, "fasta"):
                    if int(min_length) < len(str(record.seq)) < int(max_length):
                        record.description = ""
                        record.name = ""
                        record.id = str(filter_count)
                        filter_count += 1
                        SeqIO.write(record, output_handle, "fasta")
    else:
        sys.stdout.write(('Filtered FASTQ existed already: ' + out_filename + ' --- skipping\n'))
    if stranded and adapter:
        if not os.path.isfile(adapter):
            adapter_aaa = adapter_find(reference_database, out_filename, threads, max_intron_length, wd, verbose)
            if not os.path.exists(adapter_aaa) or os.path.getsize(adapter_aaa) == 0:
                sizes = [rec.id for rec in SeqIO.parse(out_filename, "fasta")]
                stranded_value = False
                fmtdate = '%H:%M:%S %d-%m'
                now = datetime.datetime.now().strftime(fmtdate)
                sys.stdout.write(
                    "###FINISHED FILTERING AT:\t" + now + "###\n###LOREAN KEPT\t\033[32m" + str(len(sizes)) +
                    "\033[0m\tREADS AFTER LENGTH FILTERING###\n")
                return out_filename, stranded_value
        else:
            adapter_aaa = adapter
        out_filename_oriented = os.path.join(wd, fastq_filename.split("/")[-1] + '.longreads.filtered.oriented.fasta')
        filter_count, out_filename_oriented, stranded_value= align.adapter_alignment(out_filename, adapter_aaa, scoring, align_score_value,
                                                                                     out_filename_oriented, threads, min_length)
        fmtdate = '%H:%M:%S %d-%m'
        now = datetime.datetime.now().strftime(fmtdate)
        if stranded_value:
            sys.stdout.write("###FINISHED FILTERING AT:\t" + now + "###\n###LOREAN KEPT\t\033[32m" + str(filter_count) +
                         "\033[0m\tREADS AFTER LENGTH FILTERING AND ORIENTATION###\n")
        else:
            sys.stdout.write("###FINISHED FILTERING AT:\t" + now + "###\n###LOREAN KEPT\t\033[32m" + str(filter_count) +
                             "\033[0m\tREADS AFTER LENGTH FILTERING###\n")
        return out_filename_oriented, stranded_value
    else:
        sizes = [rec.id for rec in SeqIO.parse(out_filename, "fasta")]
        stranded_value = False
        fmtdate = '%H:%M:%S %d-%m'
        now = datetime.datetime.now().strftime(fmtdate)
        sys.stdout.write("###FINISHED FILTERING AT:\t" + now + "###\n###LOREAN KEPT\t\033[32m" + str(len(sizes)) +
                         "\033[0m\tREADS AFTER LENGTH FILTERING###\n")
        return out_filename, stranded_value


def maskedgenome(wd, ref, gff3, length, verbose):
    """
    this module is used to mask the genome when a gff or bed file is provided
    """

    outputmerge = tempfile.NamedTemporaryFile(delete=False, mode="w", prefix="genome.", suffix=".masked.gff3", dir=wd)
    cmd = BEDTOOLS_SORT % gff3
    cmd1 = BEDTOOLS_MERGE
    cmd2 = AWK % length
    if verbose:
        sys.stdout.write(cmd)
        sys.stdout.write(cmd1)
        sys.stdout.write(cmd2)
    bedsort = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    bedmerge = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stdin=bedsort.stdout, shell=True)
    awk = subprocess.Popen(cmd2, stdin=bedmerge.stdout, stdout=outputmerge, shell=True)
    awk.communicate()

    masked = ref + ".masked.fasta"
    cmd = BEDTOOLS_MASK % (ref, outputmerge.name, masked)
    if verbose:
        sys.stdout.write(cmd)
    maskfasta=subprocess.Popen(cmd, cwd=wd, shell=True)
    maskfasta.communicate()
    return masked


def repeatsfind(genome, working_dir, threads_use, verbose):

    #name_gff = genome.split("/")[-1] + ".out.gff"

    fasta_path = os.path.join(working_dir, genome.split("/")[-1] + ".masked") #Fv10027.fasta.ModelRepets-families.fa
    fasta_out = working_dir + genome.split("/")[-1] + "-families.fa"
    gff_out = working_dir + genome.split("/")[-1] + ".out.gff3"
    if not os.path.exists(fasta_out):
        sys.stdout.write("###RUNNING REPEATMODELER TO FIND REPETITIVE ELEMENTS###\n")
        log = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)
        err = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)

        cmd = BUILD_DATABASE % (genome.split("/")[-1], genome)
        if verbose:
            sys.stdout.write(cmd)
        build = subprocess.Popen(cmd, cwd=working_dir, stdout=log, stderr=err, shell=True)
        build.communicate()


        log = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)
        err = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)

        cmd = REPEAT_MODELER % (threads_use, genome.split("/")[-1])
        if verbose:
            sys.stdout.write(cmd)
        scout = subprocess.Popen(cmd, cwd=working_dir, stdout=log, stderr=err, shell=True)
        scout.communicate()
        if not os.path.exists(fasta_out):
            sys.stdout.write("###REPEATMODELER DID NOT FIND ANY FAMILY. REVERTING TO ANNOTATE NON-MASKED GENOME###\n")
            return (genome,fasta_out,gff_out)
    log = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)
    err = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)

    sys.stdout.write("###RUNNING REPEATMASKER TO MASK THE GENOME###\n")

    cmd = REPEAT_MASKER % (genome, fasta_out, str(threads_use), working_dir)
    if verbose:
        sys.stdout.write(cmd)
    mask = subprocess.Popen(cmd, cwd=working_dir, stdout=log, stderr=err, shell=True)
    mask.communicate()

    log = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)
    err = tempfile.NamedTemporaryFile(delete=False, mode='w', dir=working_dir)
    cmd = GFF3_REPEATS % (working_dir + genome.split("/")[-1] + ".out", gff_out)
    if verbose:
        sys.stdout.write(cmd)
    mask = subprocess.Popen(cmd, cwd=working_dir, stdout=log, stderr=err, shell=True)
    mask.communicate()

    return (fasta_path, fasta_out, gff_out)


if __name__ == '__main__':
    #filterLongReads(fastq_filename, min_length, max_length, wd, adapter, threads, a, alignm_score_value)
    filterLongReads(*sys.argv[1:])