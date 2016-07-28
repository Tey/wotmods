import SoundGroups
import BigWorld
import GUI
from gui.shared import g_eventBus, events
from gui.app_loader.settings import APP_NAME_SPACE as _SPACE
from debug_utils import LOG_NOTE
from functools import partial
from gui.shared.utils.HangarSpace import _HangarSpace
from gui import GUI_SETTINGS
import re
from plugins.Engine.ModUtils import FileUtils,DecorateUtils
import subprocess
import threading
from CurrentVehicle import g_currentVehicle
from plugins.Engine.Plugin import Plugin

from gui.Scaleform.daapi.view.battle.shared.indicators import SixthSenseIndicator
from gui.battle_control.battle_constants import VEHICLE_VIEW_STATE

from account_helpers.settings_core.SettingsCore import g_settingsCore

def LOG_DEBUG(msg):
    if SixthSenseDuration.myConf['Debug']:
        LOG_NOTE(msg)

class SixthSenseDuration(Plugin):
    myConf = {
              'reloadConfigKey': 'KEY_NUMPAD2',
              'AudioPath': '/GUI/notifications_FX/cybersport_timer',
              'AudioIsExternal': True,
              'AudioExternal': ['res_mods/{v}/scripts/client/plugins/SixthSenseDuration_plugin/resources/cmdmp3win.exe',
                                'res_mods/{v}/scripts/client/plugins/SixthSenseDuration_plugin/resources/sound.mp3'],
              'AudioRange': 9000,
              'AudioTick': 1000,
              'IconRange': 9000,
              'Volume': 1.0,
              'VolumeType': "gui",
              'TimerColor': "#FF8000",
              'TimerFont': 'verdana_medium.font',
              'TimerPosition': "(round(x / 2) + 120, round(y / 6) + 20, 0.7)",
              'TimerRange': 9000,
              'TimerTick': 1000,
              'TimerZeroDelay': 200,
              'TimerText': "%s",
              'pluginEnable' : True,
              'DisplayOriginalIcon': False,
              'IconInactivePosition': "(round(x / 2) + 120,  20, 0.7)",
              'IconUnspottedPosition': "(round(x / 2) + 120, 20, 0.7)",
              'IconSpottedPosition': "(round(x / 2) + 120, 20, 0.7)",
              'IconInactivePath': "scripts/client/plugins/SixthSenseDuration_plugin/resources/inactive.dds",
              'IconUnspottedPath': "scripts/client/plugins/SixthSenseDuration_plugin/resources/unspotted.dds",
              'IconSpottedPath': "scripts/client/plugins/SixthSenseDuration_plugin/resources/spotted.dds",
              'IconSpottedSize': (52,52),
              'IconUnspottedSize': (52,52),
              'IconInactiveSize': (52,52),
              'materialFX': 'ADD',
              'Debug': False,
    }
    guiCountDown = None
    backupVolume = None 
    hasSixthSense = False
    guiUnspotted = None
    guiInactive = None
    guiSpotted = None

    # --------------- audio ------------- #
    @staticmethod
    def playSound(sound,i):
        if i < 1:
            SixthSenseDuration.sequenceEnd()
            return
        sound.stop()
        sound.play()
        i -= 1
        BigWorld.callback(SixthSenseDuration.myConf['AudioTick']/1000, partial(SixthSenseDuration.playSound,sound,i))
    
    @staticmethod
    def sequenceEnd():
        SoundGroups.g_instance.setVolume(SixthSenseDuration.myConf['VolumeType'],SixthSenseDuration.backupVolume)
    
    
    @staticmethod
    def threadedPlayExtSound():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(SixthSenseDuration.myConf['AudioExternal'], startupinfo=startupinfo)
    
    @staticmethod
    def playExtSound(i):
        if i < 1:
            return
        try:
            t = threading.Thread(target=SixthSenseDuration.threadedPlayExtSound)
            t.start()
        except:
            pass
        i -= 1
        BigWorld.callback(SixthSenseDuration.myConf['AudioTick']/1000, partial(SixthSenseDuration.playExtSound,i))
    
    @staticmethod
    def new_playSound2D(self, event):
        LOG_DEBUG("playSound2D(%s)" % event)

        if event == 'observed_by_enemy' or event == 'xvm_sixthSense' or event == 'lightbulb':
          LOG_NOTE("playSound2D: %s => BLOCKED" % (event))
          return

        old_playSound2D(self, event)

    @staticmethod
    def new_SixthSenseIndicator___onVehicleStateUpdated(self, state, value):
        LOG_DEBUG("SixthSenseIndicator.__onVehicleStateUpdated(%s, %s)" % (state, value))

        if state != VEHICLE_VIEW_STATE.OBSERVED_BY_ENEMY:
            old_SixthSenseIndicator___onVehicleStateUpdated(self, state, value)
            return

        isShow = value
        LOG_DEBUG("sixthSenseIndicator.show(%s)" % isShow)
        if SixthSenseDuration.myConf['DisplayOriginalIcon'] or not isShow:
            old_SixthSenseIndicator___onVehicleStateUpdated(self, state, value)

        SixthSenseDuration.initGuiSpotted()
        SixthSenseDuration.initGuiUnspotted()
        SixthSenseDuration.guiSpotted.visible = isShow
        SixthSenseDuration.guiUnspotted.visible = not isShow
        SixthSenseDuration.guiInactive.visible = False
        BigWorld.callback(SixthSenseDuration.myConf['IconRange']/1000,SixthSenseDuration.invertIcons)
            
        SixthSenseDuration.startGuiCountDown()
        
        i = SixthSenseDuration.myConf['AudioRange'] / SixthSenseDuration.myConf['AudioTick']
        if not SixthSenseDuration.myConf['AudioIsExternal']:
            sound = SoundGroups.g_instance.getSound2D(SixthSenseDuration.myConf['AudioPath'])
            SixthSenseDuration.backupVolume = SoundGroups.g_instance.getVolume(SixthSenseDuration.myConf['VolumeType'])
            SoundGroups.g_instance.setVolume(SixthSenseDuration.myConf['VolumeType'],SixthSenseDuration.myConf['Volume'])
            SixthSenseDuration.playSound(sound,i)
        else:
            SixthSenseDuration.playExtSound(i)

    @staticmethod
    def invertIcons():
        SixthSenseDuration.guiSpotted.visible = False
        SixthSenseDuration.guiUnspotted.visible = True
    
    # --------------- icon ------------- #
    @staticmethod
    def onChangedVeh():
        LOG_DEBUG('onChangedVeh()')

        if g_currentVehicle.item is None:
            return
        for c in g_currentVehicle.item.crew:
            tankcrew = c[1]
            if tankcrew is None:
                continue
            skills = tankcrew.skillsMap
            if 'commander_sixthSense' in skills:
                commander_sixthSense = skills['commander_sixthSense']
                if commander_sixthSense.isActive and commander_sixthSense.isEnable:
                    SixthSenseDuration.hasSixthSense = True
                    return
        SixthSenseDuration.hasSixthSense = False
    
    
    @staticmethod
    def new_changeDone(self):
        LOG_DEBUG("_HangarSpace.__changeDone()")

        old_changeDoneFromSixthSenseDuration(self)
        GUI_SETTINGS._GuiSettings__settings['sixthSenseDuration'] = SixthSenseDuration.myConf['IconRange']
        SixthSenseDuration.onChangedVeh()
    

    # --------------- countdown ------------- #
    @staticmethod
    def initGuiCountDown():
        if SixthSenseDuration.guiCountDown is not None:
            return
        SixthSenseDuration.guiCountDown = GUI.Text('')
        GUI.addRoot(SixthSenseDuration.guiCountDown)
        SixthSenseDuration.guiCountDown.widthMode = 'PIXEL'
        SixthSenseDuration.guiCountDown.heightMode = 'PIXEL'
        SixthSenseDuration.guiCountDown.verticalPositionMode = 'PIXEL'
        SixthSenseDuration.guiCountDown.horizontalPositionMode = 'PIXEL'
        SixthSenseDuration.guiCountDown.horizontalAnchor = 'LEFT'
        SixthSenseDuration.guiCountDown.verticalAnchor = 'TOP'
        SixthSenseDuration.guiCountDown.colourFormatting = True
        SixthSenseDuration.guiCountDown.font = SixthSenseDuration.myConf['TimerFont']
        SixthSenseDuration.guiCountDown.visible = False
        SixthSenseDuration.guiCountDown.position = SixthSenseDuration.fixPosition('TimerPosition')
        
    @staticmethod
    def initGuiSpotted():
        if SixthSenseDuration.guiSpotted is None:
            SixthSenseDuration.guiSpotted = SixthSenseDuration.createTexture(SixthSenseDuration.myConf['IconSpottedPath'], SixthSenseDuration.fixPosition('IconSpottedPosition'),SixthSenseDuration.myConf['IconSpottedSize'])
        SixthSenseDuration.guiSpotted.visible = False
        
    @staticmethod
    def initGuiUnspotted():
        if SixthSenseDuration.guiUnspotted is None:
            SixthSenseDuration.guiUnspotted = SixthSenseDuration.createTexture(SixthSenseDuration.myConf['IconUnspottedPath'], SixthSenseDuration.fixPosition('IconUnspottedPosition'),SixthSenseDuration.myConf['IconUnspottedSize'])
        SixthSenseDuration.guiUnspotted.visible = SixthSenseDuration.hasSixthSense    
            
    @staticmethod
    def initGuiInactive():
        if SixthSenseDuration.guiInactive is None:
            SixthSenseDuration.guiInactive = SixthSenseDuration.createTexture(SixthSenseDuration.myConf['IconInactivePath'], SixthSenseDuration.fixPosition('IconInactivePosition'),SixthSenseDuration.myConf['IconInactiveSize'])
        SixthSenseDuration.guiInactive.visible = not SixthSenseDuration.hasSixthSense

    @staticmethod
    def createTexture(texture,position,size):
        item = GUI.Simple(texture)
        GUI.addRoot(item)
        item.widthMode = 'PIXEL'
        item.heightMode = 'PIXEL'
        item.verticalPositionMode = 'PIXEL'
        item.horizontalPositionMode = 'PIXEL'
        item.horizontalAnchor = 'LEFT'
        item.verticalAnchor = 'TOP'
        item.position = position
        item.size = size
        item.materialFX = SixthSenseDuration.myConf['materialFX']
        return item
    
    @staticmethod
    def startGuiCountDown():
        if SixthSenseDuration.myConf['TimerRange'] == 0:
            return
        if SixthSenseDuration.guiCountDown is None:
            SixthSenseDuration.initGuiCountDown()
        SixthSenseDuration.guiCountDown.visible = True
        max = SixthSenseDuration.myConf['TimerRange'] / 1000
        min = - 1
        diff = - SixthSenseDuration.myConf['TimerTick'] / 1000
        for i in xrange(max,min,diff):
            BigWorld.callback(i, partial(SixthSenseDuration.tickGuiCountDown,max-i))
    
    @staticmethod
    def endGuiCountDown():
        if SixthSenseDuration.guiCountDown is not None:
            SixthSenseDuration.guiCountDown.visible = False
            
    @staticmethod
    def endGuiInactive():
        if SixthSenseDuration.guiInactive is not None:
            SixthSenseDuration.guiInactive.visible = False
            
    @staticmethod
    def endGuiUnspotted():
        if SixthSenseDuration.guiUnspotted is not None:
            SixthSenseDuration.guiUnspotted.visible = False
            
    @staticmethod
    def endGuiSpotted():
        if SixthSenseDuration.guiSpotted is not None:
            SixthSenseDuration.guiSpotted.visible = False
    
    @staticmethod    
    def tickGuiCountDown(i):
        color = SixthSenseDuration.myConf['TimerColor']
        color = '\\c' + re.sub('[^A-Za-z0-9]+', '', color) + 'FF;'
        SixthSenseDuration.guiCountDown.text = color + SixthSenseDuration.myConf['TimerText'] % (str(i))
        if i == 0:
            BigWorld.callback(SixthSenseDuration.myConf['TimerZeroDelay']/1000,SixthSenseDuration.endGuiCountDown )

    @staticmethod
    def fixPosition(type):
        x, y = GUI.screenResolution()
        return eval(SixthSenseDuration.myConf[type])
        
    @staticmethod
    def onAppInitializing(event):
        LOG_DEBUG('onAppInitializing(%s)' % event.ns)

        if event.ns == _SPACE.SF_BATTLE:
            SixthSenseDuration.initGuiCountDown()
            SixthSenseDuration.initGuiInactive()
            SixthSenseDuration.initGuiSpotted()
            SixthSenseDuration.initGuiUnspotted()

        # Not sure this is the correct way to monitor screen size changes, but it works...
        g_settingsCore.interfaceScale.onScaleChanged += SixthSenseDuration.onScaleChanged

