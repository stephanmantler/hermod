import os
import sys
import shelve
from multiprocessing import Process,Queue,Lock

import reddit

processList = {}

def launchThreads(token):
	mailQueue = Queue()

	subThread = Process(name="submissions watcher", \
						target=reddit.watchSubmissions, \
						args=(mailQueue,token))
	comThread = Process(name="comments watcher", \
						target=reddit.watchComments, \
						args=(mailQueue,token))
	mailThread = Process(name="mailer", \
						target=reddit.Mailer, \
						args=(mailQueue,token))
	subThread.start()
	comThread.start()
	mailThread.start()
	
	processList[token[1]] = (subThread, comThread, mailThread, token)
	
	
def restartThreads(token):
	processes = processList[token[1]]
	processes[0].terminate()
	processes[1].terminate()
	processes[2].terminate()
	launchThreads(token)
	

shelfLock = Lock()

def saveToken(token, address, options ):
	shelfLock.acquire()
	authTokenList = {}
	with shelve.open('.hermod.tokens') as db:
		if 'tokens' in db:
			authTokenList = db['tokens']
		authTokenList[token] =  (token, address, options )
		db['tokens']= authTokenList
	shelfLock.release()
	
def readTokens():
	shelfLock.acquire()
	authTokenList = {}
	with shelve.open('.hermod.tokens') as db:
		if 'tokens' in db:
			authTokenList = db['tokens']
	shelfLock.release()
	print(repr(authTokenList))
	
	return authTokenList
	
def removeToken(key):
	shelfLock.acquire()
	authTokenList = {}
	with shelve.open('.hermod.tokens') as db:
		if 'tokens' in db:
			del db['tokens']
	shelfLock.release()
	print(repr(authTokenList))

def touch(fname, mode=0o666, dir_fd=None, **kwargs):
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(f.fileno() if os.utime in os.supports_fd else fname,
            dir_fd=None if os.supports_fd else dir_fd, **kwargs)
            
def main(): 
	if len(sys.argv) < 2:
		print("possible commands:")
		print("  list                        list known auth tokens")
		print("  removetoken <tkey>          remove <key> from token list")
		print("  subscribe <token> <sub>     subscribe user identified by <token> to <sub>")
		print("  unsubscribe <token> <sub>   subscribe user identified by <token> to <sub>")
		print("  mute <key> <id>             mute conversation <id> for user <token>")
		return
	if sys.argv[1] == 'subscribe':
		if len(sys.argv) != 4:
			print("incorrect arg length")
			return
		print("subscribing %s to %s" % (sys.argv[2], sys.argv[3]))
		import reddit
		reddit.subscribe(None, sys.argv[2], sys.argv[3])
		return
	if sys.argv[1] == 'unsubscribe':
		if len(sys.argv) != 4:
			print("incorrect arg length")
			return
		print("unsubscribing %s from %s" % (sys.argv[2], sys.argv[3]))
		import reddit
		reddit.subscribe(None, sys.argv[2], sys.argv[3])
		return
	if sys.argv[1] == 'removetoken':
		removeToken(sys.argv[2])
		return
	if sys.argv[1] == 'list':
		tokens = readTokens()
		for key in tokens:
			print(key, repr(tokens[key]))
		return
           
if __name__ == "__main__":
	main()