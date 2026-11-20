class Model(RegisterModel):
    def setup(self):
        self.done_at = None          # simulation time (ns) when the sum is ready

    def update(self):
        # called before every access: finish the job once its time has come
        if self.done_at is not None and self.t_ns >= self.done_at:
            self.done_at = None
            self["STATUS"].set_field("BUSY", 0)
            self["STATUS"].set_field("DONE", 1)

    def on_write(self, reg, value):
        if reg.name == "CTRL" and reg.field("START"):
            words = list(self["IN_FIFO"].fifo)
            self["IN_FIFO"].fifo.clear()
            self["RESULT"].value = sum(words) & 0xFFFFFFFF
            self.done_at = self.t_ns + len(words) * self.params["ns_per_word"]
            self["STATUS"].set_field("BUSY", 1)
            self["STATUS"].set_field("DONE", 0)
            self.log(f"adding {len(words)} words, ready at {self.done_at:.0f} ns")
            reg.value = 0            # START clears itself
