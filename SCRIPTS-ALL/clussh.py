import os
import argparse
import re
import os
import stat
import atexit
import traceback
from   socket    import error as SocketError
from   paramiko  import SSHClient,AutoAddPolicy,BadHostKeyException,AuthenticationException,SSHException
from   datetime  import datetime
from   threading import Thread, Lock
from   cv2       import waitKey


CONFILE = "connections.txt"
GEOFILE = "geotriplets.txt"
KEYPATH = "../.ssh/id_rsa"
KEYPASSPHR = "eldia18hayoficina"

OPERATIONS = ["Connect","Disconnect","Execute command","Transfer files","Print tasks","Clear tasks","Update clients","Exit"]
OP_CON = 0
OP_DISCON = 1
OP_EXEC = 2
OP_TRANSFER = 3
OP_TASKS = 4
OP_CLEAR = 5
OP_UPDATE = 6
OP_EXIT = 7

TIMEOUT = 3600
CLIENTS_DB = []             # client = (city, ip, user) tuple, type = (str, str, str)
CLIENTS_SIZE = 0    
CONNECTIONS_DB = []         # connection = (SSHsession,client) tuple, type = (SSHClient, client)
CONNECTIONS_SIZE = 0
IN_PROGRESS_TASKS_DB = []   # task = (connection, cmd, date), type = (connectio, str, date)
IN_PROGRESS_TASKS_SIZE = 0 
DONE_TASKS_DB = []          # done_task = (task,(stdout,stderr)), type = (task, (str,str))

LOCK = Lock()               # only used while dealing with the tasks databases, which will be accessed by concurrent threads 

def lockAcquire(lock = LOCK):
    lock.acquire()

def lockRelease(lock = LOCK):
    lock.release()


def exit_handler():
    for (sshession,_) in CONNECTIONS_DB:
        sshession.close()

def clearScreen():
    os.system("clear") if os.name == 'posix' else os.system("cls")


def getArgsParser():
    parser = argparse.ArgumentParser(description='Handles a SSH connections cluster.')
    parser.add_argument('-con', metavar='--inputConnectionsFile', type=str, required = False, default = CONFILE,
                        help='Path to the input file containing the OVH Cloud\'s connections (by default, {})'.format(CONFILE))
    parser.add_argument('-i', metavar='--pathToKey', type=str, required = False, default = KEYPATH,
                        help='Path to the file containing the private SSH key configured for the connections (by default, {})'.format(KEYPATH))
    parser.add_argument('-p', metavar='--keyPassphrase', type=str, required = False, default = KEYPASSPHR,
                        help='The stablished passphrase for the SSH connections (by default, \"{}\")'.format(KEYPASSPHR))
    

    return parser


def parse_con_file(fname):
    '''Formats the connections file into the geotriplets format and outputs the info in the geotriplets.txt file'''
    f = open(fname, "rt")

    #Lista de lineas
    #Cada linea es uno de los 6 valores de una maquina
    dat = [line.strip() for line in f.readlines() if line.strip() != '']
    f.close()
    linesPerConnection = 6
    #Me quedo con la ciudad y la IP
    dat2 = [dat[i].split(" ")[0] for i in range(0,len(dat)) if i != 0 and i%2 == 0 and i%linesPerConnection != 0]
    #Lista de tuplas del tipo (ciudad, IP)
    dat = [*zip(dat2[::2],dat2[1::2])]

    out = open(GEOFILE,"w+",encoding="utf8")
    out.write("### ciudad-IP-nombre_de_la_máquina ###\n\n")
    for (city,ip) in dat:
        out.write("{}#{}#ubuntu\n".format(city,ip))
    
    out.close()


def show_clients():
    id = 0
    print("> CLIENTS ({}):\n".format(CLIENTS_SIZE))
    for (city,ip,user) in CLIENTS_DB:
        print("\t[{}] {}, {}@{}".format(id,city,user,ip))
        id+=1


def show_connections():
    if CONNECTIONS_DB:
        id = 0
        print("\n> CONNECTIONS ({}):\n".format(CONNECTIONS_SIZE))
        for(_,client) in CONNECTIONS_DB:
            city,ip,user = client
            print("\t[{}] {}, {}@{}".format(id,city,user,ip))
            id+=1

def show_operations():
    id = 0
    print("\n OPERATIONS:\n")
    for op in OPERATIONS:
        print("\t[{}] {}".format(id,op))
        id+=1


