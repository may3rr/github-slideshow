"""
Test suite for the ds_protocol module.
Verifies the functionality of JSON message formatting and parsing functions.
"""
import json
import pytest  # Import pytest for use, even if not explicitly called in every test
from ds_protocol import (
    ServerResponse, extract_json, format_authenticate_request,
    format_directmessage_request, format_fetch_request
)


# Test format_authenticate_request
def test_format_auth():
    """
    Tests the format_authenticate_request function.
    """
    json_output = format_authenticate_request("testuser", "testpass")
    obj = json.loads(json_output)
    assert isinstance(obj, dict)
    assert "authenticate" in obj
    assert obj["authenticate"]["username"] == "testuser"
    assert obj["authenticate"]["password"] == "testpass"


# Test format_directmessage_request
def test_format_dm():
    """
    Tests the format_directmessage_request function.
    """
    timestamp = 1603167689.3928561
    json_output = format_directmessage_request(
        "testtoken", "recipient_user", "Hello there!", timestamp
    )
    obj = json.loads(json_output)
    assert isinstance(obj, dict)
    assert "token" in obj
    assert "directmessage" in obj
    assert obj["token"] == "testtoken"
    assert obj["directmessage"]["entry"] == "Hello there!"
    assert obj["directmessage"]["recipient"] == "recipient_user"
    assert obj["directmessage"]["timestamp"] == timestamp


# Test format_fetch_request
def test_format_fetch():
    """
    Tests the format_fetch_request function for both 'all' and 'unread'.
    """
    # Test with "all"
    json_output_all = format_fetch_request("testtoken", "all")
    obj_all = json.loads(json_output_all)
    assert isinstance(obj_all, dict)
    assert "token" in obj_all
    assert "fetch" in obj_all
    assert obj_all["token"] == "testtoken"
    assert obj_all["fetch"] == "all"

    # Test with "unread"
    json_output_unread = format_fetch_request("testtoken", "unread")
    obj_unread = json.loads(json_output_unread)
    assert isinstance(obj_unread, dict)
    assert "token" in obj_unread
    assert "fetch" in obj_unread
    assert obj_unread["token"] == "testtoken"
    assert obj_unread["fetch"] == "unread"


# Tests for extract_json - Successful responses
def test_extract_auth_ok():
    """
    Tests extract_json for a successful authentication response.
    """
    json_string = ('{"response": {"type": "ok", "message": "Welcome back", '
                   '"token": "testtoken"}}')
    response = extract_json(json_string)
    assert response.type == "ok"
    assert response.message == "Welcome back"
    assert response.token == "testtoken"
    assert response.messages is None


def test_extract_dm_ok():
    """
    Tests extract_json for a successful direct message response.
    """
    json_string = '{"response": {"type": "ok", "message": "Direct message sent"}}'
    response = extract_json(json_string)
    assert response.type == "ok"
    assert response.message == "Direct message sent"
    assert response.token is None
    assert response.messages is None


def test_extract_fetch_unread_ok():
    """
    Tests extract_json for a successful fetch unread messages response.
    """
    json_string = ('{"response": {"type": "ok", "messages": '
                   '[{"message": "Msg1", "from": "userA", "timestamp": "ts1"}]}}')
    response = extract_json(json_string)
    assert response.type == "ok"
    assert response.message is None  # No top-level message field expected here
    assert response.token is None
    assert isinstance(response.messages, list)
    assert len(response.messages) == 1
    assert response.messages[0]["message"] == "Msg1"
    assert response.messages[0]["from"] == "userA"
    assert response.messages[0]["timestamp"] == "ts1"


def test_extract_fetch_all_ok():
    """
    Tests extract_json for a successful fetch all messages response.
    """
    json_string = ('{"response": {"type": "ok", "messages": ['
                   '{"message": "Msg1", "from": "userA", "timestamp": "ts1"}, '
                   '{"message": "Msg2", "recipient": "userA", "timestamp": "ts2"}'
                   ']}}')
    response = extract_json(json_string)
    assert response.type == "ok"
    assert response.message is None  # No top-level message field expected here
    assert response.token is None
    assert isinstance(response.messages, list)
    assert len(response.messages) == 2
    assert response.messages[0]["message"] == "Msg1"
    assert response.messages[0]["from"] == "userA"
    assert response.messages[0]["timestamp"] == "ts1"
    assert response.messages[1]["message"] == "Msg2"
    assert response.messages[1]["recipient"] == "userA"
    assert response.messages[1]["timestamp"] == "ts2"


# Tests for extract_json - Error responses and malformed JSON
def test_extract_server_error():
    """
    Tests extract_json for a server error response.
    """
    json_string = ('{"response": {"type": "error", '
                   '"message": "Invalid credentials"}}')
    response = extract_json(json_string)
    assert response.type == "error"
    assert response.message == "Invalid credentials"
    assert response.token is None
    assert response.messages is None


def test_extract_malformed_json():
    """
    Tests extract_json with a malformed JSON string.
    """
    json_string = '{"foo": "bar", "baz}'  # Intentionally broken JSON
    response = extract_json(json_string)
    assert response.type == "error"
    assert "Invalid JSON format." in response.message
    assert response.token is None
    assert response.messages is None


def test_extract_missing_response_key():
    """
    Tests extract_json when the 'response' key is missing.
    """
    json_string = '{"other_key": "value"}'
    response = extract_json(json_string)
    assert response.type == "error"
    assert "Missing 'response' key in JSON data." in response.message
    assert response.token is None
    assert response.messages is None


def test_extract_missing_type_key():
    """
    Tests extract_json when 'type' key is missing in the response object.
    extract_json is expected to return None for type if not present.
    This test verifies that behavior.
    """
    json_string = '{"response": {"message": "Something happened"}}'
    response = extract_json(json_string)
    assert response.type is None  # Type will be None as it's missing
    assert response.message == "Something happened"
    assert response.token is None
    assert response.messages is None


def test_extract_missing_message_key_in_error():
    """
    Tests extract_json when 'message' key is missing in an error response.
    extract_json is expected to return None for message if not present.
    """
    json_string = '{"response": {"type": "error"}}'
    response = extract_json(json_string)
    assert response.type == "error"
    assert response.message is None  # Message will be None
    assert response.token is None
    assert response.messages is None


```
