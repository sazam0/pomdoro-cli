#!/usr/bin/env python3

# %%
import time
import math
import sys
import argparse
from decouple import config as config_env
from collections import namedtuple
import subprocess
import tqdm
import pandas as pd
import datetime
from pathlib import Path
import threading
import queue
import task
from stats import statusData
import json
import logging
import simpleaudio as sa
import matplotlib.pyplot as plt
import seaborn as sns
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.style import Style
from rich.progress import track
from rich.progress import Progress
from rich.logging import RichHandler
import telegram_send
# import contextlib
# from pydub import AudioSegment
# from pydub.playback import play

# %%
console=Console()
warn=Console(stderr=True, style="bold orange")
error=Console(stderr=True, style="bold red")
constants,config=dict(),dict()
with open("{a}/{b}/{c}".format(a=str(Path.home()),b=config_env('config_dir'),
    c=config_env('constant_var'))) as f:
    constants=json.load(f)
with open("{a}/{b}".format(a="/".join([str(Path.home()),config_env('storage_dir')]),
    b=constants['fileName']['config'])) as f:
    config=json.load(f)
# constants
# config
# config['history']

# %%
def fromHistory():
    key,value=list(),list()
    _=[[key.append(int(i)),value.append(j)] for i,j in config['history'].items()]
    df=pd.DataFrame(data=value,index=key,columns=['key','job','task'])
    df.drop_duplicates(inplace=True,ignore_index=True)
    refinedHistory=df.head(9).to_dict('index')
    # refinedHistory
    config['history']={str(i+1):[j['key'],j['job'],j['task']] for i,j in refinedHistory.items()}
    rwData(config,'w',constants['fileName']['config'])
    return 0

# %%
def viewStatus(pomodoro):

    # console=Console()
    table1=Table(show_header=True,show_lines=True,title="Table: history(latest)*",header_style="bold magenta")
    table2=Table(show_header=True,show_lines=True,title="Table: pomodoro",header_style="bold magenta")
    table3=Table(show_header=True,show_lines=True,title="Table: deck",header_style="bold magenta")

    table1.add_column("id",style="cyan bold",justify="center")
    table1.add_column("index",style="dodger_blue1 bold",justify="center")
    table1.add_column("job",style="green3",justify="center",no_wrap=True)
    for i,j in config['history'].items():
        job=j[1] if j[1] in config['errand'] else "[bold]{}[/bold]".format(j[1])
        table1.add_row(i,j[0],job)

    table3.add_column("id",style="cyan bold",justify="center")
    table3.add_column("duedate",style="dodger_blue1 bold",justify="center")
    table3.add_column("task",style="green3",justify="center",no_wrap=True)
    for i,j in config['task'].items():
        table3.add_row(i,j['duedate'],j['job'])

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
    console.print(table3)
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
    pathDir = "/".join([str(Path.home()), config_env('storage_dir')])
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
        else:
            return pd.read_csv(filePath)
    return 0

# %%
def genData(dateTime, pomodoroData):
    x = dateTime
    timeParams={i:x.strftime(j) for i,j in constants['datetimeStamp'].items()}
    pomodoroData = {"index": x.strftime(constants['datetimeIndex']), **timeParams, **pomodoroData}
    df = pd.DataFrame([pomodoroData])
    return df

# %%
def telegram_status(duration,flag):
    telegram_txt={'l':"long break : ",'s':"short break: ",'p':"pomodoro: ",'b':"start pomodoro: "}
    txt=telegram_txt[flag]+str(duration)+" min"
    if (flag != 'p'):
        telegram_send.send(messages=[txt])
    else:
        pass
    return 0
# %%
def playSound(flag,sessionData,silent_flag):
    silent_flag = silent_flag or (sys.platform=='darwin')
    # do not play sound for mac
    if(not silent_flag):
        import alsaaudio
        mixer = alsaaudio.Mixer()
        current_vol=mixer.getvolume()[0]
        low_vol=mixer.setvolume(35)
        time.sleep(0.5) # wait to settle the volume
    else:
        pass
    try:
        if(flag in constants['music'].keys()):
            if(not silent_flag):
                sa.WaveObject.from_wave_file("{a}/{b}/{c}".format(a=Path.home(),
                    b=config_env('config_dir'),c=constants['music'][flag])).play().wait_done()
                low_vol=mixer.setvolume(current_vol)
                time.sleep(0.4) # wait to settle the volume
            else:
                pass
        else:
            error.log("Error: unknown flag in playSound")
            exit()
    except KeyboardInterrupt:
        exitProcess(sessionData)
    if sys.platform in ("linux", "darwin"):
        subprocess.call("clear", shell=True)
    elif sys.platform in ("nt", "dos", "ce"):
        subprocess.call("cls", shell=True)
    else:
        pass
    # sys.stdout.flush()

    return 0

