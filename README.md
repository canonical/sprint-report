# Sprint Report

This tool allows to generate a Markdown report of the issues completed within
a sprint in Jira

This command takes 2 parameters: the project Key and the name of the Sprint
The script will then print out the report on the default output and can easily
be redirected into a .md file

The first time you run this command, you will be prompted for the URL of your
Jira instance, your email used for logging in and your Jira token (which can
be found via https://id.atlassian.com/manage-profile/security/api-tokens). 
If saved, this information will be persisted in ~/.jira.token

## Features
 - It will separate the issues by Type (Bug, Task, Storie)
 - It will create markdown link for Jira Key
 - If a bug summary includes LP#<bug id> it will substitute it for a link to the
   Launchpad bug
 - **Sprint Analytics**: Shows completed issues vs total issues in the sprint
 - **Story Points Analytics**: Shows completed story points vs total story points

Example:
```
$> sprint-report FR "2023 Pulse #1"
```

Before installing this tool, ensure that you have installed the Jira pip
package:
```
$> pip install jira
```
