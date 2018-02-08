# General purpose Lambda function for sending Slack messages, encrypted in transit.

import boto3
import json
import logging
import os
import csv
import io
from collections import Counter

# Required if you want to encrypt your Slack Hook URL in the AWS console
# from base64 import b64decode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SLACK_CHANNEL = os.environ['slackChannel']
# Required if you want to encrypt your Slack hook URL in the AWS Console
# ENCRYPTED_HOOK_URL = os.environ['slackHookUrl']
# HOOK_URL = boto3.client('kms').decrypt(CiphertextBlob=b64decode(os.environ['slackHookUrl']))['Plaintext'].decode('utf-8')
HOOK_URL = os.environ['slackHookUrl']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lam = boto3.client('lambda')

def lambda_handler(event, context):
    """Sends out a formatted slack message.  Edit to your liking."""
    
    msg_text = 'Hello humans. Some of you have not tagged your AWS instances yet.'
    leaderboard_length = 15
    untagged = get_untagged_instances()
    lb = generate_leaderboard(untagged, leaderboard_length)
    
    send_slack_message(
        msg_text, 
        title='The Wall Of Shame :shame: :bell:',
        text="```\n"+lb+"\n```",
        fallback='The Wall of Shame :shame: :bell:',
        color='warning',
        actions = [
            {
                "type": "button",
                "text": ":mag: Find my stuff",
                "url": "https://hashicorp.slack.com/files/U8QGF2A30/F8ZNCRP41/show_all_instances_sh.sh"
            },
            {
                "type": "button",
                "text": ":broom: Clean up my stuff",
                "url": "https://console.aws.amazon.com/ec2/v2/home"
            },
        ]
    )
    
def send_slack_message(msg_text, **kwargs):
    """Sends a slack message to the slackChannel you specify. The only parameter
    required here is msg_text, or the main message body text. If you want to 
    format your message use the attachment feature which is documented here: 
    https://api.slack.com/docs/messages.  You simply pass in your attachment 
    parameters as keyword arguments, or key-value pairs. This function currently
    only supports a single attachment for simplicity's sake.
    """
    slack_message = {
        'channel': SLACK_CHANNEL,
        'text': msg_text,
        'attachments': [ kwargs ]
    }

    req = Request(HOOK_URL, json.dumps(slack_message).encode('utf-8'))
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)
        
def get_untagged_instances():
    """Calls the Lambda function that returns a dictionary of instances."""
    try:
        response = lam.invoke(FunctionName='getUntaggedInstances', InvocationType='RequestResponse')
    except Exception as e:
        print(e)
        raise e
    return response
    
def generate_leaderboard(response,num_leaders):
    """Generates a leaderboard showing KeyNames with the most untagged instances."""
    data = json.loads(response['Payload'].read().decode('utf-8'))
    data = json.loads(data)
    sshkeys = []
    for key, value in data.items():
        sshkeys.append(value['KeyName'])
    leaders = dict(Counter(sshkeys))
    tmp = io.StringIO()
    writer = csv.writer(tmp, delimiter='\t')
    count=0
    # This is a fancy way to say 'return leaders in reverse numerical order'.
    for key, value in sorted(leaders.items(), key=lambda x: x[1], reverse=True):
        if count < num_leaders:
            writer.writerow(["{: >2}".format(value), (key or 'No KeyName')])
        count = count + 1
    leaderboard = tmp.getvalue()
    # To keep things simple we make sure these functions always return a string.
    return(leaderboard)