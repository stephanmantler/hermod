# example_webserver.py #
########################

from flask import Flask, request
from setproctitle import setproctitle

import conf
import reddit
import util

app = Flask(__name__)

r = reddit.getReddit()

@app.route('/')
def homepage():
    text = "Redirecting to github ..."
    return text

@app.route('/authorize_callback')
def authorized():
    state = request.args.get('state', '')
    code = request.args.get('code', '')
    refresh_token = r.auth.authorize(code)
    
    util.saveToken(refresh_token,state)
    
    user = r.user.me()
    variables_text = "State=%s, code=%s, info=%s." % (state, code,
                                                      str(refresh_token))
    text = 'You are %s and have %u link karma.' % (user.name,
                                                   user.link_karma)
    back_link = "<a href='/'>Try again</a>"
    return "<h1>Success!</h1><p>You have connected your reddit account %s with your email %s</p><p>You can now close this window.</p>" % (user.name, state)

def runHttpServer():
	setproctitle("hermod (auth http server)")
	
	app.run(debug=False, port=1088)