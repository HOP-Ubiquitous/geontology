from geopy.geocoders import Nominatim
#from requests import get
import argparse
import os


DIRPATHS = ["./GEOSELF", "./GEOPAIRS"]
GEOSELF = 0
GEOPAIRS = 1
GEOFILE = "geopairs.txt"


def checkDirs():
    print("========== CHECKING NECESSARY DIRECTORIES ==========")
    size = len(DIRPATHS)
    for i in range(size):
        if not os.path.exists(DIRPATHS[i]):
            os.makedirs(DIRPATHS[i])
            print("{} directory created".format(DIRPATHS[i]))
    print("============ ALL DIRECTORIES ARE READY =============")

def getArgsParser():
    parser = argparse.ArgumentParser(description='Obtiene información sobre la geolocalización de cada par ciudad-IP presente en el fichero de entrada')
    parser.add_argument('-fin', metavar='--geoFile', type=str, required = False, default = "geopairs.txt",
                        help='Path al fichero de entrada con los pares ciudad-ip (por defecto, {})'.format(GEOFILE))

    return parser


def dumpGeoSelfData(geotriplets):
    geolocator = Nominatim(user_agent="http")
    print("\n========== PARSING GEO DATA ==========")
    geoselves = []

    for (city,ip,_) in geotriplets:
        fname = DIRPATHS[GEOSELF]+"/geo"+city+".txt".strip()
        geofile = open(fname,"w+")
        
        loc = geolocator.geocode(city, language="en")
        data = [loc.address.split(",")[-1].strip(), city, loc, ip, loc.latitude, loc.longitude]
        geofile.write("\n".join(map(str,data)))
        
        print("{} file was provided with {} geo data".format(fname, city))
        geofile.close()

        geoselves.append(fname)

    print("========= PARSING TERMINATED =========")

    return geoselves


""" def parseGeoPairsData(geoselves):
    size = len(geoselves)
    pairs = []
    for i in range(size):
        pairs.append([(geoselves[i], f) for f in geoselves if geoselves[i] is not f])

    print(pairs) """


#ip = get('https://api.ipify.org').text
checkDirs()
args = getArgsParser().parse_args()
geofin = open(args.fin,"rt")

# lista de tuplas (ciudad,ip)
geopairs = [tuple(pair.strip().split("-")) for pair in list(filter(lambda x: x != "\n" and x != "\r" and x != "\r\n",geofin.readlines()[1:]))]
geofin.close()
geoselves = dumpGeoSelfData(geopairs) # vuelva la geoinformacion de cada tripleta en su correspondiente fichero de tipo geo[ciudad].txt
""" parseGeoPairsData(geoselves) """