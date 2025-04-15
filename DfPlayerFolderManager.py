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
ConvertMode = 0;
FolderBase = 0
SourceFolder = ""
TargetFolder = ""
SimFlag = False
FolderTag = ""
CleanFlag = False
IndexFlag = False
CatalogFlag = False
DataVersion = False
VersionFolder = 99
ConfigFile = False
ConfigData = False
VersionFileFolder = 1
VersionFileTrack = 1
DebugFlags = 0

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

def StringToInt(str):
  if "0x" in str:
    result = int(str, 16)
  else:
    result = int(str)
  return result

#------------------------------------------------------------------------------
# Folder/File Common Functions
#------------------------------------------------------------------------------
def GetFirstPathNode(full):
  separator = "/"
  items = full.split("/") 
  path_node = False
  remind_nodes = []
  for item in items:
    if path_node != False:
      remind_nodes.append(item)
    elif item != ".":
      path_node = item  
  if len(remind_nodes) == 0:
    remind_path = "."
  else:
    remind_path = separator.join(remind_nodes)
  return path_node, remind_path
  
#------------------------------------------------------------------------------
# Folder/File Class
#------------------------------------------------------------------------------
class ENTRY_CLASS:
  def __init__(self, full, type):
    self.Full = full;
    self.Name = os.path.basename(full)
    self.Type = type            # 0: File, 1:Dir
    
class FILE_CLASS(ENTRY_CLASS):
  def __init__(self, full):
    global DebugFlags
    super().__init__(full, 0)
    if DebugFlags and 1:
      print("#"+full)
    
class FOLDER_CLASS(ENTRY_CLASS):  
  def __init__(self, full, level = 0):
    global DebugFlags
    super().__init__(full, 1)
    if DebugFlags and 1:
      print("@"+full)
    self.List = []
    self.Level = level
  
  def Build(self):
    flist = os.listdir(self.Full)
    for f in flist:
      full = os.path.join(self.Full, f)
      if (os.path.isdir(full)):
        fobj = FOLDER_CLASS(full, self.Level+1)
        fobj.Build()
        self.List.append(fobj)
      else:
        fobj = FILE_CLASS(full)
        self.List.append(fobj)        
  
  def GetMatchItem(self, name):
    result = False
    for item in self.List:
      if name == item.Name:
        result = item
    return result
  
  def Dump(self, rpath = ""):
    # print("Dump() - "+rpath)
    for item in self.List:
      full = os.path.join(rpath, item.Name)
      if item.Type == 1:
        print("["+item.Name+"] - "+full)
        item.Dump(rpath + "/" + item.Name)
      else:        
        print(full, "(Full="+item.Full+")")

  def GetFileObj(self, rpath, flags = 0):
    fobj = False
    if rpath == ".":
      fobj = self
    else:
      path_node,remind_path = GetFirstPathNode(rpath)
      if path_node != False:
        item = self.GetMatchItem(path_node)
      #
      # Process match file or next level path
      #
      if item == False:                   # Not found
        pass
      elif remind_path == ".":            # is last node
        fobj = item
      else:
        fobj = item.GetFileObj(remind_path)
    return fobj

  def GetFilePath(self, rpath):
    full = False
    fobj = self.GetFileObj(rpath)
    if fobj != False:
      if fobj.Type == 0:
        full = fobj.Full
    return full
    
  def isdir(self, rpath):
    st = False
    fobj = self.GetFileObj(rpath)
    if fobj != False:
      if fobj.Type == 1:                # is dir type
        st = True
    return st
    
  def isfile(self, rpath):
    st = False
    fobj = self.GetFileObj(rpath)
    if fobj != False:
      if fobj.Type == 0:                # is file type
        st = True
    return st

  def exists(self, rpath):
    st = False
    fobj = self.GetFileObj(rpath)
    if fobj != False:
      st = True
    return st
    
  def mkdir(self, rpath):
    if rpath != ".":
      path_node,remind_path = GetFirstPathNode(rpath)
      if path_node != False:
        fobj = self.GetMatchItem(path_node)
        if fobj == False:
          fobj = FOLDER_CLASS(path_node, self.Level+1)
          self.List.append(fobj)
        fobj.mkdir(remind_path)          
    
  def listdir(self, rpath):
    flist = False    
    if rpath == ".":
      flist = []
      for item in self.List:
        flist.append(item.Name)      
    else:
      fobj = self.GetFileObj(rpath)
      if fobj != False:
        if fobj.Type == 1:
          flist = fobj.listdir(".")
    return flist
    
  def RemoveFile(self, rpath):
    st = False
    path_node,remind_path = GetFirstPathNode(rpath)
    if path_node != False:
      item = self.GetMatchItem(path_node)
    #
    # Process match file or next level path
    #
    if item == False:                   # Not found
      pass
    elif remind_path == ".":            # is last node
      if item.Type == 0:                # is file type
        index = self.List.index(item)
        del self.List[index]
        st = True
    else:
      st = item.RemoveFile(remind_path)
    return st
    
  def AddFile(self, base, rpath):
    st = False
    path_node,remind_path = GetFirstPathNode(rpath)
    if path_node != False:
      if remind_path == ".":            # create file
        full = os.path.join(base, path_node)
        if os.path.isfile(full):
          fobj = self.GetMatchItem(path_node)
          if fobj == False:
            fobj = FILE_CLASS(full)
            self.List.append(fobj)
          else:
            fobj.Full = full
          st = True
        else:
          print("ERROR: [%s] not found" % full)
      else:                             # create dir        
        full = os.path.join(self.Full, path_node)
        fobj = self.GetMatchItem(path_node)
        if fobj == False:
          fobj = FOLDER_CLASS(full, self.Level+1)
        full = os.path.join(base, path_node)
        st = fobj.AddFile(full, remind_path)
    return st 

  #
  # Merge from sobj
  #
  def Merge(self, sroot):
    st = False
    level = self.Level;
    spcs = GetSpaceStringN(level)
    for sobj in sroot.List:
      # print("sobj.Name [%s]" % (sobj.Name))
      # print("sobj.Type = %d" % (sobj.Type))
      fobj = self.GetMatchItem(sobj.Name)
      if fobj == False:                 # Not exists        
        if sobj.Type == 1:              # New Folder
          fobj = FOLDER_CLASS(sobj.Name, level+1)
          fobj.Merge(sobj)
          print("%s[%d]Merge: Merge Folder [%s]" % (spcs, level, sobj.Full)) 
        else:                           # New File
          fobj = FILE_CLASS(sobj.Full)
          print("%s[%d]Merge: Add File [%s]" % (spcs, level, sobj.Full)) 
        self.List.append(fobj)
      else:                             # Exists
        if fobj.Type == 1:              # Folder Exists
          fobj.Merge(sobj)
        else:                           # File Exists
          fobj.Full = sobj.Full
  
  def ReadTextFile(self, rpath):
    data = False
    fobj = self.GetFileObj(rpath)
    if fobj != False:
      if fobj.Type == 0:
        data = ReadTextFile(fobj.Full)
    return data

  def WriteTextFile(self, rpath, data):
    pass

  def ReadJsonFile(self, rpath):
    obj = {}
    jstr = self.ReadTextFile(rpath)
    if jstr != False:
      obj = json_decode(jstr)
    return obj

  def WriteJsonFile(self, rpath, data):
    pass
    
