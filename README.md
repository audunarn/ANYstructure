# ANYstructure #
### What's new in 2.6 ###
* PULS (Panel Ultimate Limit State) is now integrated as an option for buckling calculations. PULS is a licenced DNV software.
* GUI improvements.
* Changing of multiple variables.
### What's new in 2.5 ###
* Resizing of window and different resolutions now works better.
* More color coding options.
### What's new in 2.4 ###
* Color coding.
* Updated documentation.
* Improved multiple optmization harmonizer.
* Improved report generator.
### What's new in 2.3 ###
* Span optimizer bug fixed.
* Stress scaling caused somewhat consevative results. Fixed.
* Arrow navigation added.
* GUI modificaitons.
* Multiple optmization improved.
### What's new in 2.2 ###
* GUI updates
* Shortcut updates
* Harmonization option for multiple optimization
* z* toggle on/off
* Lots of minor bug fixing, no known bugs at the moment
### What's new in 1.91 ###
* Corrected a bug when saving tank grid.
### What's new in 1.8 ###
* Fixed an issue with tank identification for lines.
* Small update to example file.
* Opened file displayed at top.
### What's new in 1.6 ###
* Change load factors option added.
* Improved load information.
* External pressures GUI improved.
* Updated documentation.
### What's new in 1.4 ###
* Had to downgrade scipy. Caused error when starting the exe.
* Updated to python 3.9.1
* Significantly smaller install file.
### What's new in 1.3 ###
* Updated documentation.
* HAPPY NEW YEAR!
### What's new in 1.2 ###
* Switched to python 3.8 64 bit (previously 3.4 32 bit)
* Load case information button. Now you can see how pressures are calculated.
* Delete and copy line properties included. Significantly speed up modelling.
* Bug fixed w.r.t. saving and loading files.
* Bug fixed w.r.t. compartment search displaying.
* Known bugs: recording of new section properties sometimes diplays wrong.
### What's new in 1.1 ###
* Also found here: https://github.com/audunarn/ANYstructure/releases/tag/1.1
* Nothing new, just bugfix. Predefined stiffener example file was empty. 
* Smaller install file
### What's new in 1.0 ###
* Time to realize that ANYstructure is stable! This is the first non-beta version.
* New GUI colors.
* Can now use delete button for lines and points.
* Updated documentation.
### What's new in 0.7.0 ###
* You can now export point, lines, beam sections to SESAM GeniE! Beams will also be created with the corresponding section properties.
* Beam section are now recorded and can be accessed in a drop down menu.
### What's new in 0.6.5 ###
* Minor update. Included span vs. weight comparison graph.
### What's new in 0.6.4 ###
* ANYinsight! No more black box results. Now both visualize and print results for all panels in optimization.
* Span optimization furhter corrected. Iterating with predefined stiffeners gives lower running times.
* Weight filter can be turned on and off.
* Control of frame/girder weight calculation in optimization modules.
* Lots of bug-fixing.
* Control number of CPUs to be used in calculations.
### What's new in 0.5.6 ###
* Correction in buckling calculations.
* Span optimization saving and result presenting improvements.
### What's new in 0.5.3 ###
* Span optimization now works better.
* You can now provide a list of stiffeners (L/T/FB) to iterate over when optimizing.
* Number of processors to use can now be specified.
* You can now deselect checking toward local buckling of stiffeners.
* Some bugs fixed.

------------------------------------------------------------------------

GUI based steel structure calculation tool.
 
## The following is calculated: ##
* Minimum plate thickness (DNVGL-OS-C101)
* Minimum section modulus of stiffener/plate (DNVGL-OS-C101)
* Minimum shear area (DNVGL-OS-C101)
* Buckling (DNVGL-RP-C201)or PULS (licenced DNV software)
* Fatigue for plate/stiffener connection (DNVGL-RP-C203)

Compartments (tank pressures) are created automatically.

Pressures on external hull (or any other generic location) is defined by specifying equations.

You can optimize single plate/stiffener field or multiple.

PLEASE CONTRIBUTE. 
For windows executable (.exe) version for non-coders, use the link below.
Note that I am looking for contributions. Non-coders can verify, make documentation, suggest improvements etc. Point
is: please do more than just use the tool and stay silent :)

Feedback: audunarn@gmail.com or discuss on github.

Please like, share or comment on LinkedIn: https://www.linkedin.com/in/audun-arnesen-nyhus-6aa17118/

Screenshot (this example can be loaded from file "ship_section_example.txt"):

![picture](https://docs.google.com/uc?id=1HJeT50bNJTLJbcHTfRke4iySV8zNOAl_)