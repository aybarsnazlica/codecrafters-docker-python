import os
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    command = sys.argv[3]
    args = sys.argv[4:]

    with TemporaryDirectory() as tmpdir:
        unshare_command = ["unshare", "--pid", "--fork", "--mount-proc", "--"]
        chroot_command = ["chroot", tmpdir, os.path.join("/", os.path.basename(command)), *args]

        shutil.copy(command, tmpdir)
        completed_process = subprocess.run(
            unshare_command + chroot_command,
            capture_output=True,
        )
        sys.stdout.buffer.write(completed_process.stdout)
        sys.stderr.buffer.write(completed_process.stderr)
        sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
