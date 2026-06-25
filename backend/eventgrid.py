"""Optional Azure Event Grid telemetry.

This is the Microsoft-architecture flex, NOT core function. It lives on a
side path: every publish is fire-and-forget on a background thread and
wrapped in try/except, so a dead network or a cloud hiccup can never delay
or break the serial write that actually sorts the item.

Enable with ESORT_EVENTGRID=1 and set:
    EVENTGRID_TOPIC_ENDPOINT
    EVENTGRID_TOPIC_KEY
"""

import os
import threading
import time


class EventGrid:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.client = None
        if not enabled:
            return
        try:
            from azure.eventgrid import EventGridPublisherClient
            from azure.core.credentials import AzureKeyCredential

            endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
            key = os.environ["EVENTGRID_TOPIC_KEY"]
            self.client = EventGridPublisherClient(endpoint, AzureKeyCredential(key))
            self._EventGridEvent = __import__(
                "azure.eventgrid", fromlist=["EventGridEvent"]
            ).EventGridEvent
            print("[eventgrid] publisher ready")
        except Exception as e:
            print(f"[eventgrid] init failed, telemetry disabled: {e}")
            self.enabled = False
            self.client = None

    def publish(self, class_name: str, conf: float):
        """Non-blocking: schedule the publish on a daemon thread and return
        immediately so the caller (the camera loop) is never held up."""
        if not self.enabled or not self.client:
            return
        threading.Thread(
            target=self._publish_blocking,
            args=(class_name, float(conf)),
            daemon=True,
        ).start()

    def _publish_blocking(self, class_name: str, conf: float):
        try:
            self.client.send(
                [
                    self._EventGridEvent(
                        subject="ewaste/sort",
                        event_type="EwasteSorted",
                        data={
                            "category": class_name,
                            "confidence": round(conf, 3),
                            "timestamp": time.time(),
                        },
                        data_version="1.0",
                    )
                ]
            )
        except Exception as e:
            print(f"[eventgrid] publish failed (ignored): {e}")
