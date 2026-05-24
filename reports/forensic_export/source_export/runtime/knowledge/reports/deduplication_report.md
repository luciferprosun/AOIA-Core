# Candidate Deduplication Report

- Total parsed entries: 3152
- Total unique candidate commands: 2570
- Duplicates against existing canonical/index: 725
- Internal candidate duplicates: 582

## Duplicate Type Counts

- candidate_internal: 382
- canonical+command_index: 481
- canonical+command_index+candidate_internal: 193
- command_index: 44
- command_index+candidate_internal: 7
- new_candidate: 2045

## Sample Existing Duplicates

- `basename` -> canonical+command_index
- `cat` -> canonical+command_index
- `cat -A file.txt` -> canonical+command_index
- `cat -n file.txt` -> canonical+command_index
- `cat /etc/anacrontab` -> canonical+command_index
- `cat /etc/bashrc` -> canonical+command_index
- `cat /etc/cron.allow` -> canonical+command_index
- `cat /etc/cron.deny` -> canonical+command_index
- `cat /etc/crontab` -> canonical+command_index
- `cat /etc/exports` -> canonical+command_index
- `cat /etc/fstab` -> canonical+command_index
- `cat /etc/os-release` -> canonical+command_index
- `cat /etc/profile` -> canonical+command_index
- `cat /etc/systemd/sys` -> canonical+command_index
- `cat /proc/cmdline` -> canonical+command_index
- `cat /proc/cpuinfo` -> canonical+command_index
- `cat /proc/mdstat` -> canonical+command_index
- `cat /proc/meminfo` -> canonical+command_index
- `cat /proc/mounts` -> canonical+command_index
- `cat /proc/net/tcp` -> canonical+command_index
- `cat /proc/net/udp` -> canonical+command_index
- `cat /proc/sys/kernel` -> canonical+command_index
- `cat /proc/version` -> canonical+command_index
- `cat /sys/fs/cgroup/m` -> canonical+command_index
- `cat /var/log/audit/a` -> canonical+command_index
- `cat /var/log/cron` -> canonical+command_index
- `cat /var/log/maillog` -> canonical+command_index
- `cat /var/log/secure` -> canonical+command_index
- `cat /var/spool/cron/` -> canonical+command_index
- `cat file.txt` -> canonical+command_index
- `cat file1 file2` -> canonical+command_index
- `cat ~/.bash_logout` -> canonical+command_index
- `cat ~/.bash_profile` -> canonical+command_index
- `cat ~/.bashrc` -> canonical+command_index
- `cd` -> command_index
- `cd -` -> canonical+command_index
- `cd /` -> canonical+command_index
- `cd /path/to/dir` -> canonical+command_index
- `cd ~` -> canonical+command_index
- `cp` -> command_index
- `cp --backup src dst` -> canonical+command_index
- `cp -a src/ dst/` -> canonical+command_index
- `cp -i src dst` -> canonical+command_index
- `cp -p src dst` -> canonical+command_index
- `cp -r src/ dst/` -> canonical+command_index
- `cp -u src dst` -> canonical+command_index
- `cp -v src dst` -> canonical+command_index
- `cp source dest` -> canonical+command_index
- `df` -> command_index
- `diff` -> command_index

Canonical runtime files were not modified.
