"""
Defines the protocol for communication with the Distributed Server (DS),
including message formatting and parsing.
"""
import json
from collections import namedtuple
from typing import Optional, List, Dict, Any


# Define ServerResponse namedtuple
ServerResponse = namedtuple(
    'ServerResponse',
    ['type', 'message', 'token', 'messages']
)


def extract_json(json_msg: str) -> ServerResponse:
    """
    Parses a JSON message string and extracts server response data.

    Args:
        json_msg: The JSON message string to parse.

    Returns:
        A ServerResponse object containing the extracted data.
        If parsing fails or expected keys are missing, returns a ServerResponse
        with type='error' and an appropriate message.
    """
    try:
        data = json.loads(json_msg)
        if 'response' not in data:
            return ServerResponse(
                type='error',
                message="Missing 'response' key in JSON data.",
                token=None,
                messages=None
            )

        response_data = data['response']
        response_type: Optional[str] = response_data.get('type')
        message: Optional[str] = response_data.get('message')
        token: Optional[str] = response_data.get('token')
        messages_data: Optional[List[Dict[str, Any]]] = \
            response_data.get('messages')

        # This block was for a specific edge case, which is complex to hit
        # and the current .get() method for messages_data handles typical cases.
        # if (messages_data is None and
        # response_type == 'ok' and
        # 'message' in response_data and
        # isinstance(response_data['message'], list)):
        # pass # Not strictly needed due to .get() usage above.

        return ServerResponse(
            type=response_type,
            message=message,
            token=token,
            messages=messages_data
        )
    except json.JSONDecodeError:
        return ServerResponse(
            type='error',
            message="Invalid JSON format.",
            token=None,
            messages=None
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catching general Exception for unexpected issues during parsing.
        error_msg = f"An unexpected error occurred: {str(e)}"
        return ServerResponse(
            type='error',
            message=error_msg,
            token=None,
            messages=None
        )


def format_authenticate_request(username: str, password: str) -> str:
    """
    Creates a JSON string for the authenticate request.

    Args:
        username: The username for authentication.
        password: The password for authentication.

    Returns:
        A JSON string representing the authenticate request.
    """
    request = {
        "authenticate": {
            "username": username,
            "password": password
        }
    }
    return json.dumps(request)


def format_directmessage_request(
    token: str, recipient: str, message_text: str, timestamp: float
) -> str:
    """
    Creates a JSON string for the direct message request.

    Args:
        token: The authentication token.
        recipient: The username of the recipient.
        message_text: The content of the message.
        timestamp: The timestamp of the message.

    Returns:
        A JSON string representing the direct message request.
    """
    request = {
        "token": token,
        "directmessage": {
            "entry": message_text,
            "recipient": recipient,
            "timestamp": timestamp
        }
    }
    return json.dumps(request)


def format_fetch_request(token: str, what: str) -> str:
    """
    Creates a JSON string for the fetch request.

    Args:
        token: The authentication token.
        what: Specifies what to fetch ('all' or 'unread').

    Returns:
        A JSON string representing the fetch request.
    """
    request = {
        "token": token,
        "fetch": what
    }
    return json.dumps(request)


```