# %%
def take_break(intervalCounter,interval):
    break_flag='n'
    try:
        x=Confirm.ask("\n[bold bright_magenta]take break? : ")
    except KeyboardInterrupt:
        break_flag='e'
        return break_flag

    if(x):
        break_flag = 'l' if ((intervalCounter % interval) == 0) else 's'
    return break_flag

# %%
def currentStatus(progress, desc, currentBar,interval, pomodoroFlag, metaData,sessionData,silent_flag,breakSession=0):
    # if(silent_flag):
    telegram_status(progress,desc[0])
    x = datetime.datetime.now()

    maxContinue_prev =  0 if(len(sessionData) == 0) else  sessionData[-1].copy().to_dict()["maxContinue"][0]

    pomodoroData = {
        "type": desc,
        "pomodoro": progress,
        "consecutiveInterval": interval,
        "completed": False,
        "worktime": 0,
        "maxContinue":None,
        **metaData,
    }
    # print(type(sessionData))
    currentBar.total = progress if (breakSession == 0) else breakSession
    currentBar.desc = desc
    minuteFactor = 60
    tic = time.perf_counter()

    currentBar.refresh()
    for _ in range(currentBar.total):
        for _ in range(minuteFactor): # 60 seconds
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                toc = time.perf_counter()
                if pomodoroFlag:
                    interruptedInterval = round((toc - tic) / 60, 4)  # convert to minute

                    pomodoroData["worktime"] = (interruptedInterval if interruptedInterval > 1.0 else 0.0)
                    try:
                        z=Confirm.ask("\n[bold bright_magenta]taking break: continue(y), (n) exit? : ")
                    except KeyboardInterrupt:
                        z=False

                    if(z): # continue
                        toc_interrupt = time.perf_counter() # break time
                        currentBar.reset()
                        pomodoroData["consecutiveInterval"]="-2"
                        pomodoroData["maxContinue"]=0
                        sessionData.append(genData(x, pomodoroData))

                        #count break time
                        consecutiveSession=sessionData[-1].copy().to_dict()
                        pomodoroData= interrupt_session(tic,toc_interrupt,consecutiveSession,metaData)

                        sessionData.append(genData(x, pomodoroData))
                        return [_,math.ceil(progress - interruptedInterval)]
                    else: # not continue
                        pomodoroData["maxContinue"] = maxContinue_prev+pomodoroData["worktime"]
                        sessionData.append(genData(x, pomodoroData))

                # intervalBar.close()
                currentBar.close()
                # minuteBar.close()
                exitProcess(sessionData)
                # exit()
            # minuteBar.update(minuteFactor)
        currentBar.update(1)
        # minuteBar.reset()
    currentBar.reset()

    pomodoroData["completed"] = True
    pomodoroData["worktime"] = progress
    pomodoroData["maxContinue"] = (maxContinue_prev + progress) if pomodoroFlag else maxContinue_prev
    sessionData.append(genData(x, pomodoroData))
    # print("len : {}".format(len(sessionData)))
    return [sessionData,0]

# %%
def interrupt_session(tic,toc,consecutiveSession,metadata):

    threshold_time = 5.0
    extraTime=round((toc - tic) / 60, 4)  # convert to minute
    extraTime= extraTime if extraTime > threshold_time else 0.0 # count xtra time if its larger than 2 min

    maxContinue_prev = consecutiveSession["maxContinue"][0]

    # filter keys from previous entry
    filter_keys=[i for i,j in constants['datetimeStamp'].items()]
    filter_keys.append("index")
    consecutiveSession={key:consecutiveSession[key] for key in consecutiveSession if key not in filter_keys}
    # new data
    consecutiveSession["type"]="interrupt_break"
    consecutiveSession["pomodoro"]="-2"
    consecutiveSession["consecutiveInterval"]="-2"
    consecutiveSession["worktime"]=extraTime
    consecutiveSession["completed"]=False
    consecutiveSession["maxContinue"]=consecutiveSession["maxContinue"][0]
    pomodoroData={**consecutiveSession,**metadata}

    return pomodoroData


