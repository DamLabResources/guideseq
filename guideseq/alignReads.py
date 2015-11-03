import subprocess
import os
import logging

"""
alignReads
"""

def alignReads(BWA_path, HG19_path, sample_name, read1, read2, output_folder):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    sample_alignment_paths = {}

    # Check if genome is already indexed by bwa
    index_files_extensions = ['.pac', '.amb', '.ann', '.bwt', '.sa']

    genome_indexed = True
    for extension in index_files_extensions:
        if not os.path.isfile(HG19_path + extension):
            genome_indexed = False
            break

    # If the genome is not already indexed, index it
    if not genome_indexed:
        logging.info('Genome index files not detected. Running BWA to generate indices.')
        bwa_index_command = '{0} index {1}'.format(BWA_path, HG19_path)
        logging.info('Running bwa command: %s', bwa_index_command)
        subprocess.call(bwa_index_command.split())
        logging.info('BWA genome index generated')
    else:
        logging.info('BWA genome index found.')

    # Run paired end alignment against the genome
    logging.info('Running paired end mapping for {0} sample'.format(sample_name))
    bwa_alignment_command = '{0} mem {1} {2} {3}'.format(BWA_path,
                                                         HG19_path,
                                                         read1,
                                                         read2)

    logging.info(bwa_alignment_command)

    # Open the outfile and redirect the output of the alignment to it.
    outfile_path = os.path.join(output_folder, sample_name + '.sam')

    with open(outfile_path, 'w') as outfile:
        subprocess.call(bwa_alignment_command.split(), stdout=outfile)

    logging.info('Paired end mapping for {0} sample completed.'.format(sample_name))

    return outfile_path
