import os
import argparse 
import json
from tabnanny import check
from geopy.distance  import great_circle
from requests        import get
from geopy.geocoders import Nominatim

JSON_MIN_RTT = "min rtt"
JSON_AVG_RTT = "avg rtt"
JSON_MAX_RTT = "max rtt"
JSON_MDEV_RTT = "mdev"
JSON_STATUS = "status"
JSON_INFO = "info"

OUTPUT_DIRS = ["./GEOINFO", "./PINGS"]
GEOINFO_DIR = 0
PINGS_DIR = 1

PING_FILE = "pinginfo.txt"
GEOFILE = "geotriplets.txt"

PING_COUNT = 100

TARGET_HEADERS = ["TO COUNTRY", "TO CITY", "COMPLETE TO", "TO IP", "TO LAT", "TO LON"]
DISTANCE_HEADER = "DISTANCE (KM)"
SOURCE_HEADERS = ["FROM COUNTRY", "FROM CITY", "COMPLETE FROM", "FROM IP", "FROM LAT", "FROM LON"]
H_COUNTRY = 0
H_CITY = 1
H_COMPLETE_LOC = 2
H_IP = 3
H_LATITUDE = 4
H_LONGITUDE = 5

def checkDirs():
    print("========== CHECKING NECESSARY DIRECTORIES ==========")
    for dir in OUTPUT_DIRS:
        if not os.path.exists(dir):
            os.makedirs(dir)
            print("{} directory created".format(dir))
    print("============ ALL DIRECTORIES ARE READY =============")

def getArgParser():
    parser = argparse.ArgumentParser(description='Realiza una cantidad especificada de pings hacia múltiples destinos')
    parser.add_argument('-c', metavar='--ping_count', type=int, required = False, default = PING_COUNT,
                        help='Número de pings a ejecutar (por defecto, {})'.format(PING_COUNT))
    parser.add_argument('-fin', metavar='--inputFile', type=str, required = False, default = GEOFILE,
                        help='Fichero de entrada con las tripletas Ciudad-IP-Usuario_Remoto (por defecto, {})'.format(GEOFILE))

    return parser


def getHeaderValue(headers, idx):
    return headers[idx].split(":")[1].strip()


def getHeaders(file,targetFile=False):
    input1 = open(file,"rt",encoding="utf8",errors="ignore")
    lines = [line.strip() for line in list(filter(lambda line: line != "\n", input1.readlines()))]
    input1.close()

    headers_len = len(TARGET_HEADERS)
    headers = [h+":"+v for (h,v) in zip(SOURCE_HEADERS if not targetFile else TARGET_HEADERS, lines[0:headers_len])]

    return headers



def getDistance(sourcePoint, targetPoint):
    (sLat, sLon) = sourcePoint
    (tLat, tLon) = targetPoint

    return great_circle((sLat,sLon),(tLat,tLon)).km


def getSourceFile(files):
    ip = get('https://api.ipify.org').text
    for file in files:
        if ip == list(filter(lambda x: x != "\n" and x != "\r" and x != "\r\n", open(file,"rt",encoding="utf8",errors="ignore").readlines()))[3].strip():
            return file

def dumpGeoData(geotriplets):
    files = []
    geolocator = Nominatim(user_agent="http")
    print("\n========== PARSING GEO DATA ==========")

    for (city,ip,_) in geotriplets:
        fname = os.path.join(OUTPUT_DIRS[GEOINFO_DIR], "geo"+city+".txt")
        geofile = open(fname,"w+")
        
        loc = geolocator.geocode(city, language="en")
        data = [loc.address.split(",")[-1].strip(), city, loc, ip, loc.latitude, loc.longitude]
        geofile.write("\n".join(map(str,data)))
        
        print("{} file was provided with {} geo data".format(fname, city))
        geofile.close()

        files.append(fname)

    print("========= PARSING TERMINATED =========")

    return files
        

parser = getArgParser()
args = parser.parse_args()
checkDirs()
geofin = open(GEOFILE,"rt")

# lista de tripletas (ciudad,ip,nombreMaquina)
geotriplets = [tuple(pair.strip().split("-")) for pair in list(filter(lambda x: x != "\n" and x != "\r" and x != "\r\n",geofin.readlines()[1:]))]
geofin.close()
files = dumpGeoData(geotriplets) # vuelca la geoinformacion de cada tripleta en su correspondiente fichero de tipo geo[ciudad].txt

source = getSourceFile(files)
source_h = getHeaders(source)

for target in files:

    baseSource = os.path.basename(source)
    baseTarget = os.path.basename(target)
    if baseSource == baseTarget or not (baseTarget.startswith("geo") and baseTarget.endswith(".txt")):
        continue

    print("File: "+ target)

    target_h = getHeaders(target,True)

    dist = getDistance((getHeaderValue(source_h, H_LATITUDE), getHeaderValue(source_h, H_LONGITUDE)), 
                    (getHeaderValue(target_h, H_LATITUDE), getHeaderValue(target_h, H_LONGITUDE)))


    outname = OUTPUT_DIRS[PINGS_DIR]+"/"+getHeaderValue(source_h,H_CITY).replace(" ","")+"-"+getHeaderValue(target_h,H_CITY).replace(" ","")+"-"+PING_FILE     
    out = open(outname,"w+")
    out.write("\n".join(map(str,source_h)))
    out.write("\n")
    out.write("\n".join(map(str,target_h)))
    out.write("\n{}:{}\n".format(DISTANCE_HEADER,dist))

    toIP = getHeaderValue(target_h,H_IP)

    minSize = len(out.readlines())+4  #4 es el minimo numero de lineas que genera como output un ping

    print("PINGING FROM {} TO {}...".format(getHeaderValue(source_h,H_CITY), getHeaderValue(target_h,H_CITY)))
    print("Outputting in {}...".format(outname))
    pingCMD = "ping -{} {} {} >> {}".format("n" if os.name == "nt" else "c", args.c, toIP, outname)
    print("Command: " + pingCMD)
    response = os.system(pingCMD)

    if (response == 1):

        data_set = {JSON_STATUS: "failure", JSON_INFO: "FAILURE --> Ping returned error code"}

    else:

        flines = list(filter(lambda line: line != "\n", out.readlines()))

        if (len(flines) <= minSize):

            data_set = {JSON_STATUS: "failure", JSON_INFO: "FAILURE --> Couldn't connect to {}".format(toIP)}

        else:

            print("SUCCESSFULL PING")
            if (os.name == "posix"):

                # dat = [min rtt, avg rtt, max rtt, mdev, status]
                dat = flines[-1::][0].split()[3].split("/")
                data_set = {JSON_MIN_RTT: dat[0], JSON_AVG_RTT: dat[1], JSON_MAX_RTT: dat[2], JSON_MDEV_RTT: dat[3], JSON_STATUS: "success"} 

            else:

                # dat = [min rtt, avg rtt, max rtt, status]
                dat = [token.split("=")[1] for token in flines[-1::][0].split(",")]
                data_set = {JSON_MIN_RTT: dat[0], JSON_AVG_RTT: dat[2], JSON_MAX_RTT: dat[1], JSON_STATUS: "success"}       


    #json_dump = json.dump(data_set, open(JSON_FILE,"w"))
    print(json.dumps(data_set))
    print("\n")
    out.close()
