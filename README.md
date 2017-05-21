# hermod
messenger of gods. a reddit &lt;-> email gateway

## Synopsis

Hermod is a small server that acts as a message gateway between Reddit and email. 

## Motivation

The motivation of this application came from the need of quickly making Reddit accessible to a blind friend, both for reading and responding. The email format was chose for being easy to use with good screen reader support and no need for installation and troubleshooting on the client computer. From their perspective, Reddit becomes a somewhat hectic, high-traffic but manageable mailing list.

## How It Works

Overall, the setup consists of the hermod application itself and an associated email account.

Submissions and comments on Reddit are collected and sent as digest email to the recipient. Responses to each of the items in the digest can be made by composing an email reply and interspersing responses between the quoted messages. These reply mails are delivered to the associated email account, where they can be picked up by hermod via IMAP. Hermod then identifies responses in those messages and posts them as comments to Reddit.

## Installation

You'll want to configure `conf.py` (see `conf.py.template` for details).

## License

MIT License (see `LICENSE` for details)

Copyright (c) 2017 Stephan Mantler