#   @staticmethod
#   def onAppInitialized(event):
#      LOG_NOTE("__onAppInitialized(%s)" % event.ns)

    @staticmethod
    def onAppDestroyed(event):
        LOG_DEBUG('onAppDestroyed(%s)' % event.ns)

        if event.ns == _SPACE.SF_BATTLE:
            SixthSenseDuration.endGuiCountDown()
            SixthSenseDuration.endGuiInactive()
            SixthSenseDuration.endGuiSpotted()
            SixthSenseDuration.endGuiUnspotted()

        g_settingsCore.interfaceScale.onScaleChanged -= SixthSenseDuration.onScaleChanged

    @staticmethod
    def onScaleChanged(scale):
        width, height = GUI.screenResolution()
        LOG_DEBUG('onScaleChanged(%s) [%dx%d]' % (scale, width, height))

        # Screen size has changed, update the position of icons

        if SixthSenseDuration.guiCountDown is not None:
            SixthSenseDuration.guiCountDown.position = SixthSenseDuration.fixPosition('TimerPosition')

        if SixthSenseDuration.guiSpotted is not None:
            SixthSenseDuration.guiSpotted.position = SixthSenseDuration.fixPosition('IconSpottedPosition')

        if SixthSenseDuration.guiUnspotted is not None:
            SixthSenseDuration.guiUnspotted.position = SixthSenseDuration.fixPosition('IconUnspottedPosition')

        if SixthSenseDuration.guiInactive is not None:
            SixthSenseDuration.guiInactive.position = SixthSenseDuration.fixPosition('IconInactivePosition')

    @classmethod
    def readConfig(cls):
        super(SixthSenseDuration, SixthSenseDuration).readConfig()
        wotv = FileUtils.getWotVersion()
        tmp = []
        for d in SixthSenseDuration.myConf['AudioExternal']:
            tmp.append(d.replace('{v}',wotv))
        SixthSenseDuration.myConf['AudioExternal'] = tmp
        SixthSenseDuration.myConf['IconInactivePath'] = SixthSenseDuration.myConf['IconInactivePath'].replace('{v}',wotv)
        SixthSenseDuration.myConf['IconUnspottedPath'] = SixthSenseDuration.myConf['IconUnspottedPath'].replace('{v}',wotv)
        SixthSenseDuration.myConf['IconSpottedPath'] = SixthSenseDuration.myConf['IconSpottedPath'].replace('{v}',wotv)
        
        
    @classmethod
    def run(cls):
        super(SixthSenseDuration, SixthSenseDuration).run()
        cls.addEventHandler(SixthSenseDuration.myConf['reloadConfigKey'],cls.reloadConfig)
        saveOldFuncs()
        injectNewFuncs()

