# This spins up the web server that hosts the game
# @author: NotYourFathersLore

from flask import Flask, request, jsonify, render_template
import sqlite3
import json
from flask_cors import CORS
from game_state import *

app = Flask(__name__)
DB = 'C:/path/to/infiltr8.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/start', methods=['POST'])
def start_game():
    data = request.get_json()
    username = data.get("username")
    session_id = create_session(username)
    return jsonify({"session_id": session_id})

@app.route('/help', methods=['GET'])
def help_command():
    return jsonify(get_available_commands())

@app.route('/scan', methods=['POST'])
def scan():
    data = request.get_json()
    username = data.get("username")
    conn = get_db()
    # Get user's current IP
    user = conn.execute("SELECT current_ip FROM users WHERE username = ?", (username,)).fetchone()
    current_ip = user["current_ip"] if user else None

    # If not connected, only return nodes with no neighbors (public-facing)
    if not current_ip:
        nodes = conn.execute("""
            SELECT ip, hostname FROM nodes
            WHERE neighbors IS NULL OR neighbors = '[]'
        """).fetchall()
        return jsonify([dict(n) for n in nodes])

    # If connected, return current node and its neighbors
    current_node = conn.execute("SELECT neighbors FROM nodes WHERE ip = ?", (current_ip,)).fetchone()
    visible_ips = [current_ip]

    if current_node and current_node["neighbors"]:
        try:
            visible_ips += json.loads(current_node["neighbors"])
        except json.JSONDecodeError:
            pass

    # Fetch node data for all visible IPs
    placeholders = ','.join(['?'] * len(visible_ips))
    nodes = conn.execute(f"""
        SELECT ip, hostname FROM nodes
        WHERE ip IN ({placeholders})
    """, visible_ips).fetchall()
    return jsonify([dict(n) for n in nodes])


@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    username = data['username']
    ip = data['ip']
    conn = get_db()

    # Check if node exists
    node = conn.execute("SELECT * FROM nodes WHERE ip=?", (ip,)).fetchone()
    if not node:
        return jsonify({"error": "Node not found"}), 404

    # Get user's current node
    user = conn.execute("SELECT current_ip FROM users WHERE username = ?", (username,)).fetchone()
    current_ip = user["current_ip"] if user else None

    # Determine if the target node is publicly accessible
    target_neighbors = json.loads(node["neighbors"]) if node["neighbors"] else []
    is_public = (not target_neighbors or node["neighbors"] == "[]")

    if is_public:
        # Allow connection to public node
        conn.execute("UPDATE users SET current_ip=? WHERE username=?", (ip, username))
        conn.commit()
        return jsonify({"message": f"Connected to {ip}"})

    # If user is connected, check if target is a neighbor
    if current_ip:
        current_node = conn.execute("SELECT neighbors FROM nodes WHERE ip = ?", (current_ip,)).fetchone()
        if current_node and current_node["neighbors"]:
            try:
                neighbors = json.loads(current_node["neighbors"])
                if ip in neighbors:
                    conn.execute("UPDATE users SET current_ip=? WHERE username=?", (ip, username))
                    conn.commit()
                    return jsonify({"message": f"Pivoted to {ip} via connect (allowed because it's a neighbor)"})
            except json.JSONDecodeError:
                pass

    return jsonify({"error": f"Access to {ip} denied. You must pivot from an allowed node."}), 403

@app.route('/ls', methods=['POST'])
def list_files():
    data = request.json
    username = data['username']
    conn = get_db()

    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user or not user['current_ip']:
        return jsonify({"error": "Not connected to a node"}), 400

    node = conn.execute("SELECT files FROM nodes WHERE ip=?", (user['current_ip'],)).fetchone()
    files = json.loads(node['files'])
    return jsonify(files)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    username = data['username']
    filename = data['filename']
    conn = get_db()

    row = conn.execute("SELECT current_ip, inventory FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return jsonify({"error": "Not connected to a node"}), 400

    ip, inventory_raw = row
    inventory = json.loads(inventory_raw or "[]")

    node = conn.execute("SELECT file_data FROM nodes WHERE ip = ?", (ip,)).fetchone()
    if not node or not node[0]:
        return jsonify({"error": "No files found."})
    
    file_data = json.loads(node[0])

    if filename not in file_data:
        return jsonify({"error": "File not found on node"}), 404

    # Add file to user inventory
    new_file = {
        "filename": filename,
        "from": ip,
        "content": file_data[filename]
    }
    inventory.append(new_file)

    conn.execute("UPDATE users SET inventory = ? WHERE username = ?", (json.dumps(inventory), username))
    conn.commit()

    '''
    inventory.append(filename)
    conn.execute("UPDATE users SET inventory=? WHERE username=?", (json.dumps(inventory), username))
    conn.commit()
    '''
    return jsonify({"message": f"Downloaded {filename}"})


@app.route('/status', methods=['POST'])
def status():
    data = request.get_json()
    session_id = data.get("username")
    state = get_state(session_id)
    if not state:
        return "Invalid session", 404
    return jsonify(state)

@app.route("/cat", methods=["POST"])
def cat_route():
    data = request.json
    username = data.get("username")
    filename = data.get("filename")

    if not username or not filename:
        return jsonify({"error": "Missing username or filename"}), 400

    result = cat_file(username, filename)
    return jsonify({"result": result})

@app.route("/whoami", methods=["POST"])
def whoami():
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    return jsonify({"result": get_whoami(username)})

@app.route('/pivot', methods=['POST'])
def pivot():
    data = request.get_json()
    username = data.get("username")
    target_ip = data.get("ip")

    if not username or not target_ip:
        return jsonify({"error": "Missing username or IP"}), 400

    result = pivot_to_node(username, target_ip)
    return jsonify({"result": result})

@app.route("/whois", methods=["POST"])
def whois():
    data = request.get_json()
    target = data.get("target")

    if not target:
        return jsonify({"error": "Missing target username"}), 400

    return jsonify({"result": get_whois(target)})

@app.route("/cloak", methods=["POST"])
def cloak():
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    result = cloak_user(username)
    return jsonify({"result": result})

@app.route("/uncloak", methods=["POST"])
def uncloak():
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    result = uncloak_user(username)
    return jsonify({"result": result})

@app.route("/spoof", methods=["POST"])
def spoof():
    data = request.get_json()
    username = data.get("username")
    target = data.get("target")

    if not username or not target:
        return jsonify({"error": "Missing username or target"}), 400

    result = spoof_user(username, target)
    return jsonify({"result": result})

@app.route("/unspoof", methods=["POST"])
def unspoof():
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    result = unspoof_user(username)
    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True)