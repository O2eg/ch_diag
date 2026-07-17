# Network Addresses And Hosts

This instruction belongs to report item `operating_system.network_addresses`. The item is backed by `operating_system.network_addresses` (local host script).

## What this item shows
- Local network addresses, interfaces, and host name mappings.
- Networking context for client, replication, backup, and monitoring connectivity.

## What to watch
- Unexpected IP address, hostname, DNS mapping, or interface state.
- Multiple addresses where ClickHouse or replication should bind only one.
- Address mismatch after failover or host rebuild.

## Common fault causes
- DNS drift.
- Network interface renumbering.
- Wrong host aliases.
- Container or VPN namespace confusion.

## Automatic evaluation
- No severity is assigned because expected interfaces and addresses require an environment baseline.
- `unsupported` means the `ip` utility was unavailable. A failure of both `ip -br addr` and the compatible `ip addr show` fallback is an error rather than partial success.

## Checklist
- Compare with ClickHouse listen_addresses, pg_hba, and replication configuration.
- Confirm monitoring and application endpoints use the expected address.
- Check standby and backup connectivity when addresses changed.
