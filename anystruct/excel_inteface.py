'''
Deprecated shim - the PULS Excel interface now lives in the standalone
ANYbuckling package (anybuckling.puls.excel). Requires xlwings.
'''
from anybuckling.puls.excel import ExcelInterface

__all__ = ["ExcelInterface"]
