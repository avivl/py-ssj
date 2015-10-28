# py-ssj

Slack slash command for Jira server interactions.

## Usage
```
/jira current - list my In Progress issues

/jira bug - create a bug param: project_id, "summary"
 
/jira task - create a task param: project_id, "summary"

/jira close - close an issue param: issue id

/jira assign - assign an issue to someone param issue id,assignee/me
```
## Configuration
In order for the plugin to work the `JIRA_USER` should have ```"Modify Reporter" permission``` 

Use the following enviroment variables:

```
JIRA_URL - https://mycompany.jira.server

JIRA_USER

JIRA_PASSWORD

SLACK_TOKEN 

SLACK_TEAM_ID

SLACK_SLASH_TOKEN
```

[Docker Image](https://hub.docker.com/r/rounds/10m-py-ssj/)