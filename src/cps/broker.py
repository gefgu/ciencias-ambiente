"""Broker MQTT local em Python (amqtt) para testes sem Mosquitto instalado."""
from __future__ import annotations
import asyncio, threading, time
from amqtt.broker import Broker

CONFIG = {"listeners": {"default": {"type": "tcp", "bind": "127.0.0.1:1883"}}, "sys_interval": 0,
          "auth": {"allow-anonymous": True, "plugins": ["auth_anonymous"]}, "topic-check": {"enabled": False}}


class LocalBroker:
    def start(self, port: int = 1883):
        cfg = {**CONFIG, "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}}}
        self.loop = asyncio.new_event_loop()
        self.broker = Broker(cfg, loop=self.loop)
        self.thread = threading.Thread(target=lambda: (asyncio.set_event_loop(self.loop), self.loop.run_until_complete(self.broker.start()), self.loop.run_forever()), daemon=True)
        self.thread.start()
        time.sleep(1.5)
        return self

    def stop(self):
        try:
            asyncio.run_coroutine_threadsafe(self.broker.shutdown(), self.loop).result(5)
        except Exception:
            pass  # daemon thread: encerra com o processo
        self.loop.call_soon_threadsafe(self.loop.stop)
