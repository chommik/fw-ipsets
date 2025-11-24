# SPDX-License-Identifier: BSD-2-Clause

import json
import subprocess
import tempfile
from abc import ABC, abstractmethod
from os import PathLike

from netaddr.ip import IPAddress, IPNetwork, cidr_merge

from fw_ipsets.config import NFTSetDefinition, IPSetType


class IPSetHandler(ABC):
    @staticmethod
    @abstractmethod
    def set_type() -> type:
        pass

    @staticmethod
    @abstractmethod
    def kernel_ipset_type() -> str:
        pass

    @classmethod
    @abstractmethod
    def preprocess_item_set(cls, new_items):
        pass

    @classmethod
    def read_from_file(cls, file_name: str | PathLike) -> set[IPAddress | IPNetwork]:
        ipset = set()
        elem_type = cls.set_type()
        with open(file_name, 'r') as infile:
            for line in infile:
                if line.startswith('#'):
                    continue
                ipset.add(elem_type(line.strip()))
        return ipset

    @classmethod
    def read_from_kernel_ipset(cls, ipset_name: str, ipset_opts: list[str]) -> set[IPAddress | IPNetwork]:
        ipset = set()
        elem_type = cls.set_type()
        for item in json.loads(subprocess.check_output(['ipset', '-o', 'json', 'list', ipset_name]))[0]['members']:
            ipset.add(elem_type(item['elem']))
        return ipset

    @classmethod
    def read_from_kernel_nft(cls, ipset_definition: NFTSetDefinition) -> set[IPAddress | IPNetwork]:
        nft_dict = json.loads(subprocess.check_output(
            ['nft', '--json', 'list', 'set', ipset_definition.family, ipset_definition.table, ipset_definition.name]))

        for nft_entry in nft_dict['nftables']:
            if 'set' in nft_entry:
                if 'elem' not in nft_entry['set']:
                    return set()

                set_elements = set()
                for elem in nft_entry['set']['elem']:
                    match elem:
                        case str(address):
                            set_elements.add(IPAddress(address))
                        case {'prefix': prefix}:
                            set_elements.add(IPNetwork(f"{prefix['addr']}/{prefix['len']}"))
                        case _:
                            raise ValueError(f"Unexpected item: {elem}")
                return set_elements
        else:
            raise RuntimeError("'nft' didn't return any set")

    @classmethod
    def ensure_kernel_nft_set_exists(cls, ipset: NFTSetDefinition):
        nft_dict = json.loads(
            subprocess.check_output(['nft', '--json', '--terse', 'list', 'sets', ipset.family, ipset.table]))
        for entry in nft_dict['nftables']:
            if 'set' in entry:
                current = entry['set']
                if (current['family'] == ipset.family
                        and current['table'] == ipset.table
                        and current['name'] == ipset.name):
                    return

        if ipset.type == IPSetType.NET:
            options = ['{', 'type ipv4_addr;', 'flags interval;', *ipset.kernel_opts, '}']
        else:  # ipset.type == IPSetType.IP:
            options = ['{', 'type ipv4_addr;', *ipset.kernel_opts, '}']

        subprocess.check_call(['nft', 'add', 'set', ipset.family, ipset.table, ipset.name, *options])

    @classmethod
    def update_kernel_ipset(cls, set_name: str, temp_suffix: str, new_items: set[IPAddress | IPNetwork]):
        with tempfile.NamedTemporaryFile('w+', delete_on_close=False) as ipset_commands:
            print(f"create {set_name}{temp_suffix} {cls.kernel_ipset_type()}", file=ipset_commands)
            for item in new_items:
                print(f"add {set_name}{temp_suffix} {item}", file=ipset_commands)
            print(f"swap {set_name}{temp_suffix} {set_name}", file=ipset_commands)
            print(f"destroy {set_name}{temp_suffix}", file=ipset_commands)
            ipset_commands.close()

            subprocess.check_call(['ipset', 'restore', '-f', ipset_commands.name])

    @classmethod
    def update_kernel_nft_set(cls, ipset: NFTSetDefinition, new_items: set[IPAddress | IPNetwork]):
        with tempfile.NamedTemporaryFile('w+', delete_on_close=False) as nft_commands:
            print(f"flush set {ipset.family} {ipset.table} {ipset.name}", file=nft_commands)

            for item in new_items:
                print(f"add element {ipset.family} {ipset.table} {ipset.name} {{ {item} }}", file=nft_commands)

            nft_commands.close()
            subprocess.check_call(['nft', '-f', nft_commands.name])


class IPAddressHandler(IPSetHandler):
    @classmethod
    def preprocess_item_set(cls, new_items):
        return new_items

    @staticmethod
    def kernel_ipset_type() -> str:
        return "hash:ip"

    @staticmethod
    def set_type() -> type:
        return IPAddress


class IPNetHandler(IPSetHandler):
    @classmethod
    def preprocess_item_set(cls, new_items):
        return set(cidr_merge(new_items))

    @staticmethod
    def kernel_ipset_type() -> str:
        return "hash:net"

    @staticmethod
    def set_type() -> type:
        return IPNetwork

