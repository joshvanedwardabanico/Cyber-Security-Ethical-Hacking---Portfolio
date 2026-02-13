from scapy.all import sniff, IP, TCP, ARP    #---> libreria scapy è uno strumento molto potente per i pacchetti di rete, ci permette di creare pacchetti, inviare ricevere pacchetti, analizzare il traffico ed effettuare scansioni
from datetime import datetime        #---> usiamo datetime per aggiungere un tempo di scansione
                                                      #abbiamo scritto questo programma per intercettare i protocolli ARP,TCP,IPv4, PAYLOAD
def packet_handler(packet):
    timestamp = datetime.now().strftime("%H:%M:%S")       

    # ===== ARP ===== ----- essendo ARP un protocollo di livello 2/3 va gestito prima di IP/TCP
    if packet.haslayer(ARP):     #verifica se il pacchetto contiene l'Arp
        arp = packet[ARP]

        if arp.op == 1:
            op = "who-has"
        elif arp.op == 2:
            op = "is-at"
        else:
            op = f"op={arp.op}"

        print(
            f"{timestamp} ARP {op} "
            f"{arp.psrc} -> {arp.pdst} "     #{arp.psrc}= IP SORGENTE / {arp.pdst}= IP destinatario
            f"({arp.hwsrc})"  # ----> MAC sorgente
        )

    # ===== TCP =====
    elif packet.haslayer(IP) and packet.haslayer(TCP):    #verifica che il pacchetto contiene IP/TCP
        ip = packet[IP]
        tcp = packet[TCP]

        print(
            f"{timestamp} TCP "
            f"{ip.src}:{tcp.sport} -> {ip.dst}:{tcp.dport} "
            f"FLAGS=[{tcp.flags}] PAYLOAD={len(tcp.payload)}B"
        )

sniff(
    filter="tcp or arp",
    prn=packet_handler,
    store=False
)