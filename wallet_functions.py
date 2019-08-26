from decimal import Decimal
import getpass
import datetime

from electrum import WalletStorage, Wallet
from electrum.util import format_satoshis
from electrum.bitcoin import is_address, COIN, TYPE_ADDRESS
from electrum.transaction import TxOutput, Transaction
from electrum.network import TxBroadcastError, BestEffortRequestFailed
from electrum.util import bfh
from electrum.bitcoin import base_encode

_ = lambda x:x  # i18n

class WalletInterface:

    def __init__(self, config, daemon, wallet_path):
        self.network = daemon.network
        storage = WalletStorage(wallet_path)

        self.str_recipient = ""
        self.str_description = ""
        self.str_amount = ""
        self.str_fee = ""

        self.config = config

        self.wallet = Wallet(storage)
        self.wallet.start_network(self.network)
        self.contacts = self.wallet.contacts

        self.network.register_callback(self.on_network, ['wallet_updated', 'network_updated', 'banner'])

    def on_network(self, event, *args):
        if event in ['wallet_updated', 'network_updated']:
            self.updated()
        elif event == 'banner':
            self.print_banner()

    def main_command(self):
        self.print_balance()

    def updated(self):
        return True

    def print_history(self):
        width = [20, 40, 14, 14]
        delta = (80 - sum(width) - 4)/3
        format_str = "%"+"%d"%width[0]+"s"+"%"+"%d"%(width[1]+delta)+"s"+"%" \
        + "%d"%(width[2]+delta)+"s"+"%"+"%d"%(width[3]+delta)+"s"
        messages = []

        for tx_hash, tx_mined_status, delta, balance in reversed(self.wallet.get_history()):
            if tx_mined_status.conf:
                timestamp = tx_mined_status.timestamp
                try:
                    time_str = datetime.datetime.fromtimestamp(timestamp).isoformat(' ')[:-3]
                except Exception:
                    time_str = "unknown"
            else:
                time_str = 'unconfirmed'

            label = self.wallet.get_label(tx_hash)
            messages.append( format_str%( time_str, label, format_satoshis(delta, whitespaces=True), format_satoshis(balance, whitespaces=True) ) )

        self.print_list(messages[::-1], format_str%( _("Date"), _("Description"), _("Amount"), _("Balance")))

    def get_balance(self):
        return(self.wallet.get_balance())

    def get_utxos(self):
        return(self.wallet.get_utxos())

    def get_history(self):
        return(self.wallet.get_history())

    def get_tx_out(self, txid):
        tx = None
        if self.wallet:
            tx = self.wallet.db.get_transaction(txid)
        if tx is None:
            raw = self.network.run_from_another_thread(self.network.get_transaction(txid))
            if raw:
                tx = Transaction(raw)
            else:
                return {}
        return tx.outputs()

    def get_tx_in(self, txid):
        tx = None
        if self.wallet:
            tx = self.wallet.db.get_transaction(txid)
        if tx is None:
            raw = self.network.run_from_another_thread(self.network.get_transaction(txid))
            if raw:
                tx = Transaction(raw)
            else:
                return {}
        final_tx_in = []
        for txin in tx.inputs():
            final_tx_in.append(self.get_tx_out(txin['prevout_hash'])[txin['prevout_n']])
        return final_tx_in

    def print_addresses(self):
        messages = map(lambda addr: "%30s    %30s       "%(addr, self.wallet.labels.get(addr,"")), self.wallet.get_addresses())
        self.print_list(messages, "%19s  %25s "%("Address", "Label"))

    def print_order(self):
        print("send order to " + self.str_recipient + ", amount: " + self.str_amount \
              + "\nfee: " + self.str_fee + ", desc: " + self.str_description)

    def enter_order(self):
        self.str_recipient = input("Pay to: ")
        self.str_description = input("Description : ")
        self.str_amount = input("Amount: ")
        self.str_fee = input("Fee: ")

    def send_order(self):
        self.do_send()

    def print_banner(self):
        for i, x in enumerate( self.wallet.network.banner.split('\n') ):
            print( x )

    def print_list(self, lst, firstline):
        lst = list(lst)
        self.maxpos = len(lst)
        if not self.maxpos: return
        print(firstline)
        for i in range(self.maxpos):
            msg = lst[i] if i < len(lst) else ""
            print(msg)

    def main(self):
        pass

    def prepare_tx(self):
        if not is_address(self.str_recipient):
            return 'Invalid Bitcoin address', ''
        try:
            amount = int(Decimal(self.str_amount) * COIN)
        except Exception:
            return 'Invalid Amount', ''
        try:
            fee = int(Decimal(self.str_fee) * COIN)
        except Exception:
            return 'Invalid Fee', ''

        if self.wallet.has_password():
            password = self.password_dialog()
            if not password:
                return
        else:
            password = None

#        c = ""
#        while c != "y":
#            c = input("ok to send (y/n)?")
#            if c == "n": return
#
        try:
            tx = self.wallet.mktx([TxOutput(TYPE_ADDRESS, self.str_recipient, amount)], password, self.config, fee)
            tx.set_rbf(True)
            return tx, base_encode(bfh(str(tx)), base=43)
        except Exception as e:
            return (repr(e)), ''

#        if self.str_description:
#            self.wallet.labels[tx.txid()] = self.str_description
#
#        print(_("Please wait..."))
#        try:
#            self.network.run_from_another_thread(self.network.broadcast_transaction(tx))
#        except TxBroadcastError as e:
#            msg = e.get_message_for_gui()
#            print(msg)
#        except BestEffortRequestFailed as e:
#            msg = repr(e)
#            print(msg)
#        else:
#            print(_('Payment sent.'))
#            #self.do_clear()
#            #self.update_contacts_tab()

    def network_dialog(self):
        print("use 'electrum setconfig server/proxy' to change your network settings")
        return True


    def settings_dialog(self):
        print("use 'electrum setconfig' to change your settings")
        return True

    def password_dialog(self):
        return getpass.getpass()


#   XXX unused

    def run_receive_tab(self, c):
        #if c == 10:
        #    out = self.run_popup('Address', ["Edit label", "Freeze", "Prioritize"])
        return

    def run_contacts_tab(self, c):
        pass
