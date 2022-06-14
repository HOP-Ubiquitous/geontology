import os
#from pythonping import ping
import argparse
import csv

OUTCSV = "all_pings.csv"
CSV_DELIMITER = '|'
PING_FILE = "pinginfo.txt"
FILE_HEADERS = ["FILE PATH"]
SOURCE_HEADERS = ["FROM COUNTRY", "FROM CITY", "FROM IP", "FROM LAT", "FROM LON"]
TARGET_HEADERS = ["TO COUNTRY", "TO CITY", "TO IP", "TO LAT", "TO LON"]
DISTANCE_HEADERS = ["DISTANCE (KM)"]
RTT_HEADERS = ["MIN RTT", "AVG RTT", "MAX RTT", "MDEV"]
PING_COUNT = 100

NEW_LINE = ["\n","\r","\r\n","\n\r"]


def getParser():
    parser = argparse.ArgumentParser(description='Vuelca todos los datos relevantes de los pings de cada máquina en un solo fichero')
    parser.add_argument('-dir', metavar='--rootDirectory', type=str, required = False, default = ".",
                    help='El directorio desde el que buscar ficheros {} (por defecto, el actual)'.format(PING_FILE))
    parser.add_argument('-p', metavar='--pingCount', type=int, required = False, default = PING_COUNT,
                    help='El número de pings por máquina a parsear (por defecto, {})'.format(PING_COUNT))
    return parser


def initializeCSVFile(npings):
    out = open(OUTCSV, "w+",newline='',encoding='utf8')
    csvwriter = csv.writer(out, delimiter=CSV_DELIMITER)
    csvwriter.writerow(FILE_HEADERS + SOURCE_HEADERS +  TARGET_HEADERS + DISTANCE_HEADERS + ["PING "+str(i) for i in range(1,npings+1)] + ["HOPS "+str(i) for i in range(1,npings+1)] + RTT_HEADERS)
    return out, csvwriter

def dumpExtraInfo(info,out):
    out.write(info)

def getPingData(filepath, npings):
    fping = open(filepath,"rt",encoding="utf8")
    flines = list(filter(lambda line: line not in NEW_LINE, fping.readlines())) # lineas de un fichero pinginfo.txt (es el output de una llamada a ping)
    
    #Si el fichero esta vacio, no lo parseamos
    if len(flines) == 0:
        return []
    
    # plines son las lineas que contienen exclusivamente la info de cada ping, entre ellos el time
    # por ejemplo, una linea tiene el formato "X bytes from IP: icmp_seq=Y ttl=Z time=K ms\n"
    plines = [l for l in flines if "time=" in l]
    
    # line.strip() es una linea de plines sin "\n", "64 bytes from 2.139.202.9: icmp_seq=2 ttl=44 time=112 ms"
    # line.strip().split("=") = ["64 bytes from 2.139.202.9: icmp_seq", "2 ttl", "44 time", "112 ms"], nos interesa el 4o elemento (indice 3)
    # con .split(" ")[0] eliminamos la magnitud "ms"
    pings = [line.strip().split("=")[3].split(" ")[0].replace(".",",") for line in plines]
    hops = [line.strip().split("=")[2].split(" ")[0] for line in plines]
    
    size = len(pings)
    #Si la lista de pings, que contiene los retardos, esta vacio, no merece la pena considerar este fichero
    if size == 0:
        return []
    if (npings > size):
        pings += [-1] * (npings - size)
        hops += [-1] * (npings - size)

    headers = [line.split(":")[1].strip() for line in flines[-(len(SOURCE_HEADERS)*2+len(DISTANCE_HEADERS)):]] #Las cabeceras de la fuente y el objetivo son las N*2+1 ultimas lineas 
            
    # estadísticas
    # "rtt min/avg/max/mdev = 110.673/111.807/113.664/0.438 ms"
    # nos quedamos con las medidas y elimnamos el "ms"
    measures = list(filter(lambda x: x.startswith("rtt min/avg/max/mdev = "), flines))

    #Si no hay measures, significa que no se ha realizado ningun ping con exito, por lo que la lista pings estaria vacia y este if nunca se ejecutaria, lo dejo por si acaso
    if measures == []:
        stats = [-1,-1,-1]
    else:
        stats = [measure.replace(".",",") for measure in measures[0].split("=")[1].split("/")]
        stats[3] = stats[3].split(" ")[0]

    # Los puntos decimales han sido separados por una coma dado que habia algunos decimales que se convertian a entero
    # algunos ultimos caracteres se eliminan para evitar el retorno de carro
    # return [emissorLoc, emissorIP, targetLoc, targetIP, ping1, ping2, ..., pingN, min rtt, avg rtt, max rtt, status]
    return headers + pings + hops + stats


parser = getParser()
args = parser.parse_args()
out, csvwriter = initializeCSVFile(args.p)
print("\nPARSED FILES:\n")
# r=root, d=directories, f = files
for r, d, f in os.walk(args.dir):
    for file in f:
        if file.endswith(PING_FILE):
            filepath = os.path.join(r, file)
            pdata = getPingData(filepath, args.p)
            if pdata:
                csvwriter.writerow([filepath] + pdata)
                
                print("   " + filepath + " " + u'\u2705')
            else:
                print("   " + filepath + " " + u'\N{cross mark}')

out.close()