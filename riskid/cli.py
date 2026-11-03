"""Command line entry point for the RiskID Workbench.

Round 0 provides the three commands as stubs that print their own name;
later rounds replace each stub with the real implementation (PLAN.md
section 4, rounds 3, 4 and 14). The command set is fixed here so that
``riskid --help`` lists all three from day one.
"""

import argparse

# The three commands, in the order PLAN.md section 4 introduces them.
COMMANDS = ("init", "serve", "check")


def main(argv=None):
    """Parse and run the command. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="riskid",
        description="RiskID Workbench: the AI risk identification method as software.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name in COMMANDS:
        sub.add_parser(
            name,
            help=f"{name} (stub in round 0; see PLAN.md section 4)",
        )
    args = parser.parse_args(argv)
    if args.command:
        print(args.command)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
