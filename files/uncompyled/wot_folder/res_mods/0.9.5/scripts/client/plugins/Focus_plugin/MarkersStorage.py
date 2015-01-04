import BigWorld
from debug_utils import LOG_NOTE
class MarkersStorage(object):
    __markers = []

    @classmethod
    def addMarker(cls, markerID, marker,config):
        if len(cls.__markers) == config["maxArrows"]:
            MarkersStorage.removeOldest()
        cls.__markers.append({"time": BigWorld.time(),"marker":marker,"id":markerID})


    @classmethod
    def hasMarker(cls, markerID):
        for data in cls.__markers:
            if data['id'] == markerID:
                return True
        return False

    @classmethod
    def hasMarkers(cls):
        return len(cls.__markers)

    @classmethod
    def updateMarkers(cls,config):
        i = 0
        for data in cls.__markers:
            id = data["id"]
            vehicle = BigWorld.entities.get(id)
            elapsed = BigWorld.time() - data["time"]
            if vehicle is None and not BigWorld.player().arena.positions.has_key(id) and config["delIfUnspotted"]:
                cls.removeByPosition(i)
            elif not vehicle.isAlive() and config["delIfDeath"]:
                cls.removeByPosition(i)
            elif not vehicle.isStarted and config["delIfNotVisible"]:
                cls.removeByPosition(i)
            elif elapsed > config["maxArrowTime"]:
                cls.removeByPosition(i)
            else:
                marker = data['marker']
                marker.update()
            i += 1

    
    @classmethod
    def removeByPosition(cls,i):
        data = cls.__markers[i]
        marker = data['marker']
        marker.clear()
        del cls.__markers[i]
    
    @classmethod
    def removeOldest(cls):
        cls.removeByPosition(0)
    
    @classmethod
    def removeMarker(cls, markerID):
        i = 0
        for data in cls.__markers:
            if data['id'] == markerID: 
                cls.removeByPosition(i)
                return
            i += 1
    
    @classmethod
    def clear(cls):
        i = 0
        for data in cls.__markers:
            cls.removeByPosition(i)
            i += 1