from .nyse import NyseAdapter
from .nasdaq import NasdaqAdapter
from .opra import OpraAdapter
from .cme import CmeAdapter

ADAPTERS = {
    "NYSE": NyseAdapter,
    "NASDAQ": NasdaqAdapter,
    "OPRA": OpraAdapter,
    "CME": CmeAdapter,
}

__all__ = ["ADAPTERS", "NyseAdapter", "NasdaqAdapter", "OpraAdapter", "CmeAdapter"]
