# SPDX-License-Identifier: BSD-2-Clause

import argparse
import logging
import os
import subprocess
import sys

import toml
from rich.logging import RichHandler

from fw_ipsets.config import Config, IPSetDefinition, IPSetType
from fw_ipsets.handler import IPAddressHandler, IPNetHandler


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--debug', '-D', action='store_true', default=False,
                        help='Enable debug logging')

    parser.add_argument('--config', '-c', required=True,
                        help='Path to config file')

    return parser.parse_args()


def setup_logging(debug: bool, color: bool):
    if color:
        handlers = [RichHandler(enable_link_path=False)]
        log_format = '%(message)s'
    else:
        handlers = [RichHandler(show_path=False, omit_repeated_times=False)]
        log_format = '%(filename)s:%(lineno)s %(levelname)s: %(message)s'

    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                        format=log_format,
                        datefmt='[%Y-%m-%d %H:%M:%S]',
                        handlers=handlers)


def read_config(config_file: str) -> Config:
    with open(config_file, 'r') as infile:
        raw_config = toml.load(infile)
    return Config(**raw_config)


def process_ipset(ipset: IPSetDefinition, temp_suffix: str) -> None:
    logging.info(f"Processing ipset '{ipset.name}'")

    match ipset.type:
        case IPSetType.IP:
            handler = IPAddressHandler
        case IPSetType.NET:
            handler = IPNetHandler

    subprocess.check_call(['ipset', '-exist', 'create', ipset.name, handler.kernel_set_type()])

    current_items = handler.read_from_kernel(ipset.name, ipset.kernel_opts)
    new_items = handler.preprocess_item_set(handler.read_from_file(ipset.source))

    logging.info(f"Current set: {len(current_items)} items, new set: {len(new_items)} items (+{len(new_items - current_items)}, -{len(current_items - new_items)})")

    handler.update_kernel_set(ipset.name, temp_suffix, new_items)



def main():
    args = parse_args()
    setup_logging(debug=args.debug,
                  color=os.isatty(sys.stdout.fileno()))
    config = read_config(args.config)

    for ipset in config.ipsets:
        process_ipset(ipset, config.temp_suffix)


if __name__ == '__main__':
    main()
