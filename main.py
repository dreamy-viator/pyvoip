
from client import Client

if __name__ == '__main__':
    REMOTE_IP = "192.168.0.28"
    REMOTE_PORT = 4444
    MY_PORT = 4444
    client = Client(remote_host_address=REMOTE_IP,
                    remote_host_port=REMOTE_PORT,
                    rtp_port=MY_PORT)

    client.start_calling()
    input("Press enter to exit ;)")