import time
import os
import textwrap
import praw
import queue

from smtplib import SMTP_SSL
from email.mime.text import MIMEText
import conf, util

# last time we've run successfully?
if os.path.exists(".hermod_ts"):
	lastrun = os.path.getatime(".hermod_ts")
else:
	lastrun = 0

now = time.time()
print("it is now " + time.ctime(now))
if lastrun == 0:
	print("first run ever, this will take a while")
else:
	print("last run %d seconds ago" % (now - lastrun))
	

print('.. connecting to Reddit')
def getReddit():
	return praw.Reddit(user_agent='hermod (by /u/icestep)',
	                     client_id=conf.reddit['client_id'], client_secret=conf.reddit['client_secret'],
	                     username=conf.reddit['username'], password=conf.reddit['password'])

def watchSubmissions(mailQueue):
	reddit = getReddit()
	print("watching submissions...")
	subreddit = reddit.subreddit(conf.reddit['subreddits'])
	for submission in subreddit.stream.submissions():
		if submission.created_utc < lastrun:
			# we've seen this already, let it slide
			continue
		print("-- new submission --")
		print(vars(submission))
		body = ""
		body = body + "[--%s--] User %s made a new submission to %s titled '%s'\n" % (submission.fullname, submission.author.name, submission.subreddit.display_name, submission.title)
		body = body + "\n\n"
		
		mailQueue.put(body)
		
def sendResponse(fullname, comment):
	reddit = getReddit()
	
	item = next(reddit.info([fullname]))
	
	print("reply to %s: %s" % (repr(item),comment))
	while True:
		try:
			return
			# item.reply(comment)
		except praw.exceptions.APIException as err:
			print("Exception: %s" % err.message)
			print("Sleeping 10 minutes")
			sleep(600)
		else:
			return
			
		
def watchComments(mailQueue):
	reddit = getReddit()
	print("watching comments...")
	subreddit = reddit.subreddit(conf.reddit['subreddits'])

	for comment in subreddit.stream.comments():
		if comment.created_utc < lastrun:
			continue
		else:
			print('=== new comment ===')
		print(time.ctime(comment.created_utc))
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
	body = ""
	itemCount = 0
	lastSent = time.time()
	while True:
		try:
			# we'll send at most once per hour
			timeout = max(0, conf.mail['interval'] - time.time() + lastSent)
			if itemCount >= conf.mail['maxcount']:
				timeout = 0
			print("waiting at most %d more seconds for messages..." % timeout)
			body = body + mailQueue.get(True if timeout > 0 else False, timeout)
			itemCount = itemCount + 1
		except queue.Empty:
			if itemCount > 0:
				print("sending mail...")
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
