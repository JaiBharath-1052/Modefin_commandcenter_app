import logging
import os
from datetime import datetime
import configparser


logging.getLogger('websockets.server').setLevel(logging.ERROR)
logging.getLogger('websockets.protocol').setLevel(logging.ERROR)
    
    

# log_file_name : /srcchtfa/app/app_log/logs/{}.log
# log_file_name : D:/Porjetcs/Git_Workspace/MF-Python-ChatBot/chatbot/app_log/logs/{}.log
# D:/OneDrive - modefin.com/chatbot with web sockets/app_log/logs/

def log_message(log_level,message):
    Config = configparser.ConfigParser()
    Config.read("app_log/log.config")
    # Config.read("D:/New Products/Chatbot/chatbot with web sockets/app_log/log.config")
    file_format = str(Config.get('LogSetting', 'log_file_format'))
    file_mode = str(Config.get('LogSetting', 'log_file_mode'))
    file_name = str(Config.get('LogSetting', 'log_file_name'))
    file_name = file_name.format(str(datetime.now().strftime("%Y-%m-%d")))
    
    
    if os.path.isfile(file_name)==False:
        with open(file_name,"a") as log:
            log.write(">>>>>>>>>>>>>>>>>>>>>>>>>>>> Log for " + str(datetime.now().strftime("%Y-%m-%d"))+"<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"+"\n")
        logging.basicConfig(filename=file_name, level= logging.DEBUG,format=file_format, filemode=file_mode, style='{') 
        logging.log(log_level,message)
        # logging.getLogger('websockets.server').setLevel(logging.ERROR)
        # logging.getLogger('websockets.protocol').setLevel(logging.ERROR)
    else:
        logging.basicConfig(filename=file_name, level= logging.DEBUG,format=file_format, filemode=file_mode, style='{')
        logging.log(log_level,message)
        # logging.getLogger('websockets.server').setLevel(logging.ERROR)
        # logging.getLogger('websockets.protocol').setLevel(logging.ERROR)
    
    
        


 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 