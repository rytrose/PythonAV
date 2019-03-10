from websocket import WS
from gpiozero import Button

if __name__ == '__main__':
    ws_server = WS()
    ws_server.start()


    def send_press():
        print("Button pressed!")
        ws_server.send("button", ["pressed"])


    button = Button(2)
    button.when_pressed = send_press
