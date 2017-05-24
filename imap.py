""" Handling email submissions via IMAP inbox.
"""


import time
import threading
import imapclient
import email
import ssl
import re

from smtplib import SMTP_SSL
from email.mime.text import MIMEText

import conf
import reddit	
import util

def sendAuthMail(to, authUrl):

	body = "Please follow the following link to connect your reddit account, and select 'Allow' on the following page.\n\n%s" % authUrl
	msg = MIMEText(body)
	

	with SMTP_SSL(conf.mail['smtphost']) as smtp:
		smtp.login(conf.mail['username'], conf.mail['password'])
		msg = MIMEText(body)
		msg['Subject'] = "Authorizing Reddit"
		msg['From'] = conf.mail['sender']
		print('[imap]','sending to',to)
		msg['To'] = to
		
		smtp.sendmail(conf.mail['sender'], to, msg.as_string())



def imapWatcher():
	"""Watch our IMAP inbox. Periodically open mailbox, look for new messages, 
	parse content for submissions to send to Reddit, delete message.
	
	This function does not normally return.
	"""

	print('[imap] polling imap for new comments...')
	
	while True:
	
		context = imapclient.create_default_context()
		
		# don't check if certificate hostname doesn't match target hostname
		context.check_hostname = False
		
		# don't check if the certificate is trusted by a certificate authority
		context.verify_mode = ssl.CERT_NONE
		
		server = imapclient.IMAPClient(conf.imap['server'], use_uid=True, ssl=conf.imap['ssl'], ssl_context=context)
		server.login(conf.imap['username'], conf.imap['password'])
		
		select_info = server.select_folder('INBOX')
		# print(select_info)
		#print('%d messages in INBOX' % select_info['EXISTS'])
		
		#messages = server.search(['NOT', 'DELETED'])
		messages = server.search(['NOT','DELETED'])
		print("[imap] %d messages that aren't deleted" % len(messages))
		
		response = server.fetch(messages, ['ENVELOPE','RFC822','FLAGS', 'RFC822.SIZE'])
		for msgid, data in response.items():
			envelope = data[b'ENVELOPE']	
			raw_mail = data[b'RFC822']
			
			print("[imap] %s (%s)" % (msgid, envelope.to[0].mailbox))
			
			if envelope.to[0].mailbox == b'hermod-reg':
				# we're not doing this at the moment.
				r = reddit.getReddit()
				recipient = envelope.sender[0]
				to ="%s@%s" % (recipient.mailbox.decode('utf-8'), recipient.host.decode('utf-8'))

				authUrl = r.auth.url(["identity","mysubreddits","read","submit","edit","privatemessages"], \
									to,'permanent',False)
				print("[imap] auth url: %s" % authUrl)
				sendAuthMail(to, authUrl)
				server.set_flags(msgid, (imapclient.DELETED))
				continue
			else:
				print('[imap] - processing comment submission -')
				msg = email.message_from_bytes(raw_mail)
				
				# figure out who sent it
				sender = envelope.sender[0]
				to ="%s@%s" % (sender.mailbox.decode('utf-8'), sender.host.decode('utf-8'))
				
				# .. and find the right token
				tokens = util.readTokens()
				token = None
				for (t, a) in tokens:
					if a == to:
						token = t
						break
						
				if token is None:
					print('[imap] ERR: could not look up access token for %s' % to)
					print('[imap] submissions will not be delivered.')
				else:
					print('[imap] using token %s' % token)
				
				body =""
				# look for text
				if msg.is_multipart():
					print("[imap] trouble: can't yet handle multipart message")
					for part in msg.walk():
						print("[imap]", part.get_content_type())
						if part.get_content_type() == "text/plain":
							body = part.get_payload(decode=True).decode(part.get_content_charset(), 'ignore')
							print("[imap] located text/plain part")
						continue
				else:
					body = msg.get_payload(decode=True).decode(msg.get_content_charset(), 'ignore')
					
				# normalize CRLF
				body = re.sub("\r\n","\n",body)
				# remove quoted-printable
				body = re.sub("\=\n","",body)
				# split by newlines
				lines = body.split("\n")

				active = None
				response = ""
				for line in lines:
					print("[imap] =>",active, line)
					idmatch = re.search("\[\-\-(\w+_\w+)\-\-\]", line)
					
					if idmatch is not None:
						# send out previous response, if any
						if active is not None:
							reddit.sendResponse(active, response)
						active = idmatch.group(1)
						response = ""
					elif line.strip() == "!mutesub":
						# TODO: find a way to mute this entire conversation
						print("[imap] muting subreddit %s (i wish)" % idmatch)
#						
#						item = next(reddit.info([active]))
#						if "mute" not in token[2]:
#							token[2]["mute"] = []
#						token[3]["mute"].append(active)
#						util.updateToken(token)
					elif not line.startswith(">"):
						response = response + line.strip() + "\n"
					

				# send out last response we've been collecting
				if active is not None:
					reddit.sendResponse(token, active, response)
					
				print("[imap] done, deleting message %s" % msgid)
				server.set_flags(msgid, (imapclient.DELETED))
					
		server.logout()
		# sleep for a while before checking again
		print("[imap] sleeping for 120 seconds")
		time.sleep(120)
