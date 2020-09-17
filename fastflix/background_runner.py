# -*- coding: utf-8 -*-

from threading import Thread

from multiprocessing.connection import Listener


def listen():
    with Listener(("127.0.0.1", 6000), authkey=b"Do not let eve find us!") as listener:
        # Looping here so that the clients / party goers can
        # always come back for more than a single request
        while True:
            print("waiting for someone to ask for something")
            with listener.accept() as conn:
                args = conn.recv()

                if args == b"stop server":
                    print("Goodnight")
                    break
                elif isinstance(args, list):
                    # Very basic check, must be more secure in production
                    print("Someone wants me to do something")
                    result = run_command(*args)
                    conn.send(result)
                else:
                    conn.send(b"I have no idea what you want me to do")


def run_command(*args):
    print(*args)
    return 1
