![picture](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure_logo.jpg)

# ANYstructure #
ANYstructure is the ultimate steel structure design tool for plate fields and cylinders! 
Weight, weld and cost optimization.
Calculations are based on DNV standards and recommended practices.

### What's new in 6.1.1 ### 
* Urgent fix for cylindrical shell updates where hidden cone defaults could overwrite radius, ring spacing and shell lengths.
* 3D CAD export dialog now includes a transformation scale input and keeps intermediate IFC files unchecked by default.
* 3D solid export can write one joined IFC product without building a heavy global boolean union.

### What's new in 6.1.0 ###
* Simplified GUI input option.
* Weld/weight optimization.
* Cost optimization.
* 3D representation of panels/cylinders.
* Improved Semi-analytical buckling implementation.
* Optimization of stiffened plate with girder.
* Bug fixing.
* Export 3D shell model.
* SciPy Differential Evolution Optimizer added.

### What's new in 6.0.3 ###
* New buckling method: Semi-analytical buckling for flat plates.
* Updated ML buckling to numerical instead of classification. Improved accuracy of the neural network.
* Updated color coding option.
* Implemented extended testing regime.
* Started work on separating calculation code from the GUI.
* Python 3.14 supported.
* Addressed some calculation bugs.
* Updated API.

------------------------------------------------------------------------

For documentation:

https://anystructure.readthedocs.io/en/latest/

For tutorials:

https://www.youtube.com/@ANYopenSoft

## Development setup ##

ANYstructure is currently maintained as a Python package named `anystruct`. The GUI can still be launched through the `ANYstructure` console command after an editable install.

Recommended local setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e C:\Github\ANYsolver
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest
```

`ANYsolver>=0.1,<0.2` is a required runtime dependency. The editable sibling
install above is used when developing both repositories; released installs
resolve the same version range from PyPI.

Launch the desktop app after installation:

```powershell
ANYstructure
```

Dependency groups are also available for focused installs:

```powershell
python -m pip install -r requirements-core.txt
python -m pip install -r requirements-ml.txt
python -m pip install -r requirements-excel.txt
```

Equivalent package extras are exposed as `core`, `ml`, `excel`, `dev`, and `all`. The default package install still includes Excel and ML dependencies for backwards compatibility.

Excel project import requires a local Excel installation and is not expected to run in basic automated tests.
The external Excel-sheet DNV PULS calculation workflow has been removed from this release; ML-CL remains available.

## The following is calculated: ##
* Minimum plate thickness (DNV-OS-C101)
* Minimum section modulus of stiffener/plate (DNVGL-OS-C101)
* Minimum shear area (DNVGL-OS-C101)
* Buckling (DNVGL-RP-C201)
* Buckling strength of shells DNV-RP-C202
* Machine learning buckling, PULS based
* Semi-analytical buckling
* Fatigue for plate/stiffener connection (DNVGL-RP-C203)


Compartments (tank pressures) are created automatically.

Pressures on external hull (or any other generic location) is defined by specifying equations.

You can optimize cylinders, single plate/stiffener field or multiple. Geometry of double bottom can be optimized.

PLEASE CONTRIBUTE. REPORT BUGS ERRORS ETC.
For windows executable (.exe) version for non-coders, use the link below.

Feedback: audunarn@gmail.com or discuss on github.

Please like, share or comment on LinkedIn: https://www.linkedin.com/in/audun-arnesen-nyhus-6aa17118/

Screenshot (this example can be loaded from file "ship_section_example.txt"):

![picture](https://github.com/audunarn/ANYstructure/blob/master/anystruct/images/ANYstructure%20screenshot.png)
