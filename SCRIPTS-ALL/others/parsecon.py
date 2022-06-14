import argparse

FILE = "connections.txt"
OUT = "geotriplets.txt"

parser = argparse.ArgumentParser(description='Formats connections data to geotriplets.')
parser.add_argument('-fin', metavar='--inputConnectionsFile', type=str, required = False, default = FILE,
                        help='Path to the input file containing the OVH Cloud\'s connections (by default, {})'.format(FILE))

args = parser.parse_args()

f = open(args.fin, "rt")

#Lista de lineas
#Cada linea es uno de los 6 valores de una maquina
dat = [line.strip() for line in f.readlines() if line.strip() != '']
linesPerConnection = 6
#Me quedo con la ciudad y la IP
dat2 = [dat[i].split(" ")[0] for i in range(0,len(dat)) if i != 0 and i%2 == 0 and i%linesPerConnection != 0]
#Lista de tuplas del tipo (ciudad, IP)
dat = [*zip(dat2[::2],dat2[1::2])]

out = open(OUT,"w+",encoding="utf8")
out.write("### ciudad-IP-nombre_de_la_máquina ###\n\n")
for (city,ip) in dat:
    out.write("{}-{}-ubuntu\n".format(city,ip))
