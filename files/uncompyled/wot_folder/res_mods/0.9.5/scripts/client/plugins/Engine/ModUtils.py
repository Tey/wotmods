from gui.shared.gui_items.Vehicle import VEHICLE_TYPES_ORDER, VEHICLE_CLASS_NAME
import BigWorld
import Keys
import ResMgr
import string
import math
from messenger import MessengerEntry
from debug_utils import LOG_ERROR, LOG_CURRENT_EXCEPTION, LOG_DEBUG, LOG_NOTE,LOG_WARNING
from helpers import VERSION_FILE_PATH
import json
import codecs
import os

class BattleUtils:

    @staticmethod
    def getPlayer():
        return BigWorld.player()
    
    @staticmethod
    def getCurrentVehicleDesc(player=None):
        if player is None:
            player = BigWorld.player()
        vehicles = player.arena.vehicles
        for vID, desc in vehicles.items():
            if vID == player.playerVehicleID:
                return desc
    
    @staticmethod
    def getVehicleType(currentVehicleDesc):
        for vehicleType in VEHICLE_TYPES_ORDER:
            if vehicleType in currentVehicleDesc['vehicleType'].type.tags:
                return vehicleType
    
    @staticmethod
    def isMyTeam(team,player=None):
        if player is None:
            player = BigWorld.player()
        return team ==player.team
    
    @staticmethod
    def isCw(player=None):
        if player is None:
            player = BigWorld.player()
        return player.arena.guiType == 0
    
    @staticmethod
    def getTeamAmount(player=None):
        if player is None:
            player = BigWorld.player()
        count = 0
        for vID, desc in player.arena.vehicles.items():
            if BattleUtils.isMyTeam(desc['team'], player) and desc['isAlive']:
                count += 1
        return count
    
    @staticmethod
    def DebugMsg(text, doHighlight = False):
        MessengerEntry.g_instance.gui.addClientMessage(text, doHighlight)
        
class MinimapUtils:
    @staticmethod
    def pos2name(pos):
        sqr = 'KJHGFEDCBA'
        line = '1234567890'
        return '%s%s' % (sqr[int(pos[1]) - 1], line[int(pos[0]) - 1])
    
    @staticmethod
    def clamp(val, vmin, vmax):
        if val < vmin:
            return vmin
        if val > vmax:
            return vmax
        return val

    @staticmethod
    def getSquareForPos(position,player):
        position = (position[0], position[2])
        arenaDesc = player.arena.arenaType
        bottomLeft, upperRight = arenaDesc.boundingBox
        spaceSize = upperRight - bottomLeft
        relPos = position - bottomLeft
        relPos[0] = MinimapUtils.clamp(relPos[0], 0.1, spaceSize[0])
        relPos[1] = MinimapUtils.clamp(relPos[1], 0.1, spaceSize[1])
        return MinimapUtils.pos2name((math.ceil(relPos[0] / spaceSize[0] * 10), math.ceil(relPos[1] / spaceSize[1] * 10)))
    
    @staticmethod
    def name2cell(name):
        if name == '%(ownPos)s':
            return 100
        if name == '%(viewPos)s':
            return 101
        try:
            row = string.ascii_uppercase.index(name[0])
            if row > 8:
                row = row - 1
            column = (int(name[1]) + 9) % 10
            return row + column * 10
        except Exception as e:
            return -1

    @staticmethod
    def getOwnPos(player):
        ownPos = BigWorld.entities[player.playerVehicleID].position
        return MinimapUtils.getSquareForPos(ownPos,player)
    