#
#
#
def GetSpaceStringN(level):
  line = ""
  for i in range(level):
    line = line + " "
  return line
  
def LoadVirtualFolder(vcfg, level = 0):
  global DebugFlags
  vobj = False
  spcs = GetSpaceStringN(level)
  print("%s[%d]LoadVirtualFolder = %s" % (spcs, level, vcfg))
  lines = ReadFileToArray(vcfg)
  for line in lines:
    line = line.strip()
    if DebugFlags & 1:
      print("Parse......[%s]" % line)
    prefix = line[0:1]
    line = line[1:]
    if prefix == "#":
      pass
    elif prefix == "@":
      if os.path.isfile(line):
        print("%s[%d]VCFG Base......%s" % (spcs, level, line))
        vobj = LoadVirtualFolder(line, level+1)
      else:
        print("%s[%d]Folder Base......%s" % (spcs, level, line))
        vobj = FOLDER_CLASS(line)
        vobj.Build()
    elif prefix == "-":
      vobj.RemoveFile(line)
      print("%s[%d]Remove......%s" % (spcs, level, line))
    elif prefix == "+":
      temp = line.split("|")
      if len(temp) == 1:                # Folder
        print("%s[%d]Merge Folder [%s]" % (spcs, level, temp[0]))
        nobj = FOLDER_CLASS(temp[0])
        nobj.Build()
        vobj.Merge(nobj)
      else:                             # File
        base = temp[0]
        rpath = temp[1]
        # print("base="+base)
        # print("rpath="+rpath)
        vobj.AddFile(base, rpath)
        print("%s[%d]Add......%s %s" % (spcs, level, base, rpath))
  return vobj
  
