import os
from slack_sdk.errors import SlackApiError

def read_config(file_path):
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config[key] = value
    return config

def send_image(app_client, channel_id, message, file_path=None):
    try:
        if file_path:
            response = app_client.files_upload_v2(
                channel=channel_id,
                file=os.path.join('images', file_path),
                initial_comment=message
            )
            assert response["file"]
        else:
            response = app_client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            assert response["ok"]
    except SlackApiError as e:
        print(f"Error uploading file: {e.response['error']}")