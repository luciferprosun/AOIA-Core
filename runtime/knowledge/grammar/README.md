# RHCSA Command Grammar Layer

This directory contains an advisory RHCSA command-shape classifier for the AOIA-Core dev branch.

It is local, deterministic, read-only, and non-executing. The goal is to classify command shape and highlight suspicious or hallucinated forms without changing runtime authority.

What it is not:

- not executor policy
- not a command safety proof
- not a factual correctness proof
- not a full Bash parser
- not a ShellCheck replacement
- not a tree-sitter-bash replacement
- not wired into AOIA runtime routing yet

Current implemented families:

- `systemctl`
- `dnf`
- `firewall-cmd`
- `semanage`
- `chmod`
- `podman`

Current status:

- prototype on the dev branch
- no merge to `main` yet
- tested with the focused grammar test module
- full unittest suite passes

CLI readout:

- local demonstration only
- JSON output
- not executor policy
- does not execute commands
- example: `python3 -m runtime.tools.command_grammar_cli "systemctl status sshd"`

Roadmap:

- expand command families
- add a richer pattern schema
- compare boundary behavior against ShellCheck and tree-sitter-bash
- add tags for hallucinated command shapes
- later expose the layer as an advisory signal only, not executor authority
