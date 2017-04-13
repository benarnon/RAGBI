from multiprocessing import Pool
import time
import os
import sys
import argparse
import shutil
import ParseGbk
import blast_script
import blast_parse
import computeBicliques
import high_throughput_tests
import json
import logging
import random
import csv

__author__ = 'Arnon Benshahar'


def parser_code():
    parser = argparse.ArgumentParser(
        description='The purpose of this script is to run the full software suite that we have developed to study gene clusters.')

    parser.add_argument("-q", "--qfolder", dest="qfolder", metavar="DIRECTORY", default='./data/testing/iv/',
                        help="Folder containing the fasta and Island Viewer format files of the centroid query.")

    parser.add_argument("-g", "--dbfolder", dest="dbfolder", metavar="DIRECTORY", default='./data/res/genomes/',
                        help="Folder containing all genbank files for use by the program.")

    parser.add_argument("-o", "--outfolder", dest="outfolder", metavar="DIRECTORY", default='./OUT' + str(int(random.random()*100)) + '/',
                        help="Folder where the results of a run will be stored.")

    parser.add_argument("-d", "--window", dest="window_size", metavar="INT", default=15,
                        help="Size of the window")

    parser.add_argument("-n", "--num_proc", dest="num_proc", metavar="INT", default=os.sysconf("SC_NPROCESSORS_CONF"),
                        type=int,
                        help="Number of processors that you want this script to run on. The default is every CPU that the system has.")

    parser.add_argument("-iv", "--island_viewer_format", dest="island_viewer_format", metavar="STRING", default='T',
                        help="IslandViewer queries format, T for islandviewer format and F for normal gbk file.")

    parser.add_argument("-min_genomes", "--min_genomes_per_block", dest="min_genomes_per_block", metavar="INT",
                        default=5,
                        help="Minimum genome in a gene-block.")

    parser.add_argument("-min_genes", "--min_genes_per_interval", dest="min_genes_per_interval", metavar="INT",
                        default=5,
                        help="Minimum genes in a gene interval.")

    parser.add_argument("-rank", "--min_rank", dest="min_rank", metavar="INT", default=20,
                        help="Minimum ranking score that will be report")

    parser.add_argument("-parse", "--parse_input", dest="parse_input", metavar="STRING", default='T',
                        help="Parse the input files")

    parser.add_argument("-e", "--e-val", dest="e-value", metavar="FLOAT", default='0.01',
                        help="eval for the BLAST search.")
    return parser.parse_args()


