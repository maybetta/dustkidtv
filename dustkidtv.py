import time
import json
from subprocess import Popen, PIPE, STDOUT
from replays import ReplayQueue, Replay, InvalidReplay


def readDfPath(configFile='config.json'):
    with open(configFile, 'r') as f:
        conf=json.load(f)
    dfPath=conf['dustmod']
    return dfPath


def runDustkidtv(keepgoing=True, dfPath="C:/Program Files (x86)/Steam/steamapps/common/Dustforce/dustmod.exe"):
    with Popen(dfPath, stdout=PIPE, stderr=STDOUT, stdin=PIPE) as df:

        print('Running dustmod : %s'%dfPath)
        time.sleep(5)


        queue=ReplayQueue()
        print('Initialized queue with %i replays'%queue.length)

        while keepgoing:

                # get next replay on the list
                rep=queue.next()
                print('Opening replay id %i : %s %s %s by %s in %.3fs | est. real time: %.3f '%(rep.replayId, rep.levelname, rep.completion, rep.finesse, rep.username, rep.time/1000., rep.realTime))

                #show replay
                rep.openReplay(rep.getReplayUri())
                time.sleep(rep.realTime)

                #update queues
                queue.update(rep.replayId)
                print('Replays in queue: %i'%queue.length)

        print(df.stdout.read())



def checkQueue():
    que=ReplayQueue()

    print(que.queueId)
    print(que.history)


    rep=que.next()

    print(rep.replayId)

    que.updateHistory(rep.replayId)
    que.updateQueue()


    print(que.queueId)
    print(que.history)



if __name__ == '__main__' :

    dfPath=readDfPath()

    runDustkidtv(dfPath=dfPath)
