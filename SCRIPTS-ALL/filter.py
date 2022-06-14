import os
import argparse 
import json
import ipinfo

INFILE = "moreips.txt"
OUTFILE = "geotriplets2.txt"

IPhandler = ipinfo.getHandler('f0218f9cb3d08c')

def getArgParser():
    parser = argparse.ArgumentParser(description='Selects from a IPs set those which answeres to ping requests and dumps in an output file the geoinformation of each one of them.')
    parser.add_argument('-fin', metavar='--inputFile', type=str, required = False, default = INFILE,
                        help='Input file containing the IPs (by default, {})'.format(INFILE))
    parser.add_argument('-out', metavar='--outputFile', type=str, required = False, default = OUTFILE,
                        help='Output file (by default, {})'.format(OUTFILE))
    return parser
        

parser = getArgParser()
args = parser.parse_args()

pingCMD = "fping < {} > temp.txt".format(args.fin)
print("Command: " + pingCMD)
response = os.system(pingCMD)

ftemp =  open("temp.txt","r")
ips = [line.split(" ")[0] for line in ftemp.readlines() if line.strip().endswith("is alive")]
os.remove("temp.txt")
print(ips)

fout = open(args.out,"w+")

for ip in ips:

    try:
        details = IPhandler.getDetails(ip)
        toCity = details.city
        fout.write("{}#{}#ubuntu\n".format(toCity,ip))
    except:
        pass 

fout.close()