#------------------------------------------------------------------------------
# Find functions
#------------------------------------------------------------------------------
def EmptyFolderNest(base, rpath):
  global VerboseFlag
  dir = os.path.join (base, rpath)
  print("----------------------------------------")
  print(" Empty Folder [%s]" % (dir))
  print("----------------------------------------")
  for file in os.listdir(dir):
    full = os.path.join (dir, file)
    if (os.path.isdir(full)):
      EmptyFolderNest(base, os.path.join(rpath, file))
      os.rmdir(full)
      if VerboseFlag:
        print("Remove folder [%s]" % full);
    else:
      os.remove(full) 
      if VerboseFlag:
        print("Remove file [%s]" % full);
        
def EmptyFolder(folder):
  if os.path.isdir(folder):
    EmptyFolderNest(folder, "");

def IsSystemFolder(vobj, folder):
  st = False
  index_file = os.path.join(folder, INDEX_FILE)
  if vobj.exists(index_file):
    index_cfg = vobj.ReadJsonFile(index_file)
    if "Folder" in index_cfg:
      if index_cfg["Folder"] == "System":
        st = True
  return st
  
def GetMp3FileCount(vobj, base_dir):
  count = 0
  for file in sorted(vobj.listdir(base_dir)):
    full = os.path.join(base_dir, file)
    if (vobj.isdir(full)):
      pass
    else:
      ext = GetFileExtension(file)
      if ext.lower() == ".mp3":
        count = count + 1
  return count

def ConvertNest(args, rpath):
  global VerboseFlag
  global DebugFlags
  
  base = args["Base"]
  target_folder = args["Target"]
  vobj = args["VOBJ"]                   # Create with base
  mode = args["Mode"]
  level = args["Level"]
  folder_tag = args["FolderTag"]
  result = False  
  mkdirr(target_folder)

  if rpath == "":
    base_dir = base
  else:
    base_dir = os.path.join(base, rpath)
    
  if level == 1 and IsSystemFolder(vobj, base_dir):
    print("----------------------------------------")
    print(" System Folder [%s]" % (base_dir))
    print("----------------------------------------")
    dst_folder = os.path.join(target_folder, rpath)
    fobj = vobj.GetFileObj(base_dir)
    if fobj == False:
      print("ERROR: Folder [%s] not found" % (base_dir))
      exit(1)
    else:
      shutil.copytree(fobj.Full, dst_folder, dirs_exist_ok=True)
  else:  
    print("----------------------------------------")
    print(" Folder [%s]" % (base_dir))
    print("----------------------------------------")
    output_folder = os.path.join(target_folder, str(args["FolderId"]));
    origin_folder = False
    if mode == MODE_SINGLE:
      if args["SongId"] == 1:
        origin_folder = "@ALL@"
    elif mode == MODE_MULTIPLE:
      args["SongId"] = 1
      origin_folder = rpath
      print("output_folder="+output_folder)
      if os.path.isdir(output_folder) == False:
        os.mkdir(output_folder)
    elif mode == MODE_SERIES:
      if level == 1:
        args["SongId"] = 1
        args["SongCount"] = 0
        args["OriginFolder"] = rpath
        origin_folder = rpath
      if level >= 1:
        file_count = GetMp3FileCount(vobj, base_dir)
        print("SongsCount=%d, file_count=%d" % (args["SongCount"], file_count))
        if args["SongCount"] + file_count > 255:
          args["FolderId"] = args["FolderId"] + 1
          args["SongId"] = 1
          args["SongCount"] = 0
          origin_folder = args["OriginFolder"]
          output_folder = os.path.join(target_folder, str(args["FolderId"]));          
    else:
      print("Error: Unsupport Mode [%d]" % (mode))
      pass
    mkdirr(output_folder)
    
    for file in sorted(vobj.listdir(base_dir)):
      full = os.path.join(base_dir, file)
      if (vobj.isdir(full)):
        backup_song_id = False
        if mode == MODE_MULTIPLE or (mode == MODE_SERIES and level == 0):
          backup_song_id = args["SongId"]
          args["SongId"] = 1
        args["Level"] = args["Level"] + 1
        ConvertNest(args, os.path.join(rpath, file))
        args["Level"] = args["Level"] - 1
        if backup_song_id != False:
          args["SongId"] = backup_song_id
          backup_song_id = False
      else:
        ext = GetFileExtension(file)
        if ext.lower() == ".mp3":
          if mode == MODE_SINGLE or mode == MODE_SERIES:
            new_full = "%s#%s,%s" % (str(args["SongId"]).zfill(3), rpath, file)
          elif mode == MODE_MULTIPLE:
            new_full = "%s#%s" % (str(args["SongId"]).zfill(3), file)          
          new_full = new_full.replace("/", "_")
          args["SongId"] = args["SongId"] + 1
          args["SongCount"] = args["SongCount"] + 1
          new_full = os.path.join(output_folder, new_full)
          if VerboseFlag:
            print(full)
            print(new_full)
          if SimFlag == False:
            if VerboseFlag:
              print("Copy1 [%s] to [%s]" % (vobj.GetFilePath(full), new_full))
            shutil.copyfile(vobj.GetFilePath(full), new_full)
        elif level == 0:
          new_full = os.path.join(target_folder, file)          
          if VerboseFlag:
            print(full)
            print(new_full)
          if SimFlag == False:
            if VerboseFlag:
              print("Copy2 [%s] to [%s]" % (vobj.GetFilePath(full), new_full))
            shutil.copyfile(vobj.GetFilePath(full), new_full)

    #
    # Write folder information file
    #
    if IndexFlag == True and origin_folder != False:
      source_index_fn = os.path.join(base_dir, INDEX_FILE)      
      target_index_fn = os.path.join(output_folder, INDEX_FILE)
      index_cfg = vobj.ReadJsonFile(source_index_fn)
      index_cfg["Folder"] = origin_folder
      WriteJsonFile(target_index_fn, index_cfg)
    
    #
    # Increment FolderId
    #
    if mode == MODE_MULTIPLE:
      args["FolderId"] = args["FolderId"] + 1
    elif mode == MODE_SERIES and level == 1:
      args["FolderId"] = args["FolderId"] + 1
    
  return result

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
  vobj = LoadVirtualFolder(src)
  src = "."
  args = {}
  args["Mode"] = ConvertMode
  args["Base"] = src
  args["Target"] = dst  
  args["Level"] = 0
  args["FolderId"] = FolderBase
  args["FolderTag"] = FolderTag
  args["SongId"] = 1
  args["VOBJ"] = vobj
  ConvertNest(args, "")