# %%
def xtra_session(tic,consecutiveSession,intervalCounter,pomodoroFlag,metadata,toc_interrupt=0):
    # print(consecutiveSession)
    # exit()
    threshold_time = 2.0
    pomodoroData=dict()
    toc = time.perf_counter()
    extraTime=round((toc - tic) / 60, 4)  # convert to minute
    # count if time exceeds threshold_time min
    extraTime= extraTime if extraTime > threshold_time else 0.0 # count xtra time if its larger than 2 min
    maxContinue_prev = consecutiveSession["maxContinue"][0]
    if(extraTime > 0.0):
        # filter keys from previous entry
        filter_keys=[i for i,j in constants['datetimeStamp'].items()]
        filter_keys.append("index")
        consecutiveSession={key:consecutiveSession[key] for key in consecutiveSession if key not in filter_keys}
        # new data
        consecutiveSession["type"]=consecutiveSession["type"][0]
        consecutiveSession["pomodoro"]="-1"
        consecutiveSession["worktime"]=extraTime
        consecutiveSession["completed"]=False
        consecutiveSession["consecutiveInterval"]=intervalCounter
        consecutiveSession["maxContinue"] = maxContinue_prev  + extraTime if pomodoroFlag else maxContinue_prev
        pomodoroData={**consecutiveSession,**metadata}

    return pomodoroData

# %%
def countdown(chosenOne, metaData, silent_flag):
    pomodoro = chosenOne.pomodoro
    shortBreak = chosenOne.shortbreak
    longBreak = chosenOne.longbreak
    interval = chosenOne.interval
    pomodoroFlag=True

    x = datetime.datetime.now()
    tic = time.perf_counter()

    intervalCounter = 1
    sessionData=list()

    barFormat='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}\t'
    intervalBar = tqdm.tqdm(total=interval, desc="interval", position=0,colour="green",bar_format=barFormat)
    currentBar = tqdm.tqdm(position=1,colour="magenta",bar_format=barFormat)
    # minuteBar = tqdm.tqdm(total=int(constants['minute']), desc="minute", position=2,bar_format=barFormat,
    # colour="blue")

    while True:
        if(len(sessionData)>20):
            # handle memory space write if length > 20
            rwData(sessionData,"a",constants['fileName']['pomodoro'])
            sessionData=list()

        for i in range(interval):
            # time.sleep(2)
            intervalBar.refresh()
            pomodoroFlag=True
            sessionData_tmp,breakSession=currentStatus( pomodoro, "pomodoro",
                currentBar, intervalCounter, pomodoroFlag, metaData, sessionData,silent_flag)
            # continue from pause / interrupt
            while(breakSession > 0):
                intervalBar.refresh()
                sessionData_tmp,breakSession=currentStatus( pomodoro, "pomodoro",
                    currentBar, intervalCounter, pomodoroFlag, metaData, sessionData,silent_flag,breakSession=breakSession)
            sessionData=sessionData_tmp

            intervalBar.update(1)
            playSound("p",sessionData, silent_flag)
            intervalBar.refresh()
            # currentBar.refresh()
            tic = time.perf_counter()
            x = datetime.datetime.now()
            # y/n take break
            break_flag=take_break(i+1,interval)
            # if reponse takes time
            consecutiveSession=sessionData[-1].copy().to_dict()
            pomodoroData=xtra_session(tic,consecutiveSession,intervalCounter,pomodoroFlag,metaData.copy())
            if (len(pomodoroData) > 0):
                # intervalCounter += 1
                sessionData.append(genData(x, pomodoroData))

            intervalCounter += 1
            # break_flag
            if(break_flag == 'e'): # canceled/interrupted (Ctrl-c)
                exitProcess(sessionData)
            elif(break_flag == 'n'): # continue pomodoro
                pass
            elif(break_flag in ['l','s']): # take break
                pomodoroFlag=False
                intervalBar.refresh()

                if (break_flag == 's'):
                    intervalCounter_break = 0
                    break_desc = "short_break"
                    break_type= shortBreak
                else: #break_flag == 'l'
                    intervalCounter_break = -1
                    break_desc = "long_break"
                    break_type= longBreak

                sessionData,_=currentStatus(break_type,break_desc,currentBar,
                        intervalCounter_break, pomodoroFlag,
                        metaData,sessionData,silent_flag)

                playSound(break_flag,sessionData, silent_flag)
                intervalBar.refresh()
                telegram_status(pomodoro,'b')

                tic = time.perf_counter()
                x = datetime.datetime.now()
                # continue/exit pomodoro

                try:
                    z=Confirm.ask("\n[bold bright_magenta]continue pomodoro? : ")
                except KeyboardInterrupt:
                    z=False

                consecutiveSession=sessionData[-1].copy().to_dict()
                pomodoroData = xtra_session(tic,consecutiveSession,intervalCounter_break,pomodoroFlag,metaData.copy())
                if (len(pomodoroData) > 0):
                    sessionData.append(genData(x, pomodoroData))
                if(not z):
                    exitProcess(sessionData)
                else:
                    pass
            else:
                pass
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
                                        help="load and show deck list")
    group.add_argument("--errandoptions", "-E", default=False, action="store_true",
                                        help="show errand list from the config.json file")
    group.add_argument("--number", "-n", type=int, default=-1, choices=[i for i in range(1,10)],
                                        metavar="int", help="task history number")
    parser.add_argument( "--pomodoro", "-p", type=str, default="", choices=help_txt["pomodoro_c"], metavar="str",
                                        help=help_txt["pomodoro_h"])
    parser.add_argument("--view", "-v", default=False, action="store_true",
                                        help="show the pomodoro and history table")
    parser.add_argument("--silent", "-S", default=False, action="store_true",help="silent notification")
    parser.add_argument("--stat", "-s", type=str, default="", metavar="str",
        help="show the pomodoro statistics [int<flag>], w:week (as offest, e.g., previous week = 1w), m:month(month number, e.g., january= 1m), M:year (as offest, e.g., current year = 0M)")
    group.add_argument("--figure", "-F", default=False, action="store_true",
                                        help="show figure of the stat")
    # argcomplete.autocomplete(parser)

    return parser.parse_args()

