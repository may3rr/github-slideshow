import pytest
import os
import json
import shutil # For robust directory removal
from ds_profile import DSProfile, ProfileError # Assuming ProfileError might be useful for future tests

TEST_PROFILE_DIR = "_test_dsu_files"

@pytest.fixture(scope="function")
def temp_dsu_dir():
    """Create a temporary directory for DSU files and clean up afterwards."""
    if os.path.exists(TEST_PROFILE_DIR):
        shutil.rmtree(TEST_PROFILE_DIR) # Clean up from previous failed run if any
    os.makedirs(TEST_PROFILE_DIR, exist_ok=True)
    yield TEST_PROFILE_DIR
    # Teardown: remove the directory and its contents
    if os.path.exists(TEST_PROFILE_DIR):
        shutil.rmtree(TEST_PROFILE_DIR)

class TestDSProfileInitLoad:
    def test_new_profile_creation(self, temp_dsu_dir):
        profile = DSProfile("user1", directory=temp_dsu_dir)
        assert profile.username == "user1"
        expected_filepath = os.path.join(temp_dsu_dir, "user1.dsu")
        assert profile.filepath == expected_filepath
        assert profile.contacts == set()
        assert profile.messages == {}
        assert not os.path.exists(expected_filepath), "DSU file should not exist for a new profile until save."

    def test_load_existing_profile(self, temp_dsu_dir):
        user_dsu_path = os.path.join(temp_dsu_dir, "user1.dsu")
        test_data = {
            "username": "user1",
            "contacts": ["contact1", "contact2"],
            "messages": {
                "contact1": [
                    {"sender": "user1", "recipient": "contact1", "message": "hello", "timestamp": 100.0},
                    {"sender": "contact1", "recipient": "user1", "message": "hi", "timestamp": 101.0}
                ],
                "contact2": [ # Unsorted
                    {"sender": "user1", "recipient": "contact2", "message": "test2", "timestamp": 201.0},
                    {"sender": "contact2", "recipient": "user1", "message": "test1", "timestamp": 200.0}
                ],
                "contact3_empty_msgs": [] # Test contact with no messages
            }
        }
        with open(user_dsu_path, 'w') as f:
            json.dump(test_data, f)

        profile = DSProfile("user1", directory=temp_dsu_dir)
        assert profile.username == "user1"
        assert profile.contacts == {"contact1", "contact2"} # contact3_empty_msgs not in contacts list
        
        assert "contact1" in profile.messages
        assert len(profile.messages["contact1"]) == 2
        assert profile.messages["contact1"][0]["timestamp"] == 100.0
        assert profile.messages["contact1"][1]["timestamp"] == 101.0

        assert "contact2" in profile.messages
        assert len(profile.messages["contact2"]) == 2
        assert profile.messages["contact2"][0]["timestamp"] == 200.0 # Should be sorted on load
        assert profile.messages["contact2"][1]["timestamp"] == 201.0

        assert "contact3_empty_msgs" in profile.messages # Key exists
        assert profile.messages["contact3_empty_msgs"] == []


    def test_load_profile_file_not_found(self, temp_dsu_dir):
        profile = DSProfile("user_no_file", directory=temp_dsu_dir)
        assert profile.username == "user_no_file"
        assert profile.contacts == set()
        assert profile.messages == {}
        # No error should occur, profile remains empty

    def test_load_profile_json_decode_error(self, temp_dsu_dir, capsys):
        malformed_dsu_path = os.path.join(temp_dsu_dir, "malformed_user.dsu")
        with open(malformed_dsu_path, 'w') as f:
            f.write("{'username': 'test', 'contacts': [}") # Invalid JSON

        profile = DSProfile("malformed_user", directory=temp_dsu_dir)
        assert profile.username == "malformed_user"
        assert profile.contacts == set(), "Contacts should be empty after a load error."
        assert profile.messages == {}, "Messages should be empty after a load error."
        # Current DSProfile prints error and continues with empty.
        # If it were to raise ProfileError, we'd use pytest.raises here.
        # For now, we can check capsys if we want to assert the print.

    def test_init_empty_username(self):
        with pytest.raises(ValueError, match="Username cannot be empty."):
            DSProfile("", directory=".")


