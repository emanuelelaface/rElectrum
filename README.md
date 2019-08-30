The idea of this project is to have an online wallet generated from the Master Public key of Electrum (https://electrum.org) to keep track of the wallet and to allow a user to send and receive Bitcoins with an offline signature via QR code.

The UI is written with the great library REMI (https://github.com/dddomodossola/remi) and the wallet is managed by Electrum used as library.

Many mobile browsers do not allow the use of the camera on an unsafe connection, so a certfile and a keyfile must be provided.

###  Dependencies

- REMI for the GUI:
```
pip install remi
```

- Electrum for the wallet:
```
sudo apt-get install python3-pyqt5 python3-setuptools python3-pip
wget https://download.electrum.org/3.3.8/Electrum-3.3.8.tar.gz
python3 -m pip install --user Electrum-3.3.8.tar.gz[fast]
```

- pyzbar to read the QR codes:
```
sudo apt-get install libzbar0
pip install pyzbar
```

- qrcode to generate the QR codes:
```
pip install qrcode[pil]
```

<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-1.png></img>
<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-2.png></img>
<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-3.png></img>
