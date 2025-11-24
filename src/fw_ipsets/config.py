# SPDX-License-Identifier: BSD-2-Clause

from enum import Enum
from pathlib import Path
from typing import List, Literal, Union, Annotated

from pydantic import BaseModel, Field


class IPSetType(str, Enum):
    NET = "net"
    IP = "ip"


class IPSetDefinition(BaseModel):
    backend: Literal["ipset"]
    name: str
    type: IPSetType
    kernel_opts: list[str] = Field(alias='kernel-opts')
    source: Path


class NFTSetDefinition(BaseModel):
    backend: Literal["nft"]
    name: str
    family: str = "ip"
    table: str
    type: IPSetType
    kernel_opts: list[str] = Field(alias='kernel-opts')
    source: Path


class Config(BaseModel):
    temp_suffix: str = Field(alias='temp-suffix')
    ipsets: List[Annotated[IPSetDefinition | NFTSetDefinition, Field(discriminator='backend')]]