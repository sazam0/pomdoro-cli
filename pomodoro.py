#!/usr/bin/env python3

# %%
import time
import sys
import argparse, argcomplete
from decouple import config as config_env
from collections import namedtuple
import subprocess
import tqdm
import pandas as pd
import datetime
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
import threading
import queue
import task
import json
from rich.console import Console
from rich.table import Table
from rich.style import Style
from rich.progress import track
# import contextlib
# from playsound import playsound

# %%
constants,config=dict(),dict()
with open('constants.json') as f:
    constants=json.load(f)
with open("{a}/{b}".format(a="/".join([str(Path.home()),config_env('path')]),
    b=constants['fileName']['config'])) as f:
    config=json.load(f)
constants
config
# config['history']

# %%
def fromHistory():
    key,value=list(),list()
    _=[[key.append(int(i)),value.append(j)] for i,j in config['history'].items()]
    df=pd.DataFrame(data=value,index=key,columns=['key','job'])
    df.drop_duplicates(inplace=True,ignore_index=True)
    refinedHistory=df.head(9).to_dict('index')
    # refinedHistory
    config['history']={str(i+1):[j['key'],j['job']] for i,j in refinedHistory.items()}
    rwData(config,'w',constants['fileName']['config'])
    return 0

# %%
def viewStatus(pomodoro):

    console=Console()
    table1=Table(show_header=True,show_lines=True,title="Table: history(latest)*",header_style="bold magenta")
    table2=Table(show_header=True,show_lines=True,title="Table: pomodoro",header_style="bold magenta")

    table1.add_column("id",style="cyan bold",justify="center")
    table1.add_column("index",style="dodger_blue1 bold",justify="center")
    table1.add_column("job",style="green3",justify="center",no_wrap=True)
    for i,j in config['history'].items():
        job=j[1] if j[1] in config['errand'] else "[bold]{}[/bold]".format(j[1])
        table1.add_row(i,j[0],job)

    table2.add_column("index",style="dodger_blue1 bold",justify="center")
    table2.add_column("name",style="dodger_blue1 bold italic",justify="center",no_wrap=True)
    table2.add_column("pomodoro",style="cyan bold",justify="center")
    table2.add_column("s_break",style="cyan bold",justify="center")
    table2.add_column("l_break",style="cyan bold",justify="center")
    table2.add_column("interval",style="cyan bold",justify="center")

    for _, j in pomodoro.items():
        if(j.name!='test'):
            table2.add_row(j.index, j.name, str(j.pomodoro), str(j.shortbreak),
                str(j.longbreak), str(j.interval),style="dim")
        else:
            table2.add_row(j.index, j.name, str(j.pomodoro), str(j.shortbreak),
                str(j.longbreak), str(j.interval),style=Style(bgcolor='grey53'))

    print('\n')
    console.print(table2)
    print('\n')
    console.print(table1)

    return 0
# %%
def exitProcess(sessionData):
    if(len(sessionData)>0):
        try:
            rwData(sessionData,"a",constants['fileName']['pomodoro'])
        except AttributeError:
            pass
    exit()
    return 0

# %%
def rwData(df, mode, fileName):
    pathDir = "/".join([str(Path.home()), config_env('path')])
    filePath="{a}/{b}".format(a=pathDir,b=fileName)
    if(mode!='r'):
        with open(filePath, mode) as f:
            if(fileName==constants['fileName']['pomodoro']):
                df=pd.concat(df)
                df.to_csv(f, sep=",", index=False, header=False, index_label="index")
                # return 0
            else: # fileName==constants['fileName']['config']
                # print('writing')
                f.write(json.dumps(df,indent=2))
    else:
        if(fileName==constants['fileName']['config']):
            with open(filePath) as f:
                config=json.load(f)
            return config

    return 0

# %%
def genData(dateTime, pomodoroData):
    x = dateTime
    timeParams={i:x.strftime(j) for i,j in constants['datetimeStamp'].items()}
    pomodoroData = {"index": x.strftime(constants['datetimeIndex']), **timeParams, **pomodoroData}
    df = pd.DataFrame([pomodoroData])
    return df

