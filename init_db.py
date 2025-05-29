# This creates the initial database if it does not already exist
# @author: NotYourFathersLore

import sqlite3
import json

DB_NAME = 'C:/path/to/infiltr8.db'

# Sample network nodes
nodes = [
    {
        "ip": "192.168.0.10",
        "hostname": "mail.infiltr8corp.local",
        "ports": "22,80,443",
        "files": ["email_archive.zip", "vpn_creds.txt", "welcome.msg"],
        "security_level": 2
    },
    {
        "ip": "192.168.0.22",
        "hostname": "dev.internal.infiltr8corp.local",
        "ports": "22,8080",
        "files": ["internal_api_docs.pdf", "beta_build.exe", "dev_notes.txt"],
        "security_level": 3
    },
    {
        "ip": "192.168.0.66",
        "hostname": "sec-db.infiltr8corp.local",
        "ports": "3306",
        "files": ["access_logs.db", "secrets.kdbx"],
        "security_level": 5
    }
]

# Create DB and tables
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Drop existing tables
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("DROP TABLE IF EXISTS nodes")

    # Create users table
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            inventory TEXT,
            current_ip TEXT,
            trace_level INTEGER
        )
    """)

    # Create nodes table
    c.execute("""
        CREATE TABLE nodes (
            ip TEXT PRIMARY KEY,
            hostname TEXT,
            ports TEXT,
            files TEXT,
            security_level INTEGER
        )
    """)

    # Add sample nodes
    for node in nodes:
        c.execute("""
            INSERT INTO nodes (ip, hostname, ports, files, security_level)
            VALUES (?, ?, ?, ?, ?)
        """, (
            node["ip"],
            node["hostname"],
            node["ports"],
            json.dumps(node["files"]),
            node["security_level"]
        ))

    # Add test user
    c.execute("""
        INSERT INTO users (username, inventory, current_ip, trace_level)
        VALUES (?, ?, ?, ?)
    """, ("testuser", json.dumps([]), None, 0))

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
