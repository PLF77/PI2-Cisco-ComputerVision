import paramiko
import json
import numpy as np
import tkinter as tk
from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
from datetime import timedelta
from datetime import datetime
import nodeenv

def SSHAndLaunch():
    ssh = paramiko.SSHClient()
    k = paramiko.RSAKey.from_private_key_file("private_key")
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname="ec2-15-236-43-196.eu-west-3.compute.amazonaws.com", username="ubuntu", pkey=k)
    # ssh.connect(hostname="ec2-13-38-116-197.eu-west-3.compute.amazonaws.com", username="ubuntu", pkey=k)
    ssh.exec_command("tmux new-session -d -s detection")
    ssh.exec_command("tmux send-keys 'cd ScriptDetection/darknet' C-m")
    ssh.exec_command("tmux send-keys 'python3 Detection_loop.py' C-m")


# Main window
root = tk.Tk()
root.title("Cisco Meraki - Waste Detection")
window_width = 1200
window_height = 800
# get the screen dimension
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
# find the center point
center_x = 20
center_y = 100
# set the position of the window to the center of the screen
root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
root.resizable(True, True)
root.iconbitmap('./cisco-logo.ico')

# Frames
left = Frame(root)
right = Frame(root)
right.pack(side=RIGHT, expand=True)
left.pack(side=LEFT)

# Image panel
img = ImageTk.PhotoImage(Image.open("cisco-logo.png"))
img_panel = Label(root, image=img)
img_panel.photo = img
img_panel.pack(in_=left)

# Date Panel
date_panel = Label(root, text="N/A")
date_panel.pack(in_=left)
# Classes panel
txt_panel = Label(root, text="No objects detected...")
txt_panel.pack(in_=left)

# Buttons
s = ttk.Style()
s.configure('my.TButton', font=('Helvetica', 20))

# Update Button
ttk.Button(root, text='🔄 Update', style='my.TButton', command=lambda: update_img()).pack(in_=right, ipadx=30, ipady=40,
                                                                                          padx=5, pady=50)
# Run Button
ttk.Button(root, text='▶ Run Detector', style='my.TButton', command=lambda: SSHAndLaunch()).pack(in_=right, ipadx=30,
                                                                                                 ipady=40, padx=5,
                                                                                                 pady=50)
# Dashboard Button
ttk.Button(root, text='📊 Dashboard', style='my.TButton', command=lambda: openNewWindow()).pack(in_=right, ipadx=30,
                                                                                                ipady=40, padx=5,
                                                                                                pady=50)