class TestDSProfileSave:
    def test_save_profile_creates_and_updates_file(self, temp_dsu_dir):
        profile = DSProfile("user2", directory=temp_dsu_dir)
        profile_path = profile.filepath

        # Initial state: add data, implicit save via add_contact/add_message
        profile.add_contact("contactA")
        profile.add_message("user2", "contactA", "msg1_unsorted", 200.0, "contactA")
        profile.add_message("user2", "contactA", "msg0_unsorted", 100.0, "contactA") # Add out of order

        # Explicit save (though add_message already saves)
        profile.save_profile() 
        assert os.path.exists(profile_path)

        with open(profile_path, 'r') as f:
            data_on_disk = json.load(f)
        
        assert data_on_disk["username"] == "user2"
        assert data_on_disk["contacts"] == ["contactA"] # Sorted list
        assert "contactA" in data_on_disk["messages"]
        assert len(data_on_disk["messages"]["contactA"]) == 2
        assert data_on_disk["messages"]["contactA"][0]["timestamp"] == 100.0 # Check sorted
        assert data_on_disk["messages"]["contactA"][1]["timestamp"] == 200.0

        # Modify profile, save again
        profile.add_contact("contactB") # This also calls save_profile
        profile.add_message("user2", "contactB", "msg_b1", 300.0, "contactB")
        # Explicit save again if needed, but add_message/add_contact handle it
        # profile.save_profile() 

        with open(profile_path, 'r') as f:
            updated_data_on_disk = json.load(f)
        
        assert updated_data_on_disk["username"] == "user2"
        assert updated_data_on_disk["contacts"] == ["contactA", "contactB"] # Sorted
        assert "contactB" in updated_data_on_disk["messages"]
        assert updated_data_on_disk["messages"]["contactB"][0]["timestamp"] == 300.0


class TestDSProfileContacts:
    def test_add_new_contact(self, temp_dsu_dir):
        profile = DSProfile("user_c1", directory=temp_dsu_dir)
        result = profile.add_contact("new_contact")
        assert result is True
        assert "new_contact" in profile.contacts
        assert "new_contact" in profile.messages # Message list should be initialized
        assert profile.messages["new_contact"] == []
        
        # Verify DSU file content
        with open(profile.filepath, 'r') as f:
            data = json.load(f)
        assert "new_contact" in data["contacts"]

    def test_add_existing_contact(self, temp_dsu_dir):
        profile = DSProfile("user_c2", directory=temp_dsu_dir)
        profile.add_contact("existing_contact")
        result = profile.add_contact("existing_contact")
        assert result is False
        assert len(profile.contacts) == 1

    def test_add_self_as_contact(self, temp_dsu_dir):
        profile = DSProfile("user_c3", directory=temp_dsu_dir)
        result = profile.add_contact("user_c3")
        assert result is False
        assert "user_c3" not in profile.contacts

    def test_add_empty_contact_name(self, temp_dsu_dir):
        profile = DSProfile("user_c4", directory=temp_dsu_dir)
        result = profile.add_contact("")
        assert result is False
        assert "" not in profile.contacts
        
    def test_get_contacts_empty_and_populated(self, temp_dsu_dir):
        profile = DSProfile("user_c5", directory=temp_dsu_dir)
        assert profile.get_contacts() == []
        
        profile.add_contact("c")
        profile.add_contact("a")
        profile.add_contact("b")
        assert profile.get_contacts() == ['a', 'b', 'c']