def show_in_progress_tasks(useLock = True):
    if useLock:
        lockAcquire()

    if IN_PROGRESS_TASKS_DB:
        id = 0
        print("\n> TASKS IN PROGRESS:\n")
        for (SSHclient,cmd,date) in IN_PROGRESS_TASKS_DB:
            _,client = SSHclient
            city,ip,user = client
            print("\t[{}] {}, {}@{} -> {} [{}]".format(id,city,user,ip,cmd,date))
            id+=1

    if useLock:
        lockRelease()


def show_done_tasks(useLock = True):
    id = 0
    if useLock:
        lockAcquire()

    print("\n> COMPLETED TASKS:\n")
    for (task,_) in DONE_TASKS_DB:
        SSHclient,cmd,date = task
        _,client = SSHclient
        city,ip,user = client
        print("\t[{}] {}, {}@{} -> {} [{}]".format(id,city,user,ip,cmd,date))
        id+=1
    
    if useLock:
        lockRelease()


def getIDs(size,info):
    '''Asks for the user for a valid list of integer IDs and returns it (both singular IDs and ranges can be specified). If empty, it is understood as "return to menu"'''
    r0 = re.compile("^((\d+-\d+)|(\d+))(,\d+-\d+|,\d+)*$")

    while True:
        ids = input("\n"+info)

        if not ids:
            return range(0,size)

        m = r0.match(ids)
        if m is None:
            if ids == "ret":
                return []
            print("ERROR: you must specify a list of either singular IDs or range of these separated by commas. Please try again.")

        else:
            parts = ids.split(",")
            r1 = re.compile("(\d+-\d+)|(\d+)")

            def getRange(line):
                parts = line.split("-")
                start, end = int(parts[0]), int(parts[1])
                return list(range(start,end+1)) if start < end else list(range(end,start+1))

            def flatten(listOfLists):
                return [item for sublist in listOfLists for item in sublist]

            ranges = flatten(list(map(getRange,filter(lambda x: x is not None, [match.group(1) for match in (r1.match(id) for id in parts) if match is not None]))))
            singularIDs = list(map(lambda x: int(x),filter(lambda x: x is not None, [match.group(2) for match in (r1.match(id) for id in parts) if match is not None])))
            allIDs = set(ranges + singularIDs)
            
            if any(list(map(lambda x: x < 0 or x >= size, allIDs))):
                print("ERROR: you must specify valid IDs included in range [{},{}]. Please try again.".format(0,size-1))
            else:
                return allIDs
            

def connect(key,pssphr):
    '''Asks for the user about the SSH clients IDs he wants to connect, updates the connections list and returns the number of current connections and a flag to force the update'''
    
    if not CLIENTS_DB:
        print("\nThere are no registered clients.")
        return 0,False
    
    clearScreen()
    show_clients()

    ids = getIDs(CLIENTS_SIZE, "Select client IDs to connect [all]: ")
    for id in ids:
        city,ip,user = CLIENTS_DB[id]

        if CLIENTS_DB[id] in [cli for _,cli in CONNECTIONS_DB]:
            print("Already connected to {}, {}@{}".format(city,user,ip))
            continue
        
        sshession = SSHClient()
        sshession.set_missing_host_key_policy(AutoAddPolicy())
        
        try:

            sshession.connect(ip,username = user, key_filename=key, passphrase=pssphr, timeout = TIMEOUT)
            print("Connected to {}, {}@{}".format(city,user,ip))
            CONNECTIONS_DB.append((sshession,CLIENTS_DB[id]))
        
        except BadHostKeyException:
            print("[SSH ERROR] {}, {}@{} --> Server's host key could not be verified".format(city,user,ip))
        except AuthenticationException:
            print("[SSH ERROR] {}, {}@{} --> Authentication failed".format(city,user,ip))
        except SSHException:
            print("[SSH ERROR] {}, {}@{} --> An unexpected error occured while connecting/establishing an SSH session")
        except SocketError:
            print("[SOCKET ERROR] {}, {}@{} --> {}".format(city,user,ip,SocketError.strerror))
        
        finally:
            continue

    return len(CONNECTIONS_DB), False if ids else True


def disconnect(exit = False):
    '''Asks for the user about the SSH connections IDs he wants to disconnect from, removes them from the connections list and returns the number of current connections'''
    
    if not CONNECTIONS_DB:
        print("\nThere are no connections opened.")
        return
    
    clearScreen()
    
    if (not exit):
        show_connections()
        ids = getIDs(CONNECTIONS_SIZE,"Select client IDs to disconnect [all]: ")
    else:
        ids = range(0,CONNECTIONS_SIZE)

    disconList = [CONNECTIONS_DB[id] for id in ids]
    for discon in disconList:
            sshession,client = discon
            city,user,ip = client
            sshession.close()
            print("Disconnected from {}, {}@{}".format(city,user,ip))
            CONNECTIONS_DB.remove(discon)

    return len(CONNECTIONS_DB), False if ids else True


