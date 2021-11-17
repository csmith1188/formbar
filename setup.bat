
REM install packages
REM apt update
REM apt upgrade -y
REM apt-get -y install python3-pip
cd installers
python_39_64.exe
cd ../
REM apt-get -y install libatlas-base-dev
REM apt-get -y install libsdl-ttf2.0-0
REM apt-get -y install python3-sdl2
REM apt-get -y install screen
REM install modules
pip install flask
pip install websocket_server
pip install pygame
pip install openpyxl
REM pip install netifaces
pip install cryptography
pip --default-timeout=1000 install pandas
cd formapp
copy key_template.py key.py
copy config_template.py config.py
cd data
copy database_template.db database.db
