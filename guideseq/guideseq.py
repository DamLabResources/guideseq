# -*- coding: utf-8 -*-
"""

guideseq.py serves as the wrapper

"""

import os
import yaml
import argparse
import traceback

# Set up logger
import log
logger = log.createCustomLogger('root')

from alignReads import alignReads
from filterBackgroundSites import filterBackgroundSites
from umi import demultiplex, umitag, consolidate
import identifyOfftargetSites

DEFAULT_DEMULTIPLEX_MIN_READS = 10000
MAX_MISMATCHES = 6

CONSOLIDATE_MIN_QUAL = 15
CONSOLIDATE_MIN_FREQ = 0.9


class GuideSeq:

    def __init__(self):
        pass

    def parseManifest(self, manifest_path):
        logger.info('Loading manifest...')

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
            logger.error('Incomplete or incorrect manifest file. Please ensure your manifest contains all required fields.')
            quit()

        # Allow the user to specify min reads for demultiplex if they want
        if 'demultiplex_min_reads' in manifest_data:
            self.demultiplex_min_reads = manifest_data['demultiplex_min_reads']
        else:
            self.demultiplex_min_reads = DEFAULT_DEMULTIPLEX_MIN_READS

        # Make sure the user has specified a control barcode
        if 'control' not in self.samples.keys():
            raise AssertionError('Your manifest must have a control sample specified.')

        # Make sure the user has both a sample and a control
        if len(self.samples) < 2:
            raise AssertionError('Your manifest must have at least one control and one treatment sample.')

        logger.info('Successfully loaded manifest.')

    def demultiplex(self):

        logger.info('Demultiplexing undemultiplexed files...')

        # Take our two barcodes and concatenate them
        swapped_sample_barcodes = {}
        for sample in self.samples:
            barcode1 = self.samples[sample]['barcode1']
            barcode2 = self.samples[sample]['barcode2']
            barcode = barcode1[1:8] + barcode2[1:8]
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

            logger.info('Successfully demultiplexed reads.')
        except Exception as e:
            logger.error('Error demultiplexing reads.')
            print traceback.format_exc()
            quit()

    def umitag(self):
        logger.info('umitagging reads...')

        try:
            self.umitagged = {}
            for sample in self.samples:
                self.umitagged[sample] = {}
                self.umitagged[sample]['read1'] = os.path.join(self.output_folder, 'umitagged', sample + '.r1.umitagged.fastq')
                self.umitagged[sample]['read2'] = os.path.join(self.output_folder, 'umitagged', sample + '.r2.umitagged.fastq')

                umitag.umitag(self.demultiplexed[sample]['read1'],
                              self.demultiplexed[sample]['read2'],
                              self.demultiplexed[sample]['index1'],
                              self.demultiplexed[sample]['index2'],
                              self.umitagged[sample]['read1'],
                              self.umitagged[sample]['read2'],
                              os.path.join(self.output_folder, 'umitagged'))

            logger.info('Successfully umitagged reads.')
        except Exception as e:
            logger.error('Error umitagging')
            print traceback.format_exc()
            quit()

    def consolidate(self):
        logger.info('Consolidating reads...')

        try:
            self.consolidated = {}

            for sample in self.samples:
                self.consolidated[sample] = {}
                self.consolidated[sample]['read1'] = os.path.join(self.output_folder, 'consolidated', sample + '.r1.consolidated.fastq')
                self.consolidated[sample]['read2'] = os.path.join(self.output_folder, 'consolidated', sample + '.r2.consolidated.fastq')

                consolidate.consolidate(self.umitagged[sample]['read1'], self.consolidated[sample]['read1'], CONSOLIDATE_MIN_QUAL, CONSOLIDATE_MIN_FREQ)
                consolidate.consolidate(self.umitagged[sample]['read2'], self.consolidated[sample]['read2'], CONSOLIDATE_MIN_QUAL, CONSOLIDATE_MIN_FREQ)

            print self.consolidated
            logger.info('Successfully consolidated reads.')
        except Exception as e:
            logger.error('Error umitagging')
            print traceback.format_exc()
            quit()


    def alignReads(self):
        logger.info('Aligning reads...')

        try:
            self.aligned = {}
            for sample in self.samples:
                sample_alignment_path = alignReads(self.BWA_path, self.reference_genome, sample,
                                                                                         self.consolidated[sample]['read1'],
                                                                                         self.consolidated[sample]['read2'],
                                                                                         os.path.join(self.output_folder, 'aligned'))
                self.aligned[sample] = sample_alignment_path
                logger.info('Finished aligning reads to genome.')

        except Exception as e:
            logger.error('Error aligning')
            print traceback.format_exc()
            quit()

    def identifyOfftargetSites(self):
        logger.info('Identifying offtarget sites...')

        try:
            self.identified = {}

            # Identify offtarget sites for each sample
            for sample in self.samples:

                # Prepare sample annotations
                sample_data = self.samples[sample]
                annotations = {}
                annotations['Description'] = sample_data['description']
                annotations['Targetsite'] = sample

                if sample is 'control':
                    annotations['Sequence'] = ''
                else:
                    annotations['Sequence'] = sample_data['target']


                print annotations
                samfile = self.aligned[sample]

                self.identified[sample] = os.path.join(self.output_folder, sample + '_identifiedOfftargets.txt')

                identifyOfftargetSites.analyze(samfile, self.reference_genome, self.identified[sample], annotations)

            logger.info('Finished identifying offtarget sites.')

        except Exception as e:
            logger.error('Error identifying offtarget sites.')
            print traceback.format_exc()
            quit()

    def filterBackgroundSites(self):
        logger.info('Filtering background sites')

        try:
            self.filtered = {}

            # Filter background in each sample
            for sample in self.samples:
                if sample != 'control':
                    logger.info('Running background filtering for {0} sample'.format(sample))
                    self.filtered[sample] = os.path.join(self.output_folder, sample + '_backgroundFiltered.txt')
                    filterBackgroundSites(self.bedtools, self.identified[sample], self.identified['control'], self.filtered[sample])
                    logger.info('Finished background filtering for {0} sample'.format(sample))

            logger.info('Finished filtering background sites.')

        except Exception as e:
            logger.error('Error filtering background sites.')
            print traceback.format_exc()
            quit()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', '-m', help='Specify the manifest Path', required=True)
    parser.add_argument('--identifyAndFilter', action='store_true', default=False)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.identifyAndFilter:
        try:
            g = GuideSeq()
            g.parseManifest(args.manifest)

            # Bootstrap the aligned samfile paths
            g.aligned = {}
            for sample in g.samples:
                g.aligned[sample] = os.path.join(g.output_folder, 'aligned', sample + '.sam')

            g.identifyOfftargetSites()
            g.filterBackgroundSites()

        except Exception as e:
            print 'Error running only identify and filter.'
            print traceback.format_exc()
            quit()

    elif args.manifest:
        g = GuideSeq()
        g.parseManifest(args.manifest)
        g.demultiplex()
        g.umitag()
        g.consolidate()
        g.alignReads()
        g.identifyOfftargetSites()
        g.filterBackgroundSites()


if __name__ == '__main__':
    main()
