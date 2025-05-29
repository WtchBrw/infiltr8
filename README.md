#Infiltr8

this is a fun idea I had to create something of a pseudo-cybersec game. The goal here is to use various commands in a terminal-style web interface in order to explore, map and "attack" hosts on a simulated network. However, scanning too aggressively, spoofing yourself to look like another user, and other various actions may gain some unwanted attention from bots and the simulated IDS/IPS within, so be careful!


###This is a WIP, not everything works but below are some of the next steps for mechanics I had in mind to implement

```
Command Ideas:
  help – list available commands
  ADDED - status – current user/session info
  ADDED - cat <filename> – read file contents
  pivot <target> – move laterally inside the network
  crack <target> – attempt to hack secured machines
  backdoor <filename> – enable a backdoor on a device
  exec <filename> – run an executable on a machine

Stretch Goals:
  Honeytokens - Scanning too aggressively unlocks fake nodes with trace consequences
  Time Triggers - New parts of the network appear after real or in-game time passes
  Faction Zones - Reveal new areas and increase trace after attacking a faction/server
  Simulated AI/Blue team detection??
  Competing players - multiplayer mode
  ADDED - Dynamic network expansion - new areas are unlocked, generated, etc. after time and objectives are completed

Mechanic Ideas:
  exploit discovery - exploring the network you find new exploits able to be downloaded to your inventory
  secured devices - require password cracking to decrypt files
  exploits - useful on only certain ports, correspond with node security levels, let you connect to secured devices
```