def BuildIndexFile(song_folder):
  global FolderTag
  global IndexFlag
  index_cfg = {}
  song_list = []

  index_file = os.path.join(song_folder, INDEX_FILE)
  if os.path.exists(index_file):
    index_cfg = ReadJsonFile(index_file)
  if "Folder" not in index_cfg:
    index_cfg["Folder"] = ""
  if "Tags" not in index_cfg:
    index_cfg["Tags"] = [FolderTag]
  
  print("BuildIndexFile [%s]" % (index_file))    
  for file in sorted(os.listdir(song_folder)):
    full = os.path.join(song_folder, file)
    if (os.path.isdir(full)):
      pass
    else:
      ext = GetFileExtension(file)
      if ext.lower() == ".mp3":
        song_list.append(file)

  if IndexFlag == True and len(song_list) > 0:
    index_cfg["Files"] = song_list
    WriteJsonFile(index_file, index_cfg)
      
#
# Build index file if not exists
#
def BuildCatalogFile(target_folder):
  global CatalogFlag
  global DataVersion
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
    fn = CATALOG_FILE
    if DataVersion != False:
      fn = "%08X.json" % (DataVersion)
    catalog_file = os.path.join(target_folder, fn)
    WriteJsonFile(catalog_file, catalog_data);

#------------------------------------------------------------------------------
# Version File Functions
#------------------------------------------------------------------------------
def GetFolderId(fn):
  result = False
  num = fn[0:2]
  if num.isnumeric():
    result = int(num)
  return result
  
def GetTrackId(fn):
  result = False
  num = fn[0:3]
  if num.isnumeric():
    result = int(num)
  return result
  
def GetSampleFile(vobj, find_folder_id, find_track_id):
  global SourceFolder
  global VersionFileFolder
  global VersionFileTrack
  result = False
  dir = "."
  for entry in sorted(vobj.listdir(dir)):
    full = os.path.join(dir, entry)
    if vobj.isdir(full):             # Find first folder
      folder_id = GetFolderId(entry)
      if find_folder_id == False or folder_id == find_folder_id:
        folder = full
        for entry in sorted(vobj.listdir(folder)):
          file = entry
          full = os.path.join(folder, entry)
          if vobj.isfile(full):        
            file_id = GetTrackId(entry)
            if find_track_id == False or file_id == find_track_id:
              full = vobj.GetFilePath(full)
              result = full
              break
    if result != False:
      break
  return result
  
def BuildDataVersion(ver_folder, id):
  global SourceFolder
  global TargetFolder
  global VersionFileFolder
  global VersionFileTrack
  
  vobj = LoadVirtualFolder(SourceFolder)
  sfn = GetSampleFile(vobj, VersionFileFolder, VersionFileTrack)
  if sfn == False:
    sfn = GetSampleFile(1, 1)
  for i in range(0, 31):
    tid = i+1
    tfn = os.path.join(TargetFolder, "%02d/%03d.mp3" % (ver_folder, tid))
    mask = 1 << i
    if id & mask:
      folder = os.path.dirname(tfn)
      mkdirr(folder)
      shutil.copyfile(sfn, tfn)

