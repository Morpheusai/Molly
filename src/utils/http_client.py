import time
import requests
import queue
import logging
from fastapi import status, HTTPException
from concurrent.futures import ThreadPoolExecutor

def raise_http_exception(result_code, result_message, status_code=status.HTTP_400_BAD_REQUEST):
    resp = {
        "result_code":result_code,
        "result_message":result_message
    }
    logging.error(f'User operation failed: resp {resp}')
    raise HTTPException(status_code=status_code, detail=resp)

class HttpClient(object):
    _instance = None
    executor = ThreadPoolExecutor(max_workers=10)
    qeue = queue.Queue()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(HttpClient, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):  # 防止多次初始化
            self._initialized = True
            HttpClient.executor.submit(self.process_queued_requests)

    def process_queued_requests(self):
        while not HttpClient.qeue.empty():
            request = HttpClient.qeue.get()
            HttpClient.http_execute(**request)

    @staticmethod
    def execute_no_response(url, method="GET", params=None, data=None, json=None, headers=None, timeout=5):
        """
        Sends an HTTP request.

        Parameters:
        - url (str): The URL to send the request to.
        - method (str, optional): The HTTP method to use. Defaults to "GET".
        - params (dict, optional): The query parameters to send. Defaults to None.
        - data (dict, optional): The data to send. Defaults to None.
        - headers (dict, optional): The headers to send. Defaults to None.
        - timeout (int, optional): The timeout in seconds. Defaults to 5.

        Returns:
        - dict: The response JSON.

        Raises:
        - Exception: If the request fails.
        """
        def http_request(url, method="GET", params=None, data=None, headers=None, timeout=5):
            try:
                requests.request(method, url, params=params, data=data, json=json, headers=headers, timeout=timeout)
            except requests.exceptions.Timeout as e:
                logging.error(f"Timeout error sending request to {url}: {e}")
                request = {
                    "url": url,
                    "method": method,
                    "params": params,
                    "data": data,
                    "json": json,
                    "headers": headers,
                    "timeout": timeout
                }
                time.sleep(3)
                HttpClient.qeue.put(request)
            except Exception as e:
                logging.error(f"Error sending request to {url}: {e}")
                raise e

        try :
            HttpClient.executor.submit(http_request, url, method, params, data, headers, timeout)
        except Exception as e:
            raise e
    
    @staticmethod
    def execute_wait_response(url, method="GET", params=None, data=None, json=None, headers=None, timeout=5):
        """
        Sends an HTTP request and waits for the response.

        Parameters:
        - url (str): The URL to send the request to.
        - method (str, optional): The HTTP method to use. Defaults to "GET".
        - params (dict, optional): The query parameters to send. Defaults to None.
        - data (dict, optional): The data to send. Defaults to None.
        - headers (dict, optional): The headers to send. Defaults to None.
        - timeout (int, optional): The timeout in seconds. Defaults to 5.

        Returns:
        - dict: The response JSON.

        Raises:
        - Exception: If the request fails.
        """
        execute_times = 0
        while True:
            try:
                response = requests.request(method, url, params=params, data=data, json=json, headers=headers, timeout=timeout)
                return response
            except requests.exceptions.Timeout as e:
                logging.error(f"Timeout error sending request to {url}: {e}")
                execute_times += 1
                if execute_times > 3:
                    return None
            except Exception as e:
                logging.error(f"Error sending request to {url}: {e}")
                return None
client = HttpClient()