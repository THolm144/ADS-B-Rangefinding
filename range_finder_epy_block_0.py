"""
Embedded Python Block: readsb SBS Message Source
Connects to readsb's SBS (BaseStation) TCP port, parses airborne
position messages, and publishes them as PMT dicts on a message
output port: {"icao":..., "lat":..., "lon":..., "alt":...}
Altitude is converted from feet (SBS) to meters.
"""

import pmt
import socket
import threading
import time
from gnuradio import gr


class blk(gr.basic_block):
    def __init__(self, host="localhost", port=30003):
        gr.basic_block.__init__(
            self,
            name="readsb SBS Source",
            in_sig=[],
            out_sig=[]
        )

        self.host = host
        self.port = port

        self.message_port_register_out(pmt.intern("pos_out"))

        self._stop_flag = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_flag.is_set():
            try:
                sock = socket.create_connection((self.host, self.port), timeout=5)
                sock.settimeout(1.0)
                buf = ""
                while not self._stop_flag.is_set():
                    try:
                        data = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        break  # connection closed, fall through to reconnect
                    buf += data.decode("utf-8", errors="ignore")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        self._parse_line(line.strip())
                sock.close()
            except (ConnectionRefusedError, OSError):
                pass  # readsb not up yet / connection dropped

            if not self._stop_flag.is_set():
                time.sleep(2.0)  # backoff before reconnect attempt

    def _parse_line(self, line):
        if not line.startswith("MSG"):
            return

        fields = line.split(",")
        if len(fields) < 16:
            return

        msg_type = fields[1]
        if msg_type != "3":       # airborne position only
            return

        icao = fields[4]
        alt_str = fields[11]
        lat_str = fields[14]
        lon_str = fields[15]

        if not (alt_str and lat_str and lon_str):
            return

        try:
            alt_ft = float(alt_str)
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            return

        alt_m = alt_ft * 0.3048

        d = {
            "icao": icao,
            "lat": lat,
            "lon": lon,
            "alt": alt_m,
        }

        self.message_port_pub(pmt.intern("pos_out"), pmt.to_pmt(d))

    def stop(self):
        self._stop_flag.set()
        self._thread.join(timeout=2.0)
        return super().stop()
