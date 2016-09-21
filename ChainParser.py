import os
from collections import defaultdict
from array import array
import shutil


def chunks(seq, size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def find_contig(chromosome_name, genome_source):
    """Scan through a genome fasta file looking for a matching contig name.  When it find it, find_contig collects
    the sequence and returns it as a string with no cruft."""
    chromosome_name = '>' + chromosome_name
    contig_header = ''
    seq_collection = []
    headers = []
    printing = False
    with open(genome_source, 'r') as genome:
        for line in genome.readlines():
            line = line.rstrip()
            if line.startswith('>'):
                # headers.append(line)
                if line == chromosome_name:
                    printing = True
                    print("Found", line)
                    contig_header = line
                elif printing:
                    break  # we've collected all sequence and reached the beginning of the next contig
            if printing:  # This MUST come after the check for a '>'
                seq_collection.append(line.upper())  # always upper case so equality checks work
    assert len(seq_collection), "Contig not found." + chromosome_name  # File contained these contigs:\n" + '\n'.join(headers)
    return ''.join(seq_collection), contig_header


def match(target, current):
    """Returns true if current satisfies the target requirements"""
    if target is None:
        return True
    return target == current


def fetch_all_chains(ref_chr, ref_strand, query_chr, query_strand, filename):
    """Fetches all chains that match the requirements.
    any of {ref_chr, ref_strand, query_chr, query_strand} can be None which means the match to anything."""
    all_chains = []
    chain = []  # never actually used before assignment
    example_line = ''
    with open(filename, 'r') as infile:
        printing = False
        for line in infile.readlines():
            if line.startswith('chain'):
                label, score, tName, tSize, tStrand, tStart, \
                tEnd, qName, qSize, qStrand, qStart, qEnd, chain_id = line.split()
                example_line = line
                printing = match(ref_chr, tName) and match(query_chr, qName) and match(ref_strand, tStrand) and match(query_strand, qStrand)
                if printing:
                    print(line, end='')
                    chain = [line]  # write header
                    all_chains.append(chain)  # "chain" will continue to be edited inside of "all_chains"
            else:
                pieces = line.split()
                if printing:
                    if len(pieces) == 3 or len(pieces) == 1:
                        chain.append(line)  # "chain" will continue to be edited inside of "all_chains"
    if len(all_chains) == 0:
        raise ValueError("A chain entry for %s and %s could not be found." % (ref_chr, query_chr) +
                         "     Example: %s" % example_line)
    return all_chains


def first_word(string):
    import re
    if '\\' in string:
        string = string[string.rindex('\\') + 1:]
    return re.split('[\W_]+', string)[0]


def rev_comp(plus_strand):
    comp = {'A': 'T', 'G': 'C', 'T': 'A', 'C': 'G', 'N': 'N', 'X': 'X'}
    # rev = array('u')
    # for a in reversed(plus_strand):
    #     rev.extend(comp[a])
    return array('u', ''.join([comp[a] for a in reversed(plus_strand)]))


class ChainParser:
    def __init__(self, chain_name, ref_source, query_source, output_folder_prefix, trial_run=False, swap_columns=False):
        self.width_remaining = defaultdict(lambda: 70)
        self.chain_name = chain_name
        self.ref_source = ref_source
        self.query_source = query_source
        self.output_folder_prefix = output_folder_prefix
        self.trial_run = trial_run
        self.swap_columns = swap_columns
        self.ref_sequence = ''
        self.query_sequence = ''
        self.ref_seq_gapped = array('u', '')
        self.query_seq_gapped = array('u', '')


    def read_seq_to_memory(self, ref_chr, query_chr, query_source, ref_source, query_file_name, ref_file_name):
        self.query_sequence, contig_header = find_contig(query_chr, query_source)
        if not self.trial_run:
            self.write_fasta_lines(query_file_name, self.query_sequence)

        self.ref_sequence, contig_header = find_contig(ref_chr, ref_source)
        if not self.trial_run:
            self.write_fasta_lines(ref_file_name, self.ref_sequence)


    def write_fasta_lines(self, filestream, seq):
        if isinstance(filestream, str):  # I'm actually given a file name and have to open it myself
            file_name = filestream
            with open(file_name, 'w') as filestream:
                self.do_write(filestream, 70, seq)
                print("Wrote", file_name, len(self.query_sequence))
        else:
            remaining = self.width_remaining[filestream]
            self.do_write(filestream, remaining, seq)

    def do_write(self, filestream, remaining, seq):
        try:
            left_over_size = 70
            remainder = seq[:remaining]
            seq = seq[remaining:]
            filestream.write(remainder + '\n')
            for line in chunks(seq, 70):
                if len(line) == 70:
                    filestream.write(line + '\n')
                else:
                    left_over_size = 70 - len(line)
                    filestream.write(line)  # no newline
            self.width_remaining[filestream] = left_over_size
        except Exception as e:
            print(e)

    def mash_fasta_and_chain_together(self, chain_lines, is_master_alignment=False):
        header, chain_lines = chain_lines[0], chain_lines[1:]
        label, score, tName, tSize, tStrand, tStart, tEnd, qName, qSize, qStrand, qStart, qEnd, chain_id = header.split()
        # convert to int except for chr names and strands
        score, tSize, tStart, tEnd, qSize, qStart, qEnd, chain_id = [int(x) for x in (score, tSize, tStart, tEnd, qSize, qStart, qEnd, chain_id)]
        query_pointer, ref_pointer = self.setup_chain_start(header, tStart, tEnd, qStart, qEnd, is_master_alignment)

        if not is_master_alignment:
            self.do_translocation_housework(header, chain_lines, ref_pointer, query_pointer)
        self.process_chain_body(chain_lines, ref_pointer, query_pointer, is_master_alignment, False)  #minus_strand=qStrand == '-')

        return True

    def process_chain_body(self, chain_lines, ref_pointer, query_pointer, is_master_alignment, minus_strand):
        ref_gapped_strand = array('u', '')
        for chain_line in chain_lines:
            pieces = chain_line.split()
            if len(pieces) == 3:
                size, gap_reference, gap_query = [int(x) for x in pieces]
                if self.swap_columns:
                    gap_reference, gap_query = gap_query, gap_reference

                # Debugging code
                if is_master_alignment and self.trial_run and len(self.query_seq_gapped) > 1000000:  # 9500000
                    break

                ref_seq_absolute = self.ref_sequence[ref_pointer: ref_pointer + size + gap_query]
                if minus_strand:
                    ref_seq_absolute = self.ref_sequence[-(ref_pointer + size + gap_query) - 1: -ref_pointer - 1]
                ref_snippet = ref_seq_absolute + 'X' * gap_reference
                ref_pointer += size + gap_query  # alignable and unalignable block concatenated together
                ref_gapped_strand.extend(ref_snippet if not minus_strand else rev_comp(ref_snippet))

                query_snippet = self.query_sequence[query_pointer: query_pointer + size] + 'X' * gap_query
                query_snippet += self.query_sequence[query_pointer + size: query_pointer + size + gap_reference]
                query_pointer += size + gap_reference  # two blocks of sequence separated by gap
                self.query_seq_gapped.extend(query_snippet)

                if len(query_snippet) != len(ref_snippet):
                    print(len(ref_snippet), len(query_snippet), "You should be outputting equal length strings til the end")

            elif len(pieces) == 1:
                # if is_master_alignment:  # last one: print out all remaining sequence
                #     # ref_gapped_strand.extend(self.ref_sequence[ref_pointer:])
                #     # self.query_seq_gapped.extend(self.query_sequence[query_pointer:])
                # else:
                    self.query_seq_gapped.extend(self.query_sequence[query_pointer: query_pointer + int(pieces[0])])
                    if minus_strand:
                        ref_gapped_strand.extend(rev_comp(self.ref_sequence[-(ref_pointer + int(pieces[0])) - 1: -ref_pointer - 1]))
                    else:
                        ref_gapped_strand.extend(self.ref_sequence[ref_pointer: ref_pointer + int(pieces[0])])
        # Now done processing all the lines in this chain
        # if minus_strand:
        #     ref_gapped_strand = rev_comp(ref_gapped_strand)
        self.ref_seq_gapped.extend(ref_gapped_strand)


    def setup_chain_start(self, header, tStart, tEnd, qStart, qEnd, is_master_alignment):
        assert header.startswith('chain')
        query_pointer, ref_pointer = (qStart, tStart) if self.swap_columns else (tStart, qStart)   # this is correct, don't switch these around
        if tEnd - tStart > 100 * 1000:
            print('>>>>', header)
        if is_master_alignment:  # include the unaligned beginning of the sequence
            longer_gap = max(ref_pointer, query_pointer)
            self.ref_seq_gapped.extend(self.ref_sequence[:ref_pointer] + 'X' * (longer_gap - ref_pointer))  # one of these gaps will be 0
            self.query_seq_gapped.extend(self.query_sequence[:query_pointer] + 'X' * (longer_gap - query_pointer))
        return query_pointer, ref_pointer

    def do_translocation_housework(self, header, chain_lines, ref_pointer, query_pointer):
        self.ref_seq_gapped.extend('G' * (500 + (100 - len(self.ref_seq_gapped) % 100)))  # visual separators
        self.query_seq_gapped.extend('G' * (500 + (100 - len(self.query_seq_gapped) % 100)))
        # delete the ungapped query sequence
        # 	delete the query sequence that doesn't match to anything based on the original start, stop, size,
        # 	replace query with X's, redundant gaps will be closed later
        # 		there probably shouldn't be any gap at all between where the gap starts and where it gets filled in by the new chain
        # 	what if that overlaps to reference sequence and not just N's?

        # delete the target reference region
        # 	target reference will be filled in with gapped version of reference (might be slightly longer)
        # 	compensate start position for all previous gaps in the reference
        # 	delete parallel query region (hopefully filled with N's)

        # insert the gapped versions on both sides
        pass

    def write_gapped_fasta(self, ref, query):
        ref_gap_name = os.path.splitext(ref)[0] + '_gapped.fa'
        query_gap_name = os.path.splitext(query)[0] + '_gapped.fa'
        with open(ref_gap_name, 'w') as ref_file:
            self.write_fasta_lines(ref_file, ''.join(self.ref_seq_gapped))
        with open(query_gap_name, 'w') as query_file:
            self.write_fasta_lines(query_file, ''.join(self.query_seq_gapped))
        return ref_gap_name, query_gap_name


    def print_only_unique(self, ref_gapped_name, query_gapped_name):
        ref_uniq_array = array('u', self.ref_seq_gapped)
        que_uniq_array = array('u', self.query_seq_gapped)
        print("Done allocating unique array")
        shortest_sequence = min(len(self.ref_seq_gapped), len(self.query_seq_gapped))
        for i in range(shortest_sequence):
            # only overlapping section
            if self.ref_seq_gapped[i] == self.query_seq_gapped[i]:
                ref_uniq_array[i] = 'X'
                que_uniq_array[i] = 'X'
            else:  # Not equal
                if self.ref_seq_gapped[i] == 'N':
                    ref_uniq_array[i] = 'X'
                if self.query_seq_gapped[i] == 'N':
                    que_uniq_array[i] = 'X'

        # Just to be thorough: prints aligned section (shortest_sequence) plus any dangling end sequence
        ref_unique_name = ref_gapped_name[:-10] + '_unique.fa'
        query_unique_name = query_gapped_name[:-10] + '_unique.fa'
        with open(ref_unique_name, 'w') as ref_filestream:
            self.write_fasta_lines(ref_filestream, ''.join(ref_uniq_array))
        with open(query_unique_name, 'w') as query_filestream:
            self.write_fasta_lines(query_filestream, ''.join(que_uniq_array))

        return ref_unique_name, query_unique_name


    @staticmethod
    def move_fasta_source_to_destination(fasta, folder_name, source_path):
        destination_folder = os.path.join(source_path, folder_name)
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder, ignore_errors=True)  # Make sure we can overwrite the contents
        os.makedirs(destination_folder, exist_ok=False)
        for key in fasta:
            shutil.move(fasta[key], destination_folder)
            fasta[key] = os.path.join(destination_folder, fasta[key])


    def main(self, chromosome_name):
        import DDV

        if isinstance(chromosome_name, str):
            chromosome_name = (chromosome_name, chromosome_name)
        ref_chr, query_chr = chromosome_name


        names = {'query': query_chr + '_%s.fa' % first_word(self.query_source),
                 'ref': ref_chr + '_%s.fa' % first_word(self.ref_source)}  # for collecting all the files names in a modifiable way

        self.read_seq_to_memory(ref_chr, query_chr, self.query_source, self.ref_source, names['query'], names['ref'])
        # Reference chain that establishes coordinate frame
        #self.mash_fasta_and_chain_together(fetch_all_chains(ref_chr, '+', query_chr, '+', filename=self.chain_name)[0], True)

        all_chains = fetch_all_chains(ref_chr, '+', query_chr, '+', filename=self.chain_name)[1:]  # skip the reference chain
        for chain in all_chains:
            self.mash_fasta_and_chain_together(chain, False)
        # all the inversions
        all_chains = fetch_all_chains(ref_chr, '+', query_chr, '-', filename=self.chain_name)
        print("Creating reverse complement")
        self.ref_sequence = ''.join(rev_comp(self.ref_sequence))
        print("Done Creating reverse complement")
        for chain in all_chains:
            self.mash_fasta_and_chain_together(chain, False)

        names['ref_gapped'], names['query_gapped'] = self.write_gapped_fasta(names['ref'], names['query'])
        names['ref_unique'], names['query_unique'] = self.print_only_unique(names['ref_gapped'], names['query_gapped'])
        print("Finished creating gapped fasta files", names['query'], names['ref'])

        folder_name = self.output_folder_prefix + query_chr
        source_path = '.\\bin\\Release\\output\\dnadata\\'
        if self.trial_run:  # these files are never used in the viz
            del names['query']
            del names['ref']
        self.move_fasta_source_to_destination(names, folder_name, source_path)
        DDV.DDV_main(['DDV',
                      names['query_gapped'],
                      source_path,
                      folder_name,
                      names['query_unique'], names['ref_unique'],
                      names['ref_gapped']])


def do_chromosome(chr):
    parser = ChainParser(chain_name='panTro4ToHg38.over.chain',  # 'chr20_sample_no_synteny_panTro4ToHg38.chain',  #
                         query_source='panTro4_chr20.fa',  #  'panTro4.fa',
                         ref_source='hg38_chr20.fa',  # 'HongKong\\hg38.fa',
                         output_folder_prefix='panTro4_and_Hg38_alignment4_',
                         trial_run=True,
                         swap_columns=False)
    # parser = ChainParser(chain_name='HongKong\\human_gorilla.bland.chain',
    #                      query_source='HongKong\\susie3_agp.fasta',
    #                      ref_source='HongKong\\hg38.fa',
    #                      output_folder_prefix='Susie3_and_Hg38_short3_',
    #                      trial_run=True,
    #                      swap_columns=True)
    parser.main(chr)


if __name__ == '__main__':
    chromosomes = [('chr20', 'chr20')]  # 'chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr22 chrX'.split()
    # TODO: handle Chr2A and Chr2B separately
    for chr in chromosomes:
        do_chromosome(chr)

    # import multiprocessing
    # workers = multiprocessing.Pool(6)  # number of simultaneous processes.  Watch your RAM usage
    # workers.map(do_chromosome, chromosomes)