def thread_exec_cmd(task):
    '''Function for threading the execution of a command in a SSH client. When done, it removes the task from the in progress tasks DB and stores it in the completed tasks one'''
    connection,cmd,_ = task
    sshession,_ = connection
    try:
        _,stdout,stderr = sshession.exec_command(cmd)

        # If the command is yet to finish, the execution waits until it does
        stdout.channel.recv_exit_status()
        output = "\n"+stdout.read().decode("utf8").replace("\n","\n\t")
        error = "\n"+stderr.read().decode("utf8").replace("\n","\n\t")
    except SSHException:
        output = ""
        error = "\n\tSSHException --> The server failed to execute the command"

    lockAcquire()

    IN_PROGRESS_TASKS_DB.remove(task)
    DONE_TASKS_DB.append((task,(output,error)))
    lockRelease()



def exec_command():
    '''Executes a command in a list of SSH connections, both specified by the user'''
    if not CONNECTIONS_DB:
        print("\nThere are no connections opened.")
        return

    clearScreen()
    show_connections()
    ids = getIDs(len(CONNECTIONS_DB),"Select connection IDs where to execute command [all]: ")
    if ids:
        cmd = input("\nCommand to execute: ")
        if cmd == "ret":
            ids = []

    for id in ids:

        _,client = CONNECTIONS_DB[id]
        city,ip,user = client
        date = datetime.now()

        lockAcquire()
        task = (CONNECTIONS_DB[id],cmd,date)
        IN_PROGRESS_TASKS_DB.append(task)
        lockRelease()

        Thread(target=thread_exec_cmd,args=(task,)).start()
        print("Executing command in {}, {}@{}".format(city,user,ip))
    
    if ids:
        print("Print TASKS to see more info about outputs and errors.\n")
    
    return False if ids else True


def print_tasks():
    '''Prints in progress and completed tasks. Also asks the user for which tasks he is interested to see their outputs. Returns True if the user wants to return to the menu (force update) and False otherwise'''

    clearScreen()
    show_in_progress_tasks()

    lockAcquire()
    forceUpdate = False
    if DONE_TASKS_DB:
        show_done_tasks(useLock = False)
        ids = getIDs(len(DONE_TASKS_DB),"Select task(s) to see outputs[see all outputs]: ")
        if ids:
            clearScreen()
            print("\n> COMPLETED TASKS INFO:\n")

            for id in ids:
                task,info = DONE_TASKS_DB[id]
                SSHclient,cmd,date = task
                _, client = SSHclient
                city,ip,user = client
                stdout, stderr = info
                print("\t{}, {}@{} -> {} [{}]\n\n\t=== OUTPUT === \n\n\t{}\n\n\t=== ERROR ===\n\n\t{}\n".format(city,user,ip,cmd,date,stdout,stderr))
        else:
            forceUpdate = True

    else:
        print("There are no completed tasks so far...")

    lockRelease()
    return forceUpdate
      

def thread_transfer(task,sourcePath,targetPath,receiver):
    '''Function for threading the transference of file between local machine and a SSH client. When done, it removes the task from the in progress tasks DB and stores it in the completed tasks one'''
    connection,cmd,_ = task
    sshession,client = connection
    _,_,user = client

    sftpClient = sshession.open_sftp()

    (transferFun,listDirFun) = (sftpClient.get,sftpClient.listdir) if receiver else (sftpClient.put,os.listdir)
    isDir = err = False

    try:
        sourcePath.replace("~", "/home/{}".format(user) if receiver else os.getcwd())
        targetPath.replace("~", "/home/{}".format(user) if not receiver else os.getcwd())
        
        # If I am to send/receive a directory
        if (not receiver and os.path.isdir(sourcePath)) or (receiver and stat.S_ISDIR(sftpClient.lstat(sourcePath).st_mode)):
            isDir = True
        
        # WARNING: if the sourcePath identifies a directory, then it must contain EXCLUSIVELY regular files
        files =  listDirFun(sourcePath) if isDir else [sourcePath]
        sourcePath = "{}/".format(sourcePath) if isDir and not sourcePath.endswith("/") else sourcePath
        targetPath = "{}/".format(targetPath) if not targetPath.endswith("/") else targetPath
        
        # I make sure that the target path (directory) exists
        try:
            if not receiver:
                try:
                    sftpClient.stat(targetPath)
                except FileNotFoundError:
                    sftpClient.mkdir(targetPath)
            elif not os.path.exists(targetPath):
                    os.mkdir(targetPath)

        # It's likely for more than one thread to create a directory, if not previously existing, so at one time it will be created and at the next time some thread will try
        # to create it again, which arises the next exception (we ignore it)
        except FileExistsError:
            pass
        
        # This code must be rewritten in order to support recursive directory transferences (see WARNING above)
        for file in files:
            transferFun(sourcePath+file if isDir else file,targetPath+file if isDir else file)
    
    except:
        infoError = traceback.format_exc()
        err = True

    lockAcquire()
    IN_PROGRESS_TASKS_DB.remove(task)
    DONE_TASKS_DB.append((task,(cmd if not err else "","" if not err else infoError)))
    lockRelease()

