import collections
import threading

class RecognitionClient(object):
  def __init__(self):
    self._stop_event = threading.Event()
    self._request_condition = threading.Condition()
    self._response_condition = threading.Condition()
    self._requests = collections.deque()
    self._expected_responses = collections.deque()
    self._responses = {}

  def _next(self):
    with self._request_condition:
      while not self._requests and not self._stop_event.is_set():
        self._request_condition.wait()
      if len(self._requests) > 0:
        return self._requests.popleft()
      else:
        raise StopIteration()

  def next(self):
    return self._next()

  def __next__(self):
    return self._next()

  def add_response(self, response):
    with self._response_condition:
      request = self._expected_responses.popleft()
      self._responses[request] = response
      self._response_condition.notify_all()

  def add_request(self, request, id):
    with self._request_condition:
      self._requests.append(request)
      with self._response_condition:
        self._expected_responses.append(id)
      self._request_condition.notify()

  def close(self):
    self._stop_event.set()
    with self._request_condition:
      self._request_condition.notify()

  def recognize(self, to_recognize, id):
    self.add_request(to_recognize, id)
    with self._response_condition:
      while True:
        self._response_condition.wait()
        if id in self._responses:
          return self._responses[id]