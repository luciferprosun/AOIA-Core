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
- system/storage inspection: `df`, `du`, `free`, `uname`, `uptime`, `dmesg`, `lsblk`, `blkid`, `smartctl`, `nvme`
- user/account inspection: `id`, `whoami`, `groups`, `getent`, `passwd -S`, `chage -l`
- network inspection: `ip`, `ss`, `ping -c`, `dig`, `host`, `tracepath`, `ethtool`, `nmcli`

Expanded low-risk read-only families:

- file read/listing, search/text readout, log readout, and RPM query forms are classified as advisory read-only shapes when they match narrow patterns
- destructive, state-changing, or ambiguous forms such as `find -delete`, `find -exec rm`, `rpm install`, and unsupported tree operations remain suspicious or rejected
- these classifications are still not command safety proofs and are not executor policy

System, network, and account inspection families:

- read-only system/storage readouts, account lookups, and network inspection forms are classified only when they match narrow advisory patterns
- configuration, account-changing, destructive, or credential-sensitive forms remain suspicious, rejected, or non-read-only
- this layer remains non-executing and is not runtime routing or executor authority

GT15 focused expansion:

- `systemctl` read-only inspection forms such as `list-units`, `list-unit-files`, `is-active`, `is-enabled`, `cat`, and `show` are separated from state-changing service actions
- `systemctl start`, `stop`, `restart`, `enable`, `disable`, `mask`, `unmask`, `isolate`, `poweroff`, and `reboot` remain non-read-only
- this is still advisory command-shape classification only and does not execute or authorize service operations

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
