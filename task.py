# %%
import requests
from requests.auth import HTTPBasicAuth
from decouple import config as config_env
import pandas as pd

# %%
def deck():
    resp = requests.get(config_env('base_url') ,auth=HTTPBasicAuth(config_env('username'), config_env('password')))
    base_df = pd.DataFrame(data=resp.json())
    base_df=base_df[base_df['archived']==False][["title","id"]]
    base_df.rename(columns={"title":"deck"},inplace=True)
    return base_df

# %%
def cards(board):
    singleBoard=config_env('base_url')+"/{boardId}/stacks"
    deck=board['deck']
    addId=lambda x : "{arg1} :: {arg2}".format(arg1=deck,arg2=x)
    resp = requests.get(singleBoard.format(boardId=board['id']),
        auth=HTTPBasicAuth(config_env('username'),config_env('password')))
    level2=pd.DataFrame(data=resp.json())
    level2=level2[~level2['title'].isin(["Done","Archieve"])]
    try:
        level2=level2[level2.cards.notnull()][['cards']]
    except AttributeError:
        return []
    # level2
    cards=pd.concat(map(lambda x: pd.DataFrame(x),level2['cards']))
    cards=cards[cards['archived']==False][["title","duedate"]]
    cards["duedate"]=pd.to_datetime(cards["duedate"]).dt.date
    cards['job']=cards['title'].apply(addId)
    cards=cards[cards['duedate'].notna()][["job","duedate"]].reset_index(drop=True)
    return list(cards.to_dict('index').values())

# %%
def getTaskList():
    id,job=[],[]
    taskList={100: {'job': 'default', 'duedate':'01-01-2020'}}
    base_df=deck()
    boardId=list(map(cards,list(base_df.to_dict('index').values())))
    boardId=[j for i in boardId if len(i)>0 for j in i]
    boardId=pd.DataFrame(boardId).sort_values(by=['duedate'])
    boardId['duedate']=boardId['duedate'].apply(lambda x :x.strftime('%d-%m-%Y'))
    boardId=boardId.head(7).reset_index(drop=True).to_dict('index')
    # add default task
    taskList.update(boardId)
    # return [list(boardId.keys()),boardId]
    return taskList

# %%
