#!/usr/bin/env python

from __future__ import print_function, division
import argparse
import sys
import os
import hgvs.parser
import hgvs.dataproviders.uta
import hgvs.assemblymapper
import hgvs.normalizer
import pyhgvs
import pyhgvs.utils as pyhgvs_utils
import logging
import csv
from ometa.runtime import ParseError
from pygr.seqdb import SequenceFileDB
import traceback


'''
    Example run:
        ./brca_pseudonym_generator.py -j hg18.fa -k hg19.fa -l hg38.fa -r refseq_annotation.hg18.gp -s refseq_annotation.hg19.gp -t refseq_annotation.hg38.gp -i aggregated.tsv -o test.out -p > stdoutErrorLog.txt

    WARNING:
        Currently only works for insertion and deletion strings less than or equal to 100 bases long. Can be modified to be larger.
'''


def parse_args():
    """
    Description:
        function 'parse_args' parses arguments from command-line and returns an argparse
        object containing the arguments and their values. Default values are 'False' if option
        is not listed in the command, else the option value is set to True.
    """
    parser = argparse.ArgumentParser(description='Fill in hg18, hg19 genomic coordinates and cDNA hgvs strings in merged BRCA variant dataset.')
    parser.add_argument('-i', '--inBRCA', type=argparse.FileType('r'),
                        help='Input ENIGMA BRCA datatable file for conversion.')
    parser.add_argument('-j', '--inHg18', type=argparse.FileType('r'),
                        help='Input hg18 reference genome fasta file.')
    parser.add_argument('-k', '--inHg19', type=argparse.FileType('r'),
                        help='Input hg19 reference genome fasta file.')
    parser.add_argument('-l', '--inHg38', type=argparse.FileType('r'),
                        help='Input hg38 reference genome fasta file.')
    parser.add_argument('-r', '--inRefSeq18', type=argparse.FileType('r'),
                        help='Input refseq annotation hg18-based genepred file.')
    parser.add_argument('-s', '--inRefSeq19', type=argparse.FileType('r'),
                        help='Input refseq annotation hg19-based genepred file.')
    parser.add_argument('-t', '--inRefSeq38', type=argparse.FileType('r'),
                        help='Input refseq annotation hg38-based genepred file.')
    parser.add_argument('-p', '--calcProtein', dest='calcProtein', action='store_true',
                        help='Set flag for hgvs protein fill-in. May not result in complete fill-in.')
    parser.add_argument('-o', '--outBRCA', type=argparse.FileType('w'),
                        help='Output filled in ENIGMA BRCA datatable file.')
    parser.add_argument('--artifacts_dir', help='Artifacts directory with pipeline artifact files.')

    parser.set_defaults(calcProtein=False)
    options = parser.parse_args()
    return options


