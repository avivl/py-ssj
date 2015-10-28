"""Slack slash command for jira interaction."""
from flask import Flask
from flask_slack import Slack
from slackclient import SlackClient
from jira import JIRA
from jira.exceptions import JIRAError
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
    user = __get_jira_username_from_slack(kwargs.get('user_id'))
    channel = kwargs.get('channel_id')
    command = kwargs.get("text").partition(' ')[0].lower()
    jira_key = kwargs.get("text").partition(' ')[2].partition(' ')[0].upper()
    jira_data = kwargs.get("text").partition(' ')[2].partition(' ')[2]
    if command == 'help':
        __help()
    if command == 'current':
        __jira_current(user, channel)
        return slack.response("")
    if command == 'bug':
        if not __jira_validate_projectkey(jira_key):
            return slack.response("Error Project not found!")
        __jira_create_bug(user, channel, jira_key, jira_data)
        return slack.response("")
    if command == 'task':
        if not __jira_validate_projectkey(jira_key):
            return slack.response("Error Project not found!")
        __jira_create_task(user, channel, jira_key, jira_data)
        return slack.response("")
    if command == 'close':
        if not __jira_validate_issue(jira_key):
            return slack.response("Error Issue not found!")
        issue = jira.issue(jira_key)
        __jira_close(user, channel, issue)
        return slack.response("")
    if command == 'assign':
        if not __jira_validate_issue(jira_key):
            return slack.response("Error Issue not found!")
        if jira_data == 'me':
            assignee = user
        else:
            assignee = __get_jira_username(jira_data)
            if len(assignee) < 1:
                return slack.response("Error User not found!")
        issue = jira.issue(jira_key)
        __jira_assign(assignee, channel, issue)
        return slack.response("")
    return slack.response(__help())


def __help():
    help = '*Usage*: \n\
        _current_ - `list my In Progress issues` \n\
        _bug_ - `create a bug param: project_id, summary` \n\
        _task_ - `create a task param: project_id, summary` \n\
        _close_ - ` close an issue param: issue id` \n\
        _assign_ - `assign an issue to someone  param issue id,assignee/me`'
    return help


def __jira_validate_projectkey(key):
    projects = jira.projects()
    for proj in projects:
        if proj.key == key:
            return True
    return False


def __jira_validate_issue(key):
    try:
        jira.issue(key)
        return True
    except JIRAError:
        return False


def __get_issue_color(status):
    if status in ['Open', 'Reopened', 'To Do']:
        return BLUE
    if status in ['Resolved', 'Closed']:
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


def __get_jira_username_from_slack(user_id):
    response = json.loads(sc.api_call('users.info', user=user_id))
    if response.get("ok"):
        slack_user = response['user']['profile']['email']
        return __get_jira_username(slack_user)
    return ""


def __get_jira_username(user_id):
    user = jira.search_users(user_id)
    return user[0].name if len(user) == 1 else ''


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


def __jira_close(user, channel, issue):
    transitions = jira.transitions(issue)
    for t in transitions:
        if t['name'] == 'Close Issue':
            jira.transition_issue(issue, t['id'])
    return __send_message_issue(issue, channel)


def __jira_assign(assignee, channel, issue):
    jira.assign_issue(issue, assignee)
    return __send_message_issue(issue, channel)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
