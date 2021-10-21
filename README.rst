============
ANYstructure
============

Save cost and time by efficient optimization and reporting!

ANYstructure is a GUI based steel dimension calculation and weight optimization tool intended for naval architects
structural engineers. It is easy to used intended to provide an efficient way to dimension and optimize
your floating structure.

It is based on DNV-OS-C101 Design of offshore steel structures, general - LRFD method.

The following is caluculated:

* Minimum section module for stiffener
* Minimum plate thickness
* Buckling capacity (DNV-RP-C201 Buckling Strength of Plated Structures), PULS (licenced DNV software)
  and Machine Learning buckling calculations.
* Plate/stiffener connection fatigue (DNV-RP-C203: Fatigue Design of Offshore Steel Structures)
* Bow slamming according to DNVGL ship rules
* Weights, COG, COB. Development recorded for reporting.

Loads are defined as follows:

* External surface loads defined by polynominal equations
* Tank loads are calculated automatically

Loads are combined according to DNVGL-OS-C101.

Installation
------------

The easiest way to install the package is via pip::

    $ pip install anystructure

Usage
-----

An entry point is defined. After installing on PIP, just type "ANYstructure" in the command window.

Alternatively run \_\_main\_\_.py

Documentation
-------------

Documentation is cointained in the tool. Help -> Open documentation.
