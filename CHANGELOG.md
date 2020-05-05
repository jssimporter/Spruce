# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased][unreleased]

## [3.0.0b5] - 2020-02-03 Kawaii
### CHANGED
- Emoji are no longer shown unless the new `--kawaii` argument is passed at the command line.
- Emoji are rendered differently in python 2 and 3. This is to deal with attempted fixes in 
  versions 3.0.0b3 and 3.0.0b4 which were only partially successful.

## [3.0.0b2] - 2020-02-03 Bruce Lee Spruce Three
### CHANGED
- Now requires python-jss 2.1.0 or above,
  as installed via JSSImporter 1.1.0 or above,
  i.e. in the folder `/Library/AutoPkg/JSSImporter`.
  Also requires Python3, best run using the AutoPkg-supplied python3 binary:
  `/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 ./spruce.py -h`
  python-jss installed from `pip` or from source will be ignored.
- The default preferences are now taken directly from the AutoPkg preferences,
  i.e. `com.github.autopkg`.
- A few updates to the code were required to function with python3 and to accommodate
  upstream changes to python-jss.
  

## [3.0.0b1] - 2019-08-18 Alpine Spruce (Picea alpestris)
### CHANGED
- Now requires python-jss 2.0.0 or above,
  as installed via JSSImporter 1.0.0 or above,
  i.e. in the folder `/Library/Application Support/JSSImporter`.
  python-jss installed from `pip` or from source will be ignored.
- The default preferences are now taken directly from the AutoPkg preferences,
  i.e. `com.github.autopkg`.
- Various sections of code had to be refactored to function with the upstream
  changes to python-jss (and for @GrahamPugh to understand it...)

### ADDED
- The JSS name is outputted during execution, to verify the correct Preferences
  are being used.


## [2.0.1] - 2016-06-22 White Spruce (Picea glauca)
### Fixed
- Now handles JSSGetError when trying to do a JDS delete during removal (#6).

## [2.0.0] - 2015-09-01 Green Dragon Spruce (Picea retroflexa)
### CHANGED
- Renamed python source to `spruce.py` to follow PEP8 recommendations.
- Restructured arguments to prevent reporting and removal from happening at the same time.
- Refactored to support running individual subreports (e.g. `--packages`, `--scripts`).
- With no arguments, spruce runs as if `--all` had been specified (meaning run all reports).
- Reimplemented removals to use an XML file. See the documentation for details on the structure of this file.
- All object queries that support the subset feature of the API now do so to minimize traffic.
- Edited README to document the 2.0 features.

### ADDED
- Added cute conifers.
- Added Computer Group report.
- Add cruftiness score, and other metadata.
- Added Policy report.
- Added Computer Configuration Profile Report.
- Added Mobile Device Group Report.
- Added Computer Report.
- Added Mobile Device Report.
- Added Mobile Device Configuration Profile Report.
- Added Ranks (levels of cruftiness).
- Added histograms (used for things like version spread).
- Added Mobile Device Application report.
- Added XML output option. This is now the easiest way to generate output for later deletion.
- Added specific descriptions of the reports.
- Objects which somehow have no name can no longer hide!

### REMOVED
- No longer allows old-style of removal file. (See docs for XML format).
- Removed full-auto report and clean options.

## [1.0.1] - 2015-05-04 Chihuahua Spruce (Picea chihuahuana)
### CHANGED
- Just code style updates.

## [0.1.0] - 2015-02-05 Norwegian Spruce (Picea abies)
Initial Release.

[unreleased]: https://github.com/sheagcraig/spruce/compare/2.0.1...HEAD
[2.0.1]: https://github.com/sheagcraig/spruce/compare/2.0.0...2.0.1
[2.0.0]: https://github.com/sheagcraig/spruce/compare/1.0.1...2.0.0
[1.0.1]: https://github.com/sheagcraig/spruce/compare/0.1.0...1.0.1
