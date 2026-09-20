"""Push notification abstraction (FCM-compatible, credential-gated).

Mock provider logs only. FCM provider requires FCM_SERVER_KEY (or
ENC:-encrypted) + FCM_API_URL; without them it reports NOT_CONFIGURED
instead of fake success. No push is ever claimed delivered when mocked.
"""
import os


class MockPushProvider:
    name = "MockPushProvider"

    def send(self, token: str, title: str, body: str) -> dict:
        masked = (token[:4] + "***") if token else "none"
        print(f"[push-mock] to={masked} title={title}")
        return {"status": "MOCK — logged only", "delivered": False}


class FcmProvider:
    name = "FcmProvider"

    def __init__(self):
        from app.auth import SecretBox
        self.key = SecretBox.reveal(os.getenv("FCM_SERVER_KEY", ""))
        self.url = os.getenv("FCM_API_URL", "https://fcm.googleapis.com/fcm/send")

    def send(self, token: str, title: str, body: str) -> dict:
        if not self.key:
            return {"status": "NOT_CONFIGURED — set FCM_SERVER_KEY", "delivered": False}
        import httpx
        try:
            r = httpx.post(self.url, json={"to": token,
                                           "notification": {"title": title, "body": body}},
                           headers={"Authorization": f"key={self.key}"}, timeout=10)
            ok = r.status_code in (200, 201)
            return {"status": "DELIVERED" if ok else f"FCM HTTP {r.status_code}",
                    "delivered": ok}
        except Exception as e:
            return {"status": f"FAILED: {type(e).__name__}", "delivered": False}


def get_push_provider():
    if os.getenv("PUSH_PROVIDER", "mock") == "fcm":
        return FcmProvider()
    return MockPushProvider()


def push_status() -> dict:
    p = get_push_provider()
    if isinstance(p, MockPushProvider):
        return {"push": "MOCK DELIVERY — logged only"}
    if not getattr(p, "key", ""):
        return {"push": "NOT_CONFIGURED — set FCM_SERVER_KEY"}
    return {"push": "LIVE provider configured — verification required"}
