import time
import os
import textwrap
from multiprocessing import Process,Queue
import conf, util, reddit, imap

mailQueue = Queue()

				
subThread = Process(name="submissions watcher", target=reddit.watchSubmissions, args=(mailQueue,))
comThread = Process(name="comments watcher", target=reddit.watchComments, args=(mailQueue,))
mailThread = Process(name="mailer",target=reddit.Mailer,args=(mailQueue,))
subThread.start()
comThread.start()
mailThread.start()

imap.imapWatcher()