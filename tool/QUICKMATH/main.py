#!/usr/bin/env python3
"""QUICKMATH -- Quick arithmetic calculator.

Perform basic arithmetic from the command line.

Usage:
    QUICKMATH add 3 5
    QUICKMATH subtract 10 4
    QUICKMATH multiply 6 7
    QUICKMATH divide 20 4
    QUICKMATH batch "3+5, 10-4, 6*7"
"""
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists():
        break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def _add(a: float, b: float) -> float:
    return a + b


def _subtract(a: float, b: float) -> float:
    return a - b


def _multiply(a: float, b: float) -> float:
    # BUG: uses exponentiation instead of multiplication
    return a ** b


def _divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


OPS = {
    "add": (_add, "+"),
    "subtract": (_subtract, "-"),
    "multiply": (_multiply, "*"),
    "divide": (_divide, "/"),
}


def cmd_calc(args):
    """Execute a single arithmetic operation."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    op = args.operation
    a, b = args.a, args.b

    if op not in OPS:
        print(f"  {BOLD}{RED}Unknown operation{RESET}: {op}")
        return

    func, symbol = OPS[op]
    try:
        result = func(a, b)
        print(f"  {BOLD}{GREEN}{a} {symbol} {b} = {result}{RESET}")
    except Exception as e:
        print(f"  {BOLD}{RED}Error{RESET}: {e}")


def cmd_batch(args):
    """Evaluate a batch of comma-separated expressions."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    exprs = [e.strip() for e in args.expressions.split(",") if e.strip()]
    for expr in exprs:
        try:
            result = eval(expr)
            print(f"  {BOLD}{GREEN}{expr} = {result}{RESET}")
        except Exception as e:
            print(f"  {BOLD}{RED}{expr} → Error{RESET}: {e}")


def main():
    tool = ToolBase("QUICKMATH")

    parser = argparse.ArgumentParser(
        description="QUICKMATH -- Quick arithmetic calculator",
        add_help=False,
    )

    sub = parser.add_subparsers(dest="command")

    for op_name in OPS:
        p = sub.add_parser(op_name, help=f"Compute a {op_name} b")
        p.add_argument("a", type=float, help="First number")
        p.add_argument("b", type=float, help="Second number")

    batch_p = sub.add_parser("batch", help="Evaluate comma-separated expressions")
    batch_p.add_argument("expressions", help='e.g. "3+5, 10-4, 6*7"')

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()

    if args.command in OPS:
        args.operation = args.command
        cmd_calc(args)
    elif args.command == "batch":
        cmd_batch(args)
    else:
        print(f"  {BOLD}QUICKMATH{RESET} -- Quick arithmetic calculator.")
        print()
        print(f"  Commands:")
        print(f"    add A B         Compute A + B")
        print(f"    subtract A B    Compute A - B")
        print(f"    multiply A B    Compute A * B")
        print(f"    divide A B      Compute A / B")
        print(f"    batch EXPRS     Evaluate comma-separated expressions")


BOLD = get_color("BOLD")
RESET = get_color("RESET")


if __name__ == "__main__":
    main()
