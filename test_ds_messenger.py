"""
Test suite for the ds_messenger.py module.
Verifies the functionality of the DirectMessenger class, including authentication,
message sending/retrieval, and interaction with a mocked DS server and protocol.
"""
import pytest
import socket
from unittest.mock import patch, MagicMock

from ds_messenger import (
    DirectMessenger, DirectMessage, AuthenticationError, ServerConnectionError
)
from ds_protocol import ServerResponse


# Constants for tests
TEST_USER = "testuser"
TEST_PASS = "testpass"
TEST_SERVER = "testserver.com"
TEST_PORT = 3001  # Default port in DirectMessenger
DEFAULT_SERVER = "127.0.0.1"


@patch('ds_protocol.format_authenticate_request', return_value='auth_json_string')
@patch('socket.socket')  # Mocks the socket class
class TestDirectMessengerInit:
    """Tests for DirectMessenger.__init__ method."""

    def test_init_successful_authentication_default_server(
            self, mock_socket_class, mock_format_auth):
        """
        Test successful initialization and authentication with the default server.
        """
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance

        successful_auth_response = ServerResponse(
            type='ok', message='Authenticated', token='test_token', messages=None
        )

        with patch.object(DirectMessenger, '_send_request',
                          return_value=successful_auth_response) as mock_internal_send:
            messenger = DirectMessenger(username=TEST_USER, password=TEST_PASS)

            mock_socket_class.assert_called_once_with(
                socket.AF_INET, socket.SOCK_STREAM
            )
            mock_socket_instance.settimeout.assert_called_once_with(5)
            mock_socket_instance.connect.assert_called_once_with(
                (DEFAULT_SERVER, TEST_PORT)
            )
            mock_format_auth.assert_called_once_with(TEST_USER, TEST_PASS)
            mock_internal_send.assert_called_once_with('auth_json_string')
            assert messenger.token == 'test_token'
            assert messenger.dsuserver == DEFAULT_SERVER
            assert messenger.client_socket is mock_socket_instance

    def test_init_successful_authentication_custom_server(
            self, mock_socket_class, mock_format_auth):
        """
        Test successful initialization and authentication with a custom server.
        """
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        successful_auth_response = ServerResponse(
            type='ok', message='Authenticated',
            token='test_token_custom', messages=None
        )

        with patch.object(DirectMessenger, '_send_request',
                          return_value=successful_auth_response) as mock_internal_send:
            messenger = DirectMessenger(
                dsuserver=TEST_SERVER, username=TEST_USER, password=TEST_PASS
            )

            mock_socket_instance.connect.assert_called_once_with(
                (TEST_SERVER, TEST_PORT)
            )
            mock_format_auth.assert_called_once_with(TEST_USER, TEST_PASS)
            mock_internal_send.assert_called_once_with('auth_json_string')
            assert messenger.token == 'test_token_custom'
            assert messenger.dsuserver == TEST_SERVER

    def test_init_authentication_failure(
            self, mock_socket_class, mock_format_auth):
        """Test initialization failure due to authentication error."""
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        auth_failure_response = ServerResponse(
            type='error', message='Auth failed', token=None, messages=None
        )

        with patch.object(DirectMessenger, '_send_request',
                          return_value=auth_failure_response):
            with pytest.raises(AuthenticationError,
                               match="Authentication failed: Auth failed"):
                DirectMessenger(username=TEST_USER, password=TEST_PASS)

        mock_socket_instance.close.assert_called_once()

    def test_init_connection_failure_socket_error_on_connect(
            self, mock_socket_class, mock_format_auth_unused):
        """Test initialization failure due to socket.error on connect."""
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.error("Connection refused")
        mock_socket_class.return_value = mock_socket_instance

        with pytest.raises(ServerConnectionError,
                           match="Could not connect to .* Connection refused"):
            DirectMessenger(username=TEST_USER, password=TEST_PASS)
        mock_socket_instance.close.assert_not_called()

    def test_init_connection_failure_timeout_on_connect(
            self, mock_socket_class, mock_format_auth_unused):
        """Test initialization failure due to socket.timeout on connect."""
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.timeout("Connection timed out")
        mock_socket_class.return_value = mock_socket_instance

        with pytest.raises(ServerConnectionError,
                           match="Connection to .* timed out"):
            DirectMessenger(username=TEST_USER, password=TEST_PASS)

    def test_init_missing_credentials(
            self, mock_socket_class_unused, mock_format_auth_unused):
        """Test initialization failure due to missing credentials."""
        with pytest.raises(ValueError,
                           match="Username and password must be provided"):
            DirectMessenger(username=TEST_USER)
        with pytest.raises(ValueError,
                           match="Username and password must be provided"):
            DirectMessenger(password=TEST_PASS)


