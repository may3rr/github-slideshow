import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Frame, Label, Entry, Button, Toplevel, scrolledtext
from ds_messenger import DirectMessenger, AuthenticationError, ServerConnectionError, DirectMessage # Import DirectMessage for type hint
from ds_profile import DSProfile 
import os

class DirectMessageApp:
    def __init__(self, root_tk: tk.Tk):
        self.root = root_tk
        self.root.title("ICS 32 Distributed Social Messenger - Login") # Initial title
        
        self.direct_messenger: DirectMessenger | None = None
        self.current_recipient: str | None = None
        self.after_id: str | None = None
        self.server_unreachable: bool = False # Flag for server connection status

        # UI Elements that need to be accessed by multiple methods
        self.contacts_tree: ttk.Treeview | None = None
        self.message_display: scrolledtext.ScrolledText | None = None
        self.message_input: ttk.Entry | None = None
        self.send_button: ttk.Button | None = None

        # Hide the main window until login is successful
        self.root.withdraw()
        self._show_login_window()

    def _center_window(self, window: tk.Toplevel | tk.Tk, width: int = 300, height: int = 200):
        """Helper function to center a window on the screen."""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def _on_login_window_close(self):
        """Handles the event when the login window is closed directly."""
        # If login window is closed, exit the application as login is mandatory.
        self.root.destroy() 

    def _show_login_window(self):
        self.login_window = Toplevel(self.root)
        self.login_window.title("Login")
        
        # Make login window modal
        self.login_window.grab_set()
        self.login_window.transient(self.root) # Usually makes it stay on top of its parent

        # Handle login window close button
        self.login_window.protocol("WM_DELETE_WINDOW", self._on_login_window_close)

        login_frame = Frame(self.login_window, padx=20, pady=20)
        login_frame.pack(expand=True, fill=tk.BOTH)

        Label(login_frame, text="Server Address:").grid(row=0, column=0, sticky="w", pady=5)
        self.server_entry = Entry(login_frame, width=30)
        self.server_entry.insert(0, "127.0.0.1") # Default server
        self.server_entry.grid(row=0, column=1, pady=5)

        Label(login_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=5)
        self.username_entry = Entry(login_frame, width=30)
        self.username_entry.grid(row=1, column=1, pady=5)

        Label(login_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=5)
        self.password_entry = Entry(login_frame, width=30, show='*')
        self.password_entry.grid(row=2, column=1, pady=5)

        self.login_button = Button(login_frame, text="Login", command=self._handle_login, width=10)
        self.login_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Set focus to username entry initially for convenience
        self.username_entry.focus_set()

        # Bind Enter key to login button
        self.login_window.bind('<Return>', lambda event: self._handle_login())

        self._center_window(self.login_window, 350, 200)


    def _handle_login(self):
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get() # No strip for password

        if not server:
            messagebox.showerror("Login Error", "Server address cannot be empty.", parent=self.login_window)
            return
        if not username:
            messagebox.showerror("Login Error", "Username cannot be empty.", parent=self.login_window)
            return
        if not password: # Password can technically be empty by some standards, but usually not for auth
            messagebox.showerror("Login Error", "Password cannot be empty.", parent=self.login_window)
            return

        try:
            # Disable login button during attempt
            self.login_button.config(state=tk.DISABLED, text="Logging in...")
            self.login_window.update_idletasks() # Ensure UI updates

            dm_instance = DirectMessenger(dsuserver=server, username=username, password=password)
            self.direct_messenger = dm_instance
            
            # If login is successful
            self.login_window.destroy()
            self.root.deiconify() # Show the main application window
            self._center_window(self.root, 800, 600) # Center main window
            self._setup_main_chat_ui()

        except AuthenticationError:
            messagebox.showerror("Login Failed", "Invalid username or password.", parent=self.login_window)
        except ServerConnectionError as sce:
            messagebox.showerror("Login Failed", f"Could not connect to the server: {sce}", parent=self.login_window)
        except ValueError as ve: # Catch potential ValueErrors from DirectMessenger init (e.g. empty user/pass if not caught above)
             messagebox.showerror("Login Error", str(ve), parent=self.login_window)
        except Exception as e:
            messagebox.showerror("Login Error", f"An unexpected error occurred: {str(e)}", parent=self.login_window)
        finally:
            # Re-enable login button if login window still exists
            if self.login_window and self.login_window.winfo_exists():
                self.login_button.config(state=tk.NORMAL, text="Login")


    def _setup_main_chat_ui(self):
        # This is a placeholder for the next subtask.
        # For now, just add a label to confirm login.
        print(f"Login successful for {self.direct_messenger.username}. Main UI setup pending.")
        Label(self.root, text=f"Welcome, {self.direct_messenger.username}! Chat UI coming soon.").pack(padx=20, pady=20)
        # In a real app, we'd build out frames for contacts, messages, entry, etc. here.
        self.root.title(f"ICS 32 Messenger - {self.direct_messenger.username}")

        # --- Main Layout ---
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left Frame for Contacts
        left_frame = ttk.Frame(main_paned_window, width=200)
        main_paned_window.add(left_frame, weight=1) # Weight makes it resizable

        # Right Frame for Messages and Input
        right_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(right_frame, weight=3) # Weight makes it resizable

        # --- Contacts List (Left Frame) ---
        self.contacts_tree = ttk.Treeview(left_frame, selectmode="browse")
        self.contacts_tree['columns'] = ('username',)
        self.contacts_tree.column("#0", width=0, stretch=tk.NO) # Hide the default #0 column
        self.contacts_tree.column('username', anchor='w', width=180)
        self.contacts_tree.heading('username', text='Contacts', anchor='w')
        self.contacts_tree["show"] = "headings" # Show only defined headings
        self.contacts_tree.tag_configure('unread', font=('TkDefaultFont', 9, 'bold')) # Default font, size 9, bold

        contacts_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.contacts_tree.yview)
        self.contacts_tree.configure(yscrollcommand=contacts_scrollbar.set)
        
        self.contacts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        contacts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.contacts_tree.bind('<<TreeviewSelect>>', self._on_contact_select)
        self._load_and_display_contacts()

        # --- Right Frame Layout (Messages and Input) ---
        right_paned_window = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned_window.pack(fill=tk.BOTH, expand=True)

        # Top Right Frame for Message Display
        top_right_frame = ttk.Frame(right_paned_window, height=400)
        right_paned_window.add(top_right_frame, weight=4)

        # Bottom Right Frame for Message Input
        bottom_right_frame = ttk.Frame(right_paned_window, height=100)
        right_paned_window.add(bottom_right_frame, weight=1)
        bottom_right_frame.grid_columnconfigure(0, weight=1) # Make entry resizable


        # --- Message Display Area (Top Right Frame) ---
        self.message_display = scrolledtext.ScrolledText(top_right_frame, wrap=tk.WORD, state='disabled', font=("Helvetica", 10))
        self.message_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.message_display.tag_configure('sent', justify='right', foreground='#007bff', font=("Helvetica", 10, "bold")) # Blue
        self.message_display.tag_configure('received', justify='left', foreground='#28a745', font=("Helvetica", 10)) # Green
        self.message_display.tag_configure('system', justify='center', foreground='gray', font=("Helvetica", 9, "italic"))


        # --- Message Input and Send Button (Bottom Right Frame) ---
        self.message_input = ttk.Entry(bottom_right_frame, width=60, font=("Helvetica", 10))
        self.message_input.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.message_input.bind("<Return>", self._send_message)
        self.message_input.config(state=tk.DISABLED)

        self.send_button = ttk.Button(bottom_right_frame, text="Send", command=self._send_message)
        self.send_button.grid(row=0, column=1, padx=5, pady=10, sticky="e")
        self.send_button.config(state=tk.DISABLED)

        # --- Menu ---
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Add Contact", command=self._add_contact_dialog)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self._on_closing) # Use _on_closing for cleanup
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # --- Periodic Check & Closing Protocol ---
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._periodic_message_check() # Start the check

    def _load_and_display_contacts(self):
        if not self.contacts_tree or not self.direct_messenger:
            return

        # Clear existing items
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)

        contacts = self.direct_messenger.get_local_contacts() # This gets from DSProfile
        if not contacts:
            # self.contacts_tree.insert('', 'end', values=("No contacts yet.",)) # Placeholder
            pass # Or simply show an empty list
        else:
            for contact_username in contacts:
                self.contacts_tree.insert('', 'end', iid=contact_username, values=(contact_username,))

    def _on_contact_select(self, event=None): # event can be None if called manually
        if not self.contacts_tree: return
        selected_items = self.contacts_tree.selection()
        if selected_items:
            selected_iid = selected_items[0] # First selected item's iid
            # The iid is the contact_username we stored
            self.current_recipient = selected_iid 
            
            if self.message_input: self.message_input.config(state=tk.NORMAL)
            if self.send_button: self.send_button.config(state=tk.NORMAL)
            if self.message_input: self.message_input.delete(0, tk.END) # Clear previous input
            if self.message_input: self.message_input.focus_set()

            self._display_conversation(self.current_recipient)
            # Remove 'unread' tag when contact is selected
            self.contacts_tree.item(selected_iid, tags=())
        else:
            self.current_recipient = None
            if self.message_input: self.message_input.config(state=tk.DISABLED)
            if self.send_button: self.send_button.config(state=tk.DISABLED)
            # Clear message display if no contact is selected
            if self.message_display:
                self.message_display.config(state='normal')
                self.message_display.delete('1.0', tk.END)
                self.message_display.insert(tk.END, "Select a contact to view messages.", 'system')
                self.message_display.config(state='disabled')


    def _display_conversation(self, contact_username: str):
        if not self.message_display or not self.direct_messenger:
            return

        self.message_display.config(state='normal')
        self.message_display.delete('1.0', tk.END)

        messages: list[DirectMessage] = self.direct_messenger.get_local_messages(contact_username)
        
        if not messages:
            self.message_display.insert(tk.END, f"No messages with {contact_username} yet.", 'system')
        else:
            for msg in messages:
                tag_to_use = 'sent' if msg.sender == self.direct_messenger.username else 'received'
                # Simple formatting, could be improved (e.g., timestamps)
                # For now, just showing the message text with sender context from tag
                prefix = "You: " if tag_to_use == 'sent' else f"{msg.sender}: "
                self.message_display.insert(tk.END, f"{prefix}{msg.message}\n\n", tag_to_use)
        
        self.message_display.config(state='disabled')
        self.message_display.see(tk.END) # Scroll to the end

    def _send_message(self, event=None): # event is for Return key binding
        if not self.current_recipient or not self.message_input or not self.direct_messenger:
            return
        
        if self.server_unreachable:
            messagebox.showerror("Server Unreachable", "Cannot send message. Server is currently unreachable.", parent=self.root)
            return

        message_text = self.message_input.get().strip()
        if not message_text:
            return # Don't send empty messages

        try:
            if self.direct_messenger.send(message_text, self.current_recipient):
                self.message_input.delete(0, tk.END)
                # The message is saved to profile by messenger.send()
                # Re-displaying the conversation will pick it up from local store.
                self._display_conversation(self.current_recipient) 
            else:
                # This 'else' block might be hit if send returns False for reasons other than connection (e.g., recipient unknown by server)
                messagebox.showerror("Send Error", "Failed to send message. Recipient may not exist or server declined.", parent=self.root)
        except ServerConnectionError: # Explicitly catch if send itself raises this
            self.server_unreachable = True
            if self.send_button: self.send_button.config(state=tk.DISABLED)
            messagebox.showerror("Send Error", "Failed to send message. Server connection lost.", parent=self.root)
            # Optionally, stop periodic checks here too if desired, or let periodic check handle it.
        except Exception as e:
            messagebox.showerror("Send Error", f"An unexpected error occurred: {str(e)}", parent=self.root)


    def _add_contact_dialog(self):
        if not self.direct_messenger: return

        new_contact_username = simpledialog.askstring("Add Contact", "Enter username:", parent=self.root)
        if new_contact_username:
            new_contact_username = new_contact_username.strip()
            if not new_contact_username:
                messagebox.showerror("Add Contact Error", "Username cannot be empty.", parent=self.root)
                return
            if new_contact_username == self.direct_messenger.username:
                messagebox.showerror("Add Contact Error", "You cannot add yourself as a contact.", parent=self.root)
                return

            if self.direct_messenger.profile: # Check if profile exists
                if self.direct_messenger.profile.add_contact(new_contact_username):
                    messagebox.showinfo("Add Contact", f"Contact '{new_contact_username}' added successfully.", parent=self.root)
                    self._load_and_display_contacts()
                    # Optionally, select the new contact
                    if self.contacts_tree:
                        self.contacts_tree.selection_set(new_contact_username) # Selects by iid
                        # _on_contact_select will be triggered
                else:
                    # Could be already existing or some other reason add_contact returns False
                    messagebox.showwarning("Add Contact", f"Contact '{new_contact_username}' may already exist or could not be added.", parent=self.root)
            else:
                messagebox.showerror("Profile Error", "User profile is not available. Cannot add contact.", parent=self.root)


    def _periodic_message_check(self):
        if not self.direct_messenger:
            # If messenger is not even initialized (e.g. login failed and somehow we got here), stop.
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            return

        try:
            # retrieve_new() in DirectMessenger saves messages to profile and returns list of DirectMessage objects
            new_messages: list[DirectMessage] = self.direct_messenger.retrieve_new()

            if self.server_unreachable: # If connection was previously lost but now succeeded
                self.server_unreachable = False
                if self.send_button: self.send_button.config(state=tk.NORMAL if self.current_recipient else tk.DISABLED)
                messagebox.showinfo("Connection Restored", "Server connection has been restored.", parent=self.root)
                # Potentially refresh contacts if they might have changed during outage
                self._load_and_display_contacts()


            if new_messages:
                updated_contacts = set()
                for msg in new_messages:
                    # retrieve_new is for incoming, so msg.sender is the contact
                    if msg.sender: 
                        updated_contacts.add(msg.sender)

                if self.current_recipient and self.current_recipient in updated_contacts:
                    self._display_conversation(self.current_recipient)
                    # Current conversation was updated, so this contact's 'unread' status is handled.
                    # Remove from updated_contacts to avoid re-tagging if it was already selected.
                    updated_contacts.discard(self.current_recipient) 
                
                if self.contacts_tree:
                    for contact_iid in updated_contacts: # Remaining contacts that got new messages
                        if self.contacts_tree.exists(contact_iid): # Check if contact is in tree
                             # Ensure it's not the current recipient if somehow still in set
                            if contact_iid != self.current_recipient:
                                self.contacts_tree.item(contact_iid, tags=('unread',))

        except ServerConnectionError:
            if not self.server_unreachable: # Show warning only once
                self.server_unreachable = True
                if self.send_button: self.send_button.config(state=tk.DISABLED)
                messagebox.showwarning("Server Connection Lost", 
                                       "Could not connect to the server. New messages cannot be retrieved. Sending is disabled.", 
                                       parent=self.root)
            # Optionally, stop periodic checks after several failures or immediately
            # For now, we'll let it keep trying, but it won't show repeated warnings.
        except Exception as e:
            print(f"Error during periodic message check: {e}") # Log other errors
        
        # Schedule next check only if the root window still exists
        if self.root.winfo_exists():
            self.after_id = self.root.after(5000, self._periodic_message_check) # Check every 5 seconds

    def _on_closing(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        if self.direct_messenger:
            try:
                self.direct_messenger.close_connection()
            except Exception as e:
                print(f"Error closing DirectMessenger connection: {e}")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DirectMessageApp(root)
    root.mainloop()

# Ensuring a final newline for linters.
```
