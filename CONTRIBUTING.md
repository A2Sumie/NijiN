# Contributing

Keep changes **source-only**. This project exists in public only because it
carries no third-party proprietary content.

## Never attach or commit

- firmware, update packages, decrypted or extracted program bytes, segments,
  flash or memory dumps, payload blobs;
- keys, certificates, key material or anything that unlocks a device file;
- extracted fonts, icon bitmaps, string tables, UI resources;
- device settings files (for example custom-settings save files) — they can
  carry personal data;
- third-party commercial software, its binaries, or derivative material;
- service/repair documentation or other documents you do not have the right
  to publish;
- photographs, camera UI screenshots, real device captures;
- personal data, local absolute paths, artifacts from your home downloads
  folder, hostnames.

Runtime and build folders can contain proprietary bytes even when the
repository is source-only. Keep them local. Do not paste them into issues;
a fingerprint and a description are enough.

## Reporting a problem

Report the input package fingerprint (SHA-256), the repository commit, the
exact feature selection, the command line, the observed behaviour and what
you expected. A register address, offset or status observation is useful; an
entire dump is not. Use synthetic or locally generated test material.

Be precise about verification depth: say whether something was checked
offline (build, verify, gauntlet) or on hardware, and which build it was.
Do not upgrade "offline green" to "works".

## Changing code

- New feature code goes in its own module with a pinned recipe in
  `resources/`: hashes and offsets only, never byte payloads of the target
  software.
- The generated code must be reproducible from the sources in this
  repository; the build refuses a compiler whose output differs from the
  reviewed bytes.
- Keep the verifier independent from the builder. A check that cannot fail
  is not a check.
- Tests must run without firmware. Gate any test that needs a local input
  file behind an environment variable and skip loudly when it is absent.
- Update `resources/` hashes through the recipe-locking path, not by hand.

## Before you push

```sh
python tools/redline_scan.py
python tools/check_repository.py --staged
python tools/check_links.py
```

All three must report no issues. `tools/check_repository.py` refuses binary
content except the reviewed brand PNGs, oversized files, blocked suffixes,
symlinks, submodules, SVGs with embedded raster data and credential-shaped
strings. `tools/redline_scan.py` additionally checks for absolute local
paths, personal markers and firmware-shaped blobs, and `tools/check_links.py`
verifies that every documentation link and anchor resolves. The repository
hook runs all three automatically:
`git config core.hooksPath .githooks`.

When adding content of a new kind, review its origin first, then update the
allowlists in these tools deliberately — never to make a warning disappear.

## Honesty rules

- If something is not verified, say so, in the same table as the things that
  are. Unverified and broken items are part of the deliverable.
- If something is not deliverable, record it as not deliverable with the
  reason, instead of quietly dropping it.
- Fix claims that turn out wrong, and keep the correction visible.
