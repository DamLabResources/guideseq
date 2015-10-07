# -*- coding: utf-8 -*-
"""

guideseq.py serves as the wrapper

"""

import os
import yaml
import argparse
from alignReads import alignReads
from umi import demultiplex, umitag, consolidate

DEFAILT_DEMULTIPLEX_MIN_READS = 10000

class GuideSeq:

    def __init__(self):
        pass

    def parseManifest(self, manifest_path):

        print 'Loading manifest...'

        with open(manifest_path, 'r') as f:
            manifest_data = yaml.load(f)

        try:
            self.BWA_path  = manifest_data['bwa']
            self.reference_genome = manifest_data['reference_genome']
            self.output_folder = manifest_data['output_folder']
            self.undemultiplexed = manifest_data['undemultiplexed']
            self.sample_barcodes = manifest_data['sample_barcodes']

        except Exception as e:
            print 'Incomplete or incorrect manifest file. Please ensure your manifest contains all required fields.'
            quit()

        if 'demultiplex_min_reads' in manifest_data:
            self.demultiplex_min_reads = manifest_data['demultiplex_min_reads']
        else:
            self.demultiplex_min_reads = DEFAILT_DEMULTIPLEX_MIN_READS

        if 'control' not in self.sample_barcodes.keys():
            raise AssertionError('Your manifest must have a control sample specified.')
        if len(self.sample_barcodes) < 2:
            raise AssertionError('Your manifest must have at least one control and one treatment sample.')

        print 'Successfully loaded manifest.'


    def demultiplex(self):

        print 'Demultiplexing undemultiplexed files...'
        swapped_sample_barcodes = dict((value, key) for key, value in self.sample_barcodes.iteritems())

        try:
            demultiplex.demultiplex(self.undemultiplexed['forward'], 
                                    self.undemultiplexed['reverse'],
                                    self.undemultiplexed['index1'],
                                    self.undemultiplexed['index2'],
                                    swapped_sample_barcodes,
                                    os.path.join(self.output_folder, 'undemultiplexed'),
                                    min_reads=self.demultiplex_min_reads)

            self.demultiplexed = {}
            for sample in self.sample_barcodes:
                self.demultiplexed[sample] = {}
                self.demultiplexed[sample]['read1'] = os.path.join(self.output_folder, 'undemultiplexed', sample + '.r1.fastq')
                self.demultiplexed[sample]['read2'] = os.path.join(self.output_folder, 'undemultiplexed', sample + '.r2.fastq')
                self.demultiplexed[sample]['index1'] = os.path.join(self.output_folder, 'undemultiplexed', sample + '.i1.fastq')
                self.demultiplexed[sample]['index2'] = os.path.join(self.output_folder, 'undemultiplexed', sample + '.i2.fastq')

            print 'Successfully demultiplexed reads.'
        except Exception as e:
            print 'Error demultiplexing reads.'
            print e
            quit()

    def umitag(self):
        print 'umitagging reads...'

        try:
            for sample in self.sample_barcodes:    
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

    def consolidate(self):
        print 'Consolidating reads...'

        try:
            self.consolidated = {}

            for sample in self.sample_barcodes:    
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


    def alignReads(self):
        print 'Aligning reads...'

        sample_alignment_paths = alignReads(self.BWA_path, self.reference_genome, self.undemux_sample_paths, self.output_folder)
        for (sample_name, alignment_path) in sample_alignment_paths.items():
            self.samples[sample_name]['alignment_path'] = alignment_path
        print 'Finished aligning reads to genome.'

        # print 'Error aligning reads.'


    def filter(self):
        pass

    def identifyOfftargetSites(self):
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



if __name__ == '__main__':
    main()
