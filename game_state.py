# This handles some of the backend stuff that the general game logic depends on
# @author: NotYourFathersLore

import sqlite3
import json

DB_FILE = 'C:/path/to/infiltr8.db'

def check_triggers(trigger_type, trigger_value, username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Find triggers matching this event
    cur.execute("""
        SELECT unlock_ip, node_data, trace_modifier FROM triggers
        WHERE trigger_type = ? AND trigger_value = ?
    """, (trigger_type, trigger_value))
    triggers = cur.fetchall()

    if not triggers:
        conn.close()
        return

    # Get user's current trace level
    cur.execute("SELECT trace_level FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()
    trace_level = user_row[0] if user_row else 0

    for row in triggers:
        unlock_ip, node_data_json, trace_modifier = row
        node_data = json.loads(node_data_json)

        # Insert node (if not already present)
        cur.execute("""
            INSERT OR IGNORE INTO nodes (ip, hostname, ports, files, file_data, security_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            unlock_ip,
            node_data.get("hostname", "unknown"),
            node_data.get("ports", ""),
            json.dumps(node_data.get("files", [])),
            json.dumps(node_data.get("file_data", {})),
            node_data.get("security_level", 1)
        ))

        # Adjust trace level
        trace_level += trace_modifier or 0

    # Update user's trace level
    cur.execute("UPDATE users SET trace_level = ? WHERE username = ?", (trace_level, username))
    conn.commit()
    conn.close()


def create_session(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Check if user exists
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing = cur.fetchone()

    if not existing:
        default_inventory = json.dumps([])
        cur.execute("""
            INSERT INTO users (username, inventory, current_ip, trace_level)
            VALUES (?, ?, ?, ?)
        """, (username, default_inventory, None, 0))
        conn.commit()

    conn.close()
    return username  # using username as session_id

def get_state(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT inventory, current_ip, trace_level, cloaked FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    inventory = json.loads(row[0]) if row[0] else []
    cloaked = "No"
    if row[3]:
        cloaked = "Yes"

    return {
        "username": username,
        "inventory": inventory,
        "connected_ip": row[1],
        "trace_level": row[2],
        "cloaked": cloaked
    }

def update_state(username, updates: dict):
    state = get_state(username)
    if not state:
        return False

    # Merge updates
    inventory = updates.get("inventory", state["inventory"])
    current_ip = updates.get("connected_ip", state["connected_ip"])
    trace_level = updates.get("trace_level", state["trace_level"])

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET inventory = ?, current_ip = ?, trace_level = ?
        WHERE username = ?
    """, (json.dumps(inventory), current_ip, trace_level, username))
    conn.commit()
    conn.close()
    return True

def cat_file(username, filename):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Get current IP and inventory
    cur.execute("SELECT current_ip, inventory FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "User not found."

    current_ip, inventory_raw = row
    inventory = json.loads(inventory_raw or "[]")

    # 1. Try current node
    cur.execute("SELECT file_data FROM nodes WHERE ip = ?", (current_ip,))
    node = cur.fetchone()

    if node and node[0]:
        try:
            node_files = json.loads(node[0])
            if filename in node_files:
                conn.close()
                check_triggers("cat", filename, username)
                return f"[{current_ip}] {filename}:\n{node_files[filename]}"
        except json.JSONDecodeError:
            pass

    # 2. Try inventory
    for file in inventory:
        if file["filename"] == filename:
            conn.close()
            return f"[inventory] {filename}:\n{file['content']}"

    conn.close()
    return f"File '{filename}' not found on {current_ip} or in inventory."

def get_available_commands():
    return {
        "help": "Show this command list.",
        "scan": "Discover visible nodes on the network.",
        "connect <ip>": "Connect to a specific IP address.",
        "ls": "List files on the currently connected node.",
        "download <filename>": "Download a file from the connected node.",
        "cat <filename>": "View the contents of a file (node or inventory).",
        "status": "Show your current session state (location, inventory, trace).",
        "whoami": "Show your current session info (username, trace, location)",
        "pivot <ip>": "Connect to an IP address adjacent to your current location",
        "Cloak": "Temporarily hides your presence from others at a cost",
        "Uncloak": "Reverses the Cloak command",
        "Spoof <username>": "Makes you look like someone you are not at a cost",
        "Unfpoof": "Reverses the Spoof command"
    }

def get_whoami(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT username, current_ip, trace_level FROM users WHERE username = ?
    """, (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "User not found."

    return f"""\
            Username: {row[0]}
            Connected IP: {row[1] or 'Not connected'}
            Trace Level: {row[2]}
            """

def pivot_to_node(username, target_ip):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Get current IP
    cur.execute("SELECT current_ip FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return "You are not connected to any node."

    current_ip = user_row[0]

    # Get neighbors of current node
    cur.execute("SELECT neighbors FROM nodes WHERE ip = ?", (current_ip,))
    node_row = cur.fetchone()
    if not node_row or not node_row[0]:
        conn.close()
        return f"{current_ip} does not support pivoting."

    neighbors = json.loads(node_row[0])
    if target_ip not in neighbors:
        conn.close()
        return f"{target_ip} is not reachable from {current_ip}."

    # Verify target node exists
    cur.execute("SELECT ip FROM nodes WHERE ip = ?", (target_ip,))
    if not cur.fetchone():
        conn.close()
        return f"Target node {target_ip} does not exist."

    # Pivot (update current_ip)
    cur.execute("UPDATE users SET current_ip = ? WHERE username = ?", (target_ip, username))
    conn.commit()
    conn.close()

    return f"Pivoted to {target_ip}."

def get_whois(target_username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Check if anyone is spoofing as this user
    cur.execute("SELECT username FROM users WHERE spoofed_as = ?", (target_username,))
    spoofed_row = cur.fetchone()
    if spoofed_row:
        # Return the spoofer’s data
        cur.execute("""
            SELECT username, current_ip, trace_level, inventory, cloaked
            FROM users WHERE username = ?
        """, (spoofed_row[0],))
    else:
        # Return normal user data
        cur.execute("""
            SELECT username, current_ip, trace_level, inventory, cloaked
            FROM users WHERE username = ?
        """, (target_username,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return f"User '{target_username}' not found."

    if row[4]:  # cloaked
        return f"User '{target_username}' not found."

    inventory = json.loads(row[3]) if row[3] else []
    return f"""\
    Username: {row[0]}
    Connected IP: {row[1] or 'Not connected'}
    Trace Level: {row[2]}
    Inventory Size: {len(inventory)}
    """

def cloak_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Ensure user exists and get current trace level
    cur.execute("SELECT trace_level FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "User not found."

    trace_level = row[0] + 5  # Apply trace penalty

    cur.execute("""
        UPDATE users
        SET cloaked = 1, trace_level = ?
        WHERE username = ?
    """, (trace_level, username))

    conn.commit()
    conn.close()
    return f"{username} is now cloaked. You are now hidden from whois and logs (+5 trace)"


def uncloak_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Ensure user exists
    cur.execute("SELECT username FROM users WHERE username = ?", (username,))
    if not cur.fetchone():
        conn.close()
        return "User not found."

    # Set cloaked = 0
    cur.execute("UPDATE users SET cloaked = 0 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return f"{username} is now uncloaked. Your presence is visible again."

def spoof_user(username, target_user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Validate both users exist
    cur.execute("SELECT trace_level FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "User not found."
    
    trace_level = row[0] + 3  # Apply trace penalty

    cur.execute("""
        UPDATE users
        SET trace_level = ?
        WHERE username = ?
        """, (trace_level, username))

    cur.execute("SELECT username FROM users WHERE username = ?", (target_user,))
    if not cur.fetchone():
        conn.close()
        return f"Target user '{target_user}' does not exist."

    # Set spoofed_as field
    cur.execute("UPDATE users SET spoofed_as = ? WHERE username = ?", (target_user, username))
    conn.commit()
    conn.close()

    return f"{username} is now spoofing as '{target_user}'."

def unspoof_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT spoofed_as FROM users WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return "User not found."

    if not row[0]:
        conn.close()
        return f"{username} is not currently spoofing anyone."

    cur.execute("UPDATE users SET spoofed_as = NULL WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return f"{username} is no longer spoofing."
