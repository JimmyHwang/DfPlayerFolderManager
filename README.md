# DfPlayerFolderManager

DfPlayerFolderManager is a tool for convert song folder structure for MP3-TF-16P

## Features

- Support specify source/target folder
- Support 3 mode folder strucutre
- Build folder index file after build folder completed
- Support apply specify to index of folder
- Support keep origin folder structure when the folder is marked "System" in index.json
- Support build data version of SD

## Installation

DfPlayerFolderManager requires python 2.x or 3.x

## Usage
```
python3 DfPlayerFolderManager.py -s Source -t Target -c -m 0
```
  * -m,--mode     Specify output folder mode
    * Mode 0: Single Mode, All songs in a folder
    * Mode 1: Multiple Mode, Copy each source folder in target folder.
    * Mode 2: Series Mode, All songs of Series in a folder.
  * -s,--source xxx     Specify source folder
  * -t,--target xxx     Specify target folder
  * -m,--mode           Specify output folder mode
  * --tag xxxx          Specify tag of folder in index file
  * --ver xxxx          Specify Data Version

## Examples
```
  [Source]
    [1997_AAAA]
    [1998_BBBB]
      [1998_CD1]
      [1998_CD2]
  [Target] with mode 0 (Single Mode)
    10/001#AAAA.mp3
       002#BBBB_CD1.mp3
       003#BBBB_CD2.mp3
  [Target] wirh mode 1 (Multiple Mode)
    10/001#AAAA.mp3
    11/001#BBBB_CD1.mp3
    12/001#BBBB_CD2.mp3
  [Target] wirh mode 2 (Series Mode)
    10/001#AAAA.mp3
    11/001#CD1.mp3
       002#CD2.mp3
```
