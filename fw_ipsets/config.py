from enum import Enum
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class IPSetType(str, Enum):
    NET = "net"
    IP = "ip"


class IPSetDefinition(BaseModel):
    name: str
    type: IPSetType
    kernel_opts: list[str] = Field(alias='kernel-opts')
    source: Path


class Config(BaseModel):
    temp_suffix: str = Field(alias='temp-suffix')
    ipsets: List[IPSetDefinition]