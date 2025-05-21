import json
import os

class ProfileError(Exception):
    """Custom exception for profile-related errors."""
    pass

class DSProfile:
    """
    Manages user profile data including contacts and messages,
    persisting them to a .dsu file.
    """

    def __init__(self, username: str, directory: str = "."):
        """
        Initializes a DSProfile instance.

        Args:
            username: The username for the profile.
            directory: The directory where the profile file will be stored.
        """
        if not username:
            raise ValueError("Username cannot be empty.")
        self.username = username
        self.filepath = os.path.join(directory, f"{username}.dsu")
        self.contacts: set[str] = set()
        self.messages: dict[str, list[dict]] = {}  # Key: contact_username, Value: list of message dicts

        self.load_profile()

    def _sort_messages_for_contact(self, contact_key: str):
        """Helper to sort messages for a specific contact by timestamp."""
        if contact_key in self.messages:
            self.messages[contact_key].sort(key=lambda msg: msg.get('timestamp', 0))

    def _sort_all_messages(self):
        """Helper to sort messages for all contacts."""
        for contact_key in self.messages:
            self._sort_messages_for_contact(contact_key)

    def load_profile(self):
        """
        Loads the user's profile data from the .dsu file.
        If the file does not exist, assumes a new profile.
        Handles JSON decoding errors and other OS errors.
        """
        try:
            if not os.path.exists(self.filepath):
                # New profile, nothing to load.
                # Ensure directory exists if we were to save immediately,
                # but load doesn't create it.
                return

            with open(self.filepath, 'r') as f:
                data = json.load(f)
            
            self.contacts = set(data.get('contacts', []))
            self.messages = data.get('messages', {})
            self._sort_all_messages() # Ensure messages are sorted after loading

        except FileNotFoundError:
            # This case is technically covered by os.path.exists, but good for robustness
            return # New profile
        except json.JSONDecodeError:
            # print(f"Error: Could not decode JSON from profile file: {self.filepath}. Initializing empty profile.")
            # Initialize with empty to prevent data corruption from a bad file.
            self.contacts = set()
            self.messages = {}
            # Optionally, raise ProfileError("Failed to decode profile data.")
        except OSError as e:
            # print(f"Error: Could not read profile file {self.filepath}: {e}. Initializing empty profile.")
            self.contacts = set()
            self.messages = {}
            # Optionally, raise ProfileError(f"OS error while loading profile: {e}")
        except Exception as e: # Catch-all for other unexpected errors during load
            # print(f"An unexpected error occurred while loading profile: {e}. Initializing empty profile.")
            self.contacts = set()
            self.messages = {}
            # Optionally, raise ProfileError(f"Unexpected error loading profile: {e}")


    def save_profile(self):
        """
        Saves the current profile data (username, contacts, messages) to the .dsu file.
        Contacts are saved as a sorted list. Messages for each contact are sorted by timestamp.
        """
        # Ensure the directory exists
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        except OSError as e:
            # print(f"Error: Could not create directory for profile file {self.filepath}: {e}")
            # raise ProfileError(f"Could not create directory for profile: {e}")
            return # Or raise error

        # Ensure messages are sorted before saving
        self._sort_all_messages()

        data = {
            'username': self.username,
            'contacts': sorted(list(self.contacts)),
            'messages': self.messages # Already sorted by _sort_all_messages
        }

        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=4) # Use indent for readability
        except OSError as e:
            # print(f"Error: Could not write profile file {self.filepath}: {e}")
            # raise ProfileError(f"OS error while saving profile: {e}")
            pass # Or raise
        except Exception as e:
            # print(f"An unexpected error occurred while saving profile: {e}")
            # raise ProfileError(f"Unexpected error saving profile: {e}")
            pass # Or raise

    def add_contact(self, contact_username: str) -> bool:
        """
        Adds a contact to the profile.

        Args:
            contact_username: The username of the contact to add.

        Returns:
            True if a new contact was added, False otherwise (e.g., contact already exists or is self).
        """
        if not contact_username or contact_username == self.username:
            return False
        
        if contact_username not in self.contacts:
            self.contacts.add(contact_username)
            if contact_username not in self.messages: # Initialize message list for new contact
                self.messages[contact_username] = []
            self.save_profile()
            return True
        
        # If contact exists, but maybe not message list (though unlikely with current logic)
        if contact_username not in self.messages:
             self.messages[contact_username] = []
             self.save_profile() # Save if we modified messages dict
        return False # Contact already existed

    def get_contacts(self) -> list[str]:
        """
        Returns a sorted list of contact usernames.
        """
        return sorted(list(self.contacts))

    def add_message(self, sender: str, recipient: str, message_text: str, timestamp: float, contact_username_key: str):
        """
        Adds a message to the profile, associated with a specific contact key.

        Args:
            sender: The username of the message sender.
            recipient: The username of the message recipient.
            message_text: The content of the message.
            timestamp: The timestamp of the message.
            contact_username_key: The key in self.messages dictionary (usually the other user).
        """
        if not contact_username_key:
            # print("Error: contact_username_key cannot be empty for add_message.")
            return

        msg_dict = {
            'sender': sender,
            'recipient': recipient,
            'message': message_text,
            'timestamp': timestamp
        }

        if contact_username_key not in self.messages:
            self.messages[contact_username_key] = []
        
        # Avoid duplicate messages if re-adding (simple check by content and timestamp)
        # More robust would be a unique message ID
        # For now, let's assume timestamps are sufficiently unique for ordering and duplicates are allowed by spec
        # if msg_dict not in self.messages[contact_username_key]:
        self.messages[contact_username_key].append(msg_dict)
        self._sort_messages_for_contact(contact_username_key)
        self.save_profile()

    def get_messages(self, contact_username_key: str) -> list[dict]:
        """
        Retrieves all messages associated with a specific contact key, sorted by timestamp.

        Args:
            contact_username_key: The key for the contact in the messages dictionary.

        Returns:
            A copy of the list of message dictionaries, or an empty list if no messages.
        """
        # Sorting is guaranteed by add_message and load_profile
        return list(self.messages.get(contact_username_key, [])) # Return a copy

    def get_all_message_dicts_sorted(self) -> list[dict]:
        """
        Collects all message dictionaries from all contacts, flattens them,
        and returns a single list sorted by timestamp.
        """
        all_msgs = []
        for contact_key in self.messages:
            all_msgs.extend(self.messages[contact_key])
        
        all_msgs.sort(key=lambda msg: msg.get('timestamp', 0))
        return all_msgs

    def delete_profile_file(self) -> bool:
        """
        Deletes the profile .dsu file. Used primarily for testing or reset.
        Returns True if successful or file didn't exist, False on error.
        """
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            return True
        except OSError:
            # print(f"Error deleting profile file {self.filepath}: {e}")
            return False