# %%
def errandList(jobId):

    job={i:j for i,j in enumerate(config['errand'])}
    selectedJob=""
    if(jobId == -1):
        table1=Table(show_header=True,show_lines=True,title="Table: history(latest)*",header_style="bold magenta")
        table1.add_column("id",style="cyan bold",justify="center")
        table1.add_column("errand",style="dodger_blue1 bold",justify="center")
        for i,j in job.items():
            table1.add_row(str(i),j)

        console.print(table1)
        jobId=intInput()
    try:
        selectedJob=job[jobId]
    except KeyError:
        error.log("Error: errand list exceds")
        exit()
    return selectedJob

# %%
def deckList():
    # https://www.edureka.co/community/31966/how-to-get-the-return-value-from-a-thread-using-python
    que=queue.Queue()
    thrdList=[threading.Thread(target=lambda q : q.put(task.getTaskList()),args=(que,)),
        # threading.Thread(target=playSound,args=("s",[]))
        ]

    with console.status("[bold green]fetching decks", spinner='bouncingBall') as status:
        # thrdList[0].start()
        # thrdList[0].join()
        for t in thrdList:
            t.start()
        for t in thrdList:
            t.join()
        # console.log("completed")
    # data=que.get()
    config['task']=que.get()
    rwData(config,'w',constants['fileName']['config'])

    return 0

# %%
def execPomodoro(inputs, pomodoroInputIndex):
    pomodoroKey=inputs.pomodoro
    selectedJob=""
    task=False

    if(inputs.taskoptions or inputs.task!=-1):
        # print("getting the list from deck")
        # id,job=task.getTaskList()
        task=True
        if(inputs.taskoptions):
            # id,job=deckList()
            _=deckList()
            table1=Table(show_header=True,show_lines=True,title="Table: choose deck",header_style="bold magenta")

            table1.add_column("id",style="cyan bold",justify="center")
            table1.add_column("duedate",style="dodger_blue1 bold",justify="center")
            table1.add_column("task",style="green3",justify="center",no_wrap=True)
            for i,j in config['task'].items():
                table1.add_row(str(i),j['duedate'],j['job'])

            console.print(table1)
            jobId=intInput()
            try:
                # jobId=1
                selectedJob=config['task'][jobId]['job']
                # selectedJob=job[jobId]['job']
            except KeyError:
                error.log("Error: input id unknown")
                exit()
        else:
            selectedJob=config['task'][str(inputs.task)]['job']

            # selectedJob=job[inputs.task]['job']
    elif(inputs.number>0): # history
        tmp={int(i):j for i,j in config['history'].items()}
        try:
            pomodoroKey,selectedJob,task=tmp[inputs.number]
        except KeyError:
            error.log("Error: history limit exceds")
            exit()
    else:
        selectedJob=errandList(inputs.errand)

    chosenOne=pomodoroInputIndex[pomodoroKey]
    statusTxt = "[bold sky_blue3]starting pomodoro: [dark_sea_green4]{arg1} [sky_blue3]=> [sea_green3]{arg2} (silent : {arg3})".format(arg1=chosenOne,
            arg2=selectedJob, arg3=inputs.silent)
    # statusTxt+=" => {arg2}".format(arg1=selectedJob)
    config['history']={str(0):[pomodoroKey,selectedJob,task], **config['history']}
    fromHistory()
    console.print(statusTxt)
    return [chosenOne ,[task,selectedJob]]