@patch('ds_protocol.format_directmessage_request', return_value='dm_json_string')
@patch('time.time', return_value=12345.6789)
class TestDirectMessengerSend:
    """Tests for DirectMessenger.send method."""

    @pytest.fixture
    def authenticated_messenger(self):
        """Fixture to provide an authenticated DirectMessenger instance."""
        with patch.object(DirectMessenger, '_connect_and_authenticate',
                          MagicMock()) as mock_connect_auth_method:
            messenger = DirectMessenger(
                dsuserver=TEST_SERVER, username=TEST_USER, password=TEST_PASS
            )
            messenger.token = "fake_token"
            messenger.client_socket = MagicMock()
            mock_connect_auth_method.assert_called_once()
            return messenger

    def test_send_successful(self, mock_time_unused, mock_format_dm,
                             authenticated_messenger):
        """Test successful message sending."""
        successful_send_response = ServerResponse(
            type='ok', message='Message sent', token=None, messages=None
        )
        authenticated_messenger._send_request = MagicMock(
            return_value=successful_send_response
        )

        result = authenticated_messenger.send("Hello", "recipient1")

        mock_format_dm.assert_called_once_with(
            "fake_token", "recipient1", "Hello", 12345.6789
        )
        authenticated_messenger._send_request.assert_called_once_with(
            'dm_json_string'
        )
        assert result is True

    def test_send_failure_server_error(self, mock_time_unused, mock_format_dm_unused,
                                     authenticated_messenger):
        """Test message sending failure due to server error response."""
        error_send_response = ServerResponse(
            type='error', message='Server error', token=None, messages=None
        )
        authenticated_messenger._send_request = MagicMock(
            return_value=error_send_response
        )

        result = authenticated_messenger.send("Hello", "recipient1")
        assert result is False

    def test_send_not_authenticated(self, mock_time_unused, mock_format_dm,
                                  authenticated_messenger):
        """Test message sending failure when not authenticated (no token)."""
        authenticated_messenger.token = None
        authenticated_messenger._send_request = MagicMock()

        result = authenticated_messenger.send("Hello", "recipient1")

        assert result is False
        mock_format_dm.assert_not_called()
        authenticated_messenger._send_request.assert_not_called()

    def test_send_socket_error_in_send_request(
            self, mock_time_unused, mock_format_dm_unused, authenticated_messenger):
        """Test message sending failure due to socket error in _send_request."""
        socket_error_response = ServerResponse(
            type='error', message='Socket error during send',
            token=None, messages=None
        )
        authenticated_messenger._send_request = MagicMock(
            return_value=socket_error_response
        )

        result = authenticated_messenger.send("Hello", "recipient1")
        assert result is False


