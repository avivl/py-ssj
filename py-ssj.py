"""Slack slash command for jira interaction."""
from flask import Flask
from flask_slack import Slack
from slackclient import SlackClient
from jira import JIRA
import json
import os

jiraIcon = "https://globus.atlassian.net/images/64jira.png"
GREEN = '#008000'
RED = '#FF0000'
YELLOW = '#FFFF00'
BLUE = '#0000FF'

JIRA_URL = os.getenv('JIRA_URL')
options = {
    'server': JIRA_URL,
}
jira = JIRA(
    options,
    basic_auth=(
        os.getenv('JIRA_USER'),
        os.getenv('JIRA_PASSWORD')))

app = Flask(__name__)
slack = Slack(app)
sc = SlackClient(os.getenv('SLACK_TOKEN'))
app.add_url_rule('/', view_func=slack.dispatch)

"""Entry point for /jira. """


@slack.command(
    'jira',
    token=os.getenv('SLACK_SLASH_TOKEN'),
    team_id=os.getenv('SLACK_TEAM_ID'),
    methods=['POST'])
def __jira_handle(**kwargs):
    user = __get_jira_username(kwargs.get('user_id'))
    channel = kwargs.get('channel_id')
    command = kwargs.get("text").partition(' ')[0].lower()
    project = kwargs.get("text").partition(' ')[2].partition(' ')[0].upper()
    summary = kwargs.get("text").partition(' ')[2].partition(' ')[2]
    if command == 'help':
        __help()
    if command == 'current':
        __jira_current(user, channel)
    if command == 'bug':
        if not __jira_validate_projectkey(project):
            return slack.response("Error Project not found!")
        __jira_create_bug(user, channel, project, summary)
    if command == 'task':
        if not __jira_validate_projectkey(project):
            return slack.response("Error Project not found!")
        __jira_create_task(user, channel, project, summary)
    return slack.response(__help())


def __help():
    help = '*Usage*: \n\
            _current_ - `list my In Progress issues` \n\
            _createb_ - `create a bug param: project_id, summary` \n\
            _createt_ - `create a task param: project_id, summary` '
    return help


def __jira_validate_projectkey(key):
    projects = jira.projects()
    for proj in projects:
        if proj.key == key:
            return True
    return False


def __get_issue_color(status):
    if status == ['Open', 'Reopened', 'To Do']:
        return BLUE
    if status == ['Resolved', 'Closed']:
        return GREEN
    if status == "Done":
        return GREEN
    return YELLOW


def __send_message_issue(issue, channel):
    attach = [{
         'color': __get_issue_color(issue.fields.status.name),
         'text': '*' + issue.fields.summary + '*\n\n *Assignee* ' +
              issue.fields.assignee.name + ' *Priority* ' +
              issue.fields.priority.name,
              'title': issue.key,
              'title_link': JIRA_URL + "/browse/" + issue.key,
              'mrkdwn_in': ['text',
                            'pretext']
              }]
    send_data = {
           'channel': channel,
           'username': 'Jira Bot',
           'icon_url': jiraIcon,
           'attachments': json.dumps(attach),
           'mrkdwn': True,
           'as_user': False}
    msg = json.loads(sc.api_call('chat.postMessage', **send_data))
    return msg


def __get_jira_username(user_id):
    response = json.loads(sc.api_call("users.info", user=user_id))
    if response.get("ok"):
        user = jira.search_users(response['user']['profile']['email'])
        if len(user) == 1:
            return user[0].name
    else:
        return ""


# Create an issue

def __jira_create_bug(user, channel, project, summary):
    return __jira_create(user, channel, project, summary, 'Bug')


def __jira_create_task(user, channel, project, summary):
    return __jira_create(user, channel, project, summary, 'Task')


def __jira_create(user, channel, project, summary, issuetype):

    issue_dict = {
                'project': {'key': project},
                'summary': summary,
                'reporter': {'name': user},
                'issuetype': {'name': issuetype},
                'assignee': {'name': user},
            }
    new_issue = jira.create_issue(fields=issue_dict)
    return __send_message_issue(new_issue, channel)

# List issues in progress


def __jira_current(user, channel):
    jql = 'status = \"In Progress\" AND assignee = ' + str(user)
    currents = jira.search_issues(jql)
    for issue in currents:
        __send_message_issue(issue, channel)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
