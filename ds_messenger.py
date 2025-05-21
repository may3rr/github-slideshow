"""
Handles direct messaging communication with a DS server, including authentication,
sending, and retrieving messages, and integrates with a local profile for
persistent storage.
"""
import socket
import time
from typing import List, Optional, Any, Dict

from ds_protocol import (
    format_authenticate_request,
    format_directmessage_request,
    format_fetch_request,
    extract_json,
    ServerResponse
)
from ds_profile import DSProfile, ProfileError


# Custom Exception for Authentication Errors
class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    pass


# Custom Exception for Server Connection Errors
class ServerConnectionError(Exception):
    """Custom exception for server connection issues."""
    pass


class DirectMessage:
    """
    Represents a single direct message with its attributes.
    """
    def __init__(
            self, recipient: Optional[str] = None,
            sender: Optional[str] = None,
            message: Optional[str] = None,
            timestamp: Optional[float] = None):
        self.recipient = recipient
        self.sender = sender
        self.message = message
        # Ensure timestamp is float if provided, otherwise None
        try:
            self.timestamp = float(timestamp) if timestamp is not None else None
        except ValueError:
            # print(f"Warning: Could not convert timestamp '{timestamp}' to float. Setting to None.")
            self.timestamp = None  # Or raise error

    def __repr__(self) -> str:
        return (f"DirectMessage(sender='{self.sender}', "
                f"recipient='{self.recipient}', "
                f"message='{self.message}', timestamp={self.timestamp})")


