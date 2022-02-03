import os
from tkinter import Tk, Frame, Button, Label, Message, StringVar, BOTH, LEFT, NW, N, E, S, W
from PIL import Image, ImageTk

import time
from subprocess import Popen, PIPE, STDOUT
from replays import ReplayQueue, Replay, InvalidReplay


dfPath="C:/Program Files (x86)/Steam/steamapps/common/Dustforce/dustmod.exe"


class Window(Frame):

    img = Image.open('dustkidtv-tashizuna.png')
    imgSize = (382, 182)
    infoText = '''    Replay ID: %i
    Timestamp: %i
    Username: %s
    Level name: %s
    Time: %.3f s
    Completion: %s
    Finesse: %s
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

    keepgoing=True


    def stop(self):
        self.keepgoing=False

    def run(self):
        with Popen(dfPath, stdout=PIPE, stderr=STDOUT, stdin=PIPE) as df:
            time.sleep(5)

            queue=ReplayQueue()
            self.queueLength=queue.length

            while self.keepgoing:

                    # get next replay on the list
                    rep=queue.next()

                    self.replayId=rep.replayId
                    self.timestamp=rep.timestamp
                    self.username=rep.username
                    self.levelname=rep.levelname
                    self.time=rep.time/1000
                    self.completion=rep.completion
                    self.finesse=rep.finesse
                    self.realTime=rep.realTime

                    self.replay_text.set(self.infoText%(self.replayId, self.timestamp, self.username, self.levelname, self.time, self.completion, self.finesse, self.realTime, self.queueLength))

                    #show replay
                    rep.openReplay(rep.getReplayUri())
                    time.sleep(rep.realTime)

                    #update queues
                    queue.update(rep.replayId)

                    self.queueLength=queue.length



    def __init__(self, master):
        Frame.__init__(self, master)
        self.master = master

        self.master.title('Dustkid TV')
        self.master.resizable(False, False)
        self.pack(fill=BOTH, expand=1)

        left = Frame(self)
        left.grid(row=0, column=0, sticky=(N, E, S, W))

        photo = ImageTk.PhotoImage(self.img)
        self.image_label = Label(left, image=photo)
        self.image_label.image = photo
        self.image_label.pack(anchor=NW)

        self.replay_text = StringVar()
        self.replay_text.set(self.infoText%(self.replayId, self.timestamp, self.username, self.levelname, self.time, self.completion, self.finesse, self.realTime, self.queueLength))
        self.message = Message(left, textvariable=self.replay_text, justify=LEFT, width=self.imgSize[0])
        self.message.pack(anchor=NW)

        self.button=Button(left, text='Start', command=lambda: self.run())
        self.button.pack(anchor=NW)

        self.button=Button(left, text='Stop', command=lambda: self.stop())
        self.button.pack(anchor=NW)

def main():

    root=Tk()

    window=Window(root)

    root.mainloop()


if __name__ == '__main__' :

    main()
