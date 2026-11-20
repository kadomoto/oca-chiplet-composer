# SPDX-License-Identifier: Apache-2.0
DIE   ?= 0
SMCT   = $(abspath $(MODEL_ROOT))/sw/smc-vp-tests
SRCS   = $(SMCT)/common/start.S smc_die$(DIE).c $(SMCT)/common/printf.c
OBJS   = $(SRCS:.c=.o)
OBJS  := $(OBJS:.S=.o)
TARGET = oca_d2d_smc$(DIE)
LDFLAGS += -T $(SMCT)/common/link.ld
include $(SMCT)/Makefile.common

# smc_die<N>.c #includes smc_main.c
smc_die$(DIE).o: smc_main.c
