#!/usr/bin/python
import os
import subprocess
import sys, getopt
import json
import datetime
import requests
from datetime import tzinfo, timedelta, datetime, date
import time
import pathlib
import glob
import shutil

MODE_SINGLE = 0
MODE_MULTIPLE = 1
MODE_SERIES = 2
INDEX_FILE = "index.json"
CATALOG_FILE = "catalog.json"

VerboseFlag = False
SongId = 1
SongList = []
ConvertMode = 0;
FolderBase = 0
SourceFolder = ""
TargetFolder = ""
SimFlag = False
FolderTag = ""
CleanFlag = False
IndexFlag = False
CatalogFlag = False

#------------------------------------------------------------------------------
# Common Functions
#------------------------------------------------------------------------------    
def IsLinux():  
  if os.name == 'nt':
    st = False
  else:
    st = True
  return st
  
def Exec(cmd):
  global VerboseFlag
  if VerboseFlag:
    print("Exec: %s" % (cmd))
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
  (output, err) = p.communicate()
  status = p.wait()
  if VerboseFlag:
    print(output)
    print("Status=%d" % (status))
  return status, output

def WriteTextFile(fn, text):
  fp = open(fn, "w")
  fp.write(text)
  fp.close()    

def ReadTextFile(fn):
  if os.path.exists(fn):
    fp = open(fn, 'r')
    data = fp.read()  
    fp.close()
  else:
    data = False
  return data

def WriteJsonFile(fn, obj):
  jstr = json_encode(obj)
  WriteTextFile(fn, jstr)

def ReadJsonFile(fn):
  if os.path.exists(fn):
    jstr = ReadTextFile(fn)
    obj = json_decode(jstr)
  else:
    obj = {}
  return obj
  
def DeleteFile(fn):
  if os.path.isfile(fn):
    os.remove(fn)

def MakeFolder(folder):
  if not os.path.exists(folder):
    os.makedirs(folder)

def MoveFile(src, dest):
  dir = os.path.dirname (dest)
  MakeFolder(dir)
  os.rename(src, dest)

def json_encode(data):
  return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
  
def json_decode(data):
  return json.loads(data)

def isset(variable):
  st = True
  try:
    variable
  except NameError:
    st = False
  return st
  
def ReadFileToArray(fn):
  with open(fn) as f:
    lines = f.readlines()
    f.close()
  return lines

def WriteArrayToFile(fn, lines):
  fo = open(fn, "w")
  line = fo.writelines(lines)
  fo.close()

def GetFileMTime(fn):
  mtime = os.stat(fn).st_mtime
  return mtime

def SetFileMTime(fn, mtime):
  os.utime(fn, (mtime, mtime))

#
# filename        => '/path/to/somefile'
# file_extension  => '.ext'
#
def GetFileExtension(fn):
  filename, file_extension = os.path.splitext(fn)
  return file_extension

def RemoveComments(lbuf):
  p = lbuf.find("#")
  if p != -1:
    lbuf = lbuf[:p]
  return lbuf

def GetFileSize(fn):
  return os.path.getsize(fn)

def GetFileTime(fn):
  mtime = os.path.getmtime(fn)
  return mtime

def mkdirr(folder):
  if os.path.exists(folder) == False:
    os.mkdir(folder);

#------------------------------------------------------------------------------
# Find functions
#------------------------------------------------------------------------------
def EmptyFolderNest(base, rpath):
  dir = os.path.join (base, rpath)
  print("----------------------------------------")
  print(" Empty Folder [%s]" % (dir))
  print("----------------------------------------")
  for file in os.listdir(dir):
    full = os.path.join (dir, file)
    if (os.path.isdir(full)):
      EmptyFolderNest(base, os.path.join(rpath, file))
      os.rmdir(full)
      print("Remove folder [%s]" % full);
    else:
      print("Remove file [%s]" % full);
      os.remove(full) 
        
def EmptyFolder(folder):
  if os.path.isdir(folder):
    EmptyFolderNest(folder, "");

