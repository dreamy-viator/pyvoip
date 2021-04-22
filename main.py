
from client import Client

if __name__ == '__main__':
    REMOTE_IP = ""
    REMOTE_PORT = 4444

    MY_IP = ""
    MY_PORT = 4444
    client = Client(remote_host_address=REMOTE_IP,
                    remote_host_port=REMOTE_PORT,
                    host_address=MY_IP,
                    rtp_port=MY_PORT)

    room = input("Enter a room number : ")
    try:
        room_number = int(room)
    except ValueError:
        print('Enter a valid room number. ex) 1, 2, 3,...1000')

    client.start_calling(room_number)
    input("Press enter to exit ;)")