def transfer():
    '''Transfers files to/from specified SSH clients. It asks the user for SSH connections to interact with and the source/target paths. Returns True if the user wants to return to the menu, False otherwise'''
    
    if not CONNECTIONS_DB:
        print("\nThere are no connections opened.")
        return
    
    clearScreen()
    show_connections()
    size = len(CONNECTIONS_DB)
    
    receiver = input("Receiver? [False]: ")
    if receiver == "ret":
        return True
    receiver = bool(receiver)
    
    ids = getIDs(size,"Select SSH client(s) where you'd like to transfer files to/from [all]: ")
    
    if ids:
        while True:
            path = input("Path to the file/directory to transfer: ")
            if path == "ret":
                ids = []
                break
            if not receiver and not os.path.exists(path):
                print("ERROR: The path specified does not exist. Please try again.")
                continue
            else:
                break

        if ids:
            target = input("Target directory: ")
            if target == "ret":
                ids = []
            for id in ids:
                
                lockAcquire()
                task = (CONNECTIONS_DB[id],"Transfer {} to {} ({})".format(path,target,"FROM" if receiver else "TO"),datetime.now())
                IN_PROGRESS_TASKS_DB.append(task)
                lockRelease()
                
                Thread(target=thread_transfer,args=(task,path,target,receiver,)).start()

    return False if ids else True
    

def updateClients(fin):
    '''Updated the clients DB if new ones are available in the input file. Returns the length of the DB and True for a forced update'''
    global CLIENTS_DB
    geofin = open(fin,"rt")

    # triplets list (city,ip,remote_user_name)
    CLIENTS_DB = [tuple(pair.strip().split("#")) for pair in list(filter(lambda x: x != "\n" and x != "\r" and x != "\r\n",geofin.readlines()[1:]))]
    geofin.close()
    return len(CLIENTS_DB), True


def getOperation() -> int:
    r0 = re.compile("^\d+$")
    size = len(OPERATIONS)
    while True:
        op = input("Select an operation: ").replace("\n","").replace(" ","")
        if not op:
            return -1
        m = r0.match(op)
        if m is None or int(op) not in range(0,size):
            print("ERROR: you must specify a valid operation ID included in range [{},{}]. Please try again.".format(0,size-1))
        else:
            return int(op)


def menu():
    '''Displays the menu and returns an integer ID, specified by the user, for one of the available operations'''
    clearScreen()
    print("\n==================== CLUS(SH)TERS MENU ====================\n")
    show_clients()
    show_connections()
    show_in_progress_tasks()
    show_operations()
    print("\n===========================================================\n")
    
    return getOperation()   

    

atexit.register(exit_handler)
args = getArgsParser().parse_args()

parse_con_file(args.con)
CLIENTS_SIZE,_ = updateClients(GEOFILE)

exit = False
forceUpdate = False
op = -1

while op is not OP_EXIT:
    op = menu()

    if op < 0:
        continue
    
    elif op is OP_CON:
        CONNECTIONS_SIZE,forceUpdate = connect(args.i,args.p)

    elif op is OP_DISCON:
        CONNECTIONS_SIZE,forceUpdate = disconnect()

    elif op is OP_EXEC:
        forceUpdate = exec_command()

    elif op is OP_TASKS:
        forceUpdate = print_tasks()

    elif op is OP_TRANSFER:
        forceUpdate = transfer()

    elif op is OP_CLEAR:
        lockAcquire()
        DONE_TASKS_DB.clear()
        lockRelease()
        forceUpdate = True

    elif op is OP_UPDATE:
        parse_con_file(args.con)
        CLIENTS_SIZE, forceUpdate = updateClients(GEOFILE)


    if not forceUpdate and op is not OP_EXIT:
        input("Press any key to continue...")
        waitKey()
