from geopy.geocoders import Nominatim
from geopy.distance  import great_circle
import argparse

parser = argparse.ArgumentParser(description='Checks if a given city\'s name can be resolved into coordinates using geopy')
parser.add_argument('-c', metavar='--cityName', type=str, required = True, help='City\'s name')
args = parser.parse_args()

geolocator = Nominatim(user_agent="http")
loc = geolocator.geocode(args.c, language="en")
dist = great_circle((loc.latitude,loc.longitude),(37.9923795,-1.1305431)).km

print("country = {}, lat = {}, long = {}, distance = {} km".format(loc.address.split(",")[-1].strip(),loc.latitude, loc.longitude,dist))
