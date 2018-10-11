from flask import Flask
import consul
import os


app = Flask(__name__)
config = {}

with open('system.properties') as f:
    for line in f.readlines():
        line = line.strip()
        parts = line.split("=")
        key = parts[0]
        value = parts[1]
        config[key] = value

if config['CONSUL_IP'] is None and not config['CONSUL_IP']:
    consul_ip = os.environ["HOST_IP"]
else:
    consul_ip = config['CONSUL_IP']

consul_port = 8500

cons = consul.Consul(host=consul_ip, port=int(consul_port))


def get_config_value(config_key):
    try:
        values = ''
        results = cons.kv.get(config_key, index=None)
        if results[1]:
            values = results[1]['Value']
    except Exception as e:
        print(e)
    return values



