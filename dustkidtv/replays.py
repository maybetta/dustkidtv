from urllib.request import urlopen, urlretrieve
from pandas import DataFrame, concat
from random import randrange
from subprocess import Popen
import json
import re
import os, sys
import dustmaker
import numpy as np
from dustkidtv.maps import STOCK_MAPS, CMP_MAPS, MAPS_WITH_THUMBNAIL



TILE_WIDTH=48
START_DELAY=1112
DEATH_DELAY=1000

class InvalidReplay(Exception):
    pass





class ReplayQueue:

    maxHistoryLength=50
    maxQueueLength=100


    def findNewReplays(self, onlyValid=True):
        dustkidPage=urlopen("https://dustkid.com/")
        content=dustkidPage.read().decode(dustkidPage.headers.get_content_charset())

        markerStart="init_replays = ["
        markerEnd="];"
        start=content.find(markerStart)+len(markerStart)
        end=content[start:].find(markerEnd)+start

        replayListJson="["+content[start:end]+"]"

        replayList=json.loads(replayListJson)

        #converts this list of dicts to pandas dataframe
        replayFrame=DataFrame(replayList)

        if onlyValid:
            replayFrame.drop(replayFrame[replayFrame['validated']!=1].index, inplace=True)

        return replayFrame


    def getBackupQueue(self, queueFilename='dustkidtv/replays.json'):

        with open(queueFilename) as f:
            replayListJson=f.read()

        replayList=json.loads(replayListJson)
        replayFrame=DataFrame(replayList)
        return replayFrame


    def computeReplayPriority(self, metadata):
        return metadata["time"] #TODO maybe add a rank score


    def sortReplays(self):
        self.queue["priority"]=self.computeReplayPriority(self.queue)
        self.queue.sort_values("priority", inplace=True, ignore_index=True)


    def getReplayId(self):
        ridList=self.queue['replay_id'].tolist()
        return ridList


    def updateHistory(self, id):
        self.history=self.history + [id]
        if len(self.history)>self.maxHistoryLength:
            self.history.pop(0)


    def updateQueue(self):
        newReplays=self.findNewReplays()

        #remove elements in history
        for id in self.history:
            newReplays.drop(newReplays[newReplays['replay_id']==id].index, inplace=True)

        self.queue=concat([newReplays, self.queue], ignore_index=True)

        #remove elements already in queue
        self.queue.drop_duplicates(subset='replay_id', ignore_index=True, inplace=True)

        queueLength=len(self.queue)
        if queueLength>self.maxQueueLength:
            self.queue=self.queue[:self.maxQueueLength]

        self.length=len(self.queue)
        self.sortReplays()
        self.queueId=self.getReplayId()


    def update(self, id):
        self.updateHistory(id)
        self.updateQueue()


    def next(self):
        if self.length > 0:
            self.current=Replay(self.queue.iloc[0])

            self.queue.drop(self.queue.index[0], inplace=True)

            self.queueId.pop(0)
        else:
            #select random replay from backup queue
            randId=randrange(len(self.backupQueue))
            self.current=Replay(self.backupQueue.iloc[randId])

        return (self.current)



    def __init__(self):
        self.history=[]
        self.queue=self.findNewReplays()
        self.length=len(self.queue)
        self.sortReplays()
        self.queueId=self.getReplayId()
        self.current=None #Replay class
        self.backupQueue=self.getBackupQueue()






