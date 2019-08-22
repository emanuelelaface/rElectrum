#!/usr/bin/python3.7

import ssl
import os
import io
import time
import base64
from io import BytesIO
from PIL import Image
import remi.gui as gui
from remi import start, App
from pyzbar.pyzbar import decode
from electrum.simple_config import SimpleConfig
from electrum import constants
from electrum.daemon import Daemon
from electrum.wallet import restore_wallet_from_text
from wallet_functions import WalletInterface
import asyncio
import pytz
import qrcode
from datetime import datetime

unit = 1e8 # BTC

config = SimpleConfig({"testnet": False})
constants.set_mainnet()
daemon = Daemon(config, listen_jsonrpc=False)

class rElectrum(App):
    def __init__(self, *args, **kwargs):
        self.wallets_list = {}
        super(rElectrum, self).__init__(*args, static_file_path={'my_res':'./res/'})

    def set_browser_id(self, **kwargs):
        self.userdir = kwargs['browser']
        if not os.path.isdir(self.userdir):
            os.mkdir(self.userdir)

    def set_timezone(self, **kwargs):
        try:
            self.timezone = pytz.timezone(kwargs['timezone'])
        except:
            self.timezone = pytz.timezone('UTC')

    def qr_code_widgets(self):
        # Video for QR Code
        width = '300'
        height = '300'
        self.qr_video = gui.Widget(_type='video')
        self.qr_video.style['overflow'] = 'hidden'
        self.qr_video.attributes['autoplay'] = 'true'
        self.qr_video.attributes['width'] = width
        self.qr_video.attributes['height'] = height
        self.qr_canvas = gui.Widget(_type='canvas')
        self.qr_canvas.style['display'] = 'none'
        self.qr_canvas.attributes['width'] = width
        self.qr_canvas.attributes['height'] = height
        self.qr_button_confirm = gui.Label('Get QR Code', style={'font-size':'16px', 'text-align':'center', 'margin':'5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '100%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px', 'border-style':'none'})
        self.qr_button_cancel = gui.Label('Cancel', style={'font-size':'16px', 'text-align':'center', 'margin':'5px 5px 5px 5px', 'padding':'5px 20px 5px 20px','color': 'white', 'width': '100%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px', 'border-style':'none'})
        self.qr_button_cancel.onclick.do(self.qr_cancel)
        self.qr_code_reason = ''

    def qr_snapshot(self, widget, callback_function):
        self.execute_javascript("""
            const video = document.querySelector('video');
            const canvas = document.querySelector('canvas');
            canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        canvas.getContext('2d').drawImage(video, 0, 0);
            var binStr = atob( canvas.toDataURL('image/png').split(',')[1] ),
            len = binStr.length,
            arr = new Uint8Array(len);
            for (var i = 0; i < len; i++ ) {
                arr[i] = binStr.charCodeAt(i);
            }
            var blob = new Blob( [arr], {type:'image/png'} );
            var xhr = new XMLHttpRequest();
            var fd = new FormData();
            xhr.open("POST", "/", true);
            xhr.setRequestHeader('filename', video.videoWidth.toString()+'-'+video.videoHeight.toString());
            xhr.setRequestHeader('listener', '%(id)s');
            xhr.setRequestHeader('listener_function', '%(callback_function)s');
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    console.log('upload success: ');
                }else if(xhr.status == 400){
                    console.log('upload failed: ');
                }
            };
            fd.append('upload_file', blob);
            xhr.send(fd);
        """%{'id':str(id(self)), 'callback_function': str(callback_function)})

    def get_qr_from_xpub(self, img_data, filename):
        image = Image.open(io.BytesIO(img_data))
        qr_code_list = decode(image)
        if len(qr_code_list)>0 and self.qr_code_reason == 'new wallet':
            self.execute_javascript('document.getElementById("spinner").style.display=""')
            qr_code_data = qr_code_list[0][0].decode('utf-8')
            self.qr_log.set_text('Pub Key Detected')
            try:
                restore_wallet_from_text(qr_code_data, path=self.userdir+'/'+self.new_wallet_name.get_value())
                done = False
                time.sleep(1)
                while not done:
                    done = True
                    for i in os.listdir(self.userdir):
                        if self.new_wallet_name.get_value()+'.tmp' in i:
                            done = False
            except:
                self.qr_log.set_text('Invalid Master Public Key')
        if len(qr_code_list)==0 and self.qr_code_reason == 'new wallet':
            self.qr_log.set_text('No valid QR code found')

    def qr_cancel(self, widget):
        self.execute_javascript("""
            const video = document.querySelector('video');
            video.srcObject.getTracks()[0].stop();
        """)
        self.set_root_widget(self.wallet_list_page)
        return

    def add_wallet_page(self):
        # Add wallet page
        self.qr_code_widgets()
        add_wallet_widgets = []
        add_wallet_widgets.append(self.logo)
        add_wallet_widgets.append(self.qr_video)
        add_wallet_widgets.append(self.qr_canvas)
        self.new_wallet_name = gui.TextInput(single_line=True, hint='Set wallet name', style={'font-size':'16px', 'text-align':'center', 'width': '70%', 'margin':'5px', 'padding':'5px 50px 5px 50px','color': 'black'})
        self.new_wallet_name.onchange.do(self.set_wallet_name)
        add_wallet_widgets.append(self.new_wallet_name)
        self.qr_button_confirm.set_style({'color': 'black'})
        add_wallet_widgets.append(gui.HBox(children=[self.qr_button_confirm, self.qr_button_cancel], style={'margin':'0px auto', 'width':'100%', 'background-color':'#1A222C'}))
        self.qr_log = gui.Label("No Wallet Name", style={'font-size':'14px', 'width':'70%', 'text-align':'center', 'margin':'5px', 'padding':'5px 50px 5px 50px', 'color': '#A7A19F', 'border-width':'0.1px', 'border-style':'dashed'})
        add_wallet_widgets.append(self.qr_log)
        self.add_wallet_page = gui.VBox(children=add_wallet_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})

    def set_wallet_name(self, widget, text):
        filename = self.new_wallet_name.get_value()
        if filename == '':
            self.qr_button_confirm.set_style({'color': 'black'})
            self.qr_button_confirm.onclick.do(None)
            self.qr_log.set_text('No Wallet Name')
            return

        if not os.path.isfile('wallets/'+filename):
            self.qr_log.set_text('Filename is valid, scan Master Public Key')
            self.qr_code_reason='new wallet'
            self.qr_button_confirm.set_style({'color': 'white'})
            self.qr_button_confirm.onclick.do(self.qr_snapshot, 'get_qr_from_xpub')
            return
        else:
            self.qr_log.set_text('Wallet already exists')
            self.qr_button_confirm.onclick.do(None)
            self.qr_button_confirm.set_style({'color': 'black'})

    def switch_to_add_wallet_page(self, widget):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        self.set_root_widget(self.add_wallet_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')
        self.execute_javascript("""
            const video = document.querySelector('video');
            video.setAttribute("playsinline", true);
            const canvas = document.querySelector('canvas');
            navigator.mediaDevices.getUserMedia({video: { facingMode: { ideal: "environment" } }, audio: false}).
                then((stream) => {video.srcObject = stream});
        """)

    def main_page(self):
        if self.userdir != '':
            self.wallets_list = {}
            asyncio.set_event_loop(asyncio.new_event_loop())
            for wallet_path in os.listdir(self.userdir):
                if wallet_path not in self.wallets_list and '.tmp.' not in wallet_path:
                        self.wallets_list[wallet_path]=WalletInterface(config, daemon, self.userdir+'/'+wallet_path)
            
            wallet_list_page_widgets = []
            wallet_list_page_widgets.append(self.logo)
            if len(self.wallets_list) > 0:
                self.buttons = {}
                for wallet in self.wallets_list:
                    self.buttons[wallet]={}
                    wallet_balance = self.wallets_list[wallet].get_balance()
                    self.buttons[wallet]['row1']=gui.Label(wallet+' '+str(sum(wallet_balance)/unit), style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
                    self.buttons[wallet]['row1'].onclick.do(self.go_to_wallet, wallet)
                    self.buttons[wallet]['row2']=gui.Label('\U00002714 '+str(wallet_balance[0]/unit)+' \U000023F3 '+str(wallet_balance[1]/unit), style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})
                    self.buttons[wallet]['row2'].onclick.do(self.go_to_wallet, wallet)
                    wallet_list_page_widgets.append(self.buttons[wallet]['row1'])
                    wallet_list_page_widgets.append(self.buttons[wallet]['row2'])
            add_label = gui.Label("+ Add Wallets", style={'font-size':'14px', 'margin':'5px', 'padding':'5px 50px 5px 50px','color': '#A7A19F', 'border-width':'0.1px', 'border-style':'dashed'})
            add_label.onclick.do(self.switch_to_add_wallet_page)
            wallet_list_page_widgets.append(add_label)
            self.wallet_list_page = gui.VBox(children=wallet_list_page_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        else:
            wallet_list_page_widgets = []
            wallet_list_page_widgets.append(self.logo)
            add_label = gui.Label("+ Add Wallets", style={'font-size':'14px', 'margin':'5px', 'padding':'5px 50px 5px 50px','color': '#A7A19F', 'border-width':'0.1px', 'border-style':'dashed'})
            add_label.onclick.do(self.switch_to_add_wallet_page)
            wallet_list_page_widgets.append(add_label)
            self.wallet_list_page = gui.VBox(children=wallet_list_page_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})

    def main(self):
        self.userdir = ''
        self.page.children['head'].add_child('fingerprintjs', '<script>\n'+open('./res/fingerprint2.js','r').read()+'\n</script>')
        self.page.children['head'].add_child('favicon', '<link rel="icon" type="image/png" href="/favicon.png">')
        self.page.children['head'].add_child('apple-120', '<link rel="apple-touch-icon" href="/my_res:icon@120.png">')
        self.page.children['head'].add_child('apple-152', '<link rel="apple-touch-icon" sizes="152x152" href="/my_res:icon@152.png">')
        self.page.children['head'].add_child('apple-180', '<link rel="apple-touch-icon" sizes="180x180" href="/my_res:icon@180.png">')
        self.page.children['head'].add_child('apple-192', '<link rel="icon" sizes="192x192" href="/my_res:icon@192.png">')
        self.page.children['head'].add_child('css-spin', '<style type="text/css">body>div { box-shadow: 0 0px 0px 0 rgba(0, 0, 0, 0), 0 0px 0px 0 rgba(0, 0, 0, 0), 0 0px 0px 0px rgba(0, 0, 0, 0); } div { background-color: rgba(0,0,0,0); } .lds-ripple { margin-left: -32px;  margin-top: 13px; display: inline-block; position: absolute; width: 64px; height: 64px; } .lds-ripple div { position: absolute; border: 4px solid #fff; opacity: 1; border-radius: 50%; animation: lds-ripple 1s cubic-bezier(0, 0.2, 0.8, 1) infinite; } .lds-ripple div:nth-child(2) { animation-delay: -0.5s; } @keyframes lds-ripple { 0% { top: 28px; left: 28px; width: 0; height: 0; opacity: 1; } 100% { top: -1px; left: -1px; width: 58px; height: 58px; opacity: 0; } } </style>')
        self.page.children['body'].add_child('div-spin', '<center><div id="spinner" class="lds-ripple"> <div> </div> <div> </div></div></center>')

        self.logo = gui.Image('/my_res:relectrum-logo.png', height=70, margin='10px')
        self.back_button=gui.Label('Back', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px'})
        self.back_button.onclick.do(self.go_back_main)
        self.main_page()
        self.add_wallet_page()

        # As default starts on Add Wallet page
        return self.wallet_list_page

    def onload(self, data):
        # Do a fingerprint of the browser for authentication.
        self.execute_javascript("""
            var params={};
            Fingerprint2.get(function(components) {
                params['browser'] = Fingerprint2.x64hash128(components.map(function (pair) { return pair.value }).join(), 31);
                sendCallbackParam('%(id)s','set_browser_id',params);
                })
        """%{'id':str(id(self))})
        # Get the user timezone
        self.execute_javascript("""
            var params={};
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            params['timezone'] = tz;
            sendCallbackParam('%(id)s','set_timezone',params);
        """%{'id':str(id(self))})
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def idle(self):
        if self.userdir != '':
            if len(self.wallets_list) != len(os.listdir(self.userdir)): # Repaint the main page every time there is a wallet change
                self.main_page()
                self.execute_javascript("""
                    const video = document.querySelector('video');
                    video.srcObject.getTracks()[0].stop();
                """)
                self.set_root_widget(self.wallet_list_page)
                self.execute_javascript('document.getElementById("spinner").style.display="none"')

        if int(time.time())%10 == 0: # Check the wallet balance every 10 seconds.
            for wallet in self.wallets_list:
                wallet_balance = self.wallets_list[wallet].get_balance()
                self.buttons[wallet]['row1'].set_text(wallet+' '+str(sum(wallet_balance)/unit))
                self.buttons[wallet]['row2'].set_text('\U00002714 '+str(wallet_balance[0]/unit)+' \U000023F3 '+str(wallet_balance[1]/unit))

    def go_to_wallet(self, widget, *args):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        wallet = args[0]
        tx_list=[]
        row_count=0
        for tx in self.wallets_list[wallet].get_history():
            tx_time = datetime.fromtimestamp(tx[1].timestamp, self.timezone).strftime("%Y-%m-%d %H:%M:%S")
            tx_id = tx[0]
            tx_amount = str(tx[2]/unit)
            tx_balance = str(tx[3]/unit)
            table_row = gui.TableRow((tx_time, tx_amount, '\U000027A1'), style={'color':'#A7A19F'}, height=30)
            for cell in table_row.children:
                if tx[2]>0:
                    table_row.get_child(cell).set_style({'color': 'lime', 'background-color':'#24303F', 'border-style':'none'})
                else:
                    table_row.get_child(cell).set_style({'color': 'red', 'background-color':'#24303F', 'border-style':'none'})

            table_row.tx_details = {'id': tx_id, 'time': tx_time, 'amount': tx_amount, 'block': str(tx[1].height), 'conf':str(tx[1].conf), 'inputs':[], 'outputs':[]}
            for addr in self.wallets_list[wallet].get_tx_in(tx_id):
                table_row.tx_details['inputs'].append({'address':addr.address, 'amount':addr.value/unit, 'mine':self.wallets_list[wallet].wallet.is_mine(addr.address)})
            for addr in self.wallets_list[wallet].get_tx_out(tx_id):
                table_row.tx_details['outputs'].append({'address':addr.address, 'amount':addr.value/unit, 'mine':self.wallets_list[wallet].wallet.is_mine(addr.address)})

            tx_list.append(table_row)
            row_count+=1

        tx_list[0].get_child(list(tx_list[0].children.keys())[0]).set_style({'border-radius': '0px 0px 0px 20px'})
        tx_list[0].get_child(list(tx_list[0].children.keys())[2]).set_style({'border-radius': '0px 0px 20px 0px'})

        table_title = gui.TableRow(('Date', 'Amount', ''))
        table_title.get_child(list(table_title.children.keys())[0]).set_style({'color': 'white', 'background-color':'#24303F', 'border-width':'0.1px', 'border-style':'none', 'border-radius': '20px 0px 0px 0px'})
        table_title.get_child(list(table_title.children.keys())[1]).set_style({'color': 'white', 'background-color':'#24303F', 'border-width':'0.1px', 'border-style':'none', 'border-radius': '0px 0px 0px 0px'})
        table_title.get_child(list(table_title.children.keys())[2]).set_style({'color': 'white', 'background-color':'#24303F', 'border-width':'0.1px', 'border-style':'none', 'border-radius': '0px 20px 0px 0px'})
        tx_list.append(table_title)

        tx_list.reverse()
        tx_table = gui.Table(tx_list, style={'width':'95%'})
        tx_table.on_table_row_click.do(self.get_tx_info)

        single_wallet_widgets = []
        single_wallet_widgets.append(self.logo)
        
        receive_button=gui.Label('Receive BTC', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px'})
        receive_button.onclick.do(self.go_to_receive, wallet)
        send_button=gui.Label('Send BTC', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px'})
        send_button.onclick.do(self.go_to_send, wallet)
        single_wallet_widgets.append(gui.HBox(children=[receive_button, send_button], style={'margin':'0px auto', 'width':'100%', 'background-color':'#1A222C'}))

        single_wallet_widgets.append(tx_table)
        delete_button=gui.Label('Delete Wallet', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#F71200', 'border-radius': '20px 20px 20px 20px'})
        delete_button.onclick.do(self.delete_wallet, wallet)
        single_wallet_widgets.append(self.back_button)
        single_wallet_widgets.append(delete_button)
        self.single_wallet_page = gui.VBox(children=single_wallet_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(self.single_wallet_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def go_back_main(self, widget):
        self.set_root_widget(self.wallet_list_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def go_back_single_wallet(self, widget):
        self.set_root_widget(self.single_wallet_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def go_to_receive(self, widget, wallet):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        receive_widgets = []
        receive_widgets.append(self.logo)
        for address in self.wallets_list[wallet].wallet.get_addresses():
            addr_hist = self.wallets_list[wallet].wallet.get_address_history_len(address)
            addr_balance = self.wallets_list[wallet].wallet.get_addr_balance(address)
            if addr_hist>0:
                button_row1=gui.Label(address, style={'font-size':'14px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'aqua', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
                button_row2=gui.Label('Used: '+str(addr_hist)+' times \U00002714 '+str(addr_balance[0]/unit)+' \U000023F3 '+str(addr_balance[1]/unit), style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'aqua', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})
            else:
                button_row1=gui.Label(address, style={'font-size':'14px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
                button_row2=gui.Label('Used: '+str(addr_hist)+' times \U00002714 '+str(addr_balance[0]/unit)+' \U000023F3 '+str(addr_balance[1]/unit), style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})

            button_row1.onclick.do(self.addr_to_qr, address)
            button_row2.onclick.do(self.addr_to_qr, address)
            receive_widgets.append(button_row1)
            receive_widgets.append(button_row2)
        receive_widgets.append(self.back_button)
        receive_page = gui.VBox(children=receive_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(receive_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def addr_to_qr(self, widget, address):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        atq_widgets = []
        atq_widgets.append(self.logo)

        image = qrcode.make(address)
        buffered = BytesIO()
        image.save(buffered, format="PNG")

        atq_widgets.append(gui.Image('data:image/png;base64, '+(base64.b64encode(buffered.getvalue())).decode('utf-8')))
        atq_widgets.append(self.back_button)
        atq_page = gui.VBox(children=atq_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(atq_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def go_to_send(self, widget, wallet):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        send_widgets = []
        send_widgets.append(self.logo)
        send_widgets.append(self.back_button)
        send_page = gui.VBox(children=send_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(send_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def delete_wallet(self, widget, *args):
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        wallet = args[0]
        def confirm(widget):
            os.remove(self.userdir+'/'+wallet)
            self.set_root_widget(self.wallet_list_page)
            self.execute_javascript('document.getElementById("spinner").style.display="none"')
        delete_wallet_widgets=[]
        delete_wallet_widgets.append(self.logo)
        delete_wallet_widgets.append(gui.Label('Deleting Wallet', style={'font-size':'20px', 'text-align':'center', 'margin':'5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '100%', 'background-color':'#F71200', 'border-radius': '0px 0px 0px 0px', 'border-style':'none'}))
        delete_wallet_widgets.append(gui.Label(wallet, style={'font-size':'20px', 'text-align':'center', 'margin':'0px 5px 20px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '100%', 'background-color':'#F71200', 'border-radius': '0px 0px 0px 0px', 'border-style':'none'}))
        confirm_button=gui.Label('Confirm', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#F71200', 'border-radius': '20px 20px 20px 20px'})
        cancel_button=gui.Label('Cancel', style={'font-size':'20px', 'text-align':'center','margin': '5px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 20px 20px'})
        cancel_button.onclick.do(self.go_back_main)
        confirm_button.onclick.do(confirm)
        delete_wallet_widgets.append(confirm_button)
        delete_wallet_widgets.append(cancel_button)
        delete_wallet_page = gui.VBox(children=delete_wallet_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(delete_wallet_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

    def get_tx_info(self, table, row, item):
        if not hasattr(row, 'tx_details'):
            return
        self.execute_javascript('document.getElementById("spinner").style.display=""')
        tx_info_widgets = []
        tx_info_widgets.append(self.logo)

        info_id_1 = gui.Label('Transaction ID', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        info_id_2 = gui.Label(row.tx_details['id'][:len(row.tx_details['id'])//2], style={'font-size':'14px', 'margin': '0px 5px 0px 5px','padding':'5px 20px 0px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 0px 0px', 'text-decoration':'none'})
        info_id_3 = gui.Label(row.tx_details['id'][len(row.tx_details['id'])//2:], style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'0px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px', 'text-decoration':'none'})
        info_id_2.type='a'
        info_id_2.attributes['href']='https://blockstream.info/tx/'+row.tx_details['id']
        info_id_2.attributes['target']='_blank'
        info_id_3.type='a'
        info_id_3.attributes['href']='https://blockstream.info/tx/'+row.tx_details['id']
        info_id_3.attributes['target']='_blank'

        tx_info_widgets.append(info_id_1)
        tx_info_widgets.append(info_id_2)
        tx_info_widgets.append(info_id_3)

        info_daytime_1 = gui.Label('Day and Time', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        info_daytime_2 = gui.Label(row.tx_details['time'], style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})
        tx_info_widgets.append(info_daytime_1)
        tx_info_widgets.append(info_daytime_2)
        
        info_amount_1 = gui.Label('Amount Transferred', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        info_amount_2 = gui.Label(row.tx_details['amount'], style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})
        if float(row.tx_details['amount'])>0:
            info_amount_2.set_style({'color':'lime'})
        else:
            info_amount_2.set_style({'color':'red'})
        tx_info_widgets.append(info_amount_1)
        tx_info_widgets.append(info_amount_2)

        info_block_1 = gui.Label('Block and Confirmations', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        info_block_2 = gui.Label(row.tx_details['block']+', '+row.tx_details['conf'], style={'font-size':'14px', 'margin': '0px 5px 5px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 20px 20px'})
        tx_info_widgets.append(info_block_1)
        tx_info_widgets.append(info_block_2)
        
        info_input_1 = gui.Label('Source Addresses', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        tx_info_widgets.append(info_input_1)
        for input_tx in row.tx_details['inputs']:
            if input_tx['mine']:
                tx_info_widgets.append(gui.Label(input_tx['address'], style={'font-size':'14px', 'margin': '0px 5px 0px 5px','padding':'0px 20px 0px 20px','color': 'aqua', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 0px 0px'}))
            else:
                tx_info_widgets.append(gui.Label(input_tx['address'], style={'font-size':'14px', 'margin': '0px 5px 0px 5px','padding':'0px 20px 0px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 0px 0px'}))
        tx_info_widgets[-1].style['margin']='0px 5px 5px 5px'
        tx_info_widgets[-1].style['padding']='0px 20px 5px 20px'
        tx_info_widgets[-1].style['border-radius']='0px 0px 20px 20px'

        info_output_1 = gui.Label('Destination Addresses', style={'font-size':'20px', 'margin': '5px 5px 0px 5px','padding':'5px 20px 5px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '20px 20px 0px 0px'})
        tx_info_widgets.append(info_output_1)
        for output_tx in row.tx_details['outputs']:
            if output_tx['mine']:
                tx_info_widgets.append(gui.Label(output_tx['address'], style={'font-size':'14px', 'margin': '0px 5px 0px 5px','padding':'0px 20px 0px 20px','color': 'aqua', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 0px 0px'}))
            else:
                tx_info_widgets.append(gui.Label(output_tx['address'], style={'font-size':'14px', 'margin': '0px 5px 0px 5px','padding':'0px 20px 0px 20px','color': 'white', 'width': '85%', 'background-color':'#24303F', 'border-radius': '0px 0px 0px 0px'}))
        tx_info_widgets[-1].style['margin']='0px 5px 5px 5px'
        tx_info_widgets[-1].style['padding']='0px 20px 5px 20px'
        tx_info_widgets[-1].style['border-radius']='0px 0px 20px 20px'

        tx_info_widgets.append(self.back_button)
        tx_info_page = gui.VBox(children=tx_info_widgets, style={'margin':'0px auto', 'background-color':'#1A222C'})
        self.set_root_widget(tx_info_page)
        self.execute_javascript('document.getElementById("spinner").style.display="none"')

        return

if __name__ == "__main__":
    start(rElectrum,
            certfile='./ssl_keys/fullchain.pem',
            keyfile='./ssl_keys/privkey.pem',
            ssl_version=ssl.PROTOCOL_TLSv1_2,
            address='0.0.0.0',
            port=8081,
            multiple_instance=True,
            enable_file_cache=True,
            start_browser=False,
            debug=False,
            update_interval = 0.1)


