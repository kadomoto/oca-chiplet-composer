# SPDX-License-Identifier: Apache-2.0
SMCT   = $(abspath $(MODEL_ROOT))/sw/smc-vp-tests
SRCS   = $(SMCT)/common/start.S smc_main.c $(SMCT)/common/printf.c
OBJS   = $(SRCS:.c=.o)
OBJS  := $(OBJS:.S=.o)
TARGET = oca_probe_smc
LDFLAGS += -T $(SMCT)/common/link.ld
include $(SMCT)/Makefile.common
