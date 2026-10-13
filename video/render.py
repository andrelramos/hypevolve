"""Render the explainer composition frame by frame through the Chrome DevTools Protocol.

usage: render.py <index.html> <lang> stills <outdir> t1,t2,...
       render.py <index.html> <lang> video <out.mp4> [fps]
"""
import base64, json, os, socket, subprocess, sys, tempfile, time, urllib.request
import websocket

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, suppress_origin=True)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg["result"]

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")


def start(page):
    prof = tempfile.mkdtemp(prefix="hfchrome")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
                             "--window-size=1920,1080", "--hide-scrollbars", "--force-device-scale-factor=1",
                             "--allow-file-access-from-files", "--remote-allow-origins=*", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(100):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            ws = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
            break
        except Exception:
            time.sleep(.2)
    if ws is None:
        proc.terminate()
        raise RuntimeError("Chrome DevTools endpoint did not start")
    try:
        c = CDP(ws)
    except Exception:
        proc.terminate()
        raise
    return proc, c


def load(c, page, lang):
    c.call("Emulation.setDeviceMetricsOverride", width=1920, height=1080, deviceScaleFactor=1, mobile=False)
    c.call("Page.enable")
    c.call("Page.navigate", url="file://" + os.path.abspath(page) + "?render&lang=" + lang)
    for _ in range(100):
        try:
            if c.js("window.__ready === true"):
                break
        except Exception:
            pass
        time.sleep(.1)
    c.js("document.fonts.ready.then(() => true)")


def shot(c, t, fmt="png"):
    c.js(f"seek({t:.5f}); 1")
    r = c.call("Page.captureScreenshot", format=fmt, **({"quality": 94} if fmt == "jpeg" else {}),
               clip={"x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1})
    return base64.b64decode(r["data"])


def main():
    page, lang, mode, out = sys.argv[1:5]
    proc, c = start(page)
    try:
        load(c, page, lang)
        if mode == "stills":
            os.makedirs(out, exist_ok=True)
            for t in sys.argv[5].split(","):
                open(os.path.join(out, f"t{float(t):05.1f}.png"), "wb").write(shot(c, float(t)))
        else:
            fps = int(sys.argv[5]) if len(sys.argv) > 5 else 30
            dur = c.js("window.DURATION")
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                                   "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
            n = int(round(dur * fps)); t0 = time.time()
            for f in range(n):
                ff.stdin.write(shot(c, f / fps, "jpeg"))
                if f % 150 == 0:
                    print(f"frame {f}/{n} {time.time() - t0:.0f}s", flush=True)
            ff.stdin.close(); ff.wait()
    finally:
        proc.terminate()


main()
