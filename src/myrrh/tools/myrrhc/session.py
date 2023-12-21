import asyncio
import sys

from myrrh.tools.myrrhc.exceptions import Reboot

from myrrh.tools.myrrhc import prompt
from myrrh.tools.myrrhc_ext import myrrhc_cmds


def getsession():
    return Cli._session


class Cli:
    _session: prompt.PromptSession | None = None

    @classmethod
    def run(cls):
        try:
            with myrrhc_cmds.make_context(sys.argv[0], list()) as ctx:
                loop = asyncio.get_event_loop()

                Cli._session = prompt.PromptSession(ctx)

                if len([v for v in filter(lambda s: s not in ("-v", "--verbose"), sys.argv)]) == 1:
                    loop.run_until_complete(Cli._session.run())
                else:
                    loop.run_until_complete(Cli._session.command_call(" ".join(sys.argv[1:])))
        except EOFError:
            pass
        except Reboot:
            sys.exit(2)

        sys.exit(0)
