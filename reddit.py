"""Functions related to sourcing submissions and comments from Reddit,
and sending them out via email digests.
"""

import time
import os
import textwrap
import praw
import queue

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

def getReddit():
	"""Convenience function to create a Reddit instance for each process
	"""
	
	return praw.Reddit(user_agent='hermod (by /u/icestep)',
	                     client_id=conf.reddit['client_id'], client_secret=conf.reddit['client_secret'],
	                     username=conf.reddit['username'], password=conf.reddit['password'])
		
def sendResponse(fullname, comment):
	"""Send a response to Reddit.
	
	Comments are stripped of leading and trailing whitespace, and only submitted
	if they are non-empty.
	
	Positional Arguments:
	fullname -- the 'full name' of the reddit object to submit the comment to
	comment -- the actual text to comment.
	"""	
	comment = comment.strip()
	if len(comment) == 0:
		# avoid empty
		return
	
	reddit = getReddit()
		
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
			

def watchSubmissions(mailQueue):
	"""Watch incoming submissions, and enqueue them to the mail digest.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	reddit = getReddit()
	print("[reddit-sub] watching submissions...")
	subreddit = reddit.subreddit(conf.reddit['subreddits'])
	for submission in subreddit.stream.submissions():
		if submission.created_utc < lastrun:
			# we've seen this already, let it slide
			continue
		print("[reddit-sub] -- new submission --")
		body = ""
		body = body + "[--%s--] User %s made a new submission to %s titled '%s'\n" % (submission.fullname, submission.author.name, submission.subreddit.display_name, submission.title)
		body = body + "\n\n"
		
		mailQueue.put(body)
			
		
def watchComments(mailQueue):
	"""Watch incoming comments (also nested) on existing submissions, and enqueue them to the mail digest.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	reddit = getReddit()
	print("[reddit-com] watching comments...")
	subreddit = reddit.subreddit(conf.reddit['subreddits'])

	for comment in subreddit.stream.comments():
		if comment.created_utc < lastrun:
			continue
		else:
			print('[reddit-com] === new comment ===')
		print('[reddit-com]',time.ctime(comment.created_utc))
#			print(vars(comment))
		parent = next(reddit.info([comment.parent_id]))
		par = (parent.title+"\n"+parent.selftext) if isinstance(parent, praw.models.reddit.submission.Submission) else parent.body

		body = ""
		body = body + "[--%s--] User %s commented on a submission in %s. The title of the submission was '%s'\n" % (comment.fullname, comment.author.name, comment.subreddit.display_name, comment.link_title)

		quote = "> " + "\n> ".join(textwrap.wrap(par.strip()))
		body = body + quote + "\n\n"
		body = body + "\n".join(textwrap.wrap(comment.body)) + "\n\n"
		
		mailQueue.put(body)

def Mailer(mailQueue):
	"""Collect items from the queue supplied by watchSumissions and watchComments, assemble
	them into digest form and send out via email.
	
	This function is designed to run as its own process, and does not normally return.
	"""
	
	body = ""
	itemCount = 0
	lastSent = time.time()
	while True:
		try:
			# we'll send at most once per hour
			timeout = max(0, conf.mail['interval'] - time.time() + lastSent)
			if itemCount >= conf.mail['maxcount']:
				timeout = 0
			print("[outmailer] waiting at most %d more seconds for messages..." % timeout)
			body = body + mailQueue.get(True if timeout > 0 else False, timeout)
			itemCount = itemCount + 1
		except queue.Empty:
			if itemCount > 0:
				print("[outmailer] sending mail...")
				with SMTP_SSL(conf.mail['smtphost']) as smtp:
					smtp.login(conf.mail['username'], conf.mail['password'])
					msg = MIMEText(body)
					msg['Subject'] = "Activity on Reddit - %d items" % itemCount
					msg['From'] = conf.mail['sender']
					msg['To'] = conf.mail['recipient']
					
					smtp.sendmail(conf.mail['sender'], conf.mail['recipient'], msg.as_string())
				
			body = ""
			itemCount = 0
			lastSent = time.time()
			util.touch(".hermod_ts")
