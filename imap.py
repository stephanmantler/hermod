""" Handling email submissions via IMAP inbox.
"""


import time
import threading
import imapclient
import email
import ssl
import re
import conf
import reddit	

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
				continue
			else:
				print('[imap] - processing comment submission -')
				msg = email.message_from_bytes(raw_mail)
				
				body =""
				# look for text
				if msg.is_multipart():
					print("[imap] trouble: can't yet handle multipart message")
					print("[imap]",repr(msg))
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
					elif line.strip() == "!mute":
						# TODO: find a way to mute this entire conversation
						print("[imap] muting conversation %s (i wish)" % idmatch)
					elif not line.startswith(">"):
						response = response + line.strip() + "\n"
					

				# send out last response we've been collecting
				if active is not None:
					reddit.sendResponse(active, response)
					
				print("[imap] done, deleting message %s" % msgid)
				server.set_flags(msgid, (imapclient.DELETED))
					
		server.logout()
		# sleep for a while before checking again
		print("[imap] sleeping for 120 seconds")
		time.sleep(120)
