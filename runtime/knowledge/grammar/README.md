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
- file readout: `cat`, `less`, `head`, `tail`
- filesystem listing/readout: `ls`, `pwd`, `tree`, `basename`, `dirname`
- search/text readout: `grep`, `find`
- log readout: `journalctl`
- RPM query readout: `rpm`

Expanded low-risk read-only families:

- file read/listing, search/text readout, log readout, and RPM query forms are classified as advisory read-only shapes when they match narrow patterns
- destructive, state-changing, or ambiguous forms such as `find -delete`, `find -exec rm`, `rpm install`, and unsupported tree operations remain suspicious or rejected
- these classifications are still not command safety proofs and are not executor policy

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

Batch / stdin mode:

- reads newline-separated command strings and prints one JSON array
- never executes input
- example: `printf 'systemctl status sshd\npodman ps\n' | python3 -m runtime.tools.command_grammar_cli --stdin`

Roadmap:

- expand command families
- add a richer pattern schema
- compare boundary behavior against ShellCheck and tree-sitter-bash
- add tags for hallucinated command shapes
- later expose the layer as an advisory signal only, not executor authority