if __name__ == '__main__':
    # Example Usage (Optional, for quick testing)
    # Create a temporary directory for testing
    test_dir = "_test_profiles"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    # Test user 1
    user1_profile = DSProfile(username="user1", directory=test_dir)
    user1_profile.add_contact("user2")
    user1_profile.add_contact("user3")
    
    # Add messages for user2
    user1_profile.add_message("user1", "user2", "Hello User2 from User1!", 1600000000.0, "user2")
    user1_profile.add_message("user2", "user1", "Hi User1 from User2!", 1600000001.0, "user2")
    user1_profile.add_message("user1", "user2", "How are you?", 1600000002.0, "user2")

    # Add messages for user3 (out of order timestamp to test sorting)
    user1_profile.add_message("user3", "user1", "Hey User1!", 1600000005.0, "user3")
    user1_profile.add_message("user1", "user3", "Greetings User3!", 1600000003.0, "user3")


    print(f"User1 Contacts: {user1_profile.get_contacts()}")
    print(f"User1 Messages with User2: {user1_profile.get_messages('user2')}")
    print(f"User1 Messages with User3: {user1_profile.get_messages('user3')}")
    
    # Test loading
    user1_loaded_profile = DSProfile(username="user1", directory=test_dir)
    print(f"\nLoaded User1 Contacts: {user1_loaded_profile.get_contacts()}")
    assert set(user1_profile.get_contacts()) == set(user1_loaded_profile.get_contacts())
    
    print(f"Loaded User1 Messages with User2: {user1_loaded_profile.get_messages('user2')}")
    assert len(user1_loaded_profile.get_messages('user2')) == 3
    assert user1_loaded_profile.get_messages('user2')[0]['timestamp'] == 1600000000.0

    print(f"Loaded User1 Messages with User3: {user1_loaded_profile.get_messages('user3')}")
    assert len(user1_loaded_profile.get_messages('user3')) == 2
    assert user1_loaded_profile.get_messages('user3')[0]['timestamp'] == 1600000003.0 # Check sort

    print(f"\nAll messages for User1 sorted: {user1_loaded_profile.get_all_message_dicts_sorted()}")
    all_msgs = user1_loaded_profile.get_all_message_dicts_sorted()
    assert len(all_msgs) == 5
    assert all_msgs[0]['timestamp'] == 1600000000.0
    assert all_msgs[-1]['timestamp'] == 1600000005.0

    # Test user 2 (new profile)
    user2_profile = DSProfile(username="user2", directory=test_dir)
    print(f"\nUser2 Contacts (new profile): {user2_profile.get_contacts()}")
    assert user2_profile.get_contacts() == []

    # Clean up test files
    # user1_profile.delete_profile_file()
    # user2_profile.delete_profile_file()
    # if os.path.exists(test_dir):
    #     import shutil
    #     shutil.rmtree(test_dir)
    print("\nDSProfile example usage complete.")
