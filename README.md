# Sprint Report

This tool allows to generate a Markdown report of the issues completed within
a sprint in Jira

This command takes 2 parameters: the project Key and the name of the Sprint
The script will then print out the report on the default output and can easily
be redirected into a .md file

## Features
 - It will separate the issues by Type (Bug, Task, Storie)
 - It will create markdown link for Jira Key
 - If a bug summary includes LP#<bug id> it will substitute it for a link to the
   Launchpad bug

Example:
```
$> sprint-report FR "2023 Pulse #1"
```
