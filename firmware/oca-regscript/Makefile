# SPDX-License-Identifier: Apache-2.0
# Register-script runner for chiplet logic models on mdie-vp.
#   make MODEL_ROOT=/path/to/tt-oca-harness-model RISCV_PREFIX=riscv-none-elf-
MODEL_ROOT ?= ../../upstream/tt-oca-harness-model
export MODEL_ROOT
.PHONY: all clean
all:
	$(MAKE) -f smc.mk IMG=rs
	$(MAKE) -f smc.mk IMG=idle
	$(MAKE) -f sep.mk
clean:
	$(MAKE) -f smc.mk IMG=rs clean
	$(MAKE) -f smc.mk IMG=idle clean
	$(MAKE) -f sep.mk clean
