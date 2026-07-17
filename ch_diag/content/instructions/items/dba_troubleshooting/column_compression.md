# Column Compression And Key Flags

This instruction belongs to report item `dba_troubleshooting.column_compression`.

## What this item shows
- Compressed/uncompressed bytes by column plus ratio, type, and key membership.

## What to watch
- Large columns with poor compression, unexpected codecs, or key columns consuming disproportionate space.

## Common fault causes
- High-entropy values, unsuitable types/codecs, duplication, schema drift, or tiny parts.

## Automatic evaluation
- No universal ratio threshold exists; prioritize absolute bytes.
- Only visible active parts are included.

## Checklist
- Rank by raw bytes before optimizing ratios.
- Test codec/type changes on representative data and compare query CPU.
