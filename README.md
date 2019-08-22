The idea of this project is to have an online wallet generated from the Master Public key of Electrum (https://electrum.org) to keep track of the wallet and to allow a user to send and receive Bitcoins with an offline signature via QR code.

The UI is written with the great library REMI (https://github.com/dddomodossola/remi) and the wallet is managed by Electrum used as library.

Many mobile browsers do not allow the use of the camera on an unsafe connection, so a certfile and a keyfile must be provided.

### Todo

- the send function is not yet implemented
- spinning wheel during menu transitions
- encryption of the wallet (but is needed?)
- front/rear camera selector

<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-1.png></img>
<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-2.png></img>
<img src=https://github.com/emanuelelaface/rElectrum/blob/master/screenshots/screen-shot-3.png></img>
