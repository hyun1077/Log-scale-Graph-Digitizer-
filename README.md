# Legacy Log-scale Graph Digitizer v1

The original digitizer UI is legacy, but this repository is **not safe to archive yet**.

## Still-active responsibilities
This repository currently runs scheduled GitHub Actions for:
- US capital-flow / liquidity data
- stock signal updates
- investment-flow data

Those market-data responsibilities are planned to move into `hyun1077/THINKING-LAB`.

## Migration rule
Do not archive this repository until all of the following are complete:
1. Move the active scripts, generated market data, and scheduled workflows to THINKING LAB.
2. Replace THINKING LAB links/iframes/imports that still point to this repository.
3. Run and verify at least one scheduled update from the new location.
4. Verify the replacement public market page/data endpoints.
5. Only then archive this repository.

For active datasheet digitizer development, use `hyun1077/Log-scale-Graph-Digitizer-v2`.
