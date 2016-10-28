from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from flask import Flask, request, Response, jsonify
from slackclient import SlackClient
import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'
SLACK_WEBHOOK_TOKEN=os.environ['SLACK_WEBHOOK_TOKEN']
SLACK_DEV_TOKEN=os.environ['SLACK_DEV_TOKEN']
slack_client = SlackClient(SLACK_DEV_TOKEN)
app = Flask(__name__)


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def check_user():
    """ This is a half-assed way of checking if the username exists by checking all the slackusers on the slack directory. 
    Returns list of slack users by firstname + last initial.
    """
    emailnameList = list()
    users_call = slack_client.api_call("users.list")
    if users_call.get("ok"):
        users = users_call['members']

    for u in users:
        if u.get('deleted') == False:
            if len(str(u.get('profile').get('last_name'))) > 0:
                nickname = str(
                    u.get('profile').get('first_name') +
                    u.get('profile').get('last_name')[0]).lower()
                emailnameList.append(nickname)
    return emailnameList


def check_calendar(username):
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object, checks the first scheduled event near current time and returns it
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    eventsResult = service.events().list(
        calendarId=username +
        '@markmedia.co',
        timeMin=now,
        maxResults=2,
        singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    if not events:
        statement = "%s should be at their desk." % username
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime')
        if now > start:
            statement = username + " is in a meeting. \n" + \
                start[11:19] + "-" + end[11:19] + " " + event['summary']
        else:
            statement = "%s should be at their desk" % username
    return statement


@app.route("/", methods=['POST'])
def main():
    if request.form.get('token') == SLACK_WEBHOOK_TOKEN:
        channel_id = request.form.get('channel_id')
        username = request.form.get('text').lower()
        if username not in check_user():
            return "%s is an invalid User. Please type `/whereis first name and last initial. E.g. yvanp`" % username
        else:

            json_statement = jsonify({
                'response_type': 'in_channel',
                'text': check_calendar(username)
            })

        return json_statement

    return "i just don't know. I wish I understood all error messages. So if you see this, you found an error. Hurray."


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