class FileUtils:
    
    @staticmethod
    def readElement(value,defaultValue,filename=""):
        if type(defaultValue) is list:
            value = value.values()
            tmp = []
            for k,v in enumerate(defaultValue[:]):
                if len(value) <= k:
                    LOG_WARNING(filename+": missing list entry",k+1)
                    tmp.append(v)
                else:
                    tmp.append(FileUtils.readElement(value[k],v,filename))
            return tmp
        if type(defaultValue) is tuple:
            values = filter(None, value.asString.split(" "))
            tmp = ()
            for k,v in enumerate(defaultValue[:]):
                if len(values) <= k:
                    LOG_WARNING(filename+": missing tuple entry",k+1)
                    tmp += (v)
                else:
                    miniTuple = (FileUtils.readElement(values[k],v,filename),)
                    tmp += miniTuple
            return tmp
        if type(defaultValue) is dict:
            confkeys = value.keys()
            tmp = {}
            for k,v in defaultValue.iteritems():
                if k not in confkeys:
                    k = str(k)
                    if k in confkeys:
                        LOG_WARNING(filename+": wrong dict key",k)
                if k not in confkeys:
                    LOG_WARNING(filename+": missing dict key",k)
                    tmp[k] = v
                else:
                    tmp[k]= FileUtils.readElement(value[k],v,filename)
            return tmp
        if type(defaultValue) is int:
            try:
                if type(value) is str:
                    value = int(value)
                else:
                    value = value.asInt
            except Exception:
                LOG_WARNING(filename+": wrong value type",value.asString)
                value = defaultValue
            return value
        if type(defaultValue) is float:
            try:
                if type(value) is str:
                    value = float(value)
                else:
                    value = value.asFloat
            except Exception:
                LOG_WARNING(filename+": wrong value type",value.asString)
                value = defaultValue
            return value
        if type(defaultValue) is bool:
            try:
                if type(value) is str:
                    value = bool(value)
                else:
                    value = value.asBool
            except Exception:
                if value.asString == "True":
                    value = True
                elif value.asString == "False":
                    value = False
                else:
                    LOG_WARNING(filename+": wrong value type",value.asString)
                    value = defaultValue
            return value
        if type(defaultValue) is str:
            if type(value) is str:
                return value
            return value.asString
        LOG_ERROR(filename+": type not found",type(defaultValue))
        return None
        
    
    @staticmethod
    def readXml(path,defset,filename = ''):
        cfg = ResMgr.openSection(path)
        if cfg is None:
            LOG_WARNING('no config found')
            return defset
        return FileUtils.readElement(cfg, defset, filename)
    
    @staticmethod
    def readConfig(path, defset, fromfile = ''):
        fileName, fileExtension = os.path.splitext(path)
        if fileExtension == ".json":
            return FileUtils.readJson(path,defset,fromfile)
        if fileExtension == ".xml":
            return FileUtils.readXml(path, defset, fromfile)
        LOG_WARNING(path+" can't be read, unknow format")
        return defset
            
    
    @staticmethod
    def getWotVersion():
        ver = ResMgr.openSection(VERSION_FILE_PATH).readString('version')
        return ver[2:7]
    
    @staticmethod
    def readJson(path,defset,filename = ''):
        fullPath = os.path.join('res_mods',FileUtils.getWotVersion())
        fullPath = os.path.join(fullPath,path)
        if not os.path.exists(fullPath):
            return defset
        json1_file = codecs.open(fullPath, 'r', 'utf-8-sig')
        return json.loads(json1_file.read(),object_hook=_decode_dict)
    
    @staticmethod
    def my_import(module_name,func_names = [],cache = False):
        if module_name in globals() and cache:
            return True
        try: 
            m = __import__(module_name, globals(), locals(), func_names, -1)
            if func_names:
                for func_name in func_names:
                    globals()[func_name] = getattr(m,func_name)
            else:
                globals()[module_name] = m
            return True
        except ImportError:
            return False
    @staticmethod
    def my_imports(modules):
        for module in modules:
            if type(module) is tuple:
                name = module[0]
                funcs = module[1]
            else:
                name = module
                funcs = []
            if not FileUtils.my_import(name, funcs):
                return module
        return ''
     
    @staticmethod
    def checkPluginsImports(plugin,modules):
        c = FileUtils.my_imports(modules)
        if c:
            LOG_ERROR( plugin +" has errors!: module '"+c+"' not found")
    
class HotKeysUtils:
    
    @staticmethod
    def parseHotkeys(hotkeyString):
        return filter(lambda keycode: keycode > 0, map(lambda code: getattr(Keys, code, 0), hotkeyString.split('+')))

    @staticmethod
    def keysMatch(inputSet, targetSet):
        return len(targetSet) and len(filter(lambda k: k in inputSet, targetSet)) == len(targetSet)

class DecorateUtils:
    
    @staticmethod
    def ensureGlobalVarNotExist(varname):
        if varname in globals():
            LOG_ERROR('global vars already definied')