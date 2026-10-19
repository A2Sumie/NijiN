#!/usr/bin/env python3
"""preflight.py — 七道强制门（gauntlet 的子集入口）。

与 `gauntlet.py gates` 等价；任何构建进 flash_kit 前必须全绿。完整酷刑电池（变异/组合/
结构/测试栈）用 `python3 gauntlet.py run`。退出码 0=全绿，非 0=有红项。
"""
import sys

import gauntlet

if __name__ == '__main__':
    sys.argv.insert(1, 'gates')
    try:
        sys.exit(gauntlet.main())
    except (ValueError, OSError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(3)
