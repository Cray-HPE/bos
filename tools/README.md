This script makes creating a BOS Session Templates easier. Its sole input is a JSON file containing the content for the Session Template. This enables a workflow where you copy the standard Session Template out of BOS, modify it, and then feed the modified file to this script to create a new Session Template. You would get the standard Session Template via the Cray CLI.
 
Workflow:

\# cray bos v1 sessiontemplate describe --format json <existing Session Template name> > my-session-template

\# vi my-session-template       # Modify the session as desired

\# bos_session_template my-session-template