def GetDataVersion(ver_folder):
  global TargetFolder
  id = 0
  for i in range(0, 31):
    tid = i+1
    tfn = os.path.join(TargetFolder, "%02d/%03d.mp3" % (ver_folder, tid))
    mask = 1 << i
    if os.path.exists(tfn):
      id = id | mask
  return id
  
def TestCode():
  fobj = FOLDER_CLASS("./Test1")
  fobj.Build()
  fobj.AddFile("./Test2", "A.txt")
  fobj.AddFile("./Test2", "B.txt")
  fobj.AddFile("./Test2", "A2/B3.txt")
  st = fobj.isfile("D.txt")
  print("D.txt exists = "+str(st))
  flist = fobj.listdir("./A2")
  print("A2 lisrdir = "+ json_encode(flist))
  data = fobj.ReadTextFile("./A1/A1.txt")
  print("A1.txt = "+data)
  data = fobj.ReadJsonFile("./A1/A1.txt")
  print("A1.txt with json = "+json_encode(data))
  fobj.RemoveFile("D.txt")
  fobj.mkdir("C/D")
  mobj = FOLDER_CLASS("./Test3")
  mobj.Build()
  fobj.Merge(mobj)
  fobj.Dump()

  # print("Load......Source100.txt")
  # vobj = LoadVirtualFolder("./Source100.txt")
  # print("Load......Source101.txt")
  # vobj = LoadVirtualFolder("./Source101.txt")
  # vobj.Dump()
  # flist = vobj.listdir(".");
  # print("Source100="+json_encode(flist))
  
  # print("Load......Source101.txt")
  # vobj = LoadVirtualFolder("Source101.txt")
  # flist = vobj.listdir(".");
  # print("Source101="+json_encode(flist))
  
  # path_name, remind_path = GetFirstPathNode("./Source1/A/B")
  # print("path_name="+path_name)
  # print("remind_path="+remind_path)
  
  # BuildDataVersion(VersionFolder, 0x55AA)
  # id = GetDataVersion(VersionFolder)
  # print("id=0x%02X" % (id))
  # db_list = GetDatabaseList()
  # print(db_list)
  sys.exit(2)
  
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
    print('   --ver         Specify version')
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
  global DataVersion
  global VersionFolder
  global ConfigFile
  global ConfigData
  global VersionFileFolder
  global VersionFileTrack

  VerboseFlag = False
  TestFlag = False
  CleanFlag = False
  ConvertFlag = False
  ConvertMode = 0                       # 0: Single Folder, 1: Multiple Folder
  FolderBase = 0
  SourceFolder = False
  TargetFolder = False
  DataVersion = False

  ConfigFile = __file__.replace(".py", ".json")
  ConfigData = ReadJsonFile(ConfigFile)
  if "VersionFile" in ConfigData:
    vfcfg = ConfigData["VersionFile"]
    if "Folder" in vfcfg:   
      VersionFileFolder = vfcfg["Folder"]
    if "Track" in vfcfg:   
      VersionFileTrack = vfcfg["Track"]
  
  try:
    opts, args = getopt.getopt(argv,"cb:s:t:m:h",["source=", "target=", "base", "mode", "tag=", "catalog", "index", "clean", "ver=", "test"])
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
    elif opt in ("--test"):           # Test Code
      TestFlag = True
    elif opt in ("--ver"):            # Data Version
      DataVersion = StringToInt(arg)
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
  print("Test Flag      = %d" % (TestFlag))
  print("Data Version   = 0x%08X" % (DataVersion))
  print("Version Folder = %d" % (VersionFolder))
  print("VerFile Folder = %d" % (VersionFileFolder))
  print("VerFile Track  = %d" % (VersionFileTrack))

  if TestFlag != False:
    TestCode()

  if SourceFolder == False or TargetFolder == False:
    print("Error: -s xxx and -t xxx is rquired")
    sys.exit(2)
    
  #
  # Prcess Route
  #
  if CleanFlag:
    EmptyFolder(TargetFolder)
    
  if ConvertFlag != False:
    ConvertFolder(SourceFolder, TargetFolder)
        
  if CatalogFlag:
    BuildCatalogFile(TargetFolder)

  if DataVersion != False:
    BuildDataVersion(VersionFolder, DataVersion)
    
if __name__ == "__main__":
   main(sys.argv[1:])
   