def main(args):

    options = parse_args()
    brcaFile = options.inBRCA
    hg18_fa = options.inHg18
    hg19_fa = options.inHg19
    hg38_fa = options.inHg38
    refSeq18 = options.inRefSeq18
    refSeq19 = options.inRefSeq19
    refSeq38 = options.inRefSeq38
    outputFile = options.outBRCA
    calcProtein = options.calcProtein
    artifacts_dir = options.artifacts_dir

    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)
    log_file_path = artifacts_dir + "brca-pseudonym-generator.log"
    logging.basicConfig(filename=log_file_path, filemode="w", level=logging.DEBUG)

    hgvs_parser = hgvs.parser.Parser()
    hgvs_dp = hgvs.dataproviders.uta.connect()
    hgvs_norm = hgvs.normalizer.Normalizer(hgvs_dp)
    hgvs_am = hgvs.assemblymapper.AssemblyMapper(hgvs_dp, assembly_name='GRCh38')

    genome36 = SequenceFileDB(hg18_fa.name)
    genome37 = SequenceFileDB(hg19_fa.name)
    genome38 = SequenceFileDB(hg38_fa.name)

    transcripts36 = pyhgvs_utils.read_transcripts(refSeq18)
    transcripts37 = pyhgvs_utils.read_transcripts(refSeq19)
    transcripts38 = pyhgvs_utils.read_transcripts(refSeq38)

    def get_transcript36(name):
        return transcripts36.get(name)

    def get_transcript37(name):
        return transcripts37.get(name)

    def get_transcript38(name):
        return transcripts38.get(name)

    hgvsG36ColumnName = 'Genomic_Coordinate_hg36'
    hgvsG37ColumnName = 'Genomic_Coordinate_hg37'
    hgvsG38ColumnName = 'Genomic_Coordinate_hg38'
    refSeqColumnName = 'Reference_Sequence'
    hgvsCDNAColumnName = 'HGVS_cDNA'
    hgvsCDNALOVDColumnName = 'HGVS_cDNA_LOVD'
    hgvsPColumnName = 'HGVS_Protein'

    # Set up header for output file
    input_file = csv.reader(brcaFile, delimiter='\t')
    output_file = csv.writer(outputFile, delimiter='\t')
    input_header_row = input_file.next()

    # The following new columns will contain data generated by this file
    new_columns_to_append = ["pyhgvs_Genomic_Coordinate_36", "pyhgvs_Genomic_Coordinate_37",
                          "pyhgvs_Genomic_Coordinate_38", "pyhgvs_Hg37_Start", "pyhgvs_Hg37_End",
                          "pyhgvs_Hg36_Start", "pyhgvs_Hg36_End", "pyhgvs_cDNA", "pyhgvs_Protein"]

    output_header_row = input_header_row + new_columns_to_append

    output_file.writerow(output_header_row)

    # Store indexes of the relevant columns
    hgvsG36Index = input_header_row.index(hgvsG36ColumnName)
    hgvsG37Index = input_header_row.index(hgvsG37ColumnName)
    hgvsG38Index = input_header_row.index(hgvsG38ColumnName)
    refSeqIndex = input_header_row.index(refSeqColumnName)
    hgvsCDNAIndex = input_header_row.index(hgvsCDNAColumnName)
    hgvsPIndex = input_header_row.index(hgvsPColumnName)
    hgvsCDNALOVDIndex = input_header_row.index(hgvsCDNALOVDColumnName)
    geneSymbolIndex = input_header_row.index("Gene_Symbol")
    synonymIndex = input_header_row.index("Synonyms")

    refSeqBRCA1Transcripts = ['NM_007294.2', 'NM_007300.3', 'NM_007299.3', 'NM_007298.3', 'NM_007297.3', 'U14680.1']
    refSeqBRCA2Transcripts = ['U43746.1']

    for line in input_file:
        if line[geneSymbolIndex] == 'BRCA1':
            line[refSeqIndex] = 'NM_007294.3'
        elif line[geneSymbolIndex] == 'BRCA2':
            line[refSeqIndex] = 'NM_000059.3'

        # Store for reference and debugging
        oldHgvsGenomic38 = line[refSeqIndex] + ':' + line[hgvsG38Index].split(',')[0]

        chrom38 = line[input_header_row.index("Chr")]
        offset38 = line[input_header_row.index("Pos")]
        ref38 = line[input_header_row.index("Ref")]
        alt38 = line[input_header_row.index("Alt")]

        # Edge cases to correct variant string formats for indels in order to be accepted by the counsyl parser
        if ref38 == '-': ref38 = ''
        if alt38 == '-': alt38 = ''
        if alt38 == 'None': alt38 = ''
        transcript38 = get_transcript38(line[refSeqIndex])
        transcript37 = get_transcript37(line[refSeqIndex])
        transcript36 = get_transcript36(line[refSeqIndex])

        # Normalize hgvs cdna string to fit what the counsyl hgvs parser determines to be the correct format
        if transcript38 is None:
            print("ERROR: could not parse transcript38 for variant: %s \n" % (line))
            continue
        cdna_coord = str(pyhgvs.format_hgvs_name("chr" + chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))
        chrom38, offset38, ref38, alt38 = pyhgvs.parse_hgvs_name(cdna_coord, genome38, get_transcript=get_transcript38)
        chrom37, offset37, ref37, alt37 = pyhgvs.parse_hgvs_name(cdna_coord, genome37, get_transcript=get_transcript37)
        chrom36, offset36, ref36, alt36 = pyhgvs.parse_hgvs_name(cdna_coord, genome36, get_transcript=get_transcript36)

        # Generate transcript hgvs cdna synonym string
        if line[synonymIndex] == "-":
            synonymString = []
        elif line[synonymIndex] == "":
            synonymString = []
        else:
            synonymString = line[synonymIndex].split(",")
        if line[geneSymbolIndex] == 'BRCA1':
            for transcriptName in refSeqBRCA1Transcripts:
                transcript38 = get_transcript38(transcriptName)
                cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))
                synonymString.append(cdna_synonym)
        elif line[geneSymbolIndex] == 'BRCA2':
            for transcriptName in refSeqBRCA2Transcripts:
                transcript38 = get_transcript38(transcriptName)
                cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))
                synonymString.append(cdna_synonym)

        # Add hgvs_cDNA values from LOVD to synonyms if not already present
        for cdna_coord_LOVD in line[hgvsCDNALOVDIndex].split(','):
            # Skip if blank
            if cdna_coord_LOVD == "-" or cdna_coord_LOVD is None or cdna_coord_LOVD == "":
                continue

            cdna_coord_LOVD = cdna_coord_LOVD.strip()

            # Don't add to synonyms if main hgvs_cDNA field is already equivalent to hgvs_cDNA value from LOVD
            cdna_coord_LOVD_for_comparison = cdna_coord_LOVD.split(':')[1]
            if cdna_coord_LOVD_for_comparison in line[hgvsCDNAIndex]:
                continue

            try:
                chrom38LOVD, offset38LOVD, ref38LOVD, alt38LOVD = pyhgvs.parse_hgvs_name(cdna_coord_LOVD, genome38, get_transcript=get_transcript38)
                if line[geneSymbolIndex] == 'BRCA1':
                    for transcriptName in refSeqBRCA1Transcripts:
                        transcript38 = get_transcript38(transcriptName)
                        cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38LOVD, int(offset38LOVD), ref38LOVD, alt38LOVD, genome38, transcript38, use_gene=False, max_allele_length=100))
                        if cdna_synonym not in synonymString:
                            synonymString.append(cdna_synonym)
                elif line[geneSymbolIndex] == 'BRCA2':
                    for transcriptName in refSeqBRCA2Transcripts:
                        transcript38 = get_transcript38(transcriptName)
                        cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38LOVD, int(offset38LOVD), ref38LOVD, alt38LOVD, genome38, transcript38, use_gene=False, max_allele_length=100))
                        if cdna_synonym not in synonymString:
                            synonymString.append(cdna_synonym)
            except Exception as e:
                print('parse error: {}'.format(cdna_coord_LOVD))
                print(e)

        protein_coord = None
        if calcProtein:
            try:
                genomic_change = '{0}:g.{1}:{2}>{3}'.format(chrom38, offset38, ref38, alt38)
                
                var_c1 = hgvs_parser.parse_hgvs_variant(cdna_coord)
                var_c1_norm = hgvs_norm.normalize(var_c1) # doing normalization explicitly to get a useful error message
                protein_coord = hgvs_am.c_to_p(var_c1_norm)
            except Exception as e:
                template = "An error of type {0} occured. Arguments:{1!r}"
                error_name = type(e).__name__
                message = template.format(error_name, e.args)
                logging.error(message)
                logging.error('Proposed GRCh38 Genomic change for error: %s', genomic_change)
                logging.error(line)

                # Exceptions related to invalid data
                data_errors = set(['HGVSParseError', 'HGVSError', 'HGVSInvalidVariantError', 'HGVSUnsupportedOperationError'])
                if error_name not in data_errors:
                    # output some more if exception doesn't seem to be related to invalid data
                    logging.error("Non data error raised")
                    logging.exception(message)
            

        # Add empty data for each new column to prepare for data insertion by index
        for i in range(len(new_columns_to_append)):
            line.append('-')

        line[output_header_row.index("pyhgvs_Genomic_Coordinate_36")] = '{0}:g.{1}:{2}>{3}'.format(chrom36,offset36,ref36,alt36)
        line[output_header_row.index("pyhgvs_Genomic_Coordinate_37")] = '{0}:g.{1}:{2}>{3}'.format(chrom37,offset37,ref37,alt37)
        line[output_header_row.index("pyhgvs_Genomic_Coordinate_38")] = '{0}:g.{1}:{2}>{3}'.format(chrom38,offset38,ref38,alt38)
        line[output_header_row.index("pyhgvs_Hg37_Start")] = str(offset37)
        line[output_header_row.index("pyhgvs_Hg37_End")] = str(int(offset37) + len(ref38) - 1)
        line[output_header_row.index("pyhgvs_Hg36_Start")] = str(offset36)
        line[output_header_row.index("pyhgvs_Hg36_End")] = str(int(offset36) + len(ref38) - 1)
        line[output_header_row.index("pyhgvs_cDNA")] = '{0}'.format(cdna_coord)
        if calcProtein == True:
            line[output_header_row.index("pyhgvs_Protein")] = '{0}'.format(str(protein_coord))
        line[synonymIndex] = ','.join(synonymString)

        output_file.writerow(line)

    hg18_fa.close()
    hg19_fa.close()
    hg38_fa.close()
    refSeq18.close()
    refSeq19.close()
    refSeq38.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