def check_options(parsed_args):
    if os.path.isdir(parsed_args.dbfolder):
        dbfolder = parsed_args.dbfolder
    else:
        logging.info( "The folder %s does not exist." % parsed_args.dbfolder)
        sys.exit()

    if os.path.isdir(parsed_args.qfolder):
        qfolder = parsed_args.qfolder
    else:
        logging.info( "The folder %s does not exist." % parsed_args.qfolder)
        sys.exit()

    # if the directory that the user specifies does not exist, then the program makes it for them.
    if not os.path.isdir(parsed_args.outfolder):
        os.makedirs(parsed_args.outfolder)
    if parsed_args.outfolder[-1] != '/':
        outfolder = parsed_args.outfolder + '/'
    else:
        outfolder = parsed_args.outfolder

    # section of code that deals determining the number of CPU cores that will be used by the program
    if parsed_args.num_proc > os.sysconf("SC_NPROCESSORS_CONF"):
        num_proc = os.sysconf("SC_NPROCESSORS_CONF")
    elif parsed_args.num_proc < 1:
        num_proc = 1
    else:
        num_proc = int(parsed_args.num_proc)

    # validate the input for the window size
    try:
        window_size = int(parsed_args.window_size)
        if window_size <= 0:
            logging.info( "The window that you entered %s is a negative number, please enter a positive integer." % parsed_args.max_gap)
            sys.exit()
        else:
            pass
    except:
        logging.info( "The window that you entered %s is not an integer, please enter a positive integer." % parsed_args.max_gap)
        sys.exit()

    # validate the query input format (isalndviewer or gbk)
    if parsed_args.island_viewer_format == 'F' or parsed_args.island_viewer_format == 'T':
        island_viewer_format = (parsed_args.island_viewer_format == 'T')
    else:
        logging.info( "T for isalndviewer format and F for normal gbk file")
        sys.exit()

    # validate the input for the min_genomes_per_block
    try:
        min_genomes_per_block = int(parsed_args.min_genomes_per_block)
        if min_genomes_per_block <= 1:
            logging.info( "The min genomes per block that you entered %s is less than 2, please enter a positive integer greater than 2." % parsed_args.max_gap)
            sys.exit()
        else:
            pass
    except:
        logging.info( "The min genomes per block you entered %s is not an integer, please enter a positive integer." % parsed_args.max_gap)
        sys.exit()

    # validate the input for the min_genomes_per_block
    try:
        min_genes_per_interval = int(parsed_args.min_genes_per_interval)
        if min_genes_per_interval <= 1:
            logging.info( "The min_genes_per_interval you entered %s is less than 2, please enter a positive integer greater than 2." % parsed_args.min_genes_per_interval)
            sys.exit()
        else:
            pass
    except:
        logging.info( "The min genomes per block you entered %s is not an integer, please enter a positive integer." % parsed_args.min_genes_per_interval)
        sys.exit()

    # validate the input for the min_genomes_per_block
    try:
        min_rank = int(parsed_args.min_rank)
        if min_rank <= 0:
            logging.info( "The min rank you entered %s is not an integer, please enter a positive integer." % parsed_args.min_rank)
            sys.exit()
        else:
            pass
    except:
        logging.info( "The min rank you entered %s is not an integer, please enter a positive integer." % parsed_args.min_rank)
        sys.exit()

    # validate the query input format (isalndviewer or gbk)
    if parsed_args.parse_input == 'F' or parsed_args.parse_input == 'T':
        parse_input = (parsed_args.parse_input == 'T')
    else:
        logging.info( "T for isalndviewer format and F for normal gbk file")
        sys.exit()

    e_val = parsed_args.eval

    return dbfolder, qfolder, outfolder, num_proc, window_size, island_viewer_format, min_genes_per_interval, min_genomes_per_block, parse_input, min_rank, e_val


def parse_cmd():
    return "./res/High-Throughput-Plamids/", "./res/genomes/", "1e-50"
    # return "./res/High-Throughput-Plamids/", "./res/genomes/", "1e-50"


def biclustering(tuple_list):
    logging.info( 'Start Biclustering')
    logging.info( str(tuple_list))
    query_file, refernce_folder, ref_fasta, query_fasta, blast_results, blast_parse_dir, query_gene_list_dir, bicluster_results, max_genome_size, min_genes_per_interval, min_genomes_per_block,window_size, e_val, min_rank = tuple_list

    logging.info( "Stage 3 parse blast results")
    list_file_name = query_gene_list_dir + query_file.split("/")[-1].split(".")[0] + ".txt"
    blast_parse.parse_blast(blast_results, blast_parse_dir, "", 10, list_file_name, query_file)

    logging.info( "Stage 4 biclustering")
    return computeBicliques.compute_bicluster(list_file_name, blast_parse_dir, bicluster_results, refernce_folder, max_genome_size, min_genes_per_interval, min_genomes_per_block,window_size, e_val, min_rank)


def parallel_high_throughput_test(tuple_list_array):
    num_proc = 1
    pool = Pool(processes=num_proc)
    pool.map(high_throughput_tests.compute_bicluster, tuple_list_array)


