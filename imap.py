import time
import threading
import imapclient
import email
import ssl
import re
import conf
import reddit

def sendResponse(id, response):
	# remove any newlines
	stripped = response.strip()
	if len(stripped) == 0:
		# avoid empty
		return
	print("++ sending response to %s:\n%s\n" % (id,response))
	reddit.sendResponse(id, response)


def imapWatcher():

	print('polling imap for new comments...')
	
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
		print("%d messages that aren't deleted" % len(messages))
		
		print()
		print("Messages:")
		response = server.fetch(messages, ['ENVELOPE','RFC822','FLAGS', 'RFC822.SIZE'])
		for msgid, data in response.items():
			envelope = data[b'ENVELOPE']	
			raw_mail = data[b'RFC822']
			
			print("%s (%s)" % (msgid, envelope.to[0].mailbox))
			
			if envelope.to[0].mailbox == b'hermod-reg':
				# we're not doing this at the moment.
				continue
			else:
				print('- processing comment submission -')
				msg = email.message_from_bytes(raw_mail)
				
				body =""
				# look for text
				if msg.is_multipart():
					print("trouble: can't yet handle multipart message")
					print(repr(msg))
					continue
				else:
					body = str(msg.get_payload(decode=False))
					
				# normalize CRLF
				body = re.sub("\r\n","\n",body)
				# remove quoted-printable
				body = re.sub("\=\n","",body)
				# split by newlines
				lines = body.split("\n")

				active = None
				response = ""
				for line in lines:
					print("=>",active, line)
					idmatch = re.search("\[\-\-(\w+_\w+)\-\-\]", line)
					if idmatch is not None:
						# send out previous response, if any
						if active is not None:
							sendResponse(active, response)
						active = idmatch.group(1)
						response = ""
					elif not line.startswith(">"):
						response = response + line.strip() + "\n"
					

				# send out last response we've been collecting
				if active is not None:
					sendResponse(active, response)
					
				print("done, deleting message %s" % msgid)
				server.set_flags(msgid, (imapclient.DELETED))
					
		server.logout()
		e = threading.Event()
		e.wait(timeout = conf.mail['interval'])
