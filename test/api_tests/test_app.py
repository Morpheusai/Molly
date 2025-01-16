
import logging
import os
import sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../src"))
print(sys.path)
import requests
host_port = "http://127.0.0.1:60717"

def test_read_root():
    response = requests.get(url=host_port + "/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "我是Molly后端服务"}