# Build Pac-Man

Build a playable Pac-Man game as a single, self-contained HTML file.

## Deliverable

- Create exactly one file named `pacman.html` in the current working directory (the directory that contains this `PROMPT.md`). This location overrides any general rule you follow about where files should go.
- Everything the game needs (HTML, CSS, JavaScript, graphics, sound) must live inside that one file. No external scripts, stylesheets, fonts, images, CDNs, or network requests of any kind.
- It must run by opening the file directly from disk (`file://`) in current desktop Chrome and Safari. No build step, no server, no install.

## The game

Make it play and feel like the arcade original. At minimum:

- A maze with walls, pellets, and power pellets, plus the side tunnel.
- Pac-Man controlled with the arrow keys (WASD also works), with responsive turning at corners.
- Four ghosts with distinct behaviors, a ghost house, and frightened mode after a power pellet (frightened ghosts can be eaten).
- Score, lives, level progression when the maze is cleared, and start / game-over states.
- A way to pause.

Beyond that, use your own judgment. A person will play every entry and judge gameplay, faithfulness, feel, polish, and bugs.

## Rules

- Work alone and autonomously. Nobody will answer questions, so do not stop to ask. Make reasonable decisions and keep going until the game is done.
- Write the game yourself. Do not search the web, fetch URLs, download packages, or look up, download, or copy any existing Pac-Man implementation.
- Only read and write files inside the current working directory. Do not inspect other directories, other projects on this machine, other git branches, or git remotes.
- You may use tools that are already installed locally (for example a shell, `node`, or a local headless browser if one exists) to test your work.
- When you finish, reply with a short summary: what you built, the controls, and any known issues.
