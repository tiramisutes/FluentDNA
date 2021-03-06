from __future__ import print_function, division, absolute_import, \
    with_statement, generators, nested_scopes
from bisect import bisect_left
import os
from DNASkittleUtils.Contigs import write_complete_fasta
from DDV import gap_char
from DDV.ChainParser import ChainParser, Batch
from DDV.Span import Span
from DDV.ChainFiles import fetch_all_chains


class UniqueOnlyChainParser(ChainParser):
    def __init__(self, *args, **kwargs):
        kwargs['second_source'] = ''  # the query sequence is not actually used anywhere
        super(UniqueOnlyChainParser, self).__init__(*args, **kwargs)
        self.uncovered_areas = []  # Absolute coordinates.  highly mutable: better as a blist


    def find_zero_coverage_areas(self, ref_chr, combining_genomes=False):
        """Start with whole chromosome, subtract coverage from there"""
        if not combining_genomes:
            self.uncovered_areas = [Span(0, len(self.ref_sequence))]  # TODO: zero indexed?
        all_chains = fetch_all_chains(ref_chr, None, None, self.chain_list)
        for chain in all_chains:  # no special treatment needed for reverse complements since we're only on reference genome
            ref_pointer = chain.tStart  # where we are in the reference
            first, second = None, None
            for entry in chain.entries:
                # Find the start region that's right before <= the end of entry
                new_removal = Span(ref_pointer, ref_pointer + entry.size)
                ref_pointer += entry.size + entry.gap_query
                scrutiny_index = max(bisect_left(self.uncovered_areas, new_removal.begin) - 1, 0)  # Binary search
                if new_removal.begin > self.uncovered_areas[scrutiny_index].end:
                    scrutiny_index += 1  # we missed this one, try the next
                if scrutiny_index >= len(self.uncovered_areas) or new_removal.end < self.uncovered_areas[scrutiny_index].begin:
                    continue  # this lands entirely between entries and shouldn't be processed
                old = self.uncovered_areas.pop(scrutiny_index)
                try:
                    first, second = old.remove_from_range(new_removal)
                except IndexError as e:
                    print([str(x) for x in [self.uncovered_areas[scrutiny_index], new_removal, self.uncovered_areas[scrutiny_index + 1]]])
                    # raise e

                while second is None:  # eating the tail, this could be multiple ranges before the end is satisfied
                    if first is not None:  # leaving behind a beginning, advance scrutiny_index by 1
                        self.uncovered_areas.insert(scrutiny_index, first)
                        # insert first, but the next thing to be checked is whether it affects the next area as well
                        scrutiny_index += 1
                        if scrutiny_index >= len(self.uncovered_areas):
                            first, second = None, None  # don't do anything: done processing this removal
                            break
                    else:
                        pass  # if both are None, then we've just deleted the uncovered entry
                    # check again on the next one
                    if new_removal.end > self.uncovered_areas[scrutiny_index].begin:
                        try:
                            first, second = self.uncovered_areas.pop(scrutiny_index).remove_from_range(new_removal)
                        except IndexError as e:
                            print([str(x) for x in [self.uncovered_areas[scrutiny_index], new_removal, self.uncovered_areas[scrutiny_index + 1]]])
                    else:
                        first, second = None, None  # don't do anything: done processing this removal
                        break

                if first is None and second is not None:
                    self.uncovered_areas.insert(scrutiny_index, second)
                elif None not in [first, second]:  # neither are None
                    self.uncovered_areas.insert(scrutiny_index, first)
                    self.uncovered_areas.insert(scrutiny_index + 1, second)  # since chain entries don't overlap themselves, we're always mutating the next entry



    def write_zero_coverage_areas(self, ref_name, ref_chr):
        uniq_collection = []  # of strings
        ref_unique_name = os.path.join(self.output_folder, os.path.splitext(ref_name)[0] + '_unique.fa')
        for region in self.uncovered_areas:
            unique_region = self.ref_sequence[region.begin: region.end].replace('N', '')
            if len(unique_region):
                uniq_collection.append(unique_region + gap_char)
        write_complete_fasta(ref_unique_name, uniq_collection)
        print("Wrote", ref_unique_name)
        return ref_unique_name


    def main(self, chromosome_name):# -> Batch:
        fasta_names, ref_chr = self.setup_for_reference_chromosome(chromosome_name)
        output_file = os.path.join(self.output_folder, os.path.splitext(fasta_names['ref'])[0] + '_unique.fa')
        if not os.path.exists(output_file):
            self.find_zero_coverage_areas(ref_chr)  # actual work

            #Now compound it with a second alignment  # --second_chain=data/Hg38ToGorGor5.over.chain
            # fasta_names, ref_chr = self.setup_for_reference_chromosome(chromosome_name)
            # self.chain_list = chain_file_to_list('data/Hg38ToGorGor5.over.chain')
            # self.find_zero_coverage_areas(ref_chr,
            #                          combining_genomes=True)  # self.uncovered_areas is preserved from previous

            fasta_names['ref_unique'] = self.write_zero_coverage_areas(fasta_names['ref'], ref_chr)

        if True:  #self.trial_run:  # these files are never used in the viz
            del fasta_names['ref']
            del fasta_names['query']
        # self.move_fasta_source_to_destination(fasta_names, folder_name, source_path)
        return Batch(chromosome_name, [fasta_names['ref_unique']], self.output_folder)  # the name of the one file to be processed by Viz


    def parse_chain(self, chromosomes=None):
        if chromosomes is None:
            chromosomes = 'chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY'.split()

        batches = []
        for chromosome in chromosomes:
            args = self.do_chromosome(chromosome)
            if args is not None:  # could be None if there was an error
                batches.append(args)
        return batches
        # import multiprocessing
        # workers = multiprocessing.Pool(6)  # number of simultaneous processes.  Watch your RAM usage
        # workers.map(self.do_chromosome, chromosomes)
        # return ..


    def do_chromosome(self, chromosome):
        try:
            return self.main(chromosome)
        except BaseException as e:
            import traceback
            traceback.print_exc()
            print("Continuing to next task...")
            return None  # Error return value

