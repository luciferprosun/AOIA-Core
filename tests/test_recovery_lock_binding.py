from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime.safety.atomic_persistence import AtomicWriteError, locked_update_json


class RecoveryLockBindingTests(unittest.TestCase):
    def test_lock_inode_replacement_blocks_locked_json_commit(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        ) as temporary:
            root = Path(temporary)
            target = root / "claim.json"
            lock = root / "claim.lock"

            def replace_lock(_current):
                lock.unlink()
                lock.write_bytes(b"")
                return {"generation": 1}, None

            with self.assertRaisesRegex(AtomicWriteError, "binding changed"):
                locked_update_json(
                    target,
                    replace_lock,
                    lock_path=lock,
                    maximum_bytes=1024,
                )

            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
