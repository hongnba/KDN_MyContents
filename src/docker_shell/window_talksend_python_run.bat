@echo off
call C:\anaconda\Scripts\activate.bat kcontents
python D:\Projects\2024\KSubscribe\Source\kSubscribe_Python_v2.0.0\src\docker_talk_send\sendHistory.py && ^
python D:\Projects\2024\KSubscribe\Source\kSubscribe_Python_v2.0.0\src\docker_talk_send\sendMultiple.py