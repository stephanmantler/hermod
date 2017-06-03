"""Functions related to sourcing submissions and comments from Reddit,
and sending them out via email digests.
"""

import time
import os
import textwrap
import praw
import queue
from setproctitle import setproctitle

from smtplib import SMTP_SSL
from email.mime.text import MIMEText

import conf
import util


# last time we've run successfully?
if os.path.exists(".hermod_ts"):
	lastrun = os.path.getatime(".hermod_ts")
else:
	lastrun = 0

now = time.time()	

def getReddit(token = None):
	"""Convenience function to create a Reddit instance for each process
	"""
	
	if token is not None:
		reddit = praw.Reddit(user_agent='hermod (by /u/icestep)', \
							client_id=conf.reddit['client_id'], \
							client_secret=conf.reddit['client_secret'], \
							refresh_token=token)
	else:
		reddit = praw.Reddit(user_agent='hermod (by /u/icestep)', \
							client_id=conf.reddit['client_id'], \
							client_secret=conf.reddit['client_secret'], \
							redirect_uri=conf.reddit['redirect_uri'])
								
	return reddit


def getSubreddits(r):
	subreddits =r.user.subreddits()
	srs = "+".join(x.display_name for x in subreddits if x not in conf.reddit['muted'])
	return srs
	
def subscribe(rr, token, subreddit):
	"""Subscribe to the specified subreddit"""
	
	r = rr
	if r is None:
		r = getReddit(token)
	print("[reddit] subscribing %s to %s" % (r.user.me().name, subreddit))
	r.subreddit(subreddit).subscribe()

def unsubscribe(rr, token, subreddit):
	"""Unsubscribe from the specified subreddit"""
	
	r = rr
	if r is None:
		r = getReddit(token)
	print("[reddit] unsubscribing %s from %s" % (r.user.me().name, subreddit))
	r.subreddit(subreddit).unsubscribe()
		
def sendResponse(token, fullname, comment):
	"""Send a response to Reddit.
	
	Comments are stripped of leading and trailing whitespace, and only submitted
	if they are non-empty.
	
	Positional Arguments:
	token -- the access token we need to authenticate
	fullname -- the 'full name' of the reddit object to submit the comment to
	comment -- the actual text to comment.
	"""	
	comment = comment.strip()
	if len(comment) == 0:
		# avoid empty
		return
		
	if token is None:
		# nothing to be done without token
		return
	
	reddit = getReddit(token)
		
	item = next(reddit.info([fullname]))
	
	print("[reddit] sending reply to %s: %s" % (repr(item),comment))
	while True:
		try:
			item.reply(comment)
		except praw.exceptions.APIException as err:
			print("[reddit] Exception: %s" % err.message)
			print("[reddit] Sleeping 10 minutes")
			sleep(600)
		else:
			return
			

def watchSubmissions(mailQueue, context):
	"""Watch incoming submissions, and enqueue them to the mail digest.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	setproctitle("hermod (submissions for %s)" % context[1])
	reddit = getReddit(context[0])
	print("[reddit-sub:%s] watching submissions..." % reddit.user.me().name)
	srlist = getSubreddits(reddit)
	if srlist is None or len(srlist) == 0:
		print("[reddit-sub:%s] empty subreddit list" % reddit.user.me().name)
		return
	subreddit = reddit.subreddit(srlist)
	for submission in subreddit.stream.submissions():
		if submission.created_utc < lastrun:
			# we've seen this already, let it slide
			continue
		print("[reddit-sub:%s] -- new submission --" % reddit.user.me().name)
		body = ""
		body = body + "[--%s--] User %s made a new submission to %s titled '%s'\n" % (submission.fullname, submission.author.name, submission.subreddit.display_name, submission.title)
		body = body + submission.selftext
		body = body + "\n\n"
		
		mailQueue.put(body)
			
		
def watchComments(mailQueue, context):
	"""Watch incoming comments (also nested) on existing submissions, and enqueue them to the mail digest.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	setproctitle("hermod (comments for %s)" % context[1])
	reddit = getReddit(context[0])
	print("[reddit-com:%s] watching comments..." % reddit.user.me().name)
	srlist = getSubreddits(reddit)
	if srlist is None or len(srlist) == 0:
		print("[reddit-sub:%s] empty subreddit list" % reddit.user.me().name)
		return
	subreddit = reddit.subreddit(srlist)

	for comment in subreddit.stream.comments():
		if comment.created_utc < lastrun:
			continue
		else:
			print('[reddit-com:%s] === new comment ===' % reddit.user.me().name)
#		print('[reddit-com]',time.ctime(comment.created_utc))
#			print(vars(comment))
		parent = next(reddit.info([comment.parent_id]))
		par = (parent.title+"\n"+parent.selftext) if isinstance(parent, praw.models.reddit.submission.Submission) else parent.body

		body = ""
		body = body + "[--%s--] User %s commented on a submission in %s. The title of the submission was '%s'\n" % (comment.fullname, comment.author.name, comment.subreddit.display_name, comment.link_title)

		quote = "> " + "\n> ".join(textwrap.wrap(par.strip()))
		body = body + quote + "\n\n"
		body = body + "\n".join(textwrap.wrap(comment.body)) + "\n\n"
		
		mailQueue.put(body)

def Mailer(mailQueue, context):
	"""Collect items from the queue supplied by watchSumissions and watchComments, assemble
	them into digest form and send out via email.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	setproctitle("hermod (outgoing mailer for %s)" % context[1])
	body = ""
	itemCount = 0
	lastSent = time.time()
	lastOut = time.time()
	while True:
		try:
			# we'll send at most once per hour
			timeout = max(0, conf.mail['interval'] - time.time() + lastSent)
			if itemCount >= conf.mail['maxcount']:
				timeout = 0
			if (time.time() - lastOut) > 60:
				# don't spam with messages after each update
				print("[outmailer] %d items queued, waiting at most %d more seconds for messages..." % (itemCount, timeout))
				lastOut = time.time()
			body = body + mailQueue.get(True if timeout > 0 else False, timeout)
			itemCount = itemCount + 1
		except queue.Empty:
			if itemCount > 0:
				print("[outmailer] sending mail to %s..." % context[1])
				with SMTP_SSL(conf.mail['smtphost']) as smtp:
					smtp.login(conf.mail['username'], conf.mail['password'])
					msg = MIMEText(body)
					msg['Subject'] = "Activity on Reddit - %d items" % itemCount
					msg['From'] = conf.mail['sender']
					msg['To'] = context[1]
					
					smtp.sendmail(conf.mail['sender'], context[1], msg.as_string())
				
			body = ""
			itemCount = 0
			lastSent = time.time()
			util.touch(".hermod_ts")