@patch('ds_protocol.format_fetch_request', return_value='fetch_json_string')
class TestDirectMessengerRetrieve:
    """Tests for DirectMessenger message retrieval methods."""

    @pytest.fixture
    def authenticated_messenger(self):
        """Fixture for an authenticated messenger instance."""
        with patch.object(DirectMessenger, '_connect_and_authenticate',
                          MagicMock()):
            messenger = DirectMessenger(
                dsuserver=TEST_SERVER, username=TEST_USER, password=TEST_PASS
            )
            messenger.token = "fake_token"
            messenger.username = TEST_USER
            messenger.client_socket = MagicMock()
            messenger._send_request = MagicMock()
            return messenger

    # --- retrieve_new ---
    def test_retrieve_new_successful(self, mock_format_fetch,
                                     authenticated_messenger):
        """Test successful retrieval of new messages."""
        sample_messages = [{
            'message': 'New msg 1', 'from': 'senderA', 'timestamp': 'ts1'
        }]
        fetch_response = ServerResponse(
            type='ok', messages=sample_messages, token=None, message=None
        )
        authenticated_messenger._send_request.return_value = fetch_response

        messages = authenticated_messenger.retrieve_new()

        mock_format_fetch.assert_called_once_with("fake_token", "unread")
        authenticated_messenger._send_request.assert_called_once_with(
            'fetch_json_string'
        )
        assert len(messages) == 1
        assert isinstance(messages[0], DirectMessage)
        assert messages[0].message == 'New msg 1'
        assert messages[0].sender == 'senderA'
        assert messages[0].recipient == TEST_USER
        assert messages[0].timestamp == 'ts1'

    def test_retrieve_new_no_messages(self, mock_format_fetch_unused,
                                      authenticated_messenger):
        """Test retrieval when there are no new messages."""
        fetch_response = ServerResponse(
            type='ok', messages=[], token=None, message=None
        )
        authenticated_messenger._send_request.return_value = fetch_response

        messages = authenticated_messenger.retrieve_new()
        assert messages == []

    def test_retrieve_new_failure_server_error(self, mock_format_fetch_unused,
                                               authenticated_messenger):
        """Test retrieval failure due to server error response."""
        fetch_response = ServerResponse(
            type='error', message='Server error', token=None, messages=None
        )
        authenticated_messenger._send_request.return_value = fetch_response

        messages = authenticated_messenger.retrieve_new()
        assert messages == []

    def test_retrieve_new_not_authenticated(self, mock_format_fetch,
                                           authenticated_messenger):
        """Test retrieval failure when not authenticated."""
        authenticated_messenger.token = None

        messages = authenticated_messenger.retrieve_new()

        assert messages == []
        mock_format_fetch.assert_not_called()
        authenticated_messenger._send_request.assert_not_called()

    def test_retrieve_new_socket_error_in_send_request(
            self, mock_format_fetch_unused, authenticated_messenger):
        """Test retrieval failure due to socket error in _send_request."""
        socket_error_response = ServerResponse(
            type='error', message='Socket error', token=None, messages=None
        )
        authenticated_messenger._send_request.return_value = socket_error_response

        messages = authenticated_messenger.retrieve_new()
        assert messages == []

    # --- retrieve_all ---
    def test_retrieve_all_successful(self, mock_format_fetch,
                                     authenticated_messenger):
        """Test successful retrieval of all messages."""
        sample_all_messages = [
            {'message': 'Incoming Msg1', 'from': 'senderA', 'timestamp': 'tsA'},
            {'message': 'Outgoing Msg2', 'recipient': 'recipientB',
             'timestamp': 'tsB'}
        ]
        fetch_response = ServerResponse(
            type='ok', messages=sample_all_messages, token=None, message=None
        )
        authenticated_messenger._send_request.return_value = fetch_response

        messages = authenticated_messenger.retrieve_all()

        mock_format_fetch.assert_called_once_with("fake_token", "all")
        authenticated_messenger._send_request.assert_called_once_with(
            'fetch_json_string'
        )
        assert len(messages) == 2
        assert messages[0].message == 'Incoming Msg1'
        assert messages[0].sender == 'senderA'
        assert messages[1].message == 'Outgoing Msg2'
        assert messages[1].recipient == 'recipientB'
        assert messages[1].sender == TEST_USER

    def test_retrieve_all_failure_server_error(self, mock_format_fetch_unused,
                                               authenticated_messenger):
        """Test 'retrieve_all' failure due to server error."""
        fetch_response = ServerResponse(type='error', message='Server error')
        authenticated_messenger._send_request.return_value = fetch_response
        messages = authenticated_messenger.retrieve_all()
        assert messages == []

    def test_retrieve_all_not_authenticated(self, mock_format_fetch,
                                            authenticated_messenger):
        """Test 'retrieve_all' failure when not authenticated."""
        authenticated_messenger.token = None
        messages = authenticated_messenger.retrieve_all()
        assert messages == []
        mock_format_fetch.assert_not_called()
        authenticated_messenger._send_request.assert_not_called()

    def test_retrieve_all_socket_error_in_send_request(
            self, mock_format_fetch_unused, authenticated_messenger):
        """Test 'retrieve_all' failure due to socket error."""
        socket_error_response = ServerResponse(type='error', message='Socket error')
        authenticated_messenger._send_request.return_value = socket_error_response
        messages = authenticated_messenger.retrieve_all()
        assert messages == []


