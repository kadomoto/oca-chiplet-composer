# SPDX-License-Identifier: Apache-2.0
# Die-to-die ping-pong for mdie-vp: one SMC image per die plus a shared SEP image.
#   make MODEL_ROOT=/path/to/tt-oca-harness-model RISCV_PREFIX=riscv-none-elf-
MODEL_ROOT ?= ../../upstream/tt-oca-harness-model
export MODEL_ROOT

.PHONY: all clean
all:
	$(MAKE) -f smc.mk DIE=0
	$(MAKE) -f smc.mk DIE=1
	$(MAKE) -f sep.mk
clean:
	$(MAKE) -f smc.mk DIE=0 clean
	$(MAKE) -f smc.mk DIE=1 clean
	$(MAKE) -f sep.mk clean
