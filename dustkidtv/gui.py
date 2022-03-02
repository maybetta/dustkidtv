import os
import io
import time
import json
import threading
from subprocess import Popen, PIPE, STDOUT
from tkinter import Tk, Frame, Button, Label, Message, StringVar, BOTH, LEFT, NW, N, E, S, W
from PIL import Image, ImageTk

from dustkidtv.replays import ReplayQueue, Replay, InvalidReplay

THUMBNAIL_SIZE=(382, 182)
ICON_SIZE=(32, 32)
PAD=3

dustkidtvThumbnail='dustkidtv/img/dustkidtv-tashizuna.png'
srank='dustkidtv/img/dfsrank.png'
arank='dustkidtv/img/dfarank.png'
brank='dustkidtv/img/dfbrank.png'
crank='dustkidtv/img/dfcrank.png'
drank='dustkidtv/img/dfdrank.png'
apple='dustkidtv/img/dfapple.png'
star='dustkidtv/img/dfstar.png'


class Window(Frame):

    dustkidImg=Image.open(dustkidtvThumbnail)
    thumbnail=dustkidImg.copy()

    srankImg=Image.open(srank)
    arankImg=Image.open(arank)
    brankImg=Image.open(brank)
    crankImg=Image.open(crank)
    drankImg=Image.open(drank)
    appleImg=Image.open(apple)
    starImg=Image.open(star)
    scores=[drankImg, crankImg, brankImg, arankImg, srankImg]

    posLowRight2=(THUMBNAIL_SIZE[0]-ICON_SIZE[0]-PAD, THUMBNAIL_SIZE[1]-ICON_SIZE[1]-PAD)
    posLowRight1=(posLowRight2[0]-ICON_SIZE[0]-PAD, THUMBNAIL_SIZE[1]-ICON_SIZE[1]-PAD)
    posLowLeft1=(PAD, THUMBNAIL_SIZE[1]-ICON_SIZE[1]-PAD)
    posLowLeft2=(posLowLeft1[0]+PAD+ICON_SIZE[0], THUMBNAIL_SIZE[1]-ICON_SIZE[1]-PAD)

    infoText = '''    Replay ID: %i
    Timestamp: %i
    Username: %s
    Level name: %s
    Time: %.3f s
    Completion: %s
    Finesse: %s
    Est. Deaths: %i
    Real time: %.3f s

    Queue length: %i
    '''

    replayId=0
    timestamp=0
    username=''
    levelname=''
    time=0
    completion=''
    finesse=''
    realTime=0

    queueLength=0

    keepgoing=False

    replay_thread=None


    def readConfig(self, configFile='config.json'):
        with open(configFile, 'r') as f:
            conf=json.load(f)

        self.dfPath=conf['path']
        self.dfExePath=conf['dustmod']

        os.environ['DFPATH']=self.dfPath
        os.environ['DFEXE']=self.dfExePath


    def stop(self):
        self.keepgoing=False
        self.replay_text.set('Waiting for replay to end...')


    def run(self):
        self.keepgoing=True
        self.replay_text.set('Starting Dustforce...')
        if self.replay_thread is None:
            self.replay_thread=threading.Thread(target=self.run_thread, daemon=True)
            self.replay_thread.start()


    def run_thread(self):
        with Popen(self.dfExePath, stdout=PIPE, stderr=STDOUT, stdin=PIPE) as df:
            time.sleep(2)

            queue=ReplayQueue()
            self.queueLength=queue.length

            while self.keepgoing:

                    # get next replay on the list
                    rep=queue.next()

                    self.replayId=rep.replayId
                    self.timestamp=rep.timestamp
                    self.username=rep.username
                    self.levelname=rep.levelname
                    self.time=rep.time/1000.
                    self.completion=rep.completion
                    self.finesse=rep.finesse
                    self.deaths=rep.deaths
                    self.realTime=rep.realTime

                    #update thumbnail
                    if rep.thumbnail:
                        img=Image.open(io.BytesIO(rep.thumbnail))
                    else:
                        img=self.dustkidImg.copy()
                    rankCompletionImg=self.scores[rep.completionNum-1]
                    rankFinesseImg=self.scores[rep.finesseNum-1]

                    img.paste(rankCompletionImg, self.posLowRight1, rankCompletionImg)
                    img.paste(rankFinesseImg, self.posLowRight2, rankFinesseImg)
                    if rep.apple and rep.isPB:
                        img.paste(self.starImg, self.posLowLeft1, self.starImg)
                        img.paste(self.appleImg, self.posLowLeft2, self.appleImg)
                    elif rep.isPB:
                        img.paste(self.starImg, self.posLowLeft1, self.starImg)
                    elif rep.apple:
                        img.paste(self.appleImg, self.posLowLeft1, self.appleImg)

                    self.thumbnail=img

                    photoTk = ImageTk.PhotoImage(self.thumbnail)
                    self.image_label.configure(image=photoTk)
                    self.image_label.image=photoTk

                    #update replay info
                    self.replay_text.set(self.infoText%(self.replayId, self.timestamp, self.username, self.levelname, self.time, self.completion, self.finesse, self.deaths, self.realTime, self.queueLength))

                    #show replay
                    rep.openReplay(rep.replayPath)
                    time.sleep(rep.realTime)

                    #update queues
                    queue.update(rep.replayId)
                    self.queueLength=queue.length

            self.replay_text.set('Thread Stopped')
            self.replay_thread = None


    def __init__(self, master):
        self.readConfig()

        Frame.__init__(self, master)
        self.master = master

        self.master.title('Dustkid TV')
        self.master.resizable(False, False)
        self.pack(fill=BOTH, expand=1)

        left = Frame(self)
        left.grid(row=0, column=0, sticky=(N, E, S, W))

        photoTk = ImageTk.PhotoImage(self.thumbnail)
        self.image_label=Label(left, image=photoTk)
        self.image_label.image=photoTk
        self.image_label.pack(anchor=NW)

        self.replay_text = StringVar()
        self.replay_text.set('Press Start')
        self.message = Message(left, textvariable=self.replay_text, justify=LEFT, width=THUMBNAIL_SIZE[0])
        self.message.pack(anchor=NW)

        self.button=Button(left, text='Start', command=lambda: self.run())
        self.button.pack(anchor=NW)

        self.button=Button(left, text='Stop', command=lambda: self.stop())
        self.button.pack(anchor=NW)


def main():

    root=Tk()

    window=Window(root)

    root.mainloop()
