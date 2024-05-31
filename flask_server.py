# !/usr/bin/python

from flask import Flask, request, jsonify
import subprocess
import csv
import re

app = Flask(__name__)
session_name = 'OP25_SESSION'


def kill_session():
    subprocess.Popen(f"screen -S {session_name} -X quit", shell=True)


def read_trunk_file(file_path):
    with open(file_path, mode='r', newline='') as file:
        reader = csv.DictReader(file, delimiter='\t', quoting=csv.QUOTE_ALL)
        data = [row for row in reader]
    return data


def modify_trunk_file(data, updates):
    for key, value in updates.items():
        if key in data[0]:
            data[0][key] = value
    return data


def save_trunk_file(data, file_path):
    with open(file_path, mode='w', newline='') as file:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)


def parse_write_config(data_str):
    updates = {}
    # Use regex to correctly split key-value pairs
    matches = re.findall(r'([^:]+?):\s*([^:]+?(?=\s+\w+:|$))', data_str)
    for key, value in matches:
        updates[key.strip()] = value.strip()
    return updates


@app.route('/hello', methods=['GET'])
def hello():
    return jsonify({"response": "ACK: HELLO"})


@app.route('/start_test', methods=['POST'])
def start_test():
    try:
        op25_cmd = f"./rx.py --args 'rtl' -N 'LNA:47' -S 2500000 -x 2 -T trunk.tsv -U -X -l http:0.0.0.0:8080"
        kill_session()
        subprocess.Popen(f"screen -dmS {session_name} {op25_cmd}", shell=True)
        return jsonify({"response": "ACK: OP25 started"})
    except Exception as e:
        return jsonify({"response": f"NACK: Error starting OP25 - {str(e)}"})


@app.route('/stop_op25', methods=['POST'])
def stop_op25():
    try:
        kill_session()
        return jsonify({"response": "ACK: OP25 stopped"})
    except Exception as e:
        return jsonify({"response": f"NACK: Error stopping OP25 - {str(e)}"})


@app.route('/get_output', methods=['GET'])
def get_output():
    try:
        output = subprocess.check_output(
            f"screen -S {session_name} -X hardcopy -h /tmp/screenlog.0 && cat /tmp/screenlog.0", shell=True)
        return jsonify({"response": output.decode('utf-8')})
    except Exception as e:
        return jsonify({"response": f"NACK: Error getting output - {str(e)}"})


@app.route('/get_config', methods=['GET'])
def get_config():
    try:
        file_path = 'trunk.tsv'
        data = read_trunk_file(file_path)
        if data:
            config = data[0]
            control_channel_list = config.get('Control Channel List', '')
            sysname = config.get('Sysname', '')
            talkgroup_list_name = config.get('TGID Tags File', '')
            response = f"Control Channel List: {control_channel_list} Sysname: {sysname} Talkgroup List Name: {talkgroup_list_name}"
            return jsonify({"response": response})
        else:
            return jsonify({"response": "NACK: No data found in trunk.tsv"})
    except Exception as e:
        return jsonify({"response": f"NACK: Error reading config - {str(e)}"})


import logging



@app.route('/write_config', methods=['POST'])
def write_config():
    logging.info("Received request to write config")
    try:
        data = request.get_json()  # Get JSON data from the request

        if data:
            logging.debug(f"Received JSON data: {data}")
            # Extract updates from the JSON data
            cc_list = data.get('Control_Channel_List', '')
            sysname = data.get('Sysname', '')
            tglist = data.get('Talkgroup_List_Name', '')

            file_path = 'trunk.tsv'
            data = read_trunk_file(file_path)
            if data:
                # Modify trunk file with the updates
                updates = {'Control Channel List': cc_list, 'Sysname': sysname, 'TGID Tags File': tglist}
                data = modify_trunk_file(data, updates)
                save_trunk_file(data, file_path)
                logging.info("Config updated successfully")
                return jsonify({"response": "ACK: Config updated"})
            else:
                logging.warning("No data found in trunk.tsv")
                return jsonify({"response": "NACK: No data found in trunk.tsv"})
        else:
            logging.warning("No JSON data received")
            return jsonify({"response": "NACK: No JSON data received"})
    except Exception as e:
        logging.error(f"Error updating config - {str(e)}")
        return jsonify({"response": f"NACK: Error updating config - {str(e)}"})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
