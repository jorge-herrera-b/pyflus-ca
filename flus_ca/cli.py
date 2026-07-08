# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from .model import FLUSCA, run_batch_from_config
from .config import config_from_gui_logs


def main():
    parser = argparse.ArgumentParser("flus-ca")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("convert-logs")
    p.add_argument("--log-simulation", required=True)
    p.add_argument("--config-mp", required=True)
    p.add_argument("--output-yaml", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("--config", required=True)

    p = sub.add_parser("run")
    p.add_argument("--config", required=True)

    p = sub.add_parser("batch")
    p.add_argument("--config", required=True)

    args = parser.parse_args()

    if args.cmd == "convert-logs":
        config_from_gui_logs(args.log_simulation, args.config_mp, args.output_yaml)
        print("YAML creado:", args.output_yaml)

    elif args.cmd == "inspect":
        model = FLUSCA(args.config)
        model.print_inspect()
        print("\\nProbando carga de rasters...")
        model.load()
        print("OK")

    elif args.cmd == "run":
        model = FLUSCA(args.config)
        out = model.run_and_save()
        print("Guardado:", out)

    elif args.cmd == "batch":
        run_batch_from_config(args.config)


if __name__ == "__main__":
    main()