def ConvertNest(args, rpath):
  global VerboseFlag

  base = args["Base"]
  target_folder = args["Target"]
  mode = args["Mode"]
  level = args["Level"]
  folder_tag = args["FolderTag"]
  result = False  
  mkdirr(target_folder)
  
  if mode == MODE_SINGLE:
    output_folder = target_folder
  elif mode == MODE_MULTIPLE:
    args["SongId"] = 1
    args["SongList"] = []
    output_folder = os.path.join(target_folder, str(args["FolderId"]));    
    print("output_folder="+output_folder)
    if os.path.isdir(output_folder) == False:
      os.mkdir(output_folder)
  elif mode == MODE_SERIES:
    if level == 1:
      args["SongId"] = 1
      args["SongList"] = []
    output_folder = os.path.join(target_folder, str(args["FolderId"]));
  else:
    print("Error: Unsupport Mode [%d]" % (mode))
    pass
  mkdirr(output_folder)
  
  dir = os.path.join (base, rpath)  
  print("----------------------------------------")
  print(" Folder [%s]" % (dir))
  print("----------------------------------------")
  for file in sorted(os.listdir(dir)):
    full = os.path.join(dir, file)
    if (os.path.isdir(full)):
      if mode == MODE_MULTIPLE or (mode == MODE_SERIES and level == 0):
        backup_song_id = args["SongId"]
        args["SongId"] = 1
      args["Level"] = args["Level"] + 1
      ConvertNest(args, os.path.join(rpath, file))
      args["Level"] = args["Level"] - 1
      if mode == MODE_MULTIPLE:
        args["SongId"] = backup_song_id      
    else:
      ext = GetFileExtension(file)
      if ext.lower() == ".mp3":
        if mode == MODE_SINGLE or mode == MODE_SERIES:
          new_full = "%s#%s,%s" % (str(args["SongId"]).zfill(3), rpath, file)
        elif mode == MODE_MULTIPLE:
          new_full = "%s#%s" % (str(args["SongId"]).zfill(3), file)          
        new_full = new_full.replace("/", "_")
        args["SongList"].append(new_full)
        args["SongId"] = args["SongId"] + 1
        new_full = os.path.join(output_folder, new_full)
        if VerboseFlag:
          print(full)
          print(new_full)
        if SimFlag == False:
          shutil.copyfile(full, new_full)

  #
  # Write folder information file
  #
  update_index = False
  if len(args["SongList"]) > 0:
    if mode == MODE_SINGLE and level == 0:
      update_index = True
    elif mode == MODE_MULTIPLE:
      update_index = True      
    elif mode == MODE_SERIES and level == 1:
      update_index = True
  
  if update_index:
    if IndexFlag:
      index_file = os.path.join(output_folder, INDEX_FILE)
      index = {}
      index["Folder"] = rpath
      index["Files"] = args["SongList"]
      index["Tag"] = folder_tag
      WriteJsonFile(index_file, index)
    args["SongList"] = []
    args["SongId"] = 1

  #
  # Increment FolderId
  #
  if mode == MODE_MULTIPLE:
    args["FolderId"] = args["FolderId"] + 1
  elif mode == MODE_SERIES and level == 1:
    args["FolderId"] = args["FolderId"] + 1
    
  return result

def WriteLineArrayToFile(lines, fn):
  with open(fn, 'w') as f:
    for line in lines:
      f.write("%s\n" % line)
        
def ConvertFolder(src, dst):
  global TargetFolder
  global CatalogData
  global CatalogFlag
  global ConvertMode
  global FolderBase
  global FolderTag
  #
  # Clean folder if need
  #
  if CleanFlag:
    EmptyFolder(dst)
  #
  # Scan folder and convert
  #  
  args = {}
  args["Mode"] = ConvertMode
  args["Base"] = src
  args["Target"] = dst  
  args["Level"] = 0
  args["FolderId"] = FolderBase
  args["FolderTag"] = FolderTag
  args["SongId"] = 1
  args["SongList"] = []
  ConvertNest(args, "")

def BuildIndexFile(song_folder):
  global FolderTag
  global IndexFlag
  create_flag = False
  index_file = os.path.join(song_folder, INDEX_FILE)
  if os.path.exists(index_file) == False:
    create_flag = True
  
  if create_flag:
    print("BuildIndexFile [%s]" % (index_file))
    song_list = []
    for file in sorted(os.listdir(song_folder)):
      full = os.path.join(song_folder, file)
      if (os.path.isdir(full)):
        pass
      else:
        ext = GetFileExtension(file)
        if ext.lower() == ".mp3":
          song_list.append(file)
    if IndexFlag == True and len(song_list) > 0:
      obj = {}
      obj["Files"] = song_list
      obj["Folder"] = ""
      obj["Tag"] = [FolderTag]
      WriteJsonFile(index_file, obj)
      
