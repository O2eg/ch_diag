# Generic Devices

This instruction belongs to report item `operating_system.lshw_generic`. The item is backed by `operating_system.lshw_generic` (local host script).

## What this item shows
- Miscellaneous hardware devices not classified elsewhere by lshw.
- Catch-all inventory for unusual devices.

## What to watch
- Unexpected unknown devices.
- Devices with missing drivers.
- New generic entries after hardware changes.

## Common fault causes
- Driver mismatch.
- Firmware change.
- VM hardware profile change.

## Automatic evaluation
- No severity is assigned; generic devices require platform-specific identification.
- Empty output is valid and unknown devices are not automatically security or performance findings.

## Checklist
- Review only entries related to database storage, network, or security policy.
- Compare before/after hardware maintenance.
- Escalate unknown production devices when policy requires.