def intInput():
    receivedInput=None
    try:
        receivedInput=int(console.input("[bold slate_blue1]Choose one of index: [/]"))
    except ValueError:
        error.log("Error: integer(number) input expected")
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
def stats(flag,figure_flag):
    def tableSum(df):
        if(flag[-1]=='w'):
            title="Table: stats(week)"
            col1="day"
        if(flag[-1]=='M'):
            title="Table: stats(months)"
            col1="month"
        table1=Table(show_header=True,show_lines=True,title=title,header_style="bold magenta")
        table1.add_column(col1,style="cyan bold",justify="center")
        table1.add_column("work time (hrs)",style="dodger_blue1 bold",justify="center")
        if((flag[-1]=='w')):
            table1.add_column("remaining time [10] (hrs)",style="light_slate_gray bold",justify="center")
        for i,j in df.items():
            tmp='{0:.2f}'.format(j)
            if((flag[-1]=='w')):
                table1.add_row(str(i),tmp,"{0:.2f}".format(10-j))
            else:
                table1.add_row(str(i),tmp)
        print('\n')
        console.print(table1)
        return 0

    # flag="1M"
    df=rwData("",'r',constants['fileName']['pomodoro'])
    grpTotal,total_wrkTime,total,summury,max_consecutive=statusData(flag,df,constants['datetimeStamp'])

    summury=summury.to_dict()
    if(flag[-1]=='w'):
        tableSum(total.to_dict()['total_worktime'])
        print('min: {0:.2f} hrs\nmax: {1:.2f} hrs\navg(over 7 days): {2:.2f} hrs'.format(summury['min'],
                            summury['max'],summury['avg']))
    elif(flag[-1]=='m'):
        print('min: {0:.2f} hrs\nmax: {1:.2f} hrs\navg(over 30 days): {2:.2f} hrs'.format(summury['min'],
                            summury['max'],summury['avg']))
    elif(flag[-1]=='M'):
        tableSum(total.to_dict()['total_worktime'])
        print('min: {0:.2f} hrs\nmax: {1:.2f} hrs\navg(over 12 months): {2:.2f} hrs'.format(summury['min'],
                            summury['max'],summury['avg']))
    else:
        print("unknown flags")
        exit()

    print('\njobs: {}'.format(", ".join(total_wrkTime.index.values)))

    # subprocess.call(["kitty", "+kitten", "icat", "/tmp/pomodoro.png"])
    # process=subprocess.Popen(["feh /tmp/pomodoro.png"],shell=True,stdout=subprocess.PIPE)
    # process=subprocess.Popen(["feh", "/tmp/pomodoro.png"],stdout=subprocess.PIPE)
    # _=process.communicate()
    # process.wait()
    if (figure_flag):
        subprocess.run("feh /tmp/pomodoro.png",shell=True)

    return 0

# %%
def main():

    pomodoroInputIndex, pomodoro = programStructure()["pomodoro"]
    inputs = parseArgs()

    if(inputs.stat == "" and not inputs.view):
        chosenOne,job = execPomodoro(inputs, pomodoroInputIndex)
        metaData = {"name":chosenOne,"task": job[0] , "comment": job[1]}
        countdown(pomodoro[chosenOne], metaData, inputs.silent)
        # print(metaData)
    elif(inputs.stat!=""):
        stats(inputs.stat,inputs.figure)
    else:
        viewStatus(pomodoro)

    return 0


# %%
if __name__ == "__main__":
    # print("hello")
    main()