class Replay:

    def openReplay(self, url):
        if sys.platform=='win32':
            if not (url.startswith('http://') or url.startswith('https://')):
                url=url.replace('/','\\')
            os.startfile(url)
        elif sys.platform=='darwin':
            Popen(['open', url])
        else:
            try:
                Popen(['xdg-open', url])
            except OSError:
                print('Can\'t open dustforce URI: ' + url)
                sys.exit()

    def downloadReplay(self):
        path='dfreplays/'+str(self.replayId)+'.dfreplay'
        urlretrieve("https://dustkid.com/backend8/get_replay.php?replay="+str(self.replayId), path)
        return path

    def getReplayUri(self):
        return "dustforce://replay/" + str(self.replayId)


    def getReplayPage(self):
        return "https://dustkid.com/replayviewer.php?replay_id=" + str(self.replayId) + "&json=true&metaonly"


    def loadMetadataFromJson(self, replayJson):
        metadata=json.loads(replayJson)
        return metadata


    def loadMetadataFromPage(self, id):
        replayPage=urlopen(self.getReplayPage())
        content=replayPage.read().decode(replayPage.headers.get_content_charset())

        #TODO not really a good check
        if 'Could not find replay' in content:
            raise InvalidReplay

        else:
            metadata=json.loads(content)
            return metadata


    def getReplayFrames(self):
        with dustmaker.DFReader(open(self.replayPath, "rb")) as reader:
            replay = reader.read_replay()

        entity_data = replay.get_player_entity_data()
        if entity_data is None:
            print("No desync data for player :(")
            replayFrames=np.empty(0)

        else:
            nframes=len(entity_data.frames)
            replayFrames=np.empty([nframes, 5])
            i=0
            for frame in entity_data.frames:
                replayFrames[i]=[frame.frame, frame.x_pos, frame.y_pos, frame.x_speed, frame.y_speed]
                i+=1

        return replayFrames


    def estimateDeaths(self):

        def doBBoxDistance(point, box):
            x, y=point
            x1, y1, x2, y2=box

            inXRange=(x>=x1 and x<=x2)
            inYRange=(y>=y1 and y<=y2)

            dx=np.minimum(np.abs(x-x1), np.abs(x-x2))
            dy=np.minimum(np.abs(y-y1), np.abs(y-y2))

            if inXRange and inYRange:
                d=0.
            elif inXRange:
                d=dy
            elif inYRange:
                d=dx
            else:
                d=np.sqrt(dx*dx+dy*dy)
            return d


        def compareToCheckpoints(candidates, coords, checkpoints, kTiles=4):
            estimatedDeathIdx=[]
            for idx in candidates:
                coord=coords[idx]
                for cp in checkpoints:
                    distance=np.sqrt(np.sum((coord-cp)**2))
                    if distance<(kTiles*TILE_WIDTH):
                        estimatedDeathIdx.append(idx)
                        break
            return np.array(estimatedDeathIdx)


        def getCandidates(err, kTiles=2):
            candidates=np.where(err>kTiles*TILE_WIDTH)[0]
            return candidates


        replayFrames=self.getReplayFrames()

        nframes=len(replayFrames)

        frames=replayFrames[:,0]
        lastFrame=int(frames[-1])

        t=frames/50.
        coords=replayFrames[:,[1,2]]
        velocity=replayFrames[:,[3,4]]

        checkpoints=self.levelFile.getCheckpointsCoordinates()
        ncheckpoints=len(checkpoints)

        deltat=t[1:]-t[:-1]

        estimatedCoords=np.empty((nframes, 2))
        estimatedCoords[0]=coords[0]
        estimatedCoords[1:]=coords[:-1]+velocity[:-1]*(deltat).reshape((nframes-1,1))

        estimatedCoords2=np.empty((nframes, 2))
        estimatedCoords2[0]=coords[0]
        estimatedCoords2[1:]=coords[:-1]+velocity[1:]*(deltat).reshape((nframes-1,1))

        estimatedBox=np.c_[np.minimum(estimatedCoords[:,0], estimatedCoords2[:,0]),np.minimum(estimatedCoords[:,1], estimatedCoords2[:,1]), np.maximum(estimatedCoords[:,0], estimatedCoords2[:,0]), np.maximum(estimatedCoords[:,1], estimatedCoords2[:,1])] # box boundary defined as [[x1, y1, x2, y2]]

        err=np.zeros(nframes, dtype=float)
        for frame in range(nframes):
            point=coords[frame]
            box=estimatedBox[frame]
            d=doBBoxDistance(point, box)
            err[frame]=d

        candidates=getCandidates(err)
        estimatedDeathIdx=compareToCheckpoints(candidates, coords, checkpoints)
        ndeaths=len(estimatedDeathIdx)

        return ndeaths


    def saveInfoToFile(self):
        out='%s %s %s in %.3fs'%(self.levelname, self.completion, self.finesse, self.username, rep.time/1000.)
        with open('replayinfo.txt', 'w') as f:
            f.write(out)


    def __init__(self, metadata=None, replayId=None, replayJson=None):

        if metadata is not None:
            self.replayId=metadata['replay_id']
        elif replayId is not None:
            self.replayId=replayId
            metadata=self.loadMetadataFromPage(replayId)
        elif replayJson is not None:
            metadata=self.loadMetadataFromJson(replayJson)
            self.replayId=metadata['replay_id']
        else:
            print('No replay info provided')
            raise InvalidReplay

        self.validated=metadata['validated']

        self.time=metadata['time']

        #download replay from dustkid
        self.replayPath=self.downloadReplay()

        self.numplayers=metadata['numplayers']

        self.character=metadata['time']

        self.completionNum=metadata['score_completion']
        self.finesseNum=metadata['score_finesse']
        scores=['D', 'C', 'B', 'A', 'S']
        self.completion=scores[self.completionNum-1]
        self.finesse=scores[self.finesseNum-1]

        self.apple=metadata['apples']
        self.isPB=False #TODO

        self.timestamp=metadata['timestamp']
        self.username=metadata['username']
        self.levelname=metadata['levelname'] #public level name
        self.level=metadata['level'] #in game level name

        print('\nopening replay %i of %s'%(self.replayId, self.level))

        self.levelFile=Level(self.level)
        if self.levelFile.hasThumbnail:
            self.thumbnail=self.levelFile.getThumbnail()
        else:
            self.thumbnail=None

        #estimation of replay length in real time
        if self.numplayers>1 or not self.levelFile.levelPath: #can't estimate deaths on dustkid daily
            self.deaths=0
        else:
            self.deaths=self.estimateDeaths()
        self.realTime=(self.time+START_DELAY+self.deaths*DEATH_DELAY)/1000.



