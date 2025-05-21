# ICS 32 Distributed Social Messenger

## Project Description

This project is a direct messaging chat application developed for ICS 32. It allows users to connect to a Distributed Social Platform (DSP) server, send and receive direct messages with other users, and store conversations locally. The application features a graphical user interface built with Tkinter.

Key features include:
- User authentication.
- Sending and receiving direct messages.
- Fetching all messages or only unread messages from the server.
- Local storage of messages and contacts in a `.dsu` file per user.
- A Tkinter-based GUI with:
    - Login screen.
    - Contacts list.
    - Conversation display area with visual distinction for sent/received messages.
    - Message input and send functionality.
    - Ability to add new contacts.
    - Automatic retrieval and display of new messages.
    - Error handling for server connectivity issues.

## File Structure

The project is organized into the following main Python modules:

-   `a3.py`: The main application file that launches the Tkinter GUI and orchestrates the user interface and interaction with the messaging client.
-   `ds_protocol.py`: Handles the JSON-based communication protocol for interacting with the DSP server. It includes functions for formatting requests and parsing server responses.
-   `ds_messenger.py`: Contains the `DirectMessenger` class, which manages the connection to the DSP server, user authentication, and provides methods for sending and retrieving messages. It also integrates with `ds_profile.py` for local storage.
-   `ds_profile.py`: Implements the `DSProfile` class, responsible for creating and managing local user profiles (`.dsu` files) that store contacts and message history.
-   `server.py`: The provided DSP server program (students are not expected to modify this).

## Setup and Running the Application

### Prerequisites
- Python 3.x
- Tkinter (usually included with Python standard library)

### Running the Server
1.  Open a terminal.
2.  Navigate to the project directory.
3.  Run the server using the command:
    ```bash
    python3 server.py [port]
    ```
    If no port is specified, the server will default to port `3001`. For this assignment, it's recommended to use port `3001` as this will be used for auto-grading.
    ```bash
    python3 server.py 3001
    ```
4.  Keep this terminal window open while the server is running.

### Running the Client Application
1.  Open another terminal.
2.  Navigate to the project directory.
3.  Run the main application:
    ```bash
    python3 a3.py
    ```
4.  The login window should appear.
    -   **Server Address**: Defaults to `127.0.0.1`. You can change this if your server is running on a different IP.
    -   **Username**: Enter your desired username.
    -   **Password**: Enter your password.
5.  After logging in, the main chat interface will load.

## Development Tools (Optional)

For development, the following tools were used for linting and style checking:
-   `pycodestyle`
-   `pylint`

You can install them via pip:
```bash
pip install pycodestyle pylint
```

## Notes
- Ensure the `server.py` is running and accessible before starting the client application (`a3.py`).
- User profiles (contacts and messages) are stored locally in `.dsu` files (e.g., `username.dsu`) in the same directory where `a3.py` is run.
```
