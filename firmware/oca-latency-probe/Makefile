# SPDX-License-Identifier: Apache-2.0
# OCA Chiplet Composer latency probe: measures firmware-visible AoU round trips
# on smu-vp.  Builds against tt-oca-harness-model's firmware infrastructure.
#   make MODEL_ROOT=/path/to/tt-oca-harness-model RISCV_PREFIX=riscv-none-elf-
MODEL_ROOT ?= ../../upstream/tt-oca-harness-model
export MODEL_ROOT

.PHONY: all smc sep clean
all: smc sep
smc:
	$(MAKE) -f smc.mk
sep:
	$(MAKE) -f sep.mk
clean:
	$(MAKE) -f smc.mk clean
	$(MAKE) -f sep.mk clean
