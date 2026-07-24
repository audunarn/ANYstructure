'''
Deprecated shim - the semi-analytical S3/U3 panel solver now lives in
the standalone ANYbuckling package (anybuckling.semianalytical.solver).

This module aliases the ANYbuckling solver module so that every existing
import (public and private names alike) keeps working:

    import anystruct.calculate_semianalytical as semi_analytical
'''
import sys as _sys

from anybuckling.semianalytical import solver as _solver

_sys.modules[__name__] = _solver

if __name__ == "__main__":
    raise SystemExit(_solver.main())
