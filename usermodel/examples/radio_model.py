"""Behavioural model of a 60 GHz chiplet-to-chiplet radio.

A START write sends the words in TX_FIFO. The transfer takes
bits / data_rate; STATUS.BUSY stays set until then and DONE is set after it.
The link budget uses free-space path loss over params["distance_mm"]:

    FSPL = 20 log10(4 pi d / lambda)
    RSSI = TX_POWER + 2 G - FSPL
    SNR  = RSSI - (-174 + 10 log10(B) + NF)
    BER  = 0.5 erfc(sqrt(SNR))            (BPSK/QPSK per bit)
"""


class Model(RegisterModel):
    def setup(self):
        self.busy_until = None
        self.pending = 0

    def link_budget(self):
        p = self.params
        lam_mm = 299.792458 / p["carrier_ghz"]
        fspl = 20 * math.log10(4 * math.pi * p["distance_mm"] / lam_mm)
        ptx = self["TX_POWER_DBM"].value
        ptx = ptx - (1 << 32) if ptx & 0x80000000 else ptx
        rssi = ptx + 2 * p["antenna_gain_dbi"] - fspl
        noise = -174 + 10 * math.log10(p["bandwidth_mhz"] * 1e6) + p["noise_figure_db"]
        snr_db = rssi - noise
        ber = 0.5 * math.erfc(math.sqrt(10 ** (snr_db / 10)))
        return rssi, snr_db, ber

    def update(self):
        st = self["STATUS"]
        st.set_field("FIFO_EMPTY", 0 if self["TX_FIFO"].fifo else 1)
        if self.busy_until is not None and self.t_ns >= self.busy_until:
            self.busy_until = None
            st.set_field("BUSY", 0)
            st.set_field("DONE", 1)
            self["TX_COUNT"].value += self.pending
            self.log(f"transfer done: {self.pending} words")

    def on_write(self, reg, value):
        if reg.name != "CTRL":
            return
        if reg.field("RESET"):
            self["TX_COUNT"].value = 0
            self["STATUS"].set_field("DONE", 0)
        if reg.field("START") and self.busy_until is None:
            words = len(self["TX_FIFO"].fifo)
            self["TX_FIFO"].fifo.clear()
            air = words * 32 / (self.params["data_rate_mbps"] * 1e6) * 1e9
            rssi, snr, ber = self.link_budget()
            self["RSSI_DBM"].value = self.to_u32(rssi)
            self["SNR_CDB"].value = self.to_u32(snr * 100)
            self["BER_PPM"].value = min(int(round(ber * 1e6)), 1_000_000)
            self["AIRTIME_NS"].value = int(round(air))
            self.pending = words
            self.busy_until = self.t_ns + air
            st = self["STATUS"]
            st.set_field("BUSY", 1)
            st.set_field("DONE", 0)
            self.log(f"start: {words} words, channel {self['CHANNEL'].value}, "
                     f"RSSI {rssi:.1f} dBm, SNR {snr:.1f} dB, BER {ber:.2e}, air {air:.1f} ns")
        reg.value = 0   # CTRL bits are self-clearing