#
# Build index file if not exists
#
def BuildCatalogFile(target_folder):
  global CatalogFlag
  catalog_data = {}
  for file in sorted(os.listdir(target_folder)):
    full = os.path.join(target_folder, file)
    if (os.path.isdir(full)):
      BuildIndexFile(full)
    else:
      pass
    index_file = os.path.join(full, INDEX_FILE);
    if os.path.exists(index_file):
      index_obj = ReadJsonFile(index_file)
      catalog_data[file] = index_obj
  if CatalogFlag:
    catalog_file = os.path.join(target_folder, CATALOG_FILE)
    WriteJsonFile(catalog_file, catalog_data);

#------------------------------------------------------------------------------
# Main 
#------------------------------------------------------------------------------
def Usage():
    print('python3 DfPlayerFolderManager.py -b 10 -s SourceFolder -t TargetFolder -m 1')
    print('   -c            Convert source folder to target folder')
    print('   -m,--mode     Specify folder convert mode')
    print('                 0: Single Folder (Default)')
    print('                 1: Multiple Folder')
    print('   -b,--base     Specify base folder id')
    print('   -s,--source   Specify source folder')
    print('   -t,--target   Specify target folder')
    print('   --tag xxx     Specify folder tag')
    print('   --catalog     Build catalog file')
    print('   --index       Build index file')    
    print('   -v            Verbose')

def main(argv):
  global VerboseFlag
  global ConvertMode
  global FolderBase
  global SourceFolder
  global TargetFolder
  global SimFlag
  global FolderTag
  global CatalogFlag
  global CleanFlag
  global IndexFlag
  global CatalogFlag
  
  VerboseFlag = False
  TestFlag = False
  CleanFlag = False
  ConvertFlag = False
  ConvertMode = 0                       # 0: Single Folder, 1: Multiple Folder
  FolderBase = 0
  SourceFolder = False
  TargetFolder = False
  
  try:
    opts, args = getopt.getopt(argv,"cb:s:t:m:h",["source=", "target=", "base", "mode", "tag=", "catalog", "index", "clean", "sim"])
  except getopt.GetoptError:
    Usage()
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      Usage()
      sys.exit()
    elif opt == "-c":                 # Password
      ConvertFlag = True
    elif opt in ("-b", "--base"):     # Base
      FolderBase = int(arg)
    elif opt in ("-m", "--mode"):     # Mode
      ConvertMode = int(arg)
    elif opt in ("-s", "--source"):   # Source
      SourceFolder = arg
    elif opt in ("-t", "--target"):   # Target
      TargetFolder = arg
    elif opt in ("--clean"):          # Clean
      CleanFlag = True
    elif opt in ("--tag"):            # Tag
      FolderTag = arg
    elif opt in ("--catalog"):        # Catalog
      CatalogFlag = True
    elif opt in ("--index"):          # Index
      IndexFlag = True
    elif opt in ("--sim"):            # Simulation
      SimFlag = True
    elif opt in ("-t"):               # Test Code
      TestFlag = True
    else:
      print ("Unknow options", opt, arg)
  
  print("Folder Base    = %d" % (FolderBase))
  print("Convert Mode   = %d" % (ConvertMode))
  print("Source Folder  = %s" % (SourceFolder))
  print("Target Folder  = %s" % (TargetFolder))
  print("Folder Tag     = %s" % (FolderTag))
  print("Clean Flag     = %d" % (CleanFlag))
  print("Verbose Flag   = %d" % (VerboseFlag))
  print("Catalog Flag   = %d" % (CatalogFlag))
  print("Index Flag     = %d" % (IndexFlag))

  if SourceFolder == False or TargetFolder == False:
    print("Error: -s xxx and -t xxx is rquired")
    sys.exit(2)
    
  #
  # Prcess Route
  #
  if ConvertFlag != False:
    if CleanFlag:
      EmptyFolder(TargetFolder)
    ConvertFolder(SourceFolder, TargetFolder)
        
  if CatalogFlag:
    BuildCatalogFile(TargetFolder)

  if TestFlag != False:
    # db_list = GetDatabaseList()
    # print(db_list)
    pass
    
if __name__ == "__main__":
   main(sys.argv[1:])
   