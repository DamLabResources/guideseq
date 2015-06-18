# -*- coding: utf-8 -*-
"""

guideseq.py serves as the wrapper

"""

import os
import yaml
import argparse
from alignReads import alignReads


class GuideSeq:

    def __init__(self):
        pass

    def parseManifest(self, manifest_path):

        print 'Loading manifest...'

        with open(manifest_path, 'r') as f:
            manifest_data = yaml.load(f)

        try:
            self.BWA_path  = manifest_data['bwa']
            self.HG19_path = manifest_data['hg19']
            self.samples   = manifest_data['samples']
            self.output_path = manifest_data['output']
        except:
            print 'Incomplete or incorrect manifest file. Please ensure your manifest contains all required fields.'

        if 'control' not in self.samples.keys():
            raise AssertionError('Your manifest must have a control sample specified.')

        if len(self.samples.keys()) < 2:
            raise AssertionError('Your manifest must have at least one control and one treatment sample.')

        print 'Successfully loaded manifest.'


    def alignReads(self):
        print 'Aligning reads...'
        sample_alignment_paths = alignReads(self.BWA_path, self.HG19_path, self.samples, self.output_path)

        for (sample_name, alignment_path) in sample_alignment_paths.items():
            self.samples[sample_name]['alignment_path'] = alignment_path

        print 'Finished aligning reads to genome.'


    def demultiplex(self):
        pass

    def consolidate(self):
        pass

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

    print '../tests/manifest.yaml'

    if args.manifest:
        g = GuideSeq()
        g.parseManifest('../tests/manifest.yaml')
        g.alignReads()

        print g.samples

if __name__ == '__main__':
    main()