class DirectMessenger:
    """
    Manages sending and receiving direct messages with a DS server,
    and stores messages locally using DSProfile.
    """
    def __init__(self, dsuserver: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None):
        self.username: Optional[str] = username
        self.password: Optional[str] = password
        self.token: Optional[str] = None
        self.dsuserver: str = dsuserver if dsuserver else "127.0.0.1"  # Default server
        self.client_socket: Optional[socket.socket] = None
        self.port: int = 3001  # Default DS server port
        self.profile: Optional[DSProfile] = None

        if not self.username or not self.password:
            raise ValueError("Username and password must be provided.")

        try:
            self._connect_and_authenticate()
            if self.token:  # If authentication was successful
                try:
                    self.profile = DSProfile(username=self.username)
                except ProfileError as pe:
                    # Allow messenger to work without profile if DSU load fails
                    print(f"Error loading profile for {self.username}: {pe}. "
                          "Profile operations will be unavailable.")
                    self.profile = None
                except Exception as e:  # Catch other unexpected DSProfile errors
                    print(f"An unexpected error occurred with profile for "
                          f"{self.username}: {e}. "
                          "Profile operations will be unavailable.")
                    self.profile = None
        except Exception as e:  # Catch any exception from _connect_and_authenticate
            self.close_connection()  # Ensure socket is closed
            raise ServerConnectionError(
                f"Failed to connect or authenticate: {e}"
            ) from e

    def _send_request(self, request_json: str) -> Optional[ServerResponse]:
        """
        Sends a pre-formatted JSON request to the server and returns the parsed response.

        Args:
            request_json: The JSON string to send.

        Returns:
            A ServerResponse object or None if a critical error occurs.
        """
        if not self.client_socket:
            return ServerResponse(type='error', message="Socket not connected.",
                                  token=None, messages=None)

        try:
            self.client_socket.sendall((request_json + "\r\n").encode('utf-8'))

            response_bytes = bytearray()
            while True:
                chunk = self.client_socket.recv(2048)
                if not chunk:
                    return ServerResponse(type='error',
                                          message="Connection closed by server.",
                                          token=None, messages=None)
                response_bytes.extend(chunk)
                if b"\r\n" in response_bytes:
                    break

            response_str = response_bytes.decode('utf-8').strip()
            return extract_json(response_str)

        except socket.timeout:
            return ServerResponse(type='error', message="Socket operation timed out.",
                                  token=None, messages=None)
        except socket.error as e:
            return ServerResponse(type='error', message=f"Socket error: {e}",
                                  token=None, messages=None)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catching general Exception for unexpected issues during send/receive.
            error_msg = f"An unexpected error occurred during request: {str(e)}"
            return ServerResponse(type='error', message=error_msg,
                                  token=None, messages=None)

    def _connect_and_authenticate(self) -> None:
        """
        Establishes a connection to the server and authenticates the user.
        Raises AuthenticationError or ServerConnectionError on failure.
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)  # Socket operation timeout
            self.client_socket.connect((self.dsuserver, self.port))
        except socket.timeout as e_timeout:
            self.client_socket = None
            raise ServerConnectionError(
                f"Connection to {self.dsuserver}:{self.port} timed out."
            ) from e_timeout
        except socket.error as e_socket:
            self.client_socket = None
            raise ServerConnectionError(
                f"Could not connect to {self.dsuserver}:{self.port}. "
                f"Error: {e_socket}"
            ) from e_socket

        auth_request = format_authenticate_request(self.username, self.password)
        response = self._send_request(auth_request)

        if response and response.type == "ok" and response.token:
            self.token = response.token
        else:
            self.close_connection()
            error_message = response.message if response else \
                "No response from server or malformed response."
            raise AuthenticationError(f"Authentication failed: {error_message}")

    def close_connection(self) -> None:
        """
        Closes the client socket if it is open and clears the token.
        """
        if self.client_socket:
            try:
                self.client_socket.close()
            except socket.error:
                pass  # Ignore errors on close
            finally:
                self.client_socket = None
        self.token = None

    def __del__(self):
        """
        Destructor to ensure the connection is closed when the object is deleted.
        """
        self.close_connection()

    def send(self, message: str, recipient: str) -> bool:
        """
        Sends a direct message to a recipient.

        Args:
            message: The content of the message.
            recipient: The username of the recipient.

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not self.token or not self.client_socket:
            return False

        timestamp = time.time()
        dm_request = format_directmessage_request(
            self.token, recipient, message, timestamp
        )
        response = self._send_request(dm_request)

        if response and response.type == "ok":
            if self.profile:
                try:
                    self.profile.add_contact(recipient)
                    self.profile.add_message(
                        sender=str(self.username),  # Ensure username is str
                        recipient=recipient,
                        message_text=message,
                        timestamp=timestamp,
                        contact_username_key=recipient
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"Error saving sent message to profile: {e}")
            return True
        return False

    def retrieve_new(self) -> List[DirectMessage]:
        """
        Retrieves all new (unread) messages from the server.
        Saves new messages to the local profile if available.

        Returns:
            A list of DirectMessage objects, or an empty list if no new
            messages or an error occurs.
        """
        if not self.token or not self.client_socket:
            return []

        fetch_request = format_fetch_request(self.token, "unread")
        response = self._send_request(fetch_request)

        messages_obj_list: List[DirectMessage] = []
        if response and response.type == "ok" and response.messages:
            for msg_data in response.messages:
                dm_sender = msg_data.get("from")
                if dm_sender is None:
                    continue  # Skip message if sender is None

                dm = DirectMessage(
                    recipient=self.username,
                    sender=dm_sender,
                    message=msg_data.get("message"),
                    timestamp=float(msg_data.get("timestamp"))
                    if msg_data.get("timestamp") is not None else None
                )
                messages_obj_list.append(dm)

                if self.profile and dm.sender and dm.timestamp is not None:
                    try:
                        self.profile.add_contact(dm.sender)
                        self.profile.add_message(
                            sender=dm.sender,
                            recipient=str(self.username),  # Ensure username is str
                            message_text=str(dm.message),  # Ensure message is str
                            timestamp=dm.timestamp,
                            contact_username_key=dm.sender
                        )
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        print(f"Error saving new message to profile: {e}")
        return messages_obj_list

    def retrieve_all(self) -> List[DirectMessage]:
        """
        Retrieves all messages (sent and received) from the server.
        Attempts to de-duplicate and save new messages to the local profile.

        Returns:
            A list of DirectMessage objects from the server, or an empty
            list if an error occurs during server fetch.
        """
        if not self.token or not self.client_socket:
            return []

        fetch_request = format_fetch_request(self.token, "all")
        response = self._send_request(fetch_request)
        server_messages_obj_list: List[DirectMessage] = []

        if response and response.type == "ok" and response.messages:
            for msg_data in response.messages:
                sender = msg_data.get("from")
                recipient_server = msg_data.get("recipient")
                timestamp_val = float(msg_data.get("timestamp")) \
                    if msg_data.get("timestamp") is not None else None
                message_text = msg_data.get("message")

                dm_obj: Optional[DirectMessage] = None
                if sender:  # Received message
                    dm_obj = DirectMessage(recipient=self.username, sender=sender,
                                           message=message_text,
                                           timestamp=timestamp_val)
                elif recipient_server:  # Sent message
                    dm_obj = DirectMessage(recipient=recipient_server,
                                           sender=self.username,
                                           message=message_text,
                                           timestamp=timestamp_val)
                if dm_obj:
                    server_messages_obj_list.append(dm_obj)
        else:
            return []  # Error fetching from server

        if self.profile:
            self._deduplicate_and_save_messages(server_messages_obj_list)

        return server_messages_obj_list

    def _deduplicate_and_save_messages(
            self, server_messages: List[DirectMessage]) -> None:
        """
        Helper to de-duplicate server messages against local profile and save new ones.

        Args:
            server_messages: A list of DirectMessage objects from the server.
        """
        if not self.profile:  # Should not happen if called from retrieve_all check
            return

        try:
            local_message_dicts = self.profile.get_all_message_dicts_sorted()
            local_msg_ids = set()
            for m_dict in local_message_dicts:
                try:
                    ts = float(m_dict['timestamp'])
                    sender = m_dict.get('sender')
                    message_content = m_dict.get('message')
                    if sender is not None and message_content is not None:
                        local_msg_ids.add((ts, sender, message_content))
                except (ValueError, TypeError, KeyError):
                    continue  # Skip malformed local message

            for dm_server in server_messages:
                if dm_server.timestamp is None or dm_server.sender is None \
                        or dm_server.message is None:
                    continue

                server_msg_id = (
                    dm_server.timestamp, dm_server.sender, dm_server.message
                )

                if server_msg_id not in local_msg_ids:
                    contact_key: Optional[str] = None
                    dm_recipient = dm_server.recipient
                    if dm_server.sender == self.username:  # Outgoing
                        contact_key = dm_recipient
                    else:  # Incoming
                        contact_key = dm_server.sender

                    if contact_key and dm_recipient is not None:
                        self.profile.add_contact(contact_key)
                        self.profile.add_message(
                            sender=dm_server.sender,
                            recipient=dm_recipient,  # Use the message's recipient
                            message_text=dm_server.message,
                            timestamp=dm_server.timestamp,
                            contact_username_key=contact_key
                        )
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error during de-duplication/saving: {e}")

    def get_local_contacts(self) -> List[str]:
        """
        Retrieves the list of contacts stored locally in the profile.
        """
        if self.profile:
            return self.profile.get_contacts()
        return []

    def get_local_messages(self, contact_username: str) -> List[DirectMessage]:
        """
        Retrieves messages for a specific contact stored locally in the profile.
        Converts message dictionaries from DSProfile into DirectMessage objects.

        Args:
            contact_username: The username of the contact.

        Returns:
            A list of DirectMessage objects.
        """
        if self.profile:
            message_dicts = self.profile.get_messages(contact_username)
            dm_list: List[DirectMessage] = []
            for msg_dict in message_dicts:
                try:
                    dm_list.append(
                        DirectMessage(
                            recipient=msg_dict.get('recipient'),
                            sender=msg_dict.get('sender'),
                            message=msg_dict.get('message'),
                            timestamp=msg_dict.get('timestamp')
                        )
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    err_msg = f"Error converting profile message: {e} - {msg_dict}"
                    print(err_msg)
            return dm_list
        return []


```
