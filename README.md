# fw-ipsets

A tool to synchronize _ipsets_ located in Linux kernel with text-based file.

Supports `hash:ip` (set of IP addresses) and `hash:net` (set of netmasks).


## Usage example

```
$ sudo python3 fw-ipsets --config config.toml
[2025-11-23 18:34:49] INFO     Processing ipset 'dshield'                                     fw-ipsets.py:49
                      INFO     Current set: 19 items, new set: 19 items (+0, -0)              fw-ipsets.py:62
                      INFO     Processing ipset 'blocklist_de'                                fw-ipsets.py:49
                      INFO     Current set: 22318 items, new set: 22318 items (+0, -0)        fw-ipsets.py:62

$ sudo ipset list
Name: dshield
Type: hash:net
Revision: 7
Header: family inet hashsize 1024 maxelem 65536 bucketsize 12 initval 0x80a854fd
Size in memory: 1368
References: 0
Number of entries: 19
Members:
(... skipped ...)

Name: blocklist_de
Type: hash:ip
Revision: 6
Header: family inet hashsize 8192 maxelem 65536 bucketsize 12 initval 0x8cbe12ee
Size in memory: 527864
References: 0
Number of entries: 22318
Members:
(... skipped ...)
```