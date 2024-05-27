import time
import requests
import socket
import threading


class OP25Client:
    def __init__(self, url, callback):
        self.url = url
        self.callback = callback
        self.connection_successful = False
        self.thread = None
        self.stop_event = threading.Event()

    def jsoncmd(self, command, arg1, arg2):
        try:
            payload = [{"command": command, "arg1": arg1, "arg2": arg2}]
            response = requests.post(self.url, json=payload)

            if response.status_code == 200:
                self.connection_successful = True
                return response.json()
            else:
                self.connection_successful = False
                return {"error": f"Failed to retrieve data. Status Code: {response.status_code}"}
        except Exception as e:
            self.connection_successful = False
            return {"error": f"An error occurred: {e}"}

    def get_latest_values(self):
        try:
            response_data = self.jsoncmd("update", 0, 0)

            if not response_data:
                return {}

            latest_values = {}
            for item in response_data:
                if item.get("json_type") == "change_freq":
                    latest_values['change_freq'] = {
                        "freq": item.get("freq"),
                        "tgid": item.get("tgid"),
                        "offset": item.get("offset"),
                        "tag": item.get("tag"),
                        "nac": item.get("nac"),
                        "system": item.get("system"),
                        "center_frequency": item.get("center_frequency"),
                        "tdma": item.get("tdma"),
                        "wacn": item.get("wacn"),
                        "sysid": item.get("sysid"),
                        "tuner": item.get("tuner"),
                        "sigtype": item.get("sigtype"),
                        "fine_tune": item.get("fine_tune"),
                        "error": item.get("error"),
                        "stream_url": item.get("stream_url"),
                    }
                elif item.get("json_type") == "trunk_update":
                    trunk_update_data = item.get(str(item.get("nac")))
                    if trunk_update_data:
                        latest_values['trunk_update'] = {
                            "top_line": trunk_update_data.get("top_line"),
                            "syid": trunk_update_data.get("syid"),
                            "rfid": trunk_update_data.get("rfid"),
                            "stid": trunk_update_data.get("stid"),
                            "sysid": trunk_update_data.get("sysid"),
                            "rxchan": trunk_update_data.get("rxchan"),
                            "txchan": trunk_update_data.get("txchan"),
                            "wacn": trunk_update_data.get("wacn"),
                            "secondary": trunk_update_data.get("secondary"),
                            "frequencies": trunk_update_data.get("frequencies"),
                            "frequency_data": trunk_update_data.get("frequency_data"),
                            "last_tsbk": trunk_update_data.get("last_tsbk"),
                            "tsbks": trunk_update_data.get("tsbks"),
                            "adjacent_data": trunk_update_data.get("adjacent_data"),
                        }
                elif item.get("json_type") == "rx_update":
                    latest_values['rx_update'] = {
                        "error": item.get("error"),
                        "fine_tune": item.get("fine_tune"),
                        "files": item.get("files"),
                    }

            return latest_values

        except Exception as e:
            print("An error occurred while fetching latest values:", e)
            return {}

    def run_loop(self):
        self.start_op25()
        while not self.stop_event.is_set():
            latest_values = self.get_latest_values()
            self.callback(latest_values)
            time.sleep(2)

    def send_cmd_to_op25(self, command):
        host = '192.168.4.1'
        port = 8081
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                client.connect((host, port))
                client.send(command.encode())
                response = client.recv(1024).decode()
                print('[DEBUG] Connecting to OP25 server')
                return response
            finally:
                client.close()
        except:
            return 'FAIL'

    def start_op25(self):
        while not self.stop_event.is_set():
            response = self.send_cmd_to_op25('HELLO')
            if 'HELLO' in response:
                print(response)
                start_response = self.send_cmd_to_op25('START_TEST')
                if "ACK" in start_response:
                    print('Starting OP25')
                    return "ACK"
            time.sleep(1)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run_loop)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        if self.thread is not None:
            self.stop_event.set()
            self.thread.join()
            self.thread = None

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()
# Example usage
def process_latest_values(latest_values):
    print("Processing latest values:", latest_values)


#if __name__ == "__main__":
#    client = OP25Client("http://192.168.4.1:8080", process_latest_values)
#    client.start()

    # To stop the client, you can call:
    # client.stop()
