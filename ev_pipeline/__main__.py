import argparse
import logging
from .acquire import acquire


def main():
    p = argparse.ArgumentParser(description="Reproducible NSW EV charger pipeline")
    p.add_argument("command", choices=["acquire", "build", "all", "validate"])
    p.add_argument("--offline", action="store_true", help="Require verified local inputs; never download")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command in ("acquire", "all", "build"):
        acquire(offline=args.offline or args.command == "build")
    if args.command in ("all", "build"):
        from .pipeline import build
        build(offline=args.offline or args.command == "build")
    if args.command == "validate":
        from .pipeline import validate_existing
        validate_existing()


if __name__ == "__main__":
    main()
