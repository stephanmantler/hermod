"""Hermod: Norse messenger of gods.

Entry point. Create and launch reddit related subprocesses, and run the 
IMAP watcher in an infinite loop.
"""

import time
import os
import textwrap
from multiprocessing import Process, Queue
from setproctitle import setproctitle

import conf
import util
import reddit
import imap
import httpserver


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

httpThread = Process(name="http server", target=httpserver.runHttpServer, args=())
httpThread.start()

# fire up existing tokens
print("[main] reading stored tokens")
authTokenList = util.readTokens()
print("[main] %s" % repr(authTokenList))
for token in authTokenList:
	print("[main] launching system for %s" % token[1])
	launchThreads(token)

# imap runs on the main loop
setproctitle("hermod (main loop)")
print("[main] launching imap watcher")
imap.imapWatcher()
