const terminal = document.getElementById('terminal');
const form = document.getElementById('command-form');
const input = document.getElementById('command-input');
let username = null;
let sessionId = null;


function appendToTerminal(text) {
  const div = document.createElement('div');
  div.textContent = text;
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
}

async function handleCommand(cmd) {
  appendToTerminal(`$ ${cmd}`);
  const [command, ...args] = cmd.split(" ");
  let response;

  try {
    switch (command) {
      case 'scan':
        res = await fetch('/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: sessionId })
        });
        data = await res.json();
        data.forEach(node => {
          appendToTerminal(`${node.ip}  ${node.hostname}`);
        });
        break;
      case 'whois':
        fetch('/whois', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target: args[0] })
        })
        .then(res => res.json())
        .then(data => appendToTerminal(data.result));
        break;
      case 'spoof':
        fetch('/spoof', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: sessionId,
            target: args[0]
          })
        })
        .then(res => res.json())
        .then(data => appendToTerminal(data.result));
        break;
      case 'unspoof':
        fetch('/unspoof', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: sessionId
          })
        })
        .then(res => res.json())
        .then(data => appendToTerminal(data.result));
        break;
      case 'cloak':
        fetch('/cloak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: sessionId })
        })
        .then(res => res.json())
        .then(data => appendToTerminal(data.result));
        break;
      case 'uncloak':
        fetch('/uncloak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: sessionId })
        })
        .then(res => res.json())
        .then(data => appendToTerminal(data.result));
        break;
      case 'connect':
        response = await fetch('/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, ip: args[0] }),
          username: sessionId
        });
        appendToTerminal(await response.text());
        break;
      case 'pivot':
        response = await fetch('/pivot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, ip: args[0] }),
          username: sessionId
        });
        appendToTerminal(await response.text());
        break;
      case 'ls':
        response = await fetch('/ls', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username }),
          username: sessionId
        });
        appendToTerminal(await response.text());
        break;
      case 'download':
        response = await fetch('/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, filename: args.join(' ') }),
          username: sessionId
        });
        appendToTerminal(await response.text());
        break;
      case 'status':
        response = await fetch('/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username }),
          username: sessionId
        });
        appendToTerminal(await response.text());
        break;
      case 'cat':
        response = await fetch('/cat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, filename: args.join(' ') }),
          username: sessionId
        });
        data = await response.json();
        for (const [cmd, desc] of Object.entries(data)) {
          appendToTerminal(`${cmd.padEnd(20)} - ${desc}`);
        }
        break;
      case 'help':
        response = await fetch('/help', {
          method: 'GET'
        });
        data = await response.json();
        for (const [cmd, desc] of Object.entries(data)) {
          appendToTerminal(`${cmd.padEnd(20)} - ${desc}`);
        }
        break;
      case 'whoami':
        response = await fetch('/whoami', {
          method: 'POST',
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: sessionId })
        });
        data = await response.json();
        appendToTerminal(data.result);
        break;
      default:
        appendToTerminal(`Unknown command: ${command}`);
    }
  } catch (e) {
    appendToTerminal(e);
    //appendToTerminal('Error connecting to server.');
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const cmd = input.value.trim();
  if (cmd) {
    handleCommand(cmd);
    input.value = '';
  }
});

async function initSession() {
  username = prompt("Enter your hacker handle:") || "anon";
  const res = await fetch("/start", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
  const data = await res.json();
  sessionId = data.session_id;
  appendToTerminal(`Session started as ${sessionId}`);
}

initSession();