def saveOldFuncs():
    global old_changeDoneFromSixthSenseDuration, old_playSound2D, old_SixthSenseIndicator___onVehicleStateUpdated
    DecorateUtils.ensureGlobalVarNotExist('old_SixthSenseIndicator___onVehicleStateUpdated')
    DecorateUtils.ensureGlobalVarNotExist('old_changeDoneFromSixthSenseDuration')
    DecorateUtils.ensureGlobalVarNotExist('old_playSound2D')
    old_SixthSenseIndicator___onVehicleStateUpdated = SixthSenseIndicator._SixthSenseIndicator__onVehicleStateUpdated
    old_changeDoneFromSixthSenseDuration = _HangarSpace._HangarSpace__changeDone
    old_playSound2D = SoundGroups.SoundGroups.playSound2D
    
def injectNewFuncs():
    SixthSenseIndicator._SixthSenseIndicator__onVehicleStateUpdated = SixthSenseDuration.new_SixthSenseIndicator___onVehicleStateUpdated
    _HangarSpace._HangarSpace__changeDone = SixthSenseDuration.new_changeDone
    SoundGroups.SoundGroups.playSound2D = SixthSenseDuration.new_playSound2D
    add = g_eventBus.addListener
    appEvent = events.AppLifeCycleEvent
    add(appEvent.INITIALIZING, SixthSenseDuration.onAppInitializing)
    # add(appEvent.INITIALIZED, SixthSenseDuration.onAppInitialized)
    add(appEvent.DESTROYED, SixthSenseDuration.onAppDestroyed)
    g_currentVehicle.onChanged += SixthSenseDuration.onChangedVeh
