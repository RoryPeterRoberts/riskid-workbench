"""Command line entry point for the RiskID Workbench.

The command set is fixed so that ``riskid --help`` lists every command from
day one. Round 3 implements ``init`` (create the organisation file and load
the data packs) and ``rebuild`` (regenerate the projections from the event
table); round 4 implements ``serve`` (the screens on localhost, SPEC.md
section 9); ``check`` is still a stub until its round (PLAN.md section 4).
"""

import argparse
import sys

# The commands, in the order PLAN.md section 4 introduces them.
COMMANDS = ("init", "serve", "check", "rebuild")


def _cmd_init(path: str) -> int:
    from riskid.store import init

    try:
        with init(path) as store:
            n_library = len(store.library())
            n_taxonomy = len(store.taxonomy())
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"initialised {path}: {n_library} library lines, {n_taxonomy} taxonomy lines")
    return 0


def _cmd_rebuild(path: str) -> int:
    from riskid.store import rebuild

    try:
        n_events = rebuild(path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"rebuilt projections for {path} from {n_events} events")
    return 0


def _allowed_hosts(host: str):
    """The Host header values to accept: loopback, plus the host served on if it is another.

    On every interface (0.0.0.0 or ::) the list is loopback plus this machine's
    own names and addresses, never "*": a wildcard would let a web page reach
    the workbench through DNS rebinding, with an Origin that matches its Host.
    """
    import socket

    from riskid.web import LOOPBACK_HOSTS

    if host not in ("0.0.0.0", "::"):
        return list(LOOPBACK_HOSTS) + ([host] if host not in LOOPBACK_HOSTS else [])
    names = {socket.gethostname(), socket.getfqdn()}
    try:
        names |= {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None)}
    except OSError:
        pass
    allowed = list(LOOPBACK_HOSTS) + sorted(n for n in names if n and n not in LOOPBACK_HOSTS)
    print("warning: serving on every network interface; anyone who can reach this "
          "machine can read and change the organisation file. Accepted host names: "
          + ", ".join(allowed), file=sys.stderr)
    return allowed


def _cmd_serve(path: str, host: str, port: int, open_browser: bool) -> int:
    from pathlib import Path

    target = Path(path)
    if not target.exists():
        print(f"error: no organisation file at {target}; create it with `riskid init`",
              file=sys.stderr)
        return 1
    import threading
    import webbrowser

    import uvicorn

    from riskid.app import create_app

    app = create_app(target, allowed_hosts=_allowed_hosts(host))
    url = f"http://{host}:{port}/inventory"
    print(f"serving {target} at {url} (Ctrl-C to stop)")
    if open_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


def main(argv=None):
    """Parse and run the command. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="riskid",
        description="RiskID Workbench: the AI risk identification method as software.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_init = sub.add_parser(
        "init", help="create an organisation file and load the data packs")
    p_init.add_argument("path", help="the .riskid file to create")

    p_rebuild = sub.add_parser(
        "rebuild", help="rebuild the projections from the event table")
    p_rebuild.add_argument("path", help="the .riskid file to rebuild")

    from riskid.config import DEFAULT_HOST, DEFAULT_PORT

    p_serve = sub.add_parser(
        "serve", help="open the workbench in the browser for an organisation file")
    p_serve.add_argument("path", help="the .riskid file to work on")
    p_serve.add_argument("--host", default=DEFAULT_HOST,
                         help=f"interface to listen on (default {DEFAULT_HOST}, this machine only)")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT,
                         help=f"port (default {DEFAULT_PORT})")
    p_serve.add_argument("--no-browser", action="store_true",
                         help="do not open a browser window")

    sub.add_parser("check", help="check (stub; see PLAN.md section 4)")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(args.path)
    if args.command == "rebuild":
        return _cmd_rebuild(args.path)
    if args.command == "serve":
        return _cmd_serve(args.path, args.host, args.port, not args.no_browser)
    if args.command:
        print(f"{args.command}: not implemented yet (PLAN.md section 4)")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
