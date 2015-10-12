# -*- coding: utf-8 -*-
"""

guideseq.py serves as the wrapper

"""

import os
import sys
import yaml
import argparse
from alignReads import alignReads
from umi import demultiplex, umitag, consolidate
import identifyOfftargetSites

DEFAILT_DEMULTIPLEX_MIN_READS = 10000
MAX_MISMATCHES = 6

class GuideSeq:

    def __init__(self):
        pass

    def parseManifest(self, manifest_path):

        print 'Loading manifest...'

        with open(manifest_path, 'r') as f:
            manifest_data = yaml.load(f)

        try:
            self.BWA_path  = manifest_data['bwa']
            self.bedtools = manifest_data['bedtools']
            self.reference_genome = manifest_data['reference_genome']
            self.output_folder = manifest_data['output_folder']
            self.undemultiplexed = manifest_data['undemultiplexed']
            self.samples = manifest_data['samples']

        except Exception as e:
            print 'Incomplete or incorrect manifest file. Please ensure your manifest contains all required fields.'
            quit()

        # Allow the user to specify min reads for demultiplex if they want
        if 'demultiplex_min_reads' in manifest_data:
            self.demultiplex_min_reads = manifest_data['demultiplex_min_reads']
        else:
            self.demultiplex_min_reads = DEFAILT_DEMULTIPLEX_MIN_READS

        # Make sure the user has specified a control barcode
        if 'control' not in self.samples.keys():
            raise AssertionError('Your manifest must have a control sample specified.')

        # Make sure the user has both a sample and a control
        if len(self.samples) < 2:
            raise AssertionError('Your manifest must have at least one control and one treatment sample.')

        print 'Successfully loaded manifest.'


    def demultiplex(self):

        print 'Demultiplexing undemultiplexed files...'

        print self.samples

        swapped_sample_barcodes = {}
        for sample in self.samples:
            barcode = self.samples[sample]['barcode']
            swapped_sample_barcodes[barcode] = sample

        try:
            demultiplex.demultiplex(self.undemultiplexed['forward'],
                                    self.undemultiplexed['reverse'],
                                    self.undemultiplexed['index1'],
                                    self.undemultiplexed['index2'],
                                    swapped_sample_barcodes,
                                    os.path.join(self.output_folder, 'demultiplexed'),
                                    min_reads=self.demultiplex_min_reads)

            self.demultiplexed = {}
            for sample in self.samples:
                self.demultiplexed[sample] = {}
                self.demultiplexed[sample]['read1'] = os.path.join(self.output_folder, 'demultiplexed', sample + '.r1.fastq')
                self.demultiplexed[sample]['read2'] = os.path.join(self.output_folder, 'demultiplexed', sample + '.r2.fastq')
                self.demultiplexed[sample]['index1'] = os.path.join(self.output_folder, 'demultiplexed', sample + '.i1.fastq')
                self.demultiplexed[sample]['index2'] = os.path.join(self.output_folder, 'demultiplexed', sample + '.i2.fastq')

            print 'Successfully demultiplexed reads.'
        except Exception as e:
            print 'Error demultiplexing reads.'
            print e
            quit()

    def umitag(self):
        print 'umitagging reads...'

        try:
            for sample in self.samples:
                umitag.umitag(self.demultiplexed[sample]['read1'],
                              self.demultiplexed[sample]['read2'],
                              self.demultiplexed[sample]['index1'],
                              self.demultiplexed[sample]['index2'],
                              os.path.join(self.output_folder, 'umitagged', sample + '.r1.umitagged.fastq'),
                              os.path.join(self.output_folder, 'umitagged', sample + '.r2.umitagged.fastq'),
                              os.path.join(self.output_folder, 'umitagged'))

            print 'Successfully umitagged reads.'
        except Exception as e:
            print 'Error umitagging'
            print e
            quit()

    def consolidate(self):
        print 'Consolidating reads...'

        try:
            self.consolidated = {}

            for sample in self.samples:    
                umitag.umitag(self.demultiplexed[sample]['read1'],
                              self.demultiplexed[sample]['read2'],
                              self.demultiplexed[sample]['index1'],
                              self.demultiplexed[sample]['index2'],
                              os.path.join(self.output_folder, 'umitagged', sample + '.r1.umitagged.fastq'),
                              os.path.join(self.output_folder, 'umitagged', sample + '.r2.umitagged.fastq'),
                              os.path.join(self.output_folder, 'umitagged'))

                self.consolidated[sample] = {}
                self.consolidated[sample]['read1'] = os.path.join(self.output_folder, 'umitagged', sample + '.r1.umitagged.fastq')
                self.consolidated[sample]['read2'] = os.path.join(self.output_folder, 'umitagged', sample + '.r2.umitagged.fastq')

            print self.consolidated
            print 'Successfully consolidated reads.'
        except Exception as e:
            print 'Error umitagging'
            print e
            quit()


    def alignReads(self):
        print 'Aligning reads...'

        try:
            self.aligned = {}
            for sample in self.samples:
                sample_alignment_path = alignReads(self.BWA_path, self.reference_genome, sample,
                                                                                         self.consolidated[sample]['read1'],
                                                                                         self.consolidated[sample]['read1'],
                                                                                         os.path.join(self.output_folder, 'aligned'))
                self.aligned[sample] = sample_alignment_path
                print 'Finished aligning reads to genome.'

        except Exception as e:
            print 'Error aligning'
            print e
            quit()

    def identifyOfftargetSites(self):
        print 'Identifying offtarget sites...'

        try:
            # Identify offtarget sites for each sample
            for sample in self.samples:

                # Prepare sample annotations
                sample_data = self.samples[sample]
                annotations = {}
                annotations['Description'] = sample_data['description']
                annotations['Treatment'] = sample_data['treatment']
                annotations['Cells'] = sample_data['cell_type']
                annotations['Targetsite'] = sample

                if target is 'control':
                    annotations['Sequence'] = 'N/A'
                else:
                    annotations['Sequence'] = sample_data['target']

                # Only identify offtargets for non-control samples
                if sample is not 'control':
                    old_stdout = sys.stdout
                    offtargets_log = open(os.path.join(self.output_folder, 'offtargets', sample + '.txt'))
                    sys.stdout = offtargets_log

                    samfile = self.aligned[sample]
                    experimental_design_dict = {}
                    identifyOfftargetSites.analyze(samfile, experimental_design_dict, self.reference_genome,
                                                                                      MAX_MISMATCHES,
                                                                                      os.path.join(self.output_folder, 'identifiedOfftargets.txt'),
                                                                                      annotations)

                    sys.stdout = old_stdout
                    offtargets_log.close()

        except Exception as e:
            print 'Error identifying offtarget sites.'
            print e
            quit()

    def filter(self):
        pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', '-m', help='Specify the manifest Path', required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.manifest:
        g = GuideSeq()
        g.parseManifest(args.manifest)
        g.demultiplex()
        g.umitag()
        g.consolidate()
        g.alignReads()
        g.identifyOfftargetSites()



if __name__ == '__main__':
    main()
