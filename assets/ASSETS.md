# Brand assets

The NijiN icon, wordmark and lockup in this directory were designed and
generated for this project (v4, padded variant). They are original work of
this project: no third-party artwork, no font outlines, no device imagery,
no screenshots.

| Directory | Files | What it is |
|---|---|---|
| `icon/` | `nijin-icon-{transparent,white,black}.{svg,png}` | The pure icon mark |
| `wordmark/` | `nijin-wordmark-{transparent,white,black}.{svg,png}` | The coloured "NijiN" text mark (flat colours, no gradients, no font dependency) |
| `lockup/` | `nijin-lockup-{transparent,white,black}.{svg,png}` | Icon + wordmark together; this is what the README header shows |

`transparent` is for placing on your own background; `white` and `black` are
mono variants for dark and light backgrounds. Every variant is padded, so
the shapes keep the same optical margin in any layout.

The PNG files are plain PNG: header, image data and end marker only, no
metadata chunks. This is enforced by `tools/check_repository.py` and
`tools/redline_scan.py`, which only accept these nine PNGs as binary
content anywhere in the repository.

## License

Copyright (C) 2026 NijiN contributors.

These assets are licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). If you
reuse them, credit "NijiN" and share derivatives under the same license.
This license covers only the artwork in `assets/`; it does not cover any
firmware, tool source or third-party material.
