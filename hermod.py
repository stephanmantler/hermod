"""Hermod: Norse messenger of gods.

Entry point. Create and launch reddit related subprocesses, and run the 
IMAP watcher in an infinite loop.
"""

import time
import os
import textwrap
from multiprocessing import Process, Queue
import conf, util, reddit, imap

mailQueue = Queue()
				
subThread = Process(name="submissions watcher", target=reddit.watchSubmissions, args=(mailQueue,))
comThread = Process(name="comments watcher", target=reddit.watchComments, args=(mailQueue,))
mailThread = Process(name="mailer",target=reddit.Mailer,args=(mailQueue,))
subThread.start()
comThread.start()
mailThread.start()

imap.imapWatcher()