class TestDirectMessengerCloseConnectionAndDel:
    """Tests for DirectMessenger.close_connection and __del__."""

    @pytest.fixture
    def connected_messenger(self):
        """Fixture for a connected messenger instance."""
        with patch('socket.socket') as mock_socket_class, \
             patch('ds_protocol.format_authenticate_request'), \
             patch.object(DirectMessenger, '_send_request') as mock_init_send_req:

            mock_socket_instance = MagicMock()
            mock_socket_class.return_value = mock_socket_instance
            mock_init_send_req.return_value = ServerResponse(
                type='ok', token='initial_token', message='Auth OK'
            )

            messenger = DirectMessenger(TEST_SERVER, TEST_USER, TEST_PASS)
            assert messenger.client_socket is mock_socket_instance
            assert messenger.token == 'initial_token'
            return messenger, mock_socket_instance

    def test_close_connection(self, connected_messenger):
        """Test the close_connection method."""
        messenger, mock_socket_instance = connected_messenger
        messenger.close_connection()

        mock_socket_instance.close.assert_called_once()
        assert messenger.token is None
        assert messenger.client_socket is None

    def test_close_connection_socket_already_none(self, connected_messenger):
        """Test close_connection when socket is already None."""
        messenger, mock_socket_instance = connected_messenger
        messenger.client_socket = None
        messenger.token = "some_token"

        messenger.close_connection()

        mock_socket_instance.close.assert_not_called()
        assert messenger.token is None
        assert messenger.client_socket is None

    @patch.object(DirectMessenger, 'close_connection')
    def test_del_calls_close_connection(self, mock_close_method):
        """Test that __del__ calls close_connection."""
        with patch('socket.socket'), \
             patch('ds_protocol.format_authenticate_request'), \
             patch.object(DirectMessenger, '_send_request',
                          return_value=ServerResponse(type='ok', token='t')):
            messenger_instance = DirectMessenger(
                TEST_SERVER, TEST_USER, TEST_PASS
            )
            mock_close_method.assert_not_called()

        del messenger_instance
        mock_close_method.assert_called_once()


@patch('ds_protocol.extract_json')
class TestDirectMessengerSendRequestInternal:
    """Focused tests for the _send_request internal method."""

    @pytest.fixture
    def messenger_for_send_request_tests(self):
        """Fixture for a messenger instance for _send_request tests."""
        with patch.object(DirectMessenger, '_connect_and_authenticate',
                          MagicMock()):
            messenger = DirectMessenger(TEST_SERVER, TEST_USER, TEST_PASS)
            messenger.client_socket = MagicMock()
            return messenger

    def test_send_request_basic_flow(self, mock_extract_json,
                                     messenger_for_send_request_tests):
        """Test basic successful flow of _send_request."""
        messenger = messenger_for_send_request_tests
        mock_socket_instance = messenger.client_socket
        mock_socket_instance.recv.side_effect = [
            b'{"response": {"type": "ok"',
            b',"message":"test"}}\r\n'
        ]

        expected_response_obj = ServerResponse(
            type='ok', message='test', token=None, messages=None
        )
        mock_extract_json.return_value = expected_response_obj

        test_json_request = '{"test": "request"}'
        response = messenger._send_request(test_json_request)

        mock_socket_instance.sendall.assert_called_once_with(
            (test_json_request + "\r\n").encode('utf-8')
        )
        mock_extract_json.assert_called_once_with(
            '{"response": {"type": "ok","message":"test"}}'
        )
        assert response == expected_response_obj

    def test_send_request_socket_timeout_on_send(
            self, mock_extract_json_unused, messenger_for_send_request_tests):
        """Test _send_request handling of socket timeout during send."""
        messenger = messenger_for_send_request_tests
        mock_socket_instance = messenger.client_socket
        mock_socket_instance.sendall.side_effect = socket.timeout("Send timed out")

        response = messenger._send_request('{"test": "request"}')

        assert response.type == 'error'
        assert "timed out" in response.message.lower()

    def test_send_request_socket_error_on_send(
            self, mock_extract_json_unused, messenger_for_send_request_tests):
        """Test _send_request handling of socket error during send."""
        messenger = messenger_for_send_request_tests
        mock_socket_instance = messenger.client_socket
        mock_socket_instance.sendall.side_effect = socket.error("Connection reset")

        response = messenger._send_request('{"test": "request"}')

        assert response.type == 'error'
        assert "socket error" in response.message.lower()
        assert "connection reset" in response.message.lower()

    def test_send_request_connection_closed_on_recv(
            self, mock_extract_json_unused, messenger_for_send_request_tests):
        """Test _send_request handling of connection closed during receive."""
        messenger = messenger_for_send_request_tests
        mock_socket_instance = messenger.client_socket
        mock_socket_instance.recv.return_value = b''  # Simulate server close

        response = messenger._send_request('{"test": "request"}')

        assert response.type == 'error'
        assert "connection closed by server" in response.message.lower()

    def test_send_request_no_socket(
            self, mock_extract_json_unused, messenger_for_send_request_tests):
        """Test _send_request when client_socket is None."""
        messenger = messenger_for_send_request_tests
        messenger.client_socket = None  # No socket
        response = messenger._send_request('{"test": "request"}')
        assert response.type == 'error'
        assert "socket not connected" in response.message.lower()


```

```