# %%
def playSound(flag,sessionData):

    try:
        if(flag in constants['music'].keys()):
            play(AudioSegment.from_wav(constants['music'][flag]))
        else:
            print("unknown flag in playSound")
            exit()
    except KeyboardInterrupt:
        exitProcess(sessionData)
    if sys.platform in ("linux", "osx"):
        subprocess.call("clear", shell=True)
    elif sys.platform in ("nt", "dos", "ce"):
        subprocess.call("cls", shell=True)
    else:
        pass
    # sys.stdout.flush()
    return 0

# %%
def currentStatus(progress, desc, minuteBar, currentBar,interval, pomodoroFlag, metaData,sessionData):
    x = datetime.datetime.now()
    pomodoroData = {
        "type": desc,
        "pomodoro": progress,
        "consecutiveInterval": interval,
        "completed": False,
        "worktime": 0,
        **metaData,
    }
    # print(type(sessionData))
    currentBar.total = progress
    currentBar.desc = desc
    minuteFactor = 1
    tic = time.perf_counter()

    currentBar.refresh()
    for _ in range(currentBar.total):
        for _ in range(int(minuteBar.total / minuteFactor)):
            try:
                time.sleep(minuteFactor)
            except KeyboardInterrupt:
                toc = time.perf_counter()
                if pomodoroFlag:
                    interruptedInterval = round(
                        (toc - tic) / 60, 4
                    )  # convert to minute
                    pomodoroData["worktime"] = (
                        interruptedInterval if interruptedInterval > 1.0 else 0.0
                    )
                    sessionData.append(genData(x, pomodoroData))
                # intervalBar.close()
                currentBar.close()
                minuteBar.close()
                exitProcess(sessionData)
                # exit()
            minuteBar.update(minuteFactor)
        currentBar.update(1)
        minuteBar.reset()
    currentBar.reset()

    pomodoroData["completed"] = True
    pomodoroData["worktime"] = progress

    sessionData.append(genData(x, pomodoroData))
    # print("len : {}".format(len(sessionData)))
    return sessionData


# %%
def countdown(chosenOne, metaData):
    pomodoro = chosenOne.pomodoro
    shortBreak = chosenOne.shortbreak
    longBreak = chosenOne.longbreak
    interval = chosenOne.interval

    intervalCounter = 1
    sessionData=list()

    intervalBar = tqdm.tqdm(total=interval, desc="interval", position=0)
    currentBar = tqdm.tqdm(position=1)
    minuteBar = tqdm.tqdm(total=int(constants['minute']), desc="minute", position=2)
    # minuteBar = ""

    while True:
        if(len(sessionData)>20):
            # handle memory space write if length > 20
            rwData(sessionData,"a",constants['fileName']['pomodoro'])
            sessionData=list()

        for i in range(interval):
            # time.sleep(2)
            sessionData=currentStatus( pomodoro, "pomodoro", minuteBar,
                currentBar, intervalCounter, True, metaData, sessionData)
            intervalBar.update(1)
            intervalCounter += 1
            playSound("p",sessionData)
            intervalBar.refresh()
            if i + 1 == interval:
                sessionData=currentStatus(longBreak, "long break", minuteBar,
                    currentBar, -1, False, metaData,sessionData)
                playSound("l",sessionData)
                intervalBar.refresh()
            else:
                sessionData=currentStatus(shortBreak, "short break", minuteBar,
                    currentBar, 0, False, metaData,sessionData)
                playSound("s",sessionData)
                intervalBar.refresh()

        intervalBar.reset()

    return 0

# %%
def parseArgs():
    mergeTxt=lambda x : ", ".join(x)
    help_txt=programStructure()

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--task", "-t", type=int, default=-1, metavar="int",
        help="deck task id")
    group.add_argument("--errand", "-e", type=int, default=-1, metavar="int",
        help="errand task id")
    group.add_argument("--taskoptions", "-T", default=False, action="store_true",
        help="show deck list")
    group.add_argument("--errandoptions", "-E", default=False, action="store_true",
        help="show errand list")
    group.add_argument("--number", "-n", type=int, default=-1, choices=[i for i in range(1,10)],
        metavar="int", help="task history number")

    parser.add_argument( "--pomodoro", "-p", type=str, default="", choices=help_txt["pomodoro_c"], metavar="str",
        help=help_txt["pomodoro_h"])
    parser.add_argument("--stat", "-s", type=str, default="", choices=help_txt["pomodoro_c"], metavar="str",
        help="")
    parser.add_argument("--view", "-v", default=False, action="store_true",
        help="show the pomodoro and history table")
    # argcomplete.autocomplete(parser)

    return parser.parse_args()