class TestDSProfileMessages:
    def test_add_message_new_contact_key(self, temp_dsu_dir):
        profile = DSProfile("user_m1", directory=temp_dsu_dir)
        # Add message for a contact_key that isn't in profile.contacts yet
        profile.add_message("user_m1", "contact_key1", "hello", 100.0, "contact_key1")
        
        assert "contact_key1" not in profile.contacts, "add_message should not add to contacts set"
        assert "contact_key1" in profile.messages
        assert len(profile.messages["contact_key1"]) == 1
        assert profile.messages["contact_key1"][0]["message"] == "hello"
        
        # Verify DSU file content
        with open(profile.filepath, 'r') as f:
            data = json.load(f)
        assert "contact_key1" in data["messages"]
        assert data["contacts"] == [], "Contacts list in DSU should be empty"

    def test_add_multiple_messages_sorting(self, temp_dsu_dir):
        profile = DSProfile("user_m2", directory=temp_dsu_dir)
        profile.add_message("user_m2", "contact1", "msg2", 200.0, "contact1")
        profile.add_message("user_m2", "contact1", "msg1", 100.0, "contact1")
        profile.add_message("user_m2", "contact1", "msg3", 300.0, "contact1")
        
        assert len(profile.messages["contact1"]) == 3
        assert profile.messages["contact1"][0]["timestamp"] == 100.0
        assert profile.messages["contact1"][1]["timestamp"] == 200.0
        assert profile.messages["contact1"][2]["timestamp"] == 300.0

        # Verify DSU file content reflects sorted order
        with open(profile.filepath, 'r') as f:
            data = json.load(f)
        assert data["messages"]["contact1"][0]["timestamp"] == 100.0
        assert data["messages"]["contact1"][1]["timestamp"] == 200.0
        assert data["messages"]["contact1"][2]["timestamp"] == 300.0

    def test_get_messages_for_contact(self, temp_dsu_dir):
        profile = DSProfile("user_m3", directory=temp_dsu_dir)
        profile.add_message("user_m3", "contactX", "msgA", 10.0, "contactX")
        profile.add_message("user_m3", "contactX", "msgB", 20.0, "contactX")

        messages_contactX = profile.get_messages("contactX")
        assert len(messages_contactX) == 2
        assert messages_contactX[0]["message"] == "msgA"
        assert messages_contactX[1]["message"] == "msgB"
        
        # Test it's a copy
        messages_contactX.append({"test": "mutation"})
        assert len(profile.messages["contactX"]) == 2, "get_messages should return a copy"

        assert profile.get_messages("non_existent_contact") == []

    def test_get_all_messages_empty(self, temp_dsu_dir):
        profile = DSProfile("user_m4", directory=temp_dsu_dir)
        assert profile.get_all_message_dicts_sorted() == []

    def test_get_all_messages_populated_and_sorted(self, temp_dsu_dir):
        profile = DSProfile("user_m5", directory=temp_dsu_dir)
        # Add messages for contact1
        profile.add_message("user_m5", "contact1", "c1_msg2", 20.0, "contact1")
        profile.add_message("user_m5", "contact1", "c1_msg1", 10.0, "contact1")
        # Add messages for contact2
        profile.add_message("user_m5", "contact2", "c2_msg2", 25.0, "contact2")
        profile.add_message("user_m5", "contact2", "c2_msg1", 5.0, "contact2")

        all_messages = profile.get_all_message_dicts_sorted()
        assert len(all_messages) == 4
        assert all_messages[0]["timestamp"] == 5.0
        assert all_messages[1]["timestamp"] == 10.0
        assert all_messages[2]["timestamp"] == 20.0
        assert all_messages[3]["timestamp"] == 25.0

        assert all_messages[0]["message"] == "c2_msg1"
        assert all_messages[1]["message"] == "c1_msg1"
        assert all_messages[2]["message"] == "c1_msg2"
        # Note: Original manual test data for all_messages[3] was "c2_msg1",
        # but based on timestamp 25.0, it should be "c2_msg2".
        assert all_messages[3]["message"] == "c2_msg2"

```
# Ensure a single newline at the end of the file.
