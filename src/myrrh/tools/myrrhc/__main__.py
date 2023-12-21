import os
import sys

argv = sys.argv
while True:
    try:
        exit_code = os.spawnl(os.P_WAIT, sys.executable, sys.executable, "-m", "myrrh.tools.myrrhc.main", *argv[1:])
    except KeyboardInterrupt:
        exit_code = 0

    if exit_code:
        if len(sys.argv) > 1:
            break

        if exit_code != 2:
            print("Myrrhc crashed with exit_code: %s" % exit_code)
            print("restart y/n?")
            c = ""
            while c not in ("y", "Y", "n", "N"):
                c = sys.stdin.read(1)

            if c in ("y", "Y"):
                continue

        break

    sys.exit(exit_code)
