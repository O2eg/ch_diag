# Disks And SSDs

This instruction belongs to report item `operating_system.lshw_disk`. The item is backed by `operating_system.lshw_disk` (local host script).

## What this item shows
- Physical or virtual disk inventory, model, size, serial, and capabilities where visible.
- Device identity context for database storage.

## What to watch
- Unexpected disk model, size, rotational flag, or serial.
- Missing disks or disks on wrong tier.
- Inventory unavailable due to permissions.

## Common fault causes
- Storage migration incomplete.
- Wrong volume attached.
- Cloud disk resized without filesystem expansion.

## Automatic evaluation
- No severity is assigned because model, rotational state, and tier require an environment baseline.
- lshw may omit disks without sufficient privileges; compare with the volume, mount, and filesystem items.

## Checklist
- Map disks to mounts used by ClickHouse.
- Compare disk identity with storage monitoring.
- Confirm ClickHouse data, temporary, log, and backup paths use the intended storage tier.