def buildDataDashboard():
    gauth = GoogleAuth()
    drive = GoogleDrive(gauth)
    file_list = drive.ListFile({'q': "'1RLgD3o2NhF3ymMrvy5vqoAAqDT1rWGjn' in parents and trashed=false"}).GetList()
    starting_date = datetime.now()
    for file in file_list:
        try:
            date_time_str = file["title"].split('/')[-1].split('_p')[0]
            date_time_obj = datetime.strptime(date_time_str, '%d-%m-%Y_%H:%M:%S')
        except Exception:
            continue
        if date_time_obj < starting_date:
            starting_date = date_time_obj
    starting_date = starting_date.replace(minute=0, second=0, microsecond=0)
    data = [[starting_date + timedelta(hours=i), np.nan] for i in range(0, (datetime.now()-starting_date).days*24 + (datetime.now()-starting_date).seconds//3600 +1)]
    df = pd.DataFrame(data, columns=["DateTime", "Objects"])
    for file in file_list:
        if (file["title"].split('.')[-1] == "json"):
            file.GetContentFile('temp.json')
            f = open("temp.json")
            results = json.load(f)
            try:
                date_time_str = file["title"].split('/')[-1].split('_p')[0]
                date_time_obj = datetime.strptime(date_time_str, '%d-%m-%Y_%H:%M:%S').replace(minute=0, second=0,
                                                                                              microsecond=0)
                df.loc[df.DateTime == date_time_obj, 'Objects'] = len(results[0]['objects'])
            except Exception:
                continue
    df = df.fillna(method='ffill')
    plot = df.plot(x='DateTime', y='Objects', style='-',title='Waste detected over the last 7 days')
    fig = plot.get_figure()
    fig.savefig("dashboardGraphTemp.png")
    df.to_pickle("./WasteDetectedDF1Week.pkl")
    print(df.tail())
    return df

def openNewWindow():
    # Toplevel object which will
    # be treated as a new window
    global newWindow, evolutionGraph, nbOfCurrentWaste, comparedToYesterday, averageNbOfWaste, up, down,middole, updateButton
    try:
        if newWindow.state() == "iconic":
            newWindow.state(newstate='normal')
            newWindow.focus()
            return
        elif newWindow.state() == "normal":
            newWindow.focus()
            return
    except (Exception,NameError, TclError):
        newWindow = Toplevel(root)
        # sets the title of the
        # Toplevel widget
        newWindow.title("Dashboard")

        # sets the geometry of toplevel
        newWindow.geometry("650x700+1230+100")
        newWindow.iconbitmap('./cisco-logo.ico')
        #Frames
        up = Frame(newWindow)
        middle = Frame(newWindow)
        down = Frame(newWindow)
        up.pack(side=TOP)
        middle.pack()
        down.pack(side=BOTTOM)
        #Labels
        evolutionGraph = Label(newWindow)
        nbOfCurrentWaste = Label(newWindow, text="",font=("Calibri Light", 45))
        comparedToYesterday = Label(newWindow, text="",font=("Calibri Light", 45))
        averageNbOfWaste = Label(newWindow, text="", font=("Calibri Light", 45))
        # Update Button
        updateButton = ttk.Button(newWindow, command=lambda: updateValuesOfDashboard(nbOfCurrentWaste,comparedToYesterday,averageNbOfWaste), text='🔄 Update')

        # A Label widget to show the evolution over the week
        evolutionImg = ImageTk.PhotoImage(Image.open("dashboardGraphTemp.png"))
        evolutionGraph.photo = evolutionImg
        evolutionGraph.config(image=evolutionImg)
        evolutionGraph.pack(in_=up,side=LEFT)
        nbOfCurrentWasteValue,comparedToYesterdayValue,averageNbOfWasteValue = getStatistics()
        # Update the values of the dashboard
        updateValuesOfDashboard(nbOfCurrentWaste,comparedToYesterday,averageNbOfWaste)

        legendLabelNbOfCurrentWaste = Label(newWindow, text="Current number \n of Waste detected", fg='#2e2e2e', font=("Calibri Light", 10)).pack(in_=middle,side=LEFT,pady=20, padx=0)
        legendLabelComparedToYesterday = Label(newWindow, text="Number of Waste detected\n compared with yesterday", fg='#2e2e2e', font=("Calibri Light", 10)).pack(in_=middle,side=LEFT,pady=20, padx=25)
        legendLabelAverageNbOfWaste = Label(newWindow, text="Average number of \n Waste detected this week", fg='#2e2e2e', font=("Calibri Light", 10)).pack(in_=middle,side=LEFT, pady=20,padx=50)

        nbOfCurrentWaste.pack(in_=down,side=LEFT, pady=0, padx=50)
        comparedToYesterday.pack(in_=down,side=LEFT, pady=0,padx=50)
        averageNbOfWaste.pack(in_=down,side=LEFT, pady=0, padx=50)
        updateButton.pack(in_=down,pady=50, padx=5)


def updateValuesOfDashboard(nbOfCurrentWaste,comparedToYesterday,averageNbOfWaste):
    nbOfCurrentWasteValue, comparedToYesterdayValue, averageNbOfWasteValue = getStatistics()
    if(nbOfCurrentWasteValue<3):
        nbOfCurrentWaste.config(text=f"{nbOfCurrentWasteValue}", fg="#84ad7d")
    elif(3<=nbOfCurrentWasteValue<7):
        nbOfCurrentWaste.config(text=f"{nbOfCurrentWasteValue}", fg="#cc7a4e")
    elif(7<=nbOfCurrentWasteValue):
        nbOfCurrentWaste.config(text=f"{nbOfCurrentWasteValue}", fg="#c94b4b")

    if(comparedToYesterdayValue<0):
        comparedToYesterday.config(text = f"{comparedToYesterdayValue}", fg="#84ad7d")
    elif(comparedToYesterdayValue==0):
        comparedToYesterday.config(text = f"{comparedToYesterdayValue}", fg="#4bb2c9")
    elif(0<comparedToYesterdayValue<5):
        comparedToYesterday.config(text = f"+{comparedToYesterdayValue}", fg="#cc7a4e")
    elif(comparedToYesterdayValue>=5):
        comparedToYesterday.config(text = f"+{comparedToYesterdayValue}", fg="#c94b4b")

    if(averageNbOfWasteValue<=3):
        averageNbOfWaste.config(text = averageNbOfWasteValue, fg="#84ad7d")
    elif(3<averageNbOfWasteValue<=5):
        averageNbOfWaste.config(text = averageNbOfWasteValue, fg="#cc7a4e")
    elif (averageNbOfWasteValue>5):
        averageNbOfWaste.config(text=averageNbOfWasteValue, fg="#c94b4b")

    evolutionImg = ImageTk.PhotoImage(Image.open("dashboardGraphTemp.png"))
    evolutionGraph.photo = evolutionImg
    evolutionGraph.config(image=evolutionImg)


def getStatistics():
    df = buildDataDashboard()
    nbOfCurrentWasteValue= df.iloc[-1,1]
    comparedToYesterdayValue=df.iloc[-1,1]-df.iloc[-1-24,1]
    averageNbOfWasteValue=round(df.iloc[:,1].mean(),1)


    return nbOfCurrentWasteValue,comparedToYesterdayValue,averageNbOfWasteValue


def update_img():
    buildDataDashboard()
    gauth = GoogleAuth()
    drive = GoogleDrive(gauth)
    gfile = drive.CreateFile({'id': '1qcMtqSJVUXxbHrC4BwZBe_l8gcRjzlKu'})
    gfile.GetContentFile('prediction.jpg')
    date = gfile["modifiedDate"]
    gfile = drive.CreateFile({'id': '1NM32CaSY2LQooSFKtsVFU1EA18mbempk'})
    gfile.GetContentFile('prediction.json')
    image = Image.open("prediction.jpg")
    image = image.resize((image.size[0] // 2, image.size[1] // 2), Image.ANTIALIAS)
    prediction = ImageTk.PhotoImage(image)
    img_panel.config(image=prediction)
    img_panel.photo = prediction
    date_panel.config(text=date)
    f = open("prediction.json")
    results = json.load(f)
    text = f"Waste detected: {len(results[0]['objects'])} object(s)"
    if text != []:
        txt_panel.config(text=text)
        date_panel.config(text=date)
    else:
        txt_panel.config(text="No objects detected...")

def delete_1WeekOldFiles():
    gauth = GoogleAuth()
    drive = GoogleDrive(gauth)
    file_list = drive.ListFile({'q': "'1RLgD3o2NhF3ymMrvy5vqoAAqDT1rWGjn' in parents and trashed=false"}).GetList()
    for file in file_list:
        date_time_str = file["title"].split('/')[-1].split('_p')[0]
        try:
            date_time_obj = datetime.strptime(date_time_str, '%d-%m-%Y_%H:%M:%S')
        except Exception:
            continue
        if (datetime.now() - date_time_obj).days > 7:
            file_to_delete = drive.CreateFile({'id': file['id']})
            file_to_delete.Delete()


def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        ssh = paramiko.SSHClient()
        k = paramiko.RSAKey.from_private_key_file("private_key")
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="ec2-15-237-72-185.eu-west-3.compute.amazonaws.com", username="ubuntu", pkey=k)
        # ssh.connect(hostname="ec2-13-38-116-197.eu-west-3.compute.amazonaws.com", username="ubuntu", pkey=k)
        ssh.exec_command("tmux kill-session -t detection")
        #delete_1WeekOldFiles()
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
df = pd.read_pickle("./WasteDetectedDF1Week.pkl")

#  Run mainloop
try:
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)
finally:
    root.mainloop()


