# Candidate Parsing Quality Report

- Total parsed entries: 3152
- Candidate records written: 3152
- Malformed or unresolved entries: 97

## Status Counts

- candidate: 1978
- duplicate_existing: 1077
- malformed: 76
- unresolved: 21

## Quality Flag Counts

- complex_pipeline_or_snippet: 1
- invalid_base_command: 2
- likely_contamination_or_comment: 7
- path_not_command: 74
- probable_pdf_merge_artifact: 16
- weak_description: 625

## Sample Malformed/Unresolved Entries

- line 3720: `cd $(dirname "$0") without symlink'` (likely_contamination_or_comment)
- line 4022: `file` (probable_pdf_merge_artifact)
- line 4028: `file '/start/,/end/p'` (weak_description, probable_pdf_merge_artifact)
- line 4033: `file -b /bin/ls` (probable_pdf_merge_artifact)
- line 4038: `file -out file.enc` (probable_pdf_merge_artifact)
- line 4048: `file /etc/passwd` (weak_description, probable_pdf_merge_artifact)
- line 4053: `file 2>/dev/null` (weak_description, probable_pdf_merge_artifact)
- line 4058: `file chronyd` (probable_pdf_merge_artifact)
- line 4063: `file file` (weak_description, probable_pdf_merge_artifact)
- line 4068: `file grup` (weak_description, probable_pdf_merge_artifact)
- line 4073: `file kadej linii` (weak_description, probable_pdf_merge_artifact)
- line 4078: `file regularnego` (weak_description, probable_pdf_merge_artifact)
- line 4083: `file symboliczne u:user:rwx file` (probable_pdf_merge_artifact)
- line 5092: `rm -rf / or rm -rf $VAR/ when $VAR unset.'` (likely_contamination_or_comment, weak_description)
- line 5102: `rm -rf /var/log/journal bypassing vacuum logic.'` (likely_contamination_or_comment, weak_description)
- line 5287: `touch file` (probable_pdf_merge_artifact)
- line 5292: `touch file.txt` (weak_description, probable_pdf_merge_artifact)
- line 5297: `touch kernel logic` (likely_contamination_or_comment, probable_pdf_merge_artifact)
- line 5302: `touch planner systems` (likely_contamination_or_comment, probable_pdf_merge_artifact)
- line 6525: `/etc/hostname` (path_not_command)
- line 6530: `/etc/hosts` (path_not_command)
- line 6535: `/etc/resolv.conf` (path_not_command)
- line 6990: `firewall-cmd --runtime-to-permanent` (likely_contamination_or_comment)
- line 8852: `/proc` (path_not_command)
- line 10458: `'systemctl edit“` (invalid_base_command)
- line 11826: `/backup/xfs.dump` (path_not_command, weak_description)
- line 11831: `/bin/backup.sh` (path_not_command, weak_description)
- line 11836: `/bin/task.sh` (path_not_command)
- line 11846: `/boot` (path_not_command)
- line 11851: `/check.sh` (path_not_command, weak_description)
- line 11856: `/dev/md0` (path_not_command)
- line 11861: `/dev/null` (path_not_command)
- line 11866: `/dev/nvme0n1` (path_not_command)
- line 11871: `/dev/sda` (path_not_command)
- line 11876: `/dev/sdb` (path_not_command)
- line 11881: `/dev/sdb1` (path_not_command)
- line 11891: `/dev/sdc` (path_not_command)
- line 11896: `/dev/sdd` (path_not_command)
- line 11901: `/dev/tty` (path_not_command)
- line 11906: `/dev/urandom` (path_not_command)
- line 11911: `/dev/vgname/lvname` (path_not_command, weak_description)
- line 11916: `/dev/vgname/snapname` (path_not_command, weak_description)
- line 11921: `/etc` (path_not_command)
- line 11926: `/etc/anacrontab` (path_not_command)
- line 11936: `/etc/audit/auditd.conf` (path_not_command)
- line 11941: `/etc/auto.nfs` (path_not_command, weak_description)
- line 11946: `/etc/centos-release` (path_not_command, weak_description)
- line 11951: `/etc/chrony.conf` (path_not_command)
- line 11956: `/etc/cron.d` (path_not_command)
- line 11961: `/etc/cron.daily` (path_not_command)
- line 11966: `/etc/cron.hourly` (path_not_command)
- line 11971: `/etc/cron.monthly` (path_not_command)
- line 11981: `/etc/cron.weekly` (path_not_command)
- line 11986: `/etc/crontab` (path_not_command)
- line 11991: `/etc/crypttab` (path_not_command)
- line 11996: `/etc/default/grub` (path_not_command, weak_description)
- line 12001: `/etc/fstab` (path_not_command)
- line 12006: `/etc/logrotate.conf` (path_not_command, weak_description)
- line 12011: `/etc/nftables.conf` (path_not_command)
- line 12016: `/etc/pam.d/system-auth` (path_not_command)
- line 12026: `/etc/passwd` (path_not_command, weak_description)
- line 12031: `/etc/redhat-release` (path_not_command, weak_description)
- line 12036: `/etc/rsyslog.conf` (path_not_command, weak_description)
- line 12041: `/etc/sssd/sssd.conf` (path_not_command)
- line 12046: `/etc/sudoers` (path_not_command)
- line 12051: `/etc/sysctl.conf` (path_not_command)
- line 12056: `/etc/sysctl.d/99-hardening.conf` (path_not_command)
- line 12061: `/etc/systemd/system/secure_processor.service` (path_not_command)
- line 12071: `/etc/updatedb.conf` (path_not_command, weak_description)
- line 12076: `/hostname` (path_not_command, weak_description)
- line 12081: `/mnt` (path_not_command, weak_description)
- line 12086: `/path` (path_not_command, weak_description)
- line 12091: `/path/to/file` (path_not_command, weak_description)
- line 12096: `/path/to/key.gpg` (path_not_command, weak_description)
- line 12101: `/path/to/module.ko` (path_not_command, weak_description)
- line 12106: `/path/to/script.sh` (path_not_command)
- line 12116: `/proc/net/sockstat` (path_not_command)
- line 12121: `/sbin/init` (path_not_command)
- line 12126: `/tmp` (path_not_command)
- line 12132: `/tmp/cap.pcap` (path_not_command)

No command rows were promoted to canonical indexes.
