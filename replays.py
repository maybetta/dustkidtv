from urllib.request import urlopen
from pandas import DataFrame, concat
from random import randrange
import json
import os, sys





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


    def getBackupQueue(self, queueFilename='replays.json'):

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

    startDelay=1112+3000

    def openReplay(self,url):
        if sys.platform=='win32':
            os.startfile(url)
        elif sys.platform=='darwin':
            Popen(['open', url])
        else:
            try:
                Popen(['xdg-open', url])
            except OSError:
                print('Can\'t open dustforce URI: ' + url)
                sys.exit()

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

        #estimation of replay length in real time
        self.deathDelay=0 #TODO
        self.realTime=(self.time+self.startDelay+self.deathDelay)/1000.

        self.character=metadata['time']

        self.completionNum=metadata['score_completion']
        self.finesseNum=metadata['score_finesse']
        scores=['D', 'C', 'B', 'A', 'S']
        self.completion=scores[self.completionNum-1]
        self.finesse=scores[self.finesseNum-1]

        self.timestamp=metadata['timestamp']
        self.username=metadata['username']
        self.levelname=metadata['levelname']
