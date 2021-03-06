# hermod
[messenger of gods](https://en.wikipedia.org/wiki/Hermóðr). A Reddit &lt;-> email gateway


## Synopsis

Hermod is a small server that acts as a bidirectional messaging gateway between [Reddit](https://www.reddit.com) and email. 


## Motivation

The motivation of this application came from the need of quickly making a small part of Reddit accessible 
to a blind friend, both for reading and responding. The email format was chose for being easy to use with
good screen reader support and no need for installation and troubleshooting on the client computer. 

From their perspective, Reddit becomes a somewhat hectic, high-traffic but manageable mailing list.


## How It Works

Overall, the setup consists of the hermod application itself and an associated email account.

Submissions and comments on Reddit are collected and sent as digest email to the recipient. Each comment includes its immediate 'parent' (comment or submission for top level comments) to provide context. Responses to each of the items in the digest can be made by composing an email reply and interspersing responses between the quoted messages. These reply mails are delivered to the associated email account, where they can be picked up via IMAP. Hermod then identifies responses in those messages and posts them as comments to Reddit.


## Installation

Prepare an email account to be used as the 'maildrop'. You'll also need an alias that is used for the Reddit auth process; currently this is hardcoded as `hermod-reg@...` and should be forwarded to the same mailbox.

Create a new reddit account, or use your own depending on your needs. [Create a new 'web' app](https://github.com/reddit/reddit/wiki/OAuth2-Quick-Start-Example) and note the client ID an client secret that are shown afterwards; you'll need to enter those in the configuration (copy `conf.py.template` to `conf.py` and edit accordingly). Also enter the correct redirect uri (name of the server that hermod is running on; port is currently hardcoded to 1088).

Hermod has been tested with dovecot IMAP servers; in theory any other IMAP server should work.

Then, to install prerequisites and run:

	# install dependencies
    pip3 install imapclient praw Flask setproctitle
    
    # run
    python3 ./hermod.py


## Usage

### Connecting with Reddit
Fire it up. 

Send an empty email to `hermod-reg@...` (subject and content do not matter). Wait for a reply to be delivered to you. It should contain a link to reddit. Open this link and agree to authenticate. Wait for the redirection to complete (this may take a moment); then you can close the window.

From then on, hermod should start to collect digest messages for you.

### Reading and responding to digests
Wait for digest messages to arrive in your mailbox. 

To reply, add your responses inline keeping the annotations in brackets intact (quoting and/or deleting other text is fine). The subject is irrelevant. For example, the reply mail could be:

    Subject: Re: Activity on Reddit - 5 items
    From: user@example.com
    To hermod@example.com
    
    > [--t1_ahbvcjd--] User dummy commented on a submission in Aww. The title of the submission
    > was 'My new kitten'
    >
    > She is the cutest, sleeping in the laundry bin like that!
    
    I love it when they do that!
    
    > [--t1_bjelw3a--] User fnord commented on a submission in AskReddit. The title of the submission
    > was 'Who invented email?'
    >
    > I did.
    
    No, I did.
    
Once this message has been delivered, the next refresh cycle will pick it up and hermod will post `I love it when they do that!` as a response to `\u\dummy`'s comment. It will also post a snarky reply to the response of `\u\fnord`.

## Caveats

In theory, hermod supports multiple accounts. However currently everybody gets to listen to the same subreddits regardless of their own subscriptions or preferences.

Comments are posted as the reddit user associate with the sender's email address. So if somebody
figures out the email address of hermod's mailbox and the one you are using to send from, they could possibly fabricate messages that get posted in your name. 

Large volumes of traffic may produce a daunting amount of email.

Crashes or network issues may lead to double deliveries of digest messages, and possibly double postings to Reddit.


## License

MIT License (see `LICENSE` for details)

Copyright (c) 2017 Stephan Mantler