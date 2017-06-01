"""Hermod: Norse messenger of gods.

Entry point. Create and launch reddit related subprocesses, and run the 
IMAP watcher in an infinite loop.
"""

import time
import os
import textwrap
from setproctitle import setproctitle
from multiprocessing import Process

import util
import imap
import httpserver


httpThread = Process(name="http server", target=httpserver.runHttpServer, args=())
httpThread.start()

# fire up existing tokens
print("[main] reading stored tokens")
authTokenList = util.readTokens()
print("[main] %s" % repr(authTokenList))
for key in authTokenList:
	token = authTokenList[key]
	print("[main] launching system for %s" % token[1])
	util.launchThreads(token)

# imap runs on the main loop
setproctitle("hermod (main loop)")
print("[main] launching imap watcher")
imap.imapWatcher()
