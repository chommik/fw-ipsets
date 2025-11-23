import json
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Type

from netaddr.ip import IPAddress, IPNetwork, BaseIP, cidr_merge


class IPSetHandler(ABC):
    @staticmethod
    @abstractmethod
    def set_type() -> type:
        pass

    @staticmethod
    @abstractmethod
    def kernel_set_type() -> str:
        pass

    @classmethod
    @abstractmethod
    def preprocess_item_set(cls, new_items):
        pass

    @classmethod
    def read_from_file(cls, file_name: str) -> set[IPAddress | IPNetwork]:
        ipset = set()
        elem_type = cls.set_type()
        with open(file_name, 'r') as infile:
            for line in infile:
                if line.startswith('#'):
                    continue
                ipset.add(elem_type(line.strip()))
        return ipset

    @classmethod
    def read_from_kernel(cls, ipset_name: str, ipset_opts: list[str]) -> set[IPAddress | IPNetwork]:
        ipset = set()
        elem_type = cls.set_type()
        for item in json.loads(subprocess.check_output(['ipset', '-o', 'json', 'list', ipset_name]))[0]['members']:
            ipset.add(elem_type(item['elem']))
        return ipset

    @classmethod
    def update_kernel_set(cls, set_name: str, temp_suffix: str, new_items: set[IPAddress | IPNetwork]):
        with tempfile.NamedTemporaryFile('w+', delete_on_close=False) as ipset_commands:
            print(f"create {set_name}{temp_suffix} {cls.kernel_set_type()}", file=ipset_commands)
            for item in new_items:
                print(f"add {set_name}{temp_suffix} {item}", file=ipset_commands)
            print(f"swap {set_name}{temp_suffix} {set_name}", file=ipset_commands)
            print(f"destroy {set_name}{temp_suffix}", file=ipset_commands)
            ipset_commands.close()

            subprocess.check_call(['ipset', 'restore', '-f', ipset_commands.name])


class IPAddressHandler(IPSetHandler):
    @classmethod
    def preprocess_item_set(cls, new_items):
        return new_items

    @staticmethod
    def kernel_set_type() -> str:
        return "hash:ip"

    @staticmethod
    def set_type() -> type:
        return IPAddress


class IPNetHandler(IPSetHandler):
    @classmethod
    def preprocess_item_set(cls, new_items):
        return set(cidr_merge(new_items))

    @staticmethod
    def kernel_set_type() -> str:
        return "hash:net"

    @staticmethod
    def set_type() -> type:
        return IPNetwork

