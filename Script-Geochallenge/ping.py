import os
import argparse 
import json
from geopy.distance  import great_circle
from requests        import get
from threading       import Thread, Lock

JSON_MIN_RTT = "min rtt"
JSON_AVG_RTT = "avg rtt"
JSON_MAX_RTT = "max rtt"
JSON_MDEV_RTT = "mdev"
JSON_STATUS = "status"
JSON_INFO = "info"

OUTPUT_DIRS = ["./GEOINFO/", "./PINGS/"]
GEOINFO_DIR = 0
PINGS_DIR = 1

PING_FILE = "pinginfo.txt"
GEOFILE = "geotriplets.txt"

PING_COUNT = 100

TARGET_HEADERS = ["TO COUNTRY", "TO CITY", "TO IP", "TO LAT", "TO LON"]
DISTANCE_HEADER = "DISTANCE (KM)"
SOURCE_HEADERS = ["FROM COUNTRY", "FROM CITY", "FROM IP", "FROM LAT", "FROM LON"]
H_COUNTRY = 0
H_CITY = 1
H_COMPLETE_LOC = 2
H_IP = 3
H_LATITUDE = 4
H_LONGITUDE = 5

LOCK = Lock() 

def getArgParser():
    parser = argparse.ArgumentParser(description='Realiza una cantidad especificada de pings hacia múltiples destinos')
    parser.add_argument('-c', metavar='--ping_count', type=int, required = False, default = PING_COUNT,
                        help='Número de pings a ejecutar (por defecto, {})'.format(PING_COUNT))
    parser.add_argument('-fin', metavar='--inputFile', type=str, required = False, default = GEOFILE,
                        help='Fichero de entrada con las tripletas Ciudad-IP-Usuario_Remoto (por defecto, {})'.format(GEOFILE))
    parser.add_argument('-local', metavar='--countryLevel', type=bool, required = False, default = False,
                        help='Flag para indicar el alcance de los pings: global o a nivel de país (por defecto, se hace pings a todos los destinos)')

    return parser


def getHeaders(data,targetFile=False):
    return [h+":"+v for (h,v) in zip(SOURCE_HEADERS if not targetFile else TARGET_HEADERS, data)]


def ping(source,target,lock = LOCK):
    if target[2] == source[2] or (args.local and target[0] != source[0]):
        return

    target_h = getHeaders(list(target),True)
    source_h = getHeaders(list(source))

    dist = great_circle((source[3],source[4]),(target[3],source[4])).km


    outname = OUTPUT_DIRS[PINGS_DIR]+source[1].replace(" ","")+"-"+source[2]+"-"+target[1].replace(" ","")+"-"+target[2]+"-"+PING_FILE     
    
    out = open(outname,"w+")
    out.write("\n".join(map(str,source_h)))
    out.write("\n")
    out.write("\n".join(map(str,target_h)))
    out.write("\n{}:{}\n".format(DISTANCE_HEADER,dist))

    toIP = target[2]

    minSize = len(out.readlines())+4  #4 es el minimo numero de lineas que genera como output un ping

    print("PINGING FROM {} TO {}...".format(source[1], target[1]))
    print("Outputting in {}...".format(outname))
    pingCMD = "ping -{} {} {} >> {}".format("n" if os.name == "nt" else "c", args.c, toIP, outname)
    print("Command: " + pingCMD)
    response = os.system(pingCMD)
    fail = False

    if (response == 1):
        fail = True
        data_set = {JSON_STATUS: "failure", JSON_INFO: "FAILURE --> Ping returned error code"}

    else:

        flines = list(filter(lambda line: line != "\n", out.readlines()))

        if (len(flines) <= minSize):
            fail = True
            data_set = {JSON_STATUS: "failure", JSON_INFO: "FAILURE --> Couldn't connect to {}".format(toIP)}

        else:

            if (os.name == "posix"):

                # dat = [min rtt, avg rtt, max rtt, mdev, status]
                try:
                    dat = flines[-1::][0].split()[3].split("/")
                    data_set = {JSON_MIN_RTT: dat[0], JSON_AVG_RTT: dat[1], JSON_MAX_RTT: dat[2], JSON_MDEV_RTT: dat[3], JSON_STATUS: "success"} 
                except:
                    print("FAILURE")
                    data_set = {JSON_STATUS: "failure", JSON_INFO: "FAILURE --> Couldn't connect to {}".format(toIP)}

            else:

                # dat = [min rtt, avg rtt, max rtt, status]
                dat = [token.split("=")[1] for token in flines[-1::][0].split(",")]
                data_set = {JSON_MIN_RTT: dat[0], JSON_AVG_RTT: dat[2], JSON_MAX_RTT: dat[1], JSON_STATUS: "success"}       


    #json_dump = json.dump(data_set, open(JSON_FILE,"w"))
    lock.acquire()
    if fail:
        print("FAIL")
    else:
        print("SUCCESSFULL PING")
    print(json.dumps(data_set))
    print("\n")
    LOCK.release()

    lock.close()

parser = getArgParser()
args = parser.parse_args()

if not os.path.exists("./PINGS/"):
    os.makedirs("./PINGS/") 

geofin = open(args.fin,"rt")

# lista de tuplas (pais,ciudad,ip,lat,lon,nombreMaquina)
geotuples = [tuple(pair.strip().split("#")) for pair in list(filter(lambda x: x != "\n" and x != "\r" and x != "\r\n",geofin.readlines()))]
geofin.close()
myIP = get('https://api.ipify.org').text
source = [t for t in geotuples if t[2] == myIP][0]
threads = []

for target in geotuples:
    t = Thread(target=ping, args=(source,target))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
