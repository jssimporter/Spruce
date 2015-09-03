# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased][unreleased]
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

[unreleased]: https://github.com/sheagcraig/yo/compare/2.0.0...HEAD
[2.0.0]: https://github.com/sheagcraig/auto_logout/compare/1.0.1...2.0.0
[1.0.1]: https://github.com/sheagcraig/auto_logout/compare/0.1.0...1.0.1
