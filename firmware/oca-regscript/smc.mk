# SPDX-License-Identifier: Apache-2.0
IMG   ?= rs
SMCT   = $(abspath $(MODEL_ROOT))/sw/smc-vp-tests
SRCS   = $(SMCT)/common/start.S smc_$(IMG).c $(SMCT)/common/printf.c
OBJS   = $(SRCS:.c=.o)
OBJS  := $(OBJS:.S=.o)
TARGET = oca_rs_$(IMG)
LDFLAGS += -T $(SMCT)/common/link.ld
include $(SMCT)/Makefile.common
smc_rs.o: oca_script.h
