# SPDX-License-Identifier: BSD-2-Clause

import argparse
import json
import logging
import os
import subprocess
import sys

import toml
from rich.logging import RichHandler

from fw_ipsets.config import Config, IPSetDefinition, IPSetType, NFTSetDefinition
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


def process_ipset(ipset: IPSetDefinition | NFTSetDefinition, temp_suffix: str) -> None:
    logging.info(f"Processing ipset '{ipset.name}'")

    if isinstance(ipset, IPSetDefinition):
        match ipset.type:
            case IPSetType.IP:
                handler = IPAddressHandler
            case IPSetType.NET:
                handler = IPNetHandler
    elif isinstance(ipset, NFTSetDefinition):
        handler = IPNetHandler
    else:
        raise ValueError(f"Unexpected ipset type: {type(ipset)}")

    match ipset:
        case IPSetDefinition():
            subprocess.check_call(['ipset', '-exist', 'create', ipset.name, handler.kernel_ipset_type()])
            current_items = handler.read_from_kernel_ipset(ipset.name, ipset.kernel_opts)
        case NFTSetDefinition():
            handler.ensure_kernel_nft_set_exists(ipset)
            current_items = handler.read_from_kernel_nft(ipset)

    new_items = handler.preprocess_item_set(handler.read_from_file(ipset.source))

    logging.info(f"Current set: {len(current_items)} items, new set: {len(new_items)} items (+{len(new_items - current_items)}, -{len(current_items - new_items)})")

    match ipset:
        case IPSetDefinition():
            handler.update_kernel_ipset(ipset.name, temp_suffix, new_items)
        case NFTSetDefinition():
            handler.update_kernel_nft_set(ipset, new_items)



def main():
    args = parse_args()
    setup_logging(debug=args.debug,
                  color=os.isatty(sys.stdout.fileno()))
    config = read_config(args.config)

    for ipset in config.ipsets:
        process_ipset(ipset, config.temp_suffix)


if __name__ == '__main__':
    main()