# %%
def errandList(jobId):
    # job={int(i):j for i,j in data['job'].items()}
    job={i:j for i,j in enumerate(config['errand'])}
    selectedJob=""
    if(jobId == -1):
        txt="{:<5s}{:<14s}\n".format("id","errand")
        txt += "".join(["-" for i in range(12)]) + "\n"
        for i,j in job.items():
            txt+="{:<5d}{:<15s}\n".format(i,j)
        print(txt)
        jobId=intInput()
    try:
        selectedJob=job[jobId]
    except KeyError:
        print("errand list exceds: selecting last entry")
        selectedJob=job[-1]
    return selectedJob

# %%
def deckList():
    # https://www.edureka.co/community/31966/how-to-get-the-return-value-from-a-thread-using-python
    que=queue.Queue()
    thrdList=[threading.Thread(target=lambda q : q.put(task.getTaskList()),args=(que,)),
        threading.Thread(target=playSound,args=("s",[]))]
    for t in thrdList:
        t.start()
    for t in thrdList:
        t.join()
    return que.get()

# %%
def execPomodoro(inputs, pomodoroInputIndex):
    pomodoroKey=inputs.pomodoro
    selectedJob=""
    task=False

    if(inputs.taskoptions or inputs.task!=-1):
        print("getting the list from deck")
        # id,job=task.getTaskList()
        id,job=deckList()
        task=True
        if(inputs.taskoptions):
            txt="{:<5s}{:<14s}{:<22s}\n".format("id","duedate", "task")
            txt += "".join(["-" for i in range(28)]) + "\n"
            for i,j in job.items():
                txt+="{:<5d}{:<14s}{:<22s}\n".format(i,j['duedate'],j['job'])
            print(txt)

            jobId=intInput()
            selectedJob=job[jobId]['job']
        else:
            selectedJob=job[inputs.task]['job']
    elif(inputs.number>0): # history
        tmp={int(i):j for i,j in config['history'].items()}
        try:
            pomodoroKey,selectedJob=tmp[inputs.number]
        except KeyError:
            print("history limit exceds: selecting oldest history")
            pomodoroKey,selectedJob=tmp[-1]
    else:
        selectedJob=errandList(inputs.errand)

    chosenOne=pomodoroInputIndex[pomodoroKey]
    statusTxt = "starting pomodoro: '{input}'".format(input=chosenOne)
    statusTxt+=" => {arg1}".format(arg1=selectedJob)
    config['history']={str(0):[pomodoroKey,selectedJob], **config['history']}
    fromHistory()
    print(statusTxt)
    return [chosenOne ,[task,selectedJob]]


def intInput():
    receivedInput=None
    try:
        receivedInput=int(input("Enter one of index: "))
    except ValueError:
        print("Error: integer(number) input expected")
        exit()
    return receivedInput

# %%
def programStructure():
    struc = {
    "pomodoro_h": "",
    "pomodoro_c": None,
    "pomodoro": list(),
    }

    pomodoroStructure=namedtuple(*[[i,j] for i,j  in constants['pomodoroStructure'].items()][0])
    pomodoro={i:pomodoroStructure(*[i,j[0],*map(int,j[1:])]) for i,j in constants['pomodoro'].items()}
    pomodoroInputIndex = {j.index: j.name for _, j in pomodoro.items()}

    tmp = ["{arg1}: {arg2}".format(arg1=j.index, arg2=j.name) for _, j in pomodoro.items()]
    struc["pomodoro_h"] = ", ".join(tmp)
    struc["pomodoro_c"] = [j.index for _, j in pomodoro.items()]

    struc["pomodoro"].extend([pomodoroInputIndex, pomodoro])
    return struc


# %%
def main():

    pomodoroInputIndex, pomodoro = programStructure()["pomodoro"]
    inputs = parseArgs()

    if(inputs.stat == "" and not inputs.view):
        chosenOne,job = execPomodoro(inputs, pomodoroInputIndex)
        metaData = {"task": job[0] , "comment": job[1]}
        # countdown(pomodoro[chosenOne], metaData)
        print(metaData)
    else:
        viewStatus(pomodoro)

    return 0


# %%
if __name__ == "__main__":
    # print("hello")
    main()