def main():
    start = time.time()
    logging.basicConfig(filename="./info.log",format='%(asctime)s %(message)s', level=logging.DEBUG)
    logging.info( "Start RAGBI program")
    # Parse all the user's arguments
    parsed_args = parser_code()
    db_folder, q_folder, outfolder, num_proc, window_size, island_viewer_format, min_genes_per_interval, min_genomes_per_block, parse_input, min_rank, e_val = check_options(
        parsed_args)
    logging.info( "args=" + str(check_options(parsed_args)))

    # Only for high_throughput
    high_throughput = False

    # This json will contain all the information about this run.
    stats_json = {'query_list': []}

    tmp_dir = './TMP'
    ref_fasta_dir = tmp_dir + '/ffc/ref/'
    query_fasta_dir = tmp_dir + '/ffc/qry/'

    if parse_input:
        if os.path.exists(outfolder):
            shutil.rmtree(outfolder)
        logging.info("Create output folder, " + outfolder )
        os.makedirs(outfolder)

        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        logging.info("Create tmp folder, " + tmp_dir)
        os.makedirs(tmp_dir)

        if os.path.exists(ref_fasta_dir):
            shutil.rmtree(ref_fasta_dir)
        logging.info("Create ref fasta folder, " + ref_fasta_dir)
        os.makedirs(ref_fasta_dir)

        if os.path.exists(query_fasta_dir):
            shutil.rmtree(query_fasta_dir)
        logging.info("Create query fasta folder, " + query_fasta_dir)
        os.makedirs(query_fasta_dir)

        '''
        Stage 1: Convert the gbk files of the query and the reference to ffc format.
        In case the query is in normal gbk format (one file, one island) we convert the gbk file into one ffc file which contains the island.
        In case the query is in Islandviewer format we split each genebank file into multiple ffc files where each file contains one island.
        For more details about the input formats please go to the README.md file.
        '''
        if island_viewer_format:
            logging.info("Parse query in IslandViewer format," + query_fasta_dir)
            query_json = ParseGbk.parseIslandViewer(q_folder, query_fasta_dir)
        else:
            logging.info("Parse query in noraml format," + query_fasta_dir)
            query_json = ParseGbk.parse(q_folder, query_fasta_dir, "NONE", True, False)
        logging.info("Parse target genomes," + ref_fasta_dir)

        with open(outfolder + 'queries.json', 'w') as outfile1:
            json.dump(query_json, outfile1)

        with open(outfolder + 'queries_csv_file.csv','w') as queries_csv_file:
            queries_csv_writer = csv.writer(queries_csv_file)
            queries_csv_writer.writerow(['Accession Number','Description','Number of islands','Length'])
            queries_csv_writer.writerow([query_json[0]['accession'],query_json[0]['description'],query_json[0]['num_of_islands'],query_json[0]['length']])
            queries_csv_writer.writerow(['Islands'])
            queries_csv_writer.writerow(['Start','End','Length', 'Number of Genes'])
            for query in query_json[0]['islands']:
                queries_csv_writer.writerow([query['start'],query['end'],query['length'],query['num_of_genes']])

        target_json = ParseGbk.parse(db_folder, ref_fasta_dir, "NONE", True, True)

        with open(outfolder + 'targets.json', 'w') as outfile1:
            json.dump(target_json, outfile1)

        with open(outfolder + 'targets_csv_file.csv','w') as queries_csv_file:
            queries_csv_writer = csv.writer(queries_csv_file)
            queries_csv_writer.writerow(['Accession Number','Specie','Description','Length','Number of Genes'])
            for target in target_json:
                queries_csv_writer.writerow([target['accession'],target['organism'],target['description'],target['length'],target['number_of_genes']])

        logging.info( 'Run biclustering' )
        # create the queries file
        blast_results_dir = tmp_dir + '/blast_results/'
        if os.path.exists(blast_results_dir):
            shutil.rmtree(blast_results_dir)
        logging.info("Create blast results folder, " + blast_results_dir)
        os.makedirs(blast_results_dir)

        blast_parse_dir = tmp_dir + '/blast_parse/'
        if os.path.exists(blast_parse_dir):
            shutil.rmtree(blast_parse_dir)
        logging.info("Create blast parse folder, " + blast_parse_dir)
        os.makedirs(blast_parse_dir)

        query_gene_list_dir = tmp_dir + '/query_gene_list_dir/'
        if os.path.exists(query_gene_list_dir):
            shutil.rmtree(query_gene_list_dir)
        logging.info("Create query gene list folder, " + query_gene_list_dir)
        os.makedirs(query_gene_list_dir)

        query_fasta_list = []
        logging.info( 'Create blast parse folders' )
        for content in os.listdir(query_fasta_dir):  # "." means current directory
            if content.split(".")[-1] == "ffc":
                query_fasta_list.append(query_fasta_dir + content)
                if not os.path.exists(blast_results_dir + "" + content.split(".")[-2]):
                    os.makedirs(blast_results_dir + "" + content.split(".")[-2])
                if not os.path.exists(blast_parse_dir + "" + content.split(".")[-2]):
                    os.makedirs(blast_parse_dir + "" + content.split(".")[-2])

        logging.info( 'Create targets.json file' )
        with open(outfolder + 'targets.json') as data_file:
            targets_json = json.load(data_file)

        s = 0
        for target in targets_json:
            s += target['number_of_genes']
        genome_size = s / len(targets_json)

        logging.info( "Avg genome size " + str(genome_size) )

        general_stats = []
        file_num = 1
        tuple_list_array = []
        for file in query_fasta_list:
            logging.info( 'File Number ' + str(file_num) )
            file_num += 1

            # Stage 2: run blastall with the query fasta vs the ref fastas
            query_file_name = file.split("/")[-1].split(".")[-2]
            blast_output = blast_results_dir + query_file_name + "/"
            blast_script.blast(ref_fasta_dir, blast_output, "", os.sysconf("SC_NPROCESSORS_CONF"), file, e_val)

            blast_results_tmp = blast_results_dir + file.split("/")[-1].split(".")[-2] + "/"
            blast_parse_tmp = blast_parse_dir + file.split("/")[-1].split(".")[-2] + "/"
            bicluster_results_tmp = outfolder + file.split("/")[-1].split(".")[-2] + "/"

            logging.info( str(file) + "," + str(db_folder) + "," + str(ref_fasta_dir) + "," + str(
                query_fasta_dir) + "," + str(blast_results_tmp) + "," + str(blast_parse) + "," + str(
                query_gene_list_dir) + "," + outfolder )
            tuple_list = (file, db_folder, ref_fasta_dir, query_fasta_dir, blast_results_tmp, blast_parse_tmp,
                          query_gene_list_dir, bicluster_results_tmp, genome_size, min_genes_per_interval, min_genomes_per_block, window_size, e_val, min_rank)
            #****#
            file_stats = biclustering(tuple_list)
            #****#

            if not high_throughput:
                file_stats['accession'] = query_file_name
                with open(outfolder + 'queries.json') as data_file:
                    query_json = json.load(data_file)
                for query in query_json:
                    if query['accession'] == query_file_name:
                        file_stats['length'] = query['length']
                        file_stats['number_of_genes'] = query['number_of_genes']
                if file_stats['num_of_cliques'] > 0:
                    general_stats.append(file_stats)
                    with open(outfolder + 'resultStats.json', 'w') as outfile1:
                        json.dump(general_stats, outfile1)
            else:
                tuple_list_array.append((query_gene_list_dir + file.split("/")[-1].split(".")[0] + ".txt", blast_parse_tmp, './', db_folder))

        with open(outfolder + 'general_results.csv','w') as general_results_csv_file:
            general_results_csv_writer = csv.writer(general_results_csv_file)
            general_results_csv_writer.writerow(['Accession Number- Start of Island - End of Island','Max Ranking Score','Number of Cliques','Number of Blocks','Avg Blocks per Clique','Context Switch'])
            for result in general_stats:
                general_results_csv_writer.writerow([result['accession'],result['max_pval'],result['num_of_cliques'],result['numOfBlocks'],result['avgBlockPerClique'],result['context_switch']])

        for root, dirs, files in os.walk(outfolder):
            for file in files:
                if file.endswith('.json'):
                    os.remove(root + '/' + file)


if __name__ == '__main__':
    main()
