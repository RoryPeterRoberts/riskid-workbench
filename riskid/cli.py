"""Command line entry point for the RiskID Workbench.

The command set is fixed so that ``riskid --help`` lists every command from
day one. Round 3 implements ``init`` (create the organisation file and load
the data packs) and ``rebuild`` (regenerate the projections from the event
table); ``serve`` and ``check`` are still stubs until their rounds (PLAN.md
section 4, rounds 4 and 14).
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

    for name in ("serve", "check"):
        sub.add_parser(name, help=f"{name} (stub; see PLAN.md section 4)")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(args.path)
    if args.command == "rebuild":
        return _cmd_rebuild(args.path)
    if args.command:
        print(f"{args.command}: not implemented yet (PLAN.md section 4)")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
