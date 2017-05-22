import os
import shelve
from multiprocessing import Process,Queue,Lock

import reddit


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


shelfLock = Lock()

def saveToken(token, address):
	shelfLock.acquire()
	authTokenList = []
	with shelve.open('.hermod.tokens') as db:
		if 'tokens' in db:
			authTokenList = db['tokens']
		authTokenList.append( (token, address) )
		db['tokens']= authTokenList
	shelfLock.release()
	
	
def readTokens():
	shelfLock.acquire()
	authTokenList = []
	with shelve.open('.hermod.tokens') as db:
		if 'tokens' in db:
			authTokenList = db['tokens']
	shelfLock.release()
	print(repr(authTokenList))
	
	return authTokenList
	

def touch(fname, mode=0o666, dir_fd=None, **kwargs):
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode, dir_fd=dir_fd)) as f:
        os.utime(f.fileno() if os.utime in os.supports_fd else fname,
            dir_fd=None if os.supports_fd else dir_fd, **kwargs)