class Level:

    def downloadLevel(self):
        path='dflevels/'+str(self.name)
        id=re.match('\d+', self.name[::-1]).group()[::-1]
        urlretrieve("http://atlas.dustforce.com/gi/downloader.php?id=%d"+str(id), path)
        return path


    def getCheckpointsCoordinates(self):
        checkpoints=[]

        with dustmaker.DFReader(open(self.levelPath, "rb")) as reader:
            levelFile=reader.read_level()
            entities=levelFile.entities

            for entity in entities.values():
                if isinstance(entity[2], dustmaker.entity.CheckPoint):
                    checkpoints.append([entity[0], entity[1]])

        return np.array(checkpoints)


    def getThumbnail(self):
        with dustmaker.DFReader(open(self.levelPath, "rb")) as reader:
            level=reader.read_level()
            thumbnail=level.sshot

        return thumbnail


    def __init__(self, level):
        self.dfPath=os.environ['DFPATH']

        self.name=level

        isStock=level in STOCK_MAPS
        isCmp=level in CMP_MAPS
        isInfini=level=='exec func ruin user'
        isDaily=re.fullmatch('random\d+', level)

        if isStock:
            self.levelPath=self.dfPath+"/content/levels2/"+level
            self.hasThumbnail=level in MAPS_WITH_THUMBNAIL
        elif isCmp:
            self.levelPath=self.dfPath+"/content/levels3/"+level
            self.hasThumbnail=True
        elif isInfini:
            self.levelPath='dflevels/infinidifficult_fixed'
            self.hasThumbnail=False
        elif isDaily:
            self.levelPath=None
            self.hasThumbnail=False
            print("can't download dustkid daily")
        else:
            self.levelPath=self.downloadLevel()
            self.hasThumbnail=True
