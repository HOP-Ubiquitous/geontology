import sys
import pandas as pd
import argparse
import csv


IN_PATH = "./all_pings.csv"
OUT_PATH = "./all_pings_formatted.csv"
CSV_SEP = "|"


HEADERS = ['COUNTRY', 'CITY', 'MONITOR TO BOTS', 'MONITOR TO TARGET', 'CLIENT TO BOTS', 'LABEL']
PINGS_COUNT = 100

def getArgsParser():
    parser = argparse.ArgumentParser(description='Formats the csv input ping file into the format the AI model requires.')
    parser.add_argument('-fin', metavar='--inputCSVFile', type=str, required = False, default = IN_PATH,
                        help='Path to the CSV input file containing all the pings (by default, {})'.format(IN_PATH))
    parser.add_argument('-s', metavar='--CSVSeparator', type=str, required = False, default = CSV_SEP,
                        help='CSV separator (by default, {})'.format(CSV_SEP))
    parser.add_argument('-fout', metavar='--outputCSVFile', type=str, required = False, default = OUT_PATH,
                        help='Path to the CSV output file containing the formatted data (by default, {})'.format(OUT_PATH))
    

    return parser


def initializeCSVFile(out_path,sep):
    out = open(out_path, "w+",newline='')
    csvwriter = csv.writer(out, delimiter=sep)
    csvwriter.writerow(HEADERS)
    return out, csvwriter

def getDF(in_path,sep):
    df = pd.read_csv(in_path,sep=sep, encoding = "unicode_escape")

    # Next columns contain values in a non-decimal type string (',' instead of '.')
    seq = ['PING ' + str(i) for i in range(1,PINGS_COUNT+1)] + ['MIN RTT', 'AVG RTT', 'MAX RTT', 'MDEV'] 
    df[seq] = df[seq].replace(',', '.',regex = True).astype("float")

    df = df[df['TO CITY'] != 'Brentwood']

args = getArgsParser().args
sep = args.s
in_path = args.fin
out_path = args.fout

fout,csvwriter = initializeCSVFile(out_path,sep)
df = getDF(in